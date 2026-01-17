# Logstash to Vector Migration - Implementation Tasks

## Overview

This document outlines the step-by-step implementation plan for migrating the Logstash configuration to Vector. The migration involves creating equivalent functionality using Vector's file source, remap transforms, and Elasticsearch sink.

## Phase 1: Project Setup and Analysis

### Setup Tasks
- [ ] T001 Create Vector configuration file structure
- [ ] T002 Set up development environment with Vector
- [ ] T003 Install Vector and verify version compatibility
- [ ] T004 Create test directory with sample log files
- [ ] T005 Set up validation scripts for comparing Logstash vs Vector output

### Analysis Tasks
- [ ] T006 Document all Logstash grok patterns and their Vector equivalents
- [ ] T007 Analyze multiline processing requirements for ap_log type
- [ ] T008 Identify Ruby script logic that needs VRL conversion
- [ ] T009 Map Logstash output configuration to Vector Elasticsearch sink
- [ ] T010 Create field mapping document (Logstash field → Vector field)

## Phase 2: File Source Configuration

### Basic File Input
- [ ] T101 Configure file source with glob pattern `/app/log/web_*.log`
- [ ] T102 Set `read_from: "end"` to match Logstash behavior
- [ ] T103 Add `system: "legendary"` field to all events
- [ ] T104 Configure basic file source options (data_dir, file_key, etc.)

### Multiline Processing (ap_log type)
- [ ] T105 Implement type detection for ap_log events
- [ ] T106 Configure multiline.start_pattern: `^\[%{DATA}\]\s\s\s\[%{DATA}\]\s\[TRACE\]\sbefore\sSysUuid::set():\scurSysUuid=%{GREEDYDATA}`
- [ ] T107 Set multiline.mode: "continue_through"
- [ ] T108 Configure multiline.condition_pattern (negated logic)
- [ ] T109 Set multiline.timeout_ms for timeout handling
- [ ] T110 Test multiline aggregation with sample ap_log data

## Phase 3: Path Parsing Transform

### Filename Extraction
- [ ] T201 Create remap transform for path parsing
- [ ] T202 Implement grok pattern: `%{GREEDYDATA}/%{NOTSPACE:filename}`
- [ ] T203 Extract filename field from file path
- [ ] T204 Validate filename extraction with test files

## Phase 4: Field Extraction Transforms

### Primary Fields (Single Pattern)
- [ ] T301 Create transform for `product` field: `.*(?i)product:"%{NOTSPACE:product}"`
- [ ] T302 Create transform for `layer` field: `.*(?i)layer:"%{NOTSPACE:layer}"`
- [ ] T303 Test product and layer extraction

### Complex Fields (Multiple Fallback Patterns)
- [ ] T304 Implement maskGroupId extraction with 5 fallback patterns:
  - Pattern 1: `.*(?i)mask_?group_?id:"%{NOTSPACE:maskGroupId}"`
  - Pattern 2: `.*(?i)maskGroupId->\s%{NOTSPACE:maskGroupId}`
  - Pattern 3: `.*(?i)reticleId="%{NOTSPACE:maskGroupId}"\>`
  - Pattern 4: `.*(?i)reticle_?id:"%{NOTSPACE:maskGroupId}"`
  - Pattern 5: `.*(?i)reticlelotid\s->\s%{NOTSPACE:maskGroupId}`
- [ ] T305 Implement Action field with 2 patterns:
  - Pattern 1: `.*(?i)Action:"%{NOTSPACE:Action}\:%{NOTSPACE:maskGroupId}"`
  - Pattern 2: `.*(?i)Action:"%{NOTSPACE:Action}"`
- [ ] T306 Implement maskLotId extraction with 4 patterns:
  - Pattern 1: `.*(?i)mask_?lot_?id:"%{NOTSPACE:maskLotId}"`
  - Pattern 2: `.*(?i)maskLotId->%{NOTSPACE:maskLotId}`
  - Pattern 3: `.*(?i)maskLotId->\s%{NOTSPACE:maskLotId}`
  - Pattern 4: `.*(?i)maskLotId\s=\s\'%{NOTSPACE:maskLotId}\'`

### Simple Fields
- [ ] T307 Implement MaskListNo extraction: `MaskListNo=%{NUMBER:MaskListNo}`
- [ ] T308 Implement rqstType extraction: `rqstType:"%{NOTSPACE:rqstType}"`
- [ ] T309 Implement IsQueryPhase extraction: `IsQueryPhase:"%{NOTSPACE:IsQueryPhase}"`
- [ ] T310 Implement srvObjCategory extraction: `srvObjCategory:"%{NOTSPACE:srvObjCategory}"`
- [ ] T311 Implement srvMethod extraction: `srvMethod:"%{NOTSPACE:srvMethod}"`
- [ ] T312 Implement Purge_Tool extraction: `purge_tool:"%{NOTSPACE:Purge_Tool}"`

## Phase 5: Processing Logic Transforms

### Tag Management (Ruby equivalent)
- [ ] T401 Create VRL logic to set MGtag = "null" when maskGroupId is null
- [ ] T402 Create VRL logic to set Ptag = "null" when product is null
- [ ] T403 Create VRL logic to set Ltag = "null" when layer is null
- [ ] T404 Test tag setting logic with various field combinations

### Field Combination Logic
- [ ] T405 Implement conditional logic: if MGtag == "null" and Ptag != "null" and Ltag != "null"
- [ ] T406 Set maskGroupId = product + "-" + layer in the conditional block
- [ ] T407 Test field combination with sample data

### Type Conversion
- [ ] T408 Convert MaskListNo to integer using to_int!()
- [ ] T409 Validate type conversion works correctly

