#!/usr/bin/env python3
"""
Generate scaled test data for Vector performance testing.

This script multiplies existing test log samples to create larger datasets
for load testing purposes.
"""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path


def generate_timestamp():
    """Generate a realistic timestamp for log entries."""
    base_time = datetime.now()
    offset = random.randint(0, 3600)  # Random offset within an hour
    ts = base_time - timedelta(seconds=offset)
    return ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def process_log_line(line: str, line_num: int) -> str:
    """Process a log line, optionally updating timestamps."""
    # If line starts with a timestamp pattern, update it
    if line and line[0] == '[':
        # Try to find and replace timestamp
        try:
            bracket_end = line.index(']')
            new_ts = generate_timestamp()
            return f"[{new_ts}]{line[bracket_end+1:]}"
        except (ValueError, IndexError):
            pass
    return line


def generate_load_data(
    input_file: str,
    output_file: str,
    multiplier: int,
    update_timestamps: bool = True
):
    """
    Generate scaled test data by multiplying input file contents.

    Args:
        input_file: Path to source log file
        output_file: Path to output file
        multiplier: Number of times to repeat the data
        update_timestamps: Whether to generate new timestamps
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    with open(input_file, 'r') as f:
        lines = f.readlines()

    if not lines:
        print(f"Error: Input file is empty: {input_file}")
        sys.exit(1)

    total_lines = len(lines) * multiplier
    print(f"Generating {total_lines:,} lines ({multiplier}x multiplier)...")

    with open(output_file, 'w') as f:
        for iteration in range(multiplier):
            for line_num, line in enumerate(lines):
                if update_timestamps:
                    line = process_log_line(line, line_num)
                f.write(line)
                if not line.endswith('\n'):
                    f.write('\n')

            # Progress indicator for large multipliers
            if multiplier >= 100 and (iteration + 1) % (multiplier // 10) == 0:
                progress = (iteration + 1) / multiplier * 100
                print(f"  Progress: {progress:.0f}%")

    output_size = os.path.getsize(output_file)
    print(f"Generated: {output_file}")
    print(f"  Lines: {total_lines:,}")
    print(f"  Size: {output_size / 1024 / 1024:.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Generate scaled test data for Vector performance testing"
    )
    parser.add_argument(
        "-i", "--input",
        default="tests/integration/data/samples/web_all_fields_test.log",
        help="Input log file (default: tests/integration/data/samples/web_all_fields_test.log)"
    )
    parser.add_argument(
        "-o", "--output",
        default="tests/performance/data/load_test.log",
        help="Output file (default: tests/performance/data/load_test.log)"
    )
    parser.add_argument(
        "-m", "--multiplier",
        type=int,
        default=100,
        help="Number of times to repeat the data (default: 100)"
    )
    parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="Don't update timestamps in generated data"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    generate_load_data(
        args.input,
        args.output,
        args.multiplier,
        update_timestamps=not args.no_timestamps
    )


if __name__ == "__main__":
    main()
