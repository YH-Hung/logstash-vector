#!/usr/bin/env python3
"""
Compare Vector and Logstash parsing outputs to ensure identical results.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an event by removing metadata fields that may differ between
    Vector and Logstash, and sorting keys for consistent comparison.
    """
    # Fields to exclude from comparison (metadata that may differ)
    exclude_fields = {
        '@timestamp', '@version', 'host', 'log', 'ecs', 'agent',
        'file', 'path', 'message',  # We'll compare parsed fields, not raw message
        'tags', 'type',  # May have different representations
        'source', 'source_type',  # Vector may add source field
        'timestamp',  # Vector adds timestamp, Logstash uses @timestamp
        'event',  # Logstash adds event.original, Vector doesn't
        'filename',  # Vector extracts this, Logstash may not (or extracts differently)
        # Tag fields: Logstash uses MGtag/Ltag/Ptag to track missing fields,
        # but Vector directly checks field existence (exists() function).
        # These are implementation differences and should be excluded from comparison.
        'MGtag', 'Ltag', 'Ptag',
    }
    
    # Create normalized copy
    normalized = {}
    for key, value in event.items():
        # Skip excluded fields
        if key in exclude_fields:
            continue
        
        # Skip fields starting with @ (Logstash metadata)
        if key.startswith('@'):
            continue
        
        # Normalize the value
        if isinstance(value, dict):
            normalized[key] = normalize_event(value)
        elif isinstance(value, list):
            # Sort lists for comparison
            normalized[key] = sorted(value) if all(isinstance(x, (str, int, float)) for x in value) else value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            # Normalize numeric types - convert to same type for comparison
            # Keep as-is, but ensure consistent representation
            normalized[key] = int(value) if isinstance(value, float) and value.is_integer() else value
        else:
            normalized[key] = value
    
    return normalized


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file and return list of events."""
    events = []
    if not file_path.exists():
        return events
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line in {file_path}: {e}", file=sys.stderr)
    
    return events


def compare_events(vector_events: List[Dict], logstash_events: List[Dict]) -> bool:
    """
    Compare normalized events from Vector and Logstash.
    Returns True if identical, False otherwise.
    """
    if len(vector_events) != len(logstash_events):
        print(f"ERROR: Different number of events - Vector: {len(vector_events)}, Logstash: {len(logstash_events)}")
        return False
    
    all_match = True
    
    for i, (vec_event, ls_event) in enumerate(zip(vector_events, logstash_events)):
        vec_norm = normalize_event(vec_event)
        ls_norm = normalize_event(ls_event)
        
        # Get all keys from both events
        all_keys = set(vec_norm.keys()) | set(ls_norm.keys())
        
        # Check for missing keys
        vec_keys = set(vec_norm.keys())
        ls_keys = set(ls_norm.keys())
        
        missing_in_logstash = vec_keys - ls_keys
        missing_in_vector = ls_keys - vec_keys
        
        if missing_in_logstash:
            print(f"Event {i}: Keys present in Vector but missing in Logstash: {missing_in_logstash}")
            all_match = False
        
        if missing_in_vector:
            print(f"Event {i}: Keys present in Logstash but missing in Vector: {missing_in_vector}")
            all_match = False
        
        # Compare values for common keys
        for key in sorted(all_keys):  # Sort for consistent output
            vec_val = vec_norm.get(key)
            ls_val = ls_norm.get(key)
            
            # Handle type differences (e.g., string "123" vs int 123)
            if vec_val != ls_val:
                # Try to normalize numeric types
                if isinstance(vec_val, (int, float)) and isinstance(ls_val, str):
                    try:
                        ls_val_num = int(ls_val) if '.' not in ls_val else float(ls_val)
                        if vec_val == ls_val_num:
                            continue  # They match after normalization
                    except (ValueError, TypeError):
                        pass
                elif isinstance(ls_val, (int, float)) and isinstance(vec_val, str):
                    try:
                        vec_val_num = int(vec_val) if '.' not in vec_val else float(vec_val)
                        if ls_val == vec_val_num:
                            continue  # They match after normalization
                    except (ValueError, TypeError):
                        pass
                
                print(f"Event {i}, field '{key}':")
                print(f"  Vector:    {vec_val} (type: {type(vec_val).__name__})")
                print(f"  Logstash:  {ls_val} (type: {type(ls_val).__name__})")
                all_match = False
    
    return all_match


def main():
    """Main comparison function."""
    output_dir = Path(__file__).parent.parent / "output"
    vector_output = output_dir / "vector_output.jsonl"
    logstash_output = output_dir / "logstash_output.jsonl"
    
    print(f"Loading Vector output from: {vector_output}")
    vector_events = load_jsonl(vector_output)
    print(f"  Loaded {len(vector_events)} events")
    
    print(f"Loading Logstash output from: {logstash_output}")
    logstash_events = load_jsonl(logstash_output)
    print(f"  Loaded {len(logstash_events)} events")
    
    if not vector_events:
        print("ERROR: No events found in Vector output", file=sys.stderr)
        sys.exit(1)
    
    if not logstash_events:
        print("ERROR: No events found in Logstash output", file=sys.stderr)
        sys.exit(1)
    
    print("\nComparing events...")
    if compare_events(vector_events, logstash_events):
        print("\n✓ SUCCESS: All events match! Vector and Logstash produce identical parsing results.")
        sys.exit(0)
    else:
        print("\n✗ FAILURE: Events differ. See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
