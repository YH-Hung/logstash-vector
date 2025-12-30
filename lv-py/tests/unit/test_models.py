"""Unit tests for Pydantic models."""


from lv_py.models import ComponentType, PluginType
from lv_py.models.logstash_config import LogstashPlugin


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


# TODO: Add more unit tests
# - Test LogstashConfiguration validation
# - Test VectorComponent validation
# - Test VectorConfiguration validation
# - Test MigrationReport calculations
# - Test all model edge cases
