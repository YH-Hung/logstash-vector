#!/usr/bin/env python3
"""
Elasticsearch Document Structure Validator
Validates that documents in Elasticsearch match expected schema
"""

import json
import sys
import requests
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'


# Expected schema definition
EXPECTED_SCHEMA = {
    # Metadata fields (always present)
    'required_fields': ['system', 'type', 'filename', 'message', 'path', 'timestamp'],
    
    # Business fields (conditional)
    'optional_fields': [
        'product', 'layer', 'maskGroupId', 'maskLotId',
        'Action', 'MaskListNo', 'rqstType', 'IsQueryPhase',
        'srvObjCategory', 'srvMethod', 'Purge_Tool',
        'MGtag', 'Ptag', 'Ltag'
    ],
    
    # Field types
    'field_types': {
        'system': str,
        'type': str,
        'filename': str,
        'message': str,
        'path': str,
        'product': str,
        'layer': str,
        'maskGroupId': str,
        'maskLotId': str,
        'Action': str,
        'MaskListNo': int,
        'rqstType': str,
        'IsQueryPhase': str,
        'srvObjCategory': str,
        'srvMethod': str,
        'Purge_Tool': str,
        'MGtag': str,
        'Ptag': str,
        'Ltag': str,
    },
    
    # Expected values for metadata
    'field_values': {
        'system': 'legendary',
        'type': 'ap_log',
    }
}


def validate_index_name(index_name: str) -> Dict[str, Any]:
    """Validate index naming convention: POD_NAMESPACE-YYYY.MM.DD"""
    result = {'valid': False, 'message': ''}
    
    # Expected format: test-namespace-YYYY.MM.DD
    parts = index_name.split('-')
    
    if len(parts) < 4:
        result['message'] = f"Invalid format: {index_name} (expected: namespace-YYYY.MM.DD)"
        return result
    
    # Extract date part (last 3 parts)
    date_part = '-'.join(parts[-3:])
    namespace = '-'.join(parts[:-3])
    
    try:
        # Try to parse date
        datetime.strptime(date_part, '%Y.%m.%d')
        result['valid'] = True
        result['message'] = f"Valid: namespace={namespace}, date={date_part}"
    except ValueError:
        result['message'] = f"Invalid date format: {date_part}"
    
    return result


