# GitHub Actions CI/CD Setup

Automatically deploy ADK agents to Cloud Run when code merges to `dev`, `stag`, or `main`.

> **Note for adk-deployment-engine repo**: This workflow is disabled by default. To enable CI/CD for testing `agents-examples`, set these repository variables (Settings → Secrets and variables → Actions → Variables):
> - `ENABLE_CI_CD` = `true`
> - `AGENTS_DIR` = `agents-examples`

---

## Quick Setup (3 Steps)

### 1. Add GitHub Secret

**Settings → Secrets and variables → Actions → New repository secret**

Name: `GCP_SA_KEY`
Value: Your service account JSON with the following IAM roles:

| Role | Level | Purpose |
|------|-------|---------|
| `roles/run.sourceDeveloper` | Project | Deploys service & manages build artifacts |
| `roles/serviceusage.serviceUsageConsumer` | Project | Permission to call required Google APIs |
| `roles/logging.logWriter` | Project | Write build/deployment logs |
| `roles/iam.serviceAccountUser` | Resource | Act as the Cloud Run runtime SA |

```bash
# Commands to grant the required roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/run.sourceDeveloper"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/serviceusage.serviceUsageConsumer"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/logging.logWriter"

gcloud iam service-accounts add-iam-policy-binding \
  PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --member="serviceAccount:YOUR_SA_EMAIL" \
  --role="roles/iam.serviceAccountUser" \
  --project=PROJECT_ID
```

### 2. Configure Each Agent

Each agent's `config.yaml` must have:

```yaml
cloud_run:
  service_name: my-agent-service
  gcp_project: my-project-id     # Required for GitHub Actions
  gcp_location: us-central1      # Required for GitHub Actions
```

### 3. Create Caller Workflow

Copy the example workflow from adk-deployment-engine and customize:

```bash
# From your repo (using adk-deployment-engine as submodule)
cp adk-deployment-engine/.github/workflows/ci-cd.yml .github/workflows/ci-cd.yml
```

**Edit `.github/workflows/ci-cd.yml`:**

**If using adk-deployment-engine as a submodule:**

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
    # if: vars.ENABLE_CI_CD == 'true'  ← Remove this line
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/detect-changes.yml@main
    with:
      agents-dir: ${{ vars.AGENTS_DIR || '' }}  # Auto-detects from Makefile, defaults to 'agents'

  deploy:
    needs: detect
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.pull_request.merged == true)
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/deploy.yml@main
    with:
      agents-dir: ${{ vars.AGENTS_DIR || '' }}  # Auto-detects from Makefile, defaults to 'agents'
      agents-to-deploy: ${{ needs.detect.outputs.agents-to-deploy }}
      branch-name: ${{ github.ref_name }}
    secrets:
      GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}
```

Replace `AlfieDelgado` with your GitHub org/username if you forked the repo.

**Important**: Remove or comment out the `if: vars.ENABLE_CI_CD == 'true'` conditions (this only applies to the adk-deployment-engine repo).

```yaml
jobs:
  detect:
    # if: vars.ENABLE_CI_CD == 'true'  ← Remove this line
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/detect-changes.yml@main
    with:
      agents-dir: ${{ vars.AGENTS_DIR || '' }}  # Auto-detects from Makefile

  deploy:
    needs: detect
    # vars.ENABLE_CI_CD == 'true' &&  ← Remove this part (keep the rest)
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.pull_request.merged == true)
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/deploy.yml@main
```

**Important:** Do first deployment manually:
```bash
make deploy my-agent
```

Then CI/CD handles re-deployments.

---

## How It Works

| Branch | Service Name | Deployed To |
|--------|-------------|-------------|
| `dev` | `dev-{service-name}` | Development |
| `stag` | `stag-{service-name}` | Staging |
| `main` | `{service-name}` | Production |

| Changed Files | Result |
|---------------|--------|
| `agents/my-agent/*` | Deploys only `my-agent` |
| Global files (`requirements.txt`, `utils/*`, etc.) | Deploys all agents |

### Pipeline Steps

```
1. detect-changes.yml → Identifies which agents changed
2. validate.yml → Validates configs and service existence
3. deploy.yml → Deploys only validated agents with existing services
```

---

## Validation Workflow

Before deployment, all agents are validated:

| Check | Description | Failure Behavior |
|-------|-------------|------------------|
| Config Schema | Validates config.yaml exists and has required fields | Fails workflow |
| Service Exists | Checks if Cloud Run service exists | Skips deployment (warns) |
| Dry-run | Simulates deployment (validates Dockerfile, imports, engine compatibility) | Warning only (continues) |

**Note:** Secret Manager validation is NOT performed in CI/CD since secret names are stored in `.env` files (gitignored).

### First Deployment Handling

When an agent hasn't been deployed before:

1. Validation creates a GitHub warning annotation
2. Agent is excluded from `ready-to-deploy` output
3. Workflow continues (doesn't fail)
4. GitHub Step Summary shows the manual deployment command

Example output:
```
⚠️ Agent 'my-agent' needs first deployment. Run: make deploy my-agent dev
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Missing `gcp_project` in config | Add `gcp_project` and `gcp_location` to `cloud_run` section |
| Permission denied | Grant all 4 IAM roles (sourceDeveloper, serviceUsageConsumer, logWriter, serviceAccountUser) to SA |
| No agents to deploy | Ensure each agent has `config.yaml` and first deploy was manual |
| Agent directory not found | Ensure Makefile has `AGENTS_DIR`, or set `AGENTS_DIR` GitHub variable |

---

## Advanced

### Different Projects Per Agent

Each agent can deploy to different GCP projects:

```yaml
# agents/agent-a/config.yaml
cloud_run:
  gcp_project: project-a-dev
  gcp_location: us-central1

# agents/agent-b/config.yaml
cloud_run:
  gcp_project: project-b-prod
  gcp_location: us-east1
```

---

## Testing

### Local Testing

```bash
# Test what code-only deployment would do
make deploy-code-only-dry my-agent
make deploy-code-only-dry my-agent dev

# Run pytest tests locally
pytest tests/ -v
```

### Continuous Testing (CI)

The `ci.yml` workflow runs all tests on every push to verify code quality:

| Workflow | Triggers | Purpose |
|----------|----------|---------|
| `ci.yml` → `test.yml` | Push to any branch, PR | Run all tests in `tests/` |

**Tests run:**
- `test_hooks.py` - Deployment hooks functionality (5 tests)
- `test_workflow.py` - CI/CD pipeline logic (23 tests)

**Total: 28 tests**

**Benefits:**
- **Shift-left testing** - Catches issues before deployment
- **Fast feedback** - Runs on every push, independent of deployment
- **No secrets needed** - Tests use mocks, don't require GCP access

The CI workflow runs separately from the deployment pipeline and doesn't require any configuration.

---

## Checklist

Before pushing to branches:

- [ ] `GCP_SA_KEY` secret set in GitHub
- [ ] Each `config.yaml` has `gcp_project` and `gcp_location`
- [ ] First deployment done manually: `make deploy <agent>`
- [ ] Workflow references point to your org (not `./.github/workflows/`)
- [ ] Tested locally: `make deploy-code-only-dry <agent>`

---
