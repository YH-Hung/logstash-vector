# CLI Interface Contract

**Tool**: `lv-py` (Logstash to Vector migration tool - Python implementation)
**Version**: 0.1.0
**Date**: 2025-12-31

## Command Overview

```bash
lv-py migrate [OPTIONS] DIRECTORY
```

Migrates Logstash configuration files (`.conf`) in DIRECTORY to Vector TOML format (`.toml`).

---

## Commands

### `lv-py migrate`

**Description**: Migrate all Logstash `.conf` files in a directory to Vector `.toml` format.

**Usage**:
```bash
lv-py migrate [OPTIONS] DIRECTORY
```

**Arguments**:

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `DIRECTORY` | Path | Yes | Directory containing Logstash `.conf` files (FR-001) |

**Options**:

| Option | Short | Type | Default | Description | Requirement |
|--------|-------|------|---------|-------------|-------------|
| `--dry-run` | `-n` | Flag | `false` | Preview migration without writing files | FR-014 |
| `--output-dir` | `-o` | Path | Same as input | Output directory for Vector configs | Extension of FR-007 |
| `--report` | `-r` | Path | `<dir>/migration-report.md` | Path for migration report | FR-010 |
| `--validate` | `-v` | Flag | `true` | Validate generated configs with `vector validate` | FR-015 |
| `--no-validate` | | Flag | `false` | Skip Vector validation (faster but risky) | |
| `--overwrite` | `-f` | Flag | `false` | Overwrite existing `.toml` files without prompting | Edge case |
| `--verbose` | | Flag | `false` | Show detailed progress and debug information | |
| `--quiet` | `-q` | Flag | `false` | Suppress all output except errors | |
| `--help` | `-h` | Flag | - | Show help message | |

**Examples**:

```bash
# Basic migration
lv-py migrate /etc/logstash/conf.d/

# Dry run to preview changes
lv-py migrate --dry-run /etc/logstash/conf.d/

# Custom output directory
lv-py migrate -o /etc/vector/config.d/ /etc/logstash/conf.d/

# Skip validation (faster, less safe)
lv-py migrate --no-validate /etc/logstash/conf.d/

# Force overwrite existing configs
lv-py migrate --overwrite /etc/logstash/conf.d/

# Verbose mode with custom report location
lv-py migrate --verbose --report /tmp/migration.md /etc/logstash/conf.d/
```

**Exit Codes**:

| Code | Meaning | When |
|------|---------|------|
| `0` | Success | All configs migrated successfully, 100% validation passed |
| `1` | Partial success | Some configs migrated, some unsupported (check report) |
| `2` | Validation failed | Generated configs failed `vector validate` (SC-003 violation) |
| `3` | Parse error | Could not parse Logstash configs (FR-013) |
| `4` | File system error | Directory not found, permission denied, etc. |

**Output (stdout)**:

```
Migrating Logstash configs from: /etc/logstash/conf.d/
Found 5 configuration files

[1/5] pipeline.conf
  ✓ 3 inputs migrated (file, beats, syslog)
  ✓ 5 filters migrated (grok, mutate, date)
  ✓ 2 outputs migrated (elasticsearch, file)
  ⚠ 1 unsupported filter: ruby (manual migration required)

[2/5] monitoring.conf
  ✓ 1 input migrated (beats)
  ✓ 1 output migrated (elasticsearch)

[3/5] ...

Migration complete!
  Total configs: 5
  Successfully migrated: 4 (80%)
  Partially migrated: 1 (20%)
  Failed: 0

Generated Vector configs:
  /etc/logstash/conf.d/pipeline.toml
  /etc/logstash/conf.d/monitoring.toml
  ...

Migration report: /etc/logstash/conf.d/migration-report.md

⚠ Review unsupported features in the migration report before deploying.
```

**Output (dry-run mode)**:

```
[DRY RUN] No files will be written

Migrating Logstash configs from: /etc/logstash/conf.d/
Found 5 configuration files

Would create:
  /etc/logstash/conf.d/pipeline.toml (2.3 KB)
    - file input → file source
    - grok filter → remap transform
    - elasticsearch output → elasticsearch sink
    ⚠ ruby filter unsupported (TODO marker added)

  /etc/logstash/conf.d/monitoring.toml (1.1 KB)
    - beats input → http source
    - elasticsearch output → elasticsearch sink

...

[DRY RUN] Run without --dry-run to write files
```

