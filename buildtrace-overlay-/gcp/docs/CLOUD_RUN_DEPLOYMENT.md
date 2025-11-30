# Google Cloud Run Deployment Guide

This guide will help you deploy the BuildTrace Overlay application to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: Create one at [console.cloud.google.com](https://console.cloud.google.com)
2. **Google Cloud CLI**: Install from [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
3. **A Google Cloud Project**: Create a new project or use an existing one
4. **Billing Enabled**: Cloud Run requires billing to be enabled on your project

## Quick Deployment

### Option 1: Using the Deployment Script (Recommended)

```bash
# Run the automated deployment script
./deploy-to-cloud-run.sh
```

The script will:
- Enable required Google Cloud APIs
- Set up secrets management for your API keys
- Deploy your application to Cloud Run
- Provide you with the service URL

### Option 2: Manual Deployment

#### Step 1: Set up your Google Cloud project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com
```

#### Step 2: Store your OpenAI API key securely

```bash
# Create a secret for your OpenAI API key
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key \
  --data-file=- \
  --project=$PROJECT_ID

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Step 3: Deploy to Cloud Run

```bash
# Deploy using source code (Cloud Run will build the container)
gcloud run deploy buildtrace-overlay \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars="FLASK_ENV=production" \
  --update-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

## Using Cloud Build for CI/CD

If you want to set up continuous deployment:

1. **Connect your GitHub repository** to Cloud Build:
   ```bash
   gcloud builds triggers create github \
     --repo-name=your-repo-name \
     --repo-owner=your-github-username \
     --branch-pattern="^main$" \
     --build-config=cloudbuild.yaml
   ```

2. **Push to main branch** to trigger automatic deployment

## Configuration Options

### Resource Allocation

The default configuration uses:
- **Memory**: 2GB (suitable for image processing)
- **CPU**: 2 vCPUs
- **Timeout**: 300 seconds (5 minutes)
- **Max Instances**: 10 (auto-scales based on traffic)
- **Min Instances**: 0 (scales to zero when not in use)

Adjust these in `cloudbuild.yaml` or deployment commands as needed.

### Environment Variables

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key (stored in Secret Manager)
- `FLASK_ENV`: Set to 'production' for Cloud Run
- `PORT`: Automatically set by Cloud Run (default 8080)

## File Storage Considerations

**Important**: Cloud Run instances are stateless. Uploaded files and results are stored temporarily and will be lost when the instance scales down.

### Solutions for Persistent Storage:

1. **Google Cloud Storage** (Recommended):
   - Modify the application to use GCS for file uploads/results
   - Create a bucket: `gsutil mb gs://your-bucket-name`
   - Update application code to use GCS client library

2. **Firestore/Cloud SQL**:
   - For metadata and structured data
   - Store file references and analysis results

## Monitoring and Logs

View application logs:
```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=buildtrace-overlay" \
  --limit 50 --format json
```

View metrics in Cloud Console:
- Navigate to Cloud Run → Services → buildtrace-overlay → Metrics

## Cost Optimization

- **Scale to Zero**: The service automatically scales to 0 instances when not in use
- **Request-based Pricing**: You only pay for actual usage
- **Estimated Costs**:
  - Light usage (< 1000 requests/month): ~$5-10/month
  - Moderate usage (10,000 requests/month): ~$20-50/month

## Troubleshooting

### Common Issues:

1. **502 Bad Gateway**:
   - Check logs for application errors
   - Increase memory allocation if needed

2. **Timeout errors**:
   - Increase timeout value (max 3600 seconds)
   - Optimize long-running operations

3. **Permission errors**:
   - Ensure APIs are enabled
   - Check IAM permissions for service accounts

4. **Missing dependencies**:
   - Review Dockerfile for all required system packages
   - Check requirements.txt for Python packages

## Security Best Practices

1. **Authentication**:
   - Remove `--allow-unauthenticated` for private deployments
   - Use Identity-Aware Proxy for user authentication

2. **Secrets Management**:
   - Never commit API keys to code
   - Always use Secret Manager for sensitive data

3. **Network Security**:
   - Consider using VPC connector for private resources
   - Implement rate limiting for public endpoints

## Support

For issues specific to the deployment:
1. Check Cloud Run logs
2. Review error messages in Cloud Console
3. Verify all environment variables are set correctly

For application issues:
- Check the application logs
- Ensure all dependencies are properly installed
- Verify API keys are valid and have sufficient quota