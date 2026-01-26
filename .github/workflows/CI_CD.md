# GitHub Actions CI/CD Setup

Automatically deploy ADK agents to Cloud Run when code merges to `dev`, `stag`, or `main`.

> **Note for adk-deployment-engine repo**: This workflow is disabled by default. To enable CI/CD for testing `agents-examples`, set the `ENABLE_CI_CD` repository variable to `true` (Settings → Secrets and variables → Actions → Variables).

---

## Quick Setup (3 Steps)

### 1. Add GitHub Secret

**Settings → Secrets and variables → Actions → New repository secret**

Name: `GCP_SA_KEY`
Value: Your service account JSON (with Cloud Run Admin, Service Account User, Secret Manager Admin roles)

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
      agents-dir: 'agents'  # Omit to auto-detect from Makefile

  deploy:
    needs: detect
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.pull_request.merged == true)
    uses: AlfieDelgado/adk-deployment-engine/.github/workflows/deploy.yml@main
    with:
      agents-dir: 'agents'  # Omit to auto-detect from Makefile
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
      agents-dir: 'agents'

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

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Missing `gcp_project` in config | Add `gcp_project` and `gcp_location` to `cloud_run` section |
| Permission denied | Grant Cloud Run Admin, Service Account User, Secret Manager Admin to SA |
| No agents to deploy | Ensure each agent has `config.yaml` and first deploy was manual |
| Agent directory not found | Check `agents-dir` parameter or ensure Makefile has `AGENTS_DIR` |

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

```bash
# Test what code-only deployment would do
make deploy-code-only-dry my-agent
make deploy-code-only-dry my-agent dev
```

---

## Checklist

Before pushing to branches:

- [ ] `GCP_SA_KEY` secret set in GitHub
- [ ] Each `config.yaml` has `gcp_project` and `gcp_location`
- [ ] First deployment done manually: `make deploy <agent>`
- [ ] Workflow references point to your org (not `./.github/workflows/`)
- [ ] Tested locally: `make deploy-code-only-dry <agent>`

---

**Technical specs:** See [GITHUB_ACTIONS.md](../../GITHUB_ACTIONS.md)
