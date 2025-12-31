#!/usr/bin/env python3
"""Test grammar structure."""

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
try:
    # Try without parseAll first
    result = grammar.parseString(test_content, parseAll=False)
    print(f"Parsed (partial): {result}")
    print(f"Keys: {result.asDict().keys()}")
    for i, item in enumerate(result):
        print(f"Item {i}: {type(item)} - {item.asDict().keys() if hasattr(item, 'asDict') else item}")
except Exception as e:
    print(f"Error (partial): {e}")

print("\n--- Now with parseAll ---\n")
try:
    result = grammar.parseString(test_content, parseAll=True)
    print(f"Success with parseAll!")
except Exception as e:
    print(f"Error (parseAll): {e}")