def validate_document_structure(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single document against expected schema"""
    issues = []
    warnings = []
    
    # Check required fields
    for field in EXPECTED_SCHEMA['required_fields']:
        if field not in doc:
            issues.append(f"Missing required field: {field}")
    
    # Validate field types
    for field, expected_type in EXPECTED_SCHEMA['field_types'].items():
        if field in doc and doc[field] is not None:
            actual_value = doc[field]
            if not isinstance(actual_value, expected_type):
                issues.append(
                    f"Field '{field}' has wrong type: "
                    f"expected {expected_type.__name__}, got {type(actual_value).__name__}"
                )
    
    # Validate expected values
    for field, expected_value in EXPECTED_SCHEMA['field_values'].items():
        if field in doc and doc[field] != expected_value:
            warnings.append(
                f"Field '{field}' has unexpected value: "
                f"expected '{expected_value}', got '{doc[field]}'"
            )
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


def query_elasticsearch(es_url: str, index_pattern: str) -> List[Dict[str, Any]]:
    """Query Elasticsearch and return documents"""
    try:
        response = requests.get(
            f"{es_url}/{index_pattern}/_search",
            params={'size': 100},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        hits = data.get('hits', {}).get('hits', [])
        
        return [hit['_source'] for hit in hits]
    
    except requests.exceptions.RequestException as e:
        print(f"{RED}✗ Failed to query Elasticsearch: {e}{NC}")
        return []


def validate_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load documents from JSON file"""
    if not file_path.exists():
        print(f"{RED}✗ File not found: {file_path}{NC}")
        return []
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Handle Elasticsearch query response format
    if 'hits' in data:
        hits = data.get('hits', {}).get('hits', [])
        return [hit['_source'] for hit in hits]
    
    # Handle array of documents
    if isinstance(data, list):
        return data
    
    # Single document
    return [data]


def main():
    """Main validation function"""
    script_dir = Path(__file__).parent
    
    print(f"{BLUE}=== Elasticsearch Document Structure Validator ==={NC}\n")
    
    # Try to validate from file first (from baseline_generator.sh output)
    es_file = script_dir / 'data' / 'baseline' / 'elasticsearch-docs.json'
    
    documents = []
    
    if es_file.exists():
        print(f"Loading documents from: {es_file}")
        documents = validate_from_file(es_file)
        print(f"{GREEN}✓ Loaded {len(documents)} documents from file{NC}\n")
    else:
        # Try live Elasticsearch
        print("No local file found, trying live Elasticsearch...")
        es_url = "http://localhost:9200"
        index_pattern = "test-namespace-*"
        
        try:
            # Check if Elasticsearch is accessible
            response = requests.get(es_url, timeout=5)
            response.raise_for_status()
            
            print(f"{GREEN}✓ Elasticsearch is accessible{NC}")
            documents = query_elasticsearch(es_url, index_pattern)
            print(f"{GREEN}✓ Loaded {len(documents)} documents from Elasticsearch{NC}\n")
        
        except requests.exceptions.RequestException:
            print(f"{YELLOW}⚠ Elasticsearch not accessible at {es_url}{NC}")
            print(f"Run ./baseline_generator.sh first to generate test data\n")
            return 3
    
    if not documents:
        print(f"{YELLOW}⚠ No documents to validate{NC}")
        return 3
    
    # Validate documents
    print(f"{BLUE}Validating {len(documents)} documents...{NC}\n")
    
    valid_count = 0
    invalid_count = 0
    all_issues = []
    all_warnings = []
    
    for i, doc in enumerate(documents):
        validation = validate_document_structure(doc)
        
        if validation['valid']:
            valid_count += 1
        else:
            invalid_count += 1
            all_issues.extend([f"Doc {i}: {issue}" for issue in validation['issues']])
        
        all_warnings.extend([f"Doc {i}: {warn}" for warn in validation['warnings']])
    
    # Print results
    print(f"{BLUE}Validation Results:{NC}")
    print(f"  Total documents: {len(documents)}")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")
    
    if all_issues:
        print(f"\n{RED}Issues Found:{NC}")
        for issue in all_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(all_issues) > 10:
            print(f"  ... and {len(all_issues) - 10} more")
    
    if all_warnings:
        print(f"\n{YELLOW}Warnings:{NC}")
        for warning in all_warnings[:10]:
            print(f"  - {warning}")
        if len(all_warnings) > 10:
            print(f"  ... and {len(all_warnings) - 10} more")
    
    # Sample document structure
    if documents:
        print(f"\n{BLUE}Sample Document Structure:{NC}")
        sample = documents[0]
        print("Fields present:")
        for field in sorted(sample.keys()):
            field_type = type(sample[field]).__name__
            value_preview = str(sample[field])[:50]
            print(f"  - {field:<20} ({field_type:<10}) = {value_preview}")
    
    # Validate index naming (if available from ES file)
    if es_file.exists():
        with open(es_file, 'r') as f:
            data = json.load(f)
        
        if 'hits' in data:
            hits = data.get('hits', {}).get('hits', [])
            if hits:
                index_name = hits[0].get('_index', '')
                print(f"\n{BLUE}Index Naming Validation:{NC}")
                print(f"  Index: {index_name}")
                
                index_validation = validate_index_name(index_name)
                if index_validation['valid']:
                    print(f"  {GREEN}✓ {index_validation['message']}{NC}")
                else:
                    print(f"  {RED}✗ {index_validation['message']}{NC}")
    
    # Final verdict
    print(f"\n{BLUE}{'='*60}{NC}")
    if invalid_count == 0 and len(all_issues) == 0:
        print(f"{GREEN}✓ PASS: All documents conform to expected schema{NC}")
        return 0
    elif invalid_count > 0:
        print(f"{RED}✗ FAIL: {invalid_count} documents have schema violations{NC}")
        return 2
    else:
        print(f"{YELLOW}⚠ WARNINGS: Schema validation passed with warnings{NC}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
