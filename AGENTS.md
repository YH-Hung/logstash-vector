# AGENTS.md

## Purpose
This repository contains configuration, documentation, and sample data for a Logstash → Vector migration. There is no compiled application or conventional test suite; most work involves editing YAML, VRL, and documentation.

## Repository Layout
- `impl/vector.yaml`: Primary Vector configuration and VRL transform logic.
- `doc/requirements.md`: Detailed migration requirements and parsing rules.
- `doc/todo.md`: Task checklist and validation notes.
- `sample/`: Sample Logstash/Fluentd configs and example log file.
- `tmp/`: Local Vector data directory (runtime output).

## Build / Lint / Test Commands
### Summary
- No build system (no `package.json`, `pyproject.toml`, `Cargo.toml`, `Makefile`, or `go.mod`).
- No lint config detected.
- No automated tests detected.

### Suggested Validation (Manual)
These commands are not defined in the repo but are common for Vector setups if the `vector` CLI is installed locally.

- Validate config syntax:
  - `vector validate --config impl/vector.yaml`
- Run Vector with the config:
  - `vector --config impl/vector.yaml`
- Run with a specific log file (if Vector supports `--require-healthy` in your setup):
  - `vector --config impl/vector.yaml --require-healthy`

### Single-Test Equivalents
There is no test runner, so there is no single-test command. Use one of the manual checks above.

## Code Style Guidelines
### General
- Prefer minimal, focused edits to configs and docs.
- Keep changes aligned to the migration requirements in `doc/requirements.md`.
- Avoid unrelated refactors; keep changes small and traceable.

### YAML (Vector Config)
- Use 2 spaces for indentation.
- Keep component names short and descriptive (e.g., `parse_fields`, `ap_log_files`).
- Group `sources`, `transforms`, and `sinks` in that order.
- Use explicit scalar values (avoid implicit YAML booleans like `on/off` if unclear).
- Maintain consistent quoting style; use single quotes for regex patterns.

### VRL (Vector Remap Language)
- Prefer explicit `to_string!()` and `to_int!()` conversions when types are expected.
- Use `parse_grok!()` only when parsing is required; otherwise use `parse_grok()`.
- Guard parsing with `is_null()` checks to avoid overwriting existing fields.
- Use `del()` for conditional field removal instead of assigning `null`.
- Keep VRL blocks in a logical order: enrich → parse → derive → convert → cleanup.

### Imports / Dependencies
- There are no language-level imports or dependencies in this repo.
- Do not add new build tools or dependency manifests unless explicitly requested.
- **Python dependencies**: Python scripts in `tests/integration/` use `uv` for dependency management. Always use `uv venv` and `uv pip install` rather than system `pip`.

### Naming Conventions
- Match existing field names exactly (case-sensitive): e.g., `maskGroupId`, `MaskListNo`, `IsQueryPhase`.
- Prefer `snake_case` for Vector component names and local VRL variables.
- Do not rename fields that are referenced by downstream systems.

### Error Handling
- Parsing failures should not stop the pipeline. Use `parse_grok()` or guarded `parse_grok!()` calls.
- Keep transforms resilient: check for `null` and handle missing fields gracefully.
- Avoid throwing errors unless a field is truly required for correctness.

### Formatting
- Keep lines readable; wrap long regex patterns only if doing so preserves YAML/VRL validity.
- Preserve the existing ordering of grok fallback patterns.
- Avoid adding inline comments unless needed to clarify non-obvious logic.

### Documentation Updates
- Update `doc/requirements.md` or `impl/implementation-summary.md` when behavior changes.
- Keep documentation factual, not speculative.

## Cursor / Copilot Rules
- No `.cursor/rules/` or `.cursorrules` found.
- No `.github/copilot-instructions.md` found.

## Change Safety Checklist
- Confirm changes preserve the parsing patterns defined in `doc/requirements.md`.
- Validate config syntax with `vector validate` if available.
- Ensure multiline regexes and grok patterns remain unchanged unless explicitly required.
- Verify field removal logic for query-phase events is intact.

## Notes for Agentic Changes
- Prefer modifying `impl/vector.yaml` over adding new files.
- Sample log files in `sample/` should be treated as reference data; do not edit unless requested.
- Keep `tmp/` free of committed artifacts.
