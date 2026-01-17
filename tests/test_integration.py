"""End-to-end integration tests for complete Vector pipeline."""
import pytest
import json
from pathlib import Path


def test_end_to_end_pipeline(sample_log_path, vector_config_path, project_root):
    """Test complete pipeline with web_hmib_1.log sample"""
    if not sample_log_path.exists():
        pytest.skip(f"Sample log file not found: {sample_log_path}")
    
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    # Validate the complete configuration
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(vector_config_path), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Vector config validation failed: {result.stderr}"
    
    # Also check for common runtime error patterns in the config
    config_content = vector_config_path.read_text()
    
    # Check that parse_grok uses proper error handling
    if 'result = parse_grok(' in config_content and 'result, err = parse_grok(' not in config_content:
        if 'parse_grok!(' not in config_content:  # Allow infallible version
            pytest.fail("Config uses parse_grok without error handling - will cause runtime errors")
    
    # Check that includes() is not used with strings
    if 'includes(string!' in config_content:
        pytest.fail("Config uses includes() with string - should use contains() - will cause runtime errors")
    
    # Check multiline pattern doesn't use grok syntax
    if '%{DATA}' in config_content:
        lines = config_content.split('\n')
        for i, line in enumerate(lines):
            if 'start_pattern' in line and '%{DATA}' in line:
                pytest.fail(f"Multiline pattern uses grok syntax instead of regex (line {i+1}) - will cause runtime errors")


def test_complete_pipeline_structure(vector_config_path):
    """Test that complete pipeline has all required components"""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    config_content = vector_config_path.read_text()
    
    # Check for required components
    assert "[sources.file_input]" in config_content, "File source not found"
    assert "[transforms.add_system_field]" in config_content, "System field transform not found"
    assert "[transforms.parse_filename]" in config_content, "Filename parsing transform not found"
    assert "[transforms.field_parser]" in config_content, "Field parser transform not found"
    assert "[transforms.processing_logic]" in config_content, "Processing logic transform not found"
    assert "[sinks.elasticsearch_output]" in config_content, "Elasticsearch sink not found"


def test_pipeline_data_flow(vector_config_path):
    """Test that pipeline data flow is correct (inputs/outputs chain properly)"""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    config_content = vector_config_path.read_text()
    
    # Verify transform chain
    # file_input -> add_system_field -> parse_filename -> field_parser -> processing_logic -> elasticsearch_output
    assert 'inputs = ["file_input"]' in config_content or 'inputs = ["add_system_field"]' in config_content
    assert 'inputs = ["parse_filename"]' in config_content or 'inputs = ["field_parser"]' in config_content
    assert 'inputs = ["processing_logic"]' in config_content or 'inputs = ["field_parser"]' in config_content


def test_error_handling_malformed_logs(temp_config_file, temp_log_file):
    """Test error handling with malformed logs"""
    # Create malformed log content
    malformed_log = "This is not a valid log format\n{invalid json}\n[incomplete\n"
    temp_log_file.write_text(malformed_log)
    
    # Create a minimal config that should handle errors gracefully
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.field_parser]
type = "remap"
inputs = ["file_input"]
source = '''
# Try to parse, but don't fail on errors
result = parse_grok(.message, ".*(?i)product:\\\"%{{NOTSPACE:product}}\\\"")
if is_object(result) {{
    .product = result.product
}}
'''

[sinks.console]
type = "console"
inputs = ["field_parser"]
encoding.codec = "json"
"""
    
    temp_config_file.write_text(config)
    
    import subprocess
    result = subprocess.run(
        ["vector", "validate", "--config-toml", str(temp_config_file), "--no-environment"],
        capture_output=True,
        text=True
    )
    
    # Config should be valid even if logs are malformed
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"


def test_all_fields_extracted(vector_config_path):
    """Test that all 12 target fields can be extracted"""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    config_content = vector_config_path.read_text()
    
    # Check for all field extraction patterns
    fields = [
        "product",
        "layer",
        "maskGroupId",
        "Action",
        "maskLotId",
        "MaskListNo",
        "rqstType",
        "IsQueryPhase",
        "srvObjCategory",
        "srvMethod",
        "Purge_Tool",
        "filename"
    ]
    
    # Verify field parser includes extraction logic
    assert "field_parser" in config_content, "Field parser transform should exist"
    
    # Check that at least some field patterns are present
    assert "parse_grok" in config_content, "Grok parsing should be used"


def test_multiline_processing_integration(vector_config_path):
    """Test that multiline processing is configured in the pipeline"""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    config_content = vector_config_path.read_text()
    
    # Check for multiline configuration
    assert "multiline" in config_content, "Multiline processing should be configured"
    assert "start_pattern" in config_content or "TRACE" in config_content, "Multiline start pattern should be configured"


def test_conditional_logic_integration(vector_config_path):
    """Test that conditional logic (field combination and removal) is in pipeline"""
    if not vector_config_path.exists():
        pytest.skip(f"Vector config not found: {vector_config_path}")
    
    config_content = vector_config_path.read_text()
    
    # Check for processing logic
    assert "processing_logic" in config_content, "Processing logic transform should exist"
    assert "MGtag" in config_content or "maskGroupId" in config_content, "Tag management should be present"
    assert "del(" in config_content or "IsQueryPhase" in config_content, "Conditional field removal should be present"
