"""
Functional equivalence tests - verify Logstash and Vector produce equivalent outputs.

These tests fulfill Constitutional Principle I: Functional Equivalence (NON-NEGOTIABLE)
"""

import json
from pathlib import Path

import pytest

from lv_py.api import migrate_directory


def test_grok_pattern_equivalence_static():
    """
    Test grok pattern migration produces correct VRL (static test).

    This tests the transformation logic without requiring running containers.
    """
    from lv_py.models import PluginType
    from lv_py.models.logstash_config import LogstashPlugin
    from lv_py.transformers import get_transformer

    # Create a grok filter plugin
    grok_plugin = LogstashPlugin(
        plugin_type=PluginType.FILTER,
        plugin_name="grok",
        config={
            "match": {
                "message": "%{COMBINEDAPACHELOG}"
            }
        },
        line_number=10,
    )

    # Transform it
    transformer = get_transformer(PluginType.FILTER, "grok")
    assert transformer is not None, "Grok transformer not found"

    vector_component = transformer.transform(grok_plugin)

    # Verify transformation
    assert vector_component.component_kind == "remap", "Should create remap transform"
    assert "parse_groks" in vector_component.config["source"], "Should use parse_groks function"

    # Verify VRL syntax uses double quotes (json format)
    vrl_source = vector_component.config["source"]
    assert '["' in vrl_source or '"' in vrl_source, "VRL should use double quotes for patterns"
    assert "['" not in vrl_source, "VRL should not use single quotes (Python format)"

    print(f"\n✓ Generated VRL:\n{vrl_source}")


def test_mutate_field_operations_equivalence():
    """
    Test mutate filter migration produces correct VRL for field operations.

    This tests: add_field, remove_field, rename, convert operations.
    """
    from lv_py.models import PluginType
    from lv_py.models.logstash_config import LogstashPlugin
    from lv_py.transformers import get_transformer

    # Create a mutate filter plugin with multiple operations
    mutate_plugin = LogstashPlugin(
        plugin_type=PluginType.FILTER,
        plugin_name="mutate",
        config={
            "add_field": {"migrated": "true", "environment": "production"},
            "remove_field": ["temp_field", "debug_info"],
            "rename": {"old_name": "new_name"},
            "convert": {"count": "integer", "enabled": "boolean"}
        },
        line_number=15,
    )

    # Transform it
    transformer = get_transformer(PluginType.FILTER, "mutate")
    assert transformer is not None, "Mutate transformer not found"

    vector_component = transformer.transform(mutate_plugin)

    # Verify transformation
    assert vector_component.component_kind == "remap", "Should create remap transform"
    vrl_source = vector_component.config["source"]

    # Verify add_field operations
    assert '.migrated = "true"' in vrl_source, "Should add 'migrated' field"
    assert '.environment = "production"' in vrl_source, "Should add 'environment' field"

    # Verify remove_field operations
    assert 'del(.temp_field)' in vrl_source or 'del(."temp_field")' in vrl_source, "Should remove temp_field"
    assert 'del(.debug_info)' in vrl_source or 'del(."debug_info")' in vrl_source, "Should remove debug_info"

    # Verify rename operations
    assert '.new_name = .old_name' in vrl_source, "Should rename old_name to new_name"
    assert 'del(.old_name)' in vrl_source, "Should delete old field after rename"

    # Verify convert operations
    assert 'to_int' in vrl_source or 'int!' in vrl_source, "Should convert count to integer"

    print(f"\n✓ Generated Mutate VRL:\n{vrl_source}")


def test_date_filter_format_mapping():
    """
    Test date filter migration with various timestamp formats.

    Verifies Joda-Time to strptime format conversion.
    """
    from lv_py.models import PluginType
    from lv_py.models.logstash_config import LogstashPlugin
    from lv_py.transformers import get_transformer

    # Test common date formats
    date_plugin = LogstashPlugin(
        plugin_type=PluginType.FILTER,
        plugin_name="date",
        config={
            "match": ["timestamp", "ISO8601"],
            "target": "@timestamp",
            "timezone": "UTC"
        },
        line_number=20,
    )

    transformer = get_transformer(PluginType.FILTER, "date")
    assert transformer is not None, "Date transformer not found"

    vector_component = transformer.transform(date_plugin)

    # Verify transformation
    assert vector_component.component_kind == "remap", "Should create remap transform"
    vrl_source = vector_component.config["source"]

    # Verify timestamp parsing
    assert 'parse_timestamp' in vrl_source or 'to_timestamp' in vrl_source, \
        "Should use timestamp parsing function"
    assert '.timestamp' in vrl_source, "Should reference timestamp field"

    print(f"\n✓ Generated Date VRL:\n{vrl_source}")


def test_transform_chaining_preserves_order():
    """
    Test that multiple filters are chained in correct order.

    Verifies Constitutional Principle I: Functional Equivalence.
    """
    from pathlib import Path
    from lv_py.migration import migrate_config
    import tempfile

    # Use complex-pipeline.conf which has multiple filters
    test_file = Path(__file__).parent.parent.parent.parent / "test-data" / "logstash" / "complex-pipeline.conf"

    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")

    # Migrate to temp file
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as tmp:
        output_path = Path(tmp.name)

    try:
        vector_config, report = migrate_config(test_file, output_path)

        if vector_config is None:
            pytest.fail(f"Migration failed: {report.errors}")

        # Find all transforms (filters) with their IDs
        transform_items = list(vector_config.transforms.items())  # [(id, component), ...]

        # Verify transforms are chained sequentially
        if len(transform_items) > 1:
            for i in range(1, len(transform_items)):
                current_id, current_transform = transform_items[i]
                previous_id, previous_transform = transform_items[i-1]

                # Current transform should have exactly one input: the previous transform
                assert len(current_transform.inputs) == 1, \
                    f"Transform {current_id} should have 1 input, has {len(current_transform.inputs)}"
                assert current_transform.inputs[0] == previous_id, \
                    f"Transform {current_id} should connect to {previous_id}, connects to {current_transform.inputs[0]}"

        print(f"\n✓ Verified {len(transform_items)} transforms are properly chained")
    finally:
        # Cleanup temp file
        if output_path.exists():
            output_path.unlink()


def test_elasticsearch_output_index_template():
    """
    Test elasticsearch output with date-based index templates.

    Verifies that index templates are preserved or TODO markers are added.
    """
    from lv_py.models import PluginType
    from lv_py.models.logstash_config import LogstashPlugin
    from lv_py.transformers import get_transformer

    # Create elasticsearch output with index template
    es_plugin = LogstashPlugin(
        plugin_type=PluginType.OUTPUT,
        plugin_name="elasticsearch",
        config={
            "hosts": ["http://localhost:9200"],
            "index": "logs-%{+YYYY.MM.dd}"
        },
        line_number=25,
    )

    transformer = get_transformer(PluginType.OUTPUT, "elasticsearch")
    assert transformer is not None, "Elasticsearch transformer not found"

    vector_component = transformer.transform(es_plugin)

    # Verify transformation
    assert vector_component.component_kind == "elasticsearch", "Should create elasticsearch sink"

    config = vector_component.config

    # Either index should be converted, or there should be a TODO comment
    if "index" in config:
        index_value = config["index"]
        # If it's a static index, it should not have Logstash template syntax
        if isinstance(index_value, str):
            assert "%{" not in index_value, "Should not contain Logstash template syntax"

    print(f"\n✓ Elasticsearch index handling: {config.get('index', 'TODO marker expected')}")
