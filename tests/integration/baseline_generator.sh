#!/bin/bash
set -e

echo "=== Logstash Baseline Generator ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to script directory
cd "$(dirname "$0")"

echo -e "${YELLOW}[1/5] Cleaning previous output...${NC}"
mkdir -p output
mkdir -p data/baseline
rm -f output/logstash-baseline.json
rm -f data/baseline/logstash-*.json

echo -e "${YELLOW}[2/5] Starting Docker containers...${NC}"
docker compose up -d elasticsearch
echo "Waiting for Elasticsearch to be ready..."
sleep 20

# Wait for Elasticsearch health
echo "Checking Elasticsearch health..."
for i in {1..30}; do
    if curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green\|yellow"'; then
        echo -e "${GREEN}✓ Elasticsearch is ready${NC}"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

echo -e "${YELLOW}[3/5] Running Logstash to generate baseline...${NC}"
docker compose up -d logstash
echo "Waiting for Logstash to process logs (includes multiline auto_flush delay)..."
sleep 45

echo -e "${YELLOW}[4/5] Collecting baseline output...${NC}"
# Copy the baseline file
if [ -f output/logstash-baseline.json ]; then
    cp output/logstash-baseline.json data/baseline/
    echo -e "${GREEN}✓ Baseline JSON collected${NC}"
    
    # Show sample output
    echo ""
    echo "Sample baseline output:"
    head -n 3 data/baseline/logstash-baseline.json | jq '.' || cat data/baseline/logstash-baseline.json | head -n 3
else
    echo -e "${RED}✗ No baseline output found${NC}"
    echo "Checking Logstash logs:"
    docker compose logs logstash | tail -n 50
fi

# Query Elasticsearch for comparison
echo ""
echo -e "${YELLOW}[5/5] Querying Elasticsearch for document count...${NC}"
DOC_COUNT=$(curl -s http://localhost:9200/_cat/indices?v | grep test-namespace || echo "No documents")
echo "$DOC_COUNT"

# Save ES documents to baseline
curl -s "http://localhost:9200/test-namespace-*/_search?size=100&pretty" > data/baseline/elasticsearch-docs.json
echo -e "${GREEN}✓ Elasticsearch documents saved${NC}"

echo ""
echo -e "${GREEN}=== Baseline generation complete ===${NC}"
echo "Output files:"
echo "  - data/baseline/logstash-baseline.json (JSON lines)"
echo "  - data/baseline/elasticsearch-docs.json (ES format)"
echo ""
echo "To stop containers: docker compose down"
echo "To view logs: docker compose logs -f logstash"
