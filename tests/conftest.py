"""Pytest configuration and fixtures for ADK deployment tests."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture(autouse=True)
def set_agents_dir():
    """Set AGENTS_DIR to agents-examples for all tests."""
    original = os.environ.get("AGENTS_DIR")
    os.environ["AGENTS_DIR"] = "agents-examples"
    yield
    if original:
        os.environ["AGENTS_DIR"] = original
    else:
        os.environ.pop("AGENTS_DIR", None)


@pytest.fixture
def cleanup_test_markers():
    """Clean up test marker files before and after tests."""
    markers = ["/tmp/pre-deploy-ran.txt", "/tmp/post-deploy-ran.txt"]
    for marker in markers:
        if os.path.exists(marker):
            os.remove(marker)
    yield
    for marker in markers:
        if os.path.exists(marker):
            os.remove(marker)
