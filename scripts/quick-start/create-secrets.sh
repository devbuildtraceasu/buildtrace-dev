#!/bin/bash
# Create secrets in Secret Manager (with placeholder values)

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"

echo "=========================================="
echo "Creating Secrets in Secret Manager"
echo "Project: $PROJECT_ID"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This script creates secrets with placeholder values."
echo "You MUST update them with real values after creation!"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Generate secure random passwords
DB_ROOT_PASSWORD=$(openssl rand -base64 32)
DB_USER_PASSWORD=$(openssl rand -base64 32)
JWT_SIGNING_KEY=$(openssl rand -base64 32)

echo "Creating secrets..."

# Database passwords (will be updated after Cloud SQL creation)
echo -n "$DB_ROOT_PASSWORD" | gcloud secrets create db-root-password \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret may already exist - update manually"

echo -n "$DB_USER_PASSWORD" | gcloud secrets create db-user-password \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret may already exist - update manually"

# OpenAI API key (placeholder)
echo -n "PLACEHOLDER_UPDATE_WITH_REAL_KEY" | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret may already exist - update manually"

# Auth provider secret (placeholder)
echo -n "PLACEHOLDER_UPDATE_WITH_REAL_SECRET" | gcloud secrets create auth-provider-secret \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret may already exist - update manually"

# JWT signing key
echo -n "$JWT_SIGNING_KEY" | gcloud secrets create jwt-signing-key \
  --data-file=- \
  --replication-policy="automatic" \
  || echo "Secret may already exist - update manually"

# Grant service account access
echo ""
echo "Granting service account access to secrets..."

SERVICE_ACCOUNT_EMAIL="buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com"
GKE_WORKLOAD_SA="buildtrace-gke-workload@$PROJECT_ID.iam.gserviceaccount.com"

for secret in db-user-password openai-api-key auth-provider-secret jwt-signing-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    || true

  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$GKE_WORKLOAD_SA" \
    --role="roles/secretmanager.secretAccessor" \
    || true
done

echo ""
echo "✅ Secrets created!"
echo ""
echo "⚠️  IMPORTANT: Update these secrets with real values:"
echo "  - openai-api-key: Set your OpenAI API key"
echo "  - auth-provider-secret: Set your auth provider secret"
echo ""
echo "To update a secret:"
echo "  echo -n 'YOUR_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo ""
echo "Generated passwords saved to secrets:"
echo "  - db-root-password: Generated (update after Cloud SQL creation)"
echo "  - db-user-password: Generated (update after Cloud SQL creation)"
echo "  - jwt-signing-key: Generated"

