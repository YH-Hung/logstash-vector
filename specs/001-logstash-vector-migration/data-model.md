# Phase 1: Data Model

**Feature**: Logstash to Vector Configuration Migration Tool
**Date**: 2025-12-31

## Overview

This document defines the core domain entities and their relationships for the Logstash-to-Vector migration tool. All models use Pydantic for validation and type safety (Python 3.11+ type hints).

---

## Entity Definitions

### 1. LogstashConfiguration

Represents a parsed Logstash configuration file.

**Fields**:
- `file_path: Path` - Source .conf file location
- `inputs: list[LogstashPlugin]` - Input plugin definitions
- `filters: list[LogstashPlugin]` - Filter plugin definitions
- `outputs: list[LogstashPlugin]` - Output plugin definitions
- `raw_content: str` - Original file content for error reporting

**Validation Rules**:
- At least one input plugin MUST be present (FR-002)
- At least one output plugin MUST be present (FR-002)
- Filters are optional (can be empty list)
- File path MUST exist and be readable

**Relationships**:
- Contains 0..N LogstashPlugin instances (as inputs/filters/outputs)
- Maps to 1 VectorConfiguration via transformation

**State Transitions**: Immutable after parsing (read-only model)

**Example**:
```python
from pydantic import BaseModel, Field
from pathlib import Path

class LogstashConfiguration(BaseModel):
    file_path: Path
    inputs: list[LogstashPlugin] = Field(min_length=1)
    filters: list[LogstashPlugin] = Field(default_factory=list)
    outputs: list[LogstashPlugin] = Field(min_length=1)
    raw_content: str

    class Config:
        frozen = True  # Immutable
```

---

### 2. LogstashPlugin

Represents a single Logstash plugin (input, filter, or output) with its configuration.

**Fields**:
- `plugin_type: PluginType` - Enum: INPUT, FILTER, OUTPUT
- `plugin_name: str` - Plugin identifier (e.g., "file", "grok", "elasticsearch")
- `config: dict[str, Any]` - Plugin configuration key-value pairs
- `conditionals: str | None` - Logstash `if` conditional statements (optional)
- `line_number: int` - Location in source file for error reporting (FR-013, SC-005)
- `supported: bool` - Whether this plugin has a Vector mapping (computed field)

**Validation Rules**:
- `plugin_name` MUST be non-empty string
- `config` MUST be valid dict (empty dict allowed for plugins with defaults)
- `line_number` MUST be positive integer
- `supported` is computed based on SUPPORTED_PLUGINS registry

**Relationships**:
- Belongs to 1 LogstashConfiguration (as input/filter/output)
- Maps to 0..N VectorComponent instances (1:N for complex transformations)

**Example**:
```python
from enum import Enum
from typing import Any

class PluginType(str, Enum):
    INPUT = "input"
    FILTER = "filter"
    OUTPUT = "output"

class LogstashPlugin(BaseModel):
    plugin_type: PluginType
    plugin_name: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    conditionals: str | None = None
    line_number: int = Field(gt=0)

    @property
    def supported(self) -> bool:
        return self.plugin_name in SUPPORTED_PLUGINS[self.plugin_type]
```

---

### 3. VectorConfiguration

Represents a generated Vector configuration in TOML format.

**Fields**:
- `file_path: Path` - Output .toml file location
- `sources: dict[str, VectorComponent]` - Vector source definitions (Logstash inputs)
- `transforms: dict[str, VectorComponent]` - Vector transform definitions (Logstash filters)
- `sinks: dict[str, VectorComponent]` - Vector sink definitions (Logstash outputs)
- `global_options: dict[str, Any]` - Vector global configuration options

**Validation Rules**:
- At least one source MUST be present (FR-006)
- At least one sink MUST be present (FR-006)
- Component IDs (dict keys) MUST be unique across sources/transforms/sinks
- Component IDs MUST be valid TOML identifiers (alphanumeric + underscore)
- Generated TOML MUST be syntactically valid (FR-008)

**Relationships**:
- Generated from 1 LogstashConfiguration
- Contains N VectorComponent instances
- Produces 1 MigrationReport during transformation