**Error Output (stderr)**:

```
Error: Directory not found: /nonexistent/path
Error: Permission denied reading /etc/logstash/conf.d/restricted.conf
Error: Parse error in pipeline.conf:42: Unexpected token '}'
Error: Vector validation failed for output.toml: Invalid sink type 'unknown'
```

---

### `lv-py validate`

**Description**: Validate Vector TOML files using `vector validate` command (FR-015).

**Usage**:
```bash
lv-py validate [OPTIONS] [FILES...]
```

**Arguments**:

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `FILES` | Paths | No | Vector `.toml` files to validate (default: all `.toml` in current dir) |

**Examples**:

```bash
# Validate specific files
lv-py validate pipeline.toml monitoring.toml

# Validate all .toml files in current directory
lv-py validate

# Validate all .toml files in directory
lv-py validate /etc/vector/config.d/*.toml
```

**Exit Codes**:
- `0`: All configs valid
- `1`: One or more configs invalid

---

### `lv-py diff`

**Description**: Compare Logstash and Vector configurations side-by-side (FR-014, User Story 3).

**Usage**:
```bash
lv-py diff LOGSTASH_CONF VECTOR_TOML
```

**Arguments**:

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `LOGSTASH_CONF` | Path | Yes | Original Logstash `.conf` file |
| `VECTOR_TOML` | Path | Yes | Generated Vector `.toml` file |

**Output**:

```
Comparing: pipeline.conf ↔ pipeline.toml

Inputs (Logstash → Vector):
  ✓ file { path => "/var/log/*.log" }
    → sources.file_logs
      type = "file"
      include = ["/var/log/*.log"]

Filters (Logstash → Vector):
  ✓ grok { match => { "message" => "%{COMBINEDAPACHELOG}" } }
    → transforms.parse_logs
      type = "remap"
      source = 'parse_groks!(.message, patterns: ["%{COMBINEDAPACHELOG}"])'

  ⚠ ruby { code => "event.set('custom', ...)" }
    → [UNSUPPORTED] Manual TODO added in Vector config

Outputs (Logstash → Vector):
  ✓ elasticsearch { hosts => ["localhost:9200"] }
    → sinks.es_output
      type = "elasticsearch"
      endpoints = ["http://localhost:9200"]

Summary:
  Matched: 3 components
  Unsupported: 1 component
  Functional equivalence: Partial (review unsupported features)
```

---

### `lv-py version`

**Description**: Show version information.

**Usage**:
```bash
lv-py version
```

**Output**:
```
lv-py version 0.1.0 (Python implementation)
Python: 3.11.7
Dependencies:
  pyparsing: 3.1.0
  tomlkit: 0.12.0
  click: 8.1.0
  pydantic: 2.5.0
```

---

## Migration Report Format

**Location**: `<input-dir>/migration-report.md` (default) or custom path via `--report`

**Format**: Markdown

**Structure**:

```markdown
# Logstash to Vector Migration Report

**Date**: 2025-12-31 14:30:00 UTC
**Source**: /etc/logstash/conf.d/
**Target**: /etc/logstash/conf.d/ (Vector configs)

## Summary

| Metric | Value |
|--------|-------|
| Total configs | 5 |
| Successfully migrated | 4 (80%) |
| Partially migrated | 1 (20%) |
| Failed | 0 (0%) |
| Total plugins | 15 |
| Supported plugins | 13 (87%) |
| Unsupported plugins | 2 (13%) |

## Migrated Configurations

### pipeline.conf → pipeline.toml

**Status**: ✅ Partial (1 unsupported feature)

**Supported Plugins**:
- `input.file` → `sources.file_logs` (file source)
- `filter.grok` → `transforms.parse_logs` (remap transform)
- `output.elasticsearch` → `sinks.es_output` (elasticsearch sink)

**Unsupported Plugins**:

#### ruby filter (line 42)

**Location**: `pipeline.conf:42`

**Original Configuration**:
```ruby
filter {
  ruby {
    code => "event.set('custom_field', Time.now.to_i)"
  }
}
```

**Manual Migration Guidance**:
The Logstash `ruby` filter executes arbitrary Ruby code at runtime. Vector does not support arbitrary code execution for security and performance reasons.

**Vector Alternatives**:
1. **Remap transform**: If the Ruby code performs simple field manipulation, use VRL (Vector Remap Language). For timestamp operations, use `now()` function:
   ```toml
   [transforms.add_timestamp]
   type = "remap"
   inputs = ["parse_logs"]
   source = '.custom_field = to_unix_timestamp(now())'
   ```

2. **Lua transform**: For more complex logic, use Vector's `lua` transform (limited Lua runtime):
   ```toml
   [transforms.custom_logic]
   type = "lua"
   inputs = ["parse_logs"]
   source = '''
     function process(event, emit)
       event.log.custom_field = os.time()
       emit(event)
     end
   '''
   ```

3. **External service**: If neither VRL nor Lua suffice, send logs to external HTTP endpoint for processing.

**TODO**: Review generated `pipeline.toml` for `# TODO: Manual migration required` comment at corresponding location.

