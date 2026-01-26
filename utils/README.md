# Utils Folder - ADK Agents Deployment Utilities

This folder contains utility scripts that support the ADK Agents deployment system.

## 📁 Overview

```
utils/
├── README.md                    # This documentation
├── deploy_agent.py             # Main deployment engine
├── create_agent_engine.py      # Vertex AI Agent Engine creator
├── makefile_helper.py          # Makefile utility for delete operations
├── env_manager.py              # Environment management module
├── docker_builder.py           # Docker and build operations
├── cloud_deployer.py           # Cloud Run deployment module
└── testing_utils.py            # Testing utilities
```

**Note**: For general usage and configuration, see the main project README.

## 🚀 deploy_agent.py

The main deployment script that handles:
- Dynamic agent configuration loading
- Environment variable processing with 3-tier priority
- Secret Manager integration for secure deployments
- Dockerfile generation from templates
- Google Cloud Run deployment with proper flag handling
- Environment-specific deployments (dev/stag/prod)
- Code-only deployment mode for CI/CD

### Core Capabilities

- **Configuration Processing**: Loads and validates per-agent `config.yaml` files
- **Environment Management**: 3-tier priority system (global `.env` → agent `.env.secrets` → substitution)
- **Secret Manager Integration**: Handles `--clear-secrets` then `--set-secrets` for clean deployments
- **Docker Build System**: Creates isolated build environments with generated Dockerfiles
- **Cloud Run Deployment**: Executes `gcloud run deploy` with all required flags

### Testing

- `make test-build <agent>` - Validates file copying and build setup
- `make test-dockerfile <agent>` - Tests Dockerfile creation without deployment
- `make deploy-dry <agent>` - Simulates complete deployment process

### CLI Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--deploy <agent>` | Deploy an agent | `--deploy my-agent` |
| `--dev` | Deploy to dev environment (adds 'dev-' prefix) | `--deploy my-agent --dev` |
| `--stag` | Deploy to staging environment (adds 'stag-' prefix) | `--deploy my-agent --stag` |
| `--preserve-env` | Skip env vars/secrets (code-only mode) | `--deploy my-agent --preserve-env` |
| `--dry-run` | Simulate deployment without executing | `--deploy my-agent --dry-run` |
| `--list` | List all available agents | `--list` |
| `--verbose` | Enable detailed logging | `--deploy my-agent --verbose` |

**Environment flags are mutually exclusive:** `--dev` and `--stag` cannot be used together.

### Deployment Modes

**Full Deployment (Default)** - Sets env vars/secrets from `.env` files:
```bash
python utils/deploy_agent.py --deploy my-agent
python utils/deploy_agent.py --deploy my-agent --dev
```

**Code-Only Deployment** - Preserves existing Cloud Run env vars/secrets:
```bash
python utils/deploy_agent.py --deploy my-agent --preserve-env
```

**Use case:** CI/CD where `.env` files are gitignored.

## 🤖 create_agent_engine.py

Vertex AI Agent Engine management module with per-agent configuration support.

### Features

- Per-agent configuration via `.env.secrets` files
- Duplicate prevention (checks existing engines)
- Engine listing (all agents or specific agent)
- Engine deletion with confirmation
- Environment priority fallback (agent → global)

### Usage

```bash
# Create agent engine (uses agents/{agent}/.env.secrets)
make create-agent-engine <agent_name>

# List agent engines for specific agent
make list-agent-engines <agent_name>

# List all agent engines (project-wide view)
python utils/create_agent_engine.py --list

# Delete agent engine for specific agent
make delete-agent-engine <agent_name>

# Direct usage with agent name
python utils/create_agent_engine.py <agent_name>
python utils/create_agent_engine.py <agent_name> --list
python utils/create_agent_engine.py <agent_name> --delete
```

## 🗑️ makefile_helper.py

Utility script for makefile operations with intelligent service management.

### Key Features

- **Auto-Detection**: Reads service names from agent `config.yaml` files
- **Environment Loading**: Uses agent-specific environment variables
- **Error Handling**: Comprehensive validation and helpful error messages
- **Clean Integration**: Simple interface for makefile commands

### Usage

```bash
# Delete Cloud Run service with auto-detected service name
make delete customer_service  # Deletes "customer-service-agent" from config.yaml
```

## 🔗 Integration with Makefile

```makefile
make deploy agent           →   python utils/deploy_agent.py --deploy agent
make deploy-dry agent       →   python utils/deploy_agent.py --deploy agent --dry-run
make test-build agent       →   python utils/deploy_agent.py test build agent
make test-dockerfile agent  →   python utils/deploy_agent.py test dockerfile agent
make create-agent-engine    →   python utils/create_agent_engine.py agent
make delete agent           →   python utils/makefile_helper.py delete agent
```

## 📊 Environment Variables

### Variable Priority System

1. **Global `.env`** (Lowest) - Project-wide defaults
2. **Agent `.env.secrets`** (Medium) - Agent-specific configuration
3. **Config substitution** (Highest) - Shell-style `${VAR}` in `config.yaml`

### Required Variables

**All operations:**
- `GOOGLE_CLOUD_PROJECT` - Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION` - Google Cloud region

**Agent Engine creation:**
- `AGENT_ENGINE_NAME` - Display name for the Agent Engine

**Agent-specific (from `.env.secrets`):**
- `SERVICE_ACCOUNT` - Service account for Cloud Run deployment
- `SECRET_NAME` - Secret Manager secret name
- Other agent-specific configuration variables
