"""Tests for field extraction using grok patterns."""
import pytest
from pathlib import Path


def test_product_field_extraction(temp_config_file, temp_log_file):
    """Test product field extraction: .*(?i)product:\"%{NOTSPACE:product}\""""
    test_log = '[2026-01-16 09:10:33:211] Rep_DisplayInfo {"product":"TMEF78", "layer":"376A-M001"}\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_fields]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, ".*(?i)product:\\\"%{{NOTSPACE:product}}\\\"")
if is_object(result) {{
    .product = result.product
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_fields"]
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


def test_layer_field_extraction(temp_config_file, temp_log_file):
    """Test layer field extraction: .*(?i)layer:\"%{NOTSPACE:layer}\""""
    test_log = '[2026-01-16 09:10:33:211] Rep_DisplayInfo {"product":"TMEF78", "layer":"376A-M001"}\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_fields]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, ".*(?i)layer:\\\"%{{NOTSPACE:layer}}\\\"")
if is_object(result) {{
    .layer = result.layer
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_fields"]
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


def test_maskgroupid_pattern1_extraction(temp_config_file, temp_log_file):
    """Test maskGroupId extraction - Pattern 1: .*(?i)mask_?group_?id:\"%{NOTSPACE:maskGroupId}\""""
    test_log = '{"mask_group_id":"TMEF78-376A-M001"}\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_fields]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, ".*(?i)mask_?group_?id:\\\"%{{NOTSPACE:maskGroupId}}\\\"")
if is_object(result) {{
    .maskGroupId = result.maskGroupId
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_fields"]
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


def test_maskgroupid_all_patterns(temp_config_file, temp_log_file):
    """Test maskGroupId extraction with all 5 fallback patterns"""
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_maskgroupid]
type = "remap"
inputs = ["file_input"]
source = '''
# Try pattern 1: mask_?group_?id:"..."
result = parse_grok(.message, ".*(?i)mask_?group_?id:\\\"%{{NOTSPACE:maskGroupId}}\\\"")
if !is_object(result) {{
    # Try pattern 2: maskGroupId-> ...
    result = parse_grok(.message, ".*(?i)maskGroupId->\\\\s%{{NOTSPACE:maskGroupId}}")
}}
if !is_object(result) {{
    # Try pattern 3: reticleId="..."
    result = parse_grok(.message, ".*(?i)reticleId=\\\"%{{NOTSPACE:maskGroupId}}\\\"\\\\>")
}}
if !is_object(result) {{
    # Try pattern 4: reticle_?id:"..."
    result = parse_grok(.message, ".*(?i)reticle_?id:\\\"%{{NOTSPACE:maskGroupId}}\\\"")
}}
if !is_object(result) {{
    # Try pattern 5: reticlelotid -> ...
    result = parse_grok(.message, ".*(?i)reticlelotid\\\\s->\\\\s%{{NOTSPACE:maskGroupId}}")
}}
if is_object(result) {{
    .maskGroupId = result.maskGroupId
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_maskgroupid"]
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


def test_action_field_extraction(temp_config_file, temp_log_file):
    """Test Action field extraction with 2 patterns"""
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_action]
type = "remap"
inputs = ["file_input"]
source = '''
# Try pattern 1: Action:"...:..."
result = parse_grok(.message, ".*(?i)Action:\\\"%{{NOTSPACE:Action}}\\\\:%{{NOTSPACE:maskGroupId}}\\\"")
if is_object(result) {{
    .Action = result.Action
    .maskGroupId = result.maskGroupId
}} else {{
    # Try pattern 2: Action:"..."
    result = parse_grok(.message, ".*(?i)Action:\\\"%{{NOTSPACE:Action}}\\\"")
    if is_object(result) {{
        .Action = result.Action
    }}
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_action"]
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


def test_masklotid_all_patterns(temp_config_file, temp_log_file):
    """Test maskLotId extraction with all 4 patterns"""
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_masklotid]
type = "remap"
inputs = ["file_input"]
source = '''
# Try pattern 1: mask_?lot_?id:"..."
result = parse_grok(.message, ".*(?i)mask_?lot_?id:\\\"%{{NOTSPACE:maskLotId}}\\\"")
if !is_object(result) {{
    # Try pattern 2: maskLotId->...
    result = parse_grok(.message, ".*(?i)maskLotId->%{{NOTSPACE:maskLotId}}")
}}
if !is_object(result) {{
    # Try pattern 3: maskLotId-> ...
    result = parse_grok(.message, ".*(?i)maskLotId->\\\\s%{{NOTSPACE:maskLotId}}")
}}
if !is_object(result) {{
    # Try pattern 4: maskLotId = '...'
    result = parse_grok(.message, ".*(?i)maskLotId\\\\s=\\\\'%{{NOTSPACE:maskLotId}}\\\\'")
}}
if is_object(result) {{
    .maskLotId = result.maskLotId
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_masklotid"]
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


def test_masklistno_extraction(temp_config_file, temp_log_file):
    """Test MaskListNo extraction: MaskListNo=%{NUMBER:MaskListNo}"""
    test_log = "MaskListNo=123\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_masklistno]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, "MaskListNo=%{{NUMBER:MaskListNo}}")
if is_object(result) {{
    .MaskListNo = result.MaskListNo
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_masklistno"]
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


def test_rqsttype_extraction(temp_config_file, temp_log_file):
    """Test rqstType extraction: rqstType:\"%{NOTSPACE:rqstType}\""""
    test_log = 'rqstType:"QUERY"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_rqsttype]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, "rqstType:\\\"%{{NOTSPACE:rqstType}}\\\"")
if is_object(result) {{
    .rqstType = result.rqstType
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_rqsttype"]
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


def test_isqueryphase_extraction(temp_config_file, temp_log_file):
    """Test IsQueryPhase extraction: IsQueryPhase:\"%{NOTSPACE:IsQueryPhase}\""""
    test_log = 'IsQueryPhase:"Y"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_isqueryphase]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, "IsQueryPhase:\\\"%{{NOTSPACE:IsQueryPhase}}\\\"")
if is_object(result) {{
    .IsQueryPhase = result.IsQueryPhase
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_isqueryphase"]
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


def test_srvobjcategory_extraction(temp_config_file, temp_log_file):
    """Test srvObjCategory extraction: srvObjCategory:\"%{NOTSPACE:srvObjCategory}\""""
    test_log = 'srvObjCategory:"MASK"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_srvobjcategory]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, "srvObjCategory:\\\"%{{NOTSPACE:srvObjCategory}}\\\"")
if is_object(result) {{
    .srvObjCategory = result.srvObjCategory
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_srvobjcategory"]
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


def test_srvmethod_extraction(temp_config_file, temp_log_file):
    """Test srvMethod extraction: srvMethod:\"%{NOTSPACE:srvMethod}\""""
    test_log = 'srvMethod:"GET_MASK_INFO"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_srvmethod]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, "srvMethod:\\\"%{{NOTSPACE:srvMethod}}\\\"")
if is_object(result) {{
    .srvMethod = result.srvMethod
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_srvmethod"]
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


def test_purge_tool_extraction(temp_config_file, temp_log_file):
    """Test Purge_Tool extraction: purge_tool:\"%{NOTSPACE:Purge_Tool}\""""
    test_log = 'purge_tool:"PURGE_V1"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.parse_purge_tool]
type = "remap"
inputs = ["file_input"]
source = '''
result = parse_grok(.message, "purge_tool:\\\"%{{NOTSPACE:Purge_Tool}}\\\"")
if is_object(result) {{
    .Purge_Tool = result.Purge_Tool
}}
'''

[sinks.console]
type = "console"
inputs = ["parse_purge_tool"]
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
