"""Cloud Run deployment module for ADK Agents.

This module provides Google Cloud Run deployment functionality with Secret Manager
integration and proper flag handling.
"""

import logging
import subprocess
import os
import re
from pathlib import Path


def filter_env_var_flags(flags, preserve_env=False):
    """Filter out flags that contain environment variable substitutions when in preserve_env mode.

    In CI/CD mode (preserve_env=True), flags like --service-account=${SERVICE_ACCOUNT}
    reference environment variables that aren't available, so they should be skipped.

    Args:
        flags: List of gcloud flags (e.g., ["--service-account=${SERVICE_ACCOUNT}", "--memory=1Gi"])
        preserve_env: Whether to filter out env var substitutions

    Returns:
        tuple: (filtered_flags, skipped_flags) where:
            - filtered_flags: Flags to include in deployment
            - skipped_flags: Flags that were skipped (for logging)
    """
    if not preserve_env:
        return flags, []

    filtered = []
    skipped = []

    # Pattern to match ${VAR_NAME} environment variable substitutions
    env_var_pattern = re.compile(r'\$\{[A-Z_][A-Z0-9_]*\}')

    for flag in flags:
        # Check if flag contains environment variable substitution
        if env_var_pattern.search(flag):
            skipped.append(flag)
        else:
            filtered.append(flag)

    return filtered, skipped


def execute_cloud_run_deployment(service_name, region, project_id, env_string,
                                secret_manager_secrets, additional_processed_flags,
                                dry_run=False, preserve_env=False):
    """Execute the actual Cloud Run deployment with Secret Manager support.

    Args:
        service_name: Cloud Run service name
        region: Google Cloud region
        project_id: Google Cloud project ID
        env_string: Environment variables string
        secret_manager_secrets: List of (secret_name, env_var_name) tuples
        additional_processed_flags: Additional Cloud Run flags
        dry_run: Whether to perform a dry run (simulation)
        preserve_env: If True, use --update-env-vars/--update-secrets to preserve
                     existing environment variables and secrets that aren't being updated

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
    ]

    # Handle secrets - pre-build secret values string for reuse in command and display
    secret_values_str = None
    if secret_manager_secrets:
        secret_values_str = ",".join([f"{env_var_name}={secret_name}:latest"
                                       for secret_name, env_var_name in secret_manager_secrets])

    if preserve_env:
        # In preserve mode (CI/CD), skip secrets entirely to preserve existing configuration
        logging.info("🔧 CI/CD mode: Preserving existing secrets (no access to .env files)")
    elif secret_manager_secrets:
        # In full deployment mode with secrets, set configured secrets
        # NOTE: --set-secrets replaces all existing secrets
        deploy_cmd.append(f"--set-secrets={secret_values_str}")
        logging.info(f"🔄 Full deployment: Setting {len(secret_manager_secrets)} secret(s) (replaces all existing secrets)")
    else:
        # In full deployment mode without secrets, clear all existing secrets
        deploy_cmd.append("--clear-secrets")
        logging.info("🧹 Full deployment: No secrets configured - clearing all existing secrets")

    # Filter out flags with environment variable substitutions when in preserve_env mode
    # This prevents CI/CD from failing on flags like --service-account=${SERVICE_ACCOUNT}
    filtered_flags, skipped_flags = filter_env_var_flags(additional_processed_flags, preserve_env)

    # Add filtered additional flags (memory, cpu, timeout, etc.)
    if filtered_flags:
        deploy_cmd.extend(filtered_flags)

    # Log skipped flags in preserve mode
    if preserve_env and skipped_flags:
        logging.info("🔧 Preserve mode: Skipping flags with environment variable substitutions:")
        for flag in skipped_flags:
            logging.info(f"   ⏭️  {flag}")
        logging.info("   These flags will use existing values from the deployed service")

    # Handle env vars - only set if NOT in preserve mode
    if preserve_env:
        logging.info("🔧 Preserve mode: Skipping environment variables (keeping existing Cloud Run env vars)")
    else:
        deploy_cmd.extend(["--set-env-vars", env_string])
        logging.info("🔄 Full deployment: Using --set-env-vars (replaces all environment variables)")

    logging.debug(f"Running command: {' '.join(deploy_cmd)}")

    # Show command in formatted multi-line for readability (only during explicit dry run)
    if dry_run:
        logging.info("📋 Formatted command (DRY RUN):")

        formatted_cmd = f"gcloud run deploy {service_name} \\"
        formatted_cmd += "\n    --source . \\"
        formatted_cmd += f"\n    --region {region} \\"
        formatted_cmd += f"\n    --project {project_id}"

        # Show secret flags
        if secret_manager_secrets and not preserve_env:
            # Full deployment mode with secrets - show --set-secrets
            formatted_cmd += f" \\\n    --set-secrets={secret_values_str}"
        elif not secret_manager_secrets and not preserve_env:
            # Full deployment mode without secrets - show --clear-secrets
            formatted_cmd += f" \\\n    --clear-secrets"
        # Note: CI/CD mode (preserve_env=True) - no flags shown (preserves existing)

        # Show additional flags (filtered in preserve mode)
        if filtered_flags:
            for flag in filtered_flags:
                formatted_cmd += f" \\\n    {flag}"

        # Show skipped flags in dry-run output
        if preserve_env and skipped_flags:
            logging.info("")
            logging.info("🔧 Preserve mode: The following flags will be skipped (contain env var substitutions):")
            for flag in skipped_flags:
                logging.info(f"   ⏭️  {flag}")

        # Show env vars (only if NOT in preserve mode)
        if not preserve_env:
            formatted_cmd += f" \\\n    --set-env-vars '{env_string}'"

        logging.info(formatted_cmd)
        logging.info("✅ Dry run complete - no actual deployment performed")
        return None

    # Deploy to Cloud Run (actual deployment - no command display)
    subprocess.run(deploy_cmd, check=True)

    return None


def deploy_agent(agent_name, config, secrets, project_id, region, dry_run=False,
                 preserve_env=False, service_prefix=None, environment=None,
                 substituted_vars=None, secret_referenced_vars=None):
    """Deploy a specific agent using official ADK approach with dynamic Cloud Run configuration.

    Args:
        agent_name: Name of the agent to deploy
        config: Agent configuration dictionary
        secrets: Agent secrets dictionary
        project_id: Google Cloud project ID
        region: Google Cloud region
        dry_run: Whether to perform a dry run
        preserve_env: If True, use --update-env-vars instead of --set-env-vars to
                     preserve existing environment variables and secrets
        service_prefix: Service name prefix (e.g., "dev-", "stag-", or "")
        environment: Environment name (dev, stag, or prod)
        substituted_vars: Set of variables that were substituted
        secret_referenced_vars: Set of variables referenced in secrets

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
    base_service_name = cloud_run_config.get("service_name", f"{agent_name}-service")

    # Apply service prefix from CLI flags (or empty string for production)
    prefix = service_prefix if service_prefix is not None else ""
    service_name = f"{prefix}{base_service_name}"

    # Setup environment variables
    env_string, secret_manager_secrets, additional_processed_flags = setup_environment_variables(
        project_id, region, agent_name, cloud_run_config,
        substituted_vars or set(), secret_referenced_vars or set()
    )

    # Log deployment info
    logging.info(f"Service: {service_name}")
    if prefix and base_service_name != service_name:
        logging.info(f"  (base service name: {base_service_name}, prefix: '{prefix}')")
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
            secret_manager_secrets, additional_processed_flags, dry_run, preserve_env
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
