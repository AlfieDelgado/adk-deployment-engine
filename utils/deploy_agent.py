#!/usr/bin/env python3
"""Dynamic deployment engine for ADK Agents with per-agent configuration.

This is the main orchestrator that uses modular components for:
- Environment management (env_manager.py)
- Docker and build operations (docker_builder.py)
- Cloud Run deployment (cloud_deployer.py)
- Testing utilities (testing_utils.py)
"""

import argparse
import logging
import os
import sys
import yaml

from pathlib import Path

from dotenv import load_dotenv

# Import modular components
from env_manager import (
    substitute_env_vars, process_secret_manager_config,
    get_env_var
)
from docker_builder import (
    create_build_directory, modify_dockerfile_template
)
from cloud_deployer import deploy_agent
from testing_utils import (
    test_build_structure, test_dockerfile_generation
)

# Load environment variables at module level
load_dotenv()


def get_agents_dir():
    """Get the agents directory from environment variable or default.

    Returns:
        str: Path to the agents directory
    """
    return os.environ.get('AGENTS_DIR', 'agents')


def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def load_agent_config(agent_name, apply_env_substitution=True):
    """Load configuration for a specific agent.

    Args:
        agent_name: Name of the agent
        apply_env_substitution: Whether to apply environment variable substitution

    Returns:
        tuple: (config, substituted_vars, secret_referenced_vars) or None
    """
    agents_dir = get_agents_dir()
    config_file = Path(f"{agents_dir}/{agent_name}/config.yaml")
    if not config_file.exists():
        logging.error(f"No config.yaml found in {agents_dir}/{agent_name}/")
        return None

    with open(config_file) as f:
        config = yaml.safe_load(f)

    substituted_vars = set()
    secret_referenced_vars = set()

    if apply_env_substitution:
        # Extract Secret Manager configurations from ORIGINAL config (before substitution)
        cloud_run_config = config.get("cloud_run", {})
        additional_flags = cloud_run_config.get("additional_flags", [])
        _, secret_referenced_vars, _, _ = process_secret_manager_config(additional_flags)

        # Apply environment variable substitution
        config, substituted_vars = substitute_env_vars(config, agent_name)

    return config, substituted_vars, secret_referenced_vars


def load_agent_secrets(agent_name):
    """Load agent-specific secrets from .env.secrets file using dotenv.

    Args:
        agent_name: Name of the agent

    Returns:
        dict: Agent secrets
    """
    from env_manager import load_environment_files
    return load_environment_files(agent_name)


def list_agents():
    """List all available agents with configs.

    Returns:
        list: List of agent dictionaries with name, path, and config
    """
    agents_dir_name = get_agents_dir()
    agents_dir = Path(agents_dir_name)
    agents = []

    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / "config.yaml").exists():
                result = load_agent_config(agent_dir.name)
                if result:
                    config, _, _ = result
                    agents.append({
                        "name": agent_dir.name,
                        "path": agent_dir,
                        "config": config
                    })

    return agents


def handle_list_command():
    """Handle the --list command to display available agents."""
    logging.info("🤖 Available agents:")
    agents = list_agents()
    if not agents:
        logging.info("No agents found with config.yaml files")
        return

    for agent in agents:
        config = agent["config"]
        docker_config = config.get("docker", {})
        cloud_config = config.get("cloud_run", {})
        agents_dir = get_agents_dir()
        secrets_file = Path(f"{agents_dir}/{agent['name']}/.env.secrets")
        has_secrets = secrets_file.exists()

        logging.info(f"\t📁 {agent['name']}")
        logging.info(f"\t\t📝 {config.get('description', 'No description')}")

        if docker_config.get("base_image"):
            logging.info(f"\t\t🐳 Base: {docker_config['base_image']}")
        if docker_config.get("system_packages"):
            logging.info(f"\t\t📦 System packages: {', '.join(docker_config['system_packages'])}")
        if has_secrets:
            logging.info("\t\t🔐 Has secrets: Yes")

        default_service_name = f"{agent['name']}-service"
        logging.info(f"\t\t⚙️  Service: {cloud_config.get('service_name', default_service_name)}")
        logging.info(f"\t\t🏷️  Tags: {', '.join(config.get('tags', []))}")
    logging.info("Deploy with: make deploy <agent-name>")


def handle_test_commands(args):
    """Handle test subcommands.

    Args:
        args: Parsed command line arguments
    """
    test_commands = {
        "build": lambda agent: test_build_structure(agent, load_agent_config, create_build_directory),
        "dockerfile": lambda agent: test_dockerfile_generation(agent, load_agent_config, modify_dockerfile_template),
    }

    if args.test_type in test_commands:
        success = test_commands[args.test_type](args.agent_name)
        if not success:
            sys.exit(1)
    else:
        logging.error(f"Unknown test type: {args.test_type}")
        sys.exit(1)


