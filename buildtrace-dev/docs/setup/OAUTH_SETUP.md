# Google OAuth Configuration Setup

## Current Status

✅ OAuth secrets created in GCP Secret Manager
✅ Backend deployed with OAuth environment variables
⚠️ Need to update Google Cloud OAuth redirect URIs

## What Was Done

1. **Created Secrets:**
   - `google-client-id` - Your Google OAuth Client ID
   - `google-client-secret` - Your Google OAuth Client Secret

2. **Updated Deployment:**
   - Added OAuth environment variables to backend deployment
   - Configured redirect URI: `https://buildtrace-backend-136394139608.us-west2.run.app/api/v1/auth/google/callback`
   - Configured frontend URL: `https://buildtrace-frontend-136394139608.us-west2.run.app`

## What You Need To Do

### Update Google OAuth Redirect URIs

You need to add the production redirect URI to your Google Cloud OAuth configuration:

1. **Go to Google Cloud Console:**
   https://console.cloud.google.com/apis/credentials?project=buildtrace-dev

2. **Find your OAuth 2.0 Client ID:**
   - Look for: `136394139608-ps3elajb1viqbd91t7jmaeqhb4v2antt.apps.googleusercontent.com`
   - Click on it to edit

3. **Add Authorized Redirect URIs:**
   Add these URIs to the "Authorized redirect URIs" section:
   ```
   https://buildtrace-backend-136394139608.us-west2.run.app/api/v1/auth/google/callback
   https://buildtrace-frontend-136394139608.us-west2.run.app
   http://localhost:5001/api/v1/auth/google/callback
   http://localhost:3000
   ```

4. **Add Authorized JavaScript Origins:**
   Add these origins:
   ```
   https://buildtrace-backend-136394139608.us-west2.run.app
   https://buildtrace-frontend-136394139608.us-west2.run.app
   http://localhost:5001
   http://localhost:3000
   ```

5. **Save Changes**

## Quick Fix Command

Alternatively, you can use the gcloud CLI to update the OAuth configuration. However, this is more complex and the Console UI is recommended.

## Testing OAuth

After updating the redirect URIs, test the OAuth flow:

1. **Open the frontend:**
   https://buildtrace-frontend-136394139608.us-west2.run.app

2. **Click "Sign in with Google"**

3. **Verify the OAuth flow:**
   - You should be redirected to Google's login page
   - After login, you should be redirected back to the frontend
   - You should be logged in successfully

## OAuth Configuration Details

**Your OAuth Credentials:**
- Client ID: `136394139608-ps3elajb1viqbd91t7jmaeqhb4v2antt.apps.googleusercontent.com`
- Client Secret: Stored in GCP Secret Manager as `google-client-secret`

**Redirect URIs (Production):**
- Backend Callback: `https://buildtrace-backend-136394139608.us-west2.run.app/api/v1/auth/google/callback`
- Frontend URL: `https://buildtrace-frontend-136394139608.us-west2.run.app`

**Redirect URIs (Development):**
- Backend Callback: `http://localhost:5001/api/v1/auth/google/callback`
- Frontend URL: `http://localhost:3000`

## Troubleshooting

### Error: "redirect_uri_mismatch"
This means the redirect URI in the request doesn't match what's configured in Google Cloud Console.
- Check that you've added the correct URIs to the Console
- Make sure there are no trailing slashes
- Wait a few minutes after saving changes for them to propagate

### Error: "OAuth not configured"
This means the backend environment variables aren't set correctly.
- Check backend logs: `gcloud run logs read buildtrace-backend --region=us-west2`
- Verify secrets are accessible by the service account
- Redeploy backend if needed: `DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh`

### Check Current Configuration

```bash
# Check backend environment variables
gcloud run services describe buildtrace-backend \
  --region=us-west2 \
  --format="value(spec.template.spec.containers[0].env)"

# Check backend secrets
gcloud run services describe buildtrace-backend \
  --region=us-west2 \
  --format="value(spec.template.spec.containers[0].env.secrets)"
```

## Service Account Permissions

Make sure the service account has access to the secrets:

```bash
# Grant secret accessor role
gcloud secrets add-iam-policy-binding google-client-id \
  --member="serviceAccount:buildtrace-service-account@buildtrace-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-client-secret \
  --member="serviceAccount:buildtrace-service-account@buildtrace-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Summary

The backend is now configured with OAuth credentials. You just need to:
1. Go to Google Cloud Console
2. Add the production redirect URIs
3. Save and wait a few minutes
4. Test the OAuth flow

Once you've done this, the "Sign in with Google" button should work correctly!
