# Reduce Multiline And gRPC Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move AP log multiline aggregation out of the file source into a `reduce` transform, then add a separate gRPC log pipeline that turns C++ gRPC log lines into Prometheus metrics.

**Architecture:** Keep the existing Elasticsearch AP log pipeline intact after aggregation: `ap_log_files -> ap_multiline_reduce -> enrich_static -> ... -> derive_and_cleanup -> elasticsearch_output`. Add a second independent metrics pipeline: `grpc_log_files -> parse_grpc_log -> grpc_log_message_metrics/grpc_log_error_metrics -> prometheus_exporter`. Document the external C++ gRPC server contract: it should route gRPC Core logs through a `gpr_set_log_function` handler backed by `spdlog`, emitting regex-compatible lines like `I0530 12:34:56.123456 123 file.cc:45] message`.

**Tech Stack:** Vector YAML, Vector `reduce` transform, VRL, Vector `log_to_metric`, Vector `prometheus_exporter`, external C++ gRPC Core logging API, `spdlog`.

---

## Review Findings (2026-05-30) — Read Before Executing

This plan was reviewed against the live repository. The structure is sound; the following corrections are folded into the tasks below and MUST be respected:

1. **Prometheus port conflict.** `impl/vector.yaml` currently has **no** `prometheus_exporter` sink — only `elasticsearch_output` and `console_output`. `doc/monitoring.md:32-42` documents an *example* `internal_metrics -> prometheus_exporter` on `0.0.0.0:9598` that is **not** actually in the config. Two `prometheus_exporter` sinks cannot bind the same address. Therefore add **one** exporter on `9598` fed by all metric inputs (including `internal_metrics`), not a gRPC-only exporter that would collide later. See Task 3.
2. **Toolchain pinned to Vector 0.55.0 (installed 2026-05-30 via `brew install vectordotdev/brew/vector`).** Two CLI facts confirmed for this version, applied throughout the plan:
   - `vector validate` and `vector test` take **positional file paths**, NOT `--config` (e.g. `vector validate impl/vector.yaml`). `--config` only works on the top-level `vector` run command.
   - `vector validate` runs environment checks and fails if `data_dir` (`tmp/vector`) is absent. Run `mkdir -p tmp/vector` first (it is gitignored). Add `--no-environment` to skip env/health checks when only config-shape validation is wanted.
   - Baseline confirmed green on 2026-05-30: all 38 existing unit tests pass; `validate` reports "Validated" (an Elasticsearch DNS warning is expected — the ES host is unreachable in this env and its healthcheck is disabled).
   - Treat `reduce`, `starts_when`, `flush_period_ms`, and `log_to_metric` option names as version-sensitive — confirm each against 0.55.0 if validation complains.
3. **Reduce in unit tests is the top risk.** `vector test` must flush the open `reduce` group at end-of-input for the Task 1 test to emit. If it does not on the pinned version, fall back to the file-source integration smoke test in Task 1 Step 4b.
4. **`requirements.md` already mis-describes multiline.** `doc/requirements.md` currently documents `mode: continue_through` + negated condition, but the live config uses `mode: halt_before` with identical start/condition patterns. Task 5 must correct this description, not just append the reduce note.
5. **Existing multiline integration test stays valid.** `tests` → "Integration: multiline sample end-to-end" injects an already-combined message at `enrich_static`, so it bypasses `ap_multiline_reduce` and continues to pass unchanged. Do not delete it.

---

## Current Context

- Main config: `impl/vector.yaml`.
- Current AP file source uses source-level `multiline` under `sources.ap_log_files`.
- Existing AP parsing is split into `impl/vrl/01_enrich_static.vrl` through `impl/vrl/08_derive_and_cleanup.vrl`.
- Existing unit tests are embedded in `impl/vector.yaml`; there are 38 tests (baseline confirmed 2026-05-30), including an end-to-end multiline test that currently injects an already-combined multiline message at `enrich_static`.
- Existing monitoring docs describe a Prometheus exporter on `0.0.0.0:9598` in `doc/monitoring.md`.

## Assumptions

