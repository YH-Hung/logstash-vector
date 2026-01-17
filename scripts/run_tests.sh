#!/bin/bash
# Single command test runner for Vector configuration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Logstash to Vector Migration - Test Runner ==="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} uv is installed"

# Check if Vector is installed
if ! command -v vector &> /dev/null; then
    echo -e "${YELLOW}Warning: Vector binary not found in PATH${NC}"
    echo "Some tests may be skipped if Vector is not available"
else
    echo -e "${GREEN}✓${NC} Vector is installed"
    vector --version
fi

echo ""
echo "Installing dependencies with uv..."
uv sync

echo ""
echo "Running tests with pytest..."
echo ""

# Run pytest through uv
uv run pytest "$@"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi

exit $EXIT_CODE
