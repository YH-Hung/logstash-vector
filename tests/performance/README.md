# Performance Testing for Vector Configuration

This directory contains performance testing tools for validating the Vector configuration's throughput, resource usage, and buffer behavior under load.

## Overview

The performance testing framework includes:
- **Load Generation**: Create scaled test data from sample logs
- **Load Testing**: Run Vector with various load levels
- **Resource Monitoring**: Track CPU and memory usage
- **Results Analysis**: Compare performance across test levels

## Quick Start

### Prerequisites
- Vector CLI installed (`vector --version`)
- Python 3.7+
- Bash shell
- `bc` command (for calculations)

### Running Tests

**Run all test levels:**
```bash
./load_test.sh all
```

**Run a specific test level:**
```bash
./load_test.sh small   # ~1,000 events
./load_test.sh medium  # ~10,000 events
./load_test.sh large   # ~100,000 events
```

## Test Levels

| Level  | Multiplier | Approx Events | Use Case |
|--------|------------|---------------|----------|
| small  | 10x        | ~1,000        | Quick validation |
| medium | 100x       | ~10,000       | Standard testing |
| large  | 1000x      | ~100,000      | Load/stress testing |

## Directory Structure

```
tests/performance/
├── README.md                 # This file
├── load_test.sh              # Main load test orchestrator
├── generate_load.py          # Test data generator
├── monitor_resources.sh      # Resource monitoring script
├── data/                     # Generated test data and configs
│   ├── load_test_*.log       # Generated test logs
│   ├── vector_test_*.yaml    # Test configurations
│   └── output_*.json         # Vector output files
└── results/                  # Test results
    ├── summary.csv           # Summary of all test runs
    ├── results_*.txt         # Detailed results per level
    └── metrics_*.csv         # Resource metrics per level
```

## Scripts

### load_test.sh

Main test orchestrator that:
1. Validates dependencies and Vector configuration
2. Generates scaled test data
3. Creates test-specific Vector configuration
4. Runs Vector and monitors resources
5. Calculates throughput metrics
6. Generates summary report

**Output:**
- `results/summary.csv` - CSV with all test metrics
- `results/results_<level>.txt` - Detailed results per test
- `results/metrics_<level>.csv` - Resource usage over time

### generate_load.py

Generates scaled test data by multiplying sample log files.

**Usage:**
```bash
python3 generate_load.py \
    --input ../integration/data/samples/web_all_fields_test.log \
    --output data/load_test.log \
    --multiplier 100
```

**Options:**
- `-i, --input`: Source log file
- `-o, --output`: Output file path
- `-m, --multiplier`: Number of times to repeat data
- `--no-timestamps`: Don't update timestamps

### monitor_resources.sh

Monitors Vector process resource usage during tests.

**Usage:**
```bash
./monitor_resources.sh <vector_pid> [interval_seconds] [output_file]
```

**Output Format (CSV):**
```
timestamp,elapsed_seconds,cpu_percent,memory_mb
2024-01-17 10:30:00,0,15.2,128.45
2024-01-17 10:30:01,1,45.8,135.22
...
```

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `input_events` | Number of events in test data |
| `output_events` | Number of events processed |
| `duration_sec` | Total processing time |
| `throughput_eps` | Events processed per second |
| `peak_memory_mb` | Maximum memory usage (MB) |
| `avg_cpu_pct` | Average CPU utilization (%) |

## Interpreting Results

### Throughput
- **Good**: > 10,000 events/sec for simple transforms
- **Expected**: 5,000-15,000 events/sec with grok parsing
- **Concern**: < 1,000 events/sec may indicate issues

### Memory Usage
- **Normal**: 50-200 MB for file source
- **High**: > 500 MB may need buffer tuning
- **Growing**: Continuous increase suggests memory leak

### CPU Usage
- **Normal**: 10-50% on modern hardware
- **High sustained**: > 80% may need optimization
- **Spiky**: Normal during parsing bursts

## Troubleshooting

### Test hangs or times out
- Check Vector logs for errors
- Verify input file format
- Reduce multiplier for initial tests

### Low throughput
- Check disk I/O performance
- Review grok patterns for efficiency
- Consider batch settings

### High memory usage
- Adjust buffer settings
- Check for large multiline events
- Review batch size configuration

## Customization

### Adjusting test levels
Edit `TEST_LEVELS` in `load_test.sh`:
```bash
declare -A TEST_LEVELS=(
    ["small"]=10
    ["medium"]=100
    ["large"]=1000
    ["xlarge"]=10000  # Add custom level
)
```

### Using different source data
Modify `SOURCE_LOG` in `load_test.sh` or use `generate_load.py` directly.

## Related Documentation

- [Integration Testing](../integration/README.md)
- [Vector Configuration](../../impl/vector.yaml)
- [Requirements](../../doc/requirements.md)