- AP log files remain `/app/log/web_*.log`.
- gRPC log files will be read from `/app/log/grpc_*.log`. If the gRPC server writes into the same `web_*.log` files, use a tee/filter from `ap_log_files` instead of a separate source.
- The provided gRPC log regex uses a 4-digit `date` field as `MMDD`, not a year.
- The Prometheus endpoint will be `0.0.0.0:9598`, matching existing docs.
- `gpr_set_log_function` and `gpr_set_log_verbosity` are gRPC Core APIs and are not considered a stable long-term C++ API. For newer gRPC versions that fully switch to Abseil logging, prefer an Abseil `LogSink` later.

## Target gRPC Log Pattern

```regex
^(?<sev>[IWEF])(?<date>\d{4}) (?<time>\d{2}:\d{2}:\d{2}\.\d{6})\s+(?<tid>\d+) (?<file>[^:]+):(?<line>\d+)\] (?<msg>.*)$
```

This is the canonical/documentation form using `(?<name>...)`. The VRL implementation in Task 2 uses the equivalent `(?P<name>...)` form required by VRL's Rust regex crate. Keep both in sync if the pattern ever changes.

Example line:

```text
I0530 12:34:56.123456   12345 server.cc:87] started grpc server on 0.0.0.0:50051
```

## Proposed File Structure

- Modify: `impl/vector.yaml`
  - Remove source-level multiline from `sources.ap_log_files`.
  - Add `transforms.ap_multiline_reduce`.
  - Change `transforms.enrich_static.inputs` from `ap_log_files` to `ap_multiline_reduce`.
  - Add `sources.grpc_log_files` and `sources.internal_metrics`.
  - Add `transforms.parse_grpc_log` and `transforms.grpc_error_log_filter`.
  - Add `transforms.grpc_log_message_metrics` and `transforms.grpc_log_error_metrics`.
  - Add a single `sinks.prometheus_metrics` (`prometheus_exporter` on `0.0.0.0:9598`) fed by `internal_metrics` + both gRPC metric transforms — do not create a second exporter on the same port.
  - Add unit tests for reduce aggregation and gRPC log-to-metric parsing.
- Create: `impl/vrl/09_parse_grpc_log.vrl`
  - Parse the provided regex and normalize metric tag fields.
- Modify: `doc/requirements.md`
  - Document that AP multiline aggregation is implemented by `reduce` rather than the file source.
  - Document the gRPC log metrics pipeline.
- Modify: `impl/implementation-summary.md`
  - Update status and architecture summary after implementation.
- Modify: `doc/monitoring.md`
  - Add Prometheus scrape examples for the new gRPC log metrics.
- Create: `agent-memory/grpc-spdlog-gpr-logging-guide.md`
  - Document how the external C++ gRPC server should configure `gpr` logging through `spdlog`.

## Task 0: Pin And Verify The Vector Toolchain

**Files:**
- None (environment setup)

- [ ] **Step 1: Confirm Vector is installed and capture the version**

Run:

```bash
vector --version
```

