#!/bin/bash

echo "🔍 Checking Cloud Run deployments..."

MAIN_URL="https://buildtrace-overlay-lioa4ql2nq-uc.a.run.app"
FEATURE_URL="https://buildtrace-overlay-feature-largesize-lioa4ql2nq-uc.a.run.app"

echo ""
echo "📊 MAIN SERVICE - Configuration Check:"
curl -s "$MAIN_URL/admin/debug" | python -m json.tool 2>/dev/null || echo "Failed to get debug info"

echo ""
echo "📊 FEATURE SERVICE - Configuration Check:"
curl -s "$FEATURE_URL/admin/debug" | python -m json.tool 2>/dev/null || echo "Failed to get debug info"

echo ""
echo "🔧 To run database migration on MAIN service:"
echo "curl -X POST $MAIN_URL/admin/migrate-auth"

echo ""
echo "🔧 To run database migration on FEATURE service:"
echo "curl -X POST $FEATURE_URL/admin/migrate-auth"

echo ""
echo "🌐 Service URLs:"
echo "Main: $MAIN_URL"
echo "Feature: $FEATURE_URL"