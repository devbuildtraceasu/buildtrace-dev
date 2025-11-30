#!/bin/bash
set -e

echo "🔧 Fixing Image Pull Issue"
echo "=========================="
echo ""
echo "The issue is that nodes need to be restarted to pick up new IAM permissions."
echo "OR we can use imagePullSecrets."
echo ""
echo "Option 1: Restart Nodes (Recommended but disruptive)"
echo "Option 2: Use Image Pull Secrets (Quick fix)"
echo ""
read -p "Choose option (1 or 2): " option

if [ "$option" == "2" ]; then
    echo ""
    echo "Creating image pull secret..."
    
    # Get current user's gcloud credentials
    if [ -f ~/.config/gcloud/application_default_credentials.json ]; then
        kubectl create secret docker-registry artifact-registry-secret \
          --docker-server=us-west2-docker.pkg.dev \
          --docker-username=_json_key \
          --docker-password="$(cat ~/.config/gcloud/application_default_credentials.json)" \
          --docker-email=dev@buildtraceai.com \
          -n prod-app \
          --dry-run=client -o yaml | kubectl apply -f -
        
        echo "✅ Secret created"
        echo ""
        echo "Updating deployments to use imagePullSecrets..."
        
        # Add imagePullSecrets to all deployments
        kubectl patch deployment ocr-worker -n prod-app -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"artifact-registry-secret"}]}}}}'
        kubectl patch deployment diff-worker -n prod-app -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"artifact-registry-secret"}]}}}}'
        kubectl patch deployment summary-worker -n prod-app -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"artifact-registry-secret"}]}}}}'
        
        echo "✅ Deployments updated"
        echo ""
        echo "Deleting pods to restart with new config..."
        kubectl delete pods -n prod-app --all
        sleep 10
        kubectl get pods -n prod-app
        
    else
        echo "❌ Error: ~/.config/gcloud/application_default_credentials.json not found"
        echo "Run: gcloud auth application-default login"
        exit 1
    fi
    
elif [ "$option" == "1" ]; then
    echo ""
    echo "To restart nodes, run these commands manually:"
    echo ""
    echo "# Get node names"
    echo "kubectl get nodes"
    echo ""
    echo "# For each node, drain it:"
    echo "kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data"
    echo ""
    echo "# Then restart the node in GCP Console or:"
    echo "gcloud compute instances reset <node-name> --zone=us-west2-a"
    echo ""
    echo "# After restart, uncordon:"
    echo "kubectl uncordon <node-name>"
    echo ""
    echo "⚠️  This will cause temporary downtime for pods on those nodes."
    
else
    echo "Invalid option"
    exit 1
fi

