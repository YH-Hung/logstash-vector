# Vector Monitoring and Alerting Guide

This document describes how to monitor the Vector log processing pipeline and configure alerts for operational issues.

## Table of Contents

1. [Vector Internal Metrics](#vector-internal-metrics)
2. [Prometheus Integration](#prometheus-integration)
3. [Key Metrics Reference](#key-metrics-reference)
4. [gRPC Log Metrics](#grpc-log-metrics)
5. [Alert Thresholds](#alert-thresholds)
6. [Grafana Dashboard](#grafana-dashboard)
7. [Alert Rules](#alert-rules)

---

## Vector Internal Metrics

Vector exposes internal metrics via a Prometheus-compatible endpoint. These metrics provide visibility into:
- Event throughput
- Processing latency
- Error rates
- Buffer utilization
- Component health

### Enabling Metrics

The production configuration in `impl/vector.yaml` uses a single `prometheus_exporter` sink named `prometheus_metrics` that combines Vector internal metrics with gRPC log metrics:

```yaml
sources:
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
    flush_period_secs: 300   # keeps rare error counters visible across scrape cycles
```

For a minimal setup (internal metrics only), a simpler configuration is sufficient:

```yaml
# Add internal metrics source
sources:
  internal_metrics:
    type: internal_metrics
    scrape_interval_secs: 15

# Expose via Prometheus endpoint
sinks:
  prometheus_exporter:
    type: prometheus_exporter
    inputs:
      - internal_metrics
    address: "0.0.0.0:9598"
```

Alternatively, use the built-in API:

```yaml
api:
  enabled: true
  address: "0.0.0.0:8686"
```

### Accessing Metrics

**Via API endpoint:**
```bash
curl http://localhost:8686/metrics
```

**Via Prometheus exporter:**
```bash
curl http://localhost:9598/metrics
```

---

## Prometheus Integration

### Scrape Configuration

Add to your Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'vector'
    static_configs:
      - targets: ['vector:9598']
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
```

**For Kubernetes with service discovery:**

```yaml
scrape_configs:
  - job_name: 'vector'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: vector
      - source_labels: [__meta_kubernetes_pod_container_port_number]
        action: keep
        regex: "9598"
```

### ServiceMonitor (Prometheus Operator)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vector
  labels:
    app: vector
spec:
  selector:
    matchLabels:
      app: vector
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```

---

## Key Metrics Reference

### Event Throughput

| Metric | Type | Description |
|--------|------|-------------|
| `component_received_events_total` | Counter | Total events received by component |
| `component_sent_events_total` | Counter | Total events sent by component |
| `component_received_bytes_total` | Counter | Total bytes received |
| `component_sent_bytes_total` | Counter | Total bytes sent |

**Usage:**
```promql
# Events per second (received)
rate(component_received_events_total{component_name="ap_log_files"}[5m])

# Events per second (sent to ES)
rate(component_sent_events_total{component_name="elasticsearch_output"}[5m])
```

### Error Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `component_errors_total` | Counter | Total errors by component |
| `component_discarded_events_total` | Counter | Events dropped/discarded |

**Usage:**
```promql
# Error rate
rate(component_errors_total[5m])

# Discarded events
increase(component_discarded_events_total[1h])
```

### Buffer Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `buffer_byte_size` | Gauge | Current buffer size in bytes |
| `buffer_events` | Gauge | Current events in buffer |
| `buffer_received_events_total` | Counter | Events added to buffer |
| `buffer_sent_events_total` | Counter | Events removed from buffer |

**Usage:**
```promql
# Buffer utilization percentage (assuming 8MB max)
buffer_byte_size / 8388608 * 100

# Buffer growth rate
rate(buffer_received_events_total[5m]) - rate(buffer_sent_events_total[5m])
```

### Latency Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `component_received_event_bytes_total` | Counter | Event size tracking |
| `utilization` | Gauge | Component utilization (0-1) |

### File Source Specific

| Metric | Type | Description |
|--------|------|-------------|
| `file_open` | Gauge | Number of open file handles |
| `files_open` | Gauge | Files being tailed |

**Usage:**
```promql
# Files being watched
files_open{component_name="ap_log_files"}
```

### Elasticsearch Sink Specific

| Metric | Type | Description |
|--------|------|-------------|
| `http_client_requests_total` | Counter | HTTP requests made |
| `http_client_request_duration_seconds` | Histogram | Request latency |

**Usage:**
```promql
# ES request latency (p99)
histogram_quantile(0.99, rate(http_client_request_duration_seconds_bucket[5m]))

# ES request success rate
sum(rate(http_client_requests_total{status="200"}[5m])) / sum(rate(http_client_requests_total[5m]))
```

---

## gRPC Log Metrics

The gRPC metrics pipeline produces two application-level counters from log files matching `/app/log/grpc_*.log`. These are exposed alongside Vector internal metrics at `0.0.0.0:9598/metrics`.

### Counters

| Counter | Tags | Description |
|---------|------|-------------|
| `grpc_log_messages_total` | `severity`, `severity_code`, `file` | Every successfully parsed gRPC log line (info, warning, error, fatal) |
| `grpc_log_errors_total` | `severity`, `file` | Error and fatal lines only |

Severity values: `info` (I), `warning` (W), `error` (E), `fatal` (F). Error and fatal lines are intentionally counted in **both** counters — `grpc_log_messages_total` for overall rate tracking and `grpc_log_errors_total` for alerting.

Lines that do not match the glog/gpr format are dropped and do not appear in any counter.

### Example PromQL Queries

```promql
# Total gRPC log messages by severity
sum by (severity) (grpc_log_messages_total)

# Per-file gRPC message rate (5m window)
sum by (file) (rate(grpc_log_messages_total[5m]))

# Overall gRPC error/fatal rate
sum(rate(grpc_log_errors_total[5m]))
```

---

## Alert Thresholds

### Critical Alerts (P1)

| Alert | Condition | Duration | Description |
|-------|-----------|----------|-------------|
| VectorDown | `up{job="vector"} == 0` | 1m | Vector not responding |
| NoEventsFlowing | `rate(component_sent_events_total[5m]) == 0` | 5m | No events being processed |
| HighErrorRate | `rate(component_errors_total[5m]) > 1` | 5m | Sustained errors |

### Warning Alerts (P2)

| Alert | Condition | Duration | Description |
|-------|-----------|----------|-------------|
| BufferNearFull | `buffer_byte_size > 6291456` | 5m | Buffer > 75% (6MB of 8MB) |
| EventsDropped | `increase(component_discarded_events_total[1h]) > 0` | - | Any events discarded |
| ESLatencyHigh | `histogram_quantile(0.99, ...) > 1` | 5m | ES p99 latency > 1s |

### Info Alerts (P3)

| Alert | Condition | Duration | Description |
|-------|-----------|----------|-------------|
| LowThroughput | `rate(component_received_events_total[5m]) < 10` | 15m | Unusually low event rate |
| ConfigReload | `increase(config_reloads_total[5m]) > 0` | - | Configuration was reloaded |

---

## Grafana Dashboard

### Dashboard JSON

Save this as `vector-dashboard.json` and import into Grafana:

```json
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": "${datasource}",
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "palette-classic"},
          "custom": {"axisLabel": "", "axisPlacement": "auto", "barAlignment": 0, "drawStyle": "line", "fillOpacity": 10, "lineInterpolation": "linear", "lineWidth": 1, "pointSize": 5, "showPoints": "auto", "spanNulls": false, "stacking": {"group": "A", "mode": "none"}}
        }
      },
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
      "id": 1,
      "options": {"legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}},
      "targets": [
        {
          "expr": "rate(component_received_events_total{component_name=\"ap_log_files\"}[5m])",
          "legendFormat": "Events In"
        },
        {
          "expr": "rate(component_sent_events_total{component_name=\"elasticsearch_output\"}[5m])",
          "legendFormat": "Events Out"
        }
      ],
      "title": "Event Throughput",
      "type": "timeseries"
    },
    {
      "datasource": "${datasource}",
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "yellow", "value": 6291456}, {"color": "red", "value": 7340032}]},
          "unit": "bytes"
        }
      },
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
      "id": 2,
      "options": {"orientation": "auto", "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false}, "showThresholdLabels": false, "showThresholdMarkers": true},
      "targets": [
        {
          "expr": "buffer_byte_size",
          "legendFormat": "Buffer Size"
        }
      ],
      "title": "Buffer Size",
      "type": "gauge"
    },
    {
      "datasource": "${datasource}",
      "fieldConfig": {
        "defaults": {"color": {"mode": "palette-classic"}, "unit": "short"}
      },
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
      "id": 3,
      "targets": [
        {
          "expr": "rate(component_errors_total[5m])",
          "legendFormat": "{{component_name}}"
        }
      ],
      "title": "Error Rate",
      "type": "timeseries"
    },
    {
      "datasource": "${datasource}",
      "fieldConfig": {
        "defaults": {"color": {"mode": "palette-classic"}, "unit": "s"}
      },
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
      "id": 4,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(http_client_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(http_client_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(http_client_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }
      ],
      "title": "Elasticsearch Latency",
      "type": "timeseries"
    }
  ],
  "refresh": "30s",
  "schemaVersion": 37,
  "style": "dark",
  "tags": ["vector", "logging"],
  "templating": {
    "list": [
      {
        "current": {"selected": false, "text": "Prometheus", "value": "Prometheus"},
        "hide": 0,
        "includeAll": false,
        "label": "Datasource",
        "multi": false,
        "name": "datasource",
        "options": [],
        "query": "prometheus",
        "queryValue": "",
        "refresh": 1,
        "regex": "",
        "skipUrlSync": false,
        "type": "datasource"
      }
    ]
  },
  "time": {"from": "now-1h", "to": "now"},
  "title": "Vector Log Processing",
  "version": 1
}
```

### Key Dashboard Panels

1. **Event Throughput** - Events in vs out over time
2. **Buffer Utilization** - Current buffer size with thresholds
3. **Error Rate** - Errors per component
4. **ES Latency** - Request latency percentiles
5. **Component Status** - Health of each pipeline component

---

## Alert Rules

### Prometheus Alert Rules

Save as `vector-alerts.yaml`:

```yaml
groups:
  - name: vector-critical
    rules:
      - alert: VectorDown
        expr: up{job="vector"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Vector instance is down"
          description: "Vector instance {{ $labels.instance }} has been down for more than 1 minute."

      - alert: VectorNoEventsFlowing
        expr: rate(component_sent_events_total{component_name="elasticsearch_output"}[5m]) == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "No events flowing to Elasticsearch"
          description: "Vector has not sent any events to Elasticsearch in the last 5 minutes."

      - alert: VectorHighErrorRate
        expr: rate(component_errors_total[5m]) > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in Vector"
          description: "Vector component {{ $labels.component_name }} has error rate > 1/sec for 5 minutes."

  - name: vector-warning
    rules:
      - alert: VectorBufferNearFull
        expr: buffer_byte_size > 6291456
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Vector buffer is filling up"
          description: "Vector buffer is at {{ $value | humanize1024 }} (>75% of 8MB limit)."

      - alert: VectorEventsDropped
        expr: increase(component_discarded_events_total[1h]) > 0
        labels:
          severity: warning
        annotations:
          summary: "Vector is dropping events"
          description: "{{ $value }} events have been dropped in the last hour."

      - alert: VectorESLatencyHigh
        expr: histogram_quantile(0.99, rate(http_client_request_duration_seconds_bucket{component_name="elasticsearch_output"}[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Elasticsearch latency is high"
          description: "p99 latency to Elasticsearch is {{ $value | humanizeDuration }}."

  - name: vector-info
    rules:
      - alert: VectorLowThroughput
        expr: rate(component_received_events_total{component_name="ap_log_files"}[5m]) < 10
        for: 15m
        labels:
          severity: info
        annotations:
          summary: "Vector throughput is unusually low"
          description: "Event rate is only {{ $value | printf \"%.2f\" }} events/sec."
```

### AlertManager Configuration

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<pagerduty-service-key>'

  - name: 'slack'
    slack_configs:
      - api_url: '<slack-webhook-url>'
        channel: '#alerts'
```

---

## Monitoring Best Practices

### What to Monitor

1. **Availability**
   - Vector process up/down
   - Health endpoint responding

2. **Throughput**
   - Events received rate
   - Events sent rate
   - Delta between in and out

3. **Errors**
   - Error rate by component
   - Discarded events

4. **Latency**
   - ES request latency
   - End-to-end processing time

5. **Resources**
   - Buffer utilization
   - Memory usage
   - CPU usage

### Alert Fatigue Prevention

- Use appropriate `for` durations
- Group related alerts
- Silence during maintenance
- Review and tune thresholds regularly

### Runbook Links

Include runbook links in alert annotations:

```yaml
annotations:
  runbook_url: "https://wiki.example.com/runbooks/vector"
```
