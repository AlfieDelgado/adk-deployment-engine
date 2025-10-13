#!/usr/bin/env python3
"""Vertex AI Agent Engine management module for ADK Agents.

This module provides functionality to create, list, and delete Vertex AI Agent Engines
with support for agent-specific configuration using the same environment loading pattern
as other utils modules.
"""

import argparse
import os
import sys
from typing import Optional, List

import vertexai
from vertexai import agent_engines

# Import modular components
from env_manager import load_environment_files, get_env_var, ConfigurationError


def get_agents_dir():
    """Get the agents directory from environment variable or default.

    Returns:
        str: Path to the agents directory
    """
    return os.environ.get('AGENTS_DIR', 'agents')


def check_existing_agent_engine(project_id: str, location: str, display_name: str) -> Optional[str]:
    """Check if an agent engine with the given display name already exists."""
    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # List all agent engines with filter
        existing_engines = list(agent_engines.list(filter=f"display_name=\"{display_name}\""))

        if existing_engines:
            latest_engine = existing_engines[0]
            engine_id = latest_engine.name.split("/")[-1]
            print("Found existing agent engine:")
            print(f"\tDisplay Name: {latest_engine.display_name}")
            print(f"\tEngine ID: {engine_id}")
            print(f"\tCreated: {latest_engine.create_time}")
            return engine_id

        return None
    except Exception as e:
        print(f"Error checking existing agent engines: {e}")
        return None


def list_agent_engines(project_id: str, location: str, display_name_filter: Optional[str] = None) -> List[dict]:
    """List agent engines with optional filtering by display name."""
    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Build filter if display name is provided
        filter_str = f"display_name=\"{display_name_filter}\"" if display_name_filter else None

        # List agent engines
        engines = list(agent_engines.list(filter=filter_str))

        if not engines:
            if display_name_filter:
                print(f"No agent engines found with display name: {display_name_filter}")
            else:
                print("No agent engines found")
            return []

        print(f"Found {len(engines)} agent engine(s):")
        engine_list = []
        for engine in engines:
            engine_id = engine.name.split("/")[-1]
            engine_info = {
                "id": engine_id,
                "display_name": engine.display_name,
                "description": getattr(engine, 'description', 'No description'),
                "created": getattr(engine, 'create_time', 'Unknown'),
                "state": getattr(engine, 'state', 'Unknown')
            }
            engine_list.append(engine_info)

            print(f"\t📁 {engine.display_name}")
            print(f"\t\tID: {engine_id}")
            print(f"\t\tDescription: {engine_info['description']}")
            print(f"\t\tCreated: {engine_info['created']}")
            print(f"\t\tState: {engine_info['state']}")
            print()

        return engine_list
    except Exception as e:
        print(f"Error listing agent engines: {e}")
        return []


def delete_agent_engine(project_id: str, location: str, display_name: str, force: bool = False) -> bool:
    """Delete an agent engine by display name."""
    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Find the agent engine
        engines = list(agent_engines.list(filter=f"display_name=\"{display_name}\""))

        if not engines:
            print(f"Error: No agent engine found with display name: {display_name}")
            return False

        if len(engines) > 1:
            print(f"Warning: Found {len(engines)} agent engines with display name '{display_name}'")
            print("This is unexpected. Please check manually.")
            return False

        engine = engines[0]
        engine_id = engine.name.split("/")[-1]

        # Confirm deletion unless force flag is set
        if not force:
            print(f"Agent engine to delete:")
            print(f"\tDisplay Name: {engine.display_name}")
            print(f"\tEngine ID: {engine_id}")
            print(f"\tCreated: {engine.create_time}")
            print()
            response = input("Are you sure you want to delete this agent engine? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Deletion cancelled.")
                return False

        # Delete the agent engine
        agent_engines.delete(engine_id)
        print(f"✅ Successfully deleted agent engine: {display_name}")
        return True

    except Exception as e:
        print(f"Error deleting agent engine: {e}")
        return False


