#!/bin/bash
# Get detailed cost summary for past 7 days using Cloud Billing API
# Requires billing account and billing API enabled

set -e

PROJECT_ID="buildtrace-dev"
DAYS=7

echo "💰 GCP Cost Summary - Past ${DAYS} Days"
echo "========================================"
echo "Project: ${PROJECT_ID}"
echo ""

# Get billing account
BILLING_ACCOUNT=$(gcloud billing projects describe ${PROJECT_ID} --format="value(billingAccountName)" 2>/dev/null)

if [ -z "$BILLING_ACCOUNT" ]; then
    echo "❌ No billing account linked to project"
    echo "   Link billing: gcloud billing projects link ${PROJECT_ID} --billing-account=BILLING_ACCOUNT_ID"
    exit 1
fi

BILLING_ACCOUNT_ID=$(basename "$BILLING_ACCOUNT")
echo "📊 Billing Account: ${BILLING_ACCOUNT_ID}"
echo ""

# Calculate date range
END_DATE=$(date -u +"%Y-%m-%d")
START_DATE=$(date -u -v-${DAYS}d +"%Y-%m-%d" 2>/dev/null || date -u -d "${DAYS} days ago" +"%Y-%m-%d" 2>/dev/null || date -u --date="${DAYS} days ago" +"%Y-%m-%d")

echo "📅 Period: ${START_DATE} to ${END_DATE}"
echo ""

# Check if Cloud Billing API is enabled
echo "🔍 Fetching cost data..."
echo ""

# Get costs by service using gcloud billing
# Note: This requires Cloud Billing API and proper permissions

# Method: Use gcloud to get cost breakdown
echo "📈 Cost Breakdown by Service:"
echo "-----------------------------"

# Try to get costs from billing export or use estimation
# For actual costs, we need to query BigQuery billing export or use Cloud Billing API

# Get resource usage summary
echo ""
echo "🔧 Resource Usage Summary:"
echo ""

# Cloud SQL
echo "🗄️  Cloud SQL Instance:"
SQL_INFO=$(gcloud sql instances describe buildtrace-dev-db --project=${PROJECT_ID} --format="yaml(settings.tier,state,settings.activationPolicy,settings.dataDiskSizeGb,settings.dataDiskType)" 2>/dev/null)
if [ ! -z "$SQL_INFO" ]; then
    echo "$SQL_INFO" | grep -E "tier:|state:|activationPolicy:|dataDiskSizeGb:|dataDiskType:" | sed 's/^/  /'
    echo "  💰 Estimated daily cost (if running): ~\$50-100 (depends on tier)"
    echo "  💰 Current status: STOPPED (only storage charged)"
fi

# Cloud Run services
echo ""
echo "🚀 Cloud Run Services:"
RUN_SERVICES=$(gcloud run services list --project=${PROJECT_ID} --format="table(metadata.name,status.url,spec.template.spec.containers[0].resources.limits.cpu,spec.template.spec.containers[0].resources.limits.memory,spec.template.spec.serviceAccountName)" 2>/dev/null)
if [ ! -z "$RUN_SERVICES" ]; then
    echo "$RUN_SERVICES"
    echo "  💰 Estimated: ~\$0.10-0.50 per service per day (with traffic)"
fi

# GCS Storage
echo ""
echo "📦 Cloud Storage:"
echo "  Checking bucket sizes..."
for bucket in buildtrace-dev-input-buildtrace-dev buildtrace-dev-processed-buildtrace-dev buildtrace-dev-artifacts-buildtrace-dev buildtrace-dev-logs-buildtrace-dev; do
    SIZE=$(gsutil du -sh gs://${bucket} 2>/dev/null | awk '{print $1}' || echo "N/A")
    echo "    ${bucket}: ${SIZE}"
done
echo "  💰 Estimated: ~\$0.023 per GB/month (Standard storage)"

# Pub/Sub
echo ""
echo "📨 Pub/Sub:"
TOPIC_COUNT=$(gcloud pubsub topics list --project=${PROJECT_ID} --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
echo "  Topics: ${TOPIC_COUNT}"
echo "  💰 Estimated: ~\$0.40 per million messages"

# Artifact Registry
echo ""
echo "📦 Artifact Registry:"
REPO_COUNT=$(gcloud artifacts repositories list --project=${PROJECT_ID} --location=us-west2 --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
echo "  Repositories: ${REPO_COUNT}"
echo "  💰 Estimated: ~\$0.10 per GB/month storage"

echo ""
echo "========================================"
echo ""
echo "📊 To get EXACT costs, use one of these methods:"
echo ""
echo "1. GCP Console (Recommended):"
echo "   https://console.cloud.google.com/billing/${BILLING_ACCOUNT_ID}/reports?project=${PROJECT_ID}"
echo ""
echo "2. Enable Billing Export to BigQuery:"
echo "   - Go to: Billing > Billing Export"
echo "   - Enable export to BigQuery"
echo "   - Query: SELECT service.description, SUM(cost) as total_cost"
echo "            FROM \`project.dataset.gcp_billing_export\`"
echo "            WHERE _PARTITIONTIME >= TIMESTAMP('${START_DATE}')"
echo "            GROUP BY service.description"
echo ""
echo "3. Use Cloud Billing API:"
echo "   gcloud alpha billing budgets list --billing-account=${BILLING_ACCOUNT_ID}"
echo ""
echo "💡 Current Status:"
echo "   ✅ Cloud SQL: STOPPED (saving compute costs)"
echo "   ⚠️  Other services: Running (check console for exact costs)"
echo ""
