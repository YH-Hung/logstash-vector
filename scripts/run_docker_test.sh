#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/output"

echo "=========================================="
echo "Docker Compose Test: Vector vs Logstash"
echo "=========================================="
echo ""

# Create output directory
echo "Creating output directory..."
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.jsonl

# Change to project root
cd "$PROJECT_ROOT"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: docker-compose or docker not found${NC}"
    exit 1
fi

# Use docker compose (newer) or docker-compose (older)
if command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}ERROR: docker compose not available${NC}"
    exit 1
fi

echo "Using: $DOCKER_COMPOSE"
echo ""

# Clean up any existing containers
echo "Cleaning up existing containers..."
$DOCKER_COMPOSE down -v 2>/dev/null || true

# Build and start services
echo "Starting Vector and Logstash services..."
echo ""

if $DOCKER_COMPOSE up --build; then
    echo ""
    echo -e "${GREEN}Services completed${NC}"
else
    echo ""
    echo -e "${YELLOW}Warning: Services exited with non-zero code (this may be expected)${NC}"
fi

# Wait a bit for files to be written
sleep 2

# Check if output files exist
VECTOR_OUTPUT="$OUTPUT_DIR/vector_output.jsonl"
LOGSTASH_OUTPUT="$OUTPUT_DIR/logstash_output.jsonl"

if [ ! -f "$VECTOR_OUTPUT" ]; then
    echo -e "${RED}ERROR: Vector output file not found: $VECTOR_OUTPUT${NC}"
    echo "Vector container logs:"
    docker logs vector_test 2>&1 | tail -50
    exit 1
fi

if [ ! -f "$LOGSTASH_OUTPUT" ]; then
    echo -e "${RED}ERROR: Logstash output file not found: $LOGSTASH_OUTPUT${NC}"
    echo "Logstash container logs:"
    docker logs logstash_test 2>&1 | tail -50
    exit 1
fi

echo ""
echo "Output files created:"
echo "  Vector:   $VECTOR_OUTPUT ($(wc -l < "$VECTOR_OUTPUT") lines)"
echo "  Logstash: $LOGSTASH_OUTPUT ($(wc -l < "$LOGSTASH_OUTPUT") lines)"
echo ""

# Run comparison
echo "Running comparison..."
echo ""

if python3 "$SCRIPT_DIR/compare_outputs.py"; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ TEST PASSED: Results are identical!"
    echo "==========================================${NC}"
    
    # Clean up
    echo ""
    echo "Cleaning up containers..."
    $DOCKER_COMPOSE down -v 2>/dev/null || true
    
    exit 0
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ TEST FAILED: Results differ"
    echo "==========================================${NC}"
    
    # Show sample outputs for debugging
    echo ""
    echo "Sample Vector output (first event):"
    head -1 "$VECTOR_OUTPUT" | python3 -m json.tool 2>/dev/null || head -1 "$VECTOR_OUTPUT"
    echo ""
    echo "Sample Logstash output (first event):"
    head -1 "$LOGSTASH_OUTPUT" | python3 -m json.tool 2>/dev/null || head -1 "$LOGSTASH_OUTPUT"
    
    # Clean up
    echo ""
    echo "Cleaning up containers..."
    $DOCKER_COMPOSE down -v 2>/dev/null || true
    
    exit 1
fi
