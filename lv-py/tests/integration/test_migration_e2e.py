"""End-to-end integration tests for migration workflow."""

from pathlib import Path

import pytest

from lv_py.api import migrate_directory


def test_migrate_file_input_to_vector(logstash_configs_dir, temp_output_dir):
    """Test migrating Logstash file input to Vector file source."""
    # Copy file-input.conf to temp directory for testing
    test_config = logstash_configs_dir / "file-input.conf"
    if not test_config.exists():
        pytest.skip(f"Test config not found: {test_config}")

    # Run migration
    result = migrate_directory(
        directory=logstash_configs_dir,
        output_dir=temp_output_dir,
        dry_run=False,
        overwrite=True,
        validate=False,  # Skip Vector CLI validation in unit tests
        verbose=True,
    )

    # Verify migration succeeded
    assert result.total_files > 0, "No files found to migrate"
    assert result.successful > 0, "No files successfully migrated"

    # Verify Vector config was created
    output_file = temp_output_dir / "file-input.toml"
    assert output_file.exists(), f"Expected output file not created: {output_file}"

    # Read and verify basic structure
    content = output_file.read_text()
    assert '["sources.' in content, "No sources section in generated config"
    assert '["sinks.' in content, "No sinks section in generated config"
    assert 'type = "file"' in content, "File source not correctly generated"

    # Verify migration report was created
    assert len(result.reports) > 0, "No migration reports generated"


def test_migrate_grok_filter_to_vector(logstash_configs_dir, temp_output_dir):
    """Test migrating Logstash grok filter to Vector remap."""
    test_config = logstash_configs_dir / "grok-filter.conf"
    if not test_config.exists():
        pytest.skip(f"Test config not found: {test_config}")

    # Run migration
    result = migrate_directory(
        directory=logstash_configs_dir,
        output_dir=temp_output_dir,
        dry_run=False,
        overwrite=True,
        validate=False,
        verbose=True,
    )

    # Verify migration succeeded
    assert result.total_files > 0, "No files found to migrate"

    # Verify Vector config was created
    output_file = temp_output_dir / "grok-filter.toml"
    assert output_file.exists(), f"Expected output file not created: {output_file}"

    # Read and verify grok transformation
    content = output_file.read_text()
    assert '["sources.' in content, "No sources section"
    assert '["transforms.' in content, "No transforms section for grok filter"
    assert '["sinks.' in content, "No sinks section"
    assert 'type = "remap"' in content, "Grok not converted to remap transform"
    assert 'parse_groks' in content, "parse_groks function not found in VRL"

    # Verify proper VRL syntax (should use double quotes in JSON array)
    assert '["' in content or 'patterns:' in content, "Grok patterns not properly formatted"

    # Verify elasticsearch sink
    assert 'type = "elasticsearch"' in content, "Elasticsearch sink not found"


def test_migrate_complete_pipeline(logstash_configs_dir, temp_output_dir):
    """Test migrating complete Logstash pipeline (input + filter + output)."""
    test_config = logstash_configs_dir / "complex-pipeline.conf"
    if not test_config.exists():
        pytest.skip(f"Test config not found: {test_config}")

    # Run migration on complex pipeline
    result = migrate_directory(
        directory=logstash_configs_dir,
        output_dir=temp_output_dir,
        dry_run=False,
        overwrite=True,
        validate=False,
        verbose=True,
    )

    # Verify migration succeeded
    assert result.total_files > 0, "No files found to migrate"

    # Verify Vector config was created
    output_file = temp_output_dir / "complex-pipeline.toml"
    assert output_file.exists(), f"Expected output file not created: {output_file}"

    content = output_file.read_text()

    # Verify multiple sources
    assert content.count('["sources.') >= 2, "Expected at least 2 sources (file + beats)"

    # Verify transforms section with proper chaining
    assert '["transforms.' in content, "No transforms section"
    assert 'inputs = [' in content, "Transforms not properly chained"

    # Verify multiple sinks
    assert content.count('["sinks.') >= 2, "Expected at least 2 sinks"

    # Verify specific plugins were migrated
    assert 'parse_groks' in content, "Grok filter not migrated"
    assert 'parse_timestamp' in content or 'to_timestamp' in content, "Date filter not migrated"

    # Note: Conditionals are currently TODO/unsupported, so we don't assert them yet


