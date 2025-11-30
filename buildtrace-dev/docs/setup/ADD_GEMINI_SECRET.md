# Adding Gemini API Key Secret to Google Cloud

## Quick Method (Using Script)

```bash
cd buildtrace-dev
./create_gemini_secret.sh
```

## Manual Method

### Step 1: Create the Secret

**Option A: From command line (prompts for key)**
```bash
gcloud secrets create gemini-api-key \
  --replication-policy="automatic" \
  --project=buildtrace-dev
```

Then add the secret value:
```bash
echo -n "YOUR_GEMINI_API_KEY_HERE" | gcloud secrets versions add gemini-api-key \
  --data-file=- \
  --project=buildtrace-dev
```

**Option B: From command line (using environment variable)**
```bash
export GEMINI_API_KEY="your-api-key-here"
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project=buildtrace-dev
```

**Option C: Using Google Cloud Console**
1. Go to: https://console.cloud.google.com/security/secret-manager?project=buildtrace-dev
2. Click "CREATE SECRET"
3. Name: `gemini-api-key`
4. Secret value: Paste your Gemini API key
5. Click "CREATE SECRET"

### Step 2: Grant Service Account Access

```bash
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:buildtrace-service-account@buildtrace-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=buildtrace-dev
```

### Step 3: Verify Secret Exists

```bash
gcloud secrets describe gemini-api-key --project=buildtrace-dev
```

### Step 4: Deploy

After the secret is created, run the deployment:

```bash
cd buildtrace-dev
./DEPLOY_AND_TEST.sh
```

## Troubleshooting

**If secret already exists:**
```bash
# Add a new version
echo -n "YOUR_NEW_API_KEY" | gcloud secrets versions add gemini-api-key \
  --data-file=- \
  --project=buildtrace-dev
```

**Check existing secrets:**
```bash
gcloud secrets list --project=buildtrace-dev
```

**View secret versions:**
```bash
gcloud secrets versions list gemini-api-key --project=buildtrace-dev
```

