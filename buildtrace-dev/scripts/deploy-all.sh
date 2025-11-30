#!/bin/bash
# Simple script to deploy both backend and frontend

set -e

echo "================================================================================"
echo "DEPLOY ALL - BACKEND + FRONTEND"
echo "================================================================================"
echo ""
echo "This will deploy both backend and frontend to Cloud Run."
echo ""

# Run the full deployment script
cd "$(dirname "$0")/.." && ./scripts/DEPLOY_AND_TEST.sh

echo ""
echo "================================================================================"
echo "Both backend and frontend deployed successfully!"
echo "================================================================================"