---

### monitoring.conf → monitoring.toml

**Status**: ✅ Fully migrated

... (repeat for each config)

---

## Warnings

- Environment variable interpolation found in 2 configs (flagged for manual review)
- Deprecated Logstash plugin detected: `multiline` codec (use Vector's `multiline` option instead)

## Next Steps

1. Review all unsupported plugins above and implement Vector alternatives
2. Test generated Vector configs: `vector validate /etc/logstash/conf.d/*.toml`
3. Run integration tests with sample logs to verify functional equivalence
4. Deploy Vector configs to staging environment before production

---

*Generated by lv-py v0.1.0*
```

---

## Configuration File Handling

**Input Files** (Logstash):
- **Extension**: `.conf`
- **Encoding**: UTF-8 (FR-001)
- **Parsing**: Logstash DSL (Ruby-like syntax) via pyparsing

**Output Files** (Vector):
- **Extension**: `.toml`
- **Encoding**: UTF-8 (FR-006)
- **Format**: TOML with preserved comments for TODO markers (FR-009)
- **Validation**: Must pass `vector validate` (FR-015, SC-003)

**Naming Convention**:
- Input: `<name>.conf`
- Output: `<name>.toml` (same base name, different extension)
- Example: `pipeline.conf` → `pipeline.toml`

**Overwrite Behavior** (Edge Case):
- Default: Prompt user if `.toml` file exists
- With `--overwrite`: Silently overwrite existing files
- Dry run: Never writes files, only shows preview

---

## Requirements Mapping

| Functional Requirement | CLI Implementation |
|------------------------|-------------------|
| FR-001: Accept directory path | `DIRECTORY` argument |
| FR-007: Write to same directory | Default behavior (override with `-o`) |
| FR-008: Syntactically valid TOML | tomlkit generation + validation |
| FR-009: TODO markers for unsupported | Comments in generated TOML |
| FR-010: Migration report | Generated markdown report (--report) |
| FR-012: Multiple files | Iterates all `.conf` in directory |
| FR-013: Clear error messages | Structured stderr with file:line |
| FR-014: Dry-run mode | `--dry-run` flag |
| FR-015: Validate configs | `--validate` flag + validate command |

| Success Criteria | CLI Implementation |
|------------------|-------------------|
| SC-001: Under 2 minutes | Performance testing required |
| SC-003: 100% valid configs | Exit code 2 if validation fails |
| SC-004: Guidance for unsupported | Detailed manual migration in report |
| SC-005: Line numbers in report | All errors/unsupported include location |
| SC-007: 95% understandable reports | Plain language, examples in guidance |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LV_PY_LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) | `INFO` |
| `VECTOR_BIN` | Path to `vector` binary for validation | `vector` (from PATH) |

---

## Dependencies on External Tools

**Vector CLI** (optional, for validation):
- Required for: `--validate` flag, `lv-py validate` command
- Installation: https://vector.dev/docs/setup/installation/
- Version: 0.34.0+ recommended
- If not installed: `--no-validate` flag skips validation

**Note**: The migration tool itself does NOT require Vector to be installed for basic operation (parsing and generation). Vector is only needed for validation (FR-015).
