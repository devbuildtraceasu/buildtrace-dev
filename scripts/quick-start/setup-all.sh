#!/bin/bash
# Master script to run all quick-start setup scripts

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"

echo "=========================================="
echo "BuildTrace Quick-Start Setup"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: PROJECT_ID not set. Please set it:"
    echo "  export PROJECT_ID='your-project-id'"
    exit 1
fi

# Confirm
echo "This will set up:"
echo "  ✓ GCP APIs"
echo "  ✓ Cloud Storage buckets"
echo "  ✓ Pub/Sub topics and subscriptions"
echo "  ✓ Service accounts and IAM roles"
echo "  ✓ Artifact Registry repositories"
echo "  ✓ Secret Manager secrets"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Make scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

# Run scripts in order
echo ""
echo "=========================================="
echo "Step 1/6: Enabling APIs..."
echo "=========================================="
"$SCRIPT_DIR/enable-apis.sh"

echo ""
echo "=========================================="
echo "Step 2/6: Creating Storage Buckets..."
echo "=========================================="
"$SCRIPT_DIR/create-storage.sh"

echo ""
echo "=========================================="
echo "Step 3/6: Creating Pub/Sub Topics..."
echo "=========================================="
"$SCRIPT_DIR/create-pubsub.sh"

echo ""
echo "=========================================="
echo "Step 4/6: Creating Service Accounts..."
echo "=========================================="
"$SCRIPT_DIR/create-service-accounts.sh"

echo ""
echo "=========================================="
echo "Step 5/6: Creating Artifact Registry..."
echo "=========================================="
"$SCRIPT_DIR/create-artifact-registry.sh"

echo ""
echo "=========================================="
echo "Step 6/6: Creating Secrets..."
echo "=========================================="
"$SCRIPT_DIR/create-secrets.sh"

echo ""
echo "=========================================="
echo "✅ Quick-Start Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Create Cloud SQL instance (via console or gcloud)"
echo "  2. Update secrets with real values (especially openai-api-key)"
echo "  3. Run verification script: ./scripts/verification/verify-setup.sh"
echo "  4. Set up local development: ./scripts/dev-setup/setup-local.sh"
echo ""

