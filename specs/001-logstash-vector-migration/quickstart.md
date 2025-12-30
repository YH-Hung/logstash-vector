# Quickstart Guide: lv-py Development

**Project**: Logstash to Vector Configuration Migration Tool (Python Implementation)
**Target Audience**: Developers implementing the tool

## Prerequisites

- **Python**: 3.11 or higher
- **uv**: Modern Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Docker & Docker Compose**: For integration tests
- **Git**: For version control
- **Optional**: Vector CLI (for validation testing)

## Project Setup

### 1. Clone and Initialize

```bash
# Navigate to repository root
cd /path/to/logstash-vector

# Create lv-py directory structure
mkdir -p lv-py/src/lv_py/{parser,transformers,generator,models,utils}
mkdir -p lv-py/tests/{unit,integration/{logstash,vector,data},fixtures}

# Navigate to Python project
cd lv-py
```

### 2. Initialize uv Project

```bash
# Initialize project with uv
uv init

# Install dependencies
uv add pyparsing tomlkit click rich pydantic

# Install dev/test dependencies
uv add --dev pytest pytest-docker-compose testcontainers pytest-cov ruff mypy
```

This creates `pyproject.toml` with configuration:

```toml
[project]
name = "lv-py"
version = "0.1.0"
description = "Logstash to Vector configuration migration tool"
requires-python = ">=3.11"
dependencies = [
    "pyparsing>=3.1.0",
    "tomlkit>=0.12.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "pydantic>=2.5.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-docker-compose>=3.2.0",
    "testcontainers>=3.7.0",
    "pytest-cov>=4.1.0",
]
dev = [
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
lv-py = "lv_py.cli:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

### 3. Create Initial File Structure

```bash
# Create __init__.py files
touch src/lv_py/__init__.py
touch src/lv_py/{parser,transformers,generator,models,utils}/__init__.py
touch tests/__init__.py
touch tests/{unit,integration,fixtures}/__init__.py

# Create initial module files
touch src/lv_py/cli.py
touch src/lv_py/parser/logstash_parser.py
touch src/lv_py/parser/ast_models.py
touch src/lv_py/transformers/{base,inputs,filters,outputs}.py
touch src/lv_py/generator/toml_generator.py
touch src/lv_py/models/{logstash_config,vector_config,migration_report}.py
touch src/lv_py/utils/{file_utils,validation}.py
```

### 4. Verify Installation

```bash
# Run Python REPL to verify imports
uv run python
>>> import pyparsing
>>> import tomlkit
>>> import click
>>> import pydantic
>>> exit()

# Verify CLI entry point (will show help)
uv run lv-py --help
```

## Development Workflow

### Running Tests

```bash
# Run unit tests (fast, no Docker)
uv run pytest tests/unit/ -v

# Run integration tests (requires Docker)
uv run pytest tests/integration/ -v

# Run all tests with coverage
uv run pytest --cov=lv_py --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_parser.py -v

# Run tests matching pattern
uv run pytest -k "test_file_input" -v
```

### Code Quality

```bash
# Format code with ruff
uv run ruff format .

# Lint code
uv run ruff check .

# Type check with mypy
uv run mypy src/lv_py

# Run all quality checks
uv run ruff check . && uv run mypy src/lv_py
```

### Running the CLI Locally

```bash
# Run CLI with uv
uv run lv-py migrate /path/to/logstash/configs

# Dry run mode
uv run lv-py migrate --dry-run /path/to/logstash/configs

# With verbose output
uv run lv-py migrate --verbose /path/to/logstash/configs
```

## Test-First Development (TDD) Workflow

Following Constitution Principle V, implement features test-first:

### Example: Adding Support for `file` Input Plugin

**Step 1: Create Integration Test**

```bash
# Create Logstash sample config
cat > tests/integration/logstash/file-input.conf << 'EOF'
input {
  file {
    path => "/var/log/app.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
  }
}

