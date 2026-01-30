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
