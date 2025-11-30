#!/bin/bash
set -e

PROJECT_ID="buildtrace-dev"
REGION="us-west2"
CLUSTER_NAME="buildtrace-dev"
NAMESPACE="prod-app"
IMAGE_NAME="gcr.io/${PROJECT_ID}/buildtrace-backend:latest"

echo "🚀 Deploying BuildTrace Workers to GKE"
echo "========================================"
echo "Project: ${PROJECT_ID}"
echo "Cluster: ${CLUSTER_NAME}"
echo "Region: ${REGION}"
echo ""

# Step 1: Build and push Docker image
echo "📦 Step 1: Building Docker image..."
cd "$(dirname "$0")/../backend"
docker build -t ${IMAGE_NAME} .
docker push ${IMAGE_NAME}
echo "✅ Image pushed: ${IMAGE_NAME}"

# Step 2: Set kubectl context
echo ""
echo "🔧 Step 2: Setting kubectl context..."
gcloud container clusters get-credentials ${CLUSTER_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID}

# Step 3: Create namespace
echo ""
echo "📁 Step 3: Creating namespace..."
kubectl apply -f ../k8s/namespace.yaml

# Step 4: Create secrets from .env file
echo ""
echo "🔐 Step 4: Creating secrets..."
if [ -f .env ]; then
  kubectl create secret generic buildtrace-app-env \
    --from-env-file .env \
    --namespace ${NAMESPACE} \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "✅ Secrets created from .env file"
else
  echo "⚠️  Warning: .env file not found. Create secret manually:"
  echo "   kubectl create secret generic buildtrace-app-env \\"
  echo "     --from-env-file backend/.env -n ${NAMESPACE}"
fi

# Step 5: Create ConfigMap and ServiceAccount
echo ""
echo "⚙️  Step 5: Creating ConfigMap and ServiceAccount..."
kubectl apply -f ../k8s/secrets.yaml

# Step 6: Verify Workload Identity binding
echo ""
echo "🔗 Step 6: Verifying Workload Identity..."
gcloud iam service-accounts add-iam-policy-binding \
  buildtrace-gke-workload@${PROJECT_ID}.iam.gserviceaccount.com \
  --member "serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/buildtrace-app-sa]" \
  --role roles/iam.workloadIdentityUser \
  --project ${PROJECT_ID} 2>&1 | grep -v "Policy is already set" || true

# Step 7: Deploy workers
echo ""
echo "🚀 Step 7: Deploying workers..."
kubectl apply -f ../k8s/ocr-worker-deployment.yaml
kubectl apply -f ../k8s/diff-worker-deployment.yaml
kubectl apply -f ../k8s/summary-worker-deployment.yaml

# Step 8: Wait for deployments
echo ""
echo "⏳ Step 8: Waiting for deployments to be ready..."
kubectl wait --for=condition=available \
  --timeout=300s \
  deployment/ocr-worker \
  deployment/diff-worker \
  deployment/summary-worker \
  -n ${NAMESPACE} || echo "⚠️  Some deployments may still be starting..."

# Step 9: Show status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Worker Status:"
kubectl get pods -n ${NAMESPACE} -l 'app in (ocr-worker,diff-worker,summary-worker)'
echo ""
echo "📝 View logs:"
echo "  OCR Worker:    kubectl logs -f deployment/ocr-worker -n ${NAMESPACE}"
echo "  Diff Worker:    kubectl logs -f deployment/diff-worker -n ${NAMESPACE}"
echo "  Summary Worker: kubectl logs -f deployment/summary-worker -n ${NAMESPACE}"

