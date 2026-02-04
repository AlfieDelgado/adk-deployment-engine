#!/usr/bin/env python3
"""Utility script for running deployment hooks defined in config.yaml."""

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


def get_project_root():
    """Get the project root directory.

    Returns:
        Path: Project root directory
    """
    current_dir = Path(__file__).parent
    deployment_engine_dir = os.environ.get('DEPLOYMENT_ENGINE_DIR')

    if deployment_engine_dir and deployment_engine_dir != '.':
        # We're running from parent project, go up to main project root
        return current_dir.parent.parent

    return current_dir.parent


def load_agent_config(agent_name):
    """Load agent's config.yaml file.

    Args:
        agent_name: Name of the agent

    Returns:
        dict: Parsed YAML configuration
    """
    agents_dir = get_agents_dir()
    project_root = get_project_root()
    config_path = project_root / f"{agents_dir}/{agent_name}/config.yaml"

    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: Config file not found: {config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        sys.exit(1)


def run_hook_script(agent_name, hook_path):
    """Run a single hook script.

    Args:
        agent_name: Name of the agent
        hook_path: Path to the hook script (relative to agent directory)

    Returns:
        bool: True if successful, False otherwise
    """
    agents_dir = get_agents_dir()
    project_root = get_project_root()
    script_path = project_root / f"{agents_dir}/{agent_name}/{hook_path}"

    if not script_path.exists():
        print(f"❌ Error: Hook script not found: {script_path}")
        return False

    try:
        # Make script executable
        os.chmod(script_path, 0o755)

        # Run the script
        result = subprocess.run(
            [str(script_path), agent_name],
            capture_output=False,
            text=True
        )

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running hook script: {e}")
        return False


def run_hooks_for_stage(agent_name, stage, skip_hooks=False):
    """Run all hooks for a given stage.

    Args:
        agent_name: Name of the agent
        stage: Stage to run hooks for (e.g., 'pre_deploy', 'post_deploy')
        skip_hooks: If True, skip running hooks

    Returns:
        bool: True if all hooks succeeded, False otherwise
    """
    if skip_hooks == "true":
        return True

    config = load_agent_config(agent_name)
    hooks = config.get('hooks', {})
    stage_hooks = hooks.get(stage, [])

    if not stage_hooks:
        # No hooks defined for this stage, that's okay
        return True

    print(f"🔧 Running {stage} hooks for {agent_name}...")

    for hook_path in stage_hooks:
        print(f"   📋 Executing: {hook_path}")

        if not run_hook_script(agent_name, hook_path):
            print(f"❌ Hook failed: {hook_path}")
            return False

        print(f"   ✅ Hook completed: {hook_path}")

    print(f"✅ All {stage} hooks completed\n")
    return True


def list_hooks(agent_name):
    """List all hooks defined in agent's config.yaml.

    Args:
        agent_name: Name of the agent
    """
    config = load_agent_config(agent_name)
    hooks = config.get('hooks', {})

    if not hooks:
        print("   No hooks defined in config.yaml")
        return

    for stage, hook_list in hooks.items():
        print(f"\n   {stage}:")
        for hook_path in hook_list:
            print(f"     - {hook_path}")


def main():
    if len(sys.argv) < 3:
        print("❌ Error: Usage: python run_hooks.py <agent-name> <stage> [--list] [--manual <hook-path>]")
        print("\n   Examples:")
        print("   python run_hooks.py my-agent pre_deploy")
        print("   python run_hooks.py my-agent post_deploy")
        print("   python run_hooks.py my-agent --list")
        print("   python run_hooks.py my-agent --manual scripts/mcp-sync.sh")
        sys.exit(1)

    agent_name = sys.argv[1]
    second_arg = sys.argv[2]

    # Handle --list flag
    if second_arg == '--list':
        list_hooks(agent_name)
        return

    # Handle --manual flag
    if second_arg == '--manual':
        if len(sys.argv) < 4:
            print("❌ Error: --manual requires a hook path")
            print("   Usage: python run_hooks.py <agent-name> --manual <hook-path>")
            sys.exit(1)

        hook_path = sys.argv[3]
        print(f"🔧 Running manual hook: {hook_path} for agent: {agent_name}")
        print(f"📋 Executing: {hook_path}\n")

        if run_hook_script(agent_name, hook_path):
            print(f"\n✅ Hook completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Hook failed")
            sys.exit(1)

    # Run hooks for a stage
    stage = second_arg
    skip_hooks = sys.argv[3] if len(sys.argv) > 3 else "false"

    if run_hooks_for_stage(agent_name, stage, skip_hooks):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