def test_migration_with_unsupported_features(logstash_configs_dir, temp_output_dir):
    """Test migration generates placeholders for unsupported plugins."""
    test_config = logstash_configs_dir / "unsupported-plugins.conf"
    if not test_config.exists():
        pytest.skip(f"Test config not found: {test_config}")

    # Run migration
    result = migrate_directory(
        directory=logstash_configs_dir,
        output_dir=temp_output_dir,
        dry_run=False,
        overwrite=True,
        validate=False,
        verbose=True,
    )

    # Should have partial success (some supported, some unsupported)
    assert result.total_files > 0, "No files found"

    # Verify migration report includes unsupported plugins
    report = next((r for r in result.reports if "unsupported-plugins" in str(r.source_file)), None)
    assert report is not None, "Migration report not found for unsupported-plugins.conf"

    # Verify unsupported plugins are tracked
    assert len(report.unsupported_plugins) > 0, "Unsupported plugins not tracked in report"

    # Find the specific unsupported plugins
    unsupported_names = [p.plugin_name for p in report.unsupported_plugins]
    assert "jdbc" in unsupported_names or "ruby" in unsupported_names or "kafka" in unsupported_names, \
        f"Expected unsupported plugins not found. Got: {unsupported_names}"

    # Verify supported plugins were still migrated
    assert len(report.supported_plugins) > 0, "No supported plugins were migrated"

    # Verify guidance is provided
    for unsupported in report.unsupported_plugins:
        assert unsupported.manual_migration_guidance, "No guidance provided for unsupported plugin"
        assert len(unsupported.vector_alternatives) > 0, "No Vector alternatives suggested"


def test_dry_run_mode(logstash_configs_dir, temp_output_dir):
    """Test dry-run mode doesn't write files."""
    # Run migration in dry-run mode
    result = migrate_directory(
        directory=logstash_configs_dir,
        output_dir=temp_output_dir,
        dry_run=True,  # Key: dry-run mode
        overwrite=True,
        validate=False,
        verbose=True,
    )

    # Verify result indicates dry-run
    assert result.is_dry_run, "Result should indicate dry-run mode"

    # Verify previews were generated
    assert len(result.previews) > 0, "No migration previews generated"

    # Verify NO files were actually written
    toml_files = list(temp_output_dir.glob("*.toml"))
    assert len(toml_files) == 0, f"Files were written in dry-run mode: {toml_files}"

    # Verify preview contains expected information
    preview = result.previews[0]
    assert preview.source_file.exists(), "Source file path invalid"
    assert preview.estimated_size > 0, "Estimated size should be calculated"
    assert len(preview.transformations) > 0, "No transformations in preview"


def test_migration_report_generation(logstash_configs_dir, temp_output_dir):
    """Test migration report is generated correctly."""
    # Run migration
    result = migrate_directory(
        directory=logstash_configs_dir,
        output_dir=temp_output_dir,
        dry_run=False,
        overwrite=True,
        validate=False,
        verbose=True,
    )

    # Verify migration reports were generated
    assert len(result.reports) > 0, "No migration reports generated"

    # Verify report structure for each migrated file
    for report in result.reports:
        # Basic report attributes
        assert report.source_file, "Report missing source file"
        assert report.target_file, "Report missing target file"
        assert report.timestamp, "Report missing timestamp"

        # Should have at least one of: supported plugins, unsupported plugins, or errors
        total_items = (len(report.supported_plugins) +
                      len(report.unsupported_plugins) +
                      len(report.errors))
        assert total_items > 0, "Report has no content"

        # If there are supported plugins, verify structure
        if report.supported_plugins:
            plugin = report.supported_plugins[0]
            assert plugin.logstash_plugin, "Supported plugin missing name"
            assert len(plugin.vector_components) > 0, "Supported plugin missing Vector mapping"

        # If there are unsupported plugins, verify guidance
        if report.unsupported_plugins:
            unsupported = report.unsupported_plugins[0]
            assert unsupported.plugin_name, "Unsupported plugin missing name"
            assert unsupported.plugin_type, "Unsupported plugin missing type"
            assert unsupported.manual_migration_guidance, "Unsupported plugin missing guidance"

        # Verify report can be converted to markdown (SC-007: 95% comprehension)
        markdown = report.to_markdown()
        assert "# " in markdown, "Report markdown missing headers"
        assert report.source_file.name in markdown, "Report markdown missing source file"

    print(f"\n✓ Generated {len(result.reports)} migration reports")
    print(f"✓ Total supported plugins: {sum(len(r.supported_plugins) for r in result.reports)}")
    print(f"✓ Total unsupported plugins: {sum(len(r.unsupported_plugins) for r in result.reports)}")
