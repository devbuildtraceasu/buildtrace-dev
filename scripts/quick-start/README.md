# Quick-Start Automation Scripts

This directory contains automation scripts to quickly set up GCP resources using gcloud CLI commands. These scripts complement the manual console setup and can be run after initial infrastructure is created.

## Prerequisites

1. **gcloud CLI installed and authenticated:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. **Set environment variables:**
   ```bash
   export PROJECT_ID="your-project-id"
   export REGION="us-west2"
   export ZONE="us-west2-a"
   ```

3. **Set project:**
   ```bash
   gcloud config set project $PROJECT_ID
   ```

## Scripts Overview

### 1. `enable-apis.sh`
Enables all required GCP APIs for BuildTrace system.

### 2. `create-storage.sh`
Creates Cloud Storage buckets with proper folder structure and lifecycle policies.

### 3. `create-pubsub.sh`
Creates Pub/Sub topics and subscriptions for job queues.

### 4. `create-service-accounts.sh`
Creates service accounts and grants required IAM roles.

### 5. `create-artifact-registry.sh`
Creates Artifact Registry repositories for Docker images.

### 6. `create-secrets.sh`
Sets up Secret Manager with placeholder secrets (update with real values).

### 7. `setup-all.sh`
Master script that runs all setup scripts in correct order.

## Usage

### Run Individual Scripts

```bash
# Enable APIs
./scripts/quick-start/enable-apis.sh

# Create storage buckets
./scripts/quick-start/create-storage.sh

# Create Pub/Sub
./scripts/quick-start/create-pubsub.sh
```

### Run All Scripts

```bash
# Make scripts executable
chmod +x scripts/quick-start/*.sh

# Run master script
./scripts/quick-start/setup-all.sh
```

## Customization

Before running scripts, update the variables at the top of each script:

```bash
PROJECT_ID="your-project-id"
REGION="us-west2"
ZONE="us-west2-a"
```

## Notes

- Scripts are idempotent - safe to run multiple times
- Some operations may take a few minutes (API enablement, Cloud SQL creation)
- Review each script before running to ensure it matches your requirements
- Scripts use `--quiet` flag to avoid interactive prompts

## Troubleshooting

If a script fails:
1. Check error message for specific issue
2. Verify PROJECT_ID and REGION are set correctly
3. Ensure you have required permissions (Owner or Editor + Security Admin)
4. Some APIs may take 1-2 minutes to fully enable - wait and retry

