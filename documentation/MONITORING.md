# BuildTrace Monitoring & Observability

Complete guide to logging, metrics, alerting, and observability for BuildTrace.

## Table of Contents

1. [Overview](#overview)
2. [Logging](#logging)
3. [Metrics](#metrics)
4. [Alerting](#alerting)
5. [Tracing](#tracing)
6. [Dashboards](#dashboards)

## Overview

BuildTrace uses **Google Cloud Logging** and **Cloud Monitoring** for observability:

- **Logging**: Structured logs with Cloud Logging
- **Metrics**: Custom and built-in metrics
- **Alerting**: Cloud Monitoring alerts
- **Tracing**: Request tracing (future)

## Logging

### Log Levels

**Standard Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Logging Configuration

**Local Development:**
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

**Production (Cloud Run):**
```python
import logging

# Cloud Run automatically captures stdout/stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Structured Logging

**Use Structured Logs:**
```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured log
logger.info("Processing started", extra={
    "session_id": session_id,
    "file_size": file_size,
    "file_type": file_type
})
```

**JSON Format (Production):**
```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### Log Categories

**Application Logs:**
```python
logger.info("Application started", extra={"environment": config.ENVIRONMENT})
logger.info("Request received", extra={"method": request.method, "path": request.path})
logger.info("Processing completed", extra={"session_id": session_id, "duration": duration})
```

**Error Logs:**
```python
try:
    # Code
except Exception as e:
    logger.error("Processing failed", extra={
        "session_id": session_id,
        "error": str(e),
        "error_type": type(e).__name__
    }, exc_info=True)
```

**Performance Logs:**
```python
import time

start_time = time.time()
# Processing
duration = time.time() - start_time
logger.info("Processing duration", extra={
    "session_id": session_id,
    "duration_seconds": duration,
    "operation": "pipeline"
})
```

### Viewing Logs

**Local:**
```bash
tail -f app.log
grep "ERROR" app.log
```

**Cloud Run:**
```bash
# Recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Filter by service
gcloud logging read \
    "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-overlay" \
    --limit=50

# Filter by severity
gcloud logging read \
    "resource.type=cloud_run_revision AND severity>=ERROR" \
    --limit=50

# Filter by time
gcloud logging read \
    "resource.type=cloud_run_revision AND timestamp>=\"2024-01-15T00:00:00Z\"" \
    --limit=50
```

**Cloud Console:**
- Navigate to Cloud Logging
- Filter by resource type: Cloud Run Revision
- Filter by service name, severity, etc.

## Metrics

### Built-in Metrics

**Cloud Run Metrics:**
- Request count
- Request latency
- Error rate
- CPU utilization
- Memory usage
- Instance count

**View Metrics:**
```bash
# Using gcloud
gcloud monitoring time-series list \
    --filter='resource.type="cloud_run_revision"'

# Cloud Console
# Navigate to Cloud Monitoring > Metrics Explorer
```

### Custom Metrics

**Define Custom Metrics:**
```python
from google.cloud import monitoring_v3

client = monitoring_v3.MetricServiceClient()
project_name = f"projects/{config.CLOUD_TASKS_PROJECT}"

# Create metric descriptor
descriptor = monitoring_v3.MetricDescriptor()
descriptor.type = "custom.googleapis.com/buildtrace/processing_time"
descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.GAUGE
descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.DOUBLE
descriptor.description = "Processing time in seconds"

client.create_metric_descriptor(
    name=project_name,
    metric_descriptor=descriptor
)
```

**Write Metrics:**
```python
from google.cloud import monitoring_v3
import time

client = monitoring_v3.MetricServiceClient()
project_name = f"projects/{config.CLOUD_TASKS_PROJECT}"

series = monitoring_v3.TimeSeries()
series.metric.type = "custom.googleapis.com/buildtrace/processing_time"
series.resource.type = "cloud_run_revision"
series.resource.labels["service_name"] = "buildtrace-overlay"
series.resource.labels["revision_name"] = "buildtrace-overlay-00001"

point = monitoring_v3.Point()
point.value.double_value = processing_time
point.interval.end_time.seconds = int(time.time())

series.points = [point]
client.create_time_series(name=project_name, time_series=[series])
```

### Key Metrics to Track

**Application Metrics:**
- Processing time per drawing
- Alignment success rate
- AI analysis success rate
- File upload size
- Session count

**Infrastructure Metrics:**
- Database connection pool usage
- Storage operations (upload/download)
- API response times
- Error rates by endpoint

**Business Metrics:**
- Active sessions
- Drawings processed per day
- User engagement
- Feature usage

## Alerting

### Alert Policies

**Create Alert Policy:**
```bash
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="High Error Rate" \
    --condition-threshold-value=0.05 \
    --condition-threshold-duration=300s \
    --condition-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="buildtrace-overlay"'
```

### Common Alerts

**High Error Rate:**
```yaml
displayName: High Error Rate
conditions:
  - displayName: Error rate > 5%
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        AND resource.labels.service_name="buildtrace-overlay"
        AND metric.type="run.googleapis.com/request_count"
        AND metric.labels.response_code_class="5xx"
      comparison: COMPARISON_GT
      thresholdValue: 0.05
      duration: 300s
```

**High Latency:**
```yaml
displayName: High Latency
conditions:
  - displayName: P95 latency > 2s
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        AND metric.type="run.googleapis.com/request_latencies"
      comparison: COMPARISON_GT
      thresholdValue: 2000
      duration: 300s
```

**Low Instance Count:**
```yaml
displayName: Low Instance Count
conditions:
  - displayName: Instances < 1
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        AND metric.type="run.googleapis.com/container/instance_count"
      comparison: COMPARISON_LT
      thresholdValue: 1
      duration: 60s
```

### Notification Channels

**Create Email Channel:**
```bash
gcloud alpha monitoring channels create \
    --type=email \
    --display-name="BuildTrace Alerts" \
    --channel-labels=email_address=alerts@example.com
```

**Create Slack Channel:**
```bash
gcloud alpha monitoring channels create \
    --type=slack \
    --display-name="BuildTrace Slack" \
    --channel-labels=channel_name=#buildtrace-alerts
```

## Tracing

### Request Tracing (Future)

**OpenTelemetry Integration:**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

cloud_trace_exporter = CloudTraceSpanExporter()
span_processor = BatchSpanProcessor(cloud_trace_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Use in code
with tracer.start_as_current_span("process_drawing"):
    # Processing code
    pass
```

## Dashboards

### Cloud Monitoring Dashboard

**Create Dashboard:**
```bash
# Via gcloud (JSON config)
gcloud monitoring dashboards create --config-from-file=dashboard.json

# Via Cloud Console
# Navigate to Cloud Monitoring > Dashboards > Create Dashboard
```

**Dashboard Widgets:**
- Line charts for metrics over time
- Bar charts for counts
- Gauge charts for current values
- Tables for detailed data

### Key Dashboards

**Application Health:**
- Request count
- Error rate
- Latency (p50, p95, p99)
- Instance count

**Processing Metrics:**
- Processing time
- Success rate
- Files processed
- Queue depth

**Infrastructure:**
- CPU usage
- Memory usage
- Database connections
- Storage usage

## Best Practices

### Logging Best Practices

1. **Use Appropriate Levels**
   - DEBUG: Development only
   - INFO: Important events
   - WARNING: Recoverable issues
   - ERROR: Failures requiring attention

2. **Include Context**
   - Session IDs
   - User IDs
   - Request IDs
   - Timestamps

3. **Avoid Sensitive Data**
   - Never log passwords
   - Mask API keys
   - Sanitize user input

4. **Structured Logs**
   - Use JSON format in production
   - Include relevant metadata
   - Consistent field names

### Metrics Best Practices

1. **Track Key Business Metrics**
   - User engagement
   - Feature usage
   - Processing success rates

2. **Monitor Infrastructure**
   - Resource utilization
   - Error rates
   - Performance metrics

3. **Set Appropriate Thresholds**
   - Based on historical data
   - Account for normal variations
   - Avoid alert fatigue

### Alerting Best Practices

1. **Actionable Alerts**
   - Clear description
   - Include context
   - Suggest remediation

2. **Appropriate Severity**
   - Critical: Immediate action needed
   - Warning: Attention required
   - Info: Informational only

3. **Avoid Alert Fatigue**
   - Set reasonable thresholds
   - Use alert grouping
   - Review and tune regularly

---

**Next Steps**: See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for debugging or [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment monitoring.

