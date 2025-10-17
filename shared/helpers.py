from pathlib import Path

from dotenv import load_dotenv


def load_env_vars():
    # Load multiple .env files in priority order
    agent_dir = Path(__file__).parent
    env_files = [
        agent_dir.parent.parent / ".env",
        agent_dir / ".env.secrets",
    ]

    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
