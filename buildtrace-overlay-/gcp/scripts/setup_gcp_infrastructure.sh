#!/bin/bash

# Configuration
PROJECT_ID="buildtrace"
REGION="us-central1"
INSTANCE_NAME="buildtrace-postgres"
DB_NAME="buildtrace_db"
DB_USER="buildtrace_user"
BUCKET_NAME="buildtrace-storage"

echo "Setting up GCP infrastructure for BuildTrace..."

# 0. Enable necessary APIs first
echo "Enabling necessary APIs..."
gcloud services enable sqladmin.googleapis.com --project=$PROJECT_ID
gcloud services enable storage-api.googleapis.com --project=$PROJECT_ID
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
gcloud services enable run.googleapis.com --project=$PROJECT_ID

echo "Waiting for APIs to be enabled..."
sleep 10

# 1. Create Cloud SQL PostgreSQL instance
echo "Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --network=default \
    --no-assign-ip \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --storage-auto-increase-limit=50 \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=03 \
    --maintenance-window-duration=4 \
    --project=$PROJECT_ID

# 2. Create database
echo "Creating database..."
gcloud sql databases create $DB_NAME \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID

# 3. Create database user
echo "Creating database user..."
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID

# 4. Create Cloud Storage bucket
echo "Creating Cloud Storage bucket..."
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/

# 5. Set bucket permissions for Cloud Run service account
echo "Setting bucket permissions..."
SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter="displayName:Default compute service account" --format="value(email)")
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT:objectAdmin gs://$BUCKET_NAME

# 6. Enable necessary APIs
echo "Enabling necessary APIs..."
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable secretmanager.googleapis.com

echo "Infrastructure setup complete!"
echo "Please save the database password when prompted and add it to Secret Manager."