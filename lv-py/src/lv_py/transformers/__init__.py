"""Transformers for converting Logstash plugins to Vector components."""

from typing import Any

from lv_py.models import ComponentType, PluginType
from lv_py.models.logstash_config import LogstashConfiguration, LogstashPlugin
from lv_py.models.migration_report import (
    MigrationReport,
    PluginMigration,
    UnsupportedPlugin,
)
from lv_py.models.vector_config import VectorComponent, VectorConfiguration
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

# Manual migration guidance templates for unsupported plugins
UNSUPPORTED_GUIDANCE: dict[str, dict[str, str | list[str]]] = {
    "kafka": {
        "guidance": "The Logstash kafka input can be migrated to Vector's kafka source.\nUpdate the configuration below with the correct kafka settings.",
        "alternatives": ["kafka source: https://vector.dev/docs/reference/configuration/sources/kafka/"],
    },
    "ruby": {
        "guidance": "The Logstash ruby filter executes custom Ruby code for event processing.\nIn Vector, use the 'remap' transform with VRL (Vector Remap Language) to achieve similar functionality.\nVRL provides built-in functions for string manipulation and field transformation.",
        "alternatives": ["remap transform with VRL: https://vector.dev/docs/reference/vrl/"],
    },
    "jdbc": {
        "guidance": "The Logstash JDBC input/filter is not directly supported in Vector.\nConsider using a separate database connector or ETL tool to feed data into Vector via HTTP or file sources.",
        "alternatives": [
            "http source: https://vector.dev/docs/reference/configuration/sources/http/",
            "file source: https://vector.dev/docs/reference/configuration/sources/file/",
        ],
    },
}


def register_transformer(
    plugin_type: PluginType, plugin_name: str, transformer: BaseTransformer
) -> None:
    """Register a transformer for a specific plugin."""
    PLUGIN_REGISTRY[plugin_type][plugin_name] = transformer


def get_transformer(plugin_type: PluginType, plugin_name: str) -> BaseTransformer | None:
    """Get the transformer for a specific plugin."""
    return PLUGIN_REGISTRY.get(plugin_type, {}).get(plugin_name)


def is_supported(plugin_type: PluginType, plugin_name: str) -> bool:
    """Check if a plugin is supported for transformation."""
    return get_transformer(plugin_type, plugin_name) is not None


def get_migration_guidance(plugin_name: str) -> tuple[str, list[str]]:
    """Get migration guidance for an unsupported plugin."""
    template = UNSUPPORTED_GUIDANCE.get(
        plugin_name,
        {
            "guidance": f"The Logstash {plugin_name} plugin is not currently supported for automatic migration.\nPlease refer to Vector documentation for equivalent components.",
            "alternatives": ["Vector documentation: https://vector.dev/docs/"],
        },
    )
    return template["guidance"], template["alternatives"]  # type: ignore


