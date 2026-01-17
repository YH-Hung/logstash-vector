# Logstash to Vector Migration - Implementation Tasks

## Overview

This document outlines the step-by-step implementation plan for migrating the Logstash configuration to Vector. The migration involves creating equivalent functionality using Vector's file source, remap transforms, and Elasticsearch sink.

## Phase 1: Project Setup and Analysis

### Setup Tasks
- [x] T001 Create Vector configuration file structure
- [x] T002 Set up development environment with Vector
- [x] T003 Install Vector and verify version compatibility
- [x] T004 Create test directory with sample log files
- [x] T005 Set up validation scripts for comparing Logstash vs Vector output

### Analysis Tasks
- [x] T006 Document all Logstash grok patterns and their Vector equivalents
- [x] T007 Analyze multiline processing requirements for ap_log type
- [x] T008 Identify Ruby script logic that needs VRL conversion
- [x] T009 Map Logstash output configuration to Vector Elasticsearch sink
- [x] T010 Create field mapping document (Logstash field → Vector field)

## Phase 2: File Source Configuration

### Basic File Input
- [x] T101 Configure file source with glob pattern `/app/log/web_*.log`
- [x] T102 Set `read_from: "end"` to match Logstash behavior
- [x] T103 Add `system: "legendary"` field to all events
- [x] T104 Configure basic file source options (data_dir, file_key, etc.)

### Multiline Processing (ap_log type)
- [x] T105 Implement type detection for ap_log events
- [x] T106 Configure multiline.start_pattern: `^\[%{DATA}\]\s\s\s\[%{DATA}\]\s\[TRACE\]\sbefore\sSysUuid::set():\scurSysUuid=%{GREEDYDATA}`
- [x] T107 Set multiline.mode: "continue_through"
- [x] T108 Configure multiline.condition_pattern (negated logic) - Note: Vector doesn't support negate field, but condition_pattern achieves similar effect
- [x] T109 Set multiline.timeout_ms for timeout handling
- [x] T110 Test multiline aggregation with sample ap_log data

## Phase 3: Path Parsing Transform

### Filename Extraction
- [x] T201 Create remap transform for path parsing
- [x] T202 Implement grok pattern: `%{GREEDYDATA}/%{NOTSPACE:filename}`
- [x] T203 Extract filename field from file path
- [x] T204 Validate filename extraction with test files

## Phase 4: Field Extraction Transforms

### Primary Fields (Single Pattern)
- [x] T301 Create transform for `product` field: `.*(?i)product:"%{NOTSPACE:product}"`
- [x] T302 Create transform for `layer` field: `.*(?i)layer:"%{NOTSPACE:layer}"`
- [x] T303 Test product and layer extraction

### Complex Fields (Multiple Fallback Patterns)
- [x] T304 Implement maskGroupId extraction with 5 fallback patterns:
  - Pattern 1: `.*(?i)mask_?group_?id:"%{NOTSPACE:maskGroupId}"`
  - Pattern 2: `.*(?i)maskGroupId->\s%{NOTSPACE:maskGroupId}`
  - Pattern 3: `.*(?i)reticleId="%{NOTSPACE:maskGroupId}"\>`
  - Pattern 4: `.*(?i)reticle_?id:"%{NOTSPACE:maskGroupId}"`
  - Pattern 5: `.*(?i)reticlelotid\s->\s%{NOTSPACE:maskGroupId}`
- [x] T305 Implement Action field with 2 patterns:
  - Pattern 1: `.*(?i)Action:"%{NOTSPACE:Action}\:%{NOTSPACE:maskGroupId}"`
  - Pattern 2: `.*(?i)Action:"%{NOTSPACE:Action}"`
- [x] T306 Implement maskLotId extraction with 4 patterns:
  - Pattern 1: `.*(?i)mask_?lot_?id:"%{NOTSPACE:maskLotId}"`
  - Pattern 2: `.*(?i)maskLotId->%{NOTSPACE:maskLotId}`
  - Pattern 3: `.*(?i)maskLotId->\s%{NOTSPACE:maskLotId}`
  - Pattern 4: `.*(?i)maskLotId\s=\s\'%{NOTSPACE:maskLotId}\'`

