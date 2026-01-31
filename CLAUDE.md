# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ADK Agents Deployment Engine is a dynamic deployment system for Google ADK (Agent Development Kit) agents. It provides per-agent configuration via YAML, automated Google Cloud Run deployment, and comprehensive secret management through Google Secret Manager.

**Core Runtime**: `main.py` - FastAPI app using Google ADK CLI, supports Vertex AI Agent Engine or SQLite for sessions.

## Commands

### Setup
```bash
# Enable required Google Cloud APIs
make enable-services

# List available agents
make list-agents
```

### Deployment
```bash
# Full deployment (sets env vars/secrets from .env files)
make deploy <agent>              # Production (no prefix)
make deploy <agent> dev          # Dev environment (dev-{service} prefix)
make deploy <agent> stag         # Staging environment (stag-{service} prefix)

# Code-only deployment (preserves existing env vars/secrets - for CI/CD)
make deploy-code-only <agent>
make deploy-code-only <agent> dev
make deploy-code-only <agent> stag
```

### Testing & Debugging
```bash
# Dry-run deployments (simulate without executing)
make deploy-dry <agent>
make deploy-code-only-dry <agent>

# Test individual components
make test-build <agent>          # Test build directory structure
make test-dockerfile <agent>     # Test Dockerfile generation
```

### Agent Engine Management
```bash
make create-agent-engine <agent>   # Create Vertex AI Agent Engine (requires AGENT_ENGINE_NAME env var)
make list-agent-engines <agent>    # List agent engines for specific agent
make delete-agent-engine <agent>   # Delete agent engine
```

### Utility
```bash
make delete <agent>  # Delete Cloud Run service (reads service_name from config.yaml)
```

### Python CLI (Alternative to Make)
```bash
python utils/deploy_agent.py --deploy <agent> [--dev|--stag] [--dry-run] [--preserve-env] [--verbose]
python utils/deploy_agent.py --list
python utils/deploy_agent.py test build <agent>
python utils/deploy_agent.py test dockerfile <agent>
python utils/agent_engine_manager.py <agent> [--list|--delete]
```

## Architecture

### Directory Structure
```
adk-deployment-engine/
├── main.py                      # FastAPI agent runtime (uses Google ADK)
├── makefile                     # CLI deployment interface
├── requirements.txt             # Python dependencies
├── environment.yml              # Conda environment
├── agents-examples/             # Example agents
│   └── quickstart/
├── shared/                      # Shared utilities package (adk-shared)
│   ├── setup.py
│   └── adk_shared/helpers.py
└── utils/                       # Deployment utilities
    ├── deploy_agent.py          # Main orchestrator
    ├── cloud_deployer.py        # Google Cloud Run deployment
    ├── docker_builder.py        # Dockerfile generation
    ├── env_manager.py           # Environment variable handling
    ├── agent_engine_manager.py  # Vertex AI Agent Engine ops
    ├── makefile_helper.py       # Makefile utilities
    └── testing_utils.py         # Testing helpers
```

### Deployment Flow

1. **Config Loading**: `config.yaml` loaded from `agents/{agent}/`
2. **Environment Variables**: 3-tier priority system (Secret Manager → `.env.secrets` → global `.env`)
3. **Build Preparation**: Create isolated build directory with generated Dockerfile
4. **Cloud Run Deploy**: Execute `gcloud run deploy` with flags from config

### Environment Variable Priority

| Priority | Source | Location |
|----------|--------|----------|
| 1 (Highest) | Google Secret Manager | `agents/{agent}/config.yaml` `--update-secrets` flags |
| 2 (Medium) | Agent-specific secrets | `agents/{agent}/.env.secrets` |
| 3 (Lowest) | Global environment | Project root `.env` |

### Variable Syntax

Use shell-style `${VAR_NAME}` syntax in `config.yaml` for substitution:
```yaml
cloud_run:
  additional_flags:
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
```

