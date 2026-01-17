# Vector Migration Implementation Summary

## Scope

Migrate the Logstash pipeline that processes `ap_log` file inputs from `/app/log/web_*.log` into a Vector configuration that preserves multiline behavior, grok parsing, conditional logic, and Elasticsearch output formatting.

## Input and Multiline Handling

- File source tails `/app/log/web_*.log` with `read_from: end` and adds `system: "legendary"` plus `type: "ap_log"`.
- Multiline aggregation is configured to start on TRACE entries that match `before SysUuid::set()` and continues through subsequent lines until the next start pattern appears.

## Parsing and Field Extraction

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

- Elasticsearch sink points to `http://elasticsearch-fz1.engmon.svc.cluster.local:9200`.
- `logstash_format: true` with `logstash_date_format: "%Y.%m.%d"` and `bulk.index: "{{ POD_NAMESPACE }}"`.
- Buffering matches required flush interval and chunk size with retry forever behavior.

## Next Steps

- Validate grok patterns with real log samples.
- Run integration tests comparing Logstash and Vector outputs.
- Tune multiline timeout if events exceed the current window.
