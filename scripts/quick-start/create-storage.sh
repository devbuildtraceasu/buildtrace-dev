#!/bin/bash
# Create Cloud Storage buckets with folder structure and lifecycle policies

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"

echo "=========================================="
echo "Creating Cloud Storage Buckets"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="

# Set project
gcloud config set project $PROJECT_ID

# Create input bucket
echo "Creating input bucket..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-dev-input-$PROJECT_ID || echo "Bucket may already exist"

# Create processed bucket
echo "Creating processed bucket..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-dev-processed-$PROJECT_ID || echo "Bucket may already exist"

# Create artifacts bucket
echo "Creating artifacts bucket..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-dev-artifacts-$PROJECT_ID || echo "Bucket may already exist"

# Create logs bucket (optional)
echo "Creating logs bucket..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-dev-logs-$PROJECT_ID || echo "Bucket may already exist"

# Create folder structure
echo ""
echo "Creating folder structure..."

# Input bucket folders
echo "  Input bucket folders..."
gsutil -m mkdir gs://buildtrace-dev-input-$PROJECT_ID/raw/ || true
gsutil -m mkdir gs://buildtrace-dev-input-$PROJECT_ID/uploaded/ || true
gsutil -m mkdir gs://buildtrace-dev-input-$PROJECT_ID/failed/ || true

# Processed bucket folders
echo "  Processed bucket folders..."
gsutil -m mkdir gs://buildtrace-dev-processed-$PROJECT_ID/ocr/ || true
gsutil -m mkdir gs://buildtrace-dev-processed-$PROJECT_ID/diffs/ || true
gsutil -m mkdir gs://buildtrace-dev-processed-$PROJECT_ID/rasterized/ || true

# Artifacts bucket folders
echo "  Artifacts bucket folders..."
gsutil -m mkdir gs://buildtrace-dev-artifacts-$PROJECT_ID/overlays/ || true
gsutil -m mkdir gs://buildtrace-dev-artifacts-$PROJECT_ID/overlays/machine/ || true
gsutil -m mkdir gs://buildtrace-dev-artifacts-$PROJECT_ID/overlays/manual/ || true
gsutil -m mkdir gs://buildtrace-dev-artifacts-$PROJECT_ID/summaries/ || true
gsutil -m mkdir gs://buildtrace-dev-artifacts-$PROJECT_ID/exports/ || true

# Remove public access
echo ""
echo "Removing public access..."
gsutil iam ch -d allUsers:objectViewer gs://buildtrace-dev-input-$PROJECT_ID || true
gsutil iam ch -d allUsers:objectViewer gs://buildtrace-dev-processed-$PROJECT_ID || true
gsutil iam ch -d allUsers:objectViewer gs://buildtrace-dev-artifacts-$PROJECT_ID || true

# Create lifecycle policy for input bucket
echo ""
echo "Creating lifecycle policies..."
cat > /tmp/lifecycle-input.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365}
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle-input.json gs://buildtrace-dev-input-$PROJECT_ID || true

# Create lifecycle policy for processed bucket (keep longer)
cat > /tmp/lifecycle-processed.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 60}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 180}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 730}
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle-processed.json gs://buildtrace-dev-processed-$PROJECT_ID || true

# Cleanup temp files
rm -f /tmp/lifecycle-input.json /tmp/lifecycle-processed.json

echo ""
echo "✅ Storage buckets created successfully!"
echo ""
echo "Buckets created:"
echo "  - gs://buildtrace-dev-input-$PROJECT_ID"
echo "  - gs://buildtrace-dev-processed-$PROJECT_ID"
echo "  - gs://buildtrace-dev-artifacts-$PROJECT_ID"
echo "  - gs://buildtrace-dev-logs-$PROJECT_ID"

