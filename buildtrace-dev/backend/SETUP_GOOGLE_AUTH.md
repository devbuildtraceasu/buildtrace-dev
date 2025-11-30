# Google Cloud Authentication Setup

## Current Issue
The application is using `shekharashishraj@gmail.com` for Google Cloud authentication, but it should use `dev@buildtraceai.com`.

## Solution

### Option 1: Use Application Default Credentials (Recommended for Development)

1. **Set the gcloud account** (if not already set):
   ```bash
   gcloud config set account dev@buildtraceai.com
   ```

2. **Re-authenticate with Application Default Credentials**:
   ```bash
   gcloud auth application-default login --account=dev@buildtraceai.com
   ```
   
   This will open a browser window for you to authenticate. After authentication, the credentials will be stored locally and used by the application.

3. **Verify the account**:
   ```bash
   gcloud config get-value account
   ```
   Should show: `dev@buildtraceai.com`

### Option 2: Use Service Account (Recommended for Production)

1. **Create a service account** in Google Cloud Console:
   - Go to IAM & Admin > Service Accounts
   - Create a new service account with email like `buildtrace-service@buildtrace-dev.iam.gserviceaccount.com`
   - Grant necessary permissions (Storage Admin, Pub/Sub Admin, etc.)

2. **Download the service account key**:
   - Click on the service account
   - Go to Keys tab
   - Create a new JSON key
   - Download the JSON file

3. **Set the environment variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

4. **Add to .env file**:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

## Verify Authentication

After setting up, restart your Flask server and check the logs. You should see:
- No more `shekharashishraj@gmail.com` errors
- Successful GCS bucket access (or proper fallback to local storage)

## Current Status

- ✅ gcloud account: `dev@buildtraceai.com`
- ⏳ Application Default Credentials: Need to re-authenticate

## Next Steps

1. Run: `gcloud auth application-default login --account=dev@buildtraceai.com`
2. Restart Flask server
3. Check logs for successful authentication

