#!/bin/bash
# Post-deployment Hook Script
# Runs health checks and notifications after successful deployment

set -e

echo "🎉 Running post-deployment tasks..."
echo "📋 Agent: $1"
echo ""

# ==============================================
# Health Check
# ==============================================
# Uncomment to enable deployment health checks
#
# echo "🏥 Running health check..."
# SERVICE_NAME=$(grep "service_name:" agents/$1/config.yaml | awk '{print $2}')
# DEPLOYMENT_URL="https://$(gcloud run services describe $SERVICE_NAME --platform managed --region us-central1 --format 'value(status.url)')"
#
# echo "🌐 Deployment URL: $DEPLOYMENT_URL"
# response=$(curl -s -o /dev/null -w "%{http_code}" "$DEPLOYMENT_URL/health")
#
# if [ "$response" = "200" ]; then
#     echo "✅ Health check passed (HTTP $response)"
# else
#     echo "❌ Health check failed (HTTP $response)"
#     exit 1
# fi

# ==============================================
# Deployment Notification
# ==============================================
# Uncomment to send deployment notifications
#
# echo "📢 Sending deployment notification..."
# webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
# message="✅ Agent $1 deployed successfully!"
#
# curl -X POST -H 'Content-type: application/json' \
#   --data "{\"text\":\"$message\"}" \
#   "$webhook_url"

# ==============================================
# Smoke Tests
# ==============================================
# Uncomment to run smoke tests after deployment
#
# echo "🧪 Running smoke tests..."
# python -m pytest tests/smoke/
# echo "✅ Smoke tests passed"

# Test marker: creates a file to verify hook ran
touch /tmp/post-deploy-ran.txt

echo "✅ Post-deployment tasks completed!"
echo "💡 Uncomment sections above to enable specific checks"
