#!/usr/bin/env python3
"""Test plugin regex pattern extraction."""

import re

# This is the actual block content from our successful block match
block_content = """
  file {
    path => "/var/log/app.log"
  }
"""

print("Block content:")
print(repr(block_content))
print()

# This is the plugin pattern from logstash_parser_regex.py
plugin_pattern = r'(\w+)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'

matches = list(re.finditer(plugin_pattern, block_content))
print(f"Found {len(matches)} plugin matches")

for i, match in enumerate(matches):
    print(f"\nPlugin {i}: {match.group(1)}")
    print(f"Config content: {repr(match.group(2))}")
