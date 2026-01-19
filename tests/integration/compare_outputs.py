#!/usr/bin/env python3
"""
Output Comparison Script for Logstash vs Vector Migration
Compares JSON outputs field-by-field to validate functional parity
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


# Fields to compare (extracted business fields)
CRITICAL_FIELDS = [
    'product', 'layer', 'maskGroupId', 'maskLotId',
    'Action', 'MaskListNo', 'rqstType', 'IsQueryPhase',
    'srvObjCategory', 'srvMethod', 'Purge_Tool'
]

# Metadata fields
METADATA_FIELDS = ['system', 'type', 'filename']


def load_json_lines(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON lines file into list of documents"""
    documents = []
    if not file_path.exists():
        print(f"{RED}✗ File not found: {file_path}{NC}")
        return documents
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
                documents.append(doc)
            except json.JSONDecodeError as e:
                print(f"{YELLOW}⚠ Warning: Skipping invalid JSON at line {line_num}: {e}{NC}")
    
    return documents


def normalize_value(value: Any) -> Any:
    """Normalize values for comparison (handle type differences)"""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return value
    # Handle arrays: Logstash creates arrays when multiple patterns match the same field
    # Vector uses first-match-wins logic, so we compare against the first array element
    if isinstance(value, list) and len(value) > 0:
        return normalize_value(value[0])
    return str(value)


def compare_field(doc_idx: int, field: str, logstash_value: Any, vector_value: Any) -> Dict[str, Any]:
    """Compare a single field between Logstash and Vector output"""
    ls_val = normalize_value(logstash_value)
    v_val = normalize_value(vector_value)
    
    if ls_val == v_val:
        return {'status': 'match', 'field': field}
    else:
        return {
            'status': 'mismatch',
            'field': field,
            'doc_index': doc_idx,
            'logstash': ls_val,
            'vector': v_val
        }


def get_doc_key(doc: Dict) -> str:
    """Extract a unique key from document for matching.
    Uses the first line of message (contains unique timestamp) + filename."""
    message = doc.get('message', '')
    first_line = message.split('\n')[0] if message else ''
    filename = doc.get('filename', '')
    return f"{filename}:{first_line[:80]}"  # Use first 80 chars of first line


def match_documents(logstash_docs: List[Dict], vector_docs: List[Dict]) -> List[tuple]:
    """Match Logstash and Vector documents by content (message first line + filename).
    Returns list of (logstash_doc, vector_doc, match_key) tuples."""

    # Build index of Vector docs by key
    vector_by_key = {}
    for v_doc in vector_docs:
        key = get_doc_key(v_doc)
        vector_by_key[key] = v_doc

    # Match Logstash docs to Vector docs
    matched_pairs = []
    unmatched_logstash = []
    used_vector_keys = set()

    for ls_doc in logstash_docs:
        ls_key = get_doc_key(ls_doc)
        if ls_key in vector_by_key and ls_key not in used_vector_keys:
            matched_pairs.append((ls_doc, vector_by_key[ls_key], ls_key))
            used_vector_keys.add(ls_key)
        else:
            unmatched_logstash.append(ls_doc)

    # Find unmatched Vector docs
    unmatched_vector = [v for k, v in vector_by_key.items() if k not in used_vector_keys]

    return matched_pairs, unmatched_logstash, unmatched_vector


def compare_documents(logstash_docs: List[Dict], vector_docs: List[Dict]) -> Dict[str, Any]:
    """Compare Logstash and Vector documents by matching on message content"""
    results = {
        'total_logstash': len(logstash_docs),
        'total_vector': len(vector_docs),
        'matches': 0,
        'mismatches': [],
        'missing_in_vector': [],
        'field_stats': defaultdict(lambda: {'match': 0, 'mismatch': 0, 'missing': 0})
    }

    # Match documents by content
    matched_pairs, unmatched_logstash, unmatched_vector = match_documents(logstash_docs, vector_docs)

    print(f"{GREEN}✓ Matched {len(matched_pairs)} document pairs by content{NC}")

    if unmatched_logstash:
        print(f"{YELLOW}⚠ {len(unmatched_logstash)} Logstash docs not matched{NC}")
    if unmatched_vector:
        print(f"{YELLOW}⚠ {len(unmatched_vector)} Vector docs not matched{NC}")

    # Compare matched document pairs
    for i, (ls_doc, v_doc, match_key) in enumerate(matched_pairs):
        doc_match = True

        # Compare critical business fields
        for field in CRITICAL_FIELDS:
            ls_val = ls_doc.get(field)
            v_val = v_doc.get(field)

            comparison = compare_field(i, field, ls_val, v_val)

            if comparison['status'] == 'match':
                results['field_stats'][field]['match'] += 1
            else:
                results['field_stats'][field]['mismatch'] += 1
                results['mismatches'].append(comparison)
                doc_match = False

            # Track missing fields
            if ls_val is not None and v_val is None:
                results['field_stats'][field]['missing'] += 1
                results['missing_in_vector'].append({
                    'doc_index': i,
                    'field': field,
                    'logstash_value': ls_val
                })

        # Compare metadata fields
        for field in METADATA_FIELDS:
            ls_val = ls_doc.get(field)
            v_val = v_doc.get(field)
            comparison = compare_field(i, field, ls_val, v_val)
            if comparison['status'] == 'mismatch':
                results['mismatches'].append(comparison)
                doc_match = False

        if doc_match:
            results['matches'] += 1

    # Update totals for matched pairs only
    results['total_matched'] = len(matched_pairs)

    return results


