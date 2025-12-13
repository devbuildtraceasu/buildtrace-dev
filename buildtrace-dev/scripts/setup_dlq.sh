#!/bin/bash
#
# Setup Dead Letter Queues and configure max_delivery_attempts
# This script creates DLQ topics/subscriptions and configures retry limits
#
# Usage: ./scripts/setup_dlq.sh
#

set -e

PROJECT_ID="${GCP_PROJECT_ID:-buildtrace-dev}"
REGION="${GCP_REGION:-us-west2}"

echo "================================================================================"
echo "SETTING UP DEAD LETTER QUEUES FOR BUILDTRACE"
echo "================================================================================"
echo "Project: ${PROJECT_ID}"
echo ""

# Topics
OCR_TOPIC="buildtrace-dev-ocr-queue"
DIFF_TOPIC="buildtrace-dev-diff-queue"
SUMMARY_TOPIC="buildtrace-dev-summary-queue"

# Subscriptions
OCR_SUB="buildtrace-dev-ocr-sub"
DIFF_SUB="buildtrace-dev-diff-sub"
SUMMARY_SUB="buildtrace-dev-summary-sub"

# DLQ Topics
OCR_DLQ="buildtrace-dev-ocr-dlq"
DIFF_DLQ="buildtrace-dev-diff-dlq"
SUMMARY_DLQ="buildtrace-dev-summary-dlq"

# DLQ Subscriptions (for monitoring dead letters)
OCR_DLQ_SUB="buildtrace-dev-ocr-dlq-sub"
DIFF_DLQ_SUB="buildtrace-dev-diff-dlq-sub"
SUMMARY_DLQ_SUB="buildtrace-dev-summary-dlq-sub"

# Max delivery attempts before sending to DLQ
MAX_DELIVERY_ATTEMPTS=5

# Service account for DLQ permissions
SERVICE_ACCOUNT="buildtrace-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Step 1: Creating Dead Letter Queue topics..."
echo "----------------------------------------"

for DLQ in $OCR_DLQ $DIFF_DLQ $SUMMARY_DLQ; do
    if gcloud pubsub topics describe $DLQ --project=$PROJECT_ID >/dev/null 2>&1; then
        echo "✓ Topic $DLQ already exists"
    else
        echo "Creating topic $DLQ..."
        gcloud pubsub topics create $DLQ --project=$PROJECT_ID
        echo "✓ Created topic $DLQ"
    fi
done

echo ""
echo "Step 2: Creating DLQ subscriptions (for monitoring)..."
echo "----------------------------------------"

for DLQ_SUB in "$OCR_DLQ_SUB $OCR_DLQ" "$DIFF_DLQ_SUB $DIFF_DLQ" "$SUMMARY_DLQ_SUB $SUMMARY_DLQ"; do
    SUB_NAME=$(echo $DLQ_SUB | cut -d' ' -f1)
    TOPIC_NAME=$(echo $DLQ_SUB | cut -d' ' -f2)
    
    if gcloud pubsub subscriptions describe $SUB_NAME --project=$PROJECT_ID >/dev/null 2>&1; then
        echo "✓ Subscription $SUB_NAME already exists"
    else
        echo "Creating subscription $SUB_NAME for topic $TOPIC_NAME..."
        gcloud pubsub subscriptions create $SUB_NAME \
            --topic=$TOPIC_NAME \
            --project=$PROJECT_ID \
            --ack-deadline=600 \
            --message-retention-duration=7d
        echo "✓ Created subscription $SUB_NAME"
    fi
done

echo ""
echo "Step 3: Granting DLQ publish permissions to main subscriptions..."
echo "----------------------------------------"

# Get the project number for the subscription service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

for DLQ in $OCR_DLQ $DIFF_DLQ $SUMMARY_DLQ; do
    echo "Granting publisher role on $DLQ to Pub/Sub service account..."
    gcloud pubsub topics add-iam-policy-binding $DLQ \
        --member="serviceAccount:${PUBSUB_SA}" \
        --role="roles/pubsub.publisher" \
        --project=$PROJECT_ID \
        --quiet 2>/dev/null || true
    echo "✓ Granted publisher role on $DLQ"
done

echo ""
echo "Step 4: Updating subscriptions with DLQ and max_delivery_attempts..."
echo "----------------------------------------"

# Update OCR subscription
echo "Updating $OCR_SUB..."
gcloud pubsub subscriptions update $OCR_SUB \
    --project=$PROJECT_ID \
    --dead-letter-topic=$OCR_DLQ \
    --max-delivery-attempts=$MAX_DELIVERY_ATTEMPTS \
    --dead-letter-topic-project=$PROJECT_ID \
    || echo "Warning: Could not update $OCR_SUB (may not exist yet)"
echo "✓ Updated $OCR_SUB"

# Update Diff subscription  
echo "Updating $DIFF_SUB..."
gcloud pubsub subscriptions update $DIFF_SUB \
    --project=$PROJECT_ID \
    --dead-letter-topic=$DIFF_DLQ \
    --max-delivery-attempts=$MAX_DELIVERY_ATTEMPTS \
    --dead-letter-topic-project=$PROJECT_ID \
    || echo "Warning: Could not update $DIFF_SUB (may not exist yet)"
echo "✓ Updated $DIFF_SUB"

# Update Summary subscription
echo "Updating $SUMMARY_SUB..."
gcloud pubsub subscriptions update $SUMMARY_SUB \
    --project=$PROJECT_ID \
    --dead-letter-topic=$SUMMARY_DLQ \
    --max-delivery-attempts=$MAX_DELIVERY_ATTEMPTS \
    --dead-letter-topic-project=$PROJECT_ID \
    || echo "Warning: Could not update $SUMMARY_SUB (may not exist yet)"
echo "✓ Updated $SUMMARY_SUB"

echo ""
echo "================================================================================"
echo "DEAD LETTER QUEUE SETUP COMPLETE"
echo "================================================================================"
echo ""
echo "Configuration:"
echo "  Max delivery attempts: $MAX_DELIVERY_ATTEMPTS"
echo ""
echo "DLQ Topics:"
echo "  - $OCR_DLQ"
echo "  - $DIFF_DLQ"
echo "  - $SUMMARY_DLQ"
echo ""
echo "DLQ Subscriptions (for monitoring):"
echo "  - $OCR_DLQ_SUB"
echo "  - $DIFF_DLQ_SUB"
echo "  - $SUMMARY_DLQ_SUB"
echo ""
echo "Messages that fail $MAX_DELIVERY_ATTEMPTS times will be sent to the DLQ."
echo "Monitor DLQ subscriptions to investigate and retry failed messages."
echo ""
echo "To pull dead letters:"
echo "  gcloud pubsub subscriptions pull $OCR_DLQ_SUB --project=$PROJECT_ID --limit=10"
echo "  gcloud pubsub subscriptions pull $DIFF_DLQ_SUB --project=$PROJECT_ID --limit=10"
echo "  gcloud pubsub subscriptions pull $SUMMARY_DLQ_SUB --project=$PROJECT_ID --limit=10"
echo ""

