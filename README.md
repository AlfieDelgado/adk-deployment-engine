# ADK Agents Deployment Engine

Dynamic deployment system for ADK agents with per-agent configuration, Google Cloud Run integration, and comprehensive secret management.

## 📑 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🔗 As Git Sub-module](#-as-git-sub-module)
- [⚙️ Core Concepts](#️-core-concepts)
- [📦 Shared Utilities Package](#-shared-utilities-package)
- [🔧 Agent Configuration](#-agent-configuration)
- [🚀 Deployment Commands](#-deployment-commands)
- [📋 Configuration Examples](#-configuration-examples)
- [🔐 Environment Setup](#-environment-setup)
- [🐛 Troubleshooting](#-troubleshooting)
- [📄 License](#-license)

---

## 🚀 Quick Start

```bash
# 1. Conda environment and Python dependencies
conda env create -f environment.yml

# 2. Set up global configuration
cp .env.example .env
# Edit .env with your Google Cloud project settings

# 3. Configure your agent
cd agents-examples/quickstart/
# Edit config.yaml and .env.secrets

# 4. Deploy your agent
make deploy quickstart
```

## 🔗 As Git Sub-module

Use this deployment engine as a sub-module in your own projects while keeping your agents private.

### Quick Setup

```bash
# 1. Add this repository as a sub-module
git submodule add https://github.com/AlfieDelgado/adk-deployment-engine.git

# 2. Create your makefile
cat > makefile << 'EOF'
AGENTS_DIR := agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
EOF

# 3. Create your agents directory and set up environment
mkdir agents
cp adk-deployment-engine/.env.example .env
```

**All make commands work identically to standalone usage**:

```bash
make deploy your-agent
make list-agents
make delete your-agent
```

> **📚 Complete sub-module guide**: See [SUBMODULE.md](SUBMODULE.md) for detailed setup instructions and advanced usage.

## ⚙️ Core Concepts

### Environment Variable Priority

| Priority | Source | Location | Use Case |
|----------|--------|----------|----------|
| 1 (Highest) | Google Secret Manager | `agents/{agent_name}/config.yaml` flags | Production secrets |
| 2 (Medium) | Agent-specific secrets | `agents/{agent_name}/.env.secrets` | Agent-specific configuration |
| 3 (Lowest) | Global environment | Project `.env` | Shared defaults |

### Variable Syntax

Use shell-style `${VAR_NAME}` syntax in `config.yaml`:

```yaml
cloud_run:
  additional_flags:
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
```

## 📦 Shared Utilities Package

The deployment engine includes a shared utilities package (`adk-shared`) that provides common functionality for agents, including environment management and helper functions.

### Quick Start
# Add to requirements.txt
```bash
adk-shared @ git+https://github.com/AlfieDelgado/adk-deployment-engine.git@main#subdirectory=shared
```

```python
# Import in your agent
from adk_shared.helpers import load_env_vars

# Load environment variables
load_env_vars()
```

> **📚 Complete documentation**: See [shared/README.md](shared/README.md) for detailed usage instructions.

## 🔧 Agent Configuration

### Basic `config.yaml` Example

```yaml
description: Customer service agent with search capabilities
tags:
  - customer-support
  - production

docker:
  base_image: python:3.13-slim
  system_packages: [curl]  # Optional system packages

cloud_run:
  service_name: customer-service-agent
  additional_flags:
    # Resources
    - --memory=2Gi
    - --cpu=1
    - --timeout=600s

    # Scaling
    - --min-instances=0
    - --max-instances=10
    - --concurrency=10

    # Environment variables with substitution
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=GOOGLE_API_KEY=${SECRET_NAME}:latest
```

### Secret Manager Integration

Configure secrets in `config.yaml`:

```yaml
cloud_run:
  additional_flags:
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
```

**Format**: `ENV_VAR=SECRET_NAME:VERSION`
- `ENV_VAR`: Container environment variable name
- `SECRET_NAME`: Secret Manager secret name
- `VERSION`: `latest` or version number

### Agent Engine Management (Optional)

For agents requiring session management, create a Vertex AI Agent Engine:

```bash
# Create Agent Engine (requires AGENT_ENGINE_NAME env var)
make create-agent-engine <agent-name>

# Add the returned AGENT_ENGINE_ID to your .env file
```

## 🚀 Deployment Commands

### Essential Commands

```bash
# Agent Management
make list-agents                  # List available agents
make deploy <agent_name>         # Deploy to Cloud Run
make delete <agent_name>         # Delete service

# Testing & Validation
make deploy-dry <agent_name>     # Test deployment (dry run)
make test-build <agent_name>     # Test build structure
make test-dockerfile <agent_name> # Test Dockerfile generation

# Agent Engine (for session management)
make create-agent-engine <agent>  # Create Vertex AI Agent Engine

# Project Setup
make enable-services              # Enable required Google Cloud APIs
```

### Verbose Deployment

```bash
# Deploy with detailed logging
python utils/deploy_agent.py --deploy <agent_name> --verbose
```

## 📋 Configuration Examples

### Simple Agent

```yaml
description: Basic test agent
tags: [simple, testing]

docker:
  base_image: python:3.13-slim

cloud_run:
  service_name: simple-agent
  additional_flags:
    - --memory=512Mi
    - --cpu=0.5
    - --timeout=60s
```

### Production Agent

```yaml
description: Production customer service agent
tags: [production, customer-support]

docker:
  base_image: python:3.13-slim
  system_packages: [curl]

cloud_run:
  service_name: prod-customer-service
  additional_flags:
    - --memory=4Gi
    - --cpu=2
    - --min-instances=1
    - --max-instances=100
    - --concurrency=20
    - --timeout=1800s
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
```

### Data Processing Agent

```yaml
description: Heavy data processing pipeline
tags: [data-processing, internal]

docker:
  base_image: python:3.13-slim
  system_packages: [postgresql-client, redis-tools]

cloud_run:
  service_name: data-processor
  additional_flags:
    - --memory=8Gi
    - --cpu=4
    - --timeout=3600s
    - --max-instances=5
```

## 🔐 Environment Setup

### Global `.env` (Project Root)

```bash
# Google Cloud configuration
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# API configuration
GOOGLE_GENAI_USE_VERTEXAI="true-or-false-to-use-vertexai-here"
GOOGLE_API_KEY="your-api-key-here"

# Optional settings
ARTIFACT_BUCKET="your-bucket-name"
```

### Agent-Specific `.env.secrets`

```bash
# agents/customer_service/.env.secrets
SERVICE_ACCOUNT="customer-service-sa@project.iam.gserviceaccount.com"
SECRET_NAME="customer-service-api-key"
AGENT_ENGINE_ID="123456789"
```

### Recommended Tags

```yaml
tags:
  - development       # Development/testing agents
  - production        # Production-ready agents
  - customer-support
  - data-processing
  - internal-tool
```

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **Environment variable not found** | Check `.env` and `.env.secrets` files |
| **Secret Manager errors** | Verify secret exists and service account has access |
| **Docker build failures** | Check `requirements.txt` and base image |
| **Deployment timeouts** | Increase `--timeout` in `config.yaml` |
| **Agent Engine creation fails** | Verify Google Cloud APIs are enabled |

### Debug Commands

```bash
# Verbose deployment output
python utils/deploy_agent.py --deploy agent --verbose

# Test agent build
make test-build agent-name

# Verify Google Cloud setup
gcloud config list
```

> **🔧 Sub-module troubleshooting**: See [SUBMODULE.md](SUBMODULE.md#troubleshooting) for sub-module specific issues.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test with `make test-*` commands
4. Submit a pull request

## 📄 License

Licensed under the [MIT License](LICENSE).

Copyright (c) 2025 Alfredo Delgado