## Submodule Usage

This project can be used as a git submodule. Two key environment variables control module resolution:

- **`AGENTS_DIR`**: Override agents directory (default: `agents`)
- **`DEPLOYMENT_ENGINE_DIR`**: Path to deployment engine (default: `.`)

When using as submodule, create a wrapper makefile:
```makefile
AGENTS_DIR := agents
DEPLOYMENT_ENGINE_DIR := adk-deployment-engine
include adk-deployment-engine/makefile
```

## Agent Configuration

Each agent has a `config.yaml` with per-agent settings:

```yaml
description: Agent description
tags: [production, customer-support]

docker:
  base_image: python:3.13-slim
  system_packages: [curl]  # Optional

cloud_run:
  service_name: my-agent
  gcp_project: my-project-id     # Required for GitHub Actions
  gcp_location: us-central1      # Required for GitHub Actions
  additional_flags:
    - --memory=2Gi
    - --cpu=1
    - --timeout=600s
    - --min-instances=0
    - --max-instances=10
    - --service-account=${SERVICE_ACCOUNT}
    - --update-secrets=API_KEY=${SECRET_NAME}:latest
```

## GitHub Actions CI/CD

The deployment engine includes reusable workflows:
- `detect-changes.yml` - Detects which agents changed
- `deploy.yml` - Reusable deployment workflow

Users create a caller workflow (see `.github/workflows/CI_CD.md`) that:
1. Runs on push/PR merge to `dev`, `stag`, `main`
2. Uses `--code-only` deployment to preserve env vars
3. Requires `GCP_SA_KEY` secret with proper IAM roles

**Note**: CI/CD is disabled in this repo by default (controlled by `ENABLE_CI_CD` variable).

## Git Workflow

| Branch | Purpose | Environment |
|--------|---------|-------------|
| `main` | Production-ready code | Production |
| `dev` | Integration testing | Development |
| `stag` | Pre-production staging | Staging |
| `feat/*` | Feature development | - |
| `fix/*` | Bug fixes | - |

**Merging**: Rebase and merge only (enforced via branch protection)

**PR Approval**: Required for `main`, `dev`, `stag` (see `.github/CODEOWNERS`)

**Conventional Commits**: Use `feat:`, `fix:`, `docs:`, `chore:`, etc.

## Key Environment Variables

### Global (.env)
- `GOOGLE_CLOUD_PROJECT` - Google Cloud project ID (required)
- `GOOGLE_CLOUD_LOCATION` - Default GCP region (required)
- `GOOGLE_CLOUD_LOCATION_DEPLOY` - Deployment region (optional, falls back to `GOOGLE_CLOUD_LOCATION`)
- `GOOGLE_GENAI_USE_VERTEXAI` - Auth mode: `true` for Vertex AI, `false` for Gemini API
- `GOOGLE_API_KEY` - API key (when `GOOGLE_GENAI_USE_VERTEXAI=false`)
- `ARTIFACT_BUCKET` - GCS bucket for artifacts (optional)

### Agent-Specific (.env.secrets)
- `AGENT_ENGINE_ID` - Vertex AI Agent Engine ID (for session management)
- `SERVICE_ACCOUNT` - Cloud Run service account email
- `SECRET_NAME` - Google Secret Manager secret name

### Agent Engine Creation
- `AGENT_ENGINE_NAME` - Display name for the Agent Engine (required when running `make create-agent-engine`)

## Important Notes

1. **Never log environment variable values** - Use variable names only in logs
2. **Docker base image**: Defaults to `python:3.13-slim`
3. **Service naming**: `{prefix}{service_name}` where prefix is `dev-`, `stag-`, or empty
4. **First deployment**: Must be done manually with `make deploy <agent>` before CI/CD can use `--code-only`
5. **Secret Manager format**: `ENV_VAR=SECRET_NAME:VERSION` in `--update-secrets` flags
