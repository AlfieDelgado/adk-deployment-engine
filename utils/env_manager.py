"""Environment management module for ADK Agents deployment.

This module provides simplified environment variable management using the same
pattern as agent.py, along with Secret Manager processing and configuration handling.
"""

import os
import re
import logging

from pathlib import Path
from dotenv import dotenv_values


class ConfigurationError(Exception):
    """Raised when there's a configuration error."""
    pass


class EnvironmentError(Exception):
    """Raised when there's an environment variable error."""
    pass


def strip_quotes(value):
    """Strip surrounding quotes from a string if present."""
    if value and isinstance(value, str):
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            return value[1:-1]
    return value


def get_env_var(key, default=None):
    """Get environment variable with optional quote stripping."""
    value = os.getenv(key, default)
    return strip_quotes(value)


def load_environment_files(agent_name=None):
    """Load environment files using the same pattern as agent.py.

    Args:
        agent_name: Optional agent name to load agent-specific .env.secrets

    Returns:
        dict: Loaded environment variables
    """
    env_vars = {}

    # Determine the project root by going up from utils directory
    current_dir = Path(__file__).parent
    project_root = current_dir.parent

    # Check if we're running as submodule using DEPLOYMENT_ENGINE_DIR environment variable
    deployment_engine_dir = os.environ.get('DEPLOYMENT_ENGINE_DIR')
    if deployment_engine_dir and deployment_engine_dir != '.':
        # We're running from parent project, go up to main project root
        project_root = project_root.parent

    # Load multiple .env files in priority order (same as agent.py)
    env_files = [
        project_root / ".env",  # Global .env file
    ]

    # Add agent-specific .env.secrets if agent_name provided
    if agent_name:
        agents_dir = os.environ.get('AGENTS_DIR', 'agents')
        env_files.append(project_root / f"{agents_dir}/{agent_name}/.env.secrets")

    for env_file in env_files:
        if env_file.exists():
            logging.debug(f"Loading environment from: {env_file}")
            # Use dotenv_values to get variables without modifying os.environ
            file_vars = dotenv_values(env_file)
            env_vars.update(file_vars)

    return env_vars


