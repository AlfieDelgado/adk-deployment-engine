# Makefile for deploying ADK Agents to Google Cloud Run
# Note: Environment loading is handled by Python scripts with agent-specific support

# Default target
.PHONY: help enable-services list-agents deploy deploy-dry deploy-code-only deploy-code-only-dry delete test-build test-dockerfile create-agent-engine list-agent-engines delete-agent-engine

# Extract arguments (remove target from command goals)
ARGS = $(filter-out $@,$(MAKECMDGOALS))
AGENT = $(word 1,$(ARGS))
SERVICE = $(word 2,$(ARGS))

# Configurable deployment engine directory (for standalone vs included usage)
DEPLOYMENT_ENGINE_DIR ?= .
export DEPLOYMENT_ENGINE_DIR

# Configurable agents directory (default to 'agents' for backward compatibility)
AGENTS_DIR ?= agents-examples
export AGENTS_DIR

# Prevent Make from treating agent names as targets
%:
	@:

# Validate agent argument (reusable pattern)
define validate_agent
@if [ -z "$(ARGS)" ]; then \
	echo "❌ Error: Provide agent name: make $(1) <agent-name>"; \
	echo "💡 Available agents:"; \
	$(MAKE) list-agents; \
	exit 1; \
fi
endef

# Validate service argument (reusable pattern)
define validate_service
@if [ -z "$(AGENT)" ]; then \
	echo "❌ Error: Provide agent name: make $(1) <agent-name> [service-name]"; \
	exit 1; \
fi
endef
help:
	@echo "ADK Agents Deployment to Google Cloud Run"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make enable-services         Enable required Google Cloud APIs"
	@echo ""
	@echo "Agent Deployment:"
	@echo "  make deploy <agent> [dev|stag]            Deploy agent with full config (default: production)"
	@echo "  make deploy-dry <agent> [dev|stag]        Dry-run full deployment (shows gcloud command)"
	@echo "  make deploy-code-only <agent> [dev|stag]  Deploy code only (preserves env vars/secrets)"
	@echo "  make deploy-code-only-dry <agent> [dev|stag]  Dry-run code-only deployment (shows gcloud command)"
	@echo "  make list-agents                      List available agents"
	@echo ""
	@echo "Agent Engine Management:"
	@echo "  make create-agent-engine <agent>    Create agent engine for specific agent"
	@echo "  make list-agent-engines <agent>      List agent engines for specific agent"
	@echo "  make delete-agent-engine <agent>     Delete agent engine for specific agent"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test-build <agent>     Test build directory structure"
	@echo "  make test-dockerfile <agent> Test Dockerfile generation"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make delete <agent>  Delete Cloud Run service (auto-detects service name from config.yaml)"
	@echo ""
	@echo "Service Naming Examples:"
	@echo "  make deploy my-agent          → my-agent-service"
	@echo "  make deploy my-agent dev      → dev-my-agent-service"
	@echo "  make deploy my-agent stag     → stag-my-agent-service"
	@echo ""
	@echo "Dry-run Examples:"
	@echo "  make deploy-dry my-agent              → Test full production deployment"
	@echo "  make deploy-dry my-agent dev          → Test full dev deployment"
	@echo "  make deploy-dry my-agent stag         → Test full staging deployment"
	@echo ""
	@echo "Code-Only Dry-run Examples (CI/CD simulation):"
	@echo "  make deploy-code-only-dry my-agent              → Test code-only production deployment"
	@echo "  make deploy-code-only-dry my-agent dev          → Test code-only dev deployment"
	@echo "  make deploy-code-only-dry my-agent stag         → Test code-only staging deployment"

# Enable required Google Cloud services
.PHONY: enable-services
enable-services:
	@echo "📋 Enabling required Google Cloud APIs..."
	gcloud services enable \
		run.googleapis.com \
		cloudbuild.googleapis.com \
		aiplatform.googleapis.com \
		storage-component.googleapis.com
	@echo "✅ Required services enabled"

# List available agents
.PHONY: list-agents
list-agents:
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py --list

# Environment flag from second argument (dev/stag/empty)
ENV = $(word 2,$(ARGS))
ENV_FLAG = $(if $(filter dev,$(ENV)),--dev,$(if $(filter stag,$(ENV)),--stag,))

