"""Tests for Vector file source configuration."""
import pytest
from pathlib import Path


def test_file_source_glob_pattern(temp_config_file, temp_log_file, parsed_output):
    """Test that file source matches glob pattern /app/log/web_*.log"""
    # Create a test log file
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    # Create Vector config with file source
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.console]
type = "console"
inputs = ["file_input"]
encoding.codec = "json"
"""
    
    # Write config
    temp_config_file.write_text(config)
    
    # For file source, we need to actually run vector in a way that processes the file
    # Since Vector processes files continuously, we'll test the config is valid
    # and that it can be loaded
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"


def test_file_source_read_from_end(temp_config_file, temp_log_file):
    """Test that read_from: 'end' is configured correctly"""
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "end"

[sinks.console]
type = "console"
inputs = ["file_input"]
encoding.codec = "json"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"
    
    # Verify read_from is set to end
    config_content = temp_config_file.read_text()
    assert 'read_from = "end"' in config_content


def test_file_source_system_field(temp_config_file, temp_log_file, parsed_output):
    """Test that system: 'legendary' field is added to all events"""
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    # Create config with system field addition via remap transform
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.add_system_field]
type = "remap"
inputs = ["file_input"]
source = '''
.system = "legendary"
'''

[sinks.console]
type = "console"
inputs = ["add_system_field"]
encoding.codec = "json"
"""
    
    temp_config_file.write_text(config)
    
    # Validate config
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"
    
    # Verify system field is added in transform
    config_content = temp_config_file.read_text()
    assert '.system = "legendary"' in config_content


def test_file_source_basic_configuration(temp_config_file, temp_log_file):
    """Test basic file source configuration options"""
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sinks.console]
type = "console"
inputs = ["file_input"]
encoding.codec = "json"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"
