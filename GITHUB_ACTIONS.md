# GitHub Actions for ADK Deployment Engine

## Objective

Create reusable GitHub Actions workflows that automatically deploy ADK agents to Google Cloud Run when code is merged to `dev`, `stag`, or `main` branches.

**Core behavior:**
- Agents deploy to environment-specific services with automatic prefixes
- `dev` branch → services prefixed with `dev-`
- `stag` branch → services prefixed with `stag-`
- `main` branch → no prefix (production)

## What This Solves

Without this, every team using the ADK deployment engine would need to:
1. Write their own GitHub Actions workflows from scratch
2. Manually configure environment-specific deployments
3. Maintain and update workflows as agents are added/removed
4. Handle service naming conventions consistently

This provides a **drop-in solution** - reference the reusable workflows and deployment just works.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  adk-deployment-engine (GitHub Repository)                   │
│                                                              │
│  .github/workflows/                                          │
│  ├── detect-changes.yml     (reusable workflow)             │
│  └── deploy.yml             (reusable workflow)             │
│                                                              │
│  utils/                                                       │
│  ├── deploy_agent.py       (Python deployment scripts)      │
│  ├── cloud_deployer.py     (Cloud Run deployment logic)     │
│  └── env_manager.py        (Environment variable handling)  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ uses
                              │
┌─────────────────────────────────────────────────────────────┐
│  Your Agent Repository (e.g., adk-agents)                    │
│                                                              │
│  .github/workflows/                                          │
│  └── ci-cd.yml            (minimal caller workflow)         │
│                                                              │
│  agents/                                                     │
│  ├── citali/                                                 │
│  ├── customer_service/                                       │
│  └── ... (more agents)                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Automatic Agent Discovery

The workflow scans your repository's `agents/` directory and finds all subdirectories containing a `config.yaml` file. You don't need to list agents anywhere.

### 2. Change Detection

When you push code or merge a PR, the workflow:
- Compares the current commit with the previous commit
- Identifies which agent directories changed
- If global files changed (deployment engine, config files), all agents are flagged

### 3. Selective Deployment

Only agents that actually changed are deployed. This saves time and prevents unnecessary service updates.

### 3.1. Deployment Modes: Full vs. Code-Only

There are two deployment modes for environment variables and secrets:

| Mode | CLI Flag | GitHub Actions Input | Behavior | Use Case |
|------|----------|---------------------|----------|----------|
| **Full Deployment** | (default) | `preserve-env: false` | Sets env vars/secrets from `.env` files | Local development, initial deployment |
| **Code-Only Mode** | `--preserve-env` | `preserve-env: true` | Skips env vars/secrets entirely | CI/CD, code-only updates |

**Full Deployment (Default)**
```bash
# Locally - requires .env and .env.secrets files
make deploy my-agent
make deploy my-agent dev
make deploy my-agent stag
```
- Uses `--set-env-vars` (sets all environment variables from `.env`)
- Uses `--clear-secrets` then `--set-secrets` (for clean slate, then set configured ones)
- Ensures configuration matches local files exactly
- **Use for**: Local development where you have `.env` and `.env.secrets` files

**Code-Only Mode (for CI/CD)**
```bash
# Locally - deploy without touching env vars/secrets
make deploy-code-only my-agent
make deploy-code-only my-agent dev

# Locally - test what code-only deployment would look like (dry run)
make deploy-code-only-dry my-agent

# GitHub Actions - .env files don't exist in repo
preserve-env: true
```
- Skips `--set-env-vars` and `--set-secrets` flags entirely
- Deploys code with existing Cloud Run env vars/secrets intact
- **Use for**: CI/CD where `.env` and `.env.secrets` are `.gitignore`'d
- **Critical for GitHub Actions**: Since `.env` files aren't in the repository, use this mode to deploy code changes without affecting the existing configuration
- **Test locally**: Use `make deploy-code-only-dry` to see the gcloud command that would run in CI/CD

