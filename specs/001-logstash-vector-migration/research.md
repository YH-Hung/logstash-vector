# Phase 0: Research & Technology Decisions

**Feature**: Logstash to Vector Configuration Migration Tool
**Date**: 2025-12-31

## Research Tasks

### 1. Logstash Configuration Parser Library

**Unknown**: Which Python library should be used to parse Logstash DSL configuration files?

**Options Evaluated**:

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **pyparsing** | Mature, flexible, good documentation, widely used for DSL parsing | More verbose than alternatives, steeper learning curve | ⭐ SELECTED |
| **lark** | Modern, clean syntax (EBNF), fast, good error messages | Less community examples for Logstash specifically | Alternative |
| **ply (Python Lex-Yacc)** | Battle-tested, similar to classic lex/yacc | Older style, more boilerplate required | Rejected |
| **Custom regex-based parser** | Full control, no dependencies | Error-prone, hard to maintain, doesn't handle nested structures well | Rejected |
| **Existing Logstash parser** | May already handle edge cases | No mature Python library found (most are Ruby/Java) | Not available |

**Decision**: **pyparsing**

**Rationale**:
- Well-suited for parsing Logstash's Ruby-like DSL syntax
- Strong support for nested structures (input/filter/output blocks)
- Excellent error reporting capabilities (needed for FR-013)
- Active community and extensive documentation
- Successfully used for similar configuration parsing tasks
- Can handle Logstash conditionals, variable references, and multi-line strings

**Implementation Approach**:
```python
# Define grammar for Logstash DSL
input_block = Keyword("input") + nestedExpr('{', '}')
filter_block = Keyword("filter") + nestedExpr('{', '}')
output_block = Keyword("output") + nestedExpr('{', '}')
plugin = Word(alphas) + nestedExpr('{', '}')
# ... full grammar definition
```

**Alternatives Considered**:
- **lark**: Would be faster and cleaner but lacks Logstash-specific examples. If pyparsing proves too verbose during implementation, lark is a viable fallback.
- **Custom parser**: Rejected due to complexity of handling Logstash's conditional statements, environment variables, and nested plugin configurations.

---

### 2. TOML Generation with Comment Preservation

**Task**: Determine best approach for generating Vector TOML configs with TODO comments for unsupported features (FR-009)

**Decision**: **tomlkit**