def create_agent_engine(agent_name: Optional[str] = None) -> str:
    """Create a new agent engine or return existing one.

    Args:
        agent_name: Optional agent name for agent-specific configuration

    Returns:
        str: Agent engine ID
    """
    # Load environment variables using modular approach
    env_vars = load_environment_files(agent_name)

    # Get required environment variables with fallback
    project_id = env_vars.get("GOOGLE_CLOUD_PROJECT") or get_env_var("GOOGLE_CLOUD_PROJECT")
    location = env_vars.get("GOOGLE_CLOUD_LOCATION") or get_env_var("GOOGLE_CLOUD_LOCATION")
    agent_engine_name = env_vars.get("AGENT_ENGINE_NAME") or get_env_var("AGENT_ENGINE_NAME")

    if not all({project_id, location, agent_engine_name}):
        print("Error: Missing required environment variables:")
        missing = []
        if not project_id:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not location:
            missing.append("GOOGLE_CLOUD_LOCATION")
        if not agent_engine_name:
            missing.append("AGENT_ENGINE_NAME")
        print(f"\t{', '.join(missing)}")

        if agent_name:
            agents_dir = get_agents_dir()
            print(f"Please set these in {agents_dir}/{agent_name}/.env.secrets or global .env")
        else:
            print("Please set these in .env")
        sys.exit(1)

    # Show which environment source we're using
    if agent_name and env_vars.get("AGENT_ENGINE_NAME"):
        agents_dir = get_agents_dir()
        print(f"🔧 Using agent-specific configuration from {agents_dir}/{agent_name}/.env.secrets")
    else:
        print("🔧 Using global configuration from .env")

    # Check if agent engine already exists
    existing_engine_id = check_existing_agent_engine(project_id, location, agent_engine_name)

    if existing_engine_id:
        print(f"\n✅ Using existing agent engine with ID: {existing_engine_id}")
        return existing_engine_id

    # Create a new agent engine
    print(f"🚀 Creating new agent engine '{agent_engine_name}'...")

    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Create an empty Agent Engine instance (no code deployment)
        # This only takes a few seconds and gives you session management capabilities
        agent_engine = agent_engines.create(
            display_name=agent_engine_name,
            description="Agent Engine instance for session management only"
        )
        # Extract your agent_engine_id for VertexAiSessionService
        agent_engine_id = agent_engine.gca_resource.name.split("/")[-1]
        print("✅ Successfully created agent engine!")
        print(f"\tAgent Engine ID: {agent_engine_id}")
        print(f"\tFull Resource Name: {agent_engine.gca_resource.name}")

        # Show usage instructions
        if agent_name:
            agents_dir = get_agents_dir()
            print(f"\n💡 You can now use this AGENT_ENGINE_ID in your {agents_dir}/{agent_name}/.env.secrets:")
        else:
            print("\n💡 You can now use this AGENT_ENGINE_ID in your .env:")
        print(f"AGENT_ENGINE_ID={agent_engine_id}")

        return agent_engine_id

    except Exception as e:
        print(f"❌ Error creating agent engine: {e}")
        sys.exit(1)


def create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Vertex AI Agent Engine management for ADK Agents")
    parser.add_argument("agent_name", nargs="?", help="Agent name for agent-specific configuration")
    parser.add_argument("--list", action="store_true", help="List agent engines")
    parser.add_argument("--delete", action="store_true", help="Delete agent engine")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts (use with --delete)")
    return parser


def main():
    """Main entry point for agent engine management."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Load environment variables for project/region
    env_vars = load_environment_files(args.agent_name)
    project_id = env_vars.get("GOOGLE_CLOUD_PROJECT") or get_env_var("GOOGLE_CLOUD_PROJECT")
    location = env_vars.get("GOOGLE_CLOUD_LOCATION") or get_env_var("GOOGLE_CLOUD_LOCATION")

    if not project_id or not location:
        print("Error: Missing GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION in environment variables")
        sys.exit(1)

    # Route to appropriate handler based on command
    if args.list:
        agent_engine_name = env_vars.get("AGENT_ENGINE_NAME") or get_env_var("AGENT_ENGINE_NAME")
        list_agent_engines(project_id, location, agent_engine_name)
    elif args.delete:
        agent_engine_name = env_vars.get("AGENT_ENGINE_NAME") or get_env_var("AGENT_ENGINE_NAME")
        if not agent_engine_name:
            print("Error: AGENT_ENGINE_NAME not found in environment variables")
            sys.exit(1)
        success = delete_agent_engine(project_id, location, agent_engine_name, args.force)
        sys.exit(0 if success else 1)
    else:
        # Default: create agent engine
        agent_engine_id = create_agent_engine(args.agent_name)
        print(f"\n🎉 Agent engine setup complete!")


if __name__ == "__main__":
    main()
