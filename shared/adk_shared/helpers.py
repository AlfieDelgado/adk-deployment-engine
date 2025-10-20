from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def load_env_vars(directory: Optional[Path] = None):
    # Load multiple .env files in priority order
    if directory is not None:
        # Use the provided directory
        agent_dir = directory
        env_files = [
            agent_dir.parent.parent / ".env",
            agent_dir / ".env.secrets",
        ]
    else:
        # Use the default behavior (backward compatibility)
        agent_dir = Path(__file__).parent
        env_files = [
            agent_dir.parent.parent / ".env",
            agent_dir / ".env.secrets",
        ]

    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
