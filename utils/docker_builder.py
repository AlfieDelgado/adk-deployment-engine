"""Docker build operations module for ADK Agents deployment.

This module provides Docker-related functionality including template modification,
build directory creation, and file management.
"""

import fnmatch
import logging
import shutil
import tempfile
from pathlib import Path


def modify_dockerfile_template(agent_name, config):
    """Modify Dockerfile.template based on agent configuration.

    Args:
        agent_name: Name of the agent
        config: Agent configuration dictionary

    Returns:
        str: Modified Dockerfile content
    """
    # Read the template
    template_path = Path("Dockerfile.template")
    if not template_path.exists():
        raise FileNotFoundError(f"Dockerfile.template not found at {template_path}")

    with open(template_path) as f:
        dockerfile_content = f.read()

    # Docker configuration
    docker_config = config.get("docker", {})
    system_packages = docker_config.get("system_packages", [])
    extra_steps = docker_config.get("extra_steps", [])

    # Replace placeholders with actual content
    replacements = {
        "{AGENT_NAME}": agent_name
    }

    # Handle system packages
    if system_packages:
        packages_block = "RUN apt-get update && apt-get install -y \\"
        for i, pkg in enumerate(system_packages):
            if i == len(system_packages) - 1:
                packages_block += f"\n        {pkg} \\"
            else:
                packages_block += f"\n        {pkg} &&"
        packages_block += "\n    rm -rf /var/lib/apt/lists/*"
        replacements["# SYSTEM_PACKAGES_PLACEHOLDER"] = packages_block
    else:
        replacements["# SYSTEM_PACKAGES_PLACEHOLDER"] = ""

    # Handle extra steps
    if extra_steps:
        extra_steps_block = "# Extra configuration steps\n"
        extra_steps_block += "\n".join(extra_steps)
        replacements["# EXTRA_STEPS_PLACEHOLDER"] = extra_steps_block
    else:
        replacements["# EXTRA_STEPS_PLACEHOLDER"] = ""

    # Apply all replacements
    for placeholder, replacement in replacements.items():
        dockerfile_content = dockerfile_content.replace(placeholder, replacement)

    return dockerfile_content


