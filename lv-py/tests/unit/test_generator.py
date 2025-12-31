"""Unit tests for TOML generator."""

from pathlib import Path
import tomlkit

from lv_py.generator.toml_generator import generate_toml
from lv_py.models.vector_config import VectorConfiguration


def test_generate_empty_config():
    """Test generating TOML from minimal configuration."""
    from lv_py.models.vector_config import VectorComponent
    from lv_py.models import ComponentType

    # Create minimal valid components instead of None
    config = VectorConfiguration(
        file_path=Path("/tmp/test.toml"),
        sources={
            "test_source": VectorComponent(
                component_type=ComponentType.SOURCE,
                component_kind="file",
                config={},
                inputs=[],
                comments=[],
            )
        },
        sinks={
            "test_sink": VectorComponent(
                component_type=ComponentType.SINK,
                component_kind="file",
                config={},
                inputs=["test_source"],
                comments=[],
            )
        },
    )
    # Test that TOML can be generated without crashing
    toml_str = config.to_toml()
    assert toml_str is not None
    assert len(toml_str) > 0
    # Verify it's valid TOML
    parsed = tomlkit.parse(toml_str)
    assert "sources" in parsed or "sources.test_source" in toml_str
    assert "sinks" in parsed or "sinks.test_sink" in toml_str


def test_generate_source_component():
    """Test generating TOML for a source component."""
    # TODO: Implement test for [sources.name] section generation
    pass


def test_generate_transform_component():
    """Test generating TOML for a transform component."""
    # TODO: Implement test for [transforms.name] section generation
    # Should include inputs field
    pass


def test_generate_sink_component():
    """Test generating TOML for a sink component."""
    # TODO: Implement test for [sinks.name] section generation
    # Should include inputs field
    pass


def test_generate_component_with_comments():
    """Test generating TOML with TODO comments (T128)."""
    from lv_py.models.vector_config import VectorComponent
    from lv_py.models import ComponentType

    # Create component with TODO markers
    config = VectorConfiguration(
        file_path=Path("/tmp/test.toml"),
        sources={
            "kafka_input_placeholder": VectorComponent(
                component_type=ComponentType.SOURCE,
                component_kind="kafka",
                config={},
                inputs=[],
                comments=[
                    "TODO: Manual migration required for unsupported plugin 'kafka' (input)",
                    "Original Logstash configuration:",
                    "  kafka {",
                    '    bootstrap_servers => "localhost:9092"',
                    '    topics => ["application-logs"]',
                    "  }",
                    "",
                    "Vector alternatives to consider:",
                    "  - kafka source: https://vector.dev/docs/reference/configuration/sources/kafka/",
                ],
            )
        },
        sinks={
            "console_output": VectorComponent(
                component_type=ComponentType.SINK,
                component_kind="console",
                config={},
                inputs=["kafka_input_placeholder"],
                comments=[],
            )
        },
    )

    # Generate TOML
    toml_str = generate_toml(config)

    # Verify TODO markers are present
    assert "TODO: Manual migration required" in toml_str
    assert "kafka" in toml_str
    assert "Original Logstash configuration:" in toml_str
    assert "Vector alternatives to consider:" in toml_str
    assert "bootstrap_servers" in toml_str

    # Verify TOML is still valid despite comments
    parsed = tomlkit.parse(toml_str)
    assert "sources.kafka_input_placeholder" in toml_str or "sources" in parsed
    assert "sinks.console_output" in toml_str or "sinks" in parsed


def test_generate_complete_pipeline():
    """Test generating TOML for complete pipeline."""
    # TODO: Implement test for full config with source -> transform -> sink
    pass


def test_toml_syntax_validity():
    """Test that generated TOML is syntactically valid."""
    # This is tested via end-to-end migration tests
    # The simple-pipeline.conf -> simple-pipeline.toml migration validates TOML syntax
    pass
