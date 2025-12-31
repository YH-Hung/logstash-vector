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
        """Generate human-readable markdown report with Rich formatting."""
        lines = []
        lines.append("# Migration Report")
        lines.append("")
        lines.append(f"**Source:** `{self.source_file}`")
        lines.append(f"**Target:** `{self.target_file}`")
        lines.append(f"**Generated:** {self.timestamp.isoformat()}")
        lines.append(f"**Success Rate:** {self.success_rate:.1%}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- ✅ Successfully migrated: {len(self.supported_plugins)} plugins")
        lines.append(f"- ⚠️  Unsupported plugins: {len(self.unsupported_plugins)}")
        lines.append(f"- ❌ Errors: {len(self.errors)}")
        lines.append(f"- ⚡ Warnings: {len(self.warnings)}")
        lines.append("")

        # Supported plugins section
        if self.supported_plugins:
            lines.append("## Successfully Migrated Plugins")
            lines.append("")
            for migration in self.supported_plugins:
                lines.append(f"### {migration.logstash_plugin}")
                lines.append(f"- **Vector components:** {', '.join(migration.vector_components)}")
                if migration.notes:
                    lines.append(f"- **Notes:** {migration.notes}")
                lines.append("")

        # Unsupported plugins section
        if self.unsupported_plugins:
            lines.append("## Unsupported Plugins (Manual Migration Required)")
            lines.append("")
            for unsupported in self.unsupported_plugins:
                lines.append(f"### {unsupported.plugin_name} (line {unsupported.line_number})")
                lines.append(f"- **Type:** {unsupported.plugin_type.value}")
                lines.append("")
                lines.append("**Original Configuration:**")
                lines.append("```")
                lines.append(unsupported.original_config)
                lines.append("```")
                lines.append("")
                lines.append("**Migration Guidance:**")
                lines.append(unsupported.manual_migration_guidance)
                lines.append("")
                if unsupported.vector_alternatives:
                    lines.append("**Vector Alternatives:**")
                    for alt in unsupported.vector_alternatives:
                        lines.append(f"- {alt}")
                    lines.append("")

        # Errors section
        if self.errors:
            lines.append("## Errors")
            lines.append("")
            for error in self.errors:
                lines.append(f"### {error.error_type.value}")
                lines.append(f"- **File:** `{error.file_path}`")
                if error.line_number:
                    lines.append(f"- **Line:** {error.line_number}")
                lines.append(f"- **Message:** {error.message}")
                if error.details:
                    lines.append(f"- **Details:** {error.details}")
                lines.append("")

        # Warnings section
        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)
