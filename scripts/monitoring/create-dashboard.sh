#!/bin/bash
# Create Cloud Monitoring Dashboard for BuildTrace Infrastructure

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Creating BuildTrace Infrastructure Dashboard"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Set project
gcloud config set project $PROJECT_ID > /dev/null 2>&1

# Create temp dashboard file with project/region replaced
TEMP_DASHBOARD=$(mktemp)
sed "s/PROJECT_ID/$PROJECT_ID/g; s/REGION/$REGION/g" \
    "$SCRIPT_DIR/buildtrace-infrastructure-dashboard.json" > "$TEMP_DASHBOARD"

echo "Creating dashboard..."
gcloud monitoring dashboards create --config-from-file="$TEMP_DASHBOARD" || {
    echo "⚠️  Dashboard may already exist. Updating instead..."
    # Get dashboard ID (this is a simplified approach)
    DASHBOARD_ID=$(gcloud monitoring dashboards list --filter="displayName:BuildTrace Infrastructure Dashboard" --format="value(name)" | head -1 | awk -F'/' '{print $NF}')
    if [ -n "$DASHBOARD_ID" ]; then
        echo "Updating existing dashboard: $DASHBOARD_ID"
        gcloud monitoring dashboards update "$DASHBOARD_ID" --config-from-file="$TEMP_DASHBOARD"
    fi
}

rm "$TEMP_DASHBOARD"

echo ""
echo "✅ Dashboard created successfully!"
echo ""
echo "View dashboard at:"
echo "https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT_ID"
echo ""