**State Transitions**:
1. **Draft** - Being constructed from Logstash config
2. **Validated** - Passed `toml_validate()` check
3. **Written** - Persisted to file system

**Example**:
```python
class VectorConfiguration(BaseModel):
    file_path: Path
    sources: dict[str, VectorComponent] = Field(default_factory=dict, min_length=1)
    transforms: dict[str, VectorComponent] = Field(default_factory=dict)
    sinks: dict[str, VectorComponent] = Field(default_factory=dict, min_length=1)
    global_options: dict[str, Any] = Field(default_factory=dict)

    def to_toml(self) -> str:
        """Generate TOML string using tomlkit."""
        # Implementation in generator/toml_generator.py
        ...

    def validate_syntax(self) -> tuple[bool, str]:
        """Validate using `vector validate` command."""
        # Implementation in utils/validation.py
        ...
```

---

### 4. VectorComponent

Represents a single Vector component (source, transform, or sink).

**Fields**:
- `component_type: ComponentType` - Enum: SOURCE, TRANSFORM, SINK
- `component_kind: str` - Vector component type (e.g., "file", "remap", "elasticsearch")
- `config: dict[str, Any]` - Component configuration
- `inputs: list[str]` - Component IDs this component reads from (for transforms/sinks)
- `comments: list[str]` - TODO markers or migration notes (FR-009)

**Validation Rules**:
- `component_kind` MUST be valid Vector component type
- `inputs` MUST reference existing component IDs (graph validation)
- SOURCE components MUST NOT have inputs
- TRANSFORM and SINK components MUST have at least one input

**Relationships**:
- Belongs to 1 VectorConfiguration
- Generated from 1 LogstashPlugin (or multiple for complex mappings)
- References other VectorComponents via `inputs` (forms DAG)

**Example**:
```python
class ComponentType(str, Enum):
    SOURCE = "source"
    TRANSFORM = "transform"
    SINK = "sink"

class VectorComponent(BaseModel):
    component_type: ComponentType
    component_kind: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)

    @validator('inputs')
    def validate_inputs_for_type(cls, v, values):
        comp_type = values.get('component_type')
        if comp_type == ComponentType.SOURCE and len(v) > 0:
            raise ValueError("SOURCE components cannot have inputs")
        if comp_type in (ComponentType.TRANSFORM, ComponentType.SINK) and len(v) == 0:
            raise ValueError(f"{comp_type} components must have at least one input")
        return v
```

---

### 5. MigrationReport

Document generated for each migration listing successes, unsupported features, and errors (FR-010).

**Fields**:
- `source_file: Path` - Original Logstash config path
- `target_file: Path` - Generated Vector config path
- `timestamp: datetime` - When migration ran
- `supported_plugins: list[PluginMigration]` - Successfully migrated plugins
- `unsupported_plugins: list[UnsupportedPlugin]` - Plugins requiring manual work
- `errors: list[MigrationError]` - Parsing or transformation errors
- `warnings: list[str]` - Non-blocking issues (e.g., deprecated features)
- `success_rate: float` - Percentage of plugins successfully migrated (0.0-1.0)

**Validation Rules**:
- `timestamp` defaults to current UTC time
- `success_rate` computed as `len(supported) / (len(supported) + len(unsupported))`
- `success_rate` MUST be between 0.0 and 1.0

**Relationships**:
- Generated from 1 LogstashConfiguration → VectorConfiguration transformation
- Contains N PluginMigration records
- Contains N UnsupportedPlugin records
- Contains N MigrationError records

**State Transitions**: Immutable after creation (report is point-in-time snapshot)

**Example**:
```python
from datetime import datetime

class MigrationReport(BaseModel):
    source_file: Path
    target_file: Path
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    supported_plugins: list[PluginMigration] = Field(default_factory=list)
    unsupported_plugins: list[UnsupportedPlugin] = Field(default_factory=list)
    errors: list[MigrationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = len(self.supported_plugins) + len(self.unsupported_plugins)
        return len(self.supported_plugins) / total if total > 0 else 0.0

    def to_markdown(self) -> str:
        """Generate human-readable markdown report."""
        # Implementation uses rich for formatting
        ...

    class Config:
        frozen = True
```

