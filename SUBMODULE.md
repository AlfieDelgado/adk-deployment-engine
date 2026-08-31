# Using ADK Agents as Git Sub-module

> **🎯 Purpose**: Quick start guide for using ADK Agents as a sub-module in your projects while keeping your agents completely private.
>
> **📚 Complete Reference**: See [README.md](README.md) for full documentation and advanced configuration options.

## ⚡ 5-Minute Setup

```bash
# 1. Add ADK deployment engine as a sub-module
git submodule add https://github.com/AlfieDelgado/adk-deployment-engine.git

# 2. Create your project makefile (single command)
cat > makefile << 'EOF'
AGENTS_DIR := agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
EOF

# 3. Set up your project environment
cp adk-deployment-engine/.env.example .env
# Edit .env with your Google Cloud project settings
mkdir agents

# 4. Create your first agent (see below)

# 5. Deploy your agent!
make deploy your-agent
```
> **🎯 That's it!** You now have a complete ADK deployment system using the sub-module. See sections below for agent creation and shared utilities.

## 📁 Your Project Structure

```
your-project/                         # Your main project (private)
├── agents/                           # Your private agents (never shared)
│   └── my-secret-agent/
│       ├── config.yaml               # Your agent configuration
│       ├── agent.py                  # Your agent code
│       ├── requirements.txt          # Your dependencies (include adk-shared)
│       └── .env.secrets              # Your secrets (never committed)
├── makefile                          # Your 3-line makefile
├── .env                              # Your environment variables
└── adk-deployment-engine/            # Sub-module (deployment engine only)
    ├── shared/                       # Shared utilities package
    └── agents-examples/              # Example agents (for reference)
```

### Configuration

**Makefile:**
```makefile
AGENTS_DIR := agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
```

### Environment Variables (.env)

```bash
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# API Configuration (choose one):
# Option 1: Enterprise auth mode (set GOOGLE_GENAI_USE_ENTERPRISE=true)
# Option 2: Gemini Developer API mode (set GOOGLE_GENAI_USE_ENTERPRISE=false and provide GOOGLE_API_KEY)
# Note: GOOGLE_GENAI_USE_VERTEXAI is a deprecated alias that is still honored as a fallback
GOOGLE_GENAI_USE_ENTERPRISE="false"
GOOGLE_API_KEY="your-api-key-here"
```

## 🤖 Creating Your First Agent

```bash
# Create agent directory
mkdir agents/my-agent

# Create config.yaml
cat > agents/my-agent/config.yaml << EOF
description: My first agent
tags: [my-agent, production]

docker:
  base_image: python:3.13-slim

cloud_run:
  service_name: my-agent-service
  gcp_project: my-project-id
  gcp_location: us-central1
  additional_flags:
    - --memory=1Gi
    - --cpu=0.5
EOF

# Create requirements.txt with shared utilities
cat > agents/my-agent/requirements.txt << EOF
google-adk==2.8.0
adk-shared @ git+https://github.com/AlfieDelgado/adk-deployment-engine.git@main#subdirectory=shared
EOF

# Create agent code with shared utilities
cat > agents/my-agent/agent.py << EOF
from google.adk.agents import LlmAgent
from adk_shared.helpers import load_env_vars

# Load environment variables automatically
load_env_vars()

my_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    instruction="You are a helpful assistant.",
    name="MyAgent",
)
EOF

# Deploy
make deploy my-agent
```

## 📦 Shared Utilities

The deployment engine includes `adk-shared` for common functionality (env management, helpers).

```bash
# Add to requirements.txt
adk-shared @ git+https://github.com/AlfieDelgado/adk-deployment-engine.git@main#subdirectory=shared
```

> **📚 Complete documentation**: See [README.md - Shared Utilities Package](README.md#shared-utilities-package)

## 🤖 Setting Up GitHub Actions

> **📚 Complete setup guide**: See [.github/workflows/CI_CD.md](.github/workflows/CI_CD.md) for step-by-step GitHub Actions instructions.

### Quick Summary

When using this repo as a submodule, you can use the reusable GitHub Actions workflows for automatic deployments.

**Basic steps:**
1. Create `GCP_SA_KEY` secret in your GitHub repository
2. Copy `.github/workflows/ci-cd.yml` from the submodule as an example
3. Remove or comment out the `if: vars.ENABLE_CI_CD == 'true'` condition (this only applies to the adk-deployment-engine repo)
4. Set `AGENTS_DIR` in your Makefile (or optionally as a GitHub variable to override)
5. Change workflow references to point to your org (e.g., `AlfieDelgado/adk-deployment-engine/.github/workflows/@main`)

**Each agent's `config.yaml` must include:**
```yaml
cloud_run:
  service_name: my-agent-service
  gcp_project: my-project-id      # Required for GitHub Actions
  gcp_location: us-central1       # Required for GitHub Actions
```

See [.github/workflows/CI_CD.md](.github/workflows/CI_CD.md) for complete instructions.

## 🔄 Updates & Maintenance

```bash
# Get latest deployment engine improvements
git submodule update --remote --merge

# Update to latest and sync
git pull origin main
git submodule update --init --recursive
```

## 🎯 Best Practices

### Security
- ✅ Never commit `.env.secrets` files
- ✅ Use different service accounts per agent
- ✅ Use Secret Manager for production secrets
- ✅ Follow principle of least privilege

### Development
- ✅ Use `make deploy-dry` to test before deploying
- ✅ Keep `agents/` directory in `.gitignore`
- ✅ Use descriptive service names

## 📚 Advanced Usage

### Custom Agents Directory

**Via Makefile (recommended):**
```makefile
AGENTS_DIR := my-custom-agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
```

**Via GitHub Variable (optional override):**
- Set `AGENTS_DIR` in: Settings → Secrets and variables → Actions → Variables
- Use this for per-environment overrides without modifying Makefile
- The workflow auto-detects from Makefile first, then checks the GitHub variable

## 🤝 Contributing

- **Issues**: Open GitHub Issues for bugs/feature requests
- **Code**: Fork repository, make changes, submit Pull Request
- **Examples**: See `adk-deployment-engine/agents-examples/` for reference
