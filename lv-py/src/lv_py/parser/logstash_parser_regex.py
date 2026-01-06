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
    """Parse configuration key => value pairs with proper nested structure support."""
    config: dict[str, Any] = {}

    i = 0
    while i < len(content):
        # Skip whitespace and comments
        while i < len(content) and content[i] in ' \t\n':
            i += 1

        if i >= len(content):
            break

        key = None

        # Match quoted key (e.g., "message" or 'message')
        if content[i] in ('"', "'"):
            quote_char = content[i]
            i += 1
            key_start = i
            # Find closing quote
            while i < len(content) and content[i] != quote_char:
                if content[i] == '\\' and i + 1 < len(content):
                    i += 2  # Skip escaped character
                else:
                    i += 1
            key = content[key_start:i]
            if i < len(content):
                i += 1  # Skip closing quote

        # Match unquoted key (e.g., match or codec)
        elif content[i].isalpha() or content[i] == '_':
            key_start = i
            while i < len(content) and (content[i].isalnum() or content[i] == '_'):
                i += 1
            key = content[key_start:i]

        # If we found a key, look for '=>' and parse value
        if key is not None:
            # Skip whitespace
            while i < len(content) and content[i] in ' \t\n':
                i += 1

            # Expect '=>'
            if i + 1 < len(content) and content[i:i+2] == '=>':
                i += 2

                # Skip whitespace
                while i < len(content) and content[i] in ' \t\n':
                    i += 1

                # Extract value using brace/bracket counting
                value_start = i
                value_end = _find_value_end(content, i)
                value_str = content[value_start:value_end].strip()

                # Parse the value
                value = _parse_value(value_str)
                config[key] = value

                i = value_end
            else:
                i += 1
        else:
            i += 1

    return config


def _find_value_end(content: str, start: int) -> int:
    """
    Find the end of a value by counting braces/brackets and looking for terminators.

    Values end at:
    - A comma or newline (if not inside braces/brackets/quotes)
    - The next key => pattern (if not inside braces/brackets/quotes)
    - End of content
    """
    i = start
    brace_depth = 0
    bracket_depth = 0
    in_quotes = False
    quote_char = None

    while i < len(content):
        char = content[i]

        # Handle quotes
        if char in ('"', "'") and (i == 0 or content[i-1] != '\\'):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None

        # Only count braces/brackets outside quotes
        if not in_quotes:
            if char == '{':
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
            elif char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1

            # Check for value termination
            if brace_depth == 0 and bracket_depth == 0:
                # Look ahead for next key => pattern
                remaining = content[i:]
                next_key_match = re.search(r'\s+\w+\s*=>', remaining)
                if next_key_match:
                    # Found next key, value ends before it
                    return i + next_key_match.start()

                # Check for comma or end of line (simple terminator)
                if char == '\n':
                    # Check if there's more content after whitespace
                    j = i + 1
                    while j < len(content) and content[j] in ' \t\n':
                        j += 1
                    # If next non-whitespace is a key or closing brace, end here
                    if j < len(content) and (content[j].isalpha() or content[j] == '}'):
                        return i

        i += 1

    return i


def _parse_value(value_str: str) -> Any:
    """Parse a configuration value with support for nested structures."""
    value_str = value_str.strip().rstrip(',')

    if not value_str:
        return ""

    # String value
    if value_str.startswith('"') or value_str.startswith("'"):
        # Remove quotes and handle escaped quotes
        return value_str[1:-1] if len(value_str) >= 2 else value_str

    # Array value
    if value_str.startswith('['):
        if not value_str.endswith(']'):
            # Handle incomplete array - find the closing bracket
            end_bracket = value_str.rfind(']')
            if end_bracket > 0:
                value_str = value_str[:end_bracket+1]

        array_content = value_str[1:-1].strip()
        if not array_content:
            return []

        items = []
        i = 0
        current_item = []

        # Parse array items respecting quotes
        in_quotes = False
        quote_char = None

        while i < len(array_content):
            char = array_content[i]

            if char in ('"', "'") and (i == 0 or array_content[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None

            if char == ',' and not in_quotes:
                # End of item
                item_str = ''.join(current_item).strip()
                if item_str:
                    items.append(_parse_value(item_str))
                current_item = []
            else:
                current_item.append(char)

            i += 1

        # Don't forget last item
        item_str = ''.join(current_item).strip()
        if item_str:
            items.append(_parse_value(item_str))

        return items

    # Hash/object value - recursively parse
    if value_str.startswith('{'):
        if not value_str.endswith('}'):
            # Handle incomplete hash
            end_brace = value_str.rfind('}')
            if end_brace > 0:
                value_str = value_str[:end_brace+1]

        hash_content = value_str[1:-1].strip()
        if not hash_content:
            return {}

        # Recursively parse hash content
        return _parse_config(hash_content)

    # Boolean
    if value_str.lower() in ('true', 'false'):
        return value_str.lower() == 'true'

    # Number (integer)
    if value_str.isdigit():
        return int(value_str)

    # Number (float)
    try:
        if '.' in value_str:
            return float(value_str)
    except ValueError:
        pass

    # Default: return as string
    return value_str
