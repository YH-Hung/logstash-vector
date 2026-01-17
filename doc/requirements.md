# Logstash to Vector Migration - Requirements Documentation

## Project Overview

This project aims to migrate a Logstash configuration to Vector while maintaining identical log parsing and forwarding functionality. The original Logstash pipeline processes Apache logs (`ap_log` type) from files matching `/app/log/web_*.log`, applies extensive grok parsing to extract structured data, and forwards the processed logs to Elasticsearch.

## Functional Requirements

### Input Requirements

**Source**: File-based log ingestion
- **Path Pattern**: `/app/log/web_*.log`
- **Read Position**: Start from end of file (`read_from: "end"`)
- **Type**: `ap_log`
- **Additional Field**: `system => "legendary"`

**Multiline Processing** (ap_log type only):
- **Start Pattern**: `\[%{DATA}\]\s\s\s\[%{DATA}\]\s\[TRACE\]\sbefore\sSysUuid::set():\scurSysUuid=%{GREEDYDATA}`
  - **Meaning**: Matches log lines that start with timestamp patterns followed by TRACE level messages about SysUuid being set
  - **Pattern Breakdown**: `\[%{DATA}\]` matches timestamp with spaces/colons (like `2026-01-16 09:10:33:130`), `\s\s\s` matches three spaces, `\[%{DATA}\]` matches UUID (like `a027d5c0-8560-49e7-8f82-70901077a4bf`), `\s\[TRACE\]` matches space and TRACE level, remaining text matches the SysUuid message content
  - **Example**: Matches `[2026-01-16 09:10:33:130]   [a027d5c0-8560-49e7-8f82-70901077a4bf] [TRACE] before SysUuid::set(): curSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf, preSysUuid=`
- **Mode**: `continue_through` (continue aggregating lines while the condition pattern matches)
- **Condition Pattern**: NOT matching the start pattern (negate: true)
- **Behavior**: When a line matches the start pattern, it begins a new multiline event. All subsequent lines that DON'T match the start pattern are appended to this event until another start pattern is found.
- **Real Example**: The first TRACE line starts a multiline event, and the following 6 lines (until the next TRACE "before" line) would be combined into one log event:
  ```
  [2026-01-16 09:10:33:130]   [a027d5c0-8560-49e7-8f82-70901077a4bf] [TRACE] before SysUuid::set(): curSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf, preSysUuid=
  [2026-01-16 09:10:33:142]   [8e475fe2-0680-41f2-b734-20cd691d05f9] [TRACE] after SysUuid::set(): curSysUuid=8e475fe2-0680-41f2-b734-20cd691d05f9, preSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf
  [2026-01-16 09:10:33:166]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rqst_DisplayInfo {"mask_lot_id":"EBGN29J.1"}
  [2026-01-16 09:10:33:203]   [8e475fe2-0680-41f2-b734-20cd691d05f9] CMMSSrv::DisplayInfo() Begin ***
  [2026-01-16 09:10:33:210]   [8e475fe2-0680-41f2-b734-20cd691d05f9] MASKLOTID = 'EBGN29J.1'
  [2026-01-16 09:10:33:210]   [8e475fe2-0680-41f2-b734-20cd691d05f9] CMMSSrv::DisplayInfo() END ***
  [2026-01-16 09:10:33:211]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rep_DisplayInfo {"gTxId":"8e475fe2-0680-41f2-b734-20cd691d05f9", "mask_group_id":"TMEF78-376A-M001", "product":"TMEF78", "layer":"376A-M001"}
  ```

### Parsing Requirements

The system must extract the following fields using grok patterns with fallback alternatives. Each pattern is explained below with its meaning, what it matches, and examples.

#### Grok Pattern Reference
**Common Grok Patterns Used**:
- `%{GREEDYDATA}`: Matches any characters (including spaces and newlines) greedily
- `%{NOTSPACE}`: Matches any sequence of non-whitespace characters
- `%{NUMBER}`: Matches numeric values (integers and decimals)
- `%{DATA}`: Matches any characters except newlines (including spaces and special characters)
- `.*`: Regex pattern matching any characters (including spaces)
- `(?i)`: Case-insensitive flag for regex patterns
- `\s`: Matches whitespace characters (spaces, tabs, etc.)
- `\"`: Matches literal quote character
- `\>`: Matches literal greater-than character

