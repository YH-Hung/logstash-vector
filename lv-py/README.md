# lv-py: Logstash to Vector Configuration Migration Tool

Python implementation of the Logstash to Vector configuration migration tool.

## Overview

`lv-py` is a CLI tool that migrates Logstash configuration files (`.conf`) to Vector TOML format (`.toml`). It supports common Logstash plugins and provides detailed migration reports for unsupported features.

## Features

- Migrate Logstash configs to Vector TOML format
- Support for common plugins:
  - **Inputs**: file, beats
  - **Filters**: grok, mutate, date
  - **Outputs**: elasticsearch, file
- Dry-run mode for previewing migrations
- Validation of generated Vector configs
- Detailed migration reports with manual migration guidance
- Integration tests with real Logstash and Vector instances

## Requirements

- Python 3.11+
- uv package manager

## Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd logstash-vector/lv-py

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Quick Start

```bash
# Migrate Logstash configs in a directory
lv-py migrate /path/to/logstash/configs

# Dry-run to preview migration
lv-py migrate --dry-run /path/to/logstash/configs

# Validate generated Vector configs
lv-py validate /path/to/vector/configs/*.toml

# Compare Logstash and Vector configs
lv-py diff pipeline.conf pipeline.toml
```

## Development

See [quickstart.md](../specs/001-logstash-vector-migration/quickstart.md) for detailed development instructions.

### Running Tests

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Run integration tests (requires Docker)
uv run pytest tests/integration/ -v

# Run all tests with coverage
uv run pytest --cov=lv_py --cov-report=html
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run mypy src/lv_py
```

## Architecture

- `src/lv_py/parser/`: Logstash DSL parser (pyparsing)
- `src/lv_py/transformers/`: Logstash→Vector transformation logic
- `src/lv_py/generator/`: Vector TOML generation (tomlkit)
- `src/lv_py/models/`: Pydantic data models
- `src/lv_py/utils/`: Utilities (file operations, validation)
- `src/lv_py/cli.py`: Click CLI interface

## Contributing

See project constitution at `../.specify/memory/constitution.md` for development principles and guidelines.

## License

MIT
