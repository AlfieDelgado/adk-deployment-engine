#!/bin/bash
# Pre-deployment Hook Script
# Runs validation and setup tasks before deployment starts

set -e

echo "🔍 Running pre-deployment tasks..."
echo "📋 Agent: $1"
echo ""

# ==============================================
# MCP Configuration Sync
# ==============================================
# Uncomment to enable MCP configuration sync with remote upstream
#
# echo "🔄 Syncing MCP configuration..."
# git pull origin main -- config/mcp/
# gcloud secrets versions access latest --secret="mcp-config" > config/mcp/config.json
# echo "✅ MCP configuration synced"

# ==============================================
# Environment Validation
# ==============================================
# Uncomment to validate required environment variables
#
# echo "🔐 Validating environment variables..."
# source agents/$1/.env.secrets
#
# required_vars=("SERVICE_ACCOUNT" "GOOGLE_CLOUD_PROJECT")
# for var in "${required_vars[@]}"; do
#     if [ -z "${!var}" ]; then
#         echo "❌ Error: $var not set"
#         exit 1
#     fi
# done
# echo "✅ Environment validation passed"

# ==============================================
# Pre-deployment Tests
# ==============================================
# Uncomment to run tests before deployment
#
# echo "🧪 Running pre-deployment tests..."
# python -m pytest tests/unit/
# echo "✅ Tests passed"

# Test marker: creates a file to verify hook ran
touch /tmp/pre-deploy-ran.txt

echo "✅ Pre-deployment tasks completed!"
echo "💡 Uncomment sections above to enable specific checks"
