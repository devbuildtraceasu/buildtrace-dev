# Quick Deployment Reference

## TL;DR - Deploy Everything Now

```bash
cd buildtrace-dev
./deploy-all.sh
```

## Common Commands

### Deploy Both Backend and Frontend
```bash
./deploy-all.sh
```
or
```bash
./DEPLOY_AND_TEST.sh
```

### Deploy Only Frontend
```bash
./deploy-frontend.sh
```

### Deploy Only Backend
```bash
DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh
```

## After Deployment

Your services will be available at:

- **Frontend:** https://buildtrace-frontend-136394139608.us-west2.run.app
- **Backend:** https://buildtrace-backend-136394139608.us-west2.run.app

## Check Status

```bash
# List all services
gcloud run services list

# Check logs
gcloud run logs read buildtrace-backend --region=us-west2 --limit=20
gcloud run logs read buildtrace-frontend --region=us-west2 --limit=20
```

## Environment Variables

### To Deploy to Different Project
```bash
export GCP_PROJECT_ID=your-project-id
./deploy-all.sh
```

### To Deploy to Different Region
```bash
export GCP_REGION=us-central1
./deploy-all.sh
```

## Troubleshooting

### Frontend not updating?
```bash
./deploy-frontend.sh
```

### Backend not updating?
```bash
DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh
```

### Both not working?
```bash
# Check you're in the right directory
pwd  # Should end with /buildtrace-dev

# Check Docker is running
docker ps

# Re-authenticate
gcloud auth login

# Try again
./deploy-all.sh
```

## Full Documentation

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete documentation.
