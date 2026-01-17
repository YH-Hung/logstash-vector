# Docker Compose Test: Vector vs Logstash

This directory contains a Docker Compose-based test that runs both Vector and Logstash configurations against the same log file (`sample/web_hmib_1.log`) and verifies they produce identical parsing results.

## Overview

The test:
1. Runs Vector with `vector/vector.test.toml` configuration
2. Runs Logstash with `sample/logstash.test.conf` configuration
3. Both process the same log file: `sample/web_hmib_1.log`
4. Outputs are written to JSONL files in the `output/` directory
5. A comparison script verifies the parsing results are identical

## Prerequisites

- Docker and Docker Compose (or `docker compose` plugin)
- Python 3.8+ (for the comparison script)

## Running the Test

### Quick Start

```bash
./scripts/run_docker_test.sh
```

This script will:
- Create the output directory
- Start both Vector and Logstash containers
- Wait for processing to complete
- Compare the outputs
- Clean up containers

### Manual Steps

If you prefer to run manually:

```bash
# 1. Create output directory
mkdir -p output

# 2. Start services
docker-compose up

# 3. Compare outputs (in another terminal)
python3 scripts/compare_outputs.py

# 4. Clean up
docker-compose down -v
```

## Configuration Files

### Vector Test Config (`vector/vector.test.toml`)

- Based on `vector/vector.toml` but outputs to JSON file instead of Elasticsearch
- Uses `read_from = "beginning"` to process the entire test file
- Outputs to `/output/vector_output.jsonl`

### Logstash Test Config (`sample/logstash.test.conf`)

- Based on `sample/logstash.conf` but adds JSON file output
- Uses `start_position => "beginning"` to process the entire test file
- Outputs to `/output/logstash_output.jsonl`
- Fixed system field value to match Vector: `"legendary"` (was `"ledgendary"`)

## Output Files

After running the test, you'll find:

- `output/vector_output.jsonl` - Parsed events from Vector
- `output/logstash_output.jsonl` - Parsed events from Logstash

Both files contain one JSON object per line (JSONL format).

## Comparison Logic

The comparison script (`scripts/compare_outputs.py`):

1. **Normalizes events** by removing metadata fields that may differ:
   - `@timestamp`, `@version`, `host`, `log`, `ecs`, `agent`
   - `file`, `path`, `message` (raw log content)
   - `tags`, `type`, `source`
   - Any field starting with `@`

2. **Compares parsed fields**:
   - Field names must match
   - Field values must match (with type normalization for numbers)
   - All events must be present in both outputs

3. **Handles type differences**:
   - String numbers are compared with actual numbers (e.g., `"123"` vs `123`)
   - Integer vs float differences are normalized

## Expected Results

When the test passes, you should see:

```
✓ SUCCESS: All events match! Vector and Logstash produce identical parsing results.
```

When there are differences, the script will show:
- Which fields differ
- The values from both systems
- The types of the values

## Troubleshooting

### No output files created

- Check container logs: `docker logs vector_test` and `docker logs logstash_test`
- Ensure the log file exists: `ls -la sample/web_hmib_1.log`
- Check file permissions in the containers

### Different number of events

This usually indicates a multiline processing difference:
- Check that both configs use the same multiline pattern
- Verify the multiline mode is correctly configured
- Review the sample log to understand expected event boundaries

### Field value mismatches

- Check for type differences (string vs number)
- Verify grok patterns match exactly
- Ensure conditional logic (field removal, combination) is identical

### Container startup issues

- Ensure Docker is running: `docker ps`
- Check available disk space: `df -h`
- Try pulling images manually: `docker pull timberio/vector:latest-alpine`

## Files Structure

```
.
├── docker-compose.yml              # Docker Compose configuration
├── vector/
│   ├── vector.toml                # Production Vector config (Elasticsearch output)
│   └── vector.test.toml           # Test Vector config (JSON file output)
├── sample/
│   ├── logstash.conf              # Original Logstash config
│   ├── logstash.test.conf          # Test Logstash config (JSON file output)
│   └── web_hmib_1.log             # Sample log file to process
├── scripts/
│   ├── run_docker_test.sh         # Main test runner script
│   └── compare_outputs.py         # Output comparison script
└── output/                        # Generated output files (gitignored)
    ├── vector_output.jsonl
    └── logstash_output.jsonl
```

## Notes

- The test configs use `read_from = "beginning"` / `start_position => "beginning"` to ensure the entire test file is processed
- Both configs output to JSONL format for easy comparison
- The comparison script ignores metadata fields that are expected to differ between Vector and Logstash
- The system field value is set to `"legendary"` in both configs (matching the Vector production config)