**Rationale**:
- Preserves comments and formatting (critical for FR-009 TODO markers)
- Pythonic API for programmatic TOML generation
- Maintains human-readable output (important for manual review)
- Official TOML specification compliance
- Better than stdlib `tomllib` (read-only) or `toml` (doesn't preserve comments)

**Usage Example**:
```python
from tomlkit import document, comment, table

doc = document()
doc.add(comment("TODO: Manual migration required for unsupported plugin"))
sources = table()
# ... build sources
doc["sources"] = sources
```

**Alternatives Considered**:
- `toml` library: Doesn't preserve comments, would lose TODO markers on round-trip
- `tomllib` (Python 3.11+): Read-only, can't generate TOML files
- Manual string formatting: Error-prone, doesn't validate TOML syntax

---

### 3. Docker Compose Integration Testing Strategy

**Task**: Determine how to run Docker Compose from pytest for integration tests (Constitution Principle III)

**Decision**: **pytest-docker-compose** + **testcontainers-python**

**Rationale**:
- `pytest-docker-compose`: Manages docker-compose.yml lifecycle in pytest fixtures
- `testcontainers-python`: Provides Python API for container interaction and log inspection
- Combined approach gives both declarative container setup and programmatic control
- Supports parallel test execution with isolated Docker networks

**Implementation Pattern**:
```python
# conftest.py
import pytest
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def docker_services():
    with DockerCompose("tests/integration") as compose:
        compose.wait_for("vector:8686")  # Vector health check
        compose.wait_for("logstash:9600")  # Logstash API
        yield compose

# test_functional_equivalence.py
def test_file_input_equivalence(docker_services):
    # Generate Vector config from Logstash config
    # Feed same logs to both containers
    # Compare outputs
    assert logstash_output == vector_output
```

**Alternatives Considered**:
- Manual `subprocess.run(["docker-compose", ...])`: Less Pythonic, harder error handling
- Pure Docker SDK: More control but too low-level, verbose
- Mocking: Violates Constitution Principle III (must use real dependencies)

---

### 4. CLI Framework Best Practices

**Task**: Research Python CLI best practices with uv package manager

**Decision**: **Click** + **Rich** for output formatting

**Rationale**:
- **Click**: Industry standard for Python CLIs, excellent documentation, decorators for commands
- **Rich**: Beautiful terminal output for migration reports (FR-010), progress indicators (edge case handling)
- Both work seamlessly with uv-managed projects
- Type-safe with Python 3.11+ type hints

**CLI Structure**:
```python
import click
from rich.console import Console
from rich.table import Table

@click.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Preview migration without writing files')
def migrate(directory: str, dry_run: bool):
    """Migrate Logstash configs to Vector TOML format."""
    console = Console()
    # ... migration logic
    console.print(migration_report)
```

**Alternatives Considered**:
- `argparse`: Stdlib but more verbose, lacks Click's elegance
- `typer`: Modern alternative but less mature ecosystem
- Plain `sys.argv` parsing: Too manual, reinventing the wheel

---

### 5. Logstash-to-Vector Plugin Mapping Research

**Task**: Document known mappings between Logstash plugins and Vector components

**Findings**:

| Logstash Plugin | Vector Component | Mapping Complexity | Notes |
|-----------------|------------------|-------------------|-------|
| **input { file }** | `sources.file` | Low | Direct 1:1 mapping, similar config options |
| **input { beats }** | `sources.http` or `sources.socket` | Medium | Beats → Vector HTTP/TCP, requires port/protocol translation |
| **filter { grok }** | `transforms.remap` with `parse_groks()` | Medium | VRL function available, pattern syntax compatible |
| **filter { mutate }** | `transforms.remap` | Low | Direct field manipulation in VRL |
| **filter { date }** | `transforms.remap` with `parse_timestamp()` | Low | VRL function handles format strings |
| **output { elasticsearch }** | `sinks.elasticsearch` | Low | Nearly identical configuration options |
| **output { file }** | `sinks.file` | Low | Direct mapping with encoding options |

**Key Insights**:
1. Most transformations map to Vector's `remap` transform using VRL (Vector Remap Language)
2. Grok patterns are compatible between Logstash and Vector (both use Oniguruma regex)
3. Beats input requires protocol decision (HTTP vs TCP) based on Beats client configuration
4. Conditionals in Logstash (`if` statements) map to VRL conditional logic in remap transforms

**Research Sources**:
- Vector documentation: https://vector.dev/docs/
- Logstash plugin docs: https://www.elastic.co/guide/en/logstash/current/
- Community migration examples and comparisons

---

### 6. Vector Configuration Validation

**Task**: Determine how to validate generated Vector configs (FR-015, SC-003)

**Decision**: Use `vector validate` CLI command + Python subprocess wrapper

**Implementation**:
```python
import subprocess
from pathlib import Path

def validate_vector_config(config_path: Path) -> tuple[bool, str]:
    """Validate Vector TOML config using Vector CLI."""
    result = subprocess.run(
        ["vector", "validate", str(config_path)],
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stderr

# Integration test
def test_generated_config_valid():
    config_path = generate_vector_config(sample_logstash_conf)
    valid, errors = validate_vector_config(config_path)
    assert valid, f"Generated config invalid: {errors}"
```

**Rationale**:
- Uses Vector's own validation (authoritative)
- Catches syntax errors, invalid plugin configs, missing required fields
- Same validation users will run before deploying configs
- Can be run in CI without starting full Vector instance (faster than integration tests)

**Alternatives Considered**:
- TOML schema validation: Wouldn't catch Vector-specific semantic errors
- Starting Vector and checking logs: Slower, harder to isolate validation vs runtime errors
- Custom Python validation: Would diverge from Vector's actual requirements over time

---

## Summary of Technology Stack

**Finalized Dependencies** (resolves Technical Context NEEDS CLARIFICATION):

```toml
# pyproject.toml
[project]
name = "lv-py"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pyparsing>=3.1.0",      # Logstash DSL parser
    "tomlkit>=0.12.0",       # TOML generation with comments
    "click>=8.1.0",          # CLI framework
    "rich>=13.0.0",          # Terminal output formatting
    "pydantic>=2.5.0",       # Data validation and models
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-docker-compose>=3.2.0",
    "testcontainers>=3.7.0",
    "pytest-cov>=4.1.0",     # Coverage reporting
]
dev = [
    "ruff>=0.1.0",           # Linting and formatting
    "mypy>=1.7.0",           # Type checking
]
```

**No remaining NEEDS CLARIFICATION items** - all technical decisions documented with rationale.
