# Logstash to Vector Migration - TDD Implementation

This project implements a complete migration from Logstash to Vector configuration using Test-Driven Development (TDD). The implementation creates Vector configuration files that replicate Logstash pipeline functionality with comprehensive test coverage.

## Project Structure

```
/
├── vector/
│   └── vector.toml              # Main Vector configuration
├── tests/
│   ├── conftest.py              # pytest fixtures (Vector runner, sample data)
│   ├── test_file_source.py      # File source configuration tests
│   ├── test_multiline.py        # Multiline processing tests
│   ├── test_path_parsing.py     # Filename extraction tests
│   ├── test_field_extraction.py # Grok pattern extraction tests
│   ├── test_processing_logic.py # Tag management, field combination, removal
│   ├── test_elasticsearch.py    # Output configuration tests
│   ├── test_integration.py      # End-to-end pipeline tests
│   └── fixtures/
│       └── sample_logs/         # Test log files
├── scripts/
│   └── run_tests.sh             # Single command test runner
├── pyproject.toml               # Python dependencies (uv)
├── Makefile                     # Test runner (alternative to script)
└── sample/                      # Original sample files
    ├── logstash.conf            # Original Logstash config
    └── web_hmib_1.log           # Sample log file
```

## Prerequisites

- **Vector**: System installation required (https://vector.dev/docs/setup/installation/)
- **uv**: Python package manager (https://github.com/astral-sh/uv)
- **Python**: 3.8+ (managed via uv)

## Quick Start

### 1. Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync
```

### 2. Run Tests

Run all tests with a single command:

```bash
# Option 1: Using the test runner script
./scripts/run_tests.sh

# Option 2: Using make
make test

# Option 3: Using uv directly
uv run pytest
```

All 44 tests should pass.

### 3. Validate Vector Configuration

```bash
vector validate --config-toml vector/vector.toml --no-environment
```

## Features Implemented

### File Source Configuration
- Glob pattern matching `/app/log/web_*.log`
- Read from end of file (`read_from: "end"`)
- System field addition (`system: "legendary"`)

### Multiline Processing
- Start pattern detection for TRACE logs
- Continue-through mode for log aggregation
- Timeout handling (5000ms)

### Field Extraction (12 fields)
All fields extracted using grok patterns with fallback logic:
- **Primary**: product, layer
- **Complex**: maskGroupId (5 patterns), Action (2 patterns), maskLotId (4 patterns)
- **Simple**: MaskListNo, rqstType, IsQueryPhase, srvObjCategory, srvMethod, Purge_Tool
- **Path**: filename

### Processing Logic
- Tag management (MGtag, Ptag, Ltag for null detection)
- Field combination (maskGroupId from product + layer)
- Type conversion (MaskListNo to integer)
- Conditional field removal (based on IsQueryPhase and rqstType)

### Elasticsearch Output
- Endpoint configuration
- Index pattern with POD_NAMESPACE template
- Basic authentication
- TLS verification

## Test Coverage

- **File Source**: 4 tests
- **Multiline**: 5 tests
- **Path Parsing**: 3 tests
- **Field Extraction**: 12 tests
- **Processing Logic**: 7 tests
- **Elasticsearch**: 6 tests
- **Integration**: 7 tests

**Total: 44 tests, all passing**

## Development

### Running Specific Tests

```bash
# Run a specific test file
uv run pytest tests/test_field_extraction.py -v

# Run a specific test
uv run pytest tests/test_field_extraction.py::test_product_field_extraction -v

# Run with verbose output
uv run pytest -vv
```

### Vector Configuration

The main Vector configuration is in `vector/vector.toml`. It includes:

1. **File Source**: Reads from `/app/log/web_*.log` with multiline support
2. **Transforms**:
   - `add_system_field`: Adds system="legendary"
   - `parse_filename`: Extracts filename from path
   - `field_parser`: Extracts all 12 target fields
   - `processing_logic`: Tag management, field combination, type conversion, conditional removal
3. **Sink**: Elasticsearch output with proper configuration

## Functional Equivalence

The Vector configuration maintains 100% functional equivalence with the original Logstash configuration:

- All grok patterns translated to VRL
- Ruby logic converted to VRL
- Multiline processing behavior replicated
- Field extraction and transformation identical
- Elasticsearch output format preserved

## Notes

- Tests use Vector's `validate` command with `--no-environment` flag to skip environment checks
- Test configs use console sinks for validation
- Production config uses Elasticsearch sink
- All grok patterns use case-insensitive matching (`(?i)`)
- VRL expressions handle optional fields gracefully

## Documentation

- `doc/requirements.md`: Complete requirements specification
- `doc/todo.md`: Implementation task breakdown
- `sample/logstash.conf`: Original Logstash configuration
- `sample/web_hmib_1.log`: Sample log file for testing
