"""Vector configuration models."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from lv_py.models import ComponentType


class VectorComponent(BaseModel):
    """Represents a single Vector component (source, transform, or sink)."""

    component_type: ComponentType
    component_kind: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)

    @field_validator("inputs")
    @classmethod
    def validate_inputs_for_type(cls, v: list[str], info: Any) -> list[str]:
        """Validate inputs based on component type."""
        comp_type = info.data.get("component_type")
        if comp_type == ComponentType.SOURCE and len(v) > 0:
            raise ValueError("SOURCE components cannot have inputs")
        if comp_type in (ComponentType.TRANSFORM, ComponentType.SINK) and len(v) == 0:
            raise ValueError(f"{comp_type} components must have at least one input")
        return v


class VectorConfiguration(BaseModel):
    """Represents a generated Vector configuration in TOML format."""

    file_path: Path
    sources: dict[str, VectorComponent] = Field(default_factory=dict, min_length=1)
    transforms: dict[str, VectorComponent] = Field(default_factory=dict)
    sinks: dict[str, VectorComponent] = Field(default_factory=dict, min_length=1)
    global_options: dict[str, Any] = Field(default_factory=dict)

    def to_toml(self) -> str:
        """Generate TOML string using tomlkit."""
        # Will be implemented in generator/toml_generator.py
        raise NotImplementedError("to_toml() will be implemented in toml_generator.py")

    def validate_syntax(self) -> tuple[bool, str]:
        """Validate using `vector validate` command."""
        # Will be implemented in utils/validation.py
        raise NotImplementedError("validate_syntax() will be implemented in validation.py")