def print_summary(results: Dict[str, Any]):
    """Print comparison summary"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}  Logstash vs Vector Comparison Summary{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")
    
    # Document counts
    print(f"Total Documents:")
    print(f"  Logstash: {results['total_logstash']}")
    print(f"  Vector:   {results['total_vector']}")
    print(f"  Matched:  {results.get('total_matched', min(results['total_logstash'], results['total_vector']))}")

    matched_count = results.get('total_matched', min(results['total_logstash'], results['total_vector']))
    match_rate = (results['matches'] / matched_count * 100) if matched_count > 0 else 0
    
    print(f"\nDocument-level Matches:")
    if results['matches'] == matched_count:
        print(f"  {GREEN}✓ {results['matches']}/{matched_count} documents match perfectly (100%){NC}")
    else:
        print(f"  {YELLOW}⚠ {results['matches']}/{matched_count} documents match ({match_rate:.1f}%){NC}")
    
    # Field-level statistics
    print(f"\n{BLUE}Field-by-Field Statistics:{NC}")
    print(f"{'Field':<20} {'Matches':<10} {'Mismatches':<12} {'Missing':<10}")
    print(f"{'-'*60}")
    
    for field in CRITICAL_FIELDS + METADATA_FIELDS:
        stats = results['field_stats'][field]
        match_count = stats['match']
        mismatch_count = stats['mismatch']
        missing_count = stats['missing']
        
        if mismatch_count == 0 and missing_count == 0:
            status_icon = f"{GREEN}✓{NC}"
        elif mismatch_count > 0:
            status_icon = f"{RED}✗{NC}"
        else:
            status_icon = f"{YELLOW}⚠{NC}"
        
        print(f"{status_icon} {field:<18} {match_count:<10} {mismatch_count:<12} {missing_count:<10}")
    
    # Detailed mismatches
    if results['mismatches']:
        print(f"\n{RED}Detailed Mismatches ({len(results['mismatches'])} total):{NC}")
        
        # Group by field for clarity
        mismatches_by_field = defaultdict(list)
        for mm in results['mismatches']:
            mismatches_by_field[mm['field']].append(mm)
        
        for field, mismatches in mismatches_by_field.items():
            print(f"\n  {YELLOW}{field} ({len(mismatches)} mismatches):{NC}")
            for mm in mismatches[:5]:  # Show first 5 per field
                print(f"    Doc {mm.get('doc_index', 'N/A')}: Logstash='{mm.get('logstash')}' vs Vector='{mm.get('vector')}'")
            if len(mismatches) > 5:
                print(f"    ... and {len(mismatches) - 5} more")
    
    # Missing fields
    if results['missing_in_vector']:
        print(f"\n{YELLOW}Fields Missing in Vector ({len(results['missing_in_vector'])} instances):{NC}")
        missing_by_field = defaultdict(list)
        for miss in results['missing_in_vector']:
            missing_by_field[miss['field']].append(miss)
        
        for field, missing in missing_by_field.items():
            print(f"  {field}: {len(missing)} occurrences")
            for m in missing[:3]:
                print(f"    Doc {m['doc_index']}: '{m['logstash_value']}'")
    
    # Final verdict
    print(f"\n{BLUE}{'='*60}{NC}")
    if results['matches'] == matched_count and not results['mismatches']:
        print(f"{GREEN}✓ PASS: Vector output matches Logstash baseline perfectly!{NC}")
        return 0
    elif match_rate >= 90:
        print(f"{YELLOW}⚠ PARTIAL PASS: {match_rate:.1f}% match rate (review mismatches){NC}")
        return 1
    else:
        print(f"{RED}✗ FAIL: Significant differences found ({match_rate:.1f}% match rate){NC}")
        return 2


def main():
    """Main comparison function"""
    script_dir = Path(__file__).parent
    baseline_dir = script_dir / 'data' / 'baseline'
    
    logstash_file = baseline_dir / 'logstash-baseline.json'
    vector_file = baseline_dir / 'vector-output.json'
    
    print(f"{BLUE}=== Logstash vs Vector Output Comparison ==={NC}\n")
    
    # Check files exist
    if not logstash_file.exists():
        print(f"{RED}✗ Logstash baseline not found: {logstash_file}{NC}")
        print(f"Run ./baseline_generator.sh first to generate Logstash baseline")
        return 3
    
    if not vector_file.exists():
        print(f"{RED}✗ Vector output not found: {vector_file}{NC}")
        print(f"Run ./vector_test_runner.sh first to generate Vector output")
        return 3
    
    print(f"Loading baseline files...")
    print(f"  Logstash: {logstash_file}")
    print(f"  Vector:   {vector_file}")
    
    # Load documents
    logstash_docs = load_json_lines(logstash_file)
    vector_docs = load_json_lines(vector_file)
    
    if not logstash_docs:
        print(f"{RED}✗ No Logstash documents loaded{NC}")
        return 3
    
    if not vector_docs:
        print(f"{RED}✗ No Vector documents loaded{NC}")
        return 3
    
    print(f"{GREEN}✓ Loaded {len(logstash_docs)} Logstash documents{NC}")
    print(f"{GREEN}✓ Loaded {len(vector_docs)} Vector documents{NC}")
    
    # Compare
    results = compare_documents(logstash_docs, vector_docs)
    
    # Print summary and return exit code
    return print_summary(results)


if __name__ == '__main__':
    sys.exit(main())
