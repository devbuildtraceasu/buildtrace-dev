# Final Solution: Image Pull Issue

## Current Status
- ✅ Permissions granted to service accounts
- ✅ Image exists in Artifact Registry
- ❌ Nodes haven't refreshed credentials yet
- ❌ Service account key creation is disabled (security policy)

## Solution: Restart Nodes

The nodes need to be restarted to pick up the new IAM permissions. This is the only reliable way since:
1. Service account key creation is disabled
2. User credentials don't work for Artifact Registry
3. Nodes cache their credentials

### Quick Fix: Restart One Node at a Time

```bash
# Get node names
kubectl get nodes

# For each node:
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
# Wait for pods to move (check with: kubectl get pods -n prod-app)

# Restart node in GCP Console:
# 1. Go to: https://console.cloud.google.com/compute/instances
# 2. Find the node instance
# 3. Click "Reset" or "Stop" then "Start"

# After restart:
kubectl uncordon <node-name>
```

### Automated Script

I've created a script to help, but you'll need to restart nodes manually in GCP Console:

```bash
./scripts/restart-nodes-for-image-pull.sh
```

### Alternative: Scale Down/Up (If Auto-Scaling Enabled)

If your cluster has auto-scaling, you can force new nodes:

```bash
# Scale down to 0
kubectl scale deployment ocr-worker diff-worker summary-worker --replicas=0 -n prod-app

# Wait for nodes to scale down (check: kubectl get nodes)
sleep 120

# Scale back up - new nodes will have correct permissions
kubectl scale deployment ocr-worker diff-worker summary-worker --replicas=2 -n prod-app
```

## Why This Happens

GKE nodes cache their IAM credentials. When we grant new permissions:
- ✅ Permissions are granted immediately
- ❌ Nodes don't refresh until restart
- ✅ New nodes automatically get correct permissions

## After Restart

Once nodes are restarted, verify:

```bash
kubectl get pods -n prod-app
# Should see: READY 1/1, STATUS Running

kubectl logs -f deployment/ocr-worker -n prod-app
# Should see: "Starting OCR worker" and "listening for messages..."
```

## Permissions Already Granted ✅

- `roles/artifactregistry.reader` - GKE node service account (project + repository)
- `roles/artifactregistry.reader` - Workload service account (repository)
- `roles/storage.objectViewer` - Compute service account

All permissions are correct - nodes just need to restart to pick them up!