---

### 6. PluginMigration

Record of a successfully migrated Logstash plugin.

**Fields**:
- `logstash_plugin: str` - Original plugin name
- `vector_components: list[str]` - Generated Vector component IDs
- `notes: str | None` - Migration notes (e.g., "Beats input mapped to HTTP source on port 5044")

**Example**:
```python
class PluginMigration(BaseModel):
    logstash_plugin: str
    vector_components: list[str] = Field(min_length=1)
    notes: str | None = None
```

---

### 7. UnsupportedPlugin

Record of a Logstash plugin that couldn't be automatically migrated (FR-009, SC-004).

**Fields**:
- `plugin_name: str` - Logstash plugin identifier
- `plugin_type: PluginType` - INPUT, FILTER, or OUTPUT
- `line_number: int` - Location in source file (SC-005)
- `original_config: str` - Original Logstash syntax for reference
- `manual_migration_guidance: str` - Suggestions for Vector equivalent (SC-004, SC-007)
- `vector_alternatives: list[str]` - Possible Vector components to research

**Validation Rules**:
- `manual_migration_guidance` MUST be non-empty (SC-004 requirement)
- `line_number` MUST be positive

**Example**:
```python
class UnsupportedPlugin(BaseModel):
    plugin_name: str = Field(min_length=1)
    plugin_type: PluginType
    line_number: int = Field(gt=0)
    original_config: str
    manual_migration_guidance: str = Field(min_length=1)
    vector_alternatives: list[str] = Field(default_factory=list)
```

---

### 8. MigrationError

Error encountered during parsing or transformation (FR-013).

**Fields**:
- `error_type: ErrorType` - Enum: PARSE_ERROR, VALIDATION_ERROR, TRANSFORMATION_ERROR
- `message: str` - Human-readable error description
- `file_path: Path` - Config file where error occurred
- `line_number: int | None` - Line number if applicable
- `details: str | None` - Stack trace or additional context

**Example**:
```python
class ErrorType(str, Enum):
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    TRANSFORMATION_ERROR = "transformation_error"

class MigrationError(BaseModel):
    error_type: ErrorType
    message: str = Field(min_length=1)
    file_path: Path
    line_number: int | None = Field(default=None, gt=0)
    details: str | None = None
```

---

## Configuration Element (Spec Reference)

**From Spec**: "Individual plugin or component within a Logstash/Vector config (input/source, filter/transform, output/sink)"

**Implementation**: Not a separate class, but represented by:
- `LogstashPlugin` (for Logstash side)
- `VectorComponent` (for Vector side)

These two classes form the fundamental mapping units in the transformation process.

---

## Entity Relationship Diagram

```
LogstashConfiguration (1) --contains--> (N) LogstashPlugin
LogstashPlugin (1) --maps-to--> (0..N) VectorComponent
VectorConfiguration (1) --contains--> (N) VectorComponent
VectorComponent (N) --references--> (N) VectorComponent [via inputs DAG]

LogstashConfiguration --transforms-to--> VectorConfiguration
Transformation --produces--> MigrationReport

MigrationReport (1) --contains--> (N) PluginMigration
MigrationReport (1) --contains--> (N) UnsupportedPlugin
MigrationReport (1) --contains--> (N) MigrationError
```

---

## Validation Summary

All models enforce spec requirements through Pydantic validators:

- **FR-002**: LogstashConfiguration requires ≥1 input and ≥1 output
- **FR-006**: VectorConfiguration requires ≥1 source and ≥1 sink
- **FR-008**: VectorConfiguration.to_toml() generates valid TOML
- **FR-009**: VectorComponent.comments stores TODO markers
- **FR-010**: MigrationReport captures all unsupported elements
- **FR-013**: MigrationError provides clear error messages
- **SC-004**: UnsupportedPlugin.manual_migration_guidance is required
- **SC-005**: All error types include line_number for location tracking
