"""Input plugin transformers (Logstash inputs → Vector sources)."""

from lv_py.models import ComponentType
from lv_py.models.logstash_config import LogstashPlugin
from lv_py.models.vector_config import VectorComponent
from lv_py.transformers.base import BaseTransformer


class FileInputTransformer(BaseTransformer):
    """Transform Logstash file input to Vector file source."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "file"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash file input to Vector file source.

        Logstash file input config:
            path => "/var/log/*.log"
            start_position => "beginning"
            sincedb_path => "/dev/null"

        Vector file source config:
            type = "file"
            include = ["/var/log/*.log"]
            read_from = "beginning"
        """
        config = plugin.config

        # Build Vector config
        vector_config = {}

        # Map path to include (Vector uses array)
        if "path" in config:
            path_value = config["path"]
            # If it's a string, convert to list
            if isinstance(path_value, str):
                vector_config["include"] = [path_value]
            elif isinstance(path_value, list):
                vector_config["include"] = path_value
        else:
            vector_config["include"] = ["/var/log/*.log"]  # Default

        # Map start_position to read_from
        start_position = config.get("start_position", "end")
        if start_position == "beginning":
            vector_config["read_from"] = "beginning"
        else:
            vector_config["read_from"] = "end"

        # Optionally map other fields
        if "tags" in config:
            # Add as metadata in comments since Vector handles this differently
            pass

        return VectorComponent(
            component_type=ComponentType.SOURCE,
            component_kind="file",
            config=vector_config,
            inputs=[],
            comments=[],
        )


class BeatsInputTransformer(BaseTransformer):
    """Transform Logstash beats input to Vector HTTP source."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "beats"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash beats input to Vector HTTP or socket source.

        Logstash beats input:
            port => 5044
            host => "0.0.0.0"

        Vector equivalent (using socket source for Lumberjack protocol):
            type = "socket"
            address = "0.0.0.0:5044"
            mode = "tcp"
        """
        config = plugin.config

        # Build Vector config
        port = config.get("port", 5044)
        host = config.get("host", "0.0.0.0")
        address = f"{host}:{port}"

        vector_config = {
            "address": address,
            "mode": "tcp",
        }

        comments = [
            "NOTE: Beats input migrated to TCP socket",
            "For full Beats protocol support, consider using Filebeat → Vector directly",
        ]

        return VectorComponent(
            component_type=ComponentType.SOURCE,
            component_kind="socket",
            config=vector_config,
            inputs=[],
            comments=comments,
        )
