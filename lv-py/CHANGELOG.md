# Changelog

All notable changes to lv-py will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-31

### Added

#### Core Migration Features
- Logstash DSL parser using pyparsing for parsing `.conf` files
- Support for common Logstash plugins:
  - **Inputs**: file, beats
  - **Filters**: grok, mutate, date
  - **Outputs**: elasticsearch, file
- Vector TOML generation with comment preservation (tomlkit)
- Automatic transformation of Logstash configurations to Vector format
- Directory-based migration (process all `.conf` files in a directory)

#### CLI Commands
- `lv-py migrate` - Migrate Logstash configs to Vector format
  - `--dry-run/-n` - Preview migration without writing files
  - `--output-dir/-o` - Custom output directory
  - `--overwrite/-f` - Overwrite existing files without confirmation
  - `--verbose/-v` - Detailed output for debugging
  - `--quiet/-q` - Minimal output mode
  - `--no-validate` - Skip Vector validation for faster migration
  - `--report/-r` - Custom migration report path
- `lv-py validate` - Validate Vector TOML configurations
- `lv-py diff` - Compare Logstash and Vector configurations side-by-side
- `lv-py --version` - Display version information

#### Validation & Reporting
- Integration with `vector validate` for syntax checking
- Detailed migration reports in Markdown format
- TODO markers for unsupported features with manual migration guidance
- Line number tracking for errors and unsupported plugins
- Success rate calculation and reporting

#### Error Handling
- Graceful handling of malformed Logstash configs
- Permission denied error handling
- Directory not found error handling
- Clear error messages with file:line references
- Color-coded output (errors=red, warnings=yellow, success=green)

#### Testing
- Unit tests for all transformers (80.54% code coverage)
- Integration tests with real Logstash samples
- Test-first development (TDD) workflow
- Docker Compose integration test infrastructure

#### Documentation
- Complete README with usage examples
- Quickstart guide for developers
- Implementation plan with architecture decisions
- CLI help text for all commands
- Environment variable support documentation

### Environment Variables
- `LV_PY_LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)
- `VECTOR_BIN` - Custom path to Vector binary for validation

### Technical Details
- Python 3.11+ type hints throughout
- Pydantic models for data validation
- Rich terminal output formatting
- Click CLI framework
- uv package manager support

### Known Limitations
- Conditional statements (`if/else`) in Logstash configs are flagged for manual review
- Environment variables in configs are detected and flagged
- Multi-pipeline configs require manual handling
- Some advanced Logstash plugins not yet supported (see migration reports)

## [Unreleased]

### Planned Features
- Additional plugin support (kafka, http input, etc.)
- Parallel file processing for improved performance
- Migration examples directory
- CONTRIBUTING.md with development guidelines
- User migration guide

[0.1.0]: https://github.com/yourusername/logstash-vector/releases/tag/v0.1.0
