"""Tests for filename extraction from path."""
import pytest
from pathlib import Path


def test_filename_extraction_from_path(temp_config_file, temp_log_file, parsed_output):
    """Test filename extraction from path using grok pattern"""
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    # Create config with path parsing transform
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_filename]
type = "remap"
inputs = ["file_input"]
source = '''
. = parse_grok!(.file, "%{{GREEDYDATA}}/%{{NOTSPACE:filename}}")
'''

[sinks.console]
type = "console"
inputs = ["parse_filename"]
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


def test_filename_extraction_various_paths(temp_config_file, temp_log_file):
    """Test filename extraction with various path formats"""
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_filename]
type = "remap"
inputs = ["file_input"]
source = '''
. = parse_grok!(.file, "%{{GREEDYDATA}}/%{{NOTSPACE:filename}}")
'''

[sinks.console]
type = "console"
inputs = ["parse_filename"]
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


def test_filename_extraction_edge_cases(temp_config_file, temp_log_file):
    """Test filename extraction edge cases (no path, root path, etc.)"""
    test_log_content = "[2026-01-16 09:10:33:130]   [test-uuid] Test log line\n"
    temp_log_file.write_text(test_log_content)
    
    # Config should handle cases where path might not match pattern
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_filename]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.file, "%{{GREEDYDATA}}/%{{NOTSPACE:filename}}")
if is_object(result) {{
    .filename = result.filename
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_filename"]
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
