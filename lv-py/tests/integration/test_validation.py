"""
Integration tests for validation and preview features (User Story 3).

Tests verify:
- Dry-run mode (preview without writing files)
- Validation command (verify Vector configs)
- Diff command (compare Logstash and Vector configs)
"""

from pathlib import Path

import pytest


class TestDryRunMode:
    """Test dry-run mode functionality."""

    def test_dry_run_no_files_written(
        self,
        logstash_samples_dir: Path,
        temp_output_dir: Path,
    ):
        """Test that dry-run mode does not write any files."""
        from lv_py.cli import migrate_directory

        # Run migration in dry-run mode
        result = migrate_directory(
            directory=logstash_samples_dir,
            output_dir=temp_output_dir,
            dry_run=True,
        )

        # Verify no .toml files were created
        toml_files = list(temp_output_dir.glob("*.toml"))
        assert len(toml_files) == 0, "Dry-run should not create any files"

        # Verify result contains preview information
        assert result.is_dry_run is True
        assert len(result.previews) > 0, "Should have preview data"

    def test_dry_run_shows_preview(
        self,
        logstash_samples_dir: Path,
        temp_output_dir: Path,
    ):
        """Test that dry-run mode shows preview of what would be migrated."""
        from lv_py.cli import migrate_directory

        # Use a simple config for testing
        test_conf = logstash_samples_dir / "file-input.conf"

        result = migrate_directory(
            directory=test_conf.parent,
            output_dir=temp_output_dir,
            dry_run=True,
        )

        # Verify preview contains expected information
        assert len(result.previews) > 0
        preview = result.previews[0]

        # Preview should show source and target paths
        assert "file-input.conf" in str(preview.source_file)
        assert "file-input.toml" in str(preview.target_file)

        # Preview should show file size estimation
        assert preview.estimated_size > 0

        # Preview should show transformation summary
        assert len(preview.transformations) > 0

    def test_dry_run_with_unsupported_features(
        self,
        logstash_samples_dir: Path,
        temp_output_dir: Path,
    ):
        """Test dry-run mode with configs containing unsupported features."""
        from lv_py.cli import migrate_directory

        # Use config with unsupported features
        test_conf = logstash_samples_dir / "unsupported-input.conf"

        result = migrate_directory(
            directory=test_conf.parent,
            output_dir=temp_output_dir,
            dry_run=True,
        )

        # Verify preview shows unsupported features
        preview = [p for p in result.previews if "unsupported" in str(p.source_file)][
            0
        ]
        assert len(preview.unsupported_plugins) > 0
        assert "TODO" in preview.notes or any(
            "TODO" in t.notes for t in preview.transformations
        )


class TestValidateCommand:
    """Test validation command functionality."""

    def test_validate_valid_config(
        self,
        vector_samples_dir: Path,
    ):
        """Test validation of valid Vector configs."""
        from lv_py.cli import validate_configs

        # Use a known valid config
        valid_toml = vector_samples_dir / "file-input.toml"

        result = validate_configs([valid_toml])

        assert result.all_valid is True
        assert len(result.validation_errors) == 0
        assert result.exit_code == 0

    def test_validate_invalid_config(
        self,
        temp_output_dir: Path,
    ):
        """Test validation of invalid Vector configs."""
        from lv_py.cli import validate_configs

        # Create an invalid config
        invalid_toml = temp_output_dir / "invalid.toml"
        invalid_toml.write_text(
            """
[sources.bad_source]
type = "nonexistent_type"
invalid_field = "value"
"""
        )

        result = validate_configs([invalid_toml])

        assert result.all_valid is False
        assert len(result.validation_errors) > 0
        assert result.exit_code == 1

    def test_validate_multiple_configs(
        self,
        vector_samples_dir: Path,
        temp_output_dir: Path,
    ):
        """Test validation of multiple Vector configs."""
        from lv_py.cli import validate_configs

        # Mix of valid and invalid configs
        valid_toml = vector_samples_dir / "file-input.toml"
        invalid_toml = temp_output_dir / "invalid.toml"
        invalid_toml.write_text("[sources.bad]\ntype = 'invalid'")

        result = validate_configs([valid_toml, invalid_toml])

        assert result.all_valid is False
        assert len(result.validation_results) == 2
        assert result.exit_code == 1

        # Check individual results
        file_input_result = [r for r in result.validation_results if "file-input" in str(r.file_path)][0]
        invalid_result = [r for r in result.validation_results if "invalid" in str(r.file_path)][0]

        assert file_input_result.is_valid is True
        assert invalid_result.is_valid is False

    def test_validate_glob_pattern(
        self,
        vector_samples_dir: Path,
    ):
        """Test validation with glob pattern for multiple files."""
        from lv_py.cli import validate_configs

        # Validate all .toml files in directory
        result = validate_configs(
            files=[vector_samples_dir / "*.toml"],
            use_glob=True,
        )

        # Should find and validate multiple configs
        assert len(result.validation_results) > 1


