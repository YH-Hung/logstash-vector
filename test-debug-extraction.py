#!/usr/bin/env python3
"""Debug extraction logic."""

import sys
sys.path.insert(0, "/Users/yinghanhung/Projects/AI/logstash-vector/lv-py/src")

from pathlib import Path
import pyparsing as pp
from lv_py.parser.logstash_parser import _create_logstash_grammar

test_content = """input {
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

grammar = _create_logstash_grammar()
parsed = grammar.parseString(test_content, parseAll=False)

print(f"Total items: {len(parsed)}")
for i, block in enumerate(parsed):
    print(f"\nBlock {i}:")
    print(f"  Type: {type(block)}")
    if isinstance(block, pp.ParseResults):
        print(f"  Dict keys: {block.asDict().keys()}")
        print(f"  block_type: {block.get('block_type', 'NOT FOUND')}")
        print(f"  Items in block: {len(block)}")
        for j, item in enumerate(block):
            if isinstance(item, pp.ParseResults):
                print(f"    Item {j}: {item.asDict().keys()}")