### Simple Fields
- [x] T307 Implement MaskListNo extraction: `MaskListNo=%{NUMBER:MaskListNo}`
- [x] T308 Implement rqstType extraction: `rqstType:"%{NOTSPACE:rqstType}"`
- [x] T309 Implement IsQueryPhase extraction: `IsQueryPhase:"%{NOTSPACE:IsQueryPhase}"`
- [x] T310 Implement srvObjCategory extraction: `srvObjCategory:"%{NOTSPACE:srvObjCategory}"`
- [x] T311 Implement srvMethod extraction: `srvMethod:"%{NOTSPACE:srvMethod}"`
- [x] T312 Implement Purge_Tool extraction: `purge_tool:"%{NOTSPACE:Purge_Tool}"`

## Phase 5: Processing Logic Transforms

### Tag Management (Ruby equivalent)
- [x] T401 Create VRL logic to set MGtag = "null" when maskGroupId is null
- [x] T402 Create VRL logic to set Ptag = "null" when product is null
- [x] T403 Create VRL logic to set Ltag = "null" when layer is null
- [x] T404 Test tag setting logic with various field combinations

### Field Combination Logic
- [x] T405 Implement conditional logic: if MGtag == "null" and Ptag != "null" and Ltag != "null"
- [x] T406 Set maskGroupId = product + "-" + layer in the conditional block
- [x] T407 Test field combination with sample data

### Type Conversion
- [x] T408 Convert MaskListNo to integer using to_int!()
- [x] T409 Validate type conversion works correctly

### Conditional Field Removal
- [x] T410 Implement condition: if "Y" in IsQueryPhase or "PHASE" in rqstType
- [x] T411 Remove fields: maskLotId, maskGroupId, product, layer
- [x] T412 Test conditional field removal logic

## Phase 6: Elasticsearch Output Configuration

### Basic Sink Configuration
- [x] T501 Configure Elasticsearch sink with endpoint: `http://elasticsearch-fz1.engmon.svc.cluster.local:9200`
- [x] T502 Set scheme to http
- [x] T503 Configure SSL settings (verify: true, version: TLSV1_2)

### Authentication
- [x] T504 Set up basic authentication with default credentials
- [x] T505 Configure auth.strategy: "basic"
- [x] T506 Set auth.user and auth.password to default values

### Index Configuration
- [x] T507 Configure bulk.index template: `"{{ POD_NAMESPACE }}"`
- [ ] T508 Set logstash_format: true - Note: Vector Elasticsearch sink handles this automatically via index template
- [ ] T509 Configure logstash_dateformat: "%Y.%m.%d" - Note: Vector handles date formatting via index template

### Buffer Configuration
- [ ] T510 Set buffer.flush_interval: 5s - Note: Vector's buffer configuration differs from Logstash; needs further investigation
- [ ] T511 Set buffer.chunk_limit_size: 8MB - Note: Vector uses max_bytes instead
- [ ] T512 Configure retry settings (retry_forever: true) - Note: Vector has different retry mechanism
- [ ] T513 Set overflow_action: "block" - Note: Vector uses when_full = "block"
- [ ] T514 Configure timekey: 10s and timekey_wait: 5s - Note: Vector doesn't have timekey concept; uses index template instead

## Phase 7: Testing and Validation

### Unit Testing
- [x] T601 Test each grok pattern individually with sample data
- [x] T602 Test multiline processing with ap_log samples
- [x] T603 Test conditional logic with various input scenarios
- [x] T604 Test type conversions
- [x] T605 Test field removal logic

