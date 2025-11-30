#!/bin/bash
set -e

PROJECT_ID="buildtrace-dev"

echo "🔍 Verifying Pub/Sub Topics and Subscriptions"
echo "=============================================="
echo "Project: ${PROJECT_ID}"
echo ""

# Check topics
echo "📋 Checking Topics..."
TOPICS=$(gcloud pubsub topics list --project=${PROJECT_ID} --format="value(name)" | grep "buildtrace-dev" || true)

REQUIRED_TOPICS=(
  "buildtrace-dev-ocr-queue"
  "buildtrace-dev-diff-queue"
  "buildtrace-dev-summary-queue"
)

for topic in "${REQUIRED_TOPICS[@]}"; do
  if echo "$TOPICS" | grep -q "$topic"; then
    echo "  ✅ $topic exists"
  else
    echo "  ❌ $topic MISSING - Creating..."
    gcloud pubsub topics create $topic --project=${PROJECT_ID}
    echo "  ✅ Created $topic"
  fi
done

echo ""
echo "📋 Checking Subscriptions..."
SUBSCRIPTIONS=$(gcloud pubsub subscriptions list --project=${PROJECT_ID} --format="value(name)" | grep "buildtrace-dev" || true)

REQUIRED_SUBS=(
  "buildtrace-dev-ocr-worker-sub"
  "buildtrace-dev-diff-worker-sub"
  "buildtrace-dev-summary-worker-sub"
)

for sub in "${REQUIRED_SUBS[@]}"; do
  sub_name=$(basename $sub)
  if echo "$SUBSCRIPTIONS" | grep -q "$sub_name"; then
    echo "  ✅ $sub_name exists"
  else
    echo "  ❌ $sub_name MISSING - Creating..."
    case $sub_name in
      *ocr*)
        gcloud pubsub subscriptions create $sub_name \
          --topic=buildtrace-dev-ocr-queue \
          --project=${PROJECT_ID} \
          --ack-deadline=600
        ;;
      *diff*)
        gcloud pubsub subscriptions create $sub_name \
          --topic=buildtrace-dev-diff-queue \
          --project=${PROJECT_ID} \
          --ack-deadline=600
        ;;
      *summary*)
        gcloud pubsub subscriptions create $sub_name \
          --topic=buildtrace-dev-summary-queue \
          --project=${PROJECT_ID} \
          --ack-deadline=600
        ;;
    esac
    echo "  ✅ Created $sub_name"
  fi
done

echo ""
echo "✅ Pub/Sub verification complete!"

