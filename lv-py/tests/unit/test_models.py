"""Unit tests for Pydantic models."""

from datetime import datetime
from pathlib import Path

import pytest

from lv_py.models import ComponentType, ErrorType, PluginType
from lv_py.models.logstash_config import LogstashPlugin
from lv_py.models.migration_report import (
    MigrationError,
    MigrationReport,
    PluginMigration,
    UnsupportedPlugin,
)


def test_plugin_type_enum():
    """Test PluginType enum values."""
    assert PluginType.INPUT == "input"
    assert PluginType.FILTER == "filter"
    assert PluginType.OUTPUT == "output"


def test_component_type_enum():
    """Test ComponentType enum values."""
    assert ComponentType.SOURCE == "source"
    assert ComponentType.TRANSFORM == "transform"
    assert ComponentType.SINK == "sink"


def test_logstash_plugin_supported():
    """Test LogstashPlugin.supported property."""
    plugin = LogstashPlugin(
        plugin_type=PluginType.INPUT,
        plugin_name="file",
        line_number=1,
    )
    assert plugin.supported is True

    unsupported = LogstashPlugin(
        plugin_type=PluginType.INPUT,
        plugin_name="kafka",  # Not in supported list
        line_number=1,
    )
    assert unsupported.supported is False


# US2 Unit Tests

class TestUnsupportedPlugin:
    """Test UnsupportedPlugin model validation (T129)."""

    def test_valid_unsupported_plugin(self):
        """Test creating a valid UnsupportedPlugin."""
        unsupported = UnsupportedPlugin(
            plugin_name="kafka",
            plugin_type=PluginType.INPUT,
            line_number=5,
            original_config='bootstrap_servers => "localhost:9092"',
            manual_migration_guidance="Migrate to Vector kafka source",
            vector_alternatives=["kafka source"],
        )

        assert unsupported.plugin_name == "kafka"
        assert unsupported.plugin_type == PluginType.INPUT
        assert unsupported.line_number == 5
        assert "localhost:9092" in unsupported.original_config
        assert len(unsupported.manual_migration_guidance) > 0
        assert len(unsupported.vector_alternatives) > 0

    def test_unsupported_plugin_requires_guidance(self):
        """Test that manual_migration_guidance is required and non-empty (SC-004)."""
        with pytest.raises(ValueError):
            UnsupportedPlugin(
                plugin_name="kafka",
                plugin_type=PluginType.INPUT,
                line_number=5,
                original_config="config",
                manual_migration_guidance="",  # Empty guidance should fail
                vector_alternatives=[],
            )

    def test_unsupported_plugin_requires_positive_line_number(self):
        """Test that line_number must be positive."""
        with pytest.raises(ValueError):
            UnsupportedPlugin(
                plugin_name="kafka",
                plugin_type=PluginType.INPUT,
                line_number=0,  # Zero line number should fail
                original_config="config",
                manual_migration_guidance="Guidance",
                vector_alternatives=[],
            )

        with pytest.raises(ValueError):
            UnsupportedPlugin(
                plugin_name="kafka",
                plugin_type=PluginType.INPUT,
                line_number=-1,  # Negative line number should fail
                original_config="config",
                manual_migration_guidance="Guidance",
                vector_alternatives=[],
            )

    def test_unsupported_plugin_vector_alternatives_optional(self):
        """Test that vector_alternatives can be empty list."""
        unsupported = UnsupportedPlugin(
            plugin_name="custom_plugin",
            plugin_type=PluginType.FILTER,
            line_number=10,
            original_config="custom config",
            manual_migration_guidance="Manual migration required",
            vector_alternatives=[],  # Empty list should be valid
        )

        assert unsupported.vector_alternatives == []


class TestPluginMigration:
    """Test PluginMigration model."""

    def test_valid_plugin_migration(self):
        """Test creating a valid PluginMigration."""
        migration = PluginMigration(
            logstash_plugin="file",
            vector_components=["file_input"],
            notes="Successfully migrated to Vector file source",
        )

        assert migration.logstash_plugin == "file"
        assert migration.vector_components == ["file_input"]
        assert migration.notes is not None

    def test_plugin_migration_requires_components(self):
        """Test that vector_components must be non-empty."""
        with pytest.raises(ValueError):
            PluginMigration(
                logstash_plugin="file",
                vector_components=[],  # Empty list should fail
                notes=None,
            )

    def test_plugin_migration_notes_optional(self):
        """Test that notes field is optional."""
        migration = PluginMigration(
            logstash_plugin="file",
            vector_components=["file_input"],
            notes=None,
        )

        assert migration.notes is None


class TestMigrationError:
    """Test MigrationError model."""

    def test_valid_migration_error(self):
        """Test creating a valid MigrationError."""
        error = MigrationError(
            error_type=ErrorType.PARSE_ERROR,
            message="Failed to parse Logstash config",
            file_path=Path("/tmp/config.conf"),
            line_number=15,
            details="Unexpected token",
        )

        assert error.error_type == ErrorType.PARSE_ERROR
        assert len(error.message) > 0
        assert error.line_number == 15
        assert error.details is not None

    def test_migration_error_line_number_optional(self):
        """Test that line_number is optional."""
        error = MigrationError(
            error_type=ErrorType.VALIDATION_ERROR,
            message="Validation failed",
            file_path=Path("/tmp/config.conf"),
            line_number=None,  # Should be valid
            details=None,
        )

        assert error.line_number is None

    def test_migration_error_requires_positive_line_number(self):
        """Test that if line_number is provided, it must be positive."""
        with pytest.raises(ValueError):
            MigrationError(
                error_type=ErrorType.PARSE_ERROR,
                message="Error",
                file_path=Path("/tmp/config.conf"),
                line_number=0,  # Zero should fail
            )


