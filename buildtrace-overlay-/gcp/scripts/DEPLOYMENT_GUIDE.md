# Branch-Based Cloud Run Deployment Guide

## Overview

This deployment system allows each Git branch to have its own Cloud Run service with a unique URL. This enables independent testing of features without affecting other branches or production.

## Quick Start

### Deploy Current Branch
```bash
./gcp/scripts/deploy-branch.sh
```

This will:
1. Detect your current Git branch
2. Build a Docker image
3. Push to Artifact Registry
4. Deploy to a branch-specific Cloud Run service
5. Display the unique URL for your branch

### Service Naming Convention

- **main branch** → `buildtrace-overlay` (production)
- **feature/largesize** → `buildtrace-overlay-feature-largesize`
- **feature/deploy** → `buildtrace-overlay-feature-deploy`
- **bugfix/auth** → `buildtrace-overlay-bugfix-auth`

### URLs

Each branch gets its own URL:
- Production: `https://buildtrace-overlay-123644909590.us-central1.run.app`
- Feature branches: `https://buildtrace-overlay-{branch-name}-123644909590.us-central1.run.app`

## Management

### List All Deployments
```bash
./gcp/scripts/manage-branches.sh
# Then select option 1
```

### Delete a Branch Deployment
```bash
./gcp/scripts/manage-branches.sh
# Then select option 2 and follow prompts
```

### Direct Deletion (CLI)
```bash
# Delete a specific branch deployment
gcloud run services delete buildtrace-overlay-feature-test \
  --region=us-central1 \
  --project=buildtrace

# List all services
gcloud run services list \
  --region=us-central1 \
  --project=buildtrace \
  --filter="metadata.name:buildtrace-overlay*"
```

## Deployment Process

### 1. Before Deploying
- Ensure you have `.env` file with required variables (especially `OPENAI_API_KEY`)
- Commit your changes (deployment script shows branch name)
- Have Docker running locally
- Be authenticated with gcloud: `gcloud auth login`

### 2. Deploy Your Branch
```bash
# From project root
./gcp/scripts/deploy-branch.sh
```

### 3. Test Your Deployment
- Visit the URL shown in deployment output
- Test your specific features
- Monitor logs: `gcloud run logs read --service=buildtrace-overlay-{your-branch}`

### 4. Cleanup When Done
```bash
# Option 1: Use management script
./gcp/scripts/manage-branches.sh

# Option 2: Direct command
gcloud run services delete buildtrace-overlay-{your-branch} \
  --region=us-central1 \
  --project=buildtrace
```

## Environment Variables

All deployments share the same environment variables:
- Database credentials (same Cloud SQL instance)
- GCS bucket configuration
- OpenAI API settings

Branch-specific variable added:
- `BRANCH`: Contains the Git branch name for debugging

## Cost Optimization

- Each service has `--max-instances=10` to prevent runaway costs
- Branch deployments should be deleted when no longer needed
- All services share the same Cloud SQL instance
- Consider setting up automatic cleanup for old branch deployments

## Troubleshooting

### Authentication Issues
```bash
gcloud auth login
gcloud config set project buildtrace
```

### View Logs
```bash
# For specific service
gcloud run logs read --service=buildtrace-overlay-feature-largesize \
  --region=us-central1 \
  --project=buildtrace

# Tail logs
gcloud run logs tail --service=buildtrace-overlay-feature-largesize \
  --region=us-central1 \
  --project=buildtrace
```

### Service Not Starting
Check:
1. Docker image built successfully
2. Environment variables in `.env` file
3. Cloud SQL instance is running
4. Service account permissions

## Best Practices

1. **Branch Naming**: Use descriptive branch names that work well in URLs
   - Good: `feature/upload-improvements`
   - Avoid: `feature/JIRA-1234!!!test`

2. **Testing**: Always test on your branch deployment before merging to main

3. **Cleanup**: Delete branch deployments when PR is merged or feature is abandoned

4. **Monitoring**: Use Cloud Console to monitor service health and logs

5. **Database**: Be careful with database migrations on branch deployments
   - Consider using separate schemas or test data
   - Never run destructive migrations on shared database

## Example Workflow

```bash
# 1. Create and checkout new feature branch
git checkout -b feature/new-upload-ui

# 2. Make your changes
# ... code changes ...

# 3. Deploy to test
./gcp/scripts/deploy-branch.sh

# 4. Test at the provided URL
# https://buildtrace-overlay-feature-new-upload-ui-123644909590.us-central1.run.app

# 5. Iterate and redeploy as needed
# ... more changes ...
./gcp/scripts/deploy-branch.sh

# 6. After PR is merged, cleanup
gcloud run services delete buildtrace-overlay-feature-new-upload-ui \
  --region=us-central1 --project=buildtrace --quiet
```

## Notes

- Production (`main` branch) always deploys to `buildtrace-overlay`
- Branch deployments are independent and don't affect each other
- All services share the same Cloud SQL database (be careful with schema changes)
- Image tags include timestamp for uniqueness
- Services are publicly accessible (--allow-unauthenticated)