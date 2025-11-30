# Development Environment Setup

This directory contains scripts and configuration files to set up your local development environment for BuildTrace.

## Contents

### `setup-local.sh`
Automated script to set up local development environment:
- Creates `.env.local` file with required environment variables
- Sets up Cloud SQL Proxy connection
- Configures local authentication
- Downloads service account key (if needed)

### `.env.local.template`
Template for local environment variables. Copy this to `.env.local` and fill in your values.

### `docker-compose.local.yml`
Docker Compose configuration for running services locally (optional).

### `local-db-setup.sh`
Script to set up local database connection via Cloud SQL Proxy.

## Quick Start

### 1. Run Setup Script

```bash
# Make script executable
chmod +x scripts/dev-setup/setup-local.sh

# Run setup
./scripts/dev-setup/setup-local.sh
```

### 2. Configure Environment Variables

The setup script will create `.env.local` from the template. Update it with your values:

```bash
# Edit .env.local
nano .env.local
```

Required variables:
- `PROJECT_ID` - Your GCP project ID
- `DB_PASSWORD` - Database password (from Secret Manager)
- `OPENAI_API_KEY` - Your OpenAI API key
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account key

### 3. Start Cloud SQL Proxy

```bash
# Start proxy (in separate terminal)
./scripts/dev-setup/local-db-setup.sh
```

### 4. Run Application Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py
```

## Manual Setup

If you prefer manual setup:

1. **Copy environment template:**
   ```bash
   cp scripts/dev-setup/.env.local.template .env.local
   ```

2. **Fill in values in `.env.local`**

3. **Download service account key:**
   ```bash
   gcloud iam service-accounts keys create buildtrace-key.json \
     --iam-account=buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Set environment variable:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="./buildtrace-key.json"
   ```

5. **Start Cloud SQL Proxy:**
   ```bash
   cloud_sql_proxy -instances=$PROJECT_ID:$REGION:buildtrace-dev-db=tcp:5432
   ```

## Troubleshooting

### Cloud SQL Proxy Connection Issues
- Verify Cloud SQL instance name is correct
- Check that your IP is authorized (if using public IP)
- Ensure service account has `roles/cloudsql.client` role

### Authentication Issues
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid key file
- Run `gcloud auth application-default login` as fallback
- Check service account has required permissions

### Environment Variable Issues
- Ensure `.env.local` is in project root
- Check that all required variables are set
- Verify no typos in variable names

