"""Unit tests for Logstash parser."""

import tempfile
from pathlib import Path

import pytest

from lv_py.models import PluginType
from lv_py.parser.logstash_parser import parse_file


def test_parse_empty_file():
    """Test parsing an empty Logstash configuration."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write("")
        temp_path = Path(f.name)

    try:
        # Empty file should raise an error or return empty config
        with pytest.raises(Exception):
            parse_file(temp_path)
    finally:
        temp_path.unlink()


def test_parse_simple_input_block():
    """Test parsing a simple input block."""
    config_content = '''
input {
  file {
    path => "/var/log/*.log"
    start_position => "beginning"
  }
}

output {
  file {
    path => "/tmp/output.log"
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        result = parse_file(temp_path)

        # Check that we have 1 input and 1 output
        assert len(result.inputs) == 1
        assert len(result.outputs) == 1
        assert len(result.filters) == 0

        # Check input plugin
        file_input = result.inputs[0]
        assert file_input.plugin_name == "file"
        assert file_input.plugin_type == PluginType.INPUT
        assert file_input.config["path"] == "/var/log/*.log"
        assert file_input.config["start_position"] == "beginning"
    finally:
        temp_path.unlink()


def test_parse_filter_block():
    """Test parsing filter blocks."""
    config_content = '''
input {
  file {
    path => "/var/log/*.log"
  }
}

filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
  mutate {
    remove_field => ["temp"]
  }
}

output {
  file {
    path => "/tmp/output.log"
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        result = parse_file(temp_path)

        # Check that we have filters
        assert len(result.filters) == 2

        # Check grok filter
        grok_filter = result.filters[0]
        assert grok_filter.plugin_name == "grok"
        assert grok_filter.plugin_type == PluginType.FILTER

        # Check mutate filter
        mutate_filter = result.filters[1]
        assert mutate_filter.plugin_name == "mutate"
        assert mutate_filter.plugin_type == PluginType.FILTER
    finally:
        temp_path.unlink()


def test_parse_output_block():
    """Test parsing output blocks."""
    config_content = '''
input {
  file {
    path => "/var/log/*.log"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "logstash-%{+YYYY.MM.dd}"
    user => "elastic"
    password => "changeme"
  }
  file {
    path => "/tmp/output.log"
    codec => "json_lines"
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        result = parse_file(temp_path)

        # Check that we have 2 outputs
        assert len(result.outputs) == 2

        # Check elasticsearch output
        es_output = result.outputs[0]
        assert es_output.plugin_name == "elasticsearch"
        assert es_output.plugin_type == PluginType.OUTPUT
        assert "hosts" in es_output.config
        assert "index" in es_output.config

        # Check file output
        file_output = result.outputs[1]
        assert file_output.plugin_name == "file"
        assert file_output.config["path"] == "/tmp/output.log"
    finally:
        temp_path.unlink()


def test_parse_multiline_config():
    """Test parsing configuration with multiple blocks."""
    config_content = '''
input {
  file {
    path => "/var/log/syslog"
  }
  beats {
    port => 5044
  }
}

filter {
  grok {
    match => { "message" => "%{SYSLOGLINE}" }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        result = parse_file(temp_path)

        # Check all sections are parsed
        assert len(result.inputs) == 2
        assert len(result.filters) == 1
        assert len(result.outputs) == 1

        # Check input plugins
        assert result.inputs[0].plugin_name == "file"
        assert result.inputs[1].plugin_name == "beats"

        # Check filter plugin
        assert result.filters[0].plugin_name == "grok"

        # Check output plugin
        assert result.outputs[0].plugin_name == "elasticsearch"
    finally:
        temp_path.unlink()


def test_parse_conditionals():
    """Test parsing Logstash conditionals."""
    # Note: Conditionals support is marked as TODO in the parser
    # This test documents expected behavior when implemented
    config_content = '''
input {
  file {
    path => "/var/log/*.log"
  }
}

filter {
  if [type] == "apache" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
  }
}

output {
  file {
    path => "/tmp/output.log"
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        # Parser should still work even with conditionals (though may not fully support them)
        result = parse_file(temp_path)
        assert len(result.inputs) == 1
        assert len(result.outputs) == 1
        # Filter parsing with conditionals may vary - just check it doesn't crash
    finally:
        temp_path.unlink()


def test_parse_invalid_syntax():
    """Test error handling for invalid Logstash syntax."""
    config_content = '''
input {
  file {
    path => "/var/log/*.log"
    # Missing closing brace
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        # Should raise an error for invalid syntax
        with pytest.raises(Exception):
            parse_file(temp_path)
    finally:
        temp_path.unlink()


def test_parse_nonexistent_file():
    """Test error when file doesn't exist."""
    with pytest.raises(Exception):
        parse_file(Path("/nonexistent/path/to/file.conf"))


def test_parse_array_values():
    """Test parsing array values in configuration."""
    config_content = '''
input {
  file {
    path => ["/var/log/syslog", "/var/log/messages"]
  }
}

output {
  elasticsearch {
    hosts => ["es1:9200", "es2:9200", "es3:9200"]
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        result = parse_file(temp_path)

        # Check array parsing
        file_input = result.inputs[0]
        assert isinstance(file_input.config["path"], list)
        assert len(file_input.config["path"]) == 2

        es_output = result.outputs[0]
        assert isinstance(es_output.config["hosts"], list)
        assert len(es_output.config["hosts"]) == 3
    finally:
        temp_path.unlink()


def test_parse_comments():
    """Test that comments are properly ignored."""
    config_content = '''
# This is a comment
input {
  file {
    # Comment inside block
    path => "/var/log/*.log"
  }
}

output {
  file {
    path => "/tmp/output.log"
  }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    try:
        result = parse_file(temp_path)

        # Should parse successfully ignoring comments
        assert len(result.inputs) == 1
        assert len(result.outputs) == 1
        # Note: Inline comments within values may not be fully supported yet
        assert "/var/log/*.log" in result.inputs[0].config["path"]
    finally:
        temp_path.unlink()
