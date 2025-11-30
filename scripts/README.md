# BuildTrace Scripts Directory

This directory contains all automation and setup scripts for the BuildTrace system.

## Directory Structure

```
scripts/
├── quick-start/          # GCP infrastructure automation scripts
├── verification/         # Post-setup verification scripts
├── dev-setup/           # Local development environment setup
└── migrations/          # Database migration scripts
```

## Quick Start

### 1. Infrastructure Setup (After Console Setup)

```bash
# Run all quick-start scripts
./scripts/quick-start/setup-all.sh

# Or run individually
./scripts/quick-start/enable-apis.sh
./scripts/quick-start/create-storage.sh
./scripts/quick-start/create-pubsub.sh
./scripts/quick-start/create-service-accounts.sh
./scripts/quick-start/create-artifact-registry.sh
./scripts/quick-start/create-secrets.sh
```

### 2. Verify Setup

```bash
# Run comprehensive verification
./scripts/verification/verify-setup.sh
```

### 3. Set Up Local Development

```bash
# Set up local environment
./scripts/dev-setup/setup-local.sh

# Start Cloud SQL Proxy (in separate terminal)
./scripts/dev-setup/local-db-setup.sh
```

### 4. Run Database Migrations

```bash
# Run all migrations
python scripts/migrations/run_migration.py

# Run specific migration
python scripts/migrations/run_migration.py --migration 001

# Dry run (validate without executing)
python scripts/migrations/run_migration.py --dry-run
```

## Prerequisites

Before running scripts:

1. **Install gcloud CLI:**
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Set environment variables:**
   ```bash
   export PROJECT_ID="your-project-id"
   export REGION="us-west2"
   ```

## Script Categories

### Quick-Start Scripts
Automate GCP resource creation using gcloud CLI. Use these after initial console setup to:
- Enable APIs
- Create storage buckets
- Set up Pub/Sub
- Configure service accounts
- Create Artifact Registry
- Set up Secret Manager

### Verification Scripts
Check that all infrastructure is correctly configured:
- Verify APIs are enabled
- Check storage buckets exist
- Validate Pub/Sub topics/subscriptions
- Verify service accounts and permissions
- Check secrets are accessible

### Development Setup Scripts
Set up local development environment:
- Create `.env.local` file
- Download service account keys
- Configure Cloud SQL Proxy
- Set up local authentication

### Migration Scripts
Database schema migrations for transitioning to job-based architecture:
- Create new tables (jobs, job_stages, etc.)
- Enhance existing tables
- Migrate existing data
- Create indexes and constraints

## Notes

- All scripts are idempotent (safe to run multiple times)
- Scripts use `--quiet` flags to avoid interactive prompts
- Review each script before running to ensure it matches your setup
- Some operations may take a few minutes (API enablement, Cloud SQL creation)

## Troubleshooting

If scripts fail:
1. Check error messages for specific issues
2. Verify PROJECT_ID and REGION are set correctly
3. Ensure you have required permissions (Owner or Editor + Security Admin)
4. Some APIs may take 1-2 minutes to fully enable - wait and retry
5. Check that prerequisites are installed (gcloud, psql, etc.)

## Next Steps

After running all scripts:
1. ✅ Infrastructure is set up
2. ✅ Local development environment is configured
3. ✅ Database is migrated to new schema
4. 🚀 Ready to start development!

