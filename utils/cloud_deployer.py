"""Cloud Run deployment module for ADK Agents.

This module provides Google Cloud Run deployment functionality with Secret Manager
integration and proper flag handling.
"""

import logging
import subprocess
import os
from pathlib import Path


def execute_cloud_run_deployment(service_name, region, project_id, env_string,
                                secret_manager_secrets, additional_processed_flags,
                                dry_run=False):
    """Execute the actual Cloud Run deployment with Secret Manager support.

    Args:
        service_name: Cloud Run service name
        region: Google Cloud region
        project_id: Google Cloud project ID
        env_string: Environment variables string
        secret_manager_secrets: List of (secret_name, env_var_name) tuples
        additional_processed_flags: Additional Cloud Run flags
        dry_run: Whether to perform a dry run (simulation)

    Returns:
        None
    """
    logging.info("🚀 Deploying to Cloud Run with dynamic configuration...")

    # Build the basic gcloud run deploy command
    deploy_cmd = [
        "gcloud", "run", "deploy", service_name,
        "--source", ".",
        "--region", region,
        "--project", project_id,
        "--set-env-vars", env_string
    ]

    # Add additional processed flags (memory, cpu, timeout, service-account, etc.)
    if additional_processed_flags:
        deploy_cmd.extend(additional_processed_flags)

    # Process Secret Manager secrets
    secret_flags = []
    for secret_name, env_var_name in secret_manager_secrets:
        secret_flags.append(f"--update-secrets={env_var_name}={secret_name}:latest")

    # Add Secret Manager flags to deploy command
    if secret_flags:
        deploy_cmd.extend(secret_flags)

    logging.debug(f"Running command: {' '.join(deploy_cmd)}")

    # Show command in formatted multi-line for readability (only during explicit dry run)
    if dry_run:
        logging.info("📋 Formatted command (DRY RUN):")

        formatted_cmd = f"gcloud run deploy {service_name} \\"
        formatted_cmd += "\n    --source . \\"
        formatted_cmd += f"\n    --region {region} \\"
        formatted_cmd += f"\n    --project {project_id} \\"
        formatted_cmd += f"\n    --set-env-vars '{env_string}'"

        # Show additional flags
        if additional_processed_flags:
            for flag in additional_processed_flags:
                formatted_cmd += f" \\\n    {flag}"

        # Show secret flags
        if secret_flags:
            for flag in secret_flags:
                formatted_cmd += f" \\\n    {flag}"

        logging.info(formatted_cmd)
        logging.info("✅ Dry run complete - no actual deployment performed")
        return None

    # Deploy to Cloud Run (actual deployment - no command display)
    subprocess.run(deploy_cmd, check=True)

    return None


def deploy_agent(agent_name, config, secrets, project_id, region, dry_run=False,
                 substituted_vars=None, secret_referenced_vars=None):
    """Deploy a specific agent using official ADK approach with dynamic Cloud Run configuration.

    Args:
        agent_name: Name of the agent to deploy
        config: Agent configuration dictionary
        secrets: Agent secrets dictionary
        project_id: Google Cloud project ID
        region: Google Cloud region
        dry_run: Whether to perform a dry run

    Returns:
        bool: True if deployment successful, False otherwise
    """
    from env_manager import setup_environment_variables
    from docker_builder import create_build_directory, generate_deployment_artifacts, cleanup_deployment_resources

    logging.info(f"🚀 Starting deployment for agent: {agent_name}")

    # Validate agent directory exists
    agents_dir = os.environ.get('AGENTS_DIR', 'agents')
    if not Path(f"{agents_dir}/{agent_name}").exists():
        logging.error(f"Agent directory '{agents_dir}/{agent_name}' not found")
        return False

    # Get Cloud Run configuration
    cloud_run_config = config.get("cloud_run", {})
    service_name = cloud_run_config.get("service_name", f"{agent_name}-service")

    # Setup environment variables
    env_string, secret_manager_secrets, additional_processed_flags = setup_environment_variables(
        project_id, region, agent_name, cloud_run_config,
        substituted_vars or set(), secret_referenced_vars or set()
    )

    # Log deployment info
    logging.info(f"Service: {service_name}")
    logging.info(f"Project: {project_id}")
    logging.info(f"Region: {region}")
    logging.info(f"Description: {config.get('description', 'No description')}")

    # Create build directory
    build_dir = create_build_directory(agent_name, config)
    if not build_dir:
        return False

    # Generate deployment artifacts
    generate_deployment_artifacts(agent_name, config, build_dir)

    # Change to build directory for deployment
    original_cwd = os.getcwd()
    os.chdir(build_dir)
    logging.debug(f"Changed working directory to: {build_dir}")

    try:
        # Execute deployment
        execute_cloud_run_deployment(
            service_name, region, project_id, env_string,
            secret_manager_secrets, additional_processed_flags, dry_run
        )
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Error during deployment: {e}")
        if hasattr(e, "stderr"):
            logging.error(f"Error output: {e.stderr}")
        return False

    finally:
        # Cleanup resources
        cleanup_deployment_resources(build_dir, original_cwd)