**Why Code-Only Mode for CI/CD:**
- `.env` and `.env.secrets` files are in `.gitignore` (not in repository)
- GitHub Actions can't access these files
- Using `preserve-env: true` ensures code deploys without trying to set empty env vars
- Initial deployment must be done manually with `.env` files present
- Subsequent code changes can be deployed automatically via CI/CD

**Example: What gets deployed**

**Local Full Deployment (`make deploy my-agent`):**
```bash
gcloud run deploy my-agent-service \
  --source . \
  --region us-central1 \
  --project myproject \
  --clear-secrets \
  --set-secrets=API_KEY=projects/.../secrets/api-key:latest,DB_PASSWORD=projects/.../secrets/db-password:latest \
  --set-env-vars='GOOGLE_CLOUD_PROJECT=myproject,GOOGLE_CLOUD_LOCATION=us-central1,DEBUG=true'
```
- ✅ Sets env vars from `.env` file
- ✅ Sets secrets from `.env.secrets` file
- ✅ Ensures service matches local configuration exactly

**CI/CD Code-Only Deployment (`preserve-env: true`):**
```bash
gcloud run deploy my-agent-service \
  --source . \
  --region us-central1 \
  --project myproject
```
- ❌ NO `--set-env-vars` flag (preserves existing Cloud Run env vars)
- ❌ NO `--set-secrets` flag (preserves existing Cloud Run secrets)
- ❌ NO `--clear-secrets` flag (preserves existing Cloud Run secrets)
- ✅ Only deploys code changes, keeps all existing configuration intact

### 4. Automatic Service Naming

Based on the target branch, services are named automatically:

| Branch | Service Name Pattern | Example |
|--------|---------------------|---------|
| `dev` | `dev-{service-name}` | `dev-citali-service` |
| `stag` | `stag-{service-name}` | `stag-citali-service` |
| `main` | `{service-name}` | `citali-service` |

The `service-name` is read from each agent's `config.yaml` file.

### 5. Environment Isolation

Each branch deploys to services with environment-specific prefixes:

| Branch | Prefix | Service Name Pattern |
|--------|--------|---------------------|
| `dev` | `dev-` | `dev-{service_name}` |
| `stag` | `stag-` | `stag-{service_name}` |
| `main` | (none) | `{service_name}` |

---

## Reusable Workflow Specifications

### Workflow 1: `detect-changes.yml`

**Trigger:** Called by consuming repository's workflow

**Purpose:** Determine which agents need to be deployed

**Inputs:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `agents-dir` | string | No | `agents` | Directory containing agent configurations |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| `agents-to-deploy` | string | JSON array of agent names that changed |
| `should-deploy-all` | boolean | `true` if all agents should deploy (global changes detected) |

**Logic:**
```yaml
1. Checkout repository code
2. Scan agents-dir for all directories containing config.yaml
3. Use git diff to find changed files since last commit
4. Categorize changes:
   - If agents/{agent}/** changed → add that agent to list
   - If global files changed → set should-deploy-all = true
5. Output results
```

**Global files that trigger full deployment:**
- `.env`
- `requirements.txt`
- `environment.yml`
- `Makefile`
- Any changes in the deployment engine (if using as submodule)

---

### Workflow 2: `deploy.yml`

**Trigger:** Called by consuming repository's workflow after `detect-changes`

**Purpose:** Deploy specified agents to Google Cloud Run

**Inputs:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `agents-dir` | string | No | `agents` | Directory containing agent configurations |
| `agents-to-deploy` | string | Yes | - | JSON array of agent names to deploy |
| `should-deploy-all` | boolean | No | `false` | If true, deploy all agents |
| `branch-name` | string | Yes | - | Name of branch being deployed (`dev`, `stag`, or `main`) |
| `preserve-env` | boolean | No | `true` | Skip --set-env-vars and --set-secrets (use for CI/CD where .env files are gitignored) |

**Secrets Required:**
| Name | Description |
|------|-------------|
| `GCP_SA_KEY` | Google Cloud service account key (JSON format) |

