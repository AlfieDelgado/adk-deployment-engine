#!/usr/bin/env python3
"""Utility script for makefile environment loading and gcloud commands."""

import os
import sys
import subprocess
import yaml
from pathlib import Path

# Add utils to path for imports
sys.path.append(str(Path(__file__).parent))
from env_manager import load_environment_files


def get_agents_dir():
    """Get the agents directory from environment variable or default.

    Returns:
        str: Path to the agents directory
    """
    return os.environ.get('AGENTS_DIR', 'agents')

def main():
    if len(sys.argv) != 3:
        print("❌ Error: Usage: python makefile_helper.py delete <agent-name>")
        sys.exit(1)

    command = sys.argv[1]
    agent_name = sys.argv[2]

    if command != 'delete':
        print("❌ Error: Only 'delete' command is supported")
        sys.exit(1)

    # Auto-detect service name from agent's config.yaml
    agents_dir = get_agents_dir()

    # Determine project root using the same logic as other utils
    current_dir = Path(__file__).parent
    project_root = current_dir.parent

    # Check if we're running as submodule using DEPLOYMENT_ENGINE_DIR environment variable
    deployment_engine_dir = os.environ.get('DEPLOYMENT_ENGINE_DIR')
    if deployment_engine_dir and deployment_engine_dir != '.':
        # We're running from parent project, go up to main project root
        project_root = project_root.parent

    config_path = project_root / f"{agents_dir}/{agent_name}/config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            service_name = config.get('cloud_run', {}).get('service_name')
            if not service_name:
                print(f"❌ Error: service_name not found in {config_path}")
                sys.exit(1)
            print(f"🔍 Auto-detected service name: {service_name}")
    except FileNotFoundError:
        print(f"❌ Error: Config file not found: {config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        sys.exit(1)

    # Load environment with agent-specific support
    env = load_environment_files(agent_name)

    # Get required environment variables
    project = env.get('GOOGLE_CLOUD_PROJECT')
    location = env.get('GOOGLE_CLOUD_LOCATION')
    region = env.get('GOOGLE_CLOUD_LOCATION_DEPLOY') or location

    print('📋 Loading environment configuration...')

    # Validate project and location
    if not project:
        print(f'❌ Error: GOOGLE_CLOUD_PROJECT not found in .env or {agents_dir}/{agent_name}/.env.secrets')
        sys.exit(1)

    if not location:
        print(f'❌ Error: GOOGLE_CLOUD_LOCATION not found in .env or {agents_dir}/{agent_name}/.env.secrets')
        sys.exit(1)

    print(f'✅ Using deployment region: {region}')

    print(f'🔧 Using agent-specific configuration from {agents_dir}/{agent_name}/.env.secrets')
    print(f'🗑️  Deleting Cloud Run service: {service_name}...')

    # Execute gcloud delete command
    cmd = ['gcloud', 'run', 'services', 'delete', service_name, '--region=' + region, '--quiet']

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print('❌ Error: gcloud command not found. Please install Google Cloud SDK.')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Error executing gcloud command: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
