#!/bin/bash
# End-to-end test script for BuildTrace async processing

set -e

BACKEND_URL="https://buildtrace-backend-otllaxbiza-wl.a.run.app"
OLD_PDF="testing/A-111/A-111_old.pdf"
NEW_PDF="testing/A-111/A-111_new.pdf"
PROJECT_ID="default-project"
USER_ID="ash-system-0000000000001"

echo "=========================================="
echo "BuildTrace End-to-End Test"
echo "=========================================="
echo "Backend URL: $BACKEND_URL"
echo ""

# Step 1: Upload old PDF
echo "Step 1: Uploading old PDF..."
OLD_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/drawings/upload" \
  -F "file=@$OLD_PDF" \
  -F "project_id=$PROJECT_ID" \
  -F "user_id=$USER_ID")

echo "Response: $OLD_RESPONSE"
OLD_VERSION_ID=$(echo "$OLD_RESPONSE" | grep -o '"drawing_version_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$OLD_VERSION_ID" ]; then
  echo "ERROR: Failed to get old_version_id from response"
  echo "Full response: $OLD_RESPONSE"
  exit 1
fi

echo "✓ Old version ID: $OLD_VERSION_ID"
echo ""

# Step 2: Upload new PDF
echo "Step 2: Uploading new PDF..."
NEW_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/drawings/upload" \
  -F "file=@$NEW_PDF" \
  -F "project_id=$PROJECT_ID" \
  -F "user_id=$USER_ID" \
  -F "old_version_id=$OLD_VERSION_ID")

echo "Response: $NEW_RESPONSE"
NEW_VERSION_ID=$(echo "$NEW_RESPONSE" | grep -o '"drawing_version_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$NEW_VERSION_ID" ]; then
  echo "ERROR: Failed to get new_version_id from response"
  echo "Full response: $NEW_RESPONSE"
  exit 1
fi

echo "✓ New version ID: $NEW_VERSION_ID"
echo ""

# Step 3: Create comparison job
echo "Step 3: Creating comparison job..."
JOB_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d "{
    \"old_drawing_version_id\": \"$OLD_VERSION_ID\",
    \"new_drawing_version_id\": \"$NEW_VERSION_ID\",
    \"project_id\": \"$PROJECT_ID\",
    \"user_id\": \"$USER_ID\"
  }")

echo "Response: $JOB_RESPONSE"
JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
  echo "ERROR: Failed to get job_id from response"
  echo "Full response: $JOB_RESPONSE"
  exit 1
fi

echo "✓ Job ID: $JOB_ID"
echo ""

# Step 4: Monitor job status
echo "Step 4: Monitoring job status..."
echo "Job ID: $JOB_ID"
echo "Check status with: curl $BACKEND_URL/api/v1/jobs/$JOB_ID"
echo ""
echo "Monitoring worker pods for 60 seconds..."
kubectl logs -n prod-app -l app=ocr-worker --tail=20 -f &
OCR_PID=$!
kubectl logs -n prod-app -l app=diff-worker --tail=20 -f &
DIFF_PID=$!
kubectl logs -n prod-app -l app=summary-worker --tail=20 -f &
SUMMARY_PID=$!

sleep 60

kill $OCR_PID $DIFF_PID $SUMMARY_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo "Job ID: $JOB_ID"
echo "Check status: curl $BACKEND_URL/api/v1/jobs/$JOB_ID"

