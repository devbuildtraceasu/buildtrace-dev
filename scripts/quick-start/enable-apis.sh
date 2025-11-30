#!/bin/bash
# Enable all required GCP APIs for BuildTrace system

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"

echo "=========================================="
echo "Enabling GCP APIs for BuildTrace"
echo "Project: $PROJECT_ID"
echo "=========================================="

# Set project
gcloud config set project $PROJECT_ID

# Core Services
echo "Enabling core services..."
gcloud services enable \
  run.googleapis.com \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --quiet

# Messaging & Queuing
echo "Enabling messaging services..."
gcloud services enable \
  pubsub.googleapis.com \
  cloudtasks.googleapis.com \
  --quiet

# Storage & Database
echo "Enabling storage and database services..."
gcloud services enable \
  storage-component.googleapis.com \
  sqladmin.googleapis.com \
  bigquery.googleapis.com \
  --quiet

# Monitoring & Logging
echo "Enabling monitoring and logging..."
gcloud services enable \
  logging.googleapis.com \
  monitoring.googleapis.com \
  clouderrorreporting.googleapis.com \
  --quiet

# Networking
echo "Enabling networking services..."
gcloud services enable \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --quiet

# Security
echo "Enabling security services..."
gcloud services enable \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  --quiet

echo ""
echo "=========================================="
echo "Verifying enabled APIs..."
echo "=========================================="

# Verify APIs are enabled
gcloud services list --enabled --filter="name:run.googleapis.com OR name:pubsub.googleapis.com OR name:sqladmin.googleapis.com" --format="table(name,state)"

echo ""
echo "✅ API enablement complete!"
echo ""
echo "Note: Some APIs may take 1-2 minutes to fully activate."
echo "If you encounter errors, wait a moment and retry."

