#!/usr/bin/env python3
"""Test _parse_config directly on the nested hash content."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lv-py" / "src"))

from lv_py.parser.logstash_parser_regex import _parse_config, _parse_value

# Test the exact content inside the hash
hash_content = '"message" => "%{COMBINEDAPACHELOG}"'

print("=" * 80)
print(f"Testing _parse_config with: {hash_content}")
print("=" * 80)

result = _parse_config(hash_content)
print(f"\nResult: {result}")
print(f"Result type: {type(result)}")
print(f"Result keys: {list(result.keys())}")

# Also test the full value parsing
full_value = '{ "message" => "%{COMBINEDAPACHELOG}" }'
print("\n" + "=" * 80)
print(f"Testing _parse_value with: {full_value}")
print("=" * 80)

result2 = _parse_value(full_value)
print(f"\nResult: {result2}")
print(f"Result type: {type(result2)}")
