# Makefile for deploying ADK Agents to Google Cloud Run
# Note: Environment loading is handled by Python scripts with agent-specific support

# Default target
.PHONY: help enable-services list-agents deploy deploy-dry delete test-build test-dockerfile create-agent-engine list-agent-engines delete-agent-engine

# Extract arguments (remove target from command goals)
ARGS = $(filter-out $@,$(MAKECMDGOALS))
AGENT = $(word 1,$(ARGS))
SERVICE = $(word 2,$(ARGS))

# Configurable agents directory (default to 'agents' for backward compatibility)
AGENTS_DIR ?= agents
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
	@echo "Agent Deployment (Per-Agent Config):"
	@echo "  make deploy <agent-name>    Deploy specific agent (e.g., make deploy oauth_multi_agent)"
	@echo "  make deploy-dry <agent-name>     Dry-run deployment (simulate without deploying)"
	@echo "  make list-agents            List available agents"
	@echo ""
	@echo "Agent Engine Management (Per-Agent Config):"
	@echo "  make create-agent-engine <agent-name>    Create agent engine for specific agent"
	@echo "  make list-agent-engines <agent-name>      List agent engines for specific agent"
	@echo "  make delete-agent-engine <agent-name>     Delete agent engine for specific agent"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test-build <agent-name>     Test build directory structure"
	@echo "  make test-dockerfile <agent-name> Test Dockerfile generation"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make delete <agent-name>  Delete Cloud Run service (auto-detects service name from config.yaml)"

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
	python utils/deploy_agent.py --list

# Deploy specific agent (dynamic deployment)
.PHONY: deploy
deploy:
	$(call validate_agent,deploy)
	@echo "🚀 Deploying agent: $(ARGS)"
	@echo "📋 Setting up required services..."
	$(MAKE) enable-services
	@echo "🚀 Deploying to Cloud Run using official ADK approach..."
	python utils/deploy_agent.py --deploy $(ARGS)

# Dry-run deployment (simulate without actually deploying)
.PHONY: deploy-dry
deploy-dry:
	$(call validate_agent,deploy-dry)
	@echo "🧪 Simulating deployment for agent: $(ARGS) (dry run)"
	python utils/deploy_agent.py --deploy $(ARGS) --dry-run

# Delete Cloud Run service for agent
.PHONY: delete
delete:
	$(call validate_agent,delete)
	python utils/makefile_helper.py delete $(AGENT)

# Test build directory structure
.PHONY: test-build
test-build:
	$(call validate_agent,test-build)
	@echo "🧪 Testing build directory structure for: $(ARGS)"
	python utils/deploy_agent.py test build $(ARGS)

# Test Dockerfile generation
.PHONY: test-dockerfile
test-dockerfile:
	$(call validate_agent,test-dockerfile)
	@echo "🧪 Testing Dockerfile generation for: $(ARGS)"
	python utils/deploy_agent.py test dockerfile $(ARGS)

# Agent Engine management (per-agent configuration)
.PHONY: create-agent-engine
create-agent-engine:
	$(call validate_agent,create-agent-engine)
	@echo "🚀 Creating Vertex AI Agent Engine for agent: $(ARGS)"
	@echo "📋 Using agent-specific configuration from $(AGENTS_DIR)/$(ARGS)/.env.secrets (if available)..."
	python utils/agent_engine_manager.py $(ARGS)

.PHONY: list-agent-engines
list-agent-engines:
	$(call validate_agent,list-agent-engines)
	@echo "📋 Listing Vertex AI Agent Engines for agent: $(ARGS)"
	python utils/agent_engine_manager.py $(ARGS) --list

.PHONY: delete-agent-engine
delete-agent-engine:
	$(call validate_agent,delete-agent-engine)
	@echo "🗑️  Deleting Vertex AI Agent Engine for agent: $(ARGS)"
	@echo "⚠️  This will permanently delete the agent engine!"
	python utils/agent_engine_manager.py $(ARGS) --delete

# TODO: create gs bucket for artifacts management and ARTIFACT_BUCKET setup

# TODO: create secrets for SECRET_NAME

# TODO: create service account for SERVICE_ACCOUNT

# TODO: add arguments for dynamic cloud run service name, including dev, prod, stg, etc.