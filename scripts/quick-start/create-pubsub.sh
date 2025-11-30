#!/bin/bash
# Create Pub/Sub topics and subscriptions for BuildTrace job queues

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"

echo "=========================================="
echo "Creating Pub/Sub Topics and Subscriptions"
echo "Project: $PROJECT_ID"
echo "=========================================="

# Set project
gcloud config set project $PROJECT_ID

# Create main topics
echo "Creating main topics..."
gcloud pubsub topics create buildtrace-dev-ocr-queue || echo "Topic may already exist"
gcloud pubsub topics create buildtrace-dev-diff-queue || echo "Topic may already exist"
gcloud pubsub topics create buildtrace-dev-summary-queue || echo "Topic may already exist"
gcloud pubsub topics create buildtrace-dev-orchestrator-queue || echo "Topic may already exist"

# Create dead-letter topics
echo "Creating dead-letter topics..."
gcloud pubsub topics create buildtrace-dev-ocr-dlq || echo "DLQ topic may already exist"
gcloud pubsub topics create buildtrace-dev-diff-dlq || echo "DLQ topic may already exist"
gcloud pubsub topics create buildtrace-dev-summary-dlq || echo "DLQ topic may already exist"

# Create pull subscriptions (will convert to push after worker deployment)
echo ""
echo "Creating worker subscriptions..."

# OCR worker subscription
gcloud pubsub subscriptions create buildtrace-dev-ocr-worker-sub \
  --topic=buildtrace-dev-ocr-queue \
  --ack-deadline=600 \
  --dead-letter-topic=buildtrace-dev-ocr-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d \
  || echo "Subscription may already exist"

# Diff worker subscription
gcloud pubsub subscriptions create buildtrace-dev-diff-worker-sub \
  --topic=buildtrace-dev-diff-queue \
  --ack-deadline=600 \
  --dead-letter-topic=buildtrace-dev-diff-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d \
  || echo "Subscription may already exist"

# Summary worker subscription
gcloud pubsub subscriptions create buildtrace-dev-summary-worker-sub \
  --topic=buildtrace-dev-summary-queue \
  --ack-deadline=600 \
  --dead-letter-topic=buildtrace-dev-summary-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d \
  || echo "Subscription may already exist"

# Create dead-letter subscriptions (for monitoring)
echo ""
echo "Creating dead-letter subscriptions..."
gcloud pubsub subscriptions create buildtrace-dev-ocr-dlq-sub \
  --topic=buildtrace-dev-ocr-dlq \
  || echo "DLQ subscription may already exist"

gcloud pubsub subscriptions create buildtrace-dev-diff-dlq-sub \
  --topic=buildtrace-dev-diff-dlq \
  || echo "DLQ subscription may already exist"

gcloud pubsub subscriptions create buildtrace-dev-summary-dlq-sub \
  --topic=buildtrace-dev-summary-dlq \
  || echo "DLQ subscription may already exist"

echo ""
echo "✅ Pub/Sub topics and subscriptions created!"
echo ""
echo "Topics created:"
echo "  - buildtrace-dev-ocr-queue"
echo "  - buildtrace-dev-diff-queue"
echo "  - buildtrace-dev-summary-queue"
echo "  - buildtrace-dev-orchestrator-queue"
echo ""
echo "Subscriptions created:"
echo "  - buildtrace-dev-ocr-worker-sub"
echo "  - buildtrace-dev-diff-worker-sub"
echo "  - buildtrace-dev-summary-worker-sub"
echo ""
echo "Note: Subscriptions are currently pull-based."
echo "Update to push subscriptions after deploying workers."

