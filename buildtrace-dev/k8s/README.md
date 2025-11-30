# GKE Worker Deployment Guide

This directory contains Kubernetes manifests for deploying BuildTrace workers to GKE.

## Prerequisites

1. **GKE Cluster**: `buildtrace-dev` cluster in `us-west2` region
2. **Docker Image**: Backend image built and pushed to `gcr.io/buildtrace-dev/buildtrace-backend:latest`
3. **Secrets**: Environment variables stored in `.env` file or Secret Manager
4. **Pub/Sub**: Topics and subscriptions created (run `scripts/verify-pubsub.sh`)

## Quick Start

### 1. Verify Pub/Sub Setup
```bash
./scripts/verify-pubsub.sh
```

### 2. Deploy Workers
```bash
./scripts/deploy-workers-gke.sh
```

## Manual Deployment Steps

### Step 1: Build and Push Docker Image
```bash
cd backend
docker build -t gcr.io/buildtrace-dev/buildtrace-backend:latest .
docker push gcr.io/buildtrace-dev/buildtrace-backend:latest
```

### Step 2: Set kubectl Context
```bash
gcloud container clusters get-credentials buildtrace-dev \
  --region us-west2 \
  --project buildtrace-dev
```

### Step 3: Create Namespace
```bash
kubectl apply -f k8s/namespace.yaml
```

### Step 4: Create Secrets
```bash
# From backend/.env file
kubectl create secret generic buildtrace-app-env \
  --from-env-file backend/.env \
  --namespace prod-app
```

### Step 5: Create ConfigMap and ServiceAccount
```bash
kubectl apply -f k8s/secrets.yaml
```

### Step 6: Set Up Workload Identity
```bash
gcloud iam service-accounts add-iam-policy-binding \
  buildtrace-gke-workload@buildtrace-dev.iam.gserviceaccount.com \
  --member "serviceAccount:buildtrace-dev.svc.id.goog[prod-app/buildtrace-app-sa]" \
  --role roles/iam.workloadIdentityUser \
  --project buildtrace-dev
```

### Step 7: Deploy Workers
```bash
kubectl apply -f k8s/ocr-worker-deployment.yaml
kubectl apply -f k8s/diff-worker-deployment.yaml
kubectl apply -f k8s/summary-worker-deployment.yaml
```

### Step 8: Verify Deployment
```bash
# Check pod status
kubectl get pods -n prod-app

# Check logs
kubectl logs -f deployment/ocr-worker -n prod-app
kubectl logs -f deployment/diff-worker -n prod-app
kubectl logs -f deployment/summary-worker -n prod-app
```

## Files

- `namespace.yaml` - Creates `prod-app` namespace
- `secrets.yaml` - ServiceAccount and ConfigMap for worker configuration
- `ocr-worker-deployment.yaml` - OCR worker deployment (2 replicas)
- `diff-worker-deployment.yaml` - Diff worker deployment (2 replicas)
- `summary-worker-deployment.yaml` - Summary worker deployment (2 replicas)

## Worker Entry Points

Workers use standalone entry point scripts:
- `backend/workers/ocr_worker_entry.py`
- `backend/workers/diff_worker_entry.py`
- `backend/workers/summary_worker_entry.py`

These scripts:
1. Initialize Pub/Sub subscriber
2. Create worker instance
3. Start listening for messages
4. Process messages and update job stages

## Scaling

To scale workers:
```bash
# Scale OCR workers to 5 replicas
kubectl scale deployment ocr-worker --replicas=5 -n prod-app

# Scale all workers
kubectl scale deployment ocr-worker diff-worker summary-worker --replicas=3 -n prod-app
```

## Troubleshooting

### Pods Not Starting
```bash
# Check pod events
kubectl describe pod <pod-name> -n prod-app

# Check logs
kubectl logs <pod-name> -n prod-app
```

### Workers Not Receiving Messages
```bash
# Verify Pub/Sub subscriptions
gcloud pubsub subscriptions list --project=buildtrace-dev

# Check subscription message count
gcloud pubsub subscriptions describe buildtrace-dev-ocr-worker-sub \
  --project=buildtrace-dev
```

### Permission Errors
```bash
# Verify Workload Identity binding
gcloud iam service-accounts get-iam-policy \
  buildtrace-gke-workload@buildtrace-dev.iam.gserviceaccount.com \
  --project=buildtrace-dev
```

## Monitoring

### View All Worker Pods
```bash
kubectl get pods -n prod-app -l 'app in (ocr-worker,diff-worker,summary-worker)'
```

### Watch Pod Status
```bash
watch kubectl get pods -n prod-app
```

### Stream Logs from All Workers
```bash
# OCR Worker
kubectl logs -f -l app=ocr-worker -n prod-app

# All workers
kubectl logs -f -l 'app in (ocr-worker,diff-worker,summary-worker)' -n prod-app
```

## Cleanup

To remove all workers:
```bash
kubectl delete deployment ocr-worker diff-worker summary-worker -n prod-app
kubectl delete configmap buildtrace-worker-config -n prod-app
kubectl delete serviceaccount buildtrace-app-sa -n prod-app
kubectl delete namespace prod-app
```

