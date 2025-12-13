#!/bin/bash
# Setup Pub/Sub topics and subscriptions for BuildTrace

set -e

PROJECT_ID=${GCP_PROJECT_ID:-buildtrace-dev}
REGION=${GCP_REGION:-us-west2}

echo "Setting up Pub/Sub topics and subscriptions for project: $PROJECT_ID"

# Topics
OCR_TOPIC="buildtrace-dev-ocr-queue"
DIFF_TOPIC="buildtrace-dev-diff-queue"
SUMMARY_TOPIC="buildtrace-dev-summary-queue"

# Subscriptions
OCR_SUB="buildtrace-dev-ocr-worker-sub"
DIFF_SUB="buildtrace-dev-diff-worker-sub"
SUMMARY_SUB="buildtrace-dev-summary-worker-sub"

# Create topics
echo "Creating topics..."
gcloud pubsub topics create $OCR_TOPIC --project=$PROJECT_ID || echo "Topic $OCR_TOPIC already exists"
gcloud pubsub topics create $DIFF_TOPIC --project=$PROJECT_ID || echo "Topic $DIFF_TOPIC already exists"
gcloud pubsub topics create $SUMMARY_TOPIC --project=$PROJECT_ID || echo "Topic $SUMMARY_TOPIC already exists"

# Create subscriptions
echo "Creating subscriptions..."
gcloud pubsub subscriptions create $OCR_SUB \
    --topic=$OCR_TOPIC \
    --ack-deadline=600 \
    --message-retention-duration=7d \
    --project=$PROJECT_ID || echo "Subscription $OCR_SUB already exists"

gcloud pubsub subscriptions create $DIFF_SUB \
    --topic=$DIFF_TOPIC \
    --ack-deadline=600 \
    --message-retention-duration=7d \
    --project=$PROJECT_ID || echo "Subscription $DIFF_SUB already exists"

gcloud pubsub subscriptions create $SUMMARY_SUB \
    --topic=$SUMMARY_TOPIC \
    --ack-deadline=600 \
    --message-retention-duration=7d \
    --project=$PROJECT_ID || echo "Subscription $SUMMARY_SUB already exists"

echo "✅ Pub/Sub setup complete!"
echo ""
echo "Topics:"
echo "  - $OCR_TOPIC"
echo "  - $DIFF_TOPIC"
echo "  - $SUMMARY_TOPIC"
echo ""
echo "Subscriptions:"
echo "  - $OCR_SUB"
echo "  - $DIFF_SUB"
echo "  - $SUMMARY_SUB"