**Pattern Structure**: Most patterns follow the format `.*(?i)field_name:"%{NOTSPACE:captured_field}"` which means:
- `.*` - Match any preceding text
- `(?i)` - Case insensitive
- `field_name:` - Literal field name with colon
- `\"` - Opening quote
- `%{NOTSPACE:captured_field}` - Capture non-space characters into the specified field
- `\"` - Closing quote (implied)

#### Core Fields
1. **filename** - Extracted from path using `%{GREEDYDATA}/%{NOTSPACE:filename}`
   - **Meaning**: Extracts the filename from the file path
   - **Pattern Breakdown**: `%{GREEDYDATA}` captures everything before the last `/`, then `%{NOTSPACE:filename}` captures the filename (non-space characters)
   - **Example**: From `/app/log/web_hmib_1.log` → extracts `web_hmib_1.log`

#### Primary Fields (Single Pattern)
2. **product** - `.*(?i)"product":"%{NOTSPACE:product}"`
   - **Meaning**: Matches any text followed by "product:" (case-insensitive) with quoted field name and captures the quoted value
   - **Pattern Breakdown**: `.*` matches anything, `(?i)` makes it case-insensitive, `"product":` is literal text with quotes around field name, `%{NOTSPACE:product}` captures non-space characters as the product value
   - **Example**: From `{"product":"TMEF78"}` → extracts `TMEF78`

3. **layer** - `.*(?i)"layer":"%{NOTSPACE:layer}"`
   - **Meaning**: Matches any text followed by "layer:" (case-insensitive) with quoted field name and captures the quoted value
   - **Pattern Breakdown**: Similar to product pattern but matches "layer:" instead with quotes around field name
   - **Example**: From `{"layer":"376A-M001"}` → extracts `376A-M001`

#### Complex Fields (Multiple Fallback Patterns)
4. **maskGroupId** - Multiple patterns with precedence (tries each pattern in order until one matches):
   - Pattern 1: `.*(?i)"mask_?group_?id":"%{NOTSPACE:maskGroupId}"`
     - **Meaning**: Matches "mask_group_id", "maskgroup_id", "mask_group_id", or "maskgroupid" (case-insensitive) with quoted field name followed by quoted value
     - **Example**: From `{"mask_group_id":"TMEF78-376A-M001"}` → extracts `TMEF78-376A-M001`
   - Pattern 2: `.*(?i)maskGroupId->\s%{NOTSPACE:maskGroupId}`
     - **Meaning**: Matches "maskGroupId->" followed by space and value
     - **Example**: From `maskGroupId-> MG001` → extracts `MG001`
   - Pattern 3: `.*(?i)reticleId="%{NOTSPACE:maskGroupId}"\>`
     - **Meaning**: Matches "reticleId=" followed by quoted value and closing bracket
     - **Example**: From `reticleId="MG001">` → extracts `MG001`
   - Pattern 4: `.*(?i)"reticle_?id":"%{NOTSPACE:maskGroupId}"`
     - **Meaning**: Matches "reticle_id" or "reticleid" (case-insensitive) with quoted field name followed by quoted value
     - **Example**: From `"reticle_id":"MG001"` → extracts `MG001`
   - Pattern 5: `.*(?i)reticlelotid\s->\s%{NOTSPACE:maskGroupId}`
     - **Meaning**: Matches "reticlelotid -> " followed by value
     - **Example**: From `reticlelotid -> MG001` → extracts `MG001`

5. **Action** - Multiple patterns:
   - Pattern 1: `.*(?i)"Action":"%{NOTSPACE:Action}\:%{NOTSPACE:maskGroupId}"`
     - **Meaning**: Matches "Action:" with quoted field name followed by value, colon, and maskGroupId value
     - **Example**: From `"Action":"CREATE:MG001"` → extracts `Action: CREATE`, `maskGroupId: MG001`
   - Pattern 2: `.*(?i)"Action":"%{NOTSPACE:Action}"`
     - **Meaning**: Matches "Action:" with quoted field name followed by quoted value (fallback when no maskGroupId)
     - **Example**: From `"Action":"CREATE"` → extracts `CREATE`

