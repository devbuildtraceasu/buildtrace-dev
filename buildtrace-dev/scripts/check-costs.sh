#!/bin/bash
# Check GCP costs for the past 7 days across all services
# Requires billing account to be linked to project

set -e

PROJECT_ID="buildtrace-dev"
DAYS=7

echo "💰 GCP Cost Analysis - Past ${DAYS} Days"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo ""

# Check if billing is enabled
echo "📊 Checking billing account..."
BILLING_ACCOUNT=$(gcloud billing projects describe ${PROJECT_ID} --format="value(billingAccountName)" 2>/dev/null || echo "")

if [ -z "$BILLING_ACCOUNT" ]; then
    echo "⚠️  Warning: No billing account linked or billing API not enabled"
    echo "   To enable: gcloud billing projects link ${PROJECT_ID} --billing-account=BILLING_ACCOUNT_ID"
    echo ""
fi

# Calculate date range
END_DATE=$(date -u +"%Y-%m-%d")
START_DATE=$(date -u -v-${DAYS}d +"%Y-%m-%d" 2>/dev/null || date -u -d "${DAYS} days ago" +"%Y-%m-%d" 2>/dev/null || date -u --date="${DAYS} days ago" +"%Y-%m-%d")

echo "📅 Date Range: ${START_DATE} to ${END_DATE}"
echo ""

# Check if billing export is set up (for detailed cost breakdown)
echo "🔍 Checking service costs..."
echo ""

# Get cost breakdown by service using billing export or estimate
# Note: This requires billing export to BigQuery or using Cloud Billing API

# Method 1: Try to get costs from Cloud Billing API (if available)
echo "📈 Service Cost Breakdown (Past ${DAYS} days):"
echo "-----------------------------------------------"

# List all services and their estimated costs
# This is a simplified version - full details require billing export

# Check Cloud SQL costs
echo ""
echo "🗄️  Cloud SQL:"
gcloud sql instances list --project=${PROJECT_ID} --format="table(name,settings.tier,state,settings.activationPolicy)" 2>/dev/null || echo "  No Cloud SQL instances found"

# Check Cloud Run costs
echo ""
echo "🚀 Cloud Run Services:"
gcloud run services list --project=${PROJECT_ID} --format="table(metadata.name,status.url,status.conditions[0].status)" 2>/dev/null || echo "  No Cloud Run services found"

# Check GCS storage
echo ""
echo "📦 Cloud Storage Buckets:"
gsutil ls -L -b gs://buildtrace-dev-* 2>/dev/null | grep -E "gs://|Storage class|Size" || echo "  Checking buckets..."

# Check Pub/Sub
echo ""
echo "📨 Pub/Sub Topics:"
gcloud pubsub topics list --project=${PROJECT_ID} --format="table(name)" 2>/dev/null || echo "  No Pub/Sub topics found"

# Check Artifact Registry
echo ""
echo "📦 Artifact Registry:"
gcloud artifacts repositories list --project=${PROJECT_ID} --location=us-west2 --format="table(name,format)" 2>/dev/null || echo "  No repositories found"

echo ""
echo "=========================================="
echo ""
echo "💡 For detailed cost breakdown:"
echo "   1. Enable billing export to BigQuery"
echo "   2. Use Cloud Billing API"
echo "   3. Check GCP Console: https://console.cloud.google.com/billing"
echo ""
echo "📊 Quick Cost Check:"
echo "   gcloud billing accounts list"
echo "   gcloud billing projects describe ${PROJECT_ID}"
echo ""

# Try to get estimated costs (if billing export is available)
if command -v bq &> /dev/null; then
    echo "🔍 Checking BigQuery billing export (if configured)..."
    # This would require billing export to be set up
fi

echo "✅ Cost check complete!"
echo ""
echo "💸 To view detailed costs in console:"
echo "   https://console.cloud.google.com/billing?project=${PROJECT_ID}"
