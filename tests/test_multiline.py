"""Tests for Vector multiline processing configuration."""
import pytest
from pathlib import Path


def test_multiline_start_pattern(temp_config_file, temp_log_file):
    """Test multiline start pattern matching TRACE lines"""
    # Sample multiline log content matching the pattern
    multiline_log = """[2026-01-16 09:10:33:130]   [a027d5c0-8560-49e7-8f82-70901077a4bf] [TRACE] before SysUuid::set(): curSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf, preSysUuid=
[2026-01-16 09:10:33:142]   [8e475fe2-0680-41f2-b734-20cd691d05f9] [TRACE] after SysUuid::set(): curSysUuid=8e475fe2-0680-41f2-b734-20cd691d05f9, preSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf
[2026-01-16 09:10:33:166]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rqst_DisplayInfo {"mask_lot_id":"EBGN29J.1"}
"""
    
    temp_log_file.write_text(multiline_log)
    
    # Create config with multiline processing
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sources.file_input.multiline]
start_pattern = '^\\[%{{DATA}}\\]\\s\\s\\s\\[%{{DATA}}\\]\\s\\[TRACE\\]\\sbefore\\sSysUuid::set\\(\\):\\scurSysUuid=%{{GREEDYDATA}}'
mode = "halt_before"
condition_pattern = '^\\[%{{DATA}}\\]\\s\\s\\s\\[%{{DATA}}\\]\\s\\[TRACE\\]\\sbefore\\sSysUuid::set\\(\\):\\scurSysUuid=%{{GREEDYDATA}}'
timeout_ms = 5000

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


def test_multiline_halt_before_mode(temp_config_file, temp_log_file):
    """Test halt_before mode configuration - stops before condition_pattern matches"""
    temp_log_file.write_text("test log\n")
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sources.file_input.multiline]
start_pattern = "^\\\\[.*TRACE.*\\\\]"
mode = "halt_before"
condition_pattern = "^\\\\[.*TRACE.*\\\\]"
timeout_ms = 5000

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
    
    config_content = temp_config_file.read_text()
    assert 'mode = "halt_before"' in config_content


def test_multiline_condition_pattern_negation(temp_config_file, temp_log_file):
    """Test condition pattern negation logic"""
    temp_log_file.write_text("test log\n")
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sources.file_input.multiline]
start_pattern = "^\\\\[.*TRACE.*\\\\]"
mode = "halt_before"
condition_pattern = "^\\\\[.*TRACE.*\\\\]"
timeout_ms = 5000

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
    
    config_content = temp_config_file.read_text()
    assert "mode = \"halt_before\"" in config_content
    assert "condition_pattern" in config_content


def test_multiline_timeout_handling(temp_config_file, temp_log_file):
    """Test multiline timeout configuration"""
    temp_log_file.write_text("test log\n")
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[sources.file_input.multiline]
start_pattern = '^\\[.*TRACE.*\\]'
mode = "halt_before"
condition_pattern = '^\\[.*TRACE.*\\]'
timeout_ms = 5000

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


def test_multiline_with_real_sample(sample_log_path, temp_config_file):
    """Test multiline processing with real sample from web_hmib_1.log"""
    if not sample_log_path.exists():
        pytest.skip(f"Sample log file not found: {sample_log_path}")
    
    # Create config that processes the real sample
    config = f"""
[sources.file_input]
type = "file"
include = ["{sample_log_path}"]
read_from = "beginning"

[sources.file_input.multiline]
start_pattern = '^\\[%{{DATA}}\\]\\s\\s\\s\\[%{{DATA}}\\]\\s\\[TRACE\\]\\sbefore\\sSysUuid::set\\(\\):\\scurSysUuid=%{{GREEDYDATA}}'
mode = "halt_before"
condition_pattern = '^\\[%{{DATA}}\\]\\s\\s\\s\\[%{{DATA}}\\]\\s\\[TRACE\\]\\sbefore\\sSysUuid::set\\(\\):\\scurSysUuid=%{{GREEDYDATA}}'
timeout_ms = 5000

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