class TestMigrationReport:
    """Test MigrationReport model and markdown generation (T130)."""

    def test_valid_migration_report(self):
        """Test creating a valid MigrationReport."""
        report = MigrationReport(
            source_file=Path("/tmp/logstash.conf"),
            target_file=Path("/tmp/vector.toml"),
            supported_plugins=[
                PluginMigration(
                    logstash_plugin="file",
                    vector_components=["file_input"],
                )
            ],
            unsupported_plugins=[
                UnsupportedPlugin(
                    plugin_name="kafka",
                    plugin_type=PluginType.INPUT,
                    line_number=5,
                    original_config="config",
                    manual_migration_guidance="Guidance",
                    vector_alternatives=["kafka source"],
                )
            ],
            errors=[],
            warnings=[],
        )

        assert report.source_file == Path("/tmp/logstash.conf")
        assert report.target_file == Path("/tmp/vector.toml")
        assert len(report.supported_plugins) == 1
        assert len(report.unsupported_plugins) == 1
        assert isinstance(report.timestamp, datetime)

    def test_migration_report_success_rate(self):
        """Test success rate calculation."""
        # All supported
        report_all_supported = MigrationReport(
            source_file=Path("/tmp/test.conf"),
            target_file=Path("/tmp/test.toml"),
            supported_plugins=[
                PluginMigration(logstash_plugin="file", vector_components=["file_input"]),
                PluginMigration(logstash_plugin="grok", vector_components=["grok_filter"]),
            ],
            unsupported_plugins=[],
        )
        assert report_all_supported.success_rate == 1.0

        # All unsupported
        report_all_unsupported = MigrationReport(
            source_file=Path("/tmp/test.conf"),
            target_file=Path("/tmp/test.toml"),
            supported_plugins=[],
            unsupported_plugins=[
                UnsupportedPlugin(
                    plugin_name="kafka",
                    plugin_type=PluginType.INPUT,
                    line_number=1,
                    original_config="config",
                    manual_migration_guidance="Guidance",
                )
            ],
        )
        assert report_all_unsupported.success_rate == 0.0

        # Mixed
        report_mixed = MigrationReport(
            source_file=Path("/tmp/test.conf"),
            target_file=Path("/tmp/test.toml"),
            supported_plugins=[
                PluginMigration(logstash_plugin="file", vector_components=["file_input"]),
            ],
            unsupported_plugins=[
                UnsupportedPlugin(
                    plugin_name="kafka",
                    plugin_type=PluginType.INPUT,
                    line_number=1,
                    original_config="config",
                    manual_migration_guidance="Guidance",
                )
            ],
        )
        assert report_mixed.success_rate == 0.5

        # Empty report
        report_empty = MigrationReport(
            source_file=Path("/tmp/test.conf"),
            target_file=Path("/tmp/test.toml"),
            supported_plugins=[],
            unsupported_plugins=[],
        )
        assert report_empty.success_rate == 0.0

    def test_migration_report_to_markdown(self):
        """Test markdown report generation with Rich formatting (T130)."""
        report = MigrationReport(
            source_file=Path("/tmp/logstash.conf"),
            target_file=Path("/tmp/vector.toml"),
            supported_plugins=[
                PluginMigration(
                    logstash_plugin="file",
                    vector_components=["file_input"],
                    notes="Migrated successfully",
                )
            ],
            unsupported_plugins=[
                UnsupportedPlugin(
                    plugin_name="kafka",
                    plugin_type=PluginType.INPUT,
                    line_number=5,
                    original_config='bootstrap_servers => "localhost:9092"',
                    manual_migration_guidance="Migrate to Vector kafka source",
                    vector_alternatives=["kafka source: https://vector.dev/docs"],
                )
            ],
            errors=[
                MigrationError(
                    error_type=ErrorType.PARSE_ERROR,
                    message="Parse error",
                    file_path=Path("/tmp/logstash.conf"),
                    line_number=10,
                )
            ],
            warnings=["Deprecated feature used"],
        )

        markdown = report.to_markdown()

        # Verify markdown structure
        assert "# Migration Report" in markdown
        assert "Source:" in markdown
        assert "/tmp/logstash.conf" in markdown
        assert "Target:" in markdown
        assert "/tmp/vector.toml" in markdown
        assert "Success Rate:" in markdown

        # Verify summary section
        assert "## Summary" in markdown
        assert "Successfully migrated: 1" in markdown
        assert "Unsupported plugins: 1" in markdown
        assert "Errors: 1" in markdown
        assert "Warnings: 1" in markdown

        # Verify supported plugins section
        assert "## Successfully Migrated Plugins" in markdown
        assert "### file" in markdown
        assert "file_input" in markdown
        assert "Migrated successfully" in markdown

        # Verify unsupported plugins section
        assert "## Unsupported Plugins" in markdown
        assert "### kafka (line 5)" in markdown
        assert "localhost:9092" in markdown
        assert "Migrate to Vector kafka source" in markdown
        assert "kafka source: https://vector.dev/docs" in markdown

        # Verify errors section
        assert "## Errors" in markdown
        assert "Parse error" in markdown

        # Verify warnings section
        assert "## Warnings" in markdown
        assert "Deprecated feature used" in markdown

    def test_migration_report_immutable(self):
        """Test that MigrationReport is immutable after creation."""
        report = MigrationReport(
            source_file=Path("/tmp/test.conf"),
            target_file=Path("/tmp/test.toml"),
        )

        # Should not be able to modify after creation
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            report.source_file = Path("/tmp/other.conf")  # type: ignore
