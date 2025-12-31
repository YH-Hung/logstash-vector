"""High-level API functions for migration, validation, and diff operations."""

from pathlib import Path

from lv_py.migration import migrate_config
from lv_py.models.migration_report import (
    ComponentMapping,
    DiffResult,
    MigrationPreview,
    MigrationResult,
    TransformationPreview,
    ValidationResult,
    ValidationResults,
)
from lv_py.parser.logstash_parser import parse_file
from lv_py.utils.file_utils import find_conf_files
from lv_py.utils.validation import validate_vector_config


def migrate_directory(
    directory: Path,
    output_dir: Path | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
    validate: bool = True,
    verbose: bool = False,
) -> MigrationResult:
    """
    Migrate all Logstash configs in a directory to Vector format.

    Args:
        directory: Directory containing .conf files
        output_dir: Optional output directory (defaults to same as input)
        dry_run: If True, only preview without writing files
        overwrite: If True, overwrite existing files without confirmation
        validate: If True, validate generated configs with vector
        verbose: If True, show detailed progress information

    Returns:
        MigrationResult with previews or reports depending on mode
    """
    # Find all .conf files
    conf_files = find_conf_files(directory)

    result = MigrationResult(
        is_dry_run=dry_run,
        total_files=len(conf_files),
    )

    for conf_file in conf_files:
        # Determine output path
        if output_dir:
            output_path = output_dir / conf_file.with_suffix(".toml").name
        else:
            output_path = conf_file.with_suffix(".toml")

        # Check for existing files and prompt for overwrite if needed
        if not dry_run and output_path.exists() and not overwrite:
            from rich.prompt import Confirm
            if not Confirm.ask(f"File {output_path} already exists. Overwrite?", default=False):
                result.failed += 1
                continue

        if dry_run:
            # Dry-run mode: create preview
            try:
                vector_config, migration_report = migrate_config(conf_file, output_path)

                # Estimate file size
                toml_content = vector_config.to_toml() if vector_config else ""
                estimated_size = len(toml_content.encode("utf-8"))

                # Extract transformations
                transformations = [
                    TransformationPreview(
                        logstash_plugin=plugin.logstash_plugin,
                        vector_component=", ".join(plugin.vector_components),
                        notes=plugin.notes,
                    )
                    for plugin in migration_report.supported_plugins
                ]

                preview = MigrationPreview(
                    source_file=conf_file,
                    target_file=output_path,
                    estimated_size=estimated_size,
                    transformations=transformations,
                    unsupported_plugins=migration_report.unsupported_plugins,
                    notes=(
                        "Contains unsupported features - review TODO markers"
                        if migration_report.unsupported_plugins
                        else ""
                    ),
                )
                result.previews.append(preview)

                if not migration_report.errors:
                    result.successful += 1
                else:
                    result.failed += 1

            except Exception:
                result.failed += 1

        else:
            # Live mode: perform migration
            try:
                vector_config, migration_report = migrate_config(conf_file, output_path)
                result.reports.append(migration_report)

                if vector_config and not migration_report.errors:
                    # Write TOML file
                    toml_content = vector_config.to_toml()
                    output_path.write_text(toml_content)

                    # Validate if requested
                    if validate:
                        is_valid, error_msg = validate_vector_config(output_path)
                        if not is_valid:
                            # Add validation error to report
                            from lv_py.models.migration_report import ErrorType, MigrationError
                            validation_error = MigrationError(
                                error_type=ErrorType.VALIDATION_ERROR,
                                message=f"Vector validation failed: {error_msg}",
                                file_path=output_path,
                                line_number=None,
                                details=error_msg
                            )
                            migration_report.errors.append(validation_error)
                            result.failed += 1
                        else:
                            result.successful += 1
                    else:
                        result.successful += 1
                else:
                    result.failed += 1

            except Exception as e:
                if verbose:
                    import traceback
                    print(f"Error migrating {conf_file}: {e}")
                    traceback.print_exc()
                result.failed += 1

    return result


