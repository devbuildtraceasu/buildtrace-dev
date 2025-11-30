#!/bin/bash
# Create service accounts and grant required IAM roles

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

echo "=========================================="
echo "Creating Service Accounts"
echo "Project: $PROJECT_ID"
echo "=========================================="

# Set project
gcloud config set project $PROJECT_ID

# Service account emails
SERVICE_ACCOUNT_EMAIL="buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com"
CLOUDBUILD_SA="buildtrace-cloudbuild@$PROJECT_ID.iam.gserviceaccount.com"
GKE_WORKLOAD_SA="buildtrace-gke-workload@$PROJECT_ID.iam.gserviceaccount.com"

# Create service accounts
echo "Creating service accounts..."
gcloud iam service-accounts create buildtrace-service-account \
  --display-name="BuildTrace Service Account" \
  --description="Service account for BuildTrace application services" \
  || echo "Service account may already exist"

gcloud iam service-accounts create buildtrace-cloudbuild \
  --display-name="BuildTrace Cloud Build" \
  --description="Service account for Cloud Build CI/CD" \
  || echo "Service account may already exist"

gcloud iam service-accounts create buildtrace-gke-workload \
  --display-name="BuildTrace GKE Workload" \
  --description="Service account for GKE workloads" \
  || echo "Service account may already exist"

echo ""
echo "Granting IAM roles to application service account..."

# Application service account roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.invoker" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/pubsub.subscriber" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/pubsub.publisher" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/logging.logWriter" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/monitoring.metricWriter" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None \
  || true

echo ""
echo "Granting IAM roles to Cloud Build service account..."

# Cloud Build service account roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/cloudbuild.builds.editor" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/artifactregistry.writer" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/run.admin" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/container.developer" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/iam.serviceAccountUser" \
  --condition=None \
  || true

echo ""
echo "Granting IAM roles to GKE workload service account..."

# GKE workload service account roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/storage.objectAdmin" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/pubsub.subscriber" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/pubsub.publisher" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/cloudsql.client" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/logging.logWriter" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/monitoring.metricWriter" \
  --condition=None \
  || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None \
  || true

echo ""
echo "✅ Service accounts created and roles granted!"
echo ""
echo "Service accounts:"
echo "  - $SERVICE_ACCOUNT_EMAIL"
echo "  - $CLOUDBUILD_SA"
echo "  - $GKE_WORKLOAD_SA"
echo ""
echo "Note: Generate service account keys for local development if needed:"
echo "  gcloud iam service-accounts keys create buildtrace-key.json \\"
echo "    --iam-account=$SERVICE_ACCOUNT_EMAIL"