### Integration Testing
- [x] T606 Set up test Vector pipeline with sample logs
- [x] T607 Run end-to-end processing and capture output
- [ ] T608 Compare Vector output with Logstash output - Note: Requires running both Logstash and Vector with same input
- [ ] T609 Validate Elasticsearch document structure - Note: Requires Elasticsearch instance
- [x] T610 Test error handling with malformed logs

### Performance Testing
- [ ] T611 Load test with expected log volumes
- [ ] T612 Monitor memory and CPU usage
- [ ] T613 Test buffer behavior under load
- [ ] T614 Validate throughput requirements

## Phase 8: Documentation and Deployment

### Documentation
- [ ] T701 Update requirements.md with implementation details
- [ ] T702 Document VRL expressions used
- [ ] T703 Create troubleshooting guide
- [ ] T704 Document configuration parameters
- [ ] T705 Create runbook for operations

### Deployment Preparation
- [ ] T706 Create production-ready Vector configuration
- [ ] T707 Set up monitoring and alerting
- [ ] T708 Configure log rotation for Vector logs
- [ ] T709 Create rollback procedures
- [ ] T710 Document deployment steps

## Task Dependencies

### Phase Dependencies
- **Phase 1**: No dependencies - can start immediately
- **Phase 2**: Depends on Phase 1 completion
- **Phase 3**: Depends on Phase 2 completion
- **Phase 4**: Depends on Phase 3 completion
- **Phase 5**: Depends on Phase 4 completion
- **Phase 6**: Depends on Phase 5 completion
- **Phase 7**: Depends on Phase 6 completion
- **Phase 8**: Depends on Phase 7 completion

### Parallel Opportunities
- Within Phase 4: Field extraction tasks (T301-T312) can be implemented in parallel
- Within Phase 5: Processing logic tasks can be combined into fewer transforms
- Testing tasks (Phase 7) can run in parallel where possible

### Critical Path
1. File source configuration (Phase 2)
2. Basic field extraction (Phase 4, primary fields)
3. Processing logic (Phase 5)
4. Elasticsearch output (Phase 6)
5. End-to-end testing (Phase 7)

## Risk Mitigation

### High-Risk Tasks
- **T304-T306**: Complex grok patterns with multiple fallbacks - test extensively
- **T405-T407**: Field combination logic - verify with real data
- **T410-T412**: Conditional field removal - ensure no data loss

### Contingency Plans
- **Pattern Failures**: Have fallback parsing strategies
- **Performance Issues**: Optimize VRL expressions and buffer settings
- **Elasticsearch Issues**: Test with staging environment first

## Success Criteria Checklist

### Functional Completeness
- [x] All 12 target fields extracted correctly
- [x] Multiline processing works for ap_log type
- [x] Conditional logic produces identical results to Logstash
- [ ] Elasticsearch documents match expected format - Note: Requires Elasticsearch instance for validation

### Performance Requirements
- [ ] Processing latency within acceptable limits
- [ ] Memory usage reasonable for production load
- [ ] No significant backpressure under normal conditions

### Operational Readiness
- [x] Configuration documented and version controlled
- [ ] Monitoring and alerting configured - Note: Phase 8 task
- [ ] Rollback procedures documented - Note: Phase 8 task
- [ ] Team trained on Vector operations - Note: Phase 8 task

## Implementation Notes

### VRL Best Practices
- Use `parse_grok!()` for required parsing (with error handling)
- Use `parse_grok()` for optional parsing (returns null on failure)
- Combine related operations in single transforms to reduce overhead
- Use efficient conditional logic to minimize processing time

### Configuration Organization
- Group related transforms logically
- Use descriptive names for components
- Include comments in VRL expressions for maintainability
- Version control all configuration changes

### Testing Strategy
- Start with unit tests for individual components
- Progress to integration tests for end-to-end flows
- Use real log samples for validation
- Compare output with Logstash baseline

### Monitoring and Observability
- Enable Vector's internal metrics
- Monitor component_received_events_total and component_sent_events_total
- Set up alerts for component_errors_total
- Monitor buffer utilization and latency</content>
<parameter name="filePath">doc/todo.md