def substitute_env_vars(config, agent_name=None):
    """Substitute environment variables in config values using ${VAR_NAME} syntax.

    Args:
        config: Configuration dictionary or value
        agent_name: Optional agent name for loading agent-specific env files

    Returns:
        tuple: (substituted_config, substituted_vars)
    """
    # Load environment variables using simplified approach
    env_vars = load_environment_files(agent_name)

    # Track which variables are substituted
    substituted_vars = set()

    def replace_var(match):
        var_expr = match.group(1)
        var_name = var_expr
        default_value = None

        # Handle default values: VAR_NAME:-default_value
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)

        # Get value from loaded environment variables
        value = env_vars.get(var_name)

        if value is None:
            # Use default value if provided
            if default_value is not None:
                value = default_value
                logging.info(f"Using default value for {var_name}")
            else:
                logging.error(f"Environment variable {var_name} not found and no default provided")
                return match.group(0)  # Return original placeholder

        # Track this variable as substituted
        substituted_vars.add(var_name)
        return str(value)

    def recursive_substitute(obj):
        if isinstance(obj, dict):
            return {k: recursive_substitute(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [recursive_substitute(item) for item in obj]
        elif isinstance(obj, str):
            # Replace ${VAR_NAME} patterns
            return re.sub(r'\$\{([^}]+)\}', replace_var, obj)
        else:
            return obj

    # Apply substitution and return both result and tracking info
    substituted_config = recursive_substitute(config)
    return substituted_config, substituted_vars


def process_secret_manager_config(additional_flags):
    """Process Secret Manager configurations from additional flags.

    Args:
        additional_flags: List of additional Cloud Run flags

    Returns:
        tuple: (secret_secrets, referenced_vars, secret_env_vars, additional_processed_flags)
    """
    secret_secrets = []
    referenced_vars = set()
    secret_env_vars = set()  # Environment variables that have secrets
    additional_processed_flags = []  # All non-secret flags after substitution

    def process_secret_string(secrets_str):
        """Process a secrets string and extract secret configurations."""
        # Parse multiple secrets separated by commas
        secret_pairs = secrets_str.split(",")
        for pair in secret_pairs:
            if "=" in pair and ":" in pair:
                env_var, secret_name_version = pair.split("=", 1)
                if ":" in secret_name_version:
                    secret_name, version = secret_name_version.split(":", 1)

                    # Check if secret name references a variable
                    if secret_name.startswith("${") and secret_name.endswith("}"):
                        var_name = secret_name[2:-1]  # Extract variable name
                        referenced_vars.add(var_name)
                    else:
                        # It's a literal secret name - track the environment variable name
                        secret_secrets.append((secret_name, env_var))
                        secret_env_vars.add(env_var)  # Key fix: track env var name

                    logging.debug(f"Found Secret Manager secret: {env_var} <- {secret_name}:{version}")

    # Process from additional_flags
    for flag in additional_flags:
        if flag.startswith("--update-secrets="):
            secrets_part = flag[len("--update-secrets="):]
            secrets_part = secrets_part.strip("'\"")
            process_secret_string(secrets_part)
        elif flag.startswith("--service-account="):
            service_account_value = flag[len("--service-account="):]
            # Extract service account variable name if it's a substitution
            if service_account_value.startswith("${") and service_account_value.endswith("}"):
                var_name = service_account_value[2:-1]
                referenced_vars.add(var_name)
                # CRITICAL FIX: Add SERVICE_ACCOUNT to excluded variables
                secret_env_vars.add("SERVICE_ACCOUNT")
            # Add service account flag to additional processed flags
            additional_processed_flags.append(flag)
        else:
            # Add all other flags (memory, cpu, timeout, etc.) to additional processed flags
            additional_processed_flags.append(flag)

    return secret_secrets, referenced_vars, secret_env_vars, additional_processed_flags


def setup_environment_variables(project_id, region, agent_name, cloud_run_config, substituted_vars, secret_referenced_vars):
    """Setup and process environment variables for deployment with Secret Manager support.

    Args:
        project_id: Google Cloud project ID
        region: Google Cloud region
        agent_name: Agent name
        cloud_run_config: Cloud Run configuration
        substituted_vars: Set of variables that were substituted
        secret_referenced_vars: Set of variables referenced in secrets

    Returns:
        tuple: (env_string, secret_manager_secrets, additional_processed_flags)
    """
    # Strip quotes from project_id and region parameters
    stripped_project_id = strip_quotes(project_id)
    stripped_region = strip_quotes(region)

    # Load environment variables using simplified approach
    env_vars = load_environment_files(agent_name)

    # Extract Secret Manager configurations
    additional_flags = cloud_run_config.get("additional_flags", [])
    secret_manager_secrets, referenced_vars, secret_manager_env_vars, additional_processed_flags = process_secret_manager_config(additional_flags)

    # Check API configuration and enforce mutual exclusivity (ADK 1.22.1+)
    use_vertexai = (env_vars.get("GOOGLE_GENAI_USE_VERTEXAI") or get_env_var("GOOGLE_GENAI_USE_VERTEXAI", "false")).lower() == "true"

    # Track which variables should be excluded based on auth mode
    excluded_by_auth_mode = set()

    if use_vertexai:
        # Vertex AI mode: GOOGLE_API_KEY must NOT be deployed
        excluded_by_auth_mode.add("GOOGLE_API_KEY")
        logging.info("✅ Vertex AI mode: GOOGLE_API_KEY will be excluded from deployment")
    else:
        # Gemini Developer API mode: Only GOOGLE_API_KEY needed
        # (GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION kept for session service)
        logging.info("✅ Gemini Developer API mode: Using GOOGLE_API_KEY")

    # Filter Secret Manager secrets based on auth mode
    filtered_secrets = []
    for secret_name, env_var_name in secret_manager_secrets:
        if env_var_name in excluded_by_auth_mode:
            logging.info(f"⏭️  Skipping Secret Manager secret: {env_var_name} (excluded by auth mode)")
        else:
            logging.info(f"🔐 Secret Manager: {env_var_name} will be loaded from secret '{secret_name}'")
            filtered_secrets.append((secret_name, env_var_name))

    # Build environment variable list with essential variables
    base_env_vars = [
        f"GOOGLE_CLOUD_PROJECT={stripped_project_id}",
        f"GOOGLE_CLOUD_LOCATION={stripped_region}"
    ]

    # Define excluded variables (handled elsewhere)
    # Add GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION to prevent duplicates from .env files
    global_env_vars = ["GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]
    excluded_vars = secret_manager_env_vars | substituted_vars | secret_referenced_vars | set(referenced_vars)
    has_api_key = False

    # Load global environment variables (excluding handled variables)
    # Skip GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION as they're already set above
    for env_var in global_env_vars:
        if env_var not in excluded_vars and env_var not in excluded_by_auth_mode and env_var not in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]:
            value = env_vars.get(env_var) or get_env_var(env_var)
            if value:
                base_env_vars.append(f"{env_var}={value}")
                if env_var == "GOOGLE_API_KEY":
                    has_api_key = True

    # Load agent secrets (excluding handled variables)
    for key, value in env_vars.items():
        if key not in excluded_vars and key not in global_env_vars and key not in excluded_by_auth_mode:
            stripped_value = strip_quotes(value)
            base_env_vars.append(f"{key}={stripped_value}")
            if key == "GOOGLE_API_KEY":
                has_api_key = True

    env_string = ",".join(base_env_vars)

    # Log API configuration status
    logging.info("🤖 API Configuration:")
    if use_vertexai:
        logging.info(f"✅ Using Vertex AI (project: {project_id}, region: {region})")
    elif "GOOGLE_API_KEY" in secret_manager_env_vars:
        logging.info("✅ Using Google AI API (with API key from Secret Manager)")
    elif has_api_key:
        logging.info("✅ Using Google AI API (with API key from .env)")
    else:
        logging.error("Missing API configuration!")
        logging.info("  - Either set GOOGLE_GENAI_USE_VERTEXAI=true in .env")
        logging.info("  - Or add GOOGLE_API_KEY to .env")
        logging.info(f"  - Or add GOOGLE_API_KEY to agents/{agent_name}/.env.secrets")
        logging.info("  - Or configure Secret Manager in config.yaml")

    logging.debug(f"Environment variables: {len(base_env_vars)}, Secrets loaded: {len(env_vars)}, Secret Manager secrets: {len(filtered_secrets)}, Additional flags: {len(additional_processed_flags)}")

    return env_string, filtered_secrets, additional_processed_flags
