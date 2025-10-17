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

### Makefile Configuration

```makefile
AGENTS_DIR := agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
```

### Environment Variables (.env)

```bash
# Required Google Cloud settings
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# API configuration
GOOGLE_GENAI_USE_VERTEXAI="True"
GOOGLE_API_KEY="your-api-key-here"
```

## 🤖 Creating Your First Agent

```bash
# Create agent directory
mkdir agents/my-agent

# Create basic configuration
cat > agents/my-agent/config.yaml << EOF
description: My first agent
tags: [my-agent, production]

docker:
  base_image: python:3.13-slim

cloud_run:
  service_name: my-agent-service
  additional_flags:
    - --memory=1Gi
    - --cpu=0.5
    - --timeout=300s
EOF

# Create requirements.txt with shared utilities
cat > agents/my-agent/requirements.txt << EOF
google-adk
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

# Add secrets (optional)
cat > agents/my-agent/.env.secrets << EOF
SERVICE_ACCOUNT="my-agent-sa@project.iam.gserviceaccount.com"
SECRET_NAME="my-agent-api-key"
EOF

# Deploy!
make deploy my-agent
```

## 📦 Shared Utilities

The deployment engine includes a shared utilities package (`adk-shared`) for common functionality across agents.

### Key Features

- ✅ **Git-based Installation**: No local submodule management required
- ✅ **Version Control**: Pin to specific commits for reproducible builds
- ✅ **Clean Imports**: Standard Python package imports
- ✅ **Environment Management**: Automatic loading of `.env` files with priority
- ✅ **Production Ready**: Works in both development and Docker deployments

> **📚 Complete reference**: See [README.md - Shared Utilities Package](README.md#shared-utilities-package) for detailed documentation.

## 🚀 Common Commands

```bash
# Daily workflow
make list-agents                    # See your agents
make deploy my-agent               # Deploy your agent
make delete my-agent               # Delete deployment

# Testing & validation
make deploy-dry my-agent           # Test deployment (dry run)
make test-build my-agent           # Test build structure
make test-dockerfile my-agent      # Test Dockerfile generation

# Agent Engine (session management)
make create-agent-engine my-agent  # Create Vertex AI Agent Engine
make list-agent-engines my-agent   # List your agent engines

# Project setup
make enable-services               # Enable required Google Cloud APIs
```

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

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No agents found"** | Check `AGENTS_DIR` setting and `config.yaml` exists |
| **Environment variable errors** | Verify `.env` file has required variables |
| **Permission errors** | Check service account permissions and IAM roles |
| **Deployment timeouts** | Increase `--timeout` in `config.yaml` |

```bash
# Debug commands
python adk-deployment-engine/utils/deploy_agent.py --deploy my-agent --verbose
make test-build my-agent
make test-dockerfile my-agent
```

## 📚 Advanced Usage

### Custom Agents Directory

```makefile
AGENTS_DIR := my-custom-agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
```

## 🤝 Contributing

- **Issues**: Open GitHub Issues for bugs/feature requests
- **Code**: Fork repository, make changes, submit Pull Request
- **Examples**: See `adk-deployment-engine/agents-examples/` for reference

---

## 🎉 Success!

You now have:
- ✅ Private agent implementations
- ✅ Professional deployment engine
- ✅ Shared utilities package
- ✅ Automatic updates and improvements
- ✅ Same simple interface as standalone
- ✅ Full control over your code

Happy deploying! 🚀