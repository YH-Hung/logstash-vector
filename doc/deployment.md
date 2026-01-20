# Vector Deployment Guide

This document provides step-by-step procedures for deploying the Vector log processing pipeline.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-deployment Checklist](#pre-deployment-checklist)
3. [Configuration](#configuration)
4. [Deployment Steps](#deployment-steps)
5. [Validation Checklist](#validation-checklist)
6. [Smoke Tests](#smoke-tests)
7. [Production Cutover](#production-cutover)

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2 cores |
| Memory | 256 MB | 512 MB |
| Disk | 1 GB | 5 GB |
| Vector Version | 0.52.0+ | Latest stable |

### Dependencies

1. **Vector binary** - Install from [vector.dev](https://vector.dev/docs/setup/installation/)

   ```bash
   # macOS
   brew install vector

   # Linux (apt)
   curl -1sLf 'https://repositories.timber.io/public/vector/cfg/setup/bash.deb.sh' | sudo -E bash
   sudo apt install vector

   # Linux (yum)
   curl -1sLf 'https://repositories.timber.io/public/vector/cfg/setup/bash.rpm.sh' | sudo -E bash
   sudo yum install vector
   ```

2. **Elasticsearch cluster** - Version 7.x or 8.x
   - Endpoint: `http://elasticsearch-fz1.engmon.svc.cluster.local:9200`
   - Authentication credentials

3. **Network connectivity**
   - Access to log source files
   - Outbound to Elasticsearch endpoint
   - Port 8686 for health checks (optional)
   - Port 9598 for Prometheus metrics (optional)

### Required Permissions

- Read access to `/app/log/web_*.log`
- Write access to data directory (`tmp/vector/`)
- Network access to Elasticsearch

---

## Pre-deployment Checklist

### Configuration Validation

- [ ] Vector configuration file exists
- [ ] Configuration validates successfully:
  ```bash
  vector validate impl/vector.yaml
  ```
- [ ] All 35 unit tests pass:
  ```bash
  vector test impl/vector.yaml
  ```

### Environment Verification

- [ ] Source log files exist at expected path:
  ```bash
  ls -la /app/log/web_*.log
  ```
- [ ] Elasticsearch is reachable:
  ```bash
  curl -s http://elasticsearch-fz1.engmon.svc.cluster.local:9200/_cluster/health
  ```
- [ ] Credentials are valid:
  ```bash
  curl -u "$ES_USER:$ES_PASSWORD" \
    http://elasticsearch-fz1.engmon.svc.cluster.local:9200/_cluster/health
  ```

### Resource Verification

- [ ] Sufficient disk space:
  ```bash
  df -h /
  ```
- [ ] Sufficient memory:
  ```bash
  free -h
  ```
- [ ] Data directory is writable:
  ```bash
  mkdir -p tmp/vector && touch tmp/vector/test && rm tmp/vector/test
  ```

### Documentation

- [ ] Runbook available to operations team
- [ ] Monitoring alerts configured
- [ ] Rollback procedure documented

---

## Configuration

### Environment Variables

Set the following environment variables before deployment:

```bash
# Required
export POD_NAMESPACE="your-namespace"  # Used for ES index prefix
export ES_USER="elastic"               # Elasticsearch username
export ES_PASSWORD="your-password"     # Elasticsearch password

# Optional
export VECTOR_LOG="info"               # Log level (trace, debug, info, warn, error)
```

### Kubernetes Secret (if applicable)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: vector-secrets
type: Opaque
stringData:
  ES_USER: elastic
  ES_PASSWORD: your-password
```

### ConfigMap for Vector Config

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vector-config
data:
  vector.yaml: |
    # Contents of impl/vector.yaml
    ...
```

### Configuration Parameters

Key settings to review:

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `data_dir` | Root | `tmp/vector` | Checkpoint storage |
| `include` | Source | `/app/log/web_*.log` | File glob pattern |
| `read_from` | Source | `end` | Start position |
| `endpoint` | Sink | ES URL | Elasticsearch endpoint |
| `batch.max_bytes` | Sink | `8388608` | Max batch size |
| `batch.timeout_secs` | Sink | `5` | Batch timeout |

---

## Deployment Steps

### Step 1: Prepare Configuration

1. Copy configuration to target location:
   ```bash
   sudo mkdir -p /etc/vector
   sudo cp impl/vector.yaml /etc/vector/vector.yaml
   ```

2. Set ownership:
   ```bash
   sudo chown -R vector:vector /etc/vector
   ```

3. Create data directory:
   ```bash
   sudo mkdir -p /var/lib/vector
   sudo chown vector:vector /var/lib/vector
   ```

### Step 2: Configure Environment

**For systemd:**
```bash
# Create environment file
sudo tee /etc/vector/vector.env << EOF
POD_NAMESPACE=production
ES_USER=elastic
ES_PASSWORD=your-password
VECTOR_LOG=info
EOF

sudo chmod 600 /etc/vector/vector.env
```

**For Kubernetes:**
```bash
kubectl create secret generic vector-secrets \
  --from-literal=ES_USER=elastic \
  --from-literal=ES_PASSWORD=your-password

kubectl create configmap vector-config \
  --from-file=vector.yaml=impl/vector.yaml
```

### Step 3: Install Service

**Systemd service file:**
```ini
# /etc/systemd/system/vector.service
[Unit]
Description=Vector Log Processor
After=network.target
Documentation=https://vector.dev

[Service]
Type=simple
User=vector
Group=vector
EnvironmentFile=/etc/vector/vector.env
ExecStart=/usr/bin/vector --config /etc/vector/vector.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable vector
sudo systemctl start vector
```

**Kubernetes Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vector
  template:
    metadata:
      labels:
        app: vector
    spec:
      containers:
        - name: vector
          image: timberio/vector:0.52.0-debian
          args:
            - --config
            - /etc/vector/vector.yaml
          env:
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: ES_USER
              valueFrom:
                secretKeyRef:
                  name: vector-secrets
                  key: ES_USER
            - name: ES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: vector-secrets
                  key: ES_PASSWORD
          volumeMounts:
            - name: config
              mountPath: /etc/vector
            - name: logs
              mountPath: /app/log
              readOnly: true
            - name: data
              mountPath: /var/lib/vector
          ports:
            - containerPort: 8686
              name: api
            - containerPort: 9598
              name: metrics
          livenessProbe:
            httpGet:
              path: /health
              port: 8686
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8686
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi
      volumes:
        - name: config
          configMap:
            name: vector-config
        - name: logs
          hostPath:
            path: /app/log
        - name: data
          emptyDir: {}
```

### Step 4: Verify Deployment

```bash
# Check service status
sudo systemctl status vector

# Or for Kubernetes
kubectl get pods -l app=vector
kubectl logs -f deployment/vector
```

---

## Validation Checklist

### Immediate Checks (within 1 minute)

- [ ] Process is running:
  ```bash
  pgrep -f "vector --config" || kubectl get pods -l app=vector
  ```

- [ ] Health endpoint responds:
  ```bash
  curl -s http://localhost:8686/health
  # Expected: {"ok":true}
  ```

- [ ] No errors in logs:
  ```bash
  journalctl -u vector --no-pager -n 50 | grep -i error
  # Or: kubectl logs deployment/vector | grep -i error
  ```

### Short-term Checks (within 5 minutes)

- [ ] Events are being received:
  ```bash
  curl -s http://localhost:8686/metrics | grep component_received_events_total
  ```

- [ ] Events are being sent to ES:
  ```bash
  curl -s http://localhost:8686/metrics | grep component_sent_events_total
  ```

- [ ] No sustained errors:
  ```bash
  curl -s http://localhost:8686/metrics | grep component_errors_total
  ```

### Data Validation (within 15 minutes)

- [ ] Documents appear in Elasticsearch:
  ```bash
  curl -u "$ES_USER:$ES_PASSWORD" \
    "http://elasticsearch:9200/${POD_NAMESPACE}-*/_count"
  ```

- [ ] Document structure is correct:
  ```bash
  curl -u "$ES_USER:$ES_PASSWORD" \
    "http://elasticsearch:9200/${POD_NAMESPACE}-*/_search?size=1" | jq .
  ```

- [ ] Required fields present:
  - `system` = "legendary"
  - `type` = "ap_log"
  - `filename`
  - Business fields (product, layer, maskGroupId, etc.)

---

## Smoke Tests

### Test 1: Basic Health Check

```bash
#!/bin/bash
# smoke_test_health.sh

HEALTH=$(curl -s http://localhost:8686/health)
if [[ "$HEALTH" == '{"ok":true}' ]]; then
    echo "PASS: Health check"
else
    echo "FAIL: Health check - got $HEALTH"
    exit 1
fi
```

### Test 2: Event Flow

```bash
#!/bin/bash
# smoke_test_events.sh

# Get initial count
INITIAL=$(curl -s http://localhost:8686/metrics | \
  grep 'component_sent_events_total{component_name="elasticsearch_output"}' | \
  awk '{print $2}')

# Wait
sleep 30

# Get new count
FINAL=$(curl -s http://localhost:8686/metrics | \
  grep 'component_sent_events_total{component_name="elasticsearch_output"}' | \
  awk '{print $2}')

if [[ "$FINAL" -gt "$INITIAL" ]]; then
    echo "PASS: Events flowing ($INITIAL -> $FINAL)"
else
    echo "FAIL: No events flowing"
    exit 1
fi
```

### Test 3: Elasticsearch Data

```bash
#!/bin/bash
# smoke_test_es.sh

COUNT=$(curl -s -u "$ES_USER:$ES_PASSWORD" \
  "http://elasticsearch:9200/${POD_NAMESPACE}-*/_count" | \
  jq -r '.count')

if [[ "$COUNT" -gt "0" ]]; then
    echo "PASS: Documents in ES ($COUNT)"
else
    echo "FAIL: No documents in ES"
    exit 1
fi
```

### Run All Smoke Tests

```bash
#!/bin/bash
# run_smoke_tests.sh

echo "Running smoke tests..."

./smoke_test_health.sh || exit 1
./smoke_test_events.sh || exit 1
./smoke_test_es.sh || exit 1

echo "All smoke tests passed!"
```

---

## Production Cutover

### Cutover Strategy

**Recommended: Parallel Run**

1. Run Vector alongside Logstash for 24-48 hours
2. Compare outputs (use integration test framework)
3. Verify data consistency in Elasticsearch
4. Switch over when confident

### Cutover Steps

#### Phase 1: Parallel Operation

1. **Deploy Vector** (not yet processing production logs)
   ```bash
   # Use test log path initially
   # include: /app/log/test_*.log
   ```

2. **Generate test data**
   ```bash
   cp /app/log/web_sample.log /app/log/test_sample.log
   ```

3. **Verify Vector output**
   - Check ES index for test data
   - Compare with Logstash output

#### Phase 2: Shadow Mode

1. **Configure Vector to read production logs**
   ```yaml
   include:
     - /app/log/web_*.log
   ```

2. **Use separate ES index** (temporarily)
   ```yaml
   bulk:
     index: "{{ POD_NAMESPACE }}-vector-%Y.%m.%d"
   ```

3. **Run for 24 hours**
   - Monitor for errors
   - Compare event counts
   - Validate data quality

#### Phase 3: Switch Over

1. **Stop Logstash**
   ```bash
   sudo systemctl stop logstash
   ```

2. **Update Vector to use production index**
   ```yaml
   bulk:
     index: "{{ POD_NAMESPACE }}-%Y.%m.%d"
   ```

3. **Restart Vector**
   ```bash
   sudo systemctl restart vector
   ```

4. **Verify**
   - Run all smoke tests
   - Monitor dashboards
   - Check alert status

#### Phase 4: Cleanup

1. **Remove Logstash**
   ```bash
   sudo systemctl disable logstash
   ```

2. **Clean up test indices** (if any)
   ```bash
   curl -X DELETE "http://elasticsearch:9200/${POD_NAMESPACE}-vector-*"
   ```

3. **Update documentation**
   - Mark migration complete
   - Archive Logstash configs

### Rollback During Cutover

If issues arise during cutover:

1. **Stop Vector**
   ```bash
   sudo systemctl stop vector
   ```

2. **Start Logstash**
   ```bash
   sudo systemctl start logstash
   ```

3. **Verify Logstash is processing**
   ```bash
   tail -f /var/log/logstash/logstash-plain.log
   ```

4. **Investigate Vector issues**
   - Review logs
   - Check configuration
   - Contact support if needed

---

## Post-Deployment Tasks

- [ ] Document final configuration
- [ ] Update monitoring dashboards
- [ ] Train operations team
- [ ] Schedule checkpoint cleanup (if needed)
- [ ] Plan capacity review in 30 days
