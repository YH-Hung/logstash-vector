"""Transformers for converting Logstash plugins to Vector components."""

from typing import Any

from lv_py.models import PluginType

# Plugin registry: maps plugin names to their transformer classes
PLUGIN_REGISTRY: dict[PluginType, dict[str, Any]] = {
    PluginType.INPUT: {},
    PluginType.FILTER: {},
    PluginType.OUTPUT: {},
}


def register_transformer(plugin_type: PluginType, plugin_name: str, transformer: Any) -> None:
    """Register a transformer for a specific plugin."""
    PLUGIN_REGISTRY[plugin_type][plugin_name] = transformer


def get_transformer(plugin_type: PluginType, plugin_name: str) -> Any:
    """Get the transformer for a specific plugin."""
    return PLUGIN_REGISTRY.get(plugin_type, {}).get(plugin_name)
