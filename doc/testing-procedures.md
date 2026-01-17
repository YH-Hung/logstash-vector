# Vector Configuration Testing and Validation Procedures

This document outlines the procedures for validating the Vector configuration and testing it against sample log files to ensure correct functionality.

## Prerequisites

- Vector CLI installed and available in PATH
- Sample log file: `sample/web_hmib_1.log`
- Access to a terminal/command line

## Configuration Validation

### Step 1: Validate Configuration Syntax

Run the following command to validate the Vector configuration for syntax errors:

```bash
vector validate impl/vector.yaml
```

**Expected Output:**
```bash
√ Loaded ["impl/vector.yaml"]
√ Component configuration
~ Health check disabled for "elasticsearch_output"
--------------------------------------------------
                                         Validated
```

**Success Criteria:**
- Configuration loads without errors
- Component configuration is validated
- Only warnings about missing Elasticsearch connectivity are acceptable

## Testing Against Sample Data

### Step 2: Prepare Test Configuration

Create a temporary test configuration that outputs to console instead of Elasticsearch:

```bash
# Create a test config file
cp impl/vector.yaml impl/test-vector.yaml
```

Edit `impl/test-vector.yaml` and modify the sinks section:

```yaml
# Replace the elasticsearch_output sink with:
sinks:
  console_output:
    type: console
    inputs:
      - parse_fields
    encoding:
      codec: json
```

### Step 3: Modify File Source for Testing

In `impl/test-vector.yaml`, update the file source to read from the sample file:

```yaml
sources:
  ap_log_files:
    type: file
    include:
      - sample/web_hmib_1.log  # Changed from /app/log/web_*.log
    start_at_beginning: true   # Added for testing
    file_key: path
    multiline:
      start_pattern: '^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'
      condition_pattern: '^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'
      mode: halt_before
      timeout_ms: 1000
```

### Step 4: Run Vector Test

Execute Vector with the test configuration:

```bash
vector --config impl/test-vector.yaml --quiet
```

