#!/bin/bash
# Create Artifact Registry repositories for Docker images

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

echo "=========================================="
echo "Creating Artifact Registry Repositories"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="

# Set project
gcloud config set project $PROJECT_ID

# Create main repository
echo "Creating main Docker repository..."
gcloud artifacts repositories create buildtrace-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for BuildTrace" \
  || echo "Repository may already exist"

# Create base images repository (optional)
echo "Creating base images repository..."
gcloud artifacts repositories create buildtrace-base-images \
  --repository-format=docker \
  --location=$REGION \
  --description="Base images for BuildTrace" \
  || echo "Repository may already exist"

# Configure Docker authentication
echo ""
echo "Configuring Docker authentication..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

# Grant Cloud Build service account access
echo ""
echo "Granting Cloud Build permissions..."

CLOUDBUILD_SA="buildtrace-cloudbuild@$PROJECT_ID.iam.gserviceaccount.com"
DEFAULT_CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

gcloud artifacts repositories add-iam-policy-binding buildtrace-repo \
  --location=$REGION \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/artifactregistry.writer" \
  || true

gcloud artifacts repositories add-iam-policy-binding buildtrace-repo \
  --location=$REGION \
  --member="serviceAccount:$DEFAULT_CB_SA" \
  --role="roles/artifactregistry.writer" \
  || true

echo ""
echo "✅ Artifact Registry repositories created!"
echo ""
echo "Repositories:"
echo "  - $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo"
echo "  - $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-base-images"
echo ""
echo "Docker authentication configured."
echo "You can now push images using:"
echo "  docker push $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/image-name:tag"

