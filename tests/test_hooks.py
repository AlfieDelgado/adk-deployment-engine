"""Test deployment hooks functionality."""

import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd):
    """Run command and return result."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_hooks_run_without_skip(cleanup_test_markers):
    """Test that hooks run when --skip-hooks is NOT provided."""
    result = run_command([
        "python", "utils/run_hooks.py", "quickstart", "pre_deploy"
    ])

    # Check hook executed
    assert os.path.exists("/tmp/pre-deploy-ran.txt"), "Hook should have created marker file"
    assert "Pre-deployment tasks completed" in result.stdout, "Expected success message"
    assert result.returncode == 0, "Command should succeed"


def test_hooks_skip_with_flag(cleanup_test_markers):
    """Test that hooks are skipped when --skip-hooks is provided."""
    result = run_command([
        "python", "utils/run_hooks.py", "quickstart", "pre_deploy", "--skip-hooks"
    ])

    # Check hook was skipped
    assert not os.path.exists("/tmp/pre-deploy-ran.txt"), "Hook should NOT have created marker file"
    assert result.returncode == 0, "Command should succeed"


def test_list_hooks():
    """Test listing hooks from config.yaml."""
    result = run_command([
        "python", "utils/run_hooks.py", "quickstart", "--list"
    ])

    assert "pre_deploy" in result.stdout, "Should show pre_deploy hooks"
    assert "post_deploy" in result.stdout, "Should show post_deploy hooks"
    assert "scripts/pre-deploy.sh" in result.stdout, "Should show pre-deploy.sh"
    assert "scripts/post-deploy.sh" in result.stdout, "Should show post-deploy.sh"
    assert result.returncode == 0, "Command should succeed"


def test_manual_hook_execution(cleanup_test_markers):
    """Test manual execution of a single hook."""
    result = run_command([
        "python", "utils/run_hooks.py", "quickstart", "--manual", "scripts/pre-deploy.sh"
    ])

    assert os.path.exists("/tmp/pre-deploy-ran.txt"), "Manual hook should have created marker file"
    assert "Hook completed successfully" in result.stdout, "Expected success message"
    assert result.returncode == 0, "Command should succeed"


def test_post_deploy_hook(cleanup_test_markers):
    """Test post-deploy hook execution."""
    result = run_command([
        "python", "utils/run_hooks.py", "quickstart", "post_deploy"
    ])

    assert os.path.exists("/tmp/post-deploy-ran.txt"), "Post-deploy hook should have created marker file"
    assert "Post-deployment tasks completed" in result.stdout, "Expected success message"
    assert result.returncode == 0, "Command should succeed"


if __name__ == "__main__":
    # Run with pytest
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
