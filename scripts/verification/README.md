# Post-Setup Verification Scripts

This directory contains scripts to verify that all GCP infrastructure has been set up correctly after the initial setup.

## Scripts

### `verify-setup.sh`
Comprehensive verification script that checks:
- ✅ All required APIs are enabled
- ✅ Cloud Storage buckets exist and are configured
- ✅ Pub/Sub topics and subscriptions are created
- ✅ Service accounts exist and have correct permissions
- ✅ Artifact Registry repositories are created
- ✅ Secrets are created and accessible
- ✅ Cloud SQL instance is running (if created)
- ✅ IAM permissions are correctly configured

### `verify-apis.sh`
Quick check for enabled APIs.

### `verify-storage.sh`
Verifies storage buckets and folder structure.

### `verify-pubsub.sh`
Verifies Pub/Sub topics and subscriptions.

### `verify-service-accounts.sh`
Verifies service accounts and IAM roles.

## Usage

### Run Full Verification

```bash
# Make script executable
chmod +x scripts/verification/verify-setup.sh

# Run verification
./scripts/verification/verify-setup.sh
```

### Run Individual Checks

```bash
./scripts/verification/verify-apis.sh
./scripts/verification/verify-storage.sh
./scripts/verification/verify-pubsub.sh
./scripts/verification/verify-service-accounts.sh
```

## Output

The verification script will output:
- ✅ Green checkmarks for successful checks
- ❌ Red X marks for failed checks
- ⚠️  Yellow warnings for issues that need attention
- Summary report at the end

## Troubleshooting

If verification fails:
1. Check the error message for specific issues
2. Ensure PROJECT_ID and REGION are set correctly
3. Verify you have required permissions (Owner or Editor + Security Admin)
4. Some resources may take a few minutes to propagate - wait and retry

