#!/bin/bash
#
# Monitor resource usage of Vector process during performance tests.
# Outputs CSV format data for analysis.
#
# Usage: ./monitor_resources.sh <vector_pid> [interval_seconds] [output_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
VECTOR_PID="${1:-}"
INTERVAL="${2:-1}"
OUTPUT_FILE="${3:-$SCRIPT_DIR/data/resource_metrics.csv}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <vector_pid> [interval_seconds] [output_file]"
    echo ""
    echo "Arguments:"
    echo "  vector_pid        PID of the Vector process to monitor"
    echo "  interval_seconds  Sampling interval (default: 1)"
    echo "  output_file       Output CSV file (default: data/resource_metrics.csv)"
    echo ""
    echo "Example:"
    echo "  $0 12345 1 metrics.csv"
    exit 1
}

# Validate arguments
if [[ -z "$VECTOR_PID" ]]; then
    usage
fi

if ! kill -0 "$VECTOR_PID" 2>/dev/null; then
    echo -e "${RED}Error: Process $VECTOR_PID not found${NC}"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Detect OS for platform-specific commands
OS="$(uname -s)"

get_process_stats() {
    local pid=$1

    case "$OS" in
        Darwin)
            # macOS: Use ps to get CPU and memory
            ps -p "$pid" -o %cpu=,rss= 2>/dev/null | awk '{
                cpu = $1
                rss_kb = $2
                rss_mb = rss_kb / 1024
                printf "%.1f,%.2f", cpu, rss_mb
            }'
            ;;
        Linux)
            # Linux: Use ps for consistent output
            ps -p "$pid" -o %cpu=,rss= 2>/dev/null | awk '{
                cpu = $1
                rss_kb = $2
                rss_mb = rss_kb / 1024
                printf "%.1f,%.2f", cpu, rss_mb
            }'
            ;;
        *)
            echo "0.0,0.0"
            ;;
    esac
}

# Write CSV header
echo "timestamp,elapsed_seconds,cpu_percent,memory_mb" > "$OUTPUT_FILE"

echo -e "${GREEN}Starting resource monitoring for PID $VECTOR_PID${NC}"
echo "Interval: ${INTERVAL}s"
echo "Output: $OUTPUT_FILE"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""
echo "Timestamp           | CPU %  | Memory (MB)"
echo "--------------------|--------|------------"

START_TIME=$(date +%s)
SAMPLE_COUNT=0

# Trap Ctrl+C for clean exit
cleanup() {
    echo ""
    echo -e "${GREEN}Monitoring stopped${NC}"
    echo "Total samples: $SAMPLE_COUNT"
    echo "Output saved to: $OUTPUT_FILE"
    exit 0
}
trap cleanup INT TERM

# Main monitoring loop
while kill -0 "$VECTOR_PID" 2>/dev/null; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    STATS=$(get_process_stats "$VECTOR_PID")
    if [[ -n "$STATS" ]]; then
        CPU=$(echo "$STATS" | cut -d',' -f1)
        MEMORY=$(echo "$STATS" | cut -d',' -f2)

        # Write to CSV
        echo "$TIMESTAMP,$ELAPSED,$CPU,$MEMORY" >> "$OUTPUT_FILE"

        # Print to console
        printf "%s | %5s%% | %8s MB\n" "$TIMESTAMP" "$CPU" "$MEMORY"

        SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    fi

    sleep "$INTERVAL"
done

echo -e "${YELLOW}Process $VECTOR_PID has terminated${NC}"
cleanup
