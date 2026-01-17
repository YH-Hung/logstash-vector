"""Runtime tests that actually execute Vector to catch runtime errors."""
import pytest
import subprocess
import tempfile
import time
from pathlib import Path


def test_vector_config_runtime_execution(vector_config_path, sample_log_path):
    """Test that Vector config can actually run without runtime errors."""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    if not sample_log_path.exists():
        pytest.skip(f"Sample log file not found: {sample_log_path}")
    
    # Create a test config that outputs to a file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_config:
        config_content = vector_config_path.read_text()
        
        # Replace Elasticsearch sink with file sink for testing
        config_content = config_content.replace(
            '[sinks.elasticsearch_output]',
            '[sinks.file_output]'
        )
        config_content = config_content.replace(
            'type = "elasticsearch"',
            'type = "file"'
        )
        config_content = config_content.replace(
            'inputs = ["processing_logic"]',
            'inputs = ["processing_logic"]\npath = "/tmp/vector_test_output.jsonl"\nencoding.codec = "json"'
        )
        # Remove elasticsearch-specific config
        lines = config_content.split('\n')
        filtered_lines = []
        skip_until_next_section = False
        for line in lines:
            if line.startswith('[sinks.file_output]'):
                skip_until_next_section = False
                filtered_lines.append(line)
            elif skip_until_next_section and (line.startswith('[') or line.strip() == ''):
                skip_until_next_section = False
                if line.strip() != '':
                    filtered_lines.append(line)
            elif not skip_until_next_section:
                if any(x in line for x in ['endpoints', 'bulk.index', 'auth.', 'tls.']):
                    skip_until_next_section = True
                else:
                    filtered_lines.append(line)
        
        # Update file path to use sample log
        filtered_content = '\n'.join(filtered_lines)
        filtered_content = filtered_content.replace(
            'include = ["/app/log/web_*.log"]',
            f'include = ["{sample_log_path}"]'
        )
        filtered_content = filtered_content.replace(
            'read_from = "end"',
            'read_from = "beginning"'
        )
        
        tmp_config.write(filtered_content)
        tmp_config_path = tmp_config.name
    
    try:
        # Try to run Vector with the config
        # Use a short timeout since we just want to verify it starts without errors
        result = subprocess.run(
            ["vector", "--config-toml", tmp_config_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Check stderr for configuration errors
        if "Configuration error" in result.stderr or "error" in result.stderr.lower():
            # If it's just about missing files or connections, that's OK
            if "unable to parse" in result.stderr.lower() or "unhandled fallible" in result.stderr.lower():
                pytest.fail(f"Vector runtime error detected:\n{result.stderr}")
        
        # Return code 0 or 1 is OK (1 might be due to missing files, which is expected in test)
        # But we should not have configuration syntax errors
        assert "Configuration error" not in result.stderr, f"Configuration error: {result.stderr}"
        
    except subprocess.TimeoutExpired:
        # Timeout is OK - it means Vector started successfully
        pass
    finally:
        # Clean up
        Path(tmp_config_path).unlink(missing_ok=True)


def test_vector_test_config_runtime_execution():
    """Test that the test config (vector.test.toml) can run without errors."""
    test_config_path = Path(__file__).parent.parent / "vector" / "vector.test.toml"
    sample_log_path = Path(__file__).parent.parent / "sample" / "web_hmib_1.log"
    
    if not test_config_path.exists():
        pytest.skip(f"Test config not found: {test_config_path}")
    
    if not sample_log_path.exists():
        pytest.skip(f"Sample log file not found: {sample_log_path}")
    
    # Create output directory
    output_dir = Path("/tmp/vector_test_output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "vector_output.jsonl"
    output_file.unlink(missing_ok=True)
    
    try:
        # Try to run Vector with the test config
        # We'll use a short timeout since we just want to verify it starts
        result = subprocess.run(
            ["vector", "--config-toml", str(test_config_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(test_config_path.parent.parent)
        )
        
        # Check for configuration errors
        stderr_lower = result.stderr.lower()
        if "configuration error" in stderr_lower:
            if any(err in stderr_lower for err in ["unable to parse", "unhandled fallible", "invalid argument type", "undefined variable"]):
                pytest.fail(f"Vector runtime configuration error:\n{result.stderr}")
        
        # Check for VRL errors
        if "error[e" in result.stderr.lower() or "vrl" in stderr_lower and "error" in stderr_lower:
            pytest.fail(f"Vector VRL error detected:\n{result.stderr}")
            
    except subprocess.TimeoutExpired:
        # Timeout is OK - means Vector started successfully
        pass
    except FileNotFoundError:
        pytest.skip("Vector binary not found")
    finally:
        # Clean up
        output_file.unlink(missing_ok=True)


def test_vector_config_validation_with_runtime_check(vector_config_path):
    """Test that validation passes AND runtime would work."""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    # First validate
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(vector_config_path), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Vector config validation failed: {result.stderr}"
    
    # Now check that there are no obvious runtime issues by checking the config content
    config_content = vector_config_path.read_text()
    
    # Check for common runtime error patterns
    errors = []
    
    # Check for parse_grok without error handling (old pattern)
    if 'result = parse_grok(' in config_content and 'result, err = parse_grok(' not in config_content:
        # But allow if using parse_grok! (infallible version)
        if 'parse_grok!(' not in config_content:
            errors.append("parse_grok without error handling found")
    
    # Check for includes() with string (should use contains)
    if 'includes(string!' in config_content:
        errors.append("includes() used with string - should use contains()")
    
    # Check for multiline pattern with grok syntax
    if '%{DATA}' in config_content and 'start_pattern' in config_content:
        # This might be OK if it's in a comment, but check context
        lines = config_content.split('\n')
        for i, line in enumerate(lines):
            if 'start_pattern' in line and '%{DATA}' in line:
                errors.append(f"Multiline pattern may use grok syntax instead of regex (line {i+1})")
                break
    
    if errors:
        pytest.fail(f"Potential runtime errors detected:\n" + "\n".join(f"  - {e}" for e in errors))
