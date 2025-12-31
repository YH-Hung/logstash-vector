#!/usr/bin/env python3
"""Test full regex flow to debug the issue."""

import re

content = """input {
  file {
    path => "/var/log/app.log"
  }
}

filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
}

output {
  file {
    path => "/var/log/output.log"
  }
}
"""

# Block pattern from logstash_parser_regex.py
block_pattern = r'(input|filter|output)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'

print("=== BLOCK MATCHING ===")
block_matches = list(re.finditer(block_pattern, content, re.IGNORECASE | re.DOTALL))
print(f"Found {len(block_matches)} blocks\n")

for i, block_match in enumerate(block_matches):
    block_type = block_match.group(1)
    block_content = block_match.group(2)

    print(f"Block {i}: {block_type}")
    print(f"Content: {repr(block_content[:100])}")
    print()

    # Now try plugin pattern on this block content
    plugin_pattern = r'(\w+)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'

    plugin_matches = list(re.finditer(plugin_pattern, block_content))
    print(f"  Found {len(plugin_matches)} plugins in this block")

    for j, plugin_match in enumerate(plugin_matches):
        plugin_name = plugin_match.group(1)
        plugin_content = plugin_match.group(2)
        print(f"    Plugin {j}: {plugin_name}")
        print(f"    Config: {repr(plugin_content[:80])}")

    print()
