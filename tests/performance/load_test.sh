#!/usr/bin/env bash
#
# Performance load testing for Vector configuration.
# Runs Vector with various load levels and captures metrics.
#
# Usage: ./load_test.sh [test_level]
#   test_level: small (1K), medium (10K), large (100K), or all

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
VECTOR_CONFIG="$PROJECT_ROOT/impl/vector.yaml"
DATA_DIR="$SCRIPT_DIR/data"
RESULTS_DIR="$SCRIPT_DIR/results"
SOURCE_LOG="$PROJECT_ROOT/tests/integration/data/samples/web_all_fields_test.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test levels
get_multiplier() {
    case "$1" in
        small)  echo 10 ;;
        medium) echo 100 ;;
        large)  echo 1000 ;;
        *)      echo "" ;;
    esac
}

# Ensure directories exist
mkdir -p "$DATA_DIR" "$RESULTS_DIR"

log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v vector &> /dev/null; then
        log_error "Vector CLI not found. Please install Vector first."
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found. Please install Python 3.7+."
        exit 1
    fi

    if [[ ! -f "$SOURCE_LOG" ]]; then
        log_error "Source log file not found: $SOURCE_LOG"
        exit 1
    fi

    log_success "All dependencies found"
}

create_test_config() {
    local config_file="$1"
    local input_file="$2"
    local output_file="$3"

    cat > "$config_file" << EOF
data_dir: $DATA_DIR/vector_data

sources:
  test_input:
    type: file
    include:
      - $input_file
    read_from: beginning
    file_key: path

transforms:
  enrich_static:
    type: remap
    inputs:
      - test_input
    source: |
      .system = "legendary"
      .type = "ap_log"

  parse_filename:
    type: remap
    inputs:
      - enrich_static
    source: |
      if !is_null(.path) && is_string(.path) {
        filename_parsed, _ = parse_grok(.path, "%{GREEDYDATA}/%{NOTSPACE:filename}")
        if filename_parsed != null && filename_parsed.filename != null {
          .filename = filename_parsed.filename
        }
      }

  parse_core_fields:
    type: remap
    inputs:
      - parse_filename
    source: |
      if !is_null(.message) && is_string(.message) {
        message_value = .message
        parsed, _ = parse_grok(message_value, s'.*(?i)"product":"%{NOTSPACE:product}"')
        if parsed != null && parsed.product != null {
          .product = parsed.product
        }
        parsed, _ = parse_grok(message_value, s'.*(?i)"layer":"%{NOTSPACE:layer}"')
        if parsed != null && parsed.layer != null {
          .layer = parsed.layer
        }
      }

  parse_mask_group_id:
    type: remap
    inputs:
      - parse_core_fields
    source: |
      if !is_null(.message) && is_string(.message) {
        message_value = .message
        if is_null(.maskGroupId) {
          parsed, _ = parse_grok(message_value, s'.*(?i)"mask_?group_?id":"%{NOTSPACE:maskGroupId}"')
          if parsed != null && parsed.maskGroupId != null {
            .maskGroupId = parsed.maskGroupId
          }
        }
        if is_null(.maskGroupId) {
          parsed, _ = parse_grok(message_value, ".*(?i)maskGroupId-> %{NOTSPACE:maskGroupId}")
          if parsed != null && parsed.maskGroupId != null {
            .maskGroupId = parsed.maskGroupId
          }
        }
      }

  parse_other_fields:
    type: remap
    inputs:
      - parse_mask_group_id
    source: |
      if !is_null(.message) && is_string(.message) {
        message_value = .message
        parsed, _ = parse_grok(message_value, "MaskListNo=%{NUMBER:MaskListNo}")
        if parsed != null && parsed.MaskListNo != null {
          .MaskListNo = to_int!(parsed.MaskListNo)
        }
        parsed, _ = parse_grok(message_value, s'"rqstType":"%{NOTSPACE:rqstType}"')
        if parsed != null && parsed.rqstType != null {
          .rqstType = parsed.rqstType
        }
        parsed, _ = parse_grok(message_value, s'"IsQueryPhase":"%{NOTSPACE:IsQueryPhase}"')
        if parsed != null && parsed.IsQueryPhase != null {
          .IsQueryPhase = parsed.IsQueryPhase
        }
      }

  derive_and_cleanup:
    type: remap
    inputs:
      - parse_other_fields
    source: |
      MGtag = if is_null(.maskGroupId) { "null" } else { "set" }
      Ptag = if is_null(.product) { "null" } else { "set" }
      Ltag = if is_null(.layer) { "null" } else { "set" }
      if MGtag == "null" && Ptag != "null" && Ltag != "null" {
        .maskGroupId = string!(.product) + "-" + string!(.layer)
      }
      if !is_null(.IsQueryPhase) {
        isQueryPhase = string!(.IsQueryPhase)
        rqstType = if !is_null(.rqstType) { string!(.rqstType) } else { "" }
        if contains(isQueryPhase, "Y") || contains(rqstType, "PHASE") {
          del(.maskLotId)
          del(.maskGroupId)
          del(.product)
          del(.layer)
        }
      }

sinks:
  test_output:
    type: file
    inputs:
      - derive_and_cleanup
    path: $output_file
    encoding:
      codec: json
EOF
}