def handle_deployment(args):
    """Handle deployment commands.

    Args:
        args: Parsed command line arguments
    """
    # Validate mutually exclusive environment flags
    if args.dev and args.stag:
        logging.error("❌ Cannot specify both --dev and --stag flags")
        sys.exit(1)

    # Determine environment and prefix from flags
    if args.dev:
        environment = "dev"
        service_prefix = "dev-"
    elif args.stag:
        environment = "stag"
        service_prefix = "stag-"
    else:
        environment = "prod"
        service_prefix = ""

    # Log environment info
    if environment != "prod":
        logging.info(f"🌍 Environment: {environment} (service prefix: '{service_prefix}')")

    # Load and validate configuration
    result = load_agent_config(args.deploy)
    if not result:
        sys.exit(1)

    config, substituted_vars, secret_referenced_vars = result
    secrets = load_agent_secrets(args.deploy)

    # Get deployment configuration from config.yaml (for CI/CD fallback)
    cloud_run_config = config.get("cloud_run", {})
    config_project = cloud_run_config.get("gcp_project")
    config_location = cloud_run_config.get("gcp_location")

    # Get environment variables (source of truth for local development)
    env_project = get_env_var("GOOGLE_CLOUD_PROJECT")
    env_location_deploy = get_env_var("GOOGLE_CLOUD_LOCATION_DEPLOY")
    env_location_api = get_env_var("GOOGLE_CLOUD_LOCATION")

    # Use env var as source of truth, fall back to config
    project_id = env_project or config_project
    location_deploy = env_location_deploy or env_location_api or config_location

    # Warn if there's a mismatch between env var and config
    if env_project and config_project and env_project != config_project:
        logging.warning(f"⚠️  GOOGLE_CLOUD_PROJECT mismatch:")
        logging.warning(f"   .env has '{env_project}', config.yaml has '{config_project}'")
        logging.warning(f"   Using: '{env_project}' (env var takes precedence)")

    if (env_location_deploy or env_location_api) and config_location:
        env_location = env_location_deploy or env_location_api
        if env_location != config_location:
            logging.warning(f"⚠️  GOOGLE_CLOUD_LOCATION mismatch:")
            logging.warning(f"   .env has '{env_location}', config.yaml has '{config_location}'")
            logging.warning(f"   Using: '{env_location}' (env var takes precedence)")

    # Validate required values
    if not project_id:
        agents_dir = get_agents_dir()
        logging.error(f"GOOGLE_CLOUD_PROJECT must be set in .env file, {agents_dir}/{args.deploy}/.env.secrets, or config.yaml")
        sys.exit(1)

    if not location_deploy:
        agents_dir = get_agents_dir()
        logging.error(f"GOOGLE_CLOUD_LOCATION must be set in .env file, {agents_dir}/{args.deploy}/.env.secrets, or config.yaml")
        sys.exit(1)

    # Deploy using cloud_deployer module
    success = deploy_agent(args.deploy, config, secrets, project_id, location_deploy,
                         dry_run=args.dry_run, preserve_env=args.preserve_env,
                         service_prefix=service_prefix, environment=environment,
                         substituted_vars=substituted_vars, secret_referenced_vars=secret_referenced_vars)
    if not success:
        sys.exit(1)


def create_argument_parser():
    """Create and configure the argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(description="Dynamic deployment engine for ADK Agents")
    parser.add_argument("--deploy", help="Deploy specific agent")
    parser.add_argument("--list", action="store_true", help="List available agents")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deployment without actually deploying")
    parser.add_argument("--preserve-env", action="store_true",
                        help="Preserve existing environment variables and secrets (use --update-env-vars and --update-secrets)")
    parser.add_argument("--dev", action="store_true",
                        help="Deploy to dev environment (adds 'dev-' prefix to service name)")
    parser.add_argument("--stag", action="store_true",
                        help="Deploy to staging environment (adds 'stag-' prefix to service name)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    # Test subcommands
    subparsers = parser.add_subparsers(dest="test", help="Test deployment components")
    test_parser = subparsers.add_parser("test", help="Test deployment components")
    test_subparsers = test_parser.add_subparsers(dest="test_type")

    # Build test subcommand
    build_parser = test_subparsers.add_parser("build", help="Test build directory structure")
    build_parser.add_argument("agent_name", nargs="?", default="quickstart", help="Agent name to test")

    # Dockerfile test subcommand
    dockerfile_parser = test_subparsers.add_parser("dockerfile", help="Test Dockerfile generation")
    dockerfile_parser.add_argument("agent_name", nargs="?", default="quickstart", help="Agent name to test")

    return parser


def main():
    """Main entry point for the deployment engine."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Setup logging based on verbosity
    setup_logging(args.verbose)

    # Route to appropriate handler based on command
    if args.list:
        handle_list_command()
    elif args.test:
        handle_test_commands(args)
    elif args.deploy:
        handle_deployment(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
