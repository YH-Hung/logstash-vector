#!/bin/bash
set -e

echo "========================================"
echo "  Logstash → Vector Integration Tests"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$SCRIPT_DIR"

# Check for Vector and add to PATH if needed
if ! command -v vector &> /dev/null; then
    if [ -x "$HOME/.vector/bin/vector" ]; then
        export PATH="$HOME/.vector/bin:$PATH"
        echo -e "${YELLOW}Note: Added ~/.vector/bin to PATH${NC}"
    else
        echo -e "${RED}✗ Vector command not found.${NC}"
        echo "Install Vector: https://vector.dev/docs/setup/installation/"
        echo "Or if installed via official script: export PATH=\"\$HOME/.vector/bin:\$PATH\""
        exit 1
    fi
fi

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test step
run_test_step() {
    local step_name="$1"
    local command="$2"
    
    echo -e "${BLUE}[TEST] $step_name${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ PASS: $step_name${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL: $step_name${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Main test sequence
echo -e "${YELLOW}Phase 1: Vector Built-in Unit Tests${NC}"
echo "------------------------------------"
run_test_step "Vector unit tests" "vector test '$PROJECT_ROOT/impl/vector.yaml'"
echo ""

echo -e "${YELLOW}Phase 2: Vector Configuration Validation${NC}"
echo "-----------------------------------------"
echo "Validating Vector configuration..."
run_test_step "Vector config validation" "vector validate --no-environment '$PROJECT_ROOT/impl/vector.yaml'"
echo ""

echo -e "${YELLOW}Phase 3: Optional Logstash Baseline Comparison${NC}"
echo "------------------------------------------------"
echo ""
echo -e "${BLUE}Note: To enable full baseline comparison:${NC}"
echo "  1. Ensure Docker is running"
echo "  2. Run: ./baseline_generator.sh"
echo "  3. Set up Python environment: uv venv .venv && source .venv/bin/activate && uv pip install requests"
echo "  4. Run: source .venv/bin/activate && python3 compare_outputs.py"
echo ""
echo "For now, checking if baseline comparison is possible..."
if [ -f "data/baseline/logstash-baseline.json" ] && [ -f "data/baseline/vector-output.json" ]; then
    echo "Baseline files found! Running comparison..."
    # Check if venv exists, create if not
    if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment with uv..."
        uv venv .venv
        source .venv/bin/activate
        uv pip install requests
    else
        source .venv/bin/activate
    fi
    run_test_step "Logstash vs Vector comparison" "python3 compare_outputs.py"
elif [ -f "data/baseline/vector-output.json" ]; then
    echo "Vector output found, but no Logstash baseline for comparison"
    echo -e "${GREEN}✓ Vector test execution completed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Skipping baseline comparison (files not found)${NC}"
    echo "  Run ./baseline_generator.sh first to generate Logstash baseline"
fi
echo ""

echo -e "${YELLOW}Phase 4: Test Summary${NC}"
echo "--------------------"
echo ""
echo "Integration Test Results:"
echo "  Passed: $TESTS_PASSED"
echo "  Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests FAILED${NC}"
    exit 1
fi
