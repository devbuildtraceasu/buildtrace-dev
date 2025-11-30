#!/bin/bash
# Script to create Gemini API key secret in Google Cloud Secret Manager

set -e

PROJECT_ID="${GCP_PROJECT_ID:-buildtrace-dev}"
SECRET_NAME="gemini-api-key"
SERVICE_ACCOUNT="buildtrace-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

echo "================================================================================"
echo "Creating Gemini API Key Secret"
echo "================================================================================"
echo ""
echo "Project: ${PROJECT_ID}"
echo "Secret Name: ${SECRET_NAME}"
echo ""

# Check if secret already exists
if gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} &>/dev/null; then
    echo "⚠ Secret '${SECRET_NAME}' already exists."
    read -p "Do you want to add a new version? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 0
    fi
    ADD_VERSION=true
else
    echo "Creating new secret '${SECRET_NAME}'..."
    ADD_VERSION=false
fi

# Get API key from user
if [ -z "$GEMINI_API_KEY" ]; then
    echo ""
    echo "Enter your Gemini API key:"
    read -s GEMINI_API_KEY
    echo ""
    
    if [ -z "$GEMINI_API_KEY" ]; then
        echo "❌ Error: API key cannot be empty"
        exit 1
    fi
else
    echo "Using GEMINI_API_KEY from environment..."
fi

# Create secret or add version
if [ "$ADD_VERSION" = true ]; then
    echo "Adding new version to existing secret..."
    echo -n "$GEMINI_API_KEY" | gcloud secrets versions add ${SECRET_NAME} \
        --data-file=- \
        --project=${PROJECT_ID}
else
    echo "Creating secret..."
    echo -n "$GEMINI_API_KEY" | gcloud secrets create ${SECRET_NAME} \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
fi

if [ $? -ne 0 ]; then
    echo "❌ Failed to create/update secret"
    exit 1
fi

echo "✓ Secret created/updated successfully"
echo ""

# Grant service account access to the secret
echo "Granting service account access to secret..."
gcloud secrets add-iam-policy-binding ${SECRET_NAME} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo "⚠ Warning: Failed to grant service account access. You may need to do this manually."
    echo "Run: gcloud secrets add-iam-policy-binding ${SECRET_NAME} \\"
    echo "  --member=\"serviceAccount:${SERVICE_ACCOUNT}\" \\"
    echo "  --role=\"roles/secretmanager.secretAccessor\" \\"
    echo "  --project=${PROJECT_ID}"
else
    echo "✓ Service account access granted"
fi

echo ""
echo "================================================================================"
echo "Secret Setup Complete"
echo "================================================================================"
echo ""
echo "Secret name: ${SECRET_NAME}"
echo "Project: ${PROJECT_ID}"
echo ""
echo "You can now deploy with: ./DEPLOY_AND_TEST.sh"
echo ""

