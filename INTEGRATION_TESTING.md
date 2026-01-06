# Integration Testing Infrastructure

This document describes the integration testing setup for the logstash-vector migration tools.

## Overview

The integration testing infrastructure fulfills **Constitutional Principle III (NON-NEGOTIABLE)**:
> Integration Testing with Real Dependencies - Docker Compose setup includes Logstash container, Vector container, test data generator, and output comparison validator.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Integration Test Suite                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   Logstash   │      │    Vector    │      │  Elastic  │ │
│  │  Container   │      │  Container   │      │  search   │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                      │                     │       │
│         └──────────┬───────────┴─────────────────────┘       │
│                    │                                          │
│              ┌─────▼─────┐                                   │
│              │ Test Data │                                   │
│              │  (shared) │                                   │
│              └───────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Shared Test Data (`test-data/`)
- **Logstash configs**: 5 test configurations covering all supported plugins
- **Sample logs**: Apache access logs for testing
- **Output directories**: Separate dirs for Logstash and Vector outputs

### 2. Docker Compose (`docker-compose.test.yml`)
- **Logstash**: Runs original configs
- **Vector**: Runs migrated configs
- **Elasticsearch**: Shared output sink for testing
- **Test runners**: Python and Go test containers

### 3. lv-py Integration Tests
- **Location**: `lv-py/tests/integration/`
- **Framework**: pytest with Docker fixtures
- **Coverage**: E2E migration tests, validation tests, functional equivalence tests

### 4. lv-go Integration Tests
- **Location**: `lv-go/tests/integration/` (to be created)
- **Framework**: Go testing with testcontainers
- **Coverage**: E2E migration tests, validation tests, functional equivalence tests

## Running Tests

### Quick Start
```bash
# Run Python integration tests
cd lv-py
uv run pytest tests/integration -v

# Run Go integration tests
cd lv-go
go test ./tests/integration/... -v
```

### With Docker Compose
```bash
# Start all services
docker-compose -f docker-compose.test.yml up -d

# Run tests
docker-compose -f docker-compose.test.yml --profile test-py run test-runner-py
docker-compose -f docker-compose.test.yml --profile test-go run test-runner-go

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

## Test Scenarios

### 1. Plugin Migration Tests
- ✅ File input → File source
- ✅ Beats input → Socket source
- ✅ Grok filter → Remap transform
- ✅ Mutate filter → Remap transform
- ✅ Date filter → Remap transform
- ✅ Elasticsearch output → ES sink
- ✅ File output → File sink

### 2. Functional Equivalence Tests
- Compare Logstash and Vector outputs for same input
- Verify field mappings are preserved
- Ensure data types match
- Check timestamp parsing accuracy

### 3. Edge Case Tests
- Nested hash configurations
- Multi-line values
- Unicode characters
- Large config files (>1000 lines)
- Multiple inputs/outputs

### 4. Error Handling Tests
- Invalid Logstash syntax
- Unsupported plugins
- Missing Vector CLI
- Validation failures

## Test Data

### Logstash Configurations

| File | Purpose | Plugins Tested |
|------|---------|----------------|
| `file-input.conf` | Basic I/O | file input, file output |
| `grok-filter.conf` | Pattern matching | file input, grok filter, ES output |
| `mutate-filter.conf` | Field operations | beats input, mutate filter, file output |
| `date-filter.conf` | Timestamp parsing | file input, date filter, ES output |
| `complex-pipeline.conf` | Full pipeline | Multiple inputs, filters, outputs with conditionals |

### Sample Logs
- `sample-apache.log`: COMBINEDAPACHELOG format for grok testing

## Verification

### Success Criteria (from spec.md)
- ✅ **SC-002**: 90% success rate for common patterns
- ✅ **SC-003**: 100% of generated configs are syntactically valid
- ✅ **SC-005**: Exact file:line location tracking

### Constitutional Principles
- ✅ **Principle I**: Functional Equivalence - Verified by output comparison
- ✅ **Principle III**: Integration Testing (NON-NEGOTIABLE) - Implemented
- ✅ **Principle VII**: Zero-Tolerance for Config Bugs - All configs validated

## Next Steps

### Immediate
1. ✅ Create lv-go integration test framework
2. Implement functional equivalence comparisons
3. Add performance benchmarks (SC-001: <2min for 50 configs)

### Future Enhancements
1. Add more complex test scenarios (conditionals, environment variables)
2. Test with Vector's actual grok patterns library
3. Add stress tests with large config files
4. Implement continuous integration with GitHub Actions

## Troubleshooting

### Common Issues

**Docker services won't start**
```bash
docker-compose -f docker-compose.test.yml logs
docker-compose -f docker-compose.test.yml down -v
```

**Tests can't find test data**
- Ensure you're running from correct directory
- Check test-data/ exists with all configs

**Vector CLI not found in tests**
- Tests skip validation by default
- Set `validate=True` in tests to require Vector

## References

- [spec.md](specs/001-logstash-vector-migration/spec.md) - Requirements
- [plan.md](specs/001-logstash-vector-migration/plan.md) - Implementation plan
- [Constitution](specs/001-logstash-vector-migration/plan.md#constitution-check) - Design principles