**Logic:**
```yaml
1. Checkout repository code (with submodules)
2. Authenticate to Google Cloud using GCP_SA_KEY
3. Determine environment based on branch-name:
   - dev → prefix="dev-", environment="dev"
   - stag → prefix="stag-", environment="stag"
   - main → prefix="", environment="prod"
4. For each agent to deploy:
   a. Read agents/{agent}/config.yaml
   b. Extract gcp_project and gcp_location from cloud_run section
   c. Extract service_name from config
   d. Apply prefix to service name
   e. Set environment variables:
      - ENVIRONMENT=dev/stag/prod
      - GOOGLE_CLOUD_PROJECT={gcp_project from config}
      - GOOGLE_CLOUD_LOCATION={gcp_location from config}
      - GOOGLE_CLOUD_LOCATION_DEPLOY={gcp_location from config}
      - AGENTS_DIR={agents-dir input}
   f. Run: `make deploy-code-only {agent} {environment}` or `make deploy {agent} {environment}`
5. Report deployment results
```

**Matrix Strategy:**
Deploy multiple agents in parallel using GitHub Actions matrix for faster deployments.

**Using Make Commands:**
The workflow uses the same `make` commands that work locally:
- `make deploy-code-only {agent} {environment}` - Code-only deployment (default for CI/CD)
- `make deploy {agent} {environment}` - Full deployment with env vars/secrets

This ensures **DRY principle** and **consistency** - what you test locally (`make deploy-code-only-dry my-agent`) is exactly what runs in CI/CD.

---

## Deployment Engine Requirements

The Python deployment scripts need to support environment variables passed by the workflow.

### Environment Variables (Set by Workflow)

| Variable | Example | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `dev`, `stag`, or `prod` | Target environment |
| `GOOGLE_CLOUD_PROJECT` | `myproject` | GCP project for this deployment |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | GCP region |
| `GOOGLE_CLOUD_LOCATION_DEPLOY` | `us-central1` | GCP deployment region |
| `AGENTS_DIR` | `agents` | Directory containing agent configurations |

### Required Code Changes

**File: `utils/cloud_deployer.py`**

When deploying to Cloud Run, the service name is constructed from CLI flags:

```python
# In deploy_agent.py - handle_deployment()
if args.dev:
    environment = "dev"
    service_prefix = "dev-"
elif args.stag:
    environment = "stag"
    service_prefix = "stag-"
else:
    environment = "prod"
    service_prefix = ""

# Pass to cloud_deployer
service_name = f"{service_prefix}{base_service_name}"
```

**Example:**
- `base_service_name = "citali-service"` (from config.yaml)
- `python utils/deploy_agent.py --deploy citali --dev` → `dev-citali-service`
- `python utils/deploy_agent.py --deploy citali --stag` → `stag-citali-service`
- `python utils/deploy_agent.py --deploy citali` → `citali-service`

**File: `utils/deploy_agent.py`**

The deployment script should:
1. Read `GOOGLE_CLOUD_PROJECT` from environment variable
2. Read `GOOGLE_CLOUD_LOCATION` from environment variable
3. Pass `SERVICE_PREFIX` (or the prefixed service name) to cloud deployer

**No need for:**
- Complex environment-specific configuration files
- Multiple config.yaml variants
- Manual service naming logic in Python

The workflow handles all environment-specific logic. The Python scripts just use the environment variables that are set.

---

## Consuming Repository Setup

### Step 1: Create GitHub Secrets

In your repository settings (Settings → Secrets and variables → Actions), add:

| Secret | Example Value | Required For |
|--------|---------------|--------------|
| `GCP_SA_KEY` | `{"type": "service_account", ...}` | All branches |

### Step 2: Create Caller Workflow

Create `.github/workflows/ci-cd.yml` in your repository:

```yaml
name: CI/CD

on:
  pull_request:
    types: [closed]
    branches: [dev, stag, main]
  push:
    branches: [dev, stag, main]

permissions:
  contents: read
  pull-requests: read

jobs:
  detect:
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/detect-changes.yml@main
    with:
      agents-dir: 'agents'

  deploy:
    needs: detect
    # Only run on merge or direct push
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.pull_request.merged == true)
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/deploy.yml@main
    with:
      agents-dir: 'agents'
      agents-to-deploy: ${{ needs.detect.outputs.agents-to-deploy }}
      should-deploy-all: ${{ needs.detect.outputs.should-deploy-all }}
      branch-name: ${{ github.ref_name }}
    secrets:
      GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}
```

