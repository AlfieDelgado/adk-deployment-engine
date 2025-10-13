"""Testing utilities module for ADK Agents deployment.

This module provides testing functionality for build directory structure,
Dockerfile generation, and other deployment components.
"""

import logging
import os
import shutil

from pathlib import Path


def print_tree(directory, prefix="", max_depth=3, current_depth=0):
    """Print directory tree structure.

    Args:
        directory: Directory to print
        prefix: Prefix for current line
        max_depth: Maximum depth to traverse
        current_depth: Current depth level
    """
    if current_depth >= max_depth:
        return

    items = sorted(directory.iterdir())
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        logging.info(f"{prefix}{current_prefix}{item.name}")

        if item.is_dir() and current_depth < max_depth - 1:
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(item, next_prefix, max_depth, current_depth + 1)


def test_build_structure(agent_name, load_agent_config_func, create_build_directory_func):
    """Test the build directory structure for a specific agent.

    Args:
        agent_name: Name of the agent to test
        load_agent_config_func: Function to load agent configuration
        create_build_directory_func: Function to create build directory

    Returns:
        bool: True if test passed, False otherwise
    """
    print(f"🧪 Testing build structure for agent: {agent_name}")

    # Load configuration using provided function
    result = load_agent_config_func(agent_name)
    if not result:
        print(f"❌ Failed to load config for agent: {agent_name}")
        return False
    config, _, _ = result

    # Create build directory using provided function
    build_dir = create_build_directory_func(agent_name, config)
    if not build_dir:
        print(f"❌ Failed to create build directory for: {agent_name}")
        return False

    try:
        # Show the directory tree structure
        print("📋 Build directory tree structure:")
        print_tree(build_dir)

        # Verify key files exist
        agent_dest = build_dir / agent_name
        checks = [
            (build_dir / "main.py", "main.py in build root"),
            (build_dir / "requirements.txt", "requirements.txt in build root"),
            (agent_dest / "agent.py", f"agent.py in {agent_name}/"),
            (agent_dest / "__init__.py", f"__init__.py in {agent_name}/"),
            (agent_dest / "config.yaml", f"config.yaml in {agent_name}/"),
        ]

        all_good = True
        for file_path, description in checks:
            if file_path.exists():
                print(f"   ✅ {description}")
            else:
                print(f"   ❌ {description} - MISSING")
                all_good = False

        return all_good

    finally:
        # Cleanup test directory
        shutil.rmtree(build_dir, ignore_errors=True)


def test_dockerfile_generation(agent_name, load_agent_config_func, modify_dockerfile_template_func):
    """Test the Dockerfile generation for a specific agent.

    Args:
        agent_name: Name of the agent to test
        load_agent_config_func: Function to load agent configuration
        modify_dockerfile_template_func: Function to modify Dockerfile template

    Returns:
        bool: True if test passed, False otherwise
    """
    print(f"🧪 Testing Dockerfile generation for agent: {agent_name}")

    # Load configuration using provided function
    result = load_agent_config_func(agent_name)
    if not result:
        print(f"❌ Failed to load config for agent: {agent_name}")
        return False
    config, _, _ = result

    print("✅ Agent configuration loaded successfully")
    print(f"📝 Description: {config.get('description', 'No description')}")
    print(f"🏷️  Tags: {', '.join(config.get('tags', []))}")

    # Show Docker configuration
    docker_config = config.get("docker", {})
    print(f"🐳 Base Image: {docker_config.get('base_image', 'python:3.13-slim')}")
    if docker_config.get('system_packages'):
        print(f"📦 System Packages: {', '.join(docker_config['system_packages'])}")
    if docker_config.get('extra_steps'):
        print(f"⚙️  Extra Steps: {len(docker_config['extra_steps'])}")

    # Generate the Dockerfile using provided function
    dockerfile_content = modify_dockerfile_template_func(agent_name, config)
    if not dockerfile_content:
        print("❌ Failed to generate Dockerfile")
        return False

    print("✅ Dockerfile generated successfully!")

    # Save to a test file in agent's folder
    agents_dir = os.environ.get('AGENTS_DIR', 'agents')
    test_dockerfile = Path(f"{agents_dir}/{agent_name}/Dockerfile.test")
    with open(test_dockerfile, 'w') as f:
        f.write(dockerfile_content)

    print(f"📝 Test Dockerfile saved to: {test_dockerfile}")

    # Show first few lines of generated Dockerfile
    lines = dockerfile_content.split('\n')
    print("📄 Generated Dockerfile preview:")
    print("-" * 40)
    for line in lines[:10]:  # Show first 10 lines
        print(line)
    if len(lines) > 10:
        print(f"... ({len(lines) - 10} more lines)")
    print("-" * 40)

    return True
