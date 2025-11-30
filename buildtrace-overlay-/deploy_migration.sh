#!/bin/bash

# Deploy migration as a one-time Cloud Run job
echo "🚀 Deploying database migration as Cloud Run job..."

# Build and submit the migration job
gcloud builds submit --tag gcr.io/buildtrace/migration-job \
  --project=buildtrace \
  --timeout=600s \
  --config - <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/buildtrace/migration-job', '-f', '-', '.']
  stdin: |
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY run_migration.py .
    COPY config.py .
    COPY gcp/ ./gcp/
    CMD ["python", "run_migration.py"]
EOF

# Run the migration job
echo "🔧 Running migration job..."
gcloud run jobs create migration-job \
  --image gcr.io/buildtrace/migration-job \
  --region us-central1 \
  --project buildtrace \
  --set-env-vars="ENVIRONMENT=production,INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres,DB_USER=buildtrace_user,DB_NAME=buildtrace_db,DB_PASS=BuildTrace2024SecurePassword" \
  --set-cloudsql-instances buildtrace:us-central1:buildtrace-postgres \
  --cpu 1 \
  --memory 512Mi \
  --max-retries 1 \
  --parallelism 1

# Execute the job
gcloud run jobs execute migration-job \
  --region us-central1 \
  --project buildtrace

echo "✅ Migration job completed!"