output {
  stdout { codec => rubydebug }
}
EOF

# Create expected Vector config
cat > tests/integration/vector/file-input.toml << 'EOF'
[sources.file_input]
type = "file"
include = ["/var/log/app.log"]
read_from = "beginning"

[sinks.stdout_output]
type = "console"
inputs = ["file_input"]
encoding.codec = "json"
EOF
```

**Step 2: Write Failing Test**

```python
# tests/integration/test_functional_equivalence.py
import pytest
from pathlib import Path
from lv_py.cli import migrate

def test_file_input_migration():
    """Test migration of Logstash file input to Vector file source."""
    logstash_conf = Path("tests/integration/logstash/file-input.conf")
    expected_toml = Path("tests/integration/vector/file-input.toml")

    # Run migration
    result = migrate(logstash_conf.parent, dry_run=False)

    # Verify Vector config generated
    output_toml = logstash_conf.with_suffix('.toml')
    assert output_toml.exists()

    # Verify content matches expected
    generated = output_toml.read_text()
    expected = expected_toml.read_text()
    assert_configs_equivalent(generated, expected)

    # Verify functional equivalence with Docker
    assert_vector_behaves_like_logstash(
        logstash_conf=logstash_conf,
        vector_conf=output_toml,
        test_logs=Path("tests/integration/data/sample-logs.json")
    )
```

**Step 3: Run Test (Red)**

```bash
uv run pytest tests/integration/test_functional_equivalence.py::test_file_input_migration -v
# FAILED - NotImplementedError: file input transformation not implemented
```

**Step 4: Implement Transformation (Green)**

```python
# src/lv_py/transformers/inputs.py
from lv_py.models.logstash_config import LogstashPlugin
from lv_py.models.vector_config import VectorComponent, ComponentType

class FileInputTransformer:
    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """Transform Logstash file input to Vector file source."""
        assert plugin.plugin_name == "file"

        return VectorComponent(
            component_type=ComponentType.SOURCE,
            component_kind="file",
            config={
                "include": [plugin.config["path"]],
                "read_from": "beginning" if plugin.config.get("start_position") == "beginning" else "end",
            },
            inputs=[],
            comments=[]
        )
```

**Step 5: Run Test (Green)**

```bash
uv run pytest tests/integration/test_functional_equivalence.py::test_file_input_migration -v
# PASSED ✓
```

**Step 6: Refactor (if needed)**

Clean up code, add error handling, optimize performance.

**Step 7: Repeat for Next Plugin**

Continue with beats input, grok filter, etc.

## Docker Compose Integration Testing

### Setup Docker Compose

```yaml
# tests/integration/docker-compose.yml
version: '3.8'