# Deploy specific agent (dynamic deployment)
.PHONY: deploy
deploy:
	$(call validate_agent,deploy)
	@echo "🚀 Deploying agent: $(word 1,$(ARGS))$(if $(ENV), to $(ENV) environment)"
	@echo "📋 Setting up required services..."
	$(MAKE) enable-services
	@echo "🚀 Deploying to Cloud Run..."
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py --deploy $(word 1,$(ARGS)) $(ENV_FLAG)

# Dry-run deployment (simulate without actually deploying)
.PHONY: deploy-dry
deploy-dry:
	$(call validate_agent,deploy-dry)
	@echo "🧪 Simulating deployment: $(word 1,$(ARGS))$(if $(ENV), to $(ENV) environment)"
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py --deploy $(word 1,$(ARGS)) --dry-run $(ENV_FLAG)

# Code-only deployment (preserves existing env vars and secrets)
.PHONY: deploy-code-only
deploy-code-only:
	$(call validate_agent,deploy-code-only)
	@echo "🔧 Deploying code only for: $(word 1,$(ARGS))$(if $(ENV), to $(ENV) environment)"
	@echo "⚠️  Preserving existing environment variables and secrets (skipping --set-env-vars and --set-secrets)"
	@echo "🚀 Deploying to Cloud Run..."
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py --deploy $(word 1,$(ARGS)) --preserve-env $(ENV_FLAG)

# Code-only dry-run deployment (shows gcloud command without env vars/secrets)
.PHONY: deploy-code-only-dry
deploy-code-only-dry:
	$(call validate_agent,deploy-code-only-dry)
	@echo "🧪 Simulating code-only deployment: $(word 1,$(ARGS))$(if $(ENV), to $(ENV) environment)"
	@echo "⚠️  Will preserve existing env vars/secrets (no --set-env-vars or --set-secrets flags)"
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py --deploy $(word 1,$(ARGS)) --dry-run --preserve-env $(ENV_FLAG)

# Delete Cloud Run service for agent
.PHONY: delete
delete:
	$(call validate_agent,delete)
	python $(DEPLOYMENT_ENGINE_DIR)/utils/makefile_helper.py delete $(AGENT)

# Test build directory structure
.PHONY: test-build
test-build:
	$(call validate_agent,test-build)
	@echo "🧪 Testing build directory structure for: $(ARGS)"
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py test build $(ARGS)

# Test Dockerfile generation
.PHONY: test-dockerfile
test-dockerfile:
	$(call validate_agent,test-dockerfile)
	@echo "🧪 Testing Dockerfile generation for: $(ARGS)"
	python $(DEPLOYMENT_ENGINE_DIR)/utils/deploy_agent.py test dockerfile $(ARGS)

# Agent Engine management (per-agent configuration)
.PHONY: create-agent-engine
create-agent-engine:
	$(call validate_agent,create-agent-engine)
	@echo "🚀 Creating Vertex AI Agent Engine for agent: $(ARGS)"
	@echo "📋 Using agent-specific configuration from $(AGENTS_DIR)/$(ARGS)/.env.secrets (if available)..."
	python $(DEPLOYMENT_ENGINE_DIR)/utils/agent_engine_manager.py $(ARGS)

.PHONY: list-agent-engines
list-agent-engines:
	$(call validate_agent,list-agent-engines)
	@echo "📋 Listing Vertex AI Agent Engines for agent: $(ARGS)"
	python $(DEPLOYMENT_ENGINE_DIR)/utils/agent_engine_manager.py $(ARGS) --list

.PHONY: delete-agent-engine
delete-agent-engine:
	$(call validate_agent,delete-agent-engine)
	@echo "🗑️  Deleting Vertex AI Agent Engine for agent: $(ARGS)"
	@echo "⚠️  This will permanently delete the agent engine!"
	python $(DEPLOYMENT_ENGINE_DIR)/utils/agent_engine_manager.py $(ARGS) --delete

# TODO: create gs bucket for artifacts management and ARTIFACT_BUCKET setup

# TODO: create secrets for SECRET_NAME

# TODO: create service account for SERVICE_ACCOUNT

# TODO: create sub conda envs by agent