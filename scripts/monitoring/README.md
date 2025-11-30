# BuildTrace Monitoring Dashboard

This directory contains scripts to create and manage Cloud Monitoring dashboards for BuildTrace infrastructure.

## Quick Start
h
# Make script executable
chmod +x scripts/monitoring/create-dashboard.sh

# Create the dashboard
./scripts/monitoring/create-dashboard.sh## Dashboard Contents

The dashboard includes monitoring for:

### Cloud SQL
- CPU Utilization
- Memory Utilization
- Active Connections
- Disk Utilization

### Pub/Sub
- Message count by topic (OCR, Diff, Summary queues)
- Unacked messages (backlog monitoring)
- Dead-letter queue metrics

### Cloud Storage
- Upload/Download operations
- Total storage bytes
- Request counts

### Artifact Registry
- Pull operations
- Push operations

## Viewing the Dashboard

After creation, view the dashboard at:
- Cloud Console: Monitoring > Dashboards
- Direct link: https://console.cloud.google.com/monitoring/dashboards?project=PROJECT_ID

## Customization

Edit `buildtrace-infrastructure-dashboard.json` to:
- Add more widgets
- Change time ranges
- Adjust aggregation periods
- Add custom metrics

## Manual Creation (Alternative)

If you prefer to create via Console:

1. Navigate to Cloud Monitoring > Dashboards
2. Click "CREATE DASHBOARD"
3. Add widgets for each metric
4. Save as "BuildTrace Infrastructure Dashboard"