def parse_dockerignore():
    """Parse .dockerignore file and return list of ignore patterns.

    Returns:
        list: Ignore patterns from .dockerignore
    """
    dockerignore_path = Path(".dockerignore")
    ignore_patterns = []

    if dockerignore_path.exists():
        with open(dockerignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    ignore_patterns.append(line)

    return ignore_patterns


def should_ignore(path, ignore_patterns, base_path):
    """Check if a path should be ignored based on .dockerignore patterns.

    Args:
        path: Path to check
        ignore_patterns: List of ignore patterns
        base_path: Base path for relative calculations

    Returns:
        bool: True if path should be ignored
    """
    relative_path = path.relative_to(base_path) if path.is_absolute() else path

    # Convert path to string for pattern matching
    path_str = str(relative_path)

    for pattern in ignore_patterns:
        # Handle patterns with ** (recursive)
        if '**' in pattern:
            # Convert **/pattern to */pattern for fnmatch
            pattern = pattern.replace('**/', '*')
            # Convert pattern/** to pattern/*
            if pattern.endswith('/**'):
                pattern = pattern[:-3] + '/*'

        # Check if path matches pattern exactly
        if fnmatch.fnmatch(path_str, pattern):
            return True

        # Check if directory name matches pattern (for patterns like __pycache__)
        if path.is_dir() and fnmatch.fnmatch(path.name, pattern):
            return True

        # Also check if any parent directory matches
        path_parts = Path(path_str).parts
        for i in range(len(path_parts)):
            parent_path = '/'.join(path_parts[:i+1])
            if fnmatch.fnmatch(parent_path, pattern):
                return True

        # Special handling for patterns ending with / (directories)
        if pattern.endswith('/') and path.is_dir():
            dir_pattern = pattern[:-1]  # Remove trailing /
            # Check if directory name matches
            if fnmatch.fnmatch(path.name, dir_pattern):
                return True
            # Check if relative path matches
            if fnmatch.fnmatch(path_str, dir_pattern):
                return True

    return False


def copy_directory_with_ignore(src, dst, ignore_patterns, is_agent_dir=False):
    """Copy directory while respecting .dockerignore patterns.

    Args:
        src: Source directory
        dst: Destination directory
        ignore_patterns: List of ignore patterns
        is_agent_dir: Whether this is an agent directory (special handling)
    """
    for item in src.iterdir():
        # Check if the item itself should be ignored
        if should_ignore(item, ignore_patterns, src):
            logging.debug(f"Ignoring: {item.name}")
            continue

        # Skip requirements.txt in agent directories (copied separately to root)
        if is_agent_dir and item.name == "requirements.txt":
            logging.debug(f"Skipping agent requirements.txt: {item.name} (already copied to root)")
            continue

        # Skip .env.* files in agent directories (.env.secrets, .env.example, etc.)
        if is_agent_dir and item.name.startswith(".env"):
            logging.debug(f"Skipping {item.name}: (environment file - not for deployment)")
            continue

        if item.is_dir():
            dst_dir = dst / item.name
            dst_dir.mkdir(exist_ok=True)
            copy_directory_with_ignore(item, dst_dir, ignore_patterns, is_agent_dir)
        else:
            shutil.copy2(item, dst)
            logging.debug(f"Copied: {item.name}")


def create_build_directory(agent_name, config):
    """Create and setup the build directory with all necessary files.

    Args:
        agent_name: Name of the agent
        config: Agent configuration

    Returns:
        Path: Build directory path or None if failed
    """
    # Create temporary build directory
    build_dir = Path(tempfile.mkdtemp(prefix=f"adk-build-{agent_name}-"))
    logging.debug(f"Created temporary build directory: {build_dir}")

    # Parse .dockerignore patterns
    ignore_patterns = parse_dockerignore()
    logging.debug(f"Loaded {len(ignore_patterns)} ignore patterns from .dockerignore")

    try:
        # Copy main.py to build directory
        main_py_path = Path("main.py")
        if not main_py_path.exists():
            raise FileNotFoundError("main.py not found in project root")
        shutil.copy(main_py_path, build_dir / "main.py")
        logging.debug("Copied main.py to build directory")

        # Copy agent requirements.txt as requirements.txt in build directory
        agent_requirements = Path(f"agents/{agent_name}/requirements.txt")
        if agent_requirements.exists():
            shutil.copy(agent_requirements, build_dir / "requirements.txt")
            logging.debug("Copied agent requirements.txt to build directory")
        else:
            # Create empty requirements.txt if agent doesn't have one
            (build_dir / "requirements.txt").touch()
            logging.debug("Created empty requirements.txt in build directory")

        # Copy entire agent directory to build directory root, respecting .dockerignore
        agent_source = Path(f"agents/{agent_name}")
        if not agent_source.exists():
            raise FileNotFoundError(f"Agent directory not found: {agent_source}")

        agent_dest = build_dir / agent_name
        agent_dest.mkdir(exist_ok=True)
        copy_directory_with_ignore(agent_source, agent_dest, ignore_patterns, is_agent_dir=True)
        logging.debug(f"Copied agent {agent_name} to build directory root (respecting .dockerignore)")

        return build_dir

    except Exception as e:
        # Cleanup build directory on error
        shutil.rmtree(build_dir, ignore_errors=True)
        logging.error(f"Error setting up build directory: {e}")
        return None


def generate_deployment_artifacts(agent_name, config, build_dir):
    """Generate Dockerfile and other deployment artifacts.

    Args:
        agent_name: Name of the agent
        config: Agent configuration
        build_dir: Build directory path

    Returns:
        str: Dockerfile content
    """
    # Modify Dockerfile template
    logging.info("🔨 Modifying Dockerfile template...")
    dockerfile_content = modify_dockerfile_template(agent_name, config)

    # Write Dockerfile to build directory
    dockerfile_path = build_dir / "Dockerfile"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    return dockerfile_content


def cleanup_deployment_resources(build_dir, original_cwd):
    """Clean up temporary resources after deployment.

    Args:
        build_dir: Build directory to cleanup
        original_cwd: Original working directory to restore
    """
    import os

    # Change back to original directory
    os.chdir(original_cwd)
    logging.debug(f"Changed back to original directory: {original_cwd}")

    # Cleanup: remove temporary build directory
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
        logging.debug(f"Cleaned up temporary build directory: {build_dir}")

    # Cleanup: remove generated Dockerfile from root
    root_dockerfile = Path("Dockerfile")
    if root_dockerfile.exists():
        root_dockerfile.unlink()