generate_test_data() {
    local level=$1
    local multiplier=$(get_multiplier "$level")
    local output_file="$DATA_DIR/load_test_${level}.log"

    log_info "Generating $level test data (${multiplier}x multiplier)..."

    python3 "$SCRIPT_DIR/generate_load.py" \
        --input "$SOURCE_LOG" \
        --output "$output_file" \
        --multiplier "$multiplier" >&2

    echo "$output_file"
}

run_single_test() {
    local level=$1
    local test_data=$2
    local results_file="$RESULTS_DIR/results_${level}.txt"
    local config_file="$DATA_DIR/vector_test_${level}.yaml"
    local output_file="$DATA_DIR/output_${level}.json"

    log_info "Running $level load test..."

    # Get line count
    local line_count=$(wc -l < "$test_data" | tr -d ' ')
    log_info "Processing $line_count events..."

    # Create test configuration
    create_test_config "$config_file" "$test_data" "$output_file"

    # Clean up previous output and checkpoint
    rm -f "$output_file"
    rm -rf "$DATA_DIR/vector_data"
    mkdir -p "$DATA_DIR/vector_data"

    # Record start time (use perl for sub-second precision on macOS)
    local start_time=$(perl -MTime::HiRes=time -e 'printf "%.3f\n", time')

    # Run Vector in background
    log_info "Starting Vector..."
    vector --config "$config_file" > /dev/null 2>&1 &
    local vector_pid=$!

    # Wait for Vector to complete (with timeout check)
    local wait_count=0
    local max_wait=120
    while kill -0 "$vector_pid" 2>/dev/null; do
        sleep 1
        wait_count=$((wait_count + 1))

        # Check if output file has expected number of lines
        if [[ -f "$output_file" ]]; then
            local current_lines=$(wc -l < "$output_file" 2>/dev/null | tr -d ' ')
            if [[ "$current_lines" -ge "$line_count" ]]; then
                log_info "All events processed ($current_lines/$line_count), stopping Vector..."
                kill "$vector_pid" 2>/dev/null || true
                sleep 1
                break
            fi
        fi

        if [[ $wait_count -ge $max_wait ]]; then
            log_warn "Timeout reached after ${max_wait}s, stopping Vector..."
            kill "$vector_pid" 2>/dev/null || true
            break
        fi
    done

    # Record end time
    local end_time=$(perl -MTime::HiRes=time -e 'printf "%.3f\n", time')
    local duration=$(echo "$end_time - $start_time" | bc)

    # Calculate metrics
    local output_lines=0
    if [[ -f "$output_file" ]]; then
        output_lines=$(wc -l < "$output_file" | tr -d ' ')
    fi

    local throughput=$(echo "scale=2; $output_lines / $duration" | bc 2>/dev/null || echo "0")

    # Get memory usage from ps (snapshot)
    local memory_mb="N/A"

    # Write results
    cat > "$results_file" << EOF
Test Level: $level
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
---
Input Events: $line_count
Output Events: $output_lines
Duration: ${duration}s
Throughput: ${throughput} events/sec
---
Input File: $test_data
Output File: $output_file
EOF

    log_success "Test complete: ${throughput} events/sec"

    # Return key metrics (comma-separated)
    echo "${level},${line_count},${output_lines},${duration},${throughput}"
}

run_all_tests() {
    local selected_level="${1:-all}"

    echo ""
    echo "========================================"
    echo "  Vector Performance Load Test"
    echo "========================================"
    echo ""

    check_dependencies

    # Validate Vector configuration first
    log_info "Validating Vector configuration..."
    if ! vector validate "$VECTOR_CONFIG" 2>/dev/null; then
        log_error "Vector configuration validation failed"
        exit 1
    fi
    log_success "Configuration valid"

    # Determine which tests to run
    local levels_to_run
    if [[ "$selected_level" == "all" ]]; then
        levels_to_run="small medium large"
    else
        local multiplier=$(get_multiplier "$selected_level")
        if [[ -z "$multiplier" ]]; then
            log_error "Invalid test level: $selected_level"
            echo "Valid levels: small, medium, large, all"
            exit 1
        fi
        levels_to_run="$selected_level"
    fi

    # Initialize summary file
    local summary_file="$RESULTS_DIR/summary.csv"
    echo "level,input_events,output_events,duration_sec,throughput_eps" > "$summary_file"

    # Run tests
    for level in $levels_to_run; do
        echo ""
        echo "----------------------------------------"
        echo "  Test Level: $level"
        echo "----------------------------------------"

        # Generate test data
        test_data=$(generate_test_data "$level")

        # Run test and capture result
        result=$(run_single_test "$level" "$test_data")
        echo "$result" >> "$summary_file"

        echo ""
    done

    echo ""
    echo "========================================"
    echo "  Test Summary"
    echo "========================================"
    echo ""
    cat "$summary_file" | column -t -s','
    echo ""
    log_success "Results saved to: $RESULTS_DIR/"
}

# Parse arguments
TEST_LEVEL="${1:-all}"

# Run tests
run_all_tests "$TEST_LEVEL"
