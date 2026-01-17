# Integration Testing for Logstash → Vector Migration

This directory contains integration tests to validate the functional parity between the original Logstash configuration and the new Vector implementation.

## Overview

The integration testing framework consists of:
- **Baseline Generation**: Run Logstash with sample data to create reference output
- **Vector Testing**: Run Vector with the same data
- **Output Comparison**: Compare outputs field-by-field
- **Error Handling**: Validate graceful handling of malformed data

## Quick Start

### Prerequisites
- Docker and Docker Compose (for Logstash baseline)
- Vector CLI installed ([installation guide](https://vector.dev/docs/setup/installation/))
- Python 3.7+ (for comparison script)

### Running Tests

**Option 1: Quick Test (Vector only, no baseline comparison)**
```bash
./run_all_tests.sh
```

**Option 2: Full Integration Test (includes Logstash baseline comparison)**
```bash
# Step 1: Generate Logstash baseline
./baseline_generator.sh

# Step 2: Run Vector tests
./vector_test_runner.sh

# Step 3: Compare outputs
python3 compare_outputs.py

# Or run all at once:
./run_all_tests.sh
```

## Directory Structure

```
tests/integration/
├── README.md                      # This file
├── docker-compose.yml             # Logstash + Elasticsearch setup
├── baseline_generator.sh          # Generate Logstash baseline
├── vector_test_runner.sh          # Run Vector tests
├── compare_outputs.py             # Compare Logstash vs Vector output
├── run_all_tests.sh               # Master test runner
├── logstash/
│   └── pipeline/
│       └── logstash.conf          # Logstash configuration
├── data/
│   ├── samples/                   # Test log files
│   │   ├── web_hmib_1.log        # Original sample
│   │   ├── web_query_phase_test.log
│   │   └── web_all_fields_test.log
│   ├── malformed/                 # Error handling test data
│   │   └── web_malformed_test.log
│   ├── baseline/                  # Generated baseline outputs
│   │   ├── logstash-baseline.json
│   │   ├── vector-output.json
│   │   └── elasticsearch-docs.json
│   └── results/                   # Test results
└── output/                        # Temporary output files
```

## Test Scripts

### baseline_generator.sh
Generates the Logstash baseline output for comparison.

**What it does:**
1. Starts Elasticsearch in Docker
2. Runs Logstash with sample logs
3. Captures JSON output to `data/baseline/logstash-baseline.json`
4. Saves Elasticsearch documents for validation

**Usage:**
```bash
./baseline_generator.sh
```

**Output files:**
- `data/baseline/logstash-baseline.json` - JSON lines format
- `data/baseline/elasticsearch-docs.json` - ES query results

**Cleanup:**
```bash
docker-compose down
```

### vector_test_runner.sh
Runs Vector against test data and validates processing.

**What it does:**
1. Validates Vector configuration
2. Creates test-specific config
3. Runs Vector with sample data
4. Captures JSON output to `data/baseline/vector-output.json`
5. Runs Vector's built-in unit tests

**Usage:**
```bash
./vector_test_runner.sh
```

**Output files:**
- `data/baseline/vector-output.json` - JSON lines format

### compare_outputs.py
Compares Logstash and Vector outputs field-by-field.

**What it does:**
1. Loads both baseline files
2. Compares all 12 critical business fields
3. Compares metadata fields (system, type, filename)
4. Generates detailed comparison report

**Usage:**
```bash
python3 compare_outputs.py
```

**Exit codes:**
- `0` - Perfect match (100%)
- `1` - Partial pass (≥90% match)
- `2` - Fail (<90% match)
- `3` - Error (files not found)

### run_all_tests.sh
Master test runner that orchestrates all integration tests.

**What it does:**
1. Runs Vector built-in unit tests
2. Executes Vector test run
3. Optionally runs baseline comparison
4. Generates summary report

**Usage:**
```bash
./run_all_tests.sh
```

## Test Data

### Sample Logs

**web_hmib_1.log**
- Original sample from production
- Contains multiline events
- Tests basic field extraction

**web_query_phase_test.log**
- Tests query phase logic
- Validates field removal when `IsQueryPhase:"Y"` or `rqstType:"QUERY_PHASE"`

**web_all_fields_test.log**
- Tests all 12 target fields
- Tests multiple grok pattern fallbacks
- Validates all parsing patterns

**web_malformed_test.log**
- Malformed timestamps
- Incomplete JSON
- Special characters
- Unicode content
- Tests error resilience

## Fields Validated

### Critical Business Fields
- `product` - Product identifier
- `layer` - Layer identifier
- `maskGroupId` - Mask group ID (or derived from product-layer)
- `maskLotId` - Mask lot identifier
- `Action` - Action field
- `MaskListNo` - Mask list number (integer)
- `rqstType` - Request type
- `IsQueryPhase` - Query phase flag
- `srvObjCategory` - Service object category
- `srvMethod` - Service method
- `Purge_Tool` - Purge tool identifier

### Metadata Fields
- `system` - Should be "legendary"
- `type` - Should be "ap_log"
- `filename` - Extracted filename

## Testing Scenarios

### 1. Normal Processing
Tests standard log parsing and field extraction.

**Expected behavior:**
- All fields extracted correctly
- Multiline events aggregated properly
- Metadata fields set correctly

### 2. Query Phase Logic
Tests conditional field removal.

**Expected behavior:**
- When `IsQueryPhase:"Y"` → remove maskLotId, maskGroupId, product, layer
- When `rqstType` contains "PHASE" → remove same fields
- Other fields preserved

### 3. Field Derivation
Tests maskGroupId derivation from product and layer.

**Expected behavior:**
- If maskGroupId is null AND product/layer exist
- Set maskGroupId = product + "-" + layer

### 4. Error Handling
Tests graceful degradation with malformed data.

**Expected behavior:**
- Pipeline continues processing
- Malformed events skipped or partially parsed
- No pipeline failures

### 5. Type Conversion
Tests data type handling.

**Expected behavior:**
- `MaskListNo` converted to integer
- Other fields remain strings

## Comparison Criteria

### Perfect Match (100%)
- All documents match exactly
- All fields match exactly
- Exit code: 0

### Partial Pass (≥90%)
- Most documents match
- Minor differences acceptable
- Exit code: 1
- Requires review

### Fail (<90%)
- Significant differences
- Migration incomplete or incorrect
- Exit code: 2

## Troubleshooting

### Logstash baseline fails to generate
```bash
# Check Docker status
docker-compose ps

# View Logstash logs
docker-compose logs logstash

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health
```

### Vector test fails
```bash
# Validate configuration
vector validate --config ../../impl/vector.yaml

# Check Vector version
vector --version

# Run with verbose logging
vector --config vector-test.yaml --verbose
```

### Comparison shows mismatches
1. Check if differences are in metadata fields vs business fields
2. Review specific mismatches in comparison output
3. Verify test data is identical between runs
4. Check for timing-dependent fields (timestamps)

## CI/CD Integration

To integrate into CI/CD pipeline:

```yaml
# Example GitHub Actions
steps:
  - name: Run Vector unit tests
    run: vector test impl/vector.yaml
  
  - name: Run integration tests
    run: cd tests/integration && ./run_all_tests.sh
  
  - name: Upload test results
    uses: actions/upload-artifact@v3
    with:
      name: test-results
      path: tests/integration/data/baseline/
```

## Next Steps

After integration tests pass:
1. Performance testing (T611-T614)
2. Elasticsearch document structure validation (T608)
3. Production deployment preparation
4. Monitoring and alerting setup

## References

- [Vector Testing Documentation](https://vector.dev/docs/reference/tests/)
- [Logstash Configuration](../../sample/logstash.conf)
- [Vector Configuration](../../impl/vector.yaml)
- [Migration Requirements](../../doc/requirements.md)
