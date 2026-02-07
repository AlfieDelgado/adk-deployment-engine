"""End-to-end tests for GitHub Actions workflows.

Tests the complete CI/CD pipeline:
- detect-changes.yml → validate.yml → deploy.yml

This tests the workflow logic locally without needing real GCP resources.
"""

import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

import pytest
import yaml


# ============================================================================
# Test Data Models
# ============================================================================

@dataclass
class ValidationResult:
    """Result from validate.yml logic."""
    status: str  # 'ready', 'needs_first_deploy', 'failed'
    agent: str
    service_name: str
    errors: List[str]
    warnings: List[str]


@dataclass
class DetectionResult:
    """Result from detect-changes.yml logic."""
    agents_to_deploy: List[str]
    should_deploy_all: bool


@dataclass
class DeploymentResult:
    """Result from deploy.yml logic."""
    agent: str
    service_name: str
    would_deploy: bool
    reason: str


# ============================================================================
# Mock GCloud Service
# ============================================================================

class MockGcloud:
    """Mock gcloud commands for testing."""

    def __init__(self, existing_services: Dict[str, List[str]] = None):
        self.existing_services = existing_services or {}

    def service_exists(self, service_name: str, project: str, region: str) -> bool:
        return service_name in self.existing_services.get(project, [])


# ============================================================================
# Workflow Logic (Extracted from GitHub Actions)
# ============================================================================

def detect_agent_changes(
    agents_dir: str,
    changed_files: List[str],
    all_agents: List[str]
) -> DetectionResult:
    """
    Detect which agents need deployment based on changed files.
    Mirrors the logic in detect-changes.yml workflow.
    """
    global_files = [
        ".env", "requirements.txt", "environment.yml",
        "makefile", "pyproject.toml", ".python-version"
    ]

    should_deploy_all = False
    for file in changed_files:
        if file in global_files or file.startswith("utils/") or file.startswith(".github/workflows/"):
            should_deploy_all = True
            break

    if should_deploy_all:
        return DetectionResult(agents_to_deploy=all_agents, should_deploy_all=True)

    changed_agents = []
    for agent in all_agents:
        agent_prefix = f"{agents_dir}/{agent}/"
        for file in changed_files:
            if file.startswith(agent_prefix):
                changed_agents.append(agent)
                break

    return DetectionResult(agents_to_deploy=changed_agents, should_deploy_all=False)


def validate_agent_config(
    agent: str,
    agents_dir: str,
    prefix: str,
    gcloud: MockGcloud
) -> ValidationResult:
    """Validate an agent's configuration. Mirrors validate.yml logic."""
    errors = []
    config_path = f"{agents_dir}/{agent}/config.yaml"

    if not os.path.exists(config_path):
        return ValidationResult(
            status='failed', agent=agent, service_name='',
            errors=[f"config.yaml not found"], warnings=[]
        )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    cloud_run = config.get('cloud_run', {})
    required = {
        'gcp_project': cloud_run.get('gcp_project'),
        'gcp_location': cloud_run.get('gcp_location'),
        'service_name': cloud_run.get('service_name')
    }

    for field, value in required.items():
        if not value or not isinstance(value, str) or not value.strip():
            errors.append(f"Missing field: cloud_run.{field}")
        else:
            required[field] = value.strip()

    if errors:
        return ValidationResult(
            status='failed', agent=agent,
            service_name=required.get('service_name', ''),
            errors=errors, warnings=[]
        )

    final_service = f"{prefix}{required['service_name']}"
    service_exists = gcloud.service_exists(
        final_service, required['gcp_project'], required['gcp_location']
    )

    return ValidationResult(
        status='ready' if service_exists else 'needs_first_deploy',
        agent=agent,
        service_name=final_service,
        errors=[],
        warnings=[]
    )


def check_deployment_readiness(
    validation_result: ValidationResult
) -> DeploymentResult:
    """Check if an agent is ready for deployment. Mirrors deploy.yml logic."""
    if validation_result.status == 'failed':
        return DeploymentResult(
            agent=validation_result.agent,
            service_name=validation_result.service_name,
            would_deploy=False,
            reason=f"Validation failed: {', '.join(validation_result.errors)}"
        )

    if validation_result.status == 'needs_first_deploy':
        return DeploymentResult(
            agent=validation_result.agent,
            service_name=validation_result.service_name,
            would_deploy=False,
            reason="Service does not exist (needs first manual deployment)"
        )

    return DeploymentResult(
        agent=validation_result.agent,
        service_name=validation_result.service_name,
        would_deploy=True,
        reason="Ready to deploy"
    )


