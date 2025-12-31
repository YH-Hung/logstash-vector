#!/usr/bin/env python3
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

# Test the pattern
block_pattern = r'(input|filter|output)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'

matches = list(re.finditer(block_pattern, content, re.IGNORECASE | re.DOTALL))
print(f"Found {len(matches)} blocks")
for i, match in enumerate(matches):
    print(f"\nBlock {i}: {match.group(1)}")
    print(f"Content length: {len(match.group(2))}")
    print(f"Content preview: {match.group(2)[:100]}")
