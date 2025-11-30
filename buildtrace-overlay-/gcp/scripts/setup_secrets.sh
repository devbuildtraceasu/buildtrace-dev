#!/bin/bash

# Setup secrets in Google Cloud Secret Manager

PROJECT_ID="buildtrace"

echo "Setting up secrets in Secret Manager..."
echo "======================================="

# Get database password from .env
DB_PASS=$(grep "^DB_PASS=" .env | cut -d'=' -f2)

if [ -z "$DB_PASS" ]; then
    echo "❌ DB_PASS not found in .env file"
    exit 1
fi

# Create database password secret
echo "Creating database password secret..."
echo -n "$DB_PASS" | gcloud secrets create db-password --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$DB_PASS" | gcloud secrets versions add db-password --data-file=- --project=$PROJECT_ID

# Check if OpenAI API key is set
OPENAI_KEY=$(grep "^OPENAI_API_KEY=" .env | cut -d'=' -f2)

if [ "$OPENAI_KEY" != "your_openai_api_key_here" ] && [ ! -z "$OPENAI_KEY" ]; then
    echo "Creating OpenAI API key secret..."
    echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=- --project=$PROJECT_ID 2>/dev/null || \
    echo -n "$OPENAI_KEY" | gcloud secrets versions add openai-api-key --data-file=- --project=$PROJECT_ID
    echo "✅ OpenAI API key secret updated"
else
    echo "⚠️  OpenAI API key not set in .env - you'll need to update it manually:"
    echo "   gcloud secrets create openai-api-key --project=$PROJECT_ID"
    echo "   echo 'your_actual_openai_key' | gcloud secrets versions add openai-api-key --data-file=-"
fi

# Grant Cloud Run access to secrets
echo "Granting Cloud Run access to secrets..."

# Get the default Compute Engine service account
SERVICE_ACCOUNT="$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID 2>/dev/null

echo ""
echo "✅ Secrets setup complete!"
echo ""
echo "📋 Summary:"
echo "  - db-password: ✅ Created/Updated"
echo "  - openai-api-key: $([ "$OPENAI_KEY" != "your_openai_api_key_here" ] && echo "✅ Created/Updated" || echo "⚠️ Needs manual setup")"
echo "  - IAM permissions: ✅ Granted to Cloud Run"
echo ""
echo "🚀 Ready for deployment!"