### Step 3: Configure Branch Protection (Recommended)

For each protected branch (`dev`, `stag`, `main`):

1. Go to repository Settings → Branches
2. Add or edit branch protection rule
3. Enable:
   - ✓ Require pull request reviews before merging
   - ✓ Require status checks to pass before merging
   - ✓ Require branches to be up to date before merging

**Required status checks:** `detect`, `deploy`

---

## Agent Configuration

Each agent must have a `config.yaml` file in its directory:

```yaml
# agents/my-agent/config.yaml
description: "My agent description"
tags: [tag1, tag2]

docker:
  base_image: python:3.13-slim
  system_packages: []

cloud_run:
  service_name: my-agent-service  # ← Base service name
  gcp_project: my-project-id       # ← Required for GitHub Actions
  gcp_location: us-central1        # ← Required for GitHub Actions
  additional_flags:
    - --memory=2Gi
    - --cpu=1
```

**Key points:**
- The `service_name` is the base name (required)
- `gcp_project` and `gcp_location` in `cloud_run` section are required for GitHub Actions
- No prefix configuration needed in config
- Prefix is controlled via CLI flags: `--dev`, `--stag`, or no flag (production)

**Example deployments:**
- Dev via CLI: `--deploy my-agent --dev` → `dev-my-agent-service`
- Stag via CLI: `--deploy my-agent --stag` → `stag-my-agent-service`
- Prod via CLI: `--deploy my-agent` → `my-agent-service`
- Dev via GitHub Actions: PR to dev branch → `dev-my-agent-service`

---

## Example Workflow

### Scenario: Developer Updates the Citali Agent

```bash
# 1. Developer creates feature branch
git checkout -b feature/update-citali-calendar

# 2. Makes changes to citali agent
vim agents/citali/agent.py

# 3. Commits and pushes
git add agents/citali/agent.py
git commit -m "Update calendar integration"
git push origin feature/update-citali

# 4. Creates PR to dev branch in GitHub

# 5. GitHub Actions automatically runs:
#    - detect-changes: Finds that citali changed
#    - (no deployment yet, waiting for merge)

# 6. Developer merges PR to dev

# 7. GitHub Actions runs:
#    - detect-changes: Confirms citali changed
#    - deploy:
#      - Reads config.yaml → service_name = "citali-service"
#      - Branch = dev → uses --dev flag
#      - Project = GCP_PROJECT
#      - Deploys to: "dev-citali-service"

# 8. To promote to staging:
#    - Create PR from dev to stag
#    - Merge PR
#    - Deploys to: "stag-citali-service" in staging project

# 9. To promote to production:
#    - Create PR from stag to main
#    - Merge PR
#    - Deploys to: "citali-service" in production project
```

---

## Adding a New Agent

With these workflows in place, adding a new agent is simple:

```bash
# 1. Create the agent directory
mkdir agents/new-agent

# 2. Create config.yaml
cat > agents/new-agent/config.yaml << EOF
description: "New agent"
tags: [new]

docker:
  base_image: python:3.13-slim

cloud_run:
  service_name: new-agent-service
  gcp_project: my-project-id
  gcp_location: us-central1
  additional_flags:
    - --memory=1Gi
EOF

# 3. Create agent.py and other files
# ... implement agent ...

# 4. Commit and create PR
git add agents/new-agent
git commit -m "Add new agent"
git push origin feature/add-new-agent

# 5. Create PR to dev

# 6. When merged, GitHub Actions automatically:
#    - Detects the new agent directory
#    - Deploys to dev-new-agent-service
```

**No workflow file editing required.**

---

## Service Naming Summary

