"""Unit tests for plugin transformers."""


from lv_py.models import ComponentType, PluginType
from lv_py.models.logstash_config import LogstashPlugin
from lv_py.transformers.filters import (
    DateFilterTransformer,
    GrokFilterTransformer,
    MutateFilterTransformer,
)
from lv_py.transformers.inputs import BeatsInputTransformer, FileInputTransformer
from lv_py.transformers.outputs import ElasticsearchOutputTransformer, FileOutputTransformer


class TestFileInputTransformer:
    """Tests for file input transformer."""

    def test_supports_file_plugin(self):
        """Test that transformer recognizes file plugin."""
        transformer = FileInputTransformer()
        assert transformer.supports("file") is True
        assert transformer.supports("beats") is False

    def test_transform_basic_config(self):
        """Test transformation of basic file input config."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.INPUT,
            plugin_name="file",
            config={
                "path": "/var/log/app.log",
                "start_position": "beginning",
            },
            line_number=1,
        )

        transformer = FileInputTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.SOURCE
        assert component.component_kind == "file"
        assert "include" in component.config
        assert component.config["include"] == ["/var/log/app.log"]
        assert component.config["read_from"] == "beginning"

class TestBeatsInputTransformer:
    """Tests for beats input transformer."""

    def test_supports_beats_plugin(self):
        """Test that transformer recognizes beats plugin."""
        transformer = BeatsInputTransformer()
        assert transformer.supports("beats") is True
        assert transformer.supports("file") is False

    def test_transform_basic_config(self):
        """Test transformation of basic beats input config."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.INPUT,
            plugin_name="beats",
            config={
                "port": 5044,
                "host": "0.0.0.0",
            },
            line_number=1,
        )

        transformer = BeatsInputTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.SOURCE
        assert component.component_kind == "socket"
        assert component.config["mode"] == "tcp"
        assert component.config["address"] == "0.0.0.0:5044"


class TestGrokFilterTransformer:
    """Tests for grok filter transformer."""

    def test_supports_grok_plugin(self):
        """Test that transformer recognizes grok plugin."""
        transformer = GrokFilterTransformer()
        assert transformer.supports("grok") is True
        assert transformer.supports("mutate") is False

    def test_transform_with_match_dict(self):
        """Test transformation of grok filter with match dict."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.FILTER,
            plugin_name="grok",
            config={
                "match": {"message": "%{COMBINEDAPACHELOG}"}
            },
            line_number=1,
        )

        transformer = GrokFilterTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.TRANSFORM
        assert component.component_kind == "remap"
        assert "source" in component.config
        assert "parse_groks" in component.config["source"]
        assert "%{COMBINEDAPACHELOG}" in component.config["source"]


class TestMutateFilterTransformer:
    """Tests for mutate filter transformer."""

    def test_supports_mutate_plugin(self):
        """Test that transformer recognizes mutate plugin."""
        transformer = MutateFilterTransformer()
        assert transformer.supports("mutate") is True
        assert transformer.supports("grok") is False

    def test_transform_remove_field(self):
        """Test transformation of mutate filter with remove_field."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.FILTER,
            plugin_name="mutate",
            config={
                "remove_field": ["temp", "debug"]
            },
            line_number=1,
        )

        transformer = MutateFilterTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.TRANSFORM
        assert component.component_kind == "remap"
        assert "source" in component.config
        assert "del(.temp)" in component.config["source"]
        assert "del(.debug)" in component.config["source"]


class TestDateFilterTransformer:
    """Tests for date filter transformer."""

    def test_supports_date_plugin(self):
        """Test that transformer recognizes date plugin."""
        transformer = DateFilterTransformer()
        assert transformer.supports("date") is True
        assert transformer.supports("mutate") is False

    def test_transform_basic_config(self):
        """Test transformation of basic date filter config."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.FILTER,
            plugin_name="date",
            config={
                "match": ["timestamp", "ISO8601"]
            },
            line_number=1,
        )

        transformer = DateFilterTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.TRANSFORM
        assert component.component_kind == "remap"
        assert "source" in component.config
        assert "parse_timestamp" in component.config["source"]
        assert ".timestamp" in component.config["source"]


class TestElasticsearchOutputTransformer:
    """Tests for elasticsearch output transformer."""

    def test_supports_elasticsearch_plugin(self):
        """Test that transformer recognizes elasticsearch plugin."""
        transformer = ElasticsearchOutputTransformer()
        assert transformer.supports("elasticsearch") is True
        assert transformer.supports("file") is False

    def test_transform_basic_config(self):
        """Test transformation of basic elasticsearch output config."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.OUTPUT,
            plugin_name="elasticsearch",
            config={
                "hosts": ["http://localhost:9200"],
                "index": "logs-%{+YYYY.MM.dd}",
            },
            line_number=1,
        )

        transformer = ElasticsearchOutputTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.SINK
        assert component.component_kind == "elasticsearch"
        assert "endpoints" in component.config
        assert component.config["endpoints"] == ["http://localhost:9200"]
        assert "index" in component.config


class TestFileOutputTransformer:
    """Tests for file output transformer."""

    def test_supports_file_plugin(self):
        """Test that transformer recognizes file plugin."""
        transformer = FileOutputTransformer()
        assert transformer.supports("file") is True
        assert transformer.supports("elasticsearch") is False

    def test_transform_basic_config(self):
        """Test transformation of basic file output config."""
        plugin = LogstashPlugin(
            plugin_type=PluginType.OUTPUT,
            plugin_name="file",
            config={
                "path": "/var/log/output.log",
                "codec": "json",
            },
            line_number=1,
        )

        transformer = FileOutputTransformer()
        component = transformer.transform(plugin)

        assert component.component_type == ComponentType.SINK
        assert component.component_kind == "file"
        assert "path" in component.config
        assert component.config["path"] == "/var/log/output.log"