**Expected Behavior:**
- Vector starts and processes the sample log file
- Two JSON events are output to console
- No grok parsing errors occur
- Vector exits after processing (since it's reading from a static file)

### Step 5: Verify Output

Check that the output contains the expected fields and values:

**First Event (Multiline - Lines 1-7):**
```json
{
  "filename": "web_hmib_1.log",
  "system": "legendary",
  "type": "ap_log",
  "product": "TMEF78",
  "layer": "376A-M001",
  "maskGroupId": "TMEF78-376A-M001",
  "maskLotId": "EBGN29J.1",
  "message": "[2026-01-16 09:10:33:130]   [a027d5c0-8560-49e7-8f82-70901077a4bf] [TRACE] before SysUuid::set(): curSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf, preSysUuid=\n[2026-01-16 09:10:33:142]   [8e475fe2-0680-41f2-b734-20cd691d05f9] [TRACE] after SysUuid::set(): curSysUuid=8e475fe2-0680-41f2-b734-20cd691d05f9, preSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf\n[2026-01-16 09:10:33:166]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rqst_DisplayInfo {\"mask_lot_id\":\"EBGN29J.1\"}\n[2026-01-16 09:10:33:203]   [8e475fe2-0680-41f2-b734-20cd691d05f9] CMMSSrv::DisplayInfo() Begin ***\n[2026-01-16 09:10:33:210]   [8e475fe2-0680-41f2-b734-20cd691d05f9] MASKLOTID = 'EBGN29J.1'\n[2026-01-16 09:10:33:210]   [8e475fe2-0680-41f2-b734-20cd691d05f9] CMMSSrv::DisplayInfo() END ***\n[2026-01-16 09:10:33:211]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rep_DisplayInfo {\"gTxId\":\"8e475fe2-0680-41f2-b734-20cd691d05f9\", \"mask_group_id\":\"TMEF78-376A-M001\", \"product\":\"TMEF78\", \"layer\":\"376A-M001\"}",
  "path": "sample/web_hmib_1.log",
  "source_type": "file",
  "timestamp": "2026-01-17T05:06:35.929107Z",
  "host": "your-hostname"
}
```

**Second Event (Single Line - Lines 8-9):**
```json
{
  "filename": "web_hmib_1.log",
  "system": "legendary",
  "type": "ap_log",
  "message": "[2026-01-16 09:10:33:130]   [8e475fe2-0680-41f2-b734-20cd691d05f9] [TRACE] before SysUuid::set(): curSysUuid=8e475fe2-0680-41f2-b734-20cd691d05f9, preSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf",
  "path": "sample/web_hmib_1.log",
  "source_type": "file",
  "timestamp": "2026-01-17T05:06:36.930870Z",
  "host": "your-hostname"
}
```

## Validation Checklist

### Functional Validation
- [ ] Configuration validates without errors
- [ ] Two events are generated from the sample file
- [ ] First event contains all extracted fields (product, layer, maskGroupId, maskLotId)
- [ ] Second event contains only basic fields (no extracted data expected)
- [ ] Multiline aggregation works correctly (first event spans lines 1-7)
- [ ] Filename extraction works (`web_hmib_1.log`)
- [ ] System field is set to `legendary`

### Performance Validation
- [ ] Vector starts without errors
- [ ] Processing completes in reasonable time (< 5 seconds for sample file)
- [ ] No grok parsing errors in logs
- [ ] Memory usage remains stable

## Troubleshooting

### Common Issues

**Issue: Configuration validation fails**
- Check YAML syntax and indentation
- Ensure all required fields are present
- Verify grok patterns are properly escaped

**Issue: No output generated**
- Verify file path in `include` matches sample file location
- Check that `start_at_beginning: true` is set for testing
- Ensure Vector has read permissions on the sample file

**Issue: Grok parsing errors**
- Check that multiline messages contain escaped quotes (`\"` instead of `"`)
- Verify grok patterns match the escaped JSON format
- Ensure pattern precedence (null checks) is working correctly

**Issue: Multiline aggregation not working**
- Verify `start_pattern` matches TRACE before lines
- Check `condition_pattern` stops at correct boundaries
- Test with `halt_before` mode configuration

### Debug Commands

**Check Vector version:**
```bash
vector --version
```

**Run with debug logging:**
```bash
vector --config impl/test-vector.yaml --log-level debug 2>&1 | head -50
```

**Test individual grok patterns:**
```bash
echo '{"test":"value"}' | vector vrl -c 'parse_grok!(., ".*test\\\":\\\"%{NOTSPACE:test}\\\"")'
```

## Automated Testing Script

Create a test script `test-vector.sh`:

```bash
#!/bin/bash
set -e

echo "=== Vector Configuration Testing ==="

# Validate configuration
echo "1. Validating configuration..."
if ! vector validate impl/vector.yaml > /dev/null 2>&1; then
    echo "❌ Configuration validation failed"
    exit 1
fi
echo "✅ Configuration validation passed"

# Create test config
echo "2. Creating test configuration..."
cp impl/vector.yaml impl/test-vector.yaml
# Use sed or similar to modify the test config as described above

# Run test
echo "3. Running test against sample data..."
output=$(vector --config impl/test-vector.yaml --quiet 2>/dev/null)

# Validate output
echo "4. Validating test results..."
if echo "$output" | grep -q '"product":"TMEF78"'; then
    echo "✅ Product field extraction working"
else
    echo "❌ Product field extraction failed"
    exit 1
fi

if echo "$output" | grep -q '"maskGroupId":"TMEF78-376A-M001"'; then
    echo "✅ MaskGroupId field extraction working"
else
    echo "❌ MaskGroupId field extraction failed"
    exit 1
fi

echo "🎉 All tests passed!"
```

## Integration Testing

For full integration testing with Elasticsearch:

1. Set up a test Elasticsearch instance
2. Update `impl/vector.yaml` with correct endpoints and credentials
3. Run Vector in the background: `vector --config impl/vector.yaml`
4. Verify documents are indexed with correct structure
5. Check that multiline events are properly stored
6. Validate field mappings and data types

## Maintenance

- Re-run validation after any configuration changes
- Test with new sample data when available
- Update grok patterns if log format changes
- Monitor for new Vector versions and compatibility</content>
<parameter name="filePath">doc/testing-procedures.md