6. **maskLotId** - Multiple patterns:
   - Pattern 1: `.*(?i)"mask_?lot_?id":"%{NOTSPACE:maskLotId}"`
     - **Meaning**: Matches variations of "mask_lot_id" with quoted field name followed by quoted value
     - **Example**: From `{"mask_lot_id":"EBGN29J.1"}` → extracts `EBGN29J.1`
   - Pattern 2: `.*(?i)maskLotId->%{NOTSPACE:maskLotId}`
     - **Meaning**: Matches "maskLotId->" followed by value (no space)
     - **Example**: From `maskLotId->ML001` → extracts `ML001`
   - Pattern 3: `.*(?i)maskLotId->\s%{NOTSPACE:maskLotId}`
     - **Meaning**: Matches "maskLotId-> " followed by value (with space)
     - **Example**: From `maskLotId-> ML001` → extracts `ML001`
   - Pattern 4: `.*(?i)maskLotId\s=\s\'%{NOTSPACE:maskLotId}\'`
     - **Meaning**: Matches "maskLotId = 'value'" with single quotes
     - **Example**: From `MASKLOTID = 'EBGN29J.1'` → extracts `EBGN29J.1`

#### Simple Fields
7. **MaskListNo** - `MaskListNo=%{NUMBER:MaskListNo}`
   - **Meaning**: Matches "MaskListNo=" followed by a number
   - **Pattern Breakdown**: `MaskListNo=` is literal text, `%{NUMBER:MaskListNo}` captures numeric value
   - **Example**: From `MaskListNo=123` → extracts `123`

8. **rqstType** - `"rqstType":"%{NOTSPACE:rqstType}"`
   - **Meaning**: Matches "rqstType:" with quoted field name followed by quoted value
   - **Example**: From `"rqstType":"QUERY"` → extracts `QUERY`

9. **IsQueryPhase** - `"IsQueryPhase":"%{NOTSPACE:IsQueryPhase}"`
   - **Meaning**: Matches "IsQueryPhase:" with quoted field name followed by quoted value
   - **Example**: From `"IsQueryPhase":"Y"` → extracts `Y`

10. **srvObjCategory** - `"srvObjCategory":"%{NOTSPACE:srvObjCategory}"`
    - **Meaning**: Matches "srvObjCategory:" with quoted field name followed by quoted value
    - **Example**: From `"srvObjCategory":"MASK"` → extracts `MASK`

11. **srvMethod** - `"srvMethod":"%{NOTSPACE:srvMethod}"`
    - **Meaning**: Matches "srvMethod:" with quoted field name followed by quoted value
    - **Example**: From `"srvMethod":"GET_MASK_INFO"` → extracts `GET_MASK_INFO`

12. **Purge_Tool** - `"purge_tool":"%{NOTSPACE:Purge_Tool}"`
    - **Meaning**: Matches "purge_tool:" with quoted field name followed by quoted value
    - **Example**: From `"purge_tool":"PURGE_V1"` → extracts `PURGE_V1`

### Processing Logic

#### Tag Management (Ruby equivalent in VRL)
- Set `MGtag = "null"` if `maskGroupId` is null
- Set `Ptag = "null"` if `product` is null
- Set `Ltag = "null"` if `layer` is null

#### Field Combination Logic
If `MGtag == "null"` AND `Ptag != "null"` AND `Ltag != "null"`:
- Set `maskGroupId = product + "-" + layer`
- **Real Example**: If `maskGroupId` is missing but `product` is `"TMEF78"` and `layer` is `"376A-M001"`, then `maskGroupId` becomes `"TMEF78-376A-M001"`

#### Type Conversion
- Convert `MaskListNo` to integer

#### Conditional Field Removal
If `"Y" in IsQueryPhase` OR `"PHASE" in rqstType`:
- Remove fields: `maskLotId`, `maskGroupId`, `product`, `layer`
- **Purpose**: Query phase operations don't need mask/lot identification, so these fields are removed to avoid confusion

### Output Requirements

**Destination**: Elasticsearch
- **Host**: `elasticsearch-fz1.engmon.svc.cluster.local`
- **Port**: `9200`
- **Scheme**: `http`
- **SSL Verification**: `true`
- **SSL Version**: `TLSV1_2`
- **Authentication**: Use default credentials (`use_default`)
- **Index Pattern**: `{{ POD_NAMESPACE }}` with date format `%Y.%m.%d`
- **Logstash Format**: `true`
- **Buffer Settings**:
  - Flush interval: 5 seconds
  - Chunk limit size: 8MB
  - Retry forever: `true`
  - Overflow action: `block`
  - Time key: 10 seconds
  - Time key wait: 5 seconds

## Technical Requirements

### Vector Configuration Structure