def transform_config(
    logstash_config: LogstashConfiguration,
) -> tuple[VectorConfiguration, MigrationReport]:
    """
    Transform a Logstash configuration to Vector configuration.

    This orchestrator:
    1. Processes all plugins (inputs, filters, outputs)
    2. Detects unsupported plugins and creates placeholders
    3. Generates migration report with guidance
    4. Returns both the Vector config and migration report

    Returns:
        Tuple of (VectorConfiguration, MigrationReport)
    """
    sources: dict[str, VectorComponent] = {}
    transforms: dict[str, VectorComponent] = {}
    sinks: dict[str, VectorComponent] = {}

    supported_migrations: list[PluginMigration] = []
    unsupported_plugins: list[UnsupportedPlugin] = []

    # Track component IDs for input references
    source_ids: list[str] = []
    transform_ids: list[str] = []

    # Process inputs
    for idx, plugin in enumerate(logstash_config.inputs):
        component_id = f"{plugin.plugin_name}_input"
        if idx > 0:
            component_id = f"{component_id}_{idx}"

        transformer = get_transformer(PluginType.INPUT, plugin.plugin_name)

        if transformer:
            # Supported plugin - transform it
            component = transformer.transform(plugin)
            sources[component_id] = component
            source_ids.append(component_id)

            supported_migrations.append(
                PluginMigration(
                    logstash_plugin=plugin.plugin_name,
                    vector_components=[component_id],
                )
            )
        else:
            # Unsupported plugin - create placeholder
            guidance, alternatives = get_migration_guidance(plugin.plugin_name)

            unsupported_plugins.append(
                UnsupportedPlugin(
                    plugin_name=plugin.plugin_name,
                    plugin_type=PluginType.INPUT,
                    line_number=plugin.line_number,
                    original_config=_format_plugin_config(plugin),
                    manual_migration_guidance=guidance,
                    vector_alternatives=alternatives,
                )
            )

            # Create placeholder component with TODO marker
            placeholder_id = f"{plugin.plugin_name}_input_placeholder"
            if idx > 0:
                placeholder_id = f"{placeholder_id}_{idx}"

            sources[placeholder_id] = VectorComponent(
                component_type=ComponentType.SOURCE,
                component_kind=plugin.plugin_name,  # Keep original name
                config={},  # Empty config - needs manual configuration
                inputs=[],
                comments=[
                    f"TODO: Manual migration required for unsupported plugin '{plugin.plugin_name}' (input)",
                    "Original Logstash configuration:",
                    f"  {plugin.plugin_name} {{",
                    *[f"    {line}" for line in _format_plugin_config(plugin).split("\n")],
                    "  }",
                    "",
                    "Vector alternatives to consider:",
                    *[f"  - {alt}" for alt in alternatives],
                    "",
                    "Manual migration guidance:",
                    *[f"  {line}" for line in guidance.split("\n")],
                ],
            )
            source_ids.append(placeholder_id)

    # Process filters
    for idx, plugin in enumerate(logstash_config.filters):
        component_id = f"{plugin.plugin_name}_filter"
        if idx > 0:
            component_id = f"{component_id}_{idx}"

        transformer = get_transformer(PluginType.FILTER, plugin.plugin_name)

        if transformer:
            # Supported plugin - transform it
            component = transformer.transform(plugin)
            # Filters read from all sources/previous transforms
            component.inputs = source_ids + transform_ids
            transforms[component_id] = component
            transform_ids.append(component_id)

            supported_migrations.append(
                PluginMigration(
                    logstash_plugin=plugin.plugin_name,
                    vector_components=[component_id],
                )
            )
        else:
            # Unsupported plugin - create placeholder
            guidance, alternatives = get_migration_guidance(plugin.plugin_name)

            unsupported_plugins.append(
                UnsupportedPlugin(
                    plugin_name=plugin.plugin_name,
                    plugin_type=PluginType.FILTER,
                    line_number=plugin.line_number,
                    original_config=_format_plugin_config(plugin),
                    manual_migration_guidance=guidance,
                    vector_alternatives=alternatives,
                )
            )

            # Create placeholder transform with TODO marker
            placeholder_id = f"{plugin.plugin_name}_filter_placeholder"
            if idx > 0:
                placeholder_id = f"{placeholder_id}_{idx}"

            transforms[placeholder_id] = VectorComponent(
                component_type=ComponentType.TRANSFORM,
                component_kind="remap",  # Default to remap for filters
                config={"source": "# FIXME: Implement transformation logic"},
                inputs=source_ids + transform_ids,
                comments=[
                    f"TODO: Manual migration required for unsupported plugin '{plugin.plugin_name}' (filter)",
                    "Original Logstash configuration:",
                    f"  {plugin.plugin_name} {{",
                    *[f"    {line}" for line in _format_plugin_config(plugin).split("\n")],
                    "  }",
                    "",
                    "Vector alternatives to consider:",
                    *[f"  - {alt}" for alt in alternatives],
                    "",
                    "Manual migration guidance:",
                    *[f"  {line}" for line in guidance.split("\n")],
                ],
            )
            transform_ids.append(placeholder_id)

    # Process outputs
    for idx, plugin in enumerate(logstash_config.outputs):
        component_id = f"{plugin.plugin_name}_output"
        if idx > 0:
            component_id = f"{component_id}_{idx}"

        transformer = get_transformer(PluginType.OUTPUT, plugin.plugin_name)

        if transformer:
            # Supported plugin - transform it
            component = transformer.transform(plugin)
            # Sinks read from all transforms (or sources if no transforms)
            component.inputs = transform_ids if transform_ids else source_ids
            sinks[component_id] = component

            supported_migrations.append(
                PluginMigration(
                    logstash_plugin=plugin.plugin_name,
                    vector_components=[component_id],
                )
            )
        else:
            # Unsupported plugin - create placeholder
            guidance, alternatives = get_migration_guidance(plugin.plugin_name)

            unsupported_plugins.append(
                UnsupportedPlugin(
                    plugin_name=plugin.plugin_name,
                    plugin_type=PluginType.OUTPUT,
                    line_number=plugin.line_number,
                    original_config=_format_plugin_config(plugin),
                    manual_migration_guidance=guidance,
                    vector_alternatives=alternatives,
                )
            )

            # Create placeholder sink with TODO marker
            placeholder_id = f"{plugin.plugin_name}_output_placeholder"
            if idx > 0:
                placeholder_id = f"{placeholder_id}_{idx}"

            sinks[placeholder_id] = VectorComponent(
                component_type=ComponentType.SINK,
                component_kind=plugin.plugin_name,  # Keep original name
                config={},  # Empty config - needs manual configuration
                inputs=transform_ids if transform_ids else source_ids,
                comments=[
                    f"TODO: Manual migration required for unsupported plugin '{plugin.plugin_name}' (output)",
                    "Original Logstash configuration:",
                    f"  {plugin.plugin_name} {{",
                    *[f"    {line}" for line in _format_plugin_config(plugin).split("\n")],
                    "  }",
                    "",
                    "Vector alternatives to consider:",
                    *[f"  - {alt}" for alt in alternatives],
                    "",
                    "Manual migration guidance:",
                    *[f"  {line}" for line in guidance.split("\n")],
                ],
            )

    # Create Vector configuration
    vector_config = VectorConfiguration(
        file_path=logstash_config.file_path.with_suffix(".toml"),
        sources=sources,
        transforms=transforms,
        sinks=sinks,
        global_options={},
    )

    # Create migration report
    migration_report = MigrationReport(
        source_file=logstash_config.file_path,
        target_file=vector_config.file_path,
        supported_plugins=supported_migrations,
        unsupported_plugins=unsupported_plugins,
        errors=[],
        warnings=[],
    )

    return vector_config, migration_report


def _format_plugin_config(plugin: LogstashPlugin) -> str:
    """Format plugin configuration for display in reports."""
    lines = []
    for key, value in plugin.config.items():
        if isinstance(value, str):
            lines.append(f'{key} => "{value}"')
        elif isinstance(value, list):
            lines.append(f'{key} => {value}')
        elif isinstance(value, dict):
            lines.append(f"{key} => {value}")
        else:
            lines.append(f"{key} => {value}")
    return "\n".join(lines)


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