| Branch | Prefix | Base Service Name | Final Service Name |
|--------|--------|-------------------|-------------------|
| `dev` | `dev-` | `citali-service` | `dev-citali-service` |
| `dev` | `dev-` | `customer-service` | `dev-customer-service` |
| `stag` | `stag-` | `citali-service` | `stag-citali-service` |
| `stag` | `stag-` | `customer-service` | `stag-customer-service` |
| `main` | (none) | `citali-service` | `citali-service` |
| `main` | (none) | `customer-service` | `customer-service` |

---

## Troubleshooting

### Issue: Agent not deploying after merge

**Check:**
1. Does `agents/{agent}/config.yaml` exist?
2. Does the config.yaml have a `service_name` under `cloud_run`?
3. Were the GitHub secrets (GCP_PROJECT, GCP_LOCATION, GCP_SA_KEY) configured?
4. Check the Actions log for the detect-changes job

### Issue: Wrong service name deployed

**Check:**
1. Verify the branch name (must be exactly `dev`, `stag`, or `main`)
2. Check that `SERVICE_PREFIX` environment variable is set correctly in the workflow
3. Verify `cloud_deployer.py` is using the prefix

### Issue: All agents deploying when only one changed

**Check:**
1. Did you modify a global file? (`.env`, `requirements.txt`, `Makefile`, deployment engine files)
2. These trigger full deployment by design

---

## Implementation Checklist

### Phase 1: Deployment Engine ✅
- [x] Add `--dev` and `--stag` CLI flags to `deploy_agent.py`
- [x] Pass service prefix from CLI flags to `cloud_deployer.py`
- [x] Add `--preserve-env` flag to `deploy_agent.py` for selective env var updates
- [x] Update `utils/deploy_agent.py` to read `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` from environment
- [x] Test local deployment with CLI flag prefixes
- [x] Test that service names get prefixes correctly

### Phase 2: Reusable Workflows ✅
- [x] Create `.github/workflows/detect-changes.yml`
  - [x] Implement agent directory scanning
  - [x] Implement change detection logic
  - [x] Output agents-to-deploy as JSON
  - [x] Handle global change detection
- [x] Create `.github/workflows/deploy.yml`
  - [x] Implement branch-to-environment mapping
  - [x] Use --dev/--stag CLI flags based on branch
  - [x] Set environment variables for Python scripts
  - [x] Implement matrix deployment
  - [x] Add deployment summary

### Phase 3: Testing
- [ ] Create test repository
- [ ] Add multiple agents
- [ ] Test dev branch deployment (prefix: dev-)
- [ ] Test stag branch deployment (prefix: stag-)
- [ ] Test main branch deployment (no prefix)
- [ ] Test selective deployment (only changed agents)
- [ ] Test global change (all agents deploy)
- [ ] Test new agent detection

### Phase 4: Documentation
- [ ] Update README.md with reusable workflows section
- [ ] Add example consumer workflow
- [ ] Document required secrets
- [ ] Document service naming convention

---

## Success Criteria

✅ **New agent automatically detected** when directory with `config.yaml` is added

✅ **Service naming works correctly:**
- Dev branch: `dev-{service-name}`
- Stag branch: `stag-{service-name}`
- Main branch: `{service-name}`

✅ **Only changed agents deploy** (unless global changes)

✅ **Different projects per environment** (dev/stag/prod)

✅ **Zero workflow configuration** when adding/removing agents

✅ **Works for any repository** using the deployment engine

---

## Notes for Implementation

- Use `actions/checkout@v4` with `submodules: recursive` since deployment engine may be a submodule
- Use `dorny/paths-filter@v3` for efficient change detection
- Use `matrix.strategy` with `fail-fast: false` for parallel deployments
- Environment variable `SERVICE_PREFIX` should be empty string for main branch, not `"null"` or omitted
- The `service_name` from `config.yaml` is used as-is; don't add any suffixes like `-service`
- All environment variables (`ENVIRONMENT`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `SERVICE_PREFIX`) must be exported before calling Python scripts
- Use `GITHUB_STEP_SUMMARY` for human-readable deployment results