Expected: a concrete version string (e.g. `vector 0.40.0`). If the command is not found, install Vector (https://vector.dev/docs/setup/installation/) before continuing — every validation step below depends on it.

- [ ] **Step 2: Record the version in the plan/progress memory**

Note the exact version in `agent-memory/progress-memory.md`. Use that version's documentation to confirm the option names this plan relies on: `reduce.starts_when`, `reduce.expire_after_ms`, `reduce.flush_period_ms`, `reduce.merge_strategies` (`concat_newline`, `retain`), and `log_to_metric.metrics[].type: counter`. If any option name differs in that version, adjust the YAML in the affected task before running it.

- [ ] **Step 3: Establish the green baseline**

Run:

```bash
vector validate impl/vector.yaml
vector test impl/vector.yaml
```

Expected: `Configuration is valid` and all 35 existing tests pass. This is the baseline you must not regress.

## Task 1: Move AP Multiline Aggregation To `reduce`

**Files:**
- Modify: `impl/vector.yaml`

> **Semantics note:** The live source uses `mode: halt_before` with `start_pattern == condition_pattern`, i.e. each line matching the SysUuid start pattern begins a new event and following non-matching lines append until the next match. The `reduce` equivalent is `starts_when: <line matches start pattern>`, which flushes the current group and opens a new one on each match. This preserves behavior exactly.

- [ ] **Step 1: Remove source-level multiline from `ap_log_files`**

Change:

```yaml
sources:
  ap_log_files:
    type: file
    include:
      - /app/log/web_*.log
    read_from: end
    file_key: path
    multiline:
      start_pattern: '^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'
      condition_pattern: '^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'
      mode: halt_before
      timeout_ms: 1000
```

To:

```yaml
sources:
  ap_log_files:
    type: file
    include:
      - /app/log/web_*.log
    read_from: end
    file_key: path
```

- [ ] **Step 2: Add `ap_multiline_reduce` before `enrich_static`**

Insert as the first transform:

```yaml
transforms:
  # Step 0: Aggregate multiline AP log records after file ingestion
  ap_multiline_reduce:
    type: reduce
    inputs:
      - ap_log_files
    group_by:
      - path
    starts_when: 'match(to_string!(.message), r''^\[.*\]\s\s\s\[.*\]\s\[TRACE\]\sbefore\sSysUuid::set\(\):\scurSysUuid=.*'')'
    expire_after_ms: 1000
    flush_period_ms: 100
    merge_strategies:
      message: concat_newline
      path: retain

  # Step 1: Static field enrichment
  enrich_static:
    type: remap
    inputs:
      - ap_multiline_reduce
    file: impl/vrl/01_enrich_static.vrl
```

Option-name caution (resolve against the pinned version from Task 0 before running `validate`):
- `flush_period_ms` controls how often expired groups are checked. If the pinned Vector version rejects it, remove that line — `expire_after_ms: 1000` alone is sufficient for correctness.
- `path: retain` keeps the last `path` value. Because `group_by` already pins `path`, every event in a group shares it, so `retain` is effectively a no-op safety net; drop it if the version rejects the strategy name.
- All non-`message` fields use the default merge strategy (first value wins), which matches the single-timestamp behavior of the old source-level multiline.

- [ ] **Step 3: Add a focused reduce transform test**

Add a test that inserts multiple AP log lines at `ap_multiline_reduce` and asserts one reduced event contains the first and last expected lines joined with newlines.

```yaml
  - name: "Unit: ap_multiline_reduce - aggregates lines until next start"
    inputs:
      - insert_at: ap_multiline_reduce
        type: log
        log_fields:
          message: '[2026-01-16 09:10:33:130]   [a027d5c0-8560-49e7-8f82-70901077a4bf] [TRACE] before SysUuid::set(): curSysUuid=a027d5c0-8560-49e7-8f82-70901077a4bf, preSysUuid='
          path: /app/log/web_hmib_1.log
      - insert_at: ap_multiline_reduce
        type: log
        log_fields:
          message: '[2026-01-16 09:10:33:166]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rqst_DisplayInfo {"mask_lot_id":"EBGN29J.1"}'
          path: /app/log/web_hmib_1.log
      - insert_at: ap_multiline_reduce
        type: log
        log_fields:
          message: '[2026-01-16 09:10:33:211]   [8e475fe2-0680-41f2-b734-20cd691d05f9] Rep_DisplayInfo "mask_group_id":"TMEF78-376A-M001" "product":"TMEF78" "layer":"376A-M001"'
          path: /app/log/web_hmib_1.log
    outputs:
      - extract_from: ap_multiline_reduce
        conditions:
          - type: vrl
            source: |
              assert!(contains!(.message, "before SysUuid::set()"))
              assert!(contains!(.message, "Rqst_DisplayInfo"))
              assert!(contains!(.message, "Rep_DisplayInfo"))
              assert!(contains!(.message, "\n"))
```

- [ ] **Step 4: Validate AP pipeline behavior**

Run:

```bash
vector validate impl/vector.yaml
vector test impl/vector.yaml
```

Expected:

```text
Configuration is valid
All tests pass, including the new ap_multiline_reduce test
```

If Vector rejects `starts_when`, confirm the installed Vector version supports the `reduce` transform syntax and adjust the condition expression to the version-specific form before changing pipeline semantics.

- [ ] **Step 4b: Fallback if `vector test` does not flush the reduce group**

`reduce` is stateful; some Vector versions do not flush an open group at end of unit-test input, so the Step 3 test may produce zero outputs instead of failing on assertions. If that happens, do NOT weaken the assertions. Instead verify aggregation with a real file smoke test and keep the unit test as documentation:

```bash
mkdir -p /app/log
vector --config impl/vector.yaml --require-healthy false &
VECTOR_PID=$!
printf '%s\n' \
  '[2026-01-16 09:10:33:130]   [a027d5c0] [TRACE] before SysUuid::set(): curSysUuid=a027d5c0, preSysUuid=' \
  '[2026-01-16 09:10:33:166]   [8e475fe2] Rqst_DisplayInfo {"mask_lot_id":"EBGN29J.1"}' \
  '[2026-01-16 09:10:34:200]   [b1] [TRACE] before SysUuid::set(): curSysUuid=b1, preSysUuid=a027d5c0' \
  >> /app/log/web_smoke.log
sleep 2
kill $VECTOR_PID
# console_output should show ONE event whose .message contains both the SysUuid and Rqst_DisplayInfo lines joined by \n
```

Expected: the first two lines collapse into one event (flushed when the third start-pattern line arrives); the third line opens a new group.

## Task 2: Add gRPC Log Parsing VRL

**Files:**
- Create: `impl/vrl/09_parse_grpc_log.vrl`
- Modify: `impl/vector.yaml`

- [ ] **Step 1: Create the parser**

Create `impl/vrl/09_parse_grpc_log.vrl`:

```coffee
# Coerce to string first so a non-string .message produces a clean error we can drop on.
msg_str, msg_err = to_string(.message)
if msg_err != null {
  abort
}

# VRL uses the Rust regex crate; named groups use the (?P<name>...) form.
parsed, err = parse_regex(msg_str, r'^(?P<sev>[IWEF])(?P<date>\d{4}) (?P<time>\d{2}:\d{2}:\d{2}\.\d{6})\s+(?P<tid>\d+) (?P<file>[^:]+):(?P<line>\d+)\] (?P<msg>.*)$')

if err != null {
  abort
}

.grpc_log = true
.grpc_severity_code = parsed.sev
.grpc_date = parsed.date
.grpc_time = parsed.time
.grpc_tid = to_int!(parsed.tid)
.grpc_file = parsed.file
.grpc_line = to_int!(parsed.line)
.grpc_message = parsed.msg

if .grpc_severity_code == "I" {
  .grpc_severity = "info"
} else if .grpc_severity_code == "W" {
  .grpc_severity = "warning"
} else if .grpc_severity_code == "E" {
  .grpc_severity = "error"
} else if .grpc_severity_code == "F" {
  .grpc_severity = "fatal"
}
```

- [ ] **Step 2: Add the gRPC file source and parser transform**

Add to `impl/vector.yaml`:

```yaml
sources:
  grpc_log_files:
    type: file
    include:
      - /app/log/grpc_*.log
    read_from: end
    file_key: path

transforms:
  parse_grpc_log:
    type: remap
    inputs:
      - grpc_log_files
    file: impl/vrl/09_parse_grpc_log.vrl
    drop_on_abort: true
    drop_on_error: true
```

- [ ] **Step 3: Add parser tests**

Add tests in `impl/vector.yaml`:

```yaml
  - name: "Unit: parse_grpc_log - parses grpc log line"
    inputs:
      - insert_at: parse_grpc_log
        type: log
        log_fields:
          message: "I0530 12:34:56.123456   12345 server.cc:87] started grpc server"
          path: "/app/log/grpc_server.log"
    outputs:
      - extract_from: parse_grpc_log
        conditions:
          - type: vrl
            source: |
              assert_eq!(.grpc_log, true)
              assert_eq!(.grpc_severity_code, "I")
              assert_eq!(.grpc_severity, "info")
              assert_eq!(.grpc_date, "0530")
              assert_eq!(.grpc_time, "12:34:56.123456")
              assert_eq!(.grpc_tid, 12345)
              assert_eq!(.grpc_file, "server.cc")
              assert_eq!(.grpc_line, 87)
              assert_eq!(.grpc_message, "started grpc server")

  - name: "Unit: parse_grpc_log - parses grpc error log line"
    inputs:
      - insert_at: parse_grpc_log
        type: log
        log_fields:
          message: "E0530 12:35:01.000042   12345 transport.cc:201] connection reset"
          path: "/app/log/grpc_server.log"
    outputs:
      - extract_from: parse_grpc_log
        conditions:
          - type: vrl
            source: |
              assert_eq!(.grpc_severity_code, "E")
              assert_eq!(.grpc_severity, "error")
              assert_eq!(.grpc_file, "transport.cc")
              assert_eq!(.grpc_line, 201)
```

Confirm non-matching lines are dropped with a local file-source smoke test after `vector validate`, because Vector unit-test output blocks are better suited to positive transform assertions.

## Task 3: Convert gRPC Log Events To Prometheus Metrics

**Files:**
- Modify: `impl/vector.yaml`
- Modify: `doc/monitoring.md`

- [ ] **Step 1: Add `log_to_metric` transforms**

Add:

```yaml
transforms:
  grpc_error_log_filter:
    type: filter
    inputs:
      - parse_grpc_log
    condition: '.grpc_severity == "error" || .grpc_severity == "fatal"'

  grpc_log_message_metrics:
    type: log_to_metric
    inputs:
      - parse_grpc_log
    metrics:
      - type: counter
        name: grpc_log_messages_total
        tags:
          severity: "{{ grpc_severity }}"
          severity_code: "{{ grpc_severity_code }}"
          file: "{{ grpc_file }}"

  grpc_log_error_metrics:
    type: log_to_metric
    inputs:
      - grpc_error_log_filter
    metrics:
      - type: counter
        name: grpc_log_errors_total
        tags:
          severity: "{{ grpc_severity }}"
          file: "{{ grpc_file }}"
```

The separate filter branch avoids relying on version-specific per-metric condition support inside `log_to_metric`.

- [ ] **Step 2: Add a single Prometheus exporter on 9598**

`impl/vector.yaml` has no exporter today, and `doc/monitoring.md` documents an `internal_metrics` exporter on the same `9598`. Add **one** exporter fed by both Vector's internal metrics and the gRPC log metrics so the port is never double-bound. Add the source and sink:

```yaml
sources:
  # Vector's own operational metrics (matches doc/monitoring.md example)
  internal_metrics:
    type: internal_metrics

sinks:
  prometheus_metrics:
    type: prometheus_exporter
    inputs:
      - internal_metrics
      - grpc_log_message_metrics
      - grpc_log_error_metrics
    address: "0.0.0.0:9598"
```

If a deployment genuinely needs gRPC metrics isolated on a different port, give that second exporter a distinct `address` (e.g. `0.0.0.0:9599`) and update `doc/deployment.md` (port list at line 53 / containerPort at line 299) plus `doc/monitoring.md`. Do not reuse `9598` for two exporters.

- [ ] **Step 3: Validate metrics output locally**

Run Vector and write one matching line into the configured log file:

```bash
vector --config impl/vector.yaml --require-healthy false
printf '%s\n' 'I0530 12:34:56.123456   12345 server.cc:87] started grpc server' >> /app/log/grpc_server.log
curl -s http://localhost:9598/metrics | grep grpc_log_messages_total
```

Expected metric shape:

```text
grpc_log_messages_total{file="server.cc",severity="info",severity_code="I"} 1
```

## Task 4: Document External C++ gRPC Server Logging

**Files:**
- Create: `agent-memory/grpc-spdlog-gpr-logging-guide.md`

- [ ] **Step 1: Keep server implementation out of this repository**

The C++ gRPC server is external to this repository. Do not add C++ source files, build files, or service startup code here. This repo should only document the logging contract that the external server must satisfy so Vector can parse the emitted log file.

- [ ] **Step 2: Provide a spdlog-based gpr logging guide**

Use `agent-memory/grpc-spdlog-gpr-logging-guide.md` as the guide for the external server team. The guide covers:

- registering `gpr_set_log_function()` before gRPC server startup;
- setting `gpr_set_log_verbosity()` from `GRPC_VERBOSITY`;
- routing gRPC Core logs through `spdlog`;
- configuring the `spdlog` pattern as `%v` so Vector receives the exact regex-compatible line;
- writing to `/app/log/grpc_server.log` by default, configurable through `GRPC_LOG_FILE`;
- verifying that emitted lines match `^[IWEF]\d{4} ...`.

- [ ] **Step 3: Align Vector docs with the external logging contract**

Document that the Vector gRPC metrics pipeline expects the external server to write lines like:

```text
I0530 12:34:56.123456   12345 server.cc:87] started grpc server
```

If deployment uses a different log path than `/app/log/grpc_server.log`, update the planned `sources.grpc_log_files.include` glob accordingly.

## Task 5: Documentation And Validation

**Files:**
- Modify: `doc/requirements.md`
- Modify: `impl/implementation-summary.md`
- Modify: `doc/monitoring.md`

- [ ] **Step 1: Update requirements**

The existing `doc/requirements.md` "Multiline Processing" section describes `mode: continue_through` with a negated condition. That never matched the live config (which used `mode: halt_before` with identical start/condition patterns), so **rewrite** that section rather than appending to it. The corrected section must state:

- Multiline aggregation is implemented by the Vector `reduce` transform (`transforms.ap_multiline_reduce`), not source-level `multiline`.
- Grouping is by `path` (`group_by`), and lines are merged into `.message` via `concat_newline`.
- A new aggregate starts when a line matches the SysUuid start pattern (`starts_when`), which is the `reduce` equivalent of the former `halt_before` behavior; the AP start pattern itself is unchanged.
- The gRPC metrics pipeline only counts lines matching the provided regex; non-matching gRPC lines are dropped (`drop_on_abort`/`drop_on_error`) and never reach the exporter.

- [ ] **Step 2: Update monitoring docs**

Add example Prometheus queries:

```promql
sum by (severity) (grpc_log_messages_total)
sum by (file) (rate(grpc_log_messages_total[5m]))
sum(rate(grpc_log_errors_total[5m]))
```

- [ ] **Step 3: Run final verification**

Run:

```bash
vector validate impl/vector.yaml
vector test impl/vector.yaml
```

Expected:

```text
Configuration is valid
All Vector unit tests pass
```

## Implementation Notes

- Keep the AP Elasticsearch pipeline and query-phase field removal logic unchanged.
- Preserve the AP multiline regex exactly unless a Vector validation error proves escaping needs adjustment.
- Keep gRPC metrics labels low-cardinality. `file` and `severity` are acceptable; do not tag full `msg`, `line`, or `tid`.
- If `/app/log/grpc_*.log` is not available in the deployment, configure the external C++ service's `GRPC_LOG_FILE` or the Vector source glob so both sides use the same file path.
- If this repo's Vector version does not support `condition` inside `log_to_metric.metrics`, implement the error/fatal counter as a separate `filter -> log_to_metric` branch.

## Self-Review

- Spec coverage: covers reduce-based multiline, the gRPC regex parser, Prometheus metrics conversion, and external C++ gRPC `gpr` logging documentation with `spdlog`.
- Placeholder scan: no unresolved planning markers are included; assumptions are explicit.
- Type consistency: gRPC parser fields are consistently named `grpc_*`; metric tags reference those fields. The sink is named `prometheus_metrics` consistently (no leftover `grpc_prometheus_metrics` references).
- Verified against the live repo (2026-05-30): `impl/vrl/01..08` exist; `enrich_static` reads `ap_log_files`; 35 embedded tests exist; no `reduce`/`log_to_metric`/`prometheus_exporter` is present yet; `doc/monitoring.md` and `doc/deployment.md` reference `9598`.
- Resolved risks (folded into tasks): (a) single exporter on `9598` to avoid binding the port twice; (b) Task 0 pins the Vector version since `vector` is not installed here; (c) Task 1 Step 4b gives a file smoke-test fallback if `vector test` does not flush the open `reduce` group.
- Remaining risk to confirm during execution: exact option names on the pinned Vector version (`flush_period_ms`, `merge_strategies` names, `log_to_metric.metrics`) — resolve via `vector validate` before changing pipeline semantics.
