#!/usr/bin/env python3
"""Debug script to test grok parser with nested hash."""

import sys
from pathlib import Path

# Add lv-py to path
sys.path.insert(0, str(Path(__file__).parent / "lv-py" / "src"))

from lv_py.parser.logstash_parser_regex import parse_file_regex

# Test with actual grok-filter.conf content
grok_config = """input {
  file {
    path => "/var/log/apache/*.log"
    start_position => "beginning"
  }
}

filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
}

output {
  elasticsearch {
    hosts => ["http://localhost:9200"]
    index => "apache-logs-%{+YYYY.MM.dd}"
  }
}
"""

print("=" * 80)
print("Testing grok parser with nested hash config")
print("=" * 80)

# Parse the config
test_file = Path("/tmp/test-grok.conf")
test_file.write_text(grok_config)

try:
    result = parse_file_regex(test_file)

    print(f"\n✓ Parsed successfully!")
    print(f"\nInputs: {len(result.inputs)}")
    print(f"Filters: {len(result.filters)}")
    print(f"Outputs: {len(result.outputs)}")

    if result.filters:
        grok_filter = result.filters[0]
        print(f"\nGrok Filter Details:")
        print(f"  Plugin Name: {grok_filter.plugin_name}")
        print(f"  Plugin Type: {grok_filter.plugin_type}")
        print(f"  Config Keys: {list(grok_filter.config.keys())}")
        print(f"  Config: {grok_filter.config}")

        if "match" in grok_filter.config:
            match_value = grok_filter.config["match"]
            print(f"\n  Match Value Type: {type(match_value)}")
            print(f"  Match Value: {match_value}")

            if isinstance(match_value, dict):
                print(f"  ✓ Match is a dict (nested hash parsed correctly!)")
                for key, pattern in match_value.items():
                    print(f"    {key} => {pattern}")
            else:
                print(f"  ✗ Match is NOT a dict - parser issue!")
        else:
            print(f"\n  ✗ No 'match' key found in config!")

    # Now test transformation
    print("\n" + "=" * 80)
    print("Testing Grok Transformer")
    print("=" * 80)

    from lv_py.transformers import get_transformer
    from lv_py.models import PluginType

    transformer = get_transformer(PluginType.FILTER, "grok")
    if transformer and result.filters:
        vector_component = transformer.transform(result.filters[0])
        print(f"\nVector Component Type: {vector_component.component_kind}")
        print(f"\nVRL Source:")
        print(vector_component.config.get("source", "No source found"))

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
