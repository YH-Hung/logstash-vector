"""Migration report models."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from lv_py.models import ErrorType, PluginType


class MigrationError(BaseModel):
    """Error encountered during parsing or transformation."""

    error_type: ErrorType
    message: str = Field(min_length=1)
    file_path: Path
    line_number: int | None = Field(default=None, gt=0)
    details: str | None = None


class UnsupportedPlugin(BaseModel):
    """Record of a Logstash plugin that couldn't be automatically migrated."""

    plugin_name: str = Field(min_length=1)
    plugin_type: PluginType
    line_number: int = Field(gt=0)
    original_config: str
    manual_migration_guidance: str = Field(min_length=1)
    vector_alternatives: list[str] = Field(default_factory=list)


class PluginMigration(BaseModel):
    """Record of a successfully migrated Logstash plugin."""

    logstash_plugin: str
    vector_components: list[str] = Field(min_length=1)
    notes: str | None = None


class MigrationReport(BaseModel):
    """Document generated for each migration run."""

    model_config = {"frozen": True}  # Immutable after creation

    source_file: Path
    target_file: Path
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    supported_plugins: list[PluginMigration] = Field(default_factory=list)
    unsupported_plugins: list[UnsupportedPlugin] = Field(default_factory=list)
    errors: list[MigrationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate migration success rate."""
        total = len(self.supported_plugins) + len(self.unsupported_plugins)
        return len(self.supported_plugins) / total if total > 0 else 0.0

    def to_markdown(self) -> str:
        """Generate human-readable markdown report."""
        # Will be implemented later
        raise NotImplementedError("to_markdown() will be implemented later")