def validate_configs(
    files: list[Path], use_glob: bool = False
) -> ValidationResults:
    """
    Validate Vector TOML configuration files.

    Args:
        files: List of .toml files to validate
        use_glob: If True, treat paths as glob patterns

    Returns:
        ValidationResults with validation status for each file
    """
    results = ValidationResults()

    # Expand glob patterns if needed
    all_files: list[Path] = []
    if use_glob:
        for pattern in files:
            if "*" in str(pattern):
                all_files.extend(pattern.parent.glob(pattern.name))
            else:
                all_files.append(pattern)
    else:
        all_files = list(files)

    # Validate each file
    for file_path in all_files:
        is_valid, error_msg = validate_vector_config(file_path)

        validation_result = ValidationResult(
            file_path=file_path,
            is_valid=is_valid,
            error_message=error_msg if not is_valid else "",
        )
        results.validation_results.append(validation_result)

        if not is_valid:
            results.all_valid = False

    # Set exit code
    results.exit_code = 0 if results.all_valid else 1

    return results


def diff_configs(logstash_config: Path, vector_config: Path) -> DiffResult:
    """
    Compare Logstash and Vector configurations.

    Args:
        logstash_config: Path to Logstash .conf file
        vector_config: Path to Vector .toml file

    Returns:
        DiffResult with component mappings and differences
    """
    # Parse Logstash config
    logstash_cfg = parse_file(logstash_config)

    # Parse Vector config (need to read TOML)
    import tomlkit

    vector_data = tomlkit.loads(vector_config.read_text())

    result = DiffResult(
        logstash_file=logstash_config,
        vector_file=vector_config,
    )

    # Map inputs to sources
    for input_plugin in logstash_cfg.inputs:
        # Find corresponding Vector source
        vector_sources = vector_data.get("sources", {})
        # Simple heuristic: find source with similar name
        matching_source = None
        for source_id, source_config in vector_sources.items():
            if input_plugin.plugin_name in source_id or source_id in str(
                input_plugin.config
            ):
                matching_source = source_id
                break

        if matching_source:
            mapping = ComponentMapping(
                logstash_plugin=f"{input_plugin.plugin_name} input",
                vector_component=f"sources.{matching_source}",
                notes=f"Maps to {vector_sources[matching_source].get('type', 'unknown')} source",
            )
            result.input_mappings.append(mapping)
        elif not input_plugin.supported:
            # Add to unsupported features
            result.unsupported_features.extend(
                [
                    up
                    for up in []
                    if up.plugin_name == input_plugin.plugin_name
                ]
            )

    # Map filters to transforms
    for filter_plugin in logstash_cfg.filters:
        vector_transforms = vector_data.get("transforms", {})
        matching_transform = None

        for transform_id, transform_config in vector_transforms.items():
            if filter_plugin.plugin_name in transform_id or transform_id in str(
                filter_plugin.config
            ):
                matching_transform = transform_id
                break

        if matching_transform:
            mapping = ComponentMapping(
                logstash_plugin=f"{filter_plugin.plugin_name} filter",
                vector_component=f"transforms.{matching_transform}",
                notes=f"Maps to {vector_transforms[matching_transform].get('type', 'unknown')} transform",
            )
            result.filter_mappings.append(mapping)

    # Map outputs to sinks
    for output_plugin in logstash_cfg.outputs:
        vector_sinks = vector_data.get("sinks", {})
        matching_sink = None

        for sink_id, sink_config in vector_sinks.items():
            if output_plugin.plugin_name in sink_id or sink_id in str(
                output_plugin.config
            ):
                matching_sink = sink_id
                break

        if matching_sink:
            mapping = ComponentMapping(
                logstash_plugin=f"{output_plugin.plugin_name} output",
                vector_component=f"sinks.{matching_sink}",
                notes=f"Maps to {vector_sinks[matching_sink].get('type', 'unknown')} sink",
            )
            result.output_mappings.append(mapping)

    return result
