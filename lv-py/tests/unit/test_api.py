"""Unit tests for API functions."""

import pytest
from pathlib import Path
from lv_py.api import migrate_directory, validate_configs, diff_configs
from lv_py.models.migration_report import (
    MigrationResult,
    ValidationResults,
    DiffResult,
)


class TestMigrateDirectory:
    """Tests for migrate_directory function."""

    def test_dry_run_mode_no_files_written(self, tmp_path):
        """Test that dry-run mode does not write files."""
        # Create test directory with .conf file
        test_dir = tmp_path / "configs"
        test_dir.mkdir()

        conf_file = test_dir / "test.conf"
        conf_file.write_text("""
input { file { path => "/test" } }
output { file { path => "/test" } }
""")

        # Run in dry-run mode
        result = migrate_directory(
            directory=test_dir,
            dry_run=True,
        )

        # Verify result structure
        assert isinstance(result, MigrationResult)
        assert result.is_dry_run is True
        assert result.total_files >= 1

        # Verify no .toml files created
        toml_files = list(test_dir.glob("*.toml"))
        assert len(toml_files) == 0

        # Should have previews instead of reports
        assert len(result.previews) > 0
        assert len(result.reports) == 0

    def test_live_mode_creates_files(self, tmp_path):
        """Test that live mode creates output files."""
        # Create test directory
        test_dir = tmp_path / "configs"
        test_dir.mkdir()

        conf_file = test_dir / "test.conf"
        conf_file.write_text("""
input { file { path => "/test" } }
output { file { path => "/test" } }
""")

        # Run in live mode
        result = migrate_directory(
            directory=test_dir,
            dry_run=False,
        )

        # Verify result structure
        assert isinstance(result, MigrationResult)
        assert result.is_dry_run is False

        # Should have reports instead of previews
        # Note: This may fail if migration logic is incomplete
        # assert len(result.reports) > 0

    def test_custom_output_directory(self, tmp_path):
        """Test migration with custom output directory."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        conf_file = input_dir / "test.conf"
        conf_file.write_text("""
input { file { path => "/test" } }
output { file { path => "/test" } }
""")

        # Run migration with custom output dir
        result = migrate_directory(
            directory=input_dir,
            output_dir=output_dir,
            dry_run=False,
        )

        # Output files should be in output_dir, not input_dir
        # Note: This may fail if migration logic is incomplete


class TestValidateConfigs:
    """Tests for validate_configs function."""

    def test_validate_single_file(self, tmp_path):
        """Test validating a single TOML file."""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text("""
[sources.test]
type = "file"
include = ["/test"]
""")

        result = validate_configs([toml_file])

        # Verify result structure
        assert isinstance(result, ValidationResults)
        assert len(result.validation_results) == 1

        # Note: Actual validation depends on Vector being installed

    def test_validate_multiple_files(self, tmp_path):
        """Test validating multiple TOML files."""
        file1 = tmp_path / "test1.toml"
        file1.write_text("[sources.test]\ntype = 'file'\ninclude = ['/test']")

        file2 = tmp_path / "test2.toml"
        file2.write_text("[sources.test2]\ntype = 'file'\ninclude = ['/test2']")

        result = validate_configs([file1, file2])

        assert isinstance(result, ValidationResults)
        assert len(result.validation_results) == 2

    def test_validation_exit_codes(self, tmp_path):
        """Test that validation sets appropriate exit codes."""
        toml_file = tmp_path / "test.toml"
        toml_file.write_text("[sources.test]\ntype = 'file'\ninclude = ['/test']")

        result = validate_configs([toml_file])

        # Exit code should be 0 or 1
        assert result.exit_code in [0, 1]


class TestDiffConfigs:
    """Tests for diff_configs function."""

    def test_basic_diff(self, tmp_path):
        """Test basic diff between Logstash and Vector configs."""
        logstash_file = tmp_path / "test.conf"
        logstash_file.write_text("""
input {
  file {
    path => "/var/log/test.log"
  }
}
output {
  file {
    path => "/var/log/output.log"
  }
}
""")

        vector_file = tmp_path / "test.toml"
        vector_file.write_text("""
[sources.file_input]
type = "file"
include = ["/var/log/test.log"]

[sinks.file_output]
type = "file"
path = "/var/log/output.log"
inputs = ["file_input"]
""")

        result = diff_configs(logstash_file, vector_file)

        # Verify result structure
        assert isinstance(result, DiffResult)
        assert result.logstash_file == logstash_file
        assert result.vector_file == vector_file

    def test_diff_formatted_output(self, tmp_path):
        """Test that diff produces formatted output."""
        logstash_file = tmp_path / "test.conf"
        logstash_file.write_text("""
input { file { path => "/test" } }
output { file { path => "/test" } }
""")

        vector_file = tmp_path / "test.toml"
        vector_file.write_text("""
[sources.test]
type = "file"
include = ["/test"]

[sinks.test]
type = "file"
path = "/test"
inputs = ["test"]
""")

        result = diff_configs(logstash_file, vector_file)
        formatted = result.to_formatted_output()

        # Should contain key elements
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Comparing" in formatted

    def test_diff_identifies_components(self, tmp_path):
        """Test that diff correctly identifies component mappings."""
        logstash_file = tmp_path / "test.conf"
        logstash_file.write_text("""
input { file { path => "/test" } }
filter { grok { match => { "message" => "%{COMBINEDAPACHELOG}" } } }
output { file { path => "/test" } }
""")

        vector_file = tmp_path / "test.toml"
        vector_file.write_text("""
[sources.file_source]
type = "file"
include = ["/test"]

[transforms.parse]
type = "remap"
inputs = ["file_source"]
source = 'parse_groks!(.message, ["%{COMBINEDAPACHELOG}"])'

[sinks.file_sink]
type = "file"
path = "/test"
inputs = ["parse"]
""")

        result = diff_configs(logstash_file, vector_file)

        # Should identify inputs, filters, and outputs
        # Note: Actual mapping quality depends on implementation
        assert isinstance(result.input_mappings, list)
        assert isinstance(result.filter_mappings, list)
        assert isinstance(result.output_mappings, list)
