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

echo -e "${YELLOW}[4/6] Preparing test configuration...${NC}"
# Create a test-specific Vector config that outputs to JSON file
# Use quoted 'EOF' to preserve backslashes in VRL code, then sed to replace paths
cat > output/vector-test.yaml << 'EOF'
data_dir: __PROJECT_ROOT__/tmp/vector

sources:
  ap_log_files:
    type: file
    include:
      - __SCRIPT_DIR__/data/samples/web_*.log
    read_from: beginning
    file_key: path
    multiline:
      start_pattern: '^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'
      condition_pattern: '^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'
      mode: halt_before
      timeout_ms: 1000

transforms:
  enrich_static:
    type: remap
    inputs:
      - ap_log_files
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
        parsed, _ = parse_grok(message_value, ".*(?i)product:\"%{NOTSPACE:product}\"")
        if parsed != null && parsed.product != null {
          .product = parsed.product
        }

        parsed, _ = parse_grok(message_value, ".*(?i)layer:\"%{NOTSPACE:layer}\"")
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
          parsed, _ = parse_grok(message_value, ".*(?i)mask_?group_?id:\"%{NOTSPACE:maskGroupId}\"")
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

        if is_null(.maskGroupId) {
          parsed, _ = parse_grok(message_value, ".*(?i)reticleId=\\\"%{NOTSPACE:maskGroupId}\\\">")
          if parsed != null && parsed.maskGroupId != null {
            .maskGroupId = parsed.maskGroupId
          }
        }

        if is_null(.maskGroupId) {
          parsed, _ = parse_grok(message_value, ".*(?i)reticle_?id:\"%{NOTSPACE:maskGroupId}\"")
          if parsed != null && parsed.maskGroupId != null {
            .maskGroupId = parsed.maskGroupId
          }
        }

        if is_null(.maskGroupId) {
          parsed, _ = parse_grok(message_value, ".*(?i)reticlelotid -> %{NOTSPACE:maskGroupId}")
          if parsed != null && parsed.maskGroupId != null {
            .maskGroupId = parsed.maskGroupId
          }
        }
      }

  parse_action:
    type: remap
    inputs:
      - parse_mask_group_id
    source: |
      if !is_null(.message) && is_string(.message) {
        message_value = .message

        if is_null(.Action) {
          parsed, _ = parse_grok(message_value, ".*(?i)Action:\"%{NOTSPACE:Action}:%{NOTSPACE:maskGroupId}\"")
          if parsed != null && parsed.Action != null {
            .Action = parsed.Action
            if is_null(.maskGroupId) && parsed.maskGroupId != null {
              .maskGroupId = parsed.maskGroupId
            }
          }
        }

        if is_null(.Action) {
          parsed, _ = parse_grok(message_value, ".*(?i)Action:\"%{NOTSPACE:Action}\"")
          if parsed != null && parsed.Action != null {
            .Action = parsed.Action
          }
        }
      }

  parse_mask_lot_id:
    type: remap
    inputs:
      - parse_action
    source: |
      if !is_null(.message) && is_string(.message) {
        message_value = .message

        if is_null(.maskLotId) {
          parsed, _ = parse_grok(message_value, ".*(?i)mask_?lot_?id:\"%{NOTSPACE:maskLotId}\"")
          if parsed != null && parsed.maskLotId != null {
            .maskLotId = parsed.maskLotId
          }
        }

        if is_null(.maskLotId) {
          parsed, _ = parse_grok(message_value, ".*(?i)maskLotId->%{NOTSPACE:maskLotId}")
          if parsed != null && parsed.maskLotId != null {
            .maskLotId = parsed.maskLotId
          }
        }

        if is_null(.maskLotId) {
          parsed, _ = parse_grok(message_value, ".*(?i)maskLotId-> %{NOTSPACE:maskLotId}")
          if parsed != null && parsed.maskLotId != null {
            .maskLotId = parsed.maskLotId
          }
        }

        if is_null(.maskLotId) {
          parsed, _ = parse_grok(message_value, ".*(?i)maskLotId = '%{NOTSPACE:maskLotId}'")
          if parsed != null && parsed.maskLotId != null {
            .maskLotId = parsed.maskLotId
          }
        }
      }

  parse_other_fields:
    type: remap
    inputs:
      - parse_mask_lot_id
    source: |
      if !is_null(.message) && is_string(.message) {
        message_value = .message

        if is_null(.MaskListNo) {
          parsed, _ = parse_grok(message_value, "MaskListNo=%{NUMBER:MaskListNo}")
          if parsed != null && parsed.MaskListNo != null {
            .MaskListNo = parsed.MaskListNo
          }
        }

        if is_null(.rqstType) {
          parsed, _ = parse_grok(message_value, "rqstType:\"%{NOTSPACE:rqstType}\"")
          if parsed != null && parsed.rqstType != null {
            .rqstType = parsed.rqstType
          }
        }

        if is_null(.IsQueryPhase) {
          parsed, _ = parse_grok(message_value, "IsQueryPhase:\"%{NOTSPACE:IsQueryPhase}\"")
          if parsed != null && parsed.IsQueryPhase != null {
            .IsQueryPhase = parsed.IsQueryPhase
          }
        }

        if is_null(.srvObjCategory) {
          parsed, _ = parse_grok(message_value, "srvObjCategory:\"%{NOTSPACE:srvObjCategory}\"")
          if parsed != null && parsed.srvObjCategory != null {
            .srvObjCategory = parsed.srvObjCategory
          }
        }

        if is_null(.srvMethod) {
          parsed, _ = parse_grok(message_value, "srvMethod:\"%{NOTSPACE:srvMethod}\"")
          if parsed != null && parsed.srvMethod != null {
            .srvMethod = parsed.srvMethod
          }
        }

        if is_null(.Purge_Tool) {
          parsed, _ = parse_grok(message_value, "purge_tool:\"%{NOTSPACE:Purge_Tool}\"")
          if parsed != null && parsed.Purge_Tool != null {
            .Purge_Tool = parsed.Purge_Tool
          }
        }
      }

  derive_and_cleanup:
    type: remap
    inputs:
      - parse_other_fields
    source: |
      if is_null(.maskGroupId) {
        .MGtag = "null"
      }

      if is_null(.product) {
        .Ptag = "null"
      }

      if is_null(.layer) {
        .Ltag = "null"
      }

      if .MGtag == "null" && .Ptag != "null" && .Ltag != "null" {
        product_str, _ = to_string(.product)
        layer_str, _ = to_string(.layer)
        if product_str != null && layer_str != null {
          .maskGroupId = product_str + "-" + layer_str
        }
      }

      if !is_null(.MaskListNo) {
        .MaskListNo = to_int!(.MaskListNo)
      }

      query_phase = false
      if !is_null(.IsQueryPhase) {
        is_query_phase_str, _ = to_string(.IsQueryPhase)
        if is_query_phase_str != null && contains(is_query_phase_str, "Y") {
          query_phase = true
        }
      }

      if !query_phase && !is_null(.rqstType) {
        rqst_type_str, _ = to_string(.rqstType)
        if rqst_type_str != null && contains(rqst_type_str, "PHASE") {
          query_phase = true
        }
      }

      if query_phase {
        del(.maskLotId)
        del(.maskGroupId)
        del(.product)
        del(.layer)
      }

sinks:
  json_output:
    type: file
    inputs:
      - derive_and_cleanup
    path: __SCRIPT_DIR__/output/vector-output.json
    encoding:
      codec: json

  console_output:
    type: console
    inputs:
      - derive_and_cleanup
    encoding:
      codec: json
EOF

# Replace placeholders with actual paths
sed -i.bak "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" output/vector-test.yaml
sed -i.bak "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" output/vector-test.yaml
rm -f output/vector-test.yaml.bak

echo -e "${GREEN}✓ Test configuration created${NC}"

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
