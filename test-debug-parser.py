#!/usr/bin/env python3
"""Debug parser to see what's happening."""

import sys
sys.path.insert(0, "/Users/yinghanhung/Projects/AI/logstash-vector/lv-py/src")

from pathlib import Path
from lv_py.parser.logstash_parser import parse_file

test_file = Path("/Users/yinghanhung/Projects/AI/logstash-vector/test-configs/simple-pipeline.conf")

try:
    result = parse_file(test_file)
    print(f"Success! Parsed {len(result.inputs)} inputs, {len(result.filters)} filters, {len(result.outputs)} outputs")
    print(f"Inputs: {[p.plugin_name for p in result.inputs]}")
    print(f"Filters: {[p.plugin_name for p in result.filters]}")
    print(f"Outputs: {[p.plugin_name for p in result.outputs]}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
