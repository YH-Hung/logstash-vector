# Integration Test Data

This directory contains shared test data for integration testing both lv-py and lv-go implementations.

## Structure

```
test-data/
├── logstash/          # Sample Logstash configurations for testing
│   ├── file-input.conf
│   ├── grok-filter.conf
│   ├── mutate-filter.conf
│   ├── date-filter.conf
│   └── complex-pipeline.conf
├── logs/              # Sample log files for testing
│   └── sample-apache.log
└── output/            # Output directories for test runs
    ├── logstash/      # Logstash output
    └── vector/        # Vector output
```

## Test Configurations

### file-input.conf
Tests basic file input → file output migration.

### grok-filter.conf
Tests grok filter → remap transform with parse_groks!().

### mutate-filter.conf
Tests mutate filter → remap transform with field operations.

### date-filter.conf
Tests date filter → remap transform with parse_timestamp!().

### complex-pipeline.conf
Tests complete pipeline with multiple inputs, filters, and outputs including conditionals.

## Running Integration Tests

### Python (lv-py)
```bash
cd lv-py
uv run pytest tests/integration -v
```

### Go (lv-go)
```bash
cd lv-go
go test ./tests/integration/... -v
```

### With Docker Compose
```bash
# From project root
docker-compose -f docker-compose.test.yml up --build

# Run Python tests
docker-compose -f docker-compose.test.yml run test-runner-py

# Run Go tests
docker-compose -f docker-compose.test.yml run test-runner-go
```

## Adding New Test Cases

1. Create new Logstash config in `logstash/`
2. Create corresponding expected Vector config in `vector/` (optional)
3. Add test case in implementation's integration test suite
4. Run tests to verify

## Constitutional Compliance

This integration testing infrastructure fulfills **Constitutional Principle III** (NON-NEGOTIABLE):
> Integration Testing with Real Dependencies

All tests use real Logstash and Vector instances via Docker Compose to verify functional equivalence.
