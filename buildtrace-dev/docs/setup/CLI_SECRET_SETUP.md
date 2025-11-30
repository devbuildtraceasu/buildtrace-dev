# Setting Gemini API Key Secret via CLI

## Quick Setup (One Command)

Replace `YOUR_GEMINI_API_KEY_HERE` with your actual API key:

```bash
echo -n "YOUR_GEMINI_API_KEY_HERE" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project=buildtrace-dev
```

## Step-by-Step Setup

### Step 1: Create the Secret

**Option A: Interactive (will prompt for key)**
```bash
gcloud secrets create gemini-api-key \
  --replication-policy="automatic" \
  --project=buildtrace-dev
```

Then add the value:
```bash
echo -n "YOUR_GEMINI_API_KEY_HERE" | gcloud secrets versions add gemini-api-key \
  --data-file=- \
  --project=buildtrace-dev
```

**Option B: Using environment variable**
```bash
# Set your API key
export GEMINI_API_KEY="your-actual-api-key-here"

# Create secret with the value
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project=buildtrace-dev
```

**Option C: From file (if you have the key in a file)**
```bash
gcloud secrets create gemini-api-key \
  --data-file=path/to/your/api-key-file.txt \
  --replication-policy="automatic" \
  --project=buildtrace-dev
```

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

## Complete One-Liner (if secret doesn't exist)

```bash
# Create secret and grant access in one go
export GEMINI_API_KEY="your-api-key-here" && \
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy="automatic" \
  --project=buildtrace-dev && \
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:buildtrace-service-account@buildtrace-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=buildtrace-dev
```

## If Secret Already Exists

If you get an error that the secret already exists, add a new version:

```bash
echo -n "YOUR_NEW_API_KEY" | gcloud secrets versions add gemini-api-key \
  --data-file=- \
  --project=buildtrace-dev
```

## Check Existing Secrets

```bash
# List all secrets
gcloud secrets list --project=buildtrace-dev

# Check if gemini-api-key exists
gcloud secrets describe gemini-api-key --project=buildtrace-dev

# List versions of a secret
gcloud secrets versions list gemini-api-key --project=buildtrace-dev
```

