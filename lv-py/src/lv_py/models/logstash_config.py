"""Logstash configuration models."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from lv_py.models import PluginType

# Registry of supported plugins
SUPPORTED_PLUGINS = {
    PluginType.INPUT: {"file", "beats"},
    PluginType.FILTER: {"grok", "mutate", "date"},
    PluginType.OUTPUT: {"elasticsearch", "file"},
}


class LogstashPlugin(BaseModel):
    """Represents a single Logstash plugin (input, filter, or output)."""

    plugin_type: PluginType
    plugin_name: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    conditionals: str | None = None
    line_number: int = Field(gt=0)

    @property
    def supported(self) -> bool:
        """Check if this plugin has a Vector mapping."""
        return self.plugin_name in SUPPORTED_PLUGINS.get(self.plugin_type, set())


class LogstashConfiguration(BaseModel):
    """Represents a parsed Logstash configuration file."""

    model_config = {"frozen": True}  # Immutable after parsing

    file_path: Path
    inputs: list[LogstashPlugin] = Field(min_length=1)
    filters: list[LogstashPlugin] = Field(default_factory=list)
    outputs: list[LogstashPlugin] = Field(min_length=1)
    raw_content: str

    @field_validator("file_path")
    @classmethod
    def validate_file_exists(cls, v: Path) -> Path:
        """Validate that the file path exists and is readable."""
        if not v.exists():
            raise ValueError(f"File does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v
