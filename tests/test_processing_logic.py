"""Tests for processing logic: tag management, field combination, type conversion, conditional removal."""
import pytest
from pathlib import Path


def test_tag_management_mgtag(temp_config_file, temp_log_file):
    """Test tag management: MGtag = 'null' when maskGroupId is null"""
    test_log = "[2026-01-16 09:10:33:130] Test log without maskGroupId\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.tag_manager]
type = "remap"
inputs = ["file_input"]
source = '''
if !exists(.maskGroupId) {{
    .MGtag = "null"
}}
if !exists(.product) {{
    .Ptag = "null"
}}
if !exists(.layer) {{
    .Ltag = "null"
}}
'''

[sinks.console]
type = "console"
inputs = ["tag_manager"]
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


def test_tag_management_ptag(temp_config_file, temp_log_file):
    """Test tag management: Ptag = 'null' when product is null"""
    test_log = "[2026-01-16 09:10:33:130] Test log without product\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.tag_manager]
type = "remap"
inputs = ["file_input"]
source = '''
if !exists(.maskGroupId) {{
    .MGtag = "null"
}}
if !exists(.product) {{
    .Ptag = "null"
}}
if !exists(.layer) {{
    .Ltag = "null"
}}
'''

[sinks.console]
type = "console"
inputs = ["tag_manager"]
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


def test_tag_management_ltag(temp_config_file, temp_log_file):
    """Test tag management: Ltag = 'null' when layer is null"""
    test_log = "[2026-01-16 09:10:33:130] Test log without layer\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.tag_manager]
type = "remap"
inputs = ["file_input"]
source = '''
if !exists(.maskGroupId) {{
    .MGtag = "null"
}}
if !exists(.product) {{
    .Ptag = "null"
}}
if !exists(.layer) {{
    .Ltag = "null"
}}
'''

[sinks.console]
type = "console"
inputs = ["tag_manager"]
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


def test_field_combination(temp_config_file, temp_log_file):
    """Test field combination: maskGroupId = product + '-' + layer when MGtag == 'null'"""
    test_log = '{"product":"TMEF78", "layer":"376A-M001"}\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.field_combiner]
type = "remap"
inputs = ["file_input"]
source = '''
# Set tags first
if !exists(.maskGroupId) {{
    .MGtag = "null"
}}
if !exists(.product) {{
    .Ptag = "null"
}}
if !exists(.layer) {{
    .Ltag = "null"
}}

# Combine fields if conditions met
if .MGtag == "null" && .Ptag != "null" && .Ltag != "null" {{
    .maskGroupId = string!(.product) + "-" + string!(.layer)
}}
'''

[sinks.console]
type = "console"
inputs = ["field_combiner"]
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


def test_type_conversion_masklistno(temp_config_file, temp_log_file):
    """Test type conversion: MaskListNo to integer"""
    test_log = "MaskListNo=123\n"
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.type_converter]
type = "remap"
inputs = ["file_input"]
source = '''
# Parse MaskListNo first
result = parse_grok(.message, "MaskListNo=%{{NUMBER:MaskListNo}}")
if is_object(result) {{
    .MaskListNo = to_int!(result.MaskListNo)
}}
'''

[sinks.console]
type = "console"
inputs = ["type_converter"]
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


def test_conditional_field_removal_isqueryphase(temp_config_file, temp_log_file):
    """Test conditional field removal when IsQueryPhase == 'Y'"""
    test_log = 'IsQueryPhase:"Y"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.conditional_remover]
type = "remap"
inputs = ["file_input"]
source = '''
# Set test fields
.IsQueryPhase = "Y"
.maskLotId = "test"
.maskGroupId = "test"
.product = "test"
.layer = "test"

# Remove fields if condition met
if .IsQueryPhase == "Y" || includes(string!(.rqstType), "PHASE") {{
    del(.maskLotId)
    del(.maskGroupId)
    del(.product)
    del(.layer)
}}
'''

[sinks.console]
type = "console"
inputs = ["conditional_remover"]
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


def test_conditional_field_removal_rqsttype(temp_config_file, temp_log_file):
    """Test conditional field removal when rqstType contains 'PHASE'"""
    test_log = 'rqstType:"QUERY_PHASE"\n'
    temp_log_file.write_text(test_log)
    
    config = f"""
[sources.file_input]
type = "file"
include = ["{temp_log_file}"]
read_from = "beginning"

[transforms.conditional_remover]
type = "remap"
inputs = ["file_input"]
source = '''
# Parse rqstType
result = parse_grok(.message, "rqstType:\\\"%{{NOTSPACE:rqstType}}\\\"")
if is_object(result) {{
    .rqstType = result.rqstType
}}

# Set test fields
.maskLotId = "test"
.maskGroupId = "test"
.product = "test"
.layer = "test"

# Remove fields if condition met
if .IsQueryPhase == "Y" || (exists(.rqstType) && includes(string!(.rqstType), "PHASE")) {{
    del(.maskLotId)
    del(.maskGroupId)
    del(.product)
    del(.layer)
}}
'''

[sinks.console]
type = "console"
inputs = ["conditional_remover"]
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
