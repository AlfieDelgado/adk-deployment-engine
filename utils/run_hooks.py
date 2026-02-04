#!/usr/bin/env python3
"""Utility script for running deployment hooks defined in config.yaml."""

import argparse
import os
import subprocess
import sys
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
    if skip_hooks:
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
    parser = argparse.ArgumentParser(
        description="Run deployment hooks defined in agent config.yaml"
    )
    parser.add_argument("agent", help="Agent name")
    parser.add_argument(
        "stage",
        nargs="?",
        help="Hook stage (pre_deploy, post_deploy), or omit with --list/--manual"
    )
    parser.add_argument("--list", action="store_true", help="List all configured hooks")
    parser.add_argument("--manual", metavar="HOOK_PATH", help="Run a single hook manually")
    parser.add_argument("--skip-hooks", action="store_true", help="Skip running hooks")

    args = parser.parse_args()

    # Handle --list flag
    if args.list:
        list_hooks(args.agent)
        return

    # Handle --manual flag
    if args.manual:
        print(f"🔧 Running manual hook: {args.manual} for agent: {args.agent}")
        print(f"📋 Executing: {args.manual}\n")

        if run_hook_script(args.agent, args.manual):
            print(f"\n✅ Hook completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Hook failed")
            sys.exit(1)

    # Run hooks for a stage (stage is required unless --list or --manual)
    if not args.stage:
        parser.error("stage is required unless using --list or --manual")

    if run_hooks_for_stage(args.agent, args.stage, args.skip_hooks):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