services:
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash:/etc/logstash/conf.d:ro
      - ./data:/data:ro
    command: logstash -f /etc/logstash/conf.d/
    ports:
      - "9600:9600"  # API

  vector:
    image: timberio/vector:0.34.0-alpine
    volumes:
      - ./vector:/etc/vector:ro
      - ./data:/data:ro
    command: --config /etc/vector/*.toml
    ports:
      - "8686:8686"  # Health check API

  log-generator:
    image: mingrammer/flog:0.4.3
    command: -f json -d 0.1s -l
    depends_on:
      - logstash
      - vector
```

### Running Integration Tests

```bash
# Start services
cd tests/integration
docker-compose up -d

# Wait for services to be ready
docker-compose ps

# Run tests
cd ../..
uv run pytest tests/integration/ -v

# View logs
cd tests/integration
docker-compose logs logstash
docker-compose logs vector

# Cleanup
docker-compose down -v
```

## Project Milestones

### Milestone 1: Parser (Week 1)
- [ ] Implement Logstash DSL grammar with pyparsing
- [ ] Parse input/filter/output blocks
- [ ] Handle nested plugin configurations
- [ ] Extract conditionals and variables
- [ ] Unit tests for parser (90%+ coverage)

### Milestone 2: Core Transformations (Week 2)
- [ ] Implement file input → file source
- [ ] Implement beats input → http/socket source
- [ ] Implement grok filter → remap transform
- [ ] Implement mutate filter → remap transform
- [ ] Implement date filter → remap transform
- [ ] Integration tests for each transformation

### Milestone 3: Outputs & Reports (Week 3)
- [ ] Implement elasticsearch output → elasticsearch sink
- [ ] Implement file output → file sink
- [ ] Generate migration reports (markdown)
- [ ] Handle unsupported plugins with TODO markers
- [ ] Validation with `vector validate`

### Milestone 4: CLI & UX (Week 4)
- [ ] Click CLI with all options
- [ ] Rich formatting for terminal output
- [ ] Dry-run mode
- [ ] Progress indicators
- [ ] Error handling and user-friendly messages

### Milestone 5: Integration Testing (Week 5)
- [ ] Docker Compose test infrastructure
- [ ] Functional equivalence tests for all supported plugins
- [ ] Complex pipeline tests
- [ ] Edge case tests (large files, unicode, errors)
- [ ] Performance testing (50 files, 1000+ lines)

## Common Development Tasks

### Adding a New Plugin Transformer

1. **Research**: Document Logstash plugin behavior and Vector equivalent (see research.md)
2. **Test**: Create integration test with sample configs
3. **Implement**: Add transformer class in `transformers/{inputs|filters|outputs}.py`
4. **Register**: Add to plugin registry in `transformers/__init__.py`
5. **Validate**: Run integration tests with Docker Compose
6. **Document**: Update plugin mapping table in research.md

### Debugging Failed Transformations

```bash
# Run with verbose logging
uv run lv-py migrate --verbose /path/to/configs

# Enable debug logging
LV_PY_LOG_LEVEL=DEBUG uv run lv-py migrate /path/to/configs

# Run specific test with pdb
uv run pytest tests/integration/test_grok_filter.py -v --pdb

# Inspect generated config
cat /path/to/output.toml

# Validate with Vector
vector validate /path/to/output.toml
```

### Performance Profiling

```bash
# Profile parser performance
uv run python -m cProfile -o profile.stats -m lv_py.cli migrate /path/to/configs

# View profile results
uv run python -m pstats profile.stats
>>> sort cumtime
>>> stats 20

# Memory profiling with memory_profiler
uv add --dev memory-profiler
uv run python -m memory_profiler src/lv_py/cli.py migrate /path/to/configs
```

## Troubleshooting

### uv Issues

```bash
# Reinstall dependencies
uv sync

# Clear cache
uv cache clean

# Update uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Docker Issues

```bash
# Rebuild containers
docker-compose build --no-cache

# Remove orphaned containers
docker-compose down --remove-orphans

# View real-time logs
docker-compose logs -f logstash vector
```

### Import Errors

```bash
# Ensure package is installed in editable mode
uv add -e .

# Verify PYTHONPATH
uv run python -c "import sys; print(sys.path)"
```

## Resources

- **pyparsing docs**: https://pyparsing-docs.readthedocs.io/
- **tomlkit docs**: https://tomlkit.readthedocs.io/
- **Click docs**: https://click.palletsprojects.com/
- **Pydantic docs**: https://docs.pydantic.dev/
- **Logstash docs**: https://www.elastic.co/guide/en/logstash/current/
- **Vector docs**: https://vector.dev/docs/
- **Project constitution**: `../.specify/memory/constitution.md`
- **Implementation plan**: `../specs/001-logstash-vector-migration/plan.md`

## Next Steps

After completing quickstart:
1. Review `data-model.md` for entity definitions
2. Read `research.md` for technology decisions
3. Check `contracts/cli-interface.md` for CLI specification
4. Start with Milestone 1 (Parser implementation)
5. Follow test-first workflow for all features
