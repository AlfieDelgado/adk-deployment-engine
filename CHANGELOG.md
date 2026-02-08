# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Next Steps: workflow status badge, improved error messages, deployment URL in summary

## [0.4.0] - 2026-02-08

### Added
- **GitHub Actions CI/CD Validation**: Continuous testing workflow that validates changes before deployment
  - `validate.yml`: Comprehensive validation including dry-run deployments, shell tests, and Python tests
  - Automatic change detection between base and head commits
  - Validates agent configuration and Dockerfile generation
  - Tests deployment scripts with dry-run mode
- **Dry-run results tracking**: Improved output and result tracking for deployment dry-runs
- **Shell testing framework**: Added tests for validate workflow shell scripts

### Changed
- Reordered validate.yml workflow steps for better logical flow
- Use `make deploy-dry` instead of direct Python calls for consistency
- Install requirements.txt in validate.yml for Python test dependencies

### Fixed
- validate.yml GITHUB_OUTPUT format for proper GitHub Actions integration
- jq quoting issues in validate workflow
- Skip flags with env var substitutions in CI/CD preserve mode (from 0.3.0)

## [0.3.0] - 2025-01-27

### Added
- **GitHub Actions CI/CD**: Reusable workflows for automatic deployment to Cloud Run
  - `detect-changes.yml`: Detects which agents changed since last commit
  - `deploy.yml`: Deploys agents with environment-specific configuration
  - `ci-cd.yml`: Caller workflow with ENABLE_CI_CD toggle
- **Per-agent project/location configuration**: Each agent defines its own `gcp_project` and `gcp_location` in `config.yaml`
- **Code-only deployment mode**: `--preserve-env` flag for selective updates without clearing env vars/secrets
- **Environment-specific service naming**: Automatic prefixes (dev-{service}, stag-{service}, {service})
- **AGENTS_DIR auto-detection**: Reads from Makefile when used as submodule
- **make deploy-code-only**: New command for CI/CD-friendly deployments
- **Branch-to-environment mapping**: dev→dev, stag→stag, main→prod

### Changed
- Updated agents-examples/quickstart/config.yaml with required CI/CD fields
- Condensed documentation following KISS/DRY principles
- Fixed API configuration documentation (Vertex AI vs Gemini Developer API mode)

### Documentation
- Added `.github/workflows/CI_CD.md`: User-facing setup guide for GitHub Actions
- Updated `README.md`: GitHub Actions section, Next Steps, deployment commands
- Updated `SUBMODULE.md`: GitHub Actions setup for submodule users
- Updated `utils/README.md`: Core capabilities and testing sections

## [0.2.2]

### Added
- Shared utilities package `adk-shared` v0.2.2

## [0.2.1]

### Added
- Shared utilities package `adk-shared` v0.2.1

## [0.2.0]

### Added
- Shared utilities package `adk-shared` v0.2.0

## [0.1.0] - Initial Release

### Added
- **Dynamic deployment system**: Per-agent configuration with `config.yaml`
- **Google Cloud Run integration**: Automated deployment with configurable resources
- **Secret Manager integration**: 3-tier priority system (Secret Manager → .env.secrets → .env)
- **Docker build system**: Isolated build environments with generated Dockerfiles
- **Make-based commands**: Simple deployment workflow (deploy, delete, test)
- **Agent Engine management**: Vertex AI Agent Engine creation and management
- **Submodule support**: Use deployment engine as git submodule in private projects
- **Environment-specific deployments**: dev, stag, prod with service prefixes
- **Comprehensive examples**: quickstart, minimal, persistent-session agents

[Unreleased]: https://github.com/AlfieDelgado/adk-deployment-engine/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/AlfieDelgado/adk-deployment-engine/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/AlfieDelgado/adk-deployment-engine/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/AlfieDelgado/adk-deployment-engine/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/AlfieDelgado/adk-deployment-engine/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/AlfieDelgado/adk-deployment-engine/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/AlfieDelgado/adk-deployment-engine/releases/tag/v0.1.0