```
sources:
  file_input:
    # File source configuration

transforms:
  parse_filename:
    # Extract filename from path

  multiline_processor:
    # Handle multiline logs for ap_log type

  field_parser:
    # Primary grok parsing for all fields

  tag_manager:
    # Implement tag setting logic

  field_combiner:
    # Combine product and layer into maskGroupId

  type_converter:
    # Convert MaskListNo to integer

  conditional_remover:
    # Remove fields based on query phase logic

sinks:
  elasticsearch_output:
    # Elasticsearch sink configuration
```

### Vector Component Specifications

#### File Source (`file`)
- **include**: `["/app/log/web_*.log"]`
- **read_from**: `"end"`
- **multiline**: Conditional for `ap_log` type (requires type detection first)

#### Remap Transforms (`remap`)
- **Language**: VRL (Vector Remap Language)
- **Key Functions**:
  - `parse_grok!()` for pattern matching
  - `exists()` for field checking
  - `del()` for field removal
  - Conditional logic with `if/else`
  - String concatenation with `+`

#### Elasticsearch Sink (`elasticsearch`)
- **endpoints**: `["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]`
- **bulk.index**: `"{{ POD_NAMESPACE }}"`
- **auth**: Basic auth with default credentials
- **buffer**: Custom buffer configuration
- **request**: Appropriate timeouts and retry settings

## Data Flow

1. **Input**: Files matching `/app/log/web_*.log` are tailed
2. **Type Detection**: Identify `ap_log` type and apply multiline processing
3. **Path Parsing**: Extract filename from file path
4. **Field Extraction**: Apply all grok patterns to extract structured data
5. **Tag Management**: Set null tags for missing fields
6. **Field Combination**: Generate `maskGroupId` from `product` and `layer` when needed
7. **Type Conversion**: Convert numeric fields to appropriate types
8. **Conditional Processing**: Remove fields based on query phase detection
9. **Output**: Forward processed logs to Elasticsearch with proper indexing

## Success Criteria

### Functional Validation
- **Field Extraction**: All 12 target fields must be extracted correctly
- **Multiline Handling**: ap_log multiline events must be aggregated properly
- **Conditional Logic**: Field combination and removal must work as specified
- **Type Conversion**: Numeric fields must be converted correctly

### Performance Requirements
- **Latency**: Processing should not introduce significant delays
- **Throughput**: Must handle expected log volume without backpressure
- **Resource Usage**: Memory and CPU usage should be reasonable

### Compatibility Requirements
- **Elasticsearch**: Must be compatible with target Elasticsearch version
- **Data Format**: Output must match Logstash format expectations
- **Error Handling**: Must handle malformed logs gracefully

## Testing Requirements

### Unit Tests
- Test each grok pattern individually
- Test multiline aggregation logic
- Test conditional field processing
- Test type conversions

### Integration Tests
- End-to-end processing from sample logs
- Elasticsearch indexing verification
- Error handling scenarios

### Performance Tests
- Load testing with expected log volumes
- Memory usage monitoring
- CPU usage monitoring

## Migration Considerations

### Logstash to Vector Differences
- **Configuration Format**: Ruby DSL → YAML/TOML
- **Processing Logic**: Ruby code → VRL expressions
- **Multiline**: Logstash multiline filter → File source multiline option
- **Output**: Logstash elasticsearch output → Vector elasticsearch sink

### Compatibility Verification
- **Pattern Accuracy**: All grok patterns must produce identical results
- **Field Mapping**: All field names and types must match
- **Conditional Logic**: All business rules must be preserved
- **Output Format**: Elasticsearch documents must be structurally identical

## Implementation Notes

### VRL Pattern Development
- Use `parse_grok!()` for infallible parsing (with error handling)
- Implement fallback logic for multiple patterns per field
- Use conditional assignments for tag management
- Implement string concatenation for field combination

### Error Handling
- All grok parsing should be wrapped in error handling
- Failed parsing should not stop pipeline processing
- Log parsing errors appropriately for debugging

### Performance Optimization
- Minimize the number of remap transforms
- Combine related operations in single transforms
- Use efficient VRL expressions
- Configure appropriate buffer sizes

## Risk Assessment

### High Risk Items
- **Complex Grok Patterns**: Multiple fallback patterns may have edge cases
- **Conditional Logic**: Business rules must be implemented exactly
- **Multiline Processing**: ap_log multiline logic is complex

### Mitigation Strategies
- **Comprehensive Testing**: Test with real log samples
- **Pattern Validation**: Verify each grok pattern individually
- **Incremental Implementation**: Build and test each component separately
- **Fallback Handling**: Ensure graceful handling of parsing failures</content>
<parameter name="filePath">doc/requirements.md