def run_cicd_pipeline(
    agents_dir: str,
    changed_files: List[str],
    branch_name: str,
    gcloud: MockGcloud
) -> Dict:
    """
    Run the complete CI/CD pipeline: detect → validate → deploy

    Returns dict with pipeline results.
    """
    # Get all agents
    all_agents = []
    agents_path = Path(agents_dir)
    if agents_path.exists():
        for agent_dir in agents_path.iterdir():
            if agent_dir.is_dir() and (agent_dir / "config.yaml").exists():
                all_agents.append(agent_dir.name)

    # STEP 1: Detect changes
    detection = detect_agent_changes(agents_dir, changed_files, all_agents)

    # STEP 2: Validate detected agents
    prefix_map = {'dev': 'dev-', 'stag': 'stag-', 'main': ''}
    prefix = prefix_map.get(branch_name, '')

    validation_results = []
    for agent in detection.agents_to_deploy:
        result = validate_agent_config(agent, agents_dir, prefix, gcloud)
        validation_results.append(result)

    # STEP 3: Check deployment readiness
    deployment_results = []
    for validation in validation_results:
        deployment = check_deployment_readiness(validation)
        deployment_results.append(deployment)

    return {
        'detected_changes': detection,
        'validation_results': validation_results,
        'deployment_results': deployment_results,
        'ready_to_deploy': [d.agent for d in deployment_results if d.would_deploy],
        'needs_first_deploy': [v.agent for v in validation_results if v.status == 'needs_first_deploy'],
        'validation_failed': [v.agent for v in validation_results if v.status == 'failed']
    }


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_gcloud_with_services():
    """Mock GCloud with existing services for all environments."""
    return MockGcloud(
        existing_services={
            'galvanic-style-239913': [
                'quickstart-agent',
                'dev-quickstart-agent',
                'stag-quickstart-agent'
            ],
            'test-project': ['test-agent', 'dev-test-agent', 'stag-test-agent']
        }
    )


@pytest.fixture
def mock_gcloud_empty():
    """Mock GCloud with no services."""
    return MockGcloud(existing_services={})


@pytest.fixture
def temp_agent_dir():
    """Create a temporary agent directory with valid config.yaml."""
    temp_dir = tempfile.mkdtemp(prefix='test_agent_')
    agent_dir = os.path.join(temp_dir, 'test-agent')
    os.makedirs(agent_dir, exist_ok=True)

    config = {
        'description': 'Test agent',
        'cloud_run': {
            'service_name': 'test-agent',
            'gcp_project': 'test-project',
            'gcp_location': 'us-central1'
        }
    }

    with open(os.path.join(agent_dir, 'config.yaml'), 'w') as f:
        yaml.dump(config, f)

    yield temp_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def invalid_agent_dir():
    """Create a temporary agent directory with invalid config.yaml."""
    temp_dir = tempfile.mkdtemp(prefix='test_invalid_agent_')
    agent_dir = os.path.join(temp_dir, 'invalid-agent')
    os.makedirs(agent_dir, exist_ok=True)

    with open(os.path.join(agent_dir, 'config.yaml'), 'w') as f:
        f.write("description: Invalid agent\n")

    yield temp_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Test: detect-changes.yml
# ============================================================================

class TestDetectChanges:
    """Test change detection logic from detect-changes.yml."""

    def test_no_changes(self):
        result = detect_agent_changes('agents-examples', [], ['quickstart'])
        assert result.agents_to_deploy == []
        assert result.should_deploy_all is False

    def test_agent_specific_change(self):
        changed_files = ['agents-examples/quickstart/agent.py']
        result = detect_agent_changes('agents-examples', changed_files, ['quickstart', 'other'])
        assert result.agents_to_deploy == ['quickstart']
        assert result.should_deploy_all is False

    def test_global_env_change(self):
        changed_files = ['.env']
        result = detect_agent_changes('agents', changed_files, ['agent1', 'agent2'])
        assert set(result.agents_to_deploy) == {'agent1', 'agent2'}
        assert result.should_deploy_all is True

    def test_requirements_change(self):
        changed_files = ['requirements.txt']
        result = detect_agent_changes('agents', changed_files, ['agent1', 'agent2'])
        assert result.should_deploy_all is True

    def test_utils_change(self):
        changed_files = ['utils/deploy_agent.py']
        result = detect_agent_changes('agents', changed_files, ['agent1', 'agent2'])
        assert result.should_deploy_all is True

    def test_workflow_change(self):
        changed_files = ['.github/workflows/deploy.yml']
        result = detect_agent_changes('agents', changed_files, ['agent1', 'agent2'])
        assert result.should_deploy_all is True


# ============================================================================
# Test: validate.yml
# ============================================================================

