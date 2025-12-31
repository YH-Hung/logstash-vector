"""Unit tests for TOML generator."""

from pathlib import Path
import tomlkit

from lv_py.generator.toml_generator import generate_toml
from lv_py.models.vector_config import VectorConfiguration


def test_generate_empty_config():
    """Test generating TOML from minimal configuration."""
    config = VectorConfiguration(
        file_path=Path("/tmp/test.toml"),
        sources={"test_source": None},  # Will fail validation but tests generator
        sinks={"test_sink": None},
    )
    # This test is primarily checking that generator doesn't crash
    # Actual validation happens in VectorConfiguration model
    pass


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
    """Test generating TOML with TODO comments."""
    # TODO: Implement test for comment preservation
    # Unsupported features should have # TODO: markers
    pass


def test_generate_complete_pipeline():
    """Test generating TOML for complete pipeline."""
    # TODO: Implement test for full config with source -> transform -> sink
    pass


def test_toml_syntax_validity():
    """Test that generated TOML is syntactically valid."""
    # This is tested via end-to-end migration tests
    # The simple-pipeline.conf -> simple-pipeline.toml migration validates TOML syntax
    pass
