"""Transformers for converting Logstash plugins to Vector components."""

from typing import Any

from lv_py.models import PluginType
from lv_py.transformers.base import BaseTransformer
from lv_py.transformers.filters import (
    DateFilterTransformer,
    GrokFilterTransformer,
    MutateFilterTransformer,
)
from lv_py.transformers.inputs import BeatsInputTransformer, FileInputTransformer
from lv_py.transformers.outputs import (
    ElasticsearchOutputTransformer,
    FileOutputTransformer,
)

# Plugin registry: maps plugin names to their transformer instances
PLUGIN_REGISTRY: dict[PluginType, dict[str, BaseTransformer]] = {
    PluginType.INPUT: {},
    PluginType.FILTER: {},
    PluginType.OUTPUT: {},
}


def register_transformer(
    plugin_type: PluginType, plugin_name: str, transformer: BaseTransformer
) -> None:
    """Register a transformer for a specific plugin."""
    PLUGIN_REGISTRY[plugin_type][plugin_name] = transformer


def get_transformer(plugin_type: PluginType, plugin_name: str) -> BaseTransformer | None:
    """Get the transformer for a specific plugin."""
    return PLUGIN_REGISTRY.get(plugin_type, {}).get(plugin_name)


# Register all transformers on module import
def _register_all_transformers() -> None:
    """Register all available transformers."""
    # Input transformers
    register_transformer(PluginType.INPUT, "file", FileInputTransformer())
    register_transformer(PluginType.INPUT, "beats", BeatsInputTransformer())

    # Filter transformers
    register_transformer(PluginType.FILTER, "grok", GrokFilterTransformer())
    register_transformer(PluginType.FILTER, "mutate", MutateFilterTransformer())
    register_transformer(PluginType.FILTER, "date", DateFilterTransformer())

    # Output transformers
    register_transformer(PluginType.OUTPUT, "elasticsearch", ElasticsearchOutputTransformer())
    register_transformer(PluginType.OUTPUT, "file", FileOutputTransformer())


# Auto-register on import
_register_all_transformers()
