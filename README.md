# ADK Agents Deployment Engine

Dynamic deployment system for ADK agents with per-agent configuration, Google Cloud Run integration, and comprehensive secret management.

## 📑 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🔗 As Git Sub-module](#-as-git-sub-module)
- [⚙️ Project Setup](#️-project-setup)
- [⚙️ Core Concepts](#️-core-concepts)
- [🔧 Agent Configuration](#-agent-configuration)
- [🚀 Deployment Commands](#-deployment-commands)
- [📋 Configuration Examples](#-configuration-examples)
- [🔐 Environment Setup](#-environment-setup)
- [🏷️ Agent Organization](#️-agent-organization)
- [📚 Best Practices](#-best-practices)
- [🐛 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)

---

## 🚀 Quick Start

```bash
# 1. Install project dependencies
pip install -r requirements.txt

# 2. Set up global configuration
cp .env.example .env
# Edit .env with your Google Cloud project settings

# 3. Create Agent Engine (Optional for session management, requires AGENT_ENGINE_NAME env var)
make create-agent-engine quickstart

# 4. Configure your agent
cd agents-examples/quickstart/
# Edit config.yaml and .env.secrets

# 5. Deploy your agent
make deploy quickstart
```

## 🔗 As Git Sub-module

Use this deployment engine as a sub-module in your own projects while keeping your agents private.

### Quick Setup (3 commands)

```bash
# 1. Add this repository as a sub-module
git submodule add https://github.com/your-org/adk-agents.git

# 2. Create your makefile (2 lines)
echo "include adk-agents/makefile" > makefile
echo "AGENTS_DIR := agents" >> makefile

# 3. Create your agents directory
mkdir agents
```

### Usage (identical to standalone)

```bash
# List your private agents
make list-agents

# Deploy your agents
make deploy your-agent

# All other commands work the same
make create-agent-engine your-agent
make delete your-agent
```

### Project Structure

```
your-project/
├── agents/                    # Your private agents (never shared)
│   └── your-secret-agent/
│       ├── config.yaml
│       ├── agent.py
│       ├── requirements.txt
│       └── .env.secrets
├── makefile                   # Your 2-line makefile
├── .env                       # Your environment variables
└── adk-agents/                # Sub-module (deployment engine)
```

### Getting Updates

```bash
# Get the latest deployment engine improvements
git submodule update --remote
```

### Benefits

- ✅ **Private Agents**: Your `agents/` folder stays completely private
- ✅ **Easy Collaboration**: Get improvements via sub-module updates
- ✅ **Same Interface**: Identical make commands as standalone
- ✅ **Zero Packaging**: No setup.py or PyPI publishing needed

> **💡 For detailed sub-module setup instructions**, see [SUBMODULE.md](SUBMODULE.md) for a complete getting-started guide.

## ⚙️ Project Setup

> **📋 Use this section for**: Setting up the project as a standalone repository

### Prerequisites

- Google Cloud SDK (`gcloud`)
- conda
- make
- Python 3.13+
- Docker

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd adk-agents

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set up global environment
cp .env.example .env
# Edit .env with your Google Cloud settings

# 4. Enable Google Cloud APIs
make enable-services
```

## ⚙️ Core Concepts

### Environment Variable Priority

| Priority | Source | Location | Use Case |
|----------|--------|----------|----------|
| 1 (Highest) | Google Secret Manager | `config.yaml` flags | Production secrets |
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

### Project Structure

```
adk-agents/
├── main.py                       # FastAPI application entrypoint
├── environment.yml               # Conda enviroment
├── requirements.txt              # Project dependencies
├── Dockerfile.template           # Docker template
├── makefile                      # Build helpers
├── .env.example                  # Environment template
├── .gitignore                    # Git exclusions
├── .dockerignore                 # Build exclusions
├── utils/                        # Utility scripts
│   ├── deploy_agent.py           # Deployment logic
│   └── agent_engine_manager.py  # Agent Engine creation
└── agents-examples/              # Example agent configurations
    └── {agent_name}/
        ├── config.yaml           # Agent configuration
        ├── agent.py              # Agent implementation
        ├── requirements.txt      # Agent-specific dependencies
        ├── .env.template         # Agent-specific secrets template
        └── tests/                # Agent tests
            └── test_*.py
```

## 🔧 Agent Configuration

### Complete `config.yaml` Example

```yaml
# Agent metadata
description: Customer service agent with search capabilities
tags:
  - customer-support
  - production

# Docker configuration
docker:
  base_image: python:3.13-slim
  system_packages:              # Optional system packages
    - curl
  extra_steps:                  # Optional Docker commands
    - RUN echo "Custom setup complete"

# Cloud Run configuration
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

    # Networking
    - --allow-unauthenticated
    - --session-affinity

    # Environment variables with substitution
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=GOOGLE_API_KEY=${SECRET_NAME}:latest
```

**When to use `env_vars`**:
- When you need explicit control over environment variables
- When variables don't need Secret Manager protection
- For OAuth tokens and authentication data
- When deploying with additional Docker steps that require specific environment settings

### Secret Manager Integration

Configure secrets in `config.yaml`:

```yaml
cloud_run:
  additional_flags:
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
    - --update-secrets=DB_PASSWORD=${DB_SECRET}:latest
```

**Format**: `ENV_VAR=SECRET_NAME:VERSION`
- `ENV_VAR`: Container environment variable name
- `SECRET_NAME`: Secret Manager secret name
- `VERSION`: `latest` or version number (1, 2, etc.)

### Agent Engine Management

For agents requiring session management, create a Vertex AI Agent Engine:

```bash
# Create Agent Engine (requires AGENT_ENGINE_NAME in .env)
make create-agent-engine

# Add the returned AGENT_ENGINE_ID to your .env file
echo "AGENT_ENGINE_ID=your-engine-id-here" >> .env
```

**Required Environment Variables**:
- `AGENT_ENGINE_NAME`: Display name for your Agent Engine
- `AGENT_ENGINE_ID`: (auto-generated) Used for session management

## 🚀 Deployment Commands

> **📋 Use this section for**: Reference of all available make commands and their usage

### Agent Management

```bash
# List available agents
make list

# Deploy an agent
make deploy <agent_name>

# Test deployment (dry run)
make deploy <agent_name> dry-run
```

### Service Management

```bash
# Delete a service (auto-detects service name from config.yaml)
make delete <agent-name>

# Enable required Google Cloud APIs
make enable-services
```

### Testing & Validation

```bash
# Test build directory structure
make test-build <agent_name>

# Test Dockerfile generation
make test-dockerfile <agent_name>

# Deploy with verbose logging
python deploy_agent.py --deploy <agent_name> --verbose
```

### Complete Command Reference

| Command | Purpose |
|---------|---------|
| `make list-agents` | List all available agents |
| `make deploy <agent>` | Deploy specific agent to Cloud Run |
| `make deploy-dry <agent>` | Simulate deployment without deploying |
| `make test-build <agent>` | Test build directory structure |
| `make test-dockerfile <agent>` | Test Dockerfile generation |
| `make delete <agent>` | Delete Cloud Run service (auto-detects from config.yaml) |
| `make enable-services` | Enable required Google Cloud APIs |
| `make create-agent-engine <agent>` | Create Vertex AI Agent Engine |
| `make list-agent-engines <agent>` | List agent engines for specific agent |
| `make delete-agent-engine <agent>` | Delete Vertex AI Agent Engine |

## 📋 Configuration Examples

### Basic Agent (Minimal Configuration)

```yaml
description: Simple test agent
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

### Production Agent (Full Configuration)

```yaml
description: Production customer service agent
tags: [production, customer-support]

docker:
  base_image: python:3.13-slim
  system_packages: [curl]
  extra_steps:
    - RUN apt-get update && apt-get install -y jq

cloud_run:
  service_name: prod-customer-service
  additional_flags:
    - --memory=4Gi
    - --cpu=2
    - --min-instances=1
    - --max-instances=100
    - --concurrency=20
    - --timeout=1800s
    - --session-affinity
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
```

### Data Processing Agent

```yaml
description: Data processing pipeline agent
tags: [data-processing, internal]

docker:
  base_image: python:3.13-slim
  system_packages:
    - postgresql-client
    - redis-tools
  extra_steps:
    - RUN pip install pandas sqlalchemy

cloud_run:
  service_name: data-processor
  additional_flags:
    - --memory=8Gi
    - --cpu=4
    - --timeout=3600s
    - --max-instances=5
```

### OAuth Multi-Agent

```yaml
description: Multi-agent system with Google OAuth2 authentication
tags:
  - oauth2
  - gmail
  - drive
  - filesystem
  - multi-agent

docker:
  base_image: python:3.13-slim
  system_packages:
    - curl
  extra_steps:
    - RUN npm install -g @modelcontextprotocol/server-filesystem
    - ENV OAUTH_ENABLED=true

cloud_run:
  service_name: oauth-multi-agent
  additional_flags:
    - --memory=4Gi
    - --cpu=2
    - --min-instances=1
    - --max-instances=10
    - --timeout=600s
```

## 🔐 Environment Setup

### Global `.env` (Project Root)

```bash
# Google Cloud configuration
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# API configuration
GOOGLE_GENAI_USE_VERTEXAI="True"
# OR
GOOGLE_API_KEY="your-api-key-here"

# Optional global settings
ARTIFACT_BUCKET="your-bucket-name"
```

### Agent-Specific `.env.secrets`

```bash
# agents/customer_service/.env.secrets
SERVICE_ACCOUNT="customer-service-sa@project.iam.gserviceaccount.com"
SECRET_NAME="customer-service-api-key"
DATA_STORES="customer-data-store-id"
AGENT_ENGINE_ID="123456789"
```

### OAuth Authentication Variables

```bash
# agents/oauth_multi_agent/.env.secrets
GOOGLE_CLIENT_ID="your-oauth-client-id"
GOOGLE_ACCESS_TOKEN="your-oauth-access-token"
OAUTH_ENABLED="true"
```

## 🏷️ Agent Organization

### Recommended Tags

```yaml
tags:
  # Environment
  - development       # Development/testing agents
  - staging           # Staging environment agents
  - production        # Production-ready agents

  # Function
  - customer-support
  - data-processing
  - internal-tool
  - api-service

  # Complexity
  - simple            # Basic agents with minimal config
  - advanced          # Complex agents with custom setup
```

## 📚 Best Practices

### Security
- ✅ Never commit `.env.secrets` files
- ✅ Use different service accounts per agent
- ✅ Use Secret Manager for production secrets
- ✅ Follow principle of least privilege

### Configuration
- ✅ Keep configuration in `config.yaml`, not code
- ✅ Use descriptive service names
- ✅ Set appropriate resource limits
- ✅ Use environment variables for changeable values

### Development Workflow
1. Start with basic configuration
2. Test with `make test-*` commands
3. Use dry run to verify setup
4. Deploy to staging first
5. Promote to production

## 🐛 Troubleshooting

> **📋 Use this section for**: Debugging common issues and finding solutions

### Common Issues

| Problem | Solution |
|---------|----------|
| **Environment variable not found** | Check `.env` and `.env.secrets` files |
| **Secret Manager errors** | Verify secret exists and service account has access |
| **Docker build failures** | Check `requirements.txt` and base image |
| **Deployment timeouts** | Increase `--timeout` in `config.yaml` |
| **Agent Engine creation fails** | Verify Google Cloud APIs are enabled and project is set |
| **OAuth authentication errors** | Check `GOOGLE_CLIENT_ID` and `GOOGLE_ACCESS_TOKEN` validity |
| **Service logs showing 403 errors** | Verify service account permissions and IAM roles |

> **🔧 Sub-module users**: If you're having issues with AGENTS_DIR or sub-module setup, see [SUBMODULE.md troubleshooting section](SUBMODULE.md#troubleshooting) for specific guidance.

### Debug Commands

```bash
# Verbose deployment output
python deploy_agent.py --deploy agent --verbose

# Check all agent configurations
make list

# Test specific agent build
make test-build agent-name

# View service logs in Cloud Console
# https://console.cloud.google.com/run

# Verify Google Cloud project setup
gcloud config list

# Check service account permissions
gcloud projects get-iam-policy $GOOGLE_CLOUD_PROJECT

# Test Agent Engine creation
make create-agent-engine
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test with `make test-*` commands
4. Submit a pull request

## 📄 License

Add your license information here.