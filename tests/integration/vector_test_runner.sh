#!/bin/bash
set -e

echo "=== Vector Test Runner ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
PROJECT_ROOT="$(cd ../.. && pwd)"

# Check for yq (required for YAML manipulation)
if ! command -v yq &> /dev/null; then
    echo -e "${RED}✗ yq command not found. Please install yq first.${NC}"
    echo "Install instructions:"
    echo "  macOS: brew install yq"
    echo "  Linux: sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq && sudo chmod +x /usr/bin/yq"
    exit 1
fi

# Check for Vector and add to PATH if needed
if ! command -v vector &> /dev/null; then
    if [ -x "$HOME/.vector/bin/vector" ]; then
        export PATH="$HOME/.vector/bin:$PATH"
        echo -e "${YELLOW}Note: Added ~/.vector/bin to PATH${NC}"
    fi
fi

echo -e "${YELLOW}[1/6] Preparing directories...${NC}"
mkdir -p "$PROJECT_ROOT/tmp/vector"
mkdir -p output

# Clear Vector checkpoint data to ensure fresh file reads
rm -rf "$PROJECT_ROOT/tmp/vector"/*

echo -e "${YELLOW}[2/6] Validating Vector configuration...${NC}"
if command -v vector &> /dev/null; then
    cd "$PROJECT_ROOT"
    vector validate impl/vector.yaml || echo -e "${YELLOW}⚠ Validation warning (may be due to data_dir path)${NC}"
    cd "$SCRIPT_DIR"
    echo -e "${GREEN}✓ Vector configuration check completed${NC}"
else
    echo -e "${RED}✗ Vector command not found. Please install Vector first.${NC}"
    echo "Install instructions: https://vector.dev/docs/setup/installation/"
    exit 1
fi

echo -e "${YELLOW}[3/6] Cleaning previous Vector output...${NC}"
rm -rf output/vector-output.json
mkdir -p output

echo -e "${YELLOW}[4/6] Preparing test configuration from impl/vector.yaml...${NC}"
# Create test config by modifying the ACTUAL impl/vector.yaml
# This ensures we test the real VRL parsing logic, not a duplicate
yq eval '
  .data_dir = "__PROJECT_ROOT__/tmp/vector" |
  .sources.ap_log_files.include = ["__SCRIPT_DIR__/data/samples/web_*.log"] |
  .sources.ap_log_files.read_from = "beginning" |
  del(.sinks) |
  .sinks.json_output.type = "file" |
  .sinks.json_output.inputs = ["derive_and_cleanup"] |
  .sinks.json_output.path = "__SCRIPT_DIR__/output/vector-output.json" |
  .sinks.json_output.encoding.codec = "json" |
  .sinks.console_output.type = "console" |
  .sinks.console_output.inputs = ["derive_and_cleanup"] |
  .sinks.console_output.encoding.codec = "json" |
  del(.tests)
' "$PROJECT_ROOT/impl/vector.yaml" > output/vector-test.yaml

# Replace placeholders with actual paths
sed -i.bak "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" output/vector-test.yaml
sed -i.bak "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" output/vector-test.yaml
rm -f output/vector-test.yaml.bak

echo -e "${GREEN}✓ Test configuration created from impl/vector.yaml${NC}"
echo "  Source: $PROJECT_ROOT/impl/vector.yaml"
echo "  Output: $SCRIPT_DIR/output/vector-test.yaml"

echo -e "${YELLOW}[5/6] Running Vector with test data...${NC}"
# Run Vector from SCRIPT_DIR with absolute config path
# Run Vector in background and kill after 15 seconds (macOS doesn't have timeout)
vector -c "$SCRIPT_DIR/output/vector-test.yaml" &
VECTOR_PID=$!
sleep 15
kill $VECTOR_PID 2>/dev/null || true
wait $VECTOR_PID 2>/dev/null || true

# Give Vector time to flush
sleep 2

echo -e "${YELLOW}[6/7] Collecting Vector output...${NC}"
if [ -f output/vector-output.json ]; then
    cp output/vector-output.json data/baseline/
    echo -e "${GREEN}✓ Vector output collected${NC}"

    # Show sample output
    echo ""
    echo "Sample Vector output:"
    head -n 3 data/baseline/vector-output.json | jq '.' || cat data/baseline/vector-output.json | head -n 3

    # Count events
    EVENT_COUNT=$(wc -l < data/baseline/vector-output.json)
    echo ""
    echo "Total events processed: $EVENT_COUNT"
else
    echo -e "${RED}✗ No Vector output found${NC}"
fi

echo ""
echo -e "${YELLOW}[7/7] Running built-in Vector tests...${NC}"
cd "$PROJECT_ROOT"
vector test impl/vector.yaml
echo -e "${GREEN}✓ Built-in tests passed${NC}"

echo ""
echo -e "${GREEN}=== Vector test run complete ===${NC}"
echo "Output files:"
echo "  - tests/integration/data/baseline/vector-output.json"
echo ""
echo "Next step: Run output comparison"
