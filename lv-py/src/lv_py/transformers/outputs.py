"""Output plugin transformers (Logstash outputs → Vector sinks)."""

from typing import Any

from lv_py.models import ComponentType
from lv_py.models.logstash_config import LogstashPlugin
from lv_py.models.vector_config import VectorComponent
from lv_py.transformers.base import BaseTransformer


class ElasticsearchOutputTransformer(BaseTransformer):
    """Transform Logstash elasticsearch output to Vector elasticsearch sink."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "elasticsearch"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash elasticsearch output to Vector elasticsearch sink.

        Logstash elasticsearch:
            hosts => ["localhost:9200"]
            index => "logstash-%{+YYYY.MM.dd}"
            user => "elastic"
            password => "changeme"

        Vector elasticsearch:
            type = "elasticsearch"
            endpoints = ["http://localhost:9200"]
            mode = "bulk"
            auth.strategy = "basic"
            auth.user = "elastic"
            auth.password = "changeme"
        """
        config = plugin.config

        vector_config: dict[str, Any] = {}

        # Map hosts to endpoints
        if "hosts" in config:
            hosts = config["hosts"]
            if isinstance(hosts, str):
                hosts = [hosts]

            # Ensure HTTP scheme is present
            endpoints = []
            for host in hosts:
                if not host.startswith("http://") and not host.startswith("https://"):
                    host = f"http://{host}"
                endpoints.append(host)

            vector_config["endpoints"] = endpoints
        else:
            vector_config["endpoints"] = ["http://localhost:9200"]

        # Set bulk mode (Vector default for Elasticsearch)
        mode_value: str = "bulk"
        vector_config["mode"] = mode_value

        # Map index (note: Vector uses different templating)
        if "index" in config:
            index = config["index"]
            # Logstash uses %{+FORMAT} for date formatting
            # Vector doesn't support this directly - use static index or add comment
            if "%{" in index:
                # Comment will be added below at lines 78-81
                vector_config["index"] = index.split("%{")[0].rstrip("-")  # Use base name
            else:
                vector_config["index"] = index

        # Handle authentication
        if "user" in config or "password" in config:
            auth_config: dict[str, str] = {
                "strategy": "basic",
                "user": config.get("user", "elastic"),
                "password": config.get("password", ""),
            }
            vector_config["auth"] = auth_config

        comments = []
        if "index" in config and "%{" in config["index"]:
            comments.append(
                f"TODO: Convert Logstash index template '{config['index']}' to Vector format"
            )

        return VectorComponent(
            component_type=ComponentType.SINK,
            component_kind="elasticsearch",
            config=vector_config,
            inputs=[],  # Will be set by orchestrator
            comments=comments,
        )


class FileOutputTransformer(BaseTransformer):
    """Transform Logstash file output to Vector file sink."""

    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        return plugin_name == "file"

    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform Logstash file output to Vector file sink.

        Logstash file:
            path => "/var/log/output.log"
            codec => "json_lines"

        Vector file:
            type = "file"
            path = "/var/log/output.log"
            encoding.codec = "json"
        """
        config = plugin.config

        vector_config: dict[str, Any] = {}

        # Map path
        if "path" in config:
            vector_config["path"] = config["path"]
        else:
            vector_config["path"] = "/var/log/vector-output.log"

        # Map codec
        codec = config.get("codec", "json_lines")

        # Map Logstash codecs to Vector encodings
        codec_map = {
            "json": "json",
            "json_lines": "json",
            "line": "text",
            "plain": "text",
            "rubydebug": "json",  # Approximate
        }

        vector_codec = codec_map.get(codec, "json")
        vector_config["encoding"] = {"codec": vector_codec}

        return VectorComponent(
            component_type=ComponentType.SINK,
            component_kind="file",
            config=vector_config,
            inputs=[],  # Will be set by orchestrator
            comments=[],
        )
