"""
Integration tests for unsupported feature handling in US2.

These tests verify that:
1. Unsupported plugins generate TODO markers in Vector configs
2. Migration reports are created with detailed guidance
3. Generated configs remain syntactically valid
4. Mixed supported/unsupported configs are handled correctly
"""

from pathlib import Path

import pytest

from lv_py.generator.toml_generator import generate_toml
from lv_py.parser.logstash_parser import parse_file
from lv_py.transformers import transform_config


class TestUnsupportedInputHandling:
    """Test handling of unsupported input plugins."""

    def test_unsupported_kafka_input(self):
        """Test that kafka input generates TODO markers and migration report."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "unsupported-input.conf"
        expected_toml = Path(__file__).parent / "vector" / "unsupported-input.toml"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)
        generated_toml = generate_toml(vector_config)

        # Assert: Check that unsupported plugin is detected
        assert len(migration_report.unsupported_plugins) == 1
        unsupported = migration_report.unsupported_plugins[0]
        assert unsupported.plugin_name == "kafka"
        assert unsupported.plugin_type.value == "input"
        assert "kafka source" in unsupported.manual_migration_guidance.lower()
        assert len(unsupported.vector_alternatives) > 0

        # Assert: Check that TODO markers are present in generated TOML
        assert "TODO: Manual migration required" in generated_toml
        assert "kafka" in generated_toml
        assert "Original Logstash configuration:" in generated_toml
        assert "Vector alternatives to consider:" in generated_toml

        # Assert: Check that generated config is syntactically valid TOML
        import tomlkit
        try:
            tomlkit.parse(generated_toml)
        except Exception as e:
            pytest.fail(f"Generated TOML is not valid: {e}")

        # Assert: Check that file output is successfully migrated
        assert len(migration_report.supported_plugins) == 1
        assert migration_report.supported_plugins[0].logstash_plugin == "file"

        # Assert: Success rate should reflect partial migration
        expected_success_rate = 1 / 2  # 1 supported, 1 unsupported
        assert migration_report.success_rate == pytest.approx(expected_success_rate)


class TestUnsupportedFilterHandling:
    """Test handling of unsupported filter plugins."""

    def test_unsupported_ruby_filter(self):
        """Test that ruby filter generates TODO markers with VRL guidance."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "unsupported-filter.conf"
        expected_toml = Path(__file__).parent / "vector" / "unsupported-filter.toml"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)
        generated_toml = generate_toml(vector_config)

        # Assert: Check that unsupported plugin is detected
        assert len(migration_report.unsupported_plugins) == 1
        unsupported = migration_report.unsupported_plugins[0]
        assert unsupported.plugin_name == "ruby"
        assert unsupported.plugin_type.value == "filter"
        assert "vrl" in unsupported.manual_migration_guidance.lower()
        assert "remap" in unsupported.manual_migration_guidance.lower()

        # Assert: Original Ruby code is preserved in migration report
        assert "upcase" in unsupported.original_config.lower()

        # Assert: Check that TODO markers are present with VRL example
        assert "TODO: Manual migration required" in generated_toml
        assert "ruby" in generated_toml.lower()
        assert "VRL" in generated_toml or "vrl" in generated_toml

        # Assert: Generated config is syntactically valid TOML
        import tomlkit
        try:
            tomlkit.parse(generated_toml)
        except Exception as e:
            pytest.fail(f"Generated TOML is not valid: {e}")

        # Assert: File input and elasticsearch output are successfully migrated
        assert len(migration_report.supported_plugins) == 2
        supported_names = [p.logstash_plugin for p in migration_report.supported_plugins]
        assert "file" in supported_names
        assert "elasticsearch" in supported_names


