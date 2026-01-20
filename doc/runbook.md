# Vector Operations Runbook

This runbook provides operational procedures for managing the Vector log processing pipeline that replaces Logstash.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Startup Procedures](#startup-procedures)
3. [Shutdown Procedures](#shutdown-procedures)
4. [Health Checks](#health-checks)
5. [Log Management](#log-management)
6. [Common Issues & Solutions](#common-issues--solutions)
7. [Maintenance Tasks](#maintenance-tasks)
8. [Escalation Procedures](#escalation-procedures)

---

## Quick Reference

### Essential Commands

| Action | Command |
|--------|---------|
| Start Vector | `vector --config /path/to/vector.yaml` |
| Validate config | `vector validate /path/to/vector.yaml` |
| Run unit tests | `vector test /path/to/vector.yaml` |
| Check health | `curl http://localhost:8686/health` |
| View metrics | `vector top` |
| Reload config | `kill -SIGHUP <pid>` |
| Graceful stop | `kill -SIGTERM <pid>` |

### Key File Locations

| File | Location |
|------|----------|
| Configuration | `/path/to/impl/vector.yaml` |
| Data directory | `tmp/vector/` (configurable) |
| Checkpoint files | `tmp/vector/*.json` |
| Logs | stdout/stderr (container) or systemd journal |

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `POD_NAMESPACE` | Elasticsearch index prefix | Required |
| `ES_USER` | Elasticsearch username | elastic |
| `ES_PASSWORD` | Elasticsearch password | changeme |
| `VECTOR_LOG` | Log level | info |

---

## Startup Procedures

### Pre-flight Checks

1. **Verify configuration syntax:**
   ```bash
   vector validate /path/to/vector.yaml
   ```

2. **Run unit tests:**
   ```bash
   vector test /path/to/vector.yaml
   ```
   Expected: All 35 tests should pass.

3. **Verify environment variables:**
   ```bash
   echo "POD_NAMESPACE: $POD_NAMESPACE"
   echo "ES_USER: $ES_USER"
   # Don't echo password
   ```

4. **Check Elasticsearch connectivity:**
   ```bash
   curl -u "$ES_USER:$ES_PASSWORD" \
     "http://elasticsearch-fz1.engmon.svc.cluster.local:9200/_cluster/health"
   ```

### Starting Vector

**Standard start:**
```bash
vector --config /path/to/vector.yaml
```

**With verbose logging:**
```bash
VECTOR_LOG=debug vector --config /path/to/vector.yaml
```

**As systemd service:**
```bash
sudo systemctl start vector
sudo systemctl status vector
```

**In Kubernetes:**
```bash
kubectl rollout restart deployment/vector -n <namespace>
kubectl get pods -n <namespace> -l app=vector
```

### Post-start Verification

1. **Check process is running:**
   ```bash
   pgrep -f "vector --config"
   ```

2. **Verify health endpoint:**
   ```bash
   curl http://localhost:8686/health
   ```
   Expected response: `{"ok":true}`

3. **Check logs for errors:**
   ```bash
   # Systemd
   journalctl -u vector -f

   # Kubernetes
   kubectl logs -f deployment/vector -n <namespace>
   ```

4. **Verify events flowing:**
   ```bash
   vector top
   ```
   Look for non-zero `events_in` and `events_out` rates.

---

## Shutdown Procedures

### Graceful Shutdown

**Preferred method (SIGTERM):**
```bash
kill -SIGTERM $(pgrep -f "vector --config")
```

Vector will:
1. Stop accepting new events
2. Finish processing in-flight events
3. Flush buffers to Elasticsearch
4. Exit cleanly

**Systemd:**
```bash
sudo systemctl stop vector
```

**Kubernetes:**
```bash
kubectl scale deployment/vector --replicas=0 -n <namespace>
```

### Emergency Shutdown

**Immediate stop (SIGKILL):**
```bash
kill -SIGKILL $(pgrep -f "vector --config")
```

**Warning:** This may result in:
- Unflushed buffer data loss
- Checkpoint inconsistency
- Requires checkpoint recovery on restart

### Shutdown Verification

1. **Confirm process stopped:**
   ```bash
   pgrep -f "vector --config" || echo "Vector stopped"
   ```

2. **Check for orphan processes:**
   ```bash
   ps aux | grep vector
   ```

---

## Health Checks

### Health Endpoint

**Check health:**
```bash
curl -s http://localhost:8686/health | jq .
```

**Expected healthy response:**
```json
{"ok": true}
```

### Metrics Endpoint

**Get all metrics:**
```bash
curl -s http://localhost:8686/metrics | head -50
```

**Key metrics to monitor:**

| Metric | Description | Healthy Value |
|--------|-------------|---------------|
| `component_received_events_total` | Events received | Increasing |
| `component_sent_events_total` | Events sent | ≈ received |
| `component_errors_total` | Error count | 0 or stable |
| `buffer_byte_size` | Buffer usage | < max_bytes |

### Using vector top

**Interactive monitoring:**
```bash
vector top
```

This shows real-time:
- Events in/out per component
- Error rates
- Throughput (events/sec)

### Kubernetes Probes

**Liveness probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8686
  initialDelaySeconds: 10
  periodSeconds: 10
```

**Readiness probe:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8686
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Log Management

### Vector Log Configuration

**Set log level via environment:**
```bash
export VECTOR_LOG=info  # Options: trace, debug, info, warn, error
```

**Log format:**
- Default: JSON format to stdout
- Fields: timestamp, level, message, component

### Log Rotation

Vector logs to stdout/stderr by design. Log rotation depends on the deployment environment:

**Systemd:**
```ini
# /etc/systemd/system/vector.service.d/override.conf
[Service]
StandardOutput=journal
StandardError=journal
```

Journal rotation is handled by systemd.

**Kubernetes:**
Container runtime handles log rotation. Configure via:
```yaml
# Typical container runtime config
containers:
- name: vector
  # Logs go to /var/log/containers/
```

**Standalone with logrotate:**
```bash
# /etc/logrotate.d/vector
/var/log/vector/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 vector vector
}
```

### Data Directory Cleanup

**Checkpoint files:**
```bash
# Location
ls -la tmp/vector/

# Safe to delete when Vector is stopped (will rescan files)
rm -rf tmp/vector/*.json
```

**When to clean checkpoints:**
- After significant configuration changes
- When file positions are incorrect
- During troubleshooting

---

## Common Issues & Solutions

### Issue: Events Not Flowing

**Symptoms:**
- `component_received_events_total` = 0
- No output in Elasticsearch

**Diagnosis:**
1. Check source files exist:
   ```bash
   ls -la /app/log/web_*.log
   ```

2. Verify file permissions:
   ```bash
   stat /app/log/web_*.log
   ```

3. Check checkpoint position:
   ```bash
   cat tmp/vector/*.json
   ```

**Solutions:**
- Ensure files match glob pattern `/app/log/web_*.log`
- Reset checkpoints if file was truncated/rotated
- Verify Vector user has read access

### Issue: Elasticsearch Connection Failures

**Symptoms:**
- `component_errors_total` increasing
- Logs show connection errors

**Diagnosis:**
1. Test connectivity:
   ```bash
   curl -v http://elasticsearch-fz1.engmon.svc.cluster.local:9200
   ```

2. Verify credentials:
   ```bash
   curl -u "$ES_USER:$ES_PASSWORD" \
     http://elasticsearch-fz1.engmon.svc.cluster.local:9200/_cluster/health
   ```

**Solutions:**
- Check network connectivity
- Verify ES cluster health
- Confirm credentials are correct
- Check ES disk space (watermark issues)

### Issue: High Memory Usage

**Symptoms:**
- Memory > 500MB
- OOM kills

**Diagnosis:**
1. Check buffer size:
   ```bash
   curl -s http://localhost:8686/metrics | grep buffer
   ```

2. Review batch settings in config

**Solutions:**
- Reduce `batch.max_bytes` (default: 8MB)
- Check for large/malformed events
- Increase container memory limits

### Issue: Grok Parse Failures

**Symptoms:**
- Fields missing in output
- Unexpected null values

**Diagnosis:**
1. Check sample event:
   ```bash
   vector tap derive_and_cleanup --limit 1
   ```

2. Test pattern manually:
   ```bash
   vector vrl --input '{"message": "..."}' --program 'parse_grok(.message, "pattern")'
   ```

**Solutions:**
- Verify log format hasn't changed
- Add additional fallback patterns
- Check for encoding issues

### Issue: Multiline Events Split

**Symptoms:**
- Stack traces appear as separate events
- Incomplete log entries

**Diagnosis:**
1. Check multiline config in source
2. Verify start pattern matches

**Solutions:**
- Adjust `multiline.start_pattern`
- Increase `multiline.timeout_ms`
- Review `multiline.mode` setting

---

## Maintenance Tasks

### Configuration Updates

**Hot reload (if supported):**
```bash
kill -SIGHUP $(pgrep -f "vector --config")
```

**Full restart:**
```bash
# Validate first
vector validate /path/to/vector.yaml
vector test /path/to/vector.yaml

# Restart
sudo systemctl restart vector
```

### Checkpoint Management

**View checkpoint status:**
```bash
cat tmp/vector/*.json | jq .
```

**Reset checkpoints (read from end):**
```bash
# Stop Vector first
sudo systemctl stop vector
rm -rf tmp/vector/*.json
sudo systemctl start vector
```

### Performance Tuning

**Monitor throughput:**
```bash
vector top
```

**Adjust batch settings:**
```yaml
batch:
  max_bytes: 8388608    # Increase for higher throughput
  timeout_secs: 5       # Decrease for lower latency
```

### Capacity Planning

Monitor these metrics for capacity planning:
- `component_received_events_total` rate
- `buffer_byte_size` vs configured max
- CPU and memory utilization

---

## Escalation Procedures

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Complete outage, no logs flowing | Immediate |
| P2 | Partial outage or severe degradation | 30 minutes |
| P3 | Minor issues, workaround available | 4 hours |
| P4 | Cosmetic or low-impact issues | Next business day |

### Escalation Path

1. **First Response (On-call)**
   - Verify issue using health checks
   - Attempt restart if appropriate
   - Collect diagnostic information

2. **Engineering Escalation**
   - If restart doesn't resolve
   - For configuration issues
   - For pattern matching problems

3. **Infrastructure Team**
   - Elasticsearch issues
   - Network connectivity
   - Resource constraints

### Diagnostic Collection

**Before escalating, collect:**

1. Vector logs (last 1000 lines):
   ```bash
   journalctl -u vector -n 1000 > vector_logs.txt
   ```

2. Configuration (redact secrets):
   ```bash
   cat /path/to/vector.yaml | grep -v password > vector_config.txt
   ```

3. Metrics snapshot:
   ```bash
   curl -s http://localhost:8686/metrics > vector_metrics.txt
   ```

4. System status:
   ```bash
   free -h
   df -h
   ps aux | grep vector
   ```

### Contact Information

| Role | Contact | Notes |
|------|---------|-------|
| On-call | PagerDuty | Primary responder |
| Platform Team | Slack #platform | Configuration help |
| Observability Team | Slack #observability | Monitoring/alerting |

---

## Appendix: Configuration Reference

### Current Production Settings

```yaml
# Elasticsearch output
endpoint: http://elasticsearch-fz1.engmon.svc.cluster.local:9200
index: "{{ POD_NAMESPACE }}-%Y.%m.%d"

# Buffer settings
batch:
  max_bytes: 8388608  # 8MB
  timeout_secs: 5
buffer:
  when_full: block

# Retry settings
retry_max_duration_secs: 3600  # 1 hour
```

### Useful Vector Commands

```bash
# Validate configuration
vector validate config.yaml

# Run unit tests
vector test config.yaml

# Interactive VRL REPL
vector vrl

# Tap into pipeline (debug)
vector tap <component_name>

# Generate config graph
vector graph config.yaml
```