class TestDiffCommand:
    """Test diff command functionality."""

    def test_diff_basic_comparison(
        self,
        logstash_samples_dir: Path,
        vector_samples_dir: Path,
    ):
        """Test basic diff between Logstash and Vector configs."""
        from lv_py.cli import diff_configs

        logstash_conf = logstash_samples_dir / "file-input.conf"
        vector_toml = vector_samples_dir / "file-input.toml"

        result = diff_configs(
            logstash_config=logstash_conf,
            vector_config=vector_toml,
        )

        # Verify diff result structure
        assert result.logstash_file == logstash_conf
        assert result.vector_file == vector_toml

        # Should have component mappings
        assert len(result.input_mappings) > 0
        assert len(result.output_mappings) > 0

    def test_diff_with_filters(
        self,
        logstash_samples_dir: Path,
        vector_samples_dir: Path,
    ):
        """Test diff with filter transformations."""
        from lv_py.cli import diff_configs

        logstash_conf = logstash_samples_dir / "grok-filter.conf"
        vector_toml = vector_samples_dir / "grok-filter.toml"

        result = diff_configs(
            logstash_config=logstash_conf,
            vector_config=vector_toml,
        )

        # Should have filter mappings
        assert len(result.filter_mappings) > 0

        # Check that grok is mapped to remap
        grok_mapping = [m for m in result.filter_mappings if "grok" in m.logstash_plugin.lower()][0]
        assert "remap" in grok_mapping.vector_component.lower()

    def test_diff_highlights_unsupported(
        self,
        logstash_samples_dir: Path,
        vector_samples_dir: Path,
    ):
        """Test that diff highlights unsupported features."""
        from lv_py.cli import diff_configs

        logstash_conf = logstash_samples_dir / "mixed-support.conf"
        vector_toml = vector_samples_dir / "mixed-support.toml"

        result = diff_configs(
            logstash_config=logstash_conf,
            vector_config=vector_toml,
        )

        # Should identify unsupported features
        assert len(result.unsupported_features) > 0

        # Each unsupported feature should have details
        for unsupported in result.unsupported_features:
            assert unsupported.plugin_name
            assert unsupported.line_number > 0
            assert unsupported.vector_alternatives or unsupported.manual_guidance

    def test_diff_side_by_side_output(
        self,
        logstash_samples_dir: Path,
        vector_samples_dir: Path,
    ):
        """Test that diff produces readable side-by-side output."""
        from lv_py.cli import diff_configs

        logstash_conf = logstash_samples_dir / "file-input.conf"
        vector_toml = vector_samples_dir / "file-input.toml"

        result = diff_configs(
            logstash_config=logstash_conf,
            vector_config=vector_toml,
        )

        # Generate formatted output
        formatted_output = result.to_formatted_output()

        # Should contain both Logstash and Vector sections
        assert "Logstash" in formatted_output or "logstash" in formatted_output.lower()
        assert "Vector" in formatted_output or "vector" in formatted_output.lower()

        # Should show mappings with arrows or similar indicators
        assert "→" in formatted_output or "->" in formatted_output or "maps to" in formatted_output.lower()


# Tests are now implemented and ready to run
