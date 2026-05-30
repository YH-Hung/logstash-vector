# Agent Progress Memory

Last updated: 2026-05-30 01:48 UTC+8

## User Request

Propose and store a plan/progress memory under `./agent-memory` for:

1. Collecting AP multiline logs with a Vector `reduce` transform instead of file-source `multiline`.
2. Adding an additional Vector pipeline that identifies gRPC-style log lines with this pattern and converts them into Prometheus metrics:

   ```regex
   ^(?<sev>[IWEF])(?<date>\d{4}) (?<time>\d{2}:\d{2}:\d{2}\.\d{6})\s+(?<tid>\d+) (?<file>[^:]+):(?<line>\d+)\] (?<msg>.*)$
   ```

3. Providing documentation that guides an external C++ gRPC server to configure a `gpr` log handler through `spdlog` and set verbosity.

## Stored Plan

- Main plan: `agent-memory/reduce-multiline-grpc-metrics-plan.md`
- External server logging guide: `agent-memory/grpc-spdlog-gpr-logging-guide.md`

## Repository Facts Observed

- `impl/vector.yaml` is the main Vector config.
- `sources.ap_log_files` currently tails `/app/log/web_*.log`.
- `sources.ap_log_files` currently uses file-source `multiline` with:
  - `start_pattern`: `^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*`
  - `condition_pattern`: same regex
  - `mode`: `halt_before`
  - `timeout_ms`: `1000`
- `transforms.enrich_static` currently reads directly from `ap_log_files`.
- Existing AP parsing is externalized under `impl/vrl/01_enrich_static.vrl` through `impl/vrl/08_derive_and_cleanup.vrl`.
- `impl/vector.yaml` has embedded Vector tests, including a multiline end-to-end test that injects a pre-combined multiline message at `enrich_static`.
- `doc/monitoring.md` already documents Prometheus exporter usage on `0.0.0.0:9598`.
- `doc/deployment.md` already lists port `9598` as optional Prometheus metrics access.
- No `agent-memory` directory existed before this request.

## Toolchain (confirmed 2026-05-30)

- Vector **0.55.0** installed via `brew install vectordotdev/brew/vector` (`/opt/homebrew/bin/vector`).
- `vector validate`/`vector test` use **positional paths**, NOT `--config`: `vector validate impl/vector.yaml`, `vector test impl/vector.yaml`.
- `vector validate` needs `data_dir` to exist: `mkdir -p tmp/vector` (gitignored). Use `--no-environment` to skip env/health checks.
- Baseline green: 38 existing unit tests pass; validate reports "Validated" (ES DNS warning expected, healthcheck disabled).
- Working on branch `feat/reduce-multiline-grpc-metrics` (chosen 2026-05-30).

## Implementation State

COMPLETE and merged to `main` (merge commit, branch feat/reduce-multiline-grpc-metrics deleted). All 6 tasks done; 48/48 Vector unit tests pass; `vector validate` clean.

As-built:
- AP multiline now via `reduce` transform `ap_multiline_reduce` (group_by path, starts_when SysUuid TRACE pattern, concat_newline, expire_after_ms 1000, flush_period_ms 100); source-level multiline removed; `enrich_static` reads from it.
- gRPC pipeline: `grpc_log_files` (/app/log/grpc_*.log) → `parse_grpc_log` (impl/vrl/09_parse_grpc_log.vrl, drop_on_abort/error) → `grpc_log_message_metrics` (counter grpc_log_messages_total, tags severity/severity_code/file) and `grpc_error_log_filter` → `grpc_log_error_metrics` (counter grpc_log_errors_total, tags severity/file). Single `prometheus_metrics` exporter on 0.0.0.0:9598 (also internal_metrics), flush_period_secs 300. log_to_metric counters require `field:` (used grpc_severity).
- Docs updated: requirements.md, implementation-summary.md, monitoring.md, testing-procedures.md; external guide at agent-memory/grpc-spdlog-gpr-logging-guide.md.

Recommended implementation order:

1. Remove `multiline` from `sources.ap_log_files`.
2. Add `transforms.ap_multiline_reduce` and point `enrich_static.inputs` to it.
3. Validate with `vector validate --config impl/vector.yaml`.
4. Add a reduce-specific test and run `vector test --config impl/vector.yaml`.
5. Add `impl/vrl/09_parse_grpc_log.vrl`.
6. Add `grpc_log_files -> parse_grpc_log -> grpc_log_message_metrics/grpc_log_error_metrics -> grpc_prometheus_metrics`.
7. Add parser and metric tests.
8. Update `doc/requirements.md`, `impl/implementation-summary.md`, and `doc/monitoring.md`.
9. Provide documentation for the external C++ gRPC server team; do not add C++ server source to this repo.

## Decisions Captured

- Use `reduce` for AP multiline so raw file reads remain line-oriented and aggregation becomes testable as a transform.
- Group reduce transactions by `path` to avoid joining records from different files.
- Use `message: concat_newline` so downstream grok behavior continues to see one combined multiline message.
- Keep gRPC metric labels low-cardinality: severity and source file are safe; message, line, and thread ID should not be metric labels.
- Treat the 4-digit gRPC `date` capture as `MMDD`.
- Use `/app/log/grpc_*.log` as the proposed gRPC log source path unless deployment says the gRPC logs share the AP log files.
- Use Prometheus exporter address `0.0.0.0:9598` to align with existing monitoring docs.
- The external C++ gRPC server should use `spdlog` behind a `gpr_set_log_function` handler and write the exact regex-compatible message body, without a normal spdlog prefix.

## Open Questions For Implementation

- Confirm whether gRPC logs are written to `/app/log/grpc_*.log` or mixed into `/app/log/web_*.log`.
- Confirm the installed Vector version supports the planned `reduce` and `log_to_metric` syntax exactly.
- Confirm whether the deployment wants gRPC metrics on the existing `9598` endpoint or a separate port.
- Confirm whether the external C++ service uses a gRPC version where `gpr_set_log_function` is still available; newer gRPC versions may require Abseil logging integration instead.

## Verification Needed Later

Run after implementation:

```bash
vector validate --config impl/vector.yaml
vector test --config impl/vector.yaml
```

Run for metrics smoke testing after Vector starts:

```bash
curl -s http://localhost:9598/metrics | grep grpc_log_messages_total
```
