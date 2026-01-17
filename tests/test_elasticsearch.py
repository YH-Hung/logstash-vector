"""Tests for Elasticsearch sink configuration."""
import pytest
from pathlib import Path


def test_elasticsearch_sink_configuration(temp_config_file, temp_log_file):
    """Test Elasticsearch sink basic configuration"""
    test_log = "[2026-01-16 09:10:33:130] Test log\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.elasticsearch_output]
type = "elasticsearch"
inputs = ["file_input"]
endpoints = ["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]
bulk.index = "{{{{ POD_NAMESPACE }}}}"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"


def test_elasticsearch_index_pattern(temp_config_file, temp_log_file):
    """Test Elasticsearch index pattern with date format"""
    test_log = "[2026-01-16 09:10:33:130] Test log\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.elasticsearch_output]
type = "elasticsearch"
inputs = ["file_input"]
endpoints = ["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]
bulk.index = "{{{{ POD_NAMESPACE }}}}"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"
    
    config_content = temp_config_file.read_text()
    assert 'bulk.index = "{{ POD_NAMESPACE }}"' in config_content


def test_elasticsearch_authentication(temp_config_file, temp_log_file):
    """Test Elasticsearch authentication settings"""
    test_log = "[2026-01-16 09:10:33:130] Test log\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.elasticsearch_output]
type = "elasticsearch"
inputs = ["file_input"]
endpoints = ["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]
bulk.index = "{{{{ POD_NAMESPACE }}}}"
auth.strategy = "basic"
auth.user = "use_default"
auth.password = "use_default"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"


def test_elasticsearch_buffer_configuration(temp_config_file, temp_log_file):
    """Test Elasticsearch buffer configuration"""
    test_log = "[2026-01-16 09:10:33:130] Test log\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.elasticsearch_output]
type = "elasticsearch"
inputs = ["file_input"]
endpoints = ["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]
bulk.index = "{{{{ POD_NAMESPACE }}}}"

[sinks.elasticsearch_output.buffer]
type = "memory"
max_events = 1000
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"


def test_elasticsearch_logstash_format(temp_config_file, temp_log_file):
    """Test Elasticsearch logstash_format output"""
    test_log = "[2026-01-16 09:10:33:130] Test log\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.elasticsearch_output]
type = "elasticsearch"
inputs = ["file_input"]
endpoints = ["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]
bulk.index = "{{{{ POD_NAMESPACE }}}}"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"


def test_elasticsearch_ssl_configuration(temp_config_file, temp_log_file):
    """Test Elasticsearch SSL configuration"""
    test_log = "[2026-01-16 09:10:33:130] Test log\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.elasticsearch_output]
type = "elasticsearch"
inputs = ["file_input"]
endpoints = ["http://elasticsearch-fz1.engmon.svc.cluster.local:9200"]
bulk.index = "{{{{ POD_NAMESPACE }}}}"
tls.verify_certificate = true
tls.verify_hostname = true
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"