class TestValidateLogic:
    """Test validation logic from validate.yml."""

    def test_config_not_found(self, mock_gcloud_empty):
        result = validate_agent_config('nonexistent', 'agents', '', mock_gcloud_empty)
        assert result.status == 'failed'
        assert 'config.yaml not found' in result.errors[0]

    def test_valid_config_existing_service(self, temp_agent_dir, mock_gcloud_with_services):
        result = validate_agent_config('test-agent', temp_agent_dir, '', mock_gcloud_with_services)
        assert result.status == 'ready'
        assert result.service_name == 'test-agent'

    def test_valid_config_no_service(self, temp_agent_dir, mock_gcloud_empty):
        result = validate_agent_config('test-agent', temp_agent_dir, '', mock_gcloud_empty)
        assert result.status == 'needs_first_deploy'
        assert result.service_name == 'test-agent'

    def test_invalid_config_missing_fields(self, invalid_agent_dir, mock_gcloud_empty):
        result = validate_agent_config('invalid-agent', invalid_agent_dir, '', mock_gcloud_empty)
        assert result.status == 'failed'
        assert len(result.errors) == 3

    def test_dev_prefix(self, temp_agent_dir, mock_gcloud_with_services):
        result = validate_agent_config('test-agent', temp_agent_dir, 'dev-', mock_gcloud_with_services)
        assert result.status == 'ready'
        assert result.service_name == 'dev-test-agent'

    def test_stag_prefix(self, temp_agent_dir, mock_gcloud_with_services):
        result = validate_agent_config('test-agent', temp_agent_dir, 'stag-', mock_gcloud_with_services)
        assert result.status == 'ready'
        assert result.service_name == 'stag-test-agent'


# ============================================================================
# Test: deploy.yml
# ============================================================================

class TestDeployLogic:
    """Test deployment logic from deploy.yml."""

    def test_ready_to_deploy(self):
        validation = ValidationResult('ready', 'test', 'dev-test', [], [])
        result = check_deployment_readiness(validation)
        assert result.would_deploy is True

    def test_needs_first_deployment(self):
        validation = ValidationResult('needs_first_deploy', 'test', 'test', [], [])
        result = check_deployment_readiness(validation)
        assert result.would_deploy is False
        assert "needs first manual deployment" in result.reason

    def test_validation_failed(self):
        validation = ValidationResult('failed', 'test', '', ['Missing field'], [])
        result = check_deployment_readiness(validation)
        assert result.would_deploy is False
        assert "Validation failed" in result.reason


# ============================================================================
# Test: End-to-End Integration
# ============================================================================

class TestEndToEnd:
    """Test complete CI/CD pipeline integration."""

    def test_existing_service_deployment(self, mock_gcloud_with_services):
        changed_files = ['agents-examples/quickstart/agent.py']
        result = run_cicd_pipeline('agents-examples', changed_files, 'dev', mock_gcloud_with_services)

        assert result['ready_to_deploy'] == ['quickstart']
        assert result['needs_first_deploy'] == []
        assert result['validation_failed'] == []

    def test_new_service_skips_deploy(self, mock_gcloud_empty):
        changed_files = ['agents-examples/quickstart/config.yaml']
        result = run_cicd_pipeline('agents-examples', changed_files, 'main', mock_gcloud_empty)

        assert result['ready_to_deploy'] == []
        assert result['needs_first_deploy'] == ['quickstart']

    def test_global_change_deploys_all(self, mock_gcloud_with_services):
        changed_files = ['requirements.txt']
        result = run_cicd_pipeline('agents-examples', changed_files, 'dev', mock_gcloud_with_services)

        assert result['detected_changes'].should_deploy_all is True
        assert result['ready_to_deploy'] == ['quickstart']

    def test_no_changes(self, mock_gcloud_with_services):
        result = run_cicd_pipeline('agents-examples', [], 'dev', mock_gcloud_with_services)

        assert result['detected_changes'].agents_to_deploy == []
        assert len(result['validation_results']) == 0

    def test_all_environments(self, mock_gcloud_with_services):
        for branch, expected_prefix in [('dev', 'dev-'), ('stag', 'stag-'), ('main', '')]:
            result = run_cicd_pipeline(
                'agents-examples',
                ['agents-examples/quickstart/agent.py'],
                branch,
                mock_gcloud_with_services
            )
            assert result['validation_results'][0].service_name.startswith(expected_prefix)


# ============================================================================
# Test: Real Quickstart Agent
# ============================================================================

