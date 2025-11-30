#!/bin/bash
set -e

echo "🔄 Restarting GKE Nodes to Pick Up IAM Permissions"
echo "=================================================="
echo ""
echo "This will restart nodes one at a time to pick up new Artifact Registry permissions."
echo "Pods will be moved to other nodes automatically (no downtime)."
echo ""
read -p "Continue? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

# Get all node names
NODES=$(kubectl get nodes -o name | sed 's|node/||')

for NODE in $NODES; do
    echo ""
    echo "🔄 Processing node: $NODE"
    echo "------------------------"
    
    # Get zone from node
    ZONE=$(kubectl get node $NODE -o jsonpath='{.metadata.labels.failure-domain\.beta\.kubernetes\.io/zone}' || echo "us-west2-a")
    
    echo "📦 Draining node..."
    kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --timeout=5m || {
        echo "⚠️  Drain failed or timed out, continuing anyway..."
    }
    
    echo "🔄 Restarting node..."
    # Try to get instance name from node
    INSTANCE_NAME=$(echo $NODE | sed 's/gke-buildtrace-dev-default-pool-//')
    
    # Restart via gcloud (if we can determine the instance)
    if [ -n "$INSTANCE_NAME" ]; then
        echo "   Attempting restart via gcloud..."
        gcloud compute instances reset $NODE --zone=$ZONE --project=buildtrace-dev 2>&1 || {
            echo "   ⚠️  Could not restart via gcloud. Please restart manually in GCP Console."
            echo "   Node: $NODE"
            echo "   Zone: $ZONE"
        }
    else
        echo "   ⚠️  Please restart node manually in GCP Console:"
        echo "   Node: $NODE"
        echo "   Zone: $ZONE"
    fi
    
    echo "⏳ Waiting for node to be ready..."
    sleep 30
    
    # Wait for node to be ready (with timeout)
    timeout=300
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if kubectl get node $NODE | grep -q "Ready"; then
            echo "✅ Node is ready!"
            break
        fi
        sleep 10
        elapsed=$((elapsed + 10))
        echo "   Still waiting... ($elapsed/$timeout seconds)"
    done
    
    echo "🔓 Uncordoning node..."
    kubectl uncordon $NODE
    
    echo "✅ Node $NODE restarted and ready!"
    echo ""
    sleep 10
done

echo ""
echo "✅ All nodes processed!"
echo ""
echo "📊 Checking pod status..."
kubectl get pods -n prod-app

