"""Filter plugin transformers (Logstash filters → Vector transforms)."""

from lv_py.models import ComponentType
from lv_py.models.logstash_config import LogstashPlugin
from lv_py.models.vector_config import VectorComponent
from lv_py.transformers.base import BaseTransformer


class GrokFilterTransformer(BaseTransformer):
    """Transform Logstash grok filter to Vector remap transform with parse_groks()."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "grok"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash grok filter to Vector remap with parse_groks().

        Logstash grok:
            match => { "message" => "%{COMBINEDAPACHELOG}" }

        Vector remap:
            type = "remap"
            source = '''
            . = parse_groks!(.message, ["%{COMBINEDAPACHELOG}"])
            '''
        """
        config = plugin.config

        # Extract grok pattern
        match_config = config.get("match", {})

        # Build VRL source code
        vrl_lines = []

        if isinstance(match_config, dict):
            for field, pattern in match_config.items():
                # Convert pattern to list if it's a string
                patterns = [pattern] if isinstance(pattern, str) else pattern
                patterns_str = str(patterns)
                vrl_lines.append(f". = parse_groks!(.{field}, {patterns_str})")

        # If no match config, add a comment
        if not vrl_lines:
            vrl_lines.append("# TODO: Add grok patterns")

        vector_config = {
            "source": "\n".join(vrl_lines),
        }

        return VectorComponent(
            component_type=ComponentType.TRANSFORM,
            component_kind="remap",
            config=vector_config,
            inputs=[],  # Will be set by orchestrator
            comments=[],
        )


class MutateFilterTransformer(BaseTransformer):
    """Transform Logstash mutate filter to Vector remap transform."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "mutate"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash mutate filter to Vector remap.

        Logstash mutate:
            remove_field => ["temp_field"]
            rename => { "old_field" => "new_field" }
            add_field => { "new_field" => "value" }

        Vector remap:
            type = "remap"
            source = '''
            del(.temp_field)
            .new_field = .old_field
            del(.old_field)
            .new_field = "value"
            '''
        """
        config = plugin.config

        vrl_lines = []

        # Handle remove_field
        if "remove_field" in config:
            remove_fields = config["remove_field"]
            if isinstance(remove_fields, str):
                remove_fields = [remove_fields]
            for field in remove_fields:
                vrl_lines.append(f"del(.{field})")

        # Handle rename
        if "rename" in config:
            renames = config["rename"]
            if isinstance(renames, dict):
                for old_name, new_name in renames.items():
                    vrl_lines.append(f".{new_name} = .{old_name}")
                    vrl_lines.append(f"del(.{old_name})")

        # Handle add_field
        if "add_field" in config:
            add_fields = config["add_field"]
            if isinstance(add_fields, dict):
                for field_name, field_value in add_fields.items():
                    # Quote string values
                    if isinstance(field_value, str):
                        vrl_lines.append(f'.{field_name} = "{field_value}"')
                    else:
                        vrl_lines.append(f".{field_name} = {field_value}")

        # Handle convert (type conversion)
        if "convert" in config:
            converts = config["convert"]
            if isinstance(converts, dict):
                for field_name, target_type in converts.items():
                    type_map = {
                        "integer": "int",
                        "float": "float",
                        "string": "string",
                        "boolean": "bool",
                    }
                    vrl_type = type_map.get(target_type, "string")
                    vrl_lines.append(f".{field_name} = to_{vrl_type}!(.{field_name})")

        if not vrl_lines:
            vrl_lines.append("# TODO: Add mutate operations")

        vector_config = {
            "source": "\n".join(vrl_lines),
        }

        return VectorComponent(
            component_type=ComponentType.TRANSFORM,
            component_kind="remap",
            config=vector_config,
            inputs=[],  # Will be set by orchestrator
            comments=[],
        )


class DateFilterTransformer(BaseTransformer):
    """Transform Logstash date filter to Vector remap with parse_timestamp()."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "date"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash date filter to Vector remap with parse_timestamp().

        Logstash date:
            match => ["timestamp_field", "ISO8601"]
            target => "@timestamp"

        Vector remap:
            type = "remap"
            source = '''
            .@timestamp = parse_timestamp!(.timestamp_field, format: "%+")
            '''
        """
        config = plugin.config

        vrl_lines = []

        # Extract match configuration
        match_config = config.get("match", [])

        if isinstance(match_config, list) and len(match_config) >= 2:
            source_field = match_config[0]
            date_format = match_config[1]

            # Convert Logstash date format to strptime format
            format_map = {
                "ISO8601": "%+",  # ISO 8601 format
                "UNIX": "%s",  # Unix timestamp
                "UNIX_MS": "%s",  # Unix timestamp in milliseconds
            }

            vrl_format = format_map.get(date_format, date_format)

            # Determine target field
            target_field = config.get("target", "@timestamp")

            # Generate VRL
            vrl_lines.append(
                f'.{target_field} = parse_timestamp!(.{source_field}, format: "{vrl_format}")'
            )
        else:
            vrl_lines.append("# TODO: Configure date parsing")

        vector_config = {
            "source": "\n".join(vrl_lines),
        }

        return VectorComponent(
            component_type=ComponentType.TRANSFORM,
            component_kind="remap",
            config=vector_config,
            inputs=[],  # Will be set by orchestrator
            comments=[],
        )