class TestQuickstartAgent:
    """Test validation against actual quickstart agent."""

    def test_config_exists(self):
        assert os.path.exists('agents-examples/quickstart/config.yaml')
        with open('agents-examples/quickstart/config.yaml') as f:
            config = yaml.safe_load(f)
        assert config['cloud_run']['gcp_project']
        assert config['cloud_run']['gcp_location']
        assert config['cloud_run']['service_name']

    def test_dev_with_mock_service(self, mock_gcloud_with_services):
        result = validate_agent_config(
            'quickstart', 'agents-examples', 'dev-', mock_gcloud_with_services
        )
        assert result.status == 'ready'
        assert result.service_name == 'dev-quickstart-agent'

    def test_prod_needs_first_deploy(self, mock_gcloud_empty):
        result = validate_agent_config(
            'quickstart', 'agents-examples', '', mock_gcloud_empty
        )
        assert result.status == 'needs_first_deploy'
        assert result.service_name == 'quickstart-agent'


# ============================================================================
# Test: Shell Script Logic
# ============================================================================

class TestShellLogic:
    """Test shell script logic from workflows (actual command execution)."""

    def test_jq_parse_json_array(self):
        """Test that jq can parse JSON arrays correctly."""
        # Test with single agent
        result = subprocess.run(
            ["jq", "-r", ".[]"],
            input='["quickstart"]',
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "quickstart"

        # Test with multiple agents
        result = subprocess.run(
            ["jq", "-r", ".[]"],
            input='["agent1", "agent2", "agent3"]',
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        agents = result.stdout.strip().split("\n")
        assert agents == ["agent1", "agent2", "agent3"]

        # Test with empty array
        result = subprocess.run(
            ["jq", "-r", ".[]"],
            input="[]",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_jq_with_echo_single_quotes(self):
        """Test echo with single quotes around JSON (workflow fix)."""
        # This is the correct way - single quotes protect the JSON
        result = subprocess.run(
            "echo '[\"quickstart\"]' | jq -r '.[]'",
            shell=True,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "quickstart"

    def test_jq_with_echo_double_quotes_fails(self):
        """Test that double quotes around JSON breaks jq (the bug)."""
        # The actual bug: when GitHub Actions expands the input, it loses proper quoting
        # Simulating what happens with the broken workflow pattern
        result = subprocess.run(
            'echo "[\"quickstart\"]" | jq -r ".[]" 2>&1 || true',
            shell=True,
            capture_output=True,
            text=True
        )
        # This should fail with parse error
        assert "parse error" in result.stdout

    @pytest.mark.skipif(not shutil.which("yq"), reason="yq not installed locally")
    def test_yq_extract_from_yaml(self):
        """Test yq extracting values from YAML config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
description: Test agent
cloud_run:
  service_name: quickstart-agent
  gcp_project: my-project
  gcp_location: us-central1
""")

            # Test extracting a single value
            result = subprocess.run(
                ["yq", "eval", ".cloud_run.gcp_project", str(config_file)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "my-project"

            # Test with default value
            result = subprocess.run(
                ["yq", "eval", ".cloud_run.nonexistent // \"default\"", str(config_file)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "default"

    @pytest.mark.skipif(not shutil.which("yq"), reason="yq not installed locally")
    def test_yq_extract_empty_string(self):
        """Test that yq returns empty string for missing fields without default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("description: Test\n")

            result = subprocess.run(
                ["yq", "eval", ".cloud_run.gcp_project // \"\"", str(config_file)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip() == ""

    def test_bash_array_operations(self):
        """Test bash array operations used in workflows."""
        result = subprocess.run(
            """
            ready=()
            ready+=("agent1")
            ready+=("agent2")
            printf '%s\\n' "${ready[@]}" | jq -R . | jq -s .
            """,
            shell=True,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert json.loads(result.stdout) == ["agent1", "agent2"]

    def test_bash_empty_array(self):
        """Test bash empty array handling."""
        result = subprocess.run(
            """
            ready=()
            if [ ${#ready[@]} -eq 0 ]; then
                echo "[]"
            else
                printf '%s\\n' "${ready[@]}" | jq -R . | jq -s .
            fi
            """,
            shell=True,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "[]"

    def test_github_env_pattern(self):
        """Test the $GITHUB_ENV pattern used in workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "env.txt"

            # Simulate writing to GITHUB_ENV
            subprocess.run(
                f'echo "ENVIRONMENT=dev" >> {env_file}',
                shell=True
            )
            subprocess.run(
                f'echo "PREFIX=dev-" >> {env_file}',
                shell=True
            )

            # Read back
            result = subprocess.run(
                f"cat {env_file}",
                shell=True,
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            lines = result.stdout.strip().split("\n")
            assert "ENVIRONMENT=dev" in lines
            assert "PREFIX=dev-" in lines