class TestMixedSupportHandling:
    """Test handling of configs with both supported and unsupported plugins."""

    def test_mixed_supported_unsupported_config(self):
        """Test that mixed configs generate partial valid configs with TODO markers."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "mixed-support.conf"
        expected_toml = Path(__file__).parent / "vector" / "mixed-support.toml"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)
        generated_toml = generate_toml(vector_config)

        # Assert: Check supported plugins are migrated
        assert len(migration_report.supported_plugins) >= 3
        supported_names = [p.logstash_plugin for p in migration_report.supported_plugins]
        assert "file" in supported_names  # input
        assert "grok" in supported_names  # filter
        assert "mutate" in supported_names  # filter
        assert "elasticsearch" in supported_names  # output

        # Assert: Check unsupported plugins are flagged
        assert len(migration_report.unsupported_plugins) == 2
        unsupported_names = [p.plugin_name for p in migration_report.unsupported_plugins]
        assert "kafka" in unsupported_names  # input
        assert "ruby" in unsupported_names  # filter

        # Assert: Check that multiple TODO markers exist
        todo_count = generated_toml.count("TODO:")
        assert todo_count >= 2, "Should have TODO markers for each unsupported plugin"

        # Assert: Check that supported plugins have clean transformations
        assert "file_input" in generated_toml
        assert "parse_groks" in generated_toml  # grok filter
        assert "production" in generated_toml  # mutate filter (can be with or without quotes)
        assert "elasticsearch_output" in generated_toml

        # Assert: Generated config is syntactically valid TOML despite unsupported parts
        import tomlkit
        try:
            tomlkit.parse(generated_toml)
        except Exception as e:
            pytest.fail(f"Generated TOML is not valid: {e}")

        # Assert: Success rate should reflect partial migration
        total_plugins = len(migration_report.supported_plugins) + len(migration_report.unsupported_plugins)
        expected_success_rate = len(migration_report.supported_plugins) / total_plugins
        assert migration_report.success_rate == pytest.approx(expected_success_rate)

    def test_migration_report_has_line_numbers(self):
        """Test that unsupported plugins include line numbers (FR-013, SC-005)."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "mixed-support.conf"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)

        # Assert: All unsupported plugins should have line numbers
        for unsupported in migration_report.unsupported_plugins:
            assert unsupported.line_number > 0, f"{unsupported.plugin_name} should have line number"

    def test_migration_report_has_clear_guidance(self):
        """Test that migration reports provide clear manual migration guidance (SC-004, SC-007)."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "unsupported-filter.conf"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)

        # Assert: All unsupported plugins should have non-empty guidance
        for unsupported in migration_report.unsupported_plugins:
            assert len(unsupported.manual_migration_guidance) > 0, "Guidance should not be empty"
            assert len(unsupported.vector_alternatives) > 0, "Should suggest Vector alternatives"
            # Guidance should be actionable (contain helpful keywords)
            guidance_lower = unsupported.manual_migration_guidance.lower()
            assert any(
                keyword in guidance_lower
                for keyword in ["remap", "vrl", "transform", "source", "sink", "configure"]
            ), "Guidance should contain actionable keywords"


class TestTODOMarkerGeneration:
    """Test TODO marker generation in TOML output."""

    def test_todo_markers_include_original_config(self):
        """Test that TODO markers include original Logstash syntax."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "unsupported-input.conf"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)
        generated_toml = generate_toml(vector_config)

        # Assert: TODO marker should include original config
        assert "bootstrap_servers" in generated_toml
        assert "localhost:9092" in generated_toml
        assert "topics" in generated_toml

    def test_todo_markers_include_vector_alternatives(self):
        """Test that TODO markers suggest Vector alternatives."""
        # Arrange
        logstash_conf = Path(__file__).parent / "logstash" / "unsupported-filter.conf"

        # Act
        logstash_config = parse_file(logstash_conf)
        vector_config, migration_report = transform_config(logstash_config)
        generated_toml = generate_toml(vector_config)

        # Assert: TODO marker should suggest Vector alternatives
        assert "remap" in generated_toml.lower()
        assert "vrl" in generated_toml.lower()
        assert "https://vector.dev/docs" in generated_toml


@pytest.mark.skip(reason="Will run after implementation to verify RED phase")
def test_all_unsupported_features_tests_initially_fail():
    """
    This test documents that all above tests should fail initially (RED phase).
    Run this test with: uv run pytest tests/integration/test_unsupported_features.py::test_all_unsupported_features_tests_initially_fail -v

    Expected failures:
    - transform_config() function doesn't exist yet
    - Migration report generation not implemented
    - TODO marker generation not implemented
    - Unsupported plugin detection not implemented
    """
    pytest.fail("This test is a placeholder to document RED phase. Remove skip marker to verify all tests fail.")
