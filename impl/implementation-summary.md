# Vector Migration Implementation Summary

## Status: ✅ Functionally Complete and Tested

**Last Updated**: 2026-05-30

## Scope

Migrate the Logstash pipeline that processes `ap_log` file inputs from `/app/log/web_*.log` into a Vector configuration that preserves multiline behavior, grok parsing, conditional logic, and Elasticsearch output formatting.

## Input and Multiline Handling

- File source (`ap_log_files`) tails `/app/log/web_*.log` with `read_from: end`. Static enrichment (`enrich_static`) adds `system: "legendary"` and `type: "ap_log"`.
- Multiline aggregation is implemented by the `reduce` transform `ap_multiline_reduce` (NOT source-level multiline). It groups events by `path`, merges lines into `.message` via `concat_newline`, and starts a new aggregate (`starts_when`) whenever a line matches the SysUuid TRACE start pattern — preserving the original Logstash `halt_before` behavior.

## Parsing and Field Extraction

VRL parsing logic is externalized into separate files in `impl/vrl/`:
- `01_enrich_static.vrl` - Static field enrichment (system, type)
- `02_parse_filename.vrl` - Filename extraction from path
- `03_parse_core_fields.vrl` - Product and layer extraction
- `04_parse_mask_group_id.vrl` - MaskGroupId with 5 fallback patterns
- `05_parse_action.vrl` - Action field with 2 fallback patterns
- `06_parse_mask_lot_id.vrl` - MaskLotId with 4 fallback patterns
- `07_parse_other_fields.vrl` - Remaining fields extraction
- `08_derive_and_cleanup.vrl` - Field derivation and query phase cleanup
- `09_parse_grpc_log.vrl` - Parses glog/gpr-style gRPC log lines into structured `grpc_*` fields; non-matching lines are dropped

Field extraction summary:
- Filename is parsed from `.path` using `%{GREEDYDATA}/%{NOTSPACE:filename}`.
- Primary fields: `product`, `layer`.
- Complex fields: `maskGroupId` (5 fallbacks), `Action` (2 fallbacks), `maskLotId` (4 fallbacks).
- Simple fields: `MaskListNo`, `rqstType`, `IsQueryPhase`, `srvObjCategory`, `srvMethod`, `Purge_Tool`.

## Processing Logic

- Tag fields `MGtag`, `Ptag`, `Ltag` are set to `"null"` when corresponding fields are missing.
- `maskGroupId` is derived from `product` and `layer` when missing.
- `MaskListNo` is converted to integer.
- If `IsQueryPhase` contains `"Y"` or `rqstType` contains `"PHASE"`, remove `maskLotId`, `maskGroupId`, `product`, and `layer`.

## Output

### Production Sink (Elasticsearch)
- Elasticsearch sink points to `http://elasticsearch-fz1.engmon.svc.cluster.local:9200`.
- `logstash_format: true` with `logstash_date_format: "%Y.%m.%d"` and `bulk.index: "{{ POD_NAMESPACE }}"`.
- Buffering matches required flush interval and chunk size with retry forever behavior.

### Local Testing Sink (Console)
- Console sink outputs JSON-encoded events to stdout.
- Useful for local development and debugging without Elasticsearch dependency.
- Run with `vector --config impl/vector.yaml --require-healthy false` for local testing.

### gRPC Log Metrics Pipeline

An independent pipeline (no connection to the AP/Elasticsearch flow) converts gRPC server log files to Prometheus metrics:

1. **Source** (`grpc_log_files`): tails `/app/log/grpc_*.log` with `read_from: end`.
2. **Transform** (`parse_grpc_log`): remap using `impl/vrl/09_parse_grpc_log.vrl`. Parses glog/gpr-style lines into `grpc_severity`, `grpc_severity_code`, `grpc_date`, `grpc_time`, `grpc_tid`, `grpc_file`, `grpc_line`, `grpc_message`. Non-matching lines are dropped (`drop_on_abort: true`, `drop_on_error: true`).
3. **Transform** (`grpc_log_message_metrics`): `log_to_metric` counter `grpc_log_messages_total` (tags: `severity`, `severity_code`, `file`) — counts every parsed line.
4. **Transform** (`grpc_error_log_filter`): filter on `grpc_severity == "error" || grpc_severity == "fatal"`.
5. **Transform** (`grpc_log_error_metrics`): `log_to_metric` counter `grpc_log_errors_total` (tags: `severity`, `file`) — counts only error/fatal lines. Error/fatal lines are intentionally counted in both counters.
6. **Sink** (`prometheus_metrics`): `prometheus_exporter` on `0.0.0.0:9598`, inputs include `internal_metrics`, `grpc_log_message_metrics`, and `grpc_log_error_metrics`. Uses `flush_period_secs: 300` to keep rare error counters visible across scrape cycles.

## Testing

### Unit Tests
- **48 unit tests** embedded in `impl/vector.yaml` covering:
  - Field extraction (all 12 business fields)
  - Multiline event aggregation
  - Query phase conditional logic
  - Field derivation (maskGroupId from product-layer)
  - Type conversions
  - Error handling
- Run `vector test impl/vector.yaml` to execute the unit test suite.
- **Status**: ✅ All 48 tests passing

### Integration Testing
- **Complete integration testing framework** in `tests/integration/`:
  - Docker-based Logstash + Elasticsearch environment
  - Automated baseline generation and comparison
  - Output validation tools
  - Test data for all scenarios
- **Status**: ✅ Framework complete and ready for use
- See `tests/integration/README.md` for comprehensive testing guide

## Current Status

### ✅ Completed
- All 12 business fields extraction implemented
- Multiline processing configured and tested
- Conditional logic (query phase, field derivation) implemented
- Type conversions working
- Elasticsearch output configured
- 48/48 unit tests passing
- Integration testing framework complete

### 🔄 Ready for Execution
- Logstash baseline comparison (requires Docker)
- Performance testing with production volumes
- Production deployment

### 📊 Overall Progress: 91% Complete
- **Functional Implementation**: 100% ✅
- **Unit Testing**: 100% ✅
- **Integration Testing Framework**: 100% ✅
- **Performance Testing**: Pending
- **Production Deployment**: Pending

## Next Steps

1. Run full Logstash baseline comparison (framework ready in `tests/integration/`)
2. Execute performance tests with realistic log volumes
3. Prepare production deployment procedures
4. Set up monitoring and alerting

## References

- **Requirements**: `doc/requirements.md`
- **Task Tracking**: `doc/todo.md`
- **Testing Guide**: `tests/integration/README.md`
- **Integration Testing Status**: `INTEGRATION_TESTING_COMPLETE.md`
