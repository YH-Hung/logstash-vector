"""Simple regex-based Logstash parser as fallback for pyparsing issues."""

import re
from pathlib import Path
from typing import Any

from lv_py.models import PluginType
from lv_py.models.logstash_config import LogstashConfiguration, LogstashPlugin


def _extract_blocks(content: str) -> list[tuple[str, str, int]]:
    """
    Extract top-level blocks (input, filter, output) by counting braces.

    Returns list of (block_type, block_content, start_position).
    """
    blocks = []
    block_keywords = ['input', 'filter', 'output']

    i = 0
    while i < len(content):
        # Skip whitespace and comments
        while i < len(content) and content[i] in ' \t\n':
            i += 1

        if i >= len(content):
            break

        # Check for block keyword
        found_keyword = None
        for keyword in block_keywords:
            if content[i:i+len(keyword)].lower() == keyword:
                # Verify it's a whole word
                if i + len(keyword) < len(content) and content[i + len(keyword)].isalnum():
                    continue
                found_keyword = keyword
                break

        if found_keyword:
            keyword_start = i
            i += len(found_keyword)

            # Skip whitespace to find opening brace
            while i < len(content) and content[i] in ' \t\n':
                i += 1

            if i >= len(content) or content[i] != '{':
                # Not a block, continue
                continue

            # Found opening brace, now count to find matching closing brace
            i += 1  # Skip opening brace
            brace_depth = 1
            content_start = i

            while i < len(content) and brace_depth > 0:
                if content[i] == '{':
                    brace_depth += 1
                elif content[i] == '}':
                    brace_depth -= 1
                i += 1

            # Extract block content (everything between the braces)
            block_content = content[content_start:i-1]
            blocks.append((found_keyword.lower(), block_content, keyword_start))
        else:
            i += 1

    return blocks


def _extract_plugins(block_content: str, block_start: int, full_content: str) -> list[tuple[str, dict[str, Any], int]]:
    """
    Extract plugins from a block by finding plugin_name { ... } patterns.

    Returns list of (plugin_name, config_dict, line_number).
    """
    plugins = []

    i = 0
    while i < len(block_content):
        # Skip whitespace
        while i < len(block_content) and block_content[i] in ' \t\n':
            i += 1

        if i >= len(block_content):
            break

        # Try to match identifier (plugin name)
        if block_content[i].isalpha() or block_content[i] == '_':
            name_start = i
            while i < len(block_content) and (block_content[i].isalnum() or block_content[i] == '_'):
                i += 1

            plugin_name = block_content[name_start:i]

            # Skip whitespace to find opening brace
            while i < len(block_content) and block_content[i] in ' \t\n':
                i += 1

            if i >= len(block_content) or block_content[i] != '{':
                # Not a plugin, continue
                continue

            # Found opening brace, count to find matching closing brace
            i += 1  # Skip opening brace
            brace_depth = 1
            config_start = i

            while i < len(block_content) and brace_depth > 0:
                if block_content[i] == '{':
                    brace_depth += 1
                elif block_content[i] == '}':
                    brace_depth -= 1
                i += 1

            # Extract config content
            config_content = block_content[config_start:i-1]
            config_dict = _parse_config(config_content)

            # Calculate line number
            line_number = full_content[:block_start + name_start].count('\n') + 1

            plugins.append((plugin_name, config_dict, line_number))
        else:
            i += 1

    return plugins


def parse_file_regex(file_path: Path) -> LogstashConfiguration:
    """
    Parse Logstash config using manual parsing with brace counting.

    This approach handles nested braces correctly by counting depth.
    """
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    raw_content = file_path.read_text()

    inputs: list[LogstashPlugin] = []
    filters: list[LogstashPlugin] = []
    outputs: list[LogstashPlugin] = []

    # Extract blocks by finding block keywords and counting braces
    blocks = _extract_blocks(raw_content)

    for block_type, block_content, block_start in blocks:
        line_number = raw_content[:block_start].count('\n') + 1

        # Parse plugins within the block
        plugins = _extract_plugins(block_content, block_start, raw_content)

        for plugin_name, plugin_config, plugin_line in plugins:
            # Create LogstashPlugin
            if block_type == "input":
                inputs.append(LogstashPlugin(
                    plugin_type=PluginType.INPUT,
                    plugin_name=plugin_name,
                    config=plugin_config,
                    line_number=plugin_line,
                ))
            elif block_type == "filter":
                filters.append(LogstashPlugin(
                    plugin_type=PluginType.FILTER,
                    plugin_name=plugin_name,
                    config=plugin_config,
                    line_number=plugin_line,
                ))
            elif block_type == "output":
                outputs.append(LogstashPlugin(
                    plugin_type=PluginType.OUTPUT,
                    plugin_name=plugin_name,
                    config=plugin_config,
                    line_number=plugin_line,
                ))

    # Validate we have at least one input and one output
    if not inputs:
        raise ValueError(f"No input plugins found in {file_path}")
    if not outputs:
        raise ValueError(f"No output plugins found in {file_path}")

    return LogstashConfiguration(
        file_path=file_path,
        inputs=inputs,
        filters=filters,
        outputs=outputs,
        raw_content=raw_content,
    )


def _parse_config(content: str) -> dict[str, Any]:
    """Parse configuration key => value pairs."""
    config: dict[str, Any] = {}

    # Pattern for key => value
    # Handles: key => "value", key => [array], key => { nested }
    kv_pattern = r'(\w+)\s*=>\s*(.+?)(?=\s+\w+\s*=>|$)'

    for match in re.finditer(kv_pattern, content, re.DOTALL):
        key = match.group(1)
        value_str = match.group(2).strip()

        # Parse the value
        value = _parse_value(value_str)
        config[key] = value

    return config


def _parse_value(value_str: str) -> Any:
    """Parse a configuration value."""
    value_str = value_str.strip().rstrip(',')

    # String value
    if value_str.startswith('"') or value_str.startswith("'"):
        return value_str.strip('"').strip("'")

    # Array value
    if value_str.startswith('['):
        array_content = value_str.strip('[]')
        items = []
        for item in re.split(r',\s*', array_content):
            items.append(item.strip('"').strip("'"))
        return items

    # Hash/object value (simplified - just store as string for now)
    if value_str.startswith('{'):
        # For hashes like { "field" => "pattern" }, parse as dict
        hash_dict: dict[str, Any] = {}
        hash_content = value_str.strip('{}')
        for kv_match in re.finditer(r'"([^"]+)"\s*=>\s*"([^"]+)"', hash_content):
            hash_dict[kv_match.group(1)] = kv_match.group(2)
        return hash_dict if hash_dict else value_str

    # Boolean
    if value_str.lower() in ('true', 'false'):
        return value_str.lower() == 'true'

    # Number
    if value_str.isdigit():
        return int(value_str)

    # Default: return as string
    return value_str
