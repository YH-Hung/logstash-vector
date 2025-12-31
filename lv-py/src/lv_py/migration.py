"""Migration orchestration - coordinates parsing, transformation, and generation."""

from datetime import datetime
from pathlib import Path

from lv_py.models.logstash_config import LogstashConfiguration
from lv_py.models.migration_report import (
    MigrationError,
    MigrationReport,
    PluginMigration,
    UnsupportedPlugin,
)
from lv_py.models.vector_config import VectorComponent, VectorConfiguration
from lv_py.models import ComponentType, ErrorType
from lv_py.parser.logstash_parser import parse_file
from lv_py.transformers import get_transformer


def migrate_config(
    logstash_conf_path: Path, output_path: Path | None = None
) -> tuple[VectorConfiguration | None, MigrationReport]:
    """
    Migrate a Logstash configuration to Vector format.

    Args:
        logstash_conf_path: Path to Logstash .conf file
        output_path: Optional custom output path (defaults to same dir with .toml extension)

    Returns:
        Tuple of (VectorConfiguration | None, MigrationReport)
    """
    # Determine output path
    if output_path is None:
        output_path = logstash_conf_path.with_suffix(".toml")

    # Initialize report tracking
    supported_plugins: list[PluginMigration] = []
    unsupported_plugins: list[UnsupportedPlugin] = []
    errors: list[MigrationError] = []
    warnings: list[str] = []

    try:
        # Parse Logstash configuration
        logstash_config = parse_file(logstash_conf_path)
    except ValueError as e:
        # Parsing failed
        errors.append(
            MigrationError(
                error_type=ErrorType.PARSE_ERROR,
                message=str(e),
                file_path=logstash_conf_path,
                details=None,
            )
        )
        report = MigrationReport(
            source_file=logstash_conf_path,
            target_file=output_path,
            timestamp=datetime.utcnow(),
            supported_plugins=supported_plugins,
            unsupported_plugins=unsupported_plugins,
            errors=errors,
            warnings=warnings,
        )
        return None, report

    # Transform plugins to Vector components
    sources: dict[str, VectorComponent] = {}
    transforms: dict[str, VectorComponent] = {}
    sinks: dict[str, VectorComponent] = {}

    # Keep track of component IDs for chaining
    source_ids: list[str] = []
    transform_ids: list[str] = []

    # Transform inputs → sources
    for idx, input_plugin in enumerate(logstash_config.inputs):
        transformer = get_transformer(input_plugin.plugin_type, input_plugin.plugin_name)

        if transformer is None:
            # Unsupported plugin
            unsupported_plugins.append(
                UnsupportedPlugin(
                    plugin_name=input_plugin.plugin_name,
                    plugin_type=input_plugin.plugin_type,
                    line_number=input_plugin.line_number,
                    original_config=str(input_plugin.config),
                    manual_migration_guidance=f"The '{input_plugin.plugin_name}' input plugin is not currently supported. Please refer to Vector documentation for equivalent source types.",
                    vector_alternatives=["file", "socket", "http"],
                )
            )
            continue

        try:
            component = transformer.transform(input_plugin)
            component_id = f"{input_plugin.plugin_name}_input_{idx}"
            sources[component_id] = component
            source_ids.append(component_id)

            supported_plugins.append(
                PluginMigration(
                    logstash_plugin=f"{input_plugin.plugin_name} (input)",
                    vector_components=[component_id],
                    notes=f"Migrated to Vector {component.component_kind} source",
                )
            )
        except Exception as e:
            errors.append(
                MigrationError(
                    error_type=ErrorType.TRANSFORMATION_ERROR,
                    message=f"Failed to transform {input_plugin.plugin_name} input",
                    file_path=logstash_conf_path,
                    line_number=input_plugin.line_number,
                    details=str(e),
                )
            )

    # Transform filters → transforms
    for idx, filter_plugin in enumerate(logstash_config.filters):
        transformer = get_transformer(filter_plugin.plugin_type, filter_plugin.plugin_name)

        if transformer is None:
            unsupported_plugins.append(
                UnsupportedPlugin(
                    plugin_name=filter_plugin.plugin_name,
                    plugin_type=filter_plugin.plugin_type,
                    line_number=filter_plugin.line_number,
                    original_config=str(filter_plugin.config),
                    manual_migration_guidance=f"The '{filter_plugin.plugin_name}' filter plugin is not currently supported. Consider using Vector's remap transform with VRL.",
                    vector_alternatives=["remap", "filter"],
                )
            )
            continue

        try:
            component = transformer.transform(filter_plugin)
            component_id = f"{filter_plugin.plugin_name}_filter_{idx}"

            # Set inputs to previous stage (sources or previous transforms)
            if transform_ids:
                component.inputs = [transform_ids[-1]]
            else:
                component.inputs = source_ids

            transforms[component_id] = component
            transform_ids.append(component_id)

            supported_plugins.append(
                PluginMigration(
                    logstash_plugin=f"{filter_plugin.plugin_name} (filter)",
                    vector_components=[component_id],
                    notes=f"Migrated to Vector {component.component_kind} transform",
                )
            )
        except Exception as e:
            errors.append(
                MigrationError(
                    error_type=ErrorType.TRANSFORMATION_ERROR,
                    message=f"Failed to transform {filter_plugin.plugin_name} filter",
                    file_path=logstash_conf_path,
                    line_number=filter_plugin.line_number,
                    details=str(e),
                )
            )

    # Transform outputs → sinks
    for idx, output_plugin in enumerate(logstash_config.outputs):
        transformer = get_transformer(output_plugin.plugin_type, output_plugin.plugin_name)

        if transformer is None:
            unsupported_plugins.append(
                UnsupportedPlugin(
                    plugin_name=output_plugin.plugin_name,
                    plugin_type=output_plugin.plugin_type,
                    line_number=output_plugin.line_number,
                    original_config=str(output_plugin.config),
                    manual_migration_guidance=f"The '{output_plugin.plugin_name}' output plugin is not currently supported. Please refer to Vector documentation for equivalent sink types.",
                    vector_alternatives=["elasticsearch", "file", "console", "http"],
                )
            )
            continue

        try:
            component = transformer.transform(output_plugin)
            component_id = f"{output_plugin.plugin_name}_output_{idx}"

            # Set inputs to last stage (transforms or sources)
            if transform_ids:
                component.inputs = [transform_ids[-1]]
            else:
                component.inputs = source_ids

            sinks[component_id] = component

            supported_plugins.append(
                PluginMigration(
                    logstash_plugin=f"{output_plugin.plugin_name} (output)",
                    vector_components=[component_id],
                    notes=f"Migrated to Vector {component.component_kind} sink",
                )
            )
        except Exception as e:
            errors.append(
                MigrationError(
                    error_type=ErrorType.TRANSFORMATION_ERROR,
                    message=f"Failed to transform {output_plugin.plugin_name} output",
                    file_path=logstash_conf_path,
                    line_number=output_plugin.line_number,
                    details=str(e),
                )
            )

    # Create VectorConfiguration if we have at least one source and one sink
    vector_config = None
    if sources and sinks:
        try:
            vector_config = VectorConfiguration(
                file_path=output_path,
                sources=sources,
                transforms=transforms,
                sinks=sinks,
                global_options={},
            )
        except Exception as e:
            errors.append(
                MigrationError(
                    error_type=ErrorType.VALIDATION_ERROR,
                    message="Failed to create Vector configuration",
                    file_path=logstash_conf_path,
                    details=str(e),
                )
            )
    elif not sources:
        errors.append(
            MigrationError(
                error_type=ErrorType.TRANSFORMATION_ERROR,
                message="No source components generated - cannot create valid Vector config",
                file_path=logstash_conf_path,
            )
        )
    elif not sinks:
        errors.append(
            MigrationError(
                error_type=ErrorType.TRANSFORMATION_ERROR,
                message="No sink components generated - cannot create valid Vector config",
                file_path=logstash_conf_path,
            )
        )

    # Create migration report
    report = MigrationReport(
        source_file=logstash_conf_path,
        target_file=output_path,
        timestamp=datetime.utcnow(),
        supported_plugins=supported_plugins,
        unsupported_plugins=unsupported_plugins,
        errors=errors,
        warnings=warnings,
    )

    return vector_config, report
