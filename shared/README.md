# ADK Shared Utilities

Common utilities for ADK agents.

## 📦 Installation

Add to your agent's `requirements.txt`:

```bash
adk-shared @ git+https://github.com/AlfieDelgado/adk-deployment-engine.git@main#subdirectory=shared
```

## 🚀 Usage

```python
# Import in your agent
from adk_shared.helpers import load_env_vars

# Load environment variables
load_env_vars()
```

## 📋 Functions

### `load_env_vars()`

Loads environment variables from:
1. **Project root `.env`** (defaults)
2. **Agent directory `.env.secrets`** (overrides defaults)

**Example**:
```
your-project/
├── .env                    # Project defaults
├── agents/
│   └── your-agent/
│       ├── .env.secrets    # Agent overrides
│       └── agent.py
```

```python
# agents/your-agent/agent.py
from adk_shared.helpers import load_env_vars
import os

load_env_vars()
api_key = os.getenv('API_KEY')
```

## 🎯 Benefits

- ✅ Git-based installation
- ✅ Clean Python imports
- ✅ Works in development and production
- ✅ No deployment engine dependency required

## 📁 Structure

```
shared/
├── README.md
├── setup.py
└── adk_shared/
    ├── __init__.py
    └── helpers.py
```