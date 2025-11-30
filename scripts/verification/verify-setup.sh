#!/bin/bash
# Comprehensive verification script for BuildTrace GCP infrastructure

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-west2}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

echo "=========================================="
echo "BuildTrace Infrastructure Verification"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Set project
gcloud config set project $PROJECT_ID > /dev/null 2>&1

# Function to check and report
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅${NC} $1"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $1"
        ((FAILED++))
        return 1
    fi
}

warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
    ((WARNINGS++))
}

# Check APIs
echo "Checking APIs..."
echo "----------------"

APIS=(
    "run.googleapis.com"
    "container.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "pubsub.googleapis.com"
    "storage-component.googleapis.com"
    "sqladmin.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
    "secretmanager.googleapis.com"
)

for api in "${APIS[@]}"; do
    gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api" && \
        check "API enabled: $api" || \
        warn "API not enabled: $api"
done

echo ""

# Check Storage Buckets
echo "Checking Storage Buckets..."
echo "---------------------------"

BUCKETS=(
    "buildtrace-dev-input-$PROJECT_ID"
    "buildtrace-dev-processed-$PROJECT_ID"
    "buildtrace-dev-artifacts-$PROJECT_ID"
)

for bucket in "${BUCKETS[@]}"; do
    gsutil ls -b gs://$bucket > /dev/null 2>&1 && \
        check "Bucket exists: $bucket" || \
        warn "Bucket missing: $bucket"
done

echo ""

# Check Pub/Sub Topics
echo "Checking Pub/Sub Topics..."
echo "--------------------------"

TOPICS=(
    "buildtrace-dev-ocr-queue"
    "buildtrace-dev-diff-queue"
    "buildtrace-dev-summary-queue"
    "buildtrace-dev-orchestrator-queue"
    "buildtrace-dev-ocr-dlq"
    "buildtrace-dev-diff-dlq"
    "buildtrace-dev-summary-dlq"
)

for topic in "${TOPICS[@]}"; do
    gcloud pubsub topics describe $topic > /dev/null 2>&1 && \
        check "Topic exists: $topic" || \
        warn "Topic missing: $topic"
done

echo ""

# Check Pub/Sub Subscriptions
echo "Checking Pub/Sub Subscriptions..."
echo "----------------------------------"

SUBSCRIPTIONS=(
    "buildtrace-dev-ocr-worker-sub"
    "buildtrace-dev-diff-worker-sub"
    "buildtrace-dev-summary-worker-sub"
    "buildtrace-dev-ocr-dlq-sub"
    "buildtrace-dev-diff-dlq-sub"
    "buildtrace-dev-summary-dlq-sub"
)

for sub in "${SUBSCRIPTIONS[@]}"; do
    gcloud pubsub subscriptions describe $sub > /dev/null 2>&1 && \
        check "Subscription exists: $sub" || \
        warn "Subscription missing: $sub"
done

echo ""

# Check Service Accounts
echo "Checking Service Accounts..."
echo "----------------------------"

SERVICE_ACCOUNTS=(
    "buildtrace-service-account"
    "buildtrace-cloudbuild"
    "buildtrace-gke-workload"
)

for sa in "${SERVICE_ACCOUNTS[@]}"; do
    gcloud iam service-accounts describe $sa@$PROJECT_ID.iam.gserviceaccount.com > /dev/null 2>&1 && \
        check "Service account exists: $sa" || \
        warn "Service account missing: $sa"
done

echo ""

# Check Artifact Registry
echo "Checking Artifact Registry..."
echo "-----------------------------"

REPOS=(
    "buildtrace-repo"
    "buildtrace-base-images"
)

for repo in "${REPOS[@]}"; do
    gcloud artifacts repositories describe $repo --location=$REGION > /dev/null 2>&1 && \
        check "Repository exists: $repo" || \
        warn "Repository missing: $repo"
done

echo ""

# Check Secrets
echo "Checking Secrets..."
echo "-------------------"

SECRETS=(
    "db-root-password"
    "db-user-password"
    "openai-api-key"
    "auth-provider-secret"
    "jwt-signing-key"
)

for secret in "${SECRETS[@]}"; do
    gcloud secrets describe $secret > /dev/null 2>&1 && \
        check "Secret exists: $secret" || \
        warn "Secret missing: $secret"
done

echo ""

# Check Cloud SQL (optional - may not be created yet)
echo "Checking Cloud SQL (optional)..."
echo "---------------------------------"

gcloud sql instances describe buildtrace-dev-db > /dev/null 2>&1 && \
    check "Cloud SQL instance exists: buildtrace-dev-db" || \
    warn "Cloud SQL instance not found (this is OK if not created yet)"

echo ""

# Summary
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Some warnings found, but no failures.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please review and fix issues.${NC}"
    exit 1
fi

