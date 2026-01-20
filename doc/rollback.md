# Vector Rollback Procedures

This document provides procedures for rolling back from Vector to Logstash in case of issues.

## Table of Contents

1. [Pre-rollback Checklist](#pre-rollback-checklist)
2. [Rollback Steps](#rollback-steps)
3. [Re-enable Logstash](#re-enable-logstash)
4. [Data Verification](#data-verification)
5. [Post-rollback Validation](#post-rollback-validation)
6. [Root Cause Analysis](#root-cause-analysis)

---

## Pre-rollback Checklist

Before initiating a rollback, verify:

### Decision Criteria

- [ ] Issue confirmed (not a false alarm)
- [ ] Issue impacts production data flow
- [ ] Immediate fix not possible
- [ ] Rollback approved by tech lead/on-call manager

### Readiness Checks

- [ ] Logstash configuration still available
- [ ] Logstash binary/package still installed
- [ ] Elasticsearch credentials unchanged
- [ ] Source log files still at expected paths

### Documentation

- [ ] Current time noted
- [ ] Issue description documented
- [ ] Vector logs saved for analysis

### Communication

- [ ] Team notified of rollback
- [ ] Stakeholders informed of potential data gap

---

## Rollback Steps

### Step 1: Stop Vector

**Systemd:**
```bash
sudo systemctl stop vector
sudo systemctl disable vector
```

**Kubernetes:**
```bash
kubectl scale deployment/vector --replicas=0 -n <namespace>
```

**Verify stopped:**
```bash
pgrep -f "vector --config" && echo "Still running!" || echo "Stopped"
```

### Step 2: Preserve Vector State (for debugging)

```bash
# Create backup directory
BACKUP_DIR="/tmp/vector-rollback-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Save configuration
cp /etc/vector/vector.yaml "$BACKUP_DIR/"

# Save checkpoint files
cp -r tmp/vector/* "$BACKUP_DIR/" 2>/dev/null || true

# Save recent logs
journalctl -u vector --since "1 hour ago" > "$BACKUP_DIR/vector-logs.txt"

echo "Backup saved to: $BACKUP_DIR"
```

### Step 3: Clear Vector Checkpoints (optional)

If Vector will be restarted later and you want to avoid reprocessing:

```bash
# Keep checkpoints
echo "Preserving checkpoints for potential retry"

# Or clear them to force fresh start
# rm -rf tmp/vector/*.json
```

---

## Re-enable Logstash

### Step 1: Verify Logstash Configuration

```bash
# Check configuration exists
ls -la /etc/logstash/conf.d/

# Validate configuration
/usr/share/logstash/bin/logstash --config.test_and_exit -f /etc/logstash/conf.d/
```

### Step 2: Start Logstash

**Systemd:**
```bash
sudo systemctl enable logstash
sudo systemctl start logstash
```

**Docker:**
```bash
docker-compose up -d logstash
```

**Verify running:**
```bash
sudo systemctl status logstash

# Check logs
tail -f /var/log/logstash/logstash-plain.log
```

### Step 3: Verify Event Flow

```bash
# Check Logstash is processing
curl -s http://localhost:9600/_node/stats/events | jq '.events'

# Verify events in ES
curl -s -u "$ES_USER:$ES_PASSWORD" \
  "http://elasticsearch:9200/${POD_NAMESPACE}-$(date +%Y.%m.%d)/_count"
```

---

## Data Verification

### Check for Data Gaps

1. **Identify gap window:**
   ```bash
   # Time Vector stopped
   VECTOR_STOP=$(date -Iseconds)

   # Time Logstash started
   LOGSTASH_START=$(date -Iseconds)

   echo "Potential gap: $VECTOR_STOP to $LOGSTASH_START"
   ```

2. **Query ES for gap:**
   ```bash
   curl -s -u "$ES_USER:$ES_PASSWORD" \
     "http://elasticsearch:9200/${POD_NAMESPACE}-*/_search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": {
         "range": {
           "@timestamp": {
             "gte": "'"$VECTOR_STOP"'",
             "lte": "'"$LOGSTASH_START"'"
           }
         }
       },
       "size": 0
     }' | jq '.hits.total'
   ```

### Verify Data Consistency

```bash
# Count recent documents
curl -s -u "$ES_USER:$ES_PASSWORD" \
  "http://elasticsearch:9200/${POD_NAMESPACE}-*/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "gte": "now-1h"
        }
      }
    },
    "size": 0
  }' | jq '.hits.total.value'
```

### Reprocess Missing Data (if needed)

If there's a gap and log files still contain the data:

**Option 1: Temporary Vector run**
```bash
# Create config to read from specific position
cat > /tmp/vector-catchup.yaml << EOF
data_dir: /tmp/vector-catchup-data

sources:
  catchup:
    type: file
    include:
      - /app/log/web_*.log
    read_from: beginning
    # Will read all data in files

sinks:
  elasticsearch_catchup:
    # Same as production config
    ...
EOF

# Run until caught up, then stop manually
vector --config /tmp/vector-catchup.yaml
```

**Option 2: Let Logstash catch up**
- Logstash will process from its last checkpoint
- May result in some duplicate events (ES can dedupe by _id)

---

## Post-rollback Validation

### Immediate Checks (within 5 minutes)

- [ ] Logstash process running
- [ ] Events flowing to ES
- [ ] No errors in Logstash logs
- [ ] Monitoring alerts cleared

### Short-term Checks (within 1 hour)

- [ ] Event rate back to normal
- [ ] All expected fields present in documents
- [ ] No data quality issues
- [ ] Dashboards showing data

### Documentation

- [ ] Rollback time recorded
- [ ] Duration of outage documented
- [ ] Data gap (if any) documented
- [ ] Incident ticket created

---

## Root Cause Analysis

### Collect Evidence

1. **Vector logs:**
   ```bash
   # From backup
   cat "$BACKUP_DIR/vector-logs.txt"

   # Or from journal
   journalctl -u vector --since "2 hours ago"
   ```

2. **Configuration at time of failure:**
   ```bash
   cat "$BACKUP_DIR/vector.yaml"
   ```

3. **Metrics at time of failure:**
   ```bash
   # If Prometheus data available
   # Query for Vector metrics around failure time
   ```

4. **ES cluster status:**
   ```bash
   curl -s -u "$ES_USER:$ES_PASSWORD" \
     "http://elasticsearch:9200/_cluster/health?pretty"
   ```

### Common Failure Modes

| Symptom | Likely Cause | Investigation |
|---------|--------------|---------------|
| No events flowing | Source file issues | Check file paths, permissions |
| ES connection errors | Network/auth issues | Test connectivity, credentials |
| High error rate | Parsing failures | Check log format changes |
| Memory exhaustion | Buffer overflow | Review batch/buffer settings |
| Slow processing | ES backpressure | Check ES cluster health |

### Post-mortem Template

```markdown
## Incident Summary
- **Date:** YYYY-MM-DD
- **Duration:** X hours
- **Impact:** Description of impact

## Timeline
- HH:MM - First alert triggered
- HH:MM - Investigation started
- HH:MM - Rollback initiated
- HH:MM - Logstash restored
- HH:MM - Normal operations confirmed

## Root Cause
Detailed description of what went wrong.

## Data Impact
- Events during gap: X
- Reprocessed: Y
- Lost: Z

## Action Items
1. [ ] Fix: Description
2. [ ] Improvement: Description
3. [ ] Documentation: Update X

## Lessons Learned
- What worked well
- What could be improved
```

---

## Recovery Path

After rollback is stable, plan the path back to Vector:

### Short-term (1-7 days)

1. Analyze root cause
2. Fix identified issues
3. Test fix in development environment
4. Update unit tests if needed

### Medium-term (1-2 weeks)

1. Deploy fixed Vector to staging
2. Run parallel with Logstash
3. Validate output matches
4. Run load tests

### Long-term (2-4 weeks)

1. Plan re-cutover with larger safety margin
2. Implement additional monitoring
3. Update runbooks based on lessons learned
4. Schedule cutover with team awareness

---

## Emergency Contacts

| Role | Contact | When to Contact |
|------|---------|-----------------|
| On-call engineer | PagerDuty | First response |
| Platform lead | Slack/Phone | Escalation |
| Elasticsearch admin | Slack | ES issues |

---

## Appendix: Quick Rollback Commands

```bash
# One-liner rollback (use with caution)
sudo systemctl stop vector && sudo systemctl disable vector && \
sudo systemctl enable logstash && sudo systemctl start logstash && \
sudo systemctl status logstash
```

```bash
# Kubernetes rollback
kubectl scale deployment/vector --replicas=0 && \
kubectl scale deployment/logstash --replicas=1
```
