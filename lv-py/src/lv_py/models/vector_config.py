"""Vector configuration models."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from lv_py.models import ComponentType


class VectorComponent(BaseModel):
    """Represents a single Vector component (source, transform, or sink)."""

    component_type: ComponentType
    component_kind: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)

    def validate_final(self) -> None:
        """
        Validate the component after all fields are set.

        Call this method after setting inputs in the migration orchestrator.
        """
        if self.component_type == ComponentType.SOURCE and len(self.inputs) > 0:
            raise ValueError("SOURCE components cannot have inputs")
        if self.component_type in (ComponentType.TRANSFORM, ComponentType.SINK) and len(self.inputs) == 0:
            raise ValueError(f"{self.component_type} components must have at least one input")


class VectorConfiguration(BaseModel):
    """Represents a generated Vector configuration in TOML format."""

    file_path: Path
    sources: dict[str, VectorComponent] = Field(default_factory=dict, min_length=1)
    transforms: dict[str, VectorComponent] = Field(default_factory=dict)
    sinks: dict[str, VectorComponent] = Field(default_factory=dict, min_length=1)
    global_options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_all_components(self) -> 'VectorConfiguration':
        """Validate all components have proper inputs set."""
        for component in self.sources.values():
            component.validate_final()
        for component in self.transforms.values():
            component.validate_final()
        for component in self.sinks.values():
            component.validate_final()
        return self

    def to_toml(self) -> str:
        """Generate TOML string using tomlkit."""
        from lv_py.generator.toml_generator import generate_toml

        return generate_toml(self)

    def validate_syntax(self) -> tuple[bool, str]:
        """Validate using `vector validate` command."""
        from lv_py.utils.validation import validate_vector_config

        return validate_vector_config(self.file_path)