### Conditional Field Removal
- [ ] T410 Implement condition: if "Y" in IsQueryPhase or "PHASE" in rqstType
- [ ] T411 Remove fields: maskLotId, maskGroupId, product, layer
- [ ] T412 Test conditional field removal logic

## Phase 6: Elasticsearch Output Configuration

### Basic Sink Configuration
- [ ] T501 Configure Elasticsearch sink with endpoint: `http://elasticsearch-fz1.engmon.svc.cluster.local:9200`
- [ ] T502 Set scheme to http
- [ ] T503 Configure SSL settings (verify: true, version: TLSV1_2)

### Authentication
- [ ] T504 Set up basic authentication with default credentials
- [ ] T505 Configure auth.strategy: "basic"
- [ ] T506 Set auth.user and auth.password to default values

### Index Configuration
- [ ] T507 Configure bulk.index template: `"{{ POD_NAMESPACE }}"`
- [ ] T508 Set logstash_format: true
- [ ] T509 Configure logstash_dateformat: "%Y.%m.%d"

### Buffer Configuration
- [ ] T510 Set buffer.flush_interval: 5s
- [ ] T511 Set buffer.chunk_limit_size: 8MB
- [ ] T512 Configure retry settings (retry_forever: true)
- [ ] T513 Set overflow_action: "block"
- [ ] T514 Configure timekey: 10s and timekey_wait: 5s

## Phase 7: Testing and Validation

### Unit Testing
- [ ] T601 Test each grok pattern individually with sample data
- [ ] T602 Test multiline processing with ap_log samples
- [ ] T603 Test conditional logic with various input scenarios
- [ ] T604 Test type conversions
- [ ] T605 Test field removal logic

### Integration Testing
- [ ] T606 Set up test Vector pipeline with sample logs
- [ ] T607 Run end-to-end processing and capture output
- [ ] T608 Compare Vector output with Logstash output
- [ ] T609 Validate Elasticsearch document structure
- [ ] T610 Test error handling with malformed logs

### Performance Testing
- [ ] T611 Load test with expected log volumes
- [ ] T612 Monitor memory and CPU usage
- [ ] T613 Test buffer behavior under load
- [ ] T614 Validate throughput requirements

## Phase 8: Documentation and Deployment

### Documentation
- [ ] T701 Update requirements.md with implementation details
- [ ] T702 Document VRL expressions used
- [ ] T703 Create troubleshooting guide
- [ ] T704 Document configuration parameters
- [ ] T705 Create runbook for operations

### Deployment Preparation
- [ ] T706 Create production-ready Vector configuration
- [ ] T707 Set up monitoring and alerting
- [ ] T708 Configure log rotation for Vector logs
- [ ] T709 Create rollback procedures
- [ ] T710 Document deployment steps

## Task Dependencies

### Phase Dependencies
- **Phase 1**: No dependencies - can start immediately
- **Phase 2**: Depends on Phase 1 completion
- **Phase 3**: Depends on Phase 2 completion
- **Phase 4**: Depends on Phase 3 completion
- **Phase 5**: Depends on Phase 4 completion
- **Phase 6**: Depends on Phase 5 completion
- **Phase 7**: Depends on Phase 6 completion
- **Phase 8**: Depends on Phase 7 completion

### Parallel Opportunities
- Within Phase 4: Field extraction tasks (T301-T312) can be implemented in parallel
- Within Phase 5: Processing logic tasks can be combined into fewer transforms
- Testing tasks (Phase 7) can run in parallel where possible

### Critical Path
1. File source configuration (Phase 2)
2. Basic field extraction (Phase 4, primary fields)
3. Processing logic (Phase 5)
4. Elasticsearch output (Phase 6)
5. End-to-end testing (Phase 7)

## Risk Mitigation

### High-Risk Tasks
- **T304-T306**: Complex grok patterns with multiple fallbacks - test extensively
- **T405-T407**: Field combination logic - verify with real data
- **T410-T412**: Conditional field removal - ensure no data loss

### Contingency Plans
- **Pattern Failures**: Have fallback parsing strategies
- **Performance Issues**: Optimize VRL expressions and buffer settings
- **Elasticsearch Issues**: Test with staging environment first

## Success Criteria Checklist

### Functional Completeness
- [ ] All 12 target fields extracted correctly
- [ ] Multiline processing works for ap_log type
- [ ] Conditional logic produces identical results to Logstash
- [ ] Elasticsearch documents match expected format

### Performance Requirements
- [ ] Processing latency within acceptable limits
- [ ] Memory usage reasonable for production load
- [ ] No significant backpressure under normal conditions

### Operational Readiness
- [ ] Configuration documented and version controlled
- [ ] Monitoring and alerting configured
- [ ] Rollback procedures documented
- [ ] Team trained on Vector operations

## Implementation Notes

### VRL Best Practices
- Use `parse_grok!()` for required parsing (with error handling)
- Use `parse_grok()` for optional parsing (returns null on failure)
- Combine related operations in single transforms to reduce overhead
- Use efficient conditional logic to minimize processing time

### Configuration Organization
- Group related transforms logically
- Use descriptive names for components
- Include comments in VRL expressions for maintainability
- Version control all configuration changes

### Testing Strategy
- Start with unit tests for individual components
- Progress to integration tests for end-to-end flows
- Use real log samples for validation
- Compare output with Logstash baseline

### Monitoring and Observability
- Enable Vector's internal metrics
- Monitor component_received_events_total and component_sent_events_total
- Set up alerts for component_errors_total
- Monitor buffer utilization and latency</content>
<parameter name="filePath">doc/todo.md