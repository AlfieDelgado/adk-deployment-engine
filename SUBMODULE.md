# Using ADK Agents as Git Sub-module

> **🎯 Purpose**: Quick start guide for using ADK Agents as a sub-module in your projects while keeping your agents completely private.
>
> **📚 Complete Reference**: See [README.md](README.md) for the full project documentation and advanced configuration options.

## ⚡ 5-Minute Setup

```bash
# 1. Add sub-module to your project
git submodule add https://github.com/your-org/adk-deployment-engine.git

# 2. Create your 2-line makefile
echo "include adk-deployment-engine/makefile" > makefile
echo "AGENTS_DIR := agents" >> makefile

# 3. Set up environment
cp adk-deployment-engine/.env.example .env
# Edit .env with your Google Cloud settings
mkdir agents

# 4. Start deploying!
make deploy your-agent
```

> **💡 New to sub-modules?** See the detailed setup instructions below.

---

## 🚀 Detailed Setup

### 1. Add Sub-module

```bash
# Add the deployment engine to your project
git submodule add https://github.com/your-org/adk-deployment-engine.git
```

### 2. Create Your Makefile

```bash
# Create a simple 2-line makefile
echo "include adk-deployment-engine/makefile" > makefile
echo "AGENTS_DIR := agents" >> makefile
```

### 3. Set Up Environment

```bash
# Create your environment file
cp adk-deployment-engine/.env.example .env
# Edit .env with your Google Cloud settings

# Create your agents directory
mkdir agents
```

That's it! You can now use all the same make commands.

## 🎯 Most Common Commands

```bash
# Daily workflow
make list-agents                    # See your agents
make deploy your-agent               # Deploy your agent
make delete your-agent               # Delete deployment

# Testing & validation
make deploy-dry your-agent           # Test deployment (no actual deploy)
make test-build your-agent           # Test build structure
make test-dockerfile your-agent      # Test Dockerfile generation

# Agent Engine (for session management)
make create-agent-engine your-agent  # Create Vertex AI Agent Engine
make list-agent-engines your-agent   # List your agent engines
```

> **📚 Complete command reference**: See [README.md - Deployment Commands](README.md#deployment-commands) for all available commands and options.

## 📁 Project Structure

Your project will look like this:

```
your-project/
├── agents/                           # Your private agents (never shared)
│   └── my-secret-agent/
│       ├── config.yaml               # Your agent configuration
│       ├── agent.py                  # Your agent code
│       ├── requirements.txt          # Your dependencies
│       └── .env.secrets              # Your secrets (never committed)
├── makefile                          # Your 2-line makefile
├── .env                              # Your environment variables
└── adk-deployment-engine/            # Sub-module
    ├── makefile                      # Deployment engine makefile
    ├── utils/                        # All deployment utilities
    └── agents-examples/              # Example agents (for reference)
```

## 🔧 Configuration

### Makefile (2 lines)

```makefile
include adk-deployment-engine/makefile
AGENTS_DIR := agents
```

- `include adk-deployment-engine/makefile`: Imports all deployment commands
- `AGENTS_DIR := agents`: Tells the engine where your agents are located

### Environment Variables (.env)

```bash
# Required Google Cloud settings
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# API configuration
GOOGLE_GENAI_USE_VERTEXAI="True"
# OR
GOOGLE_API_KEY="your-api-key-here"
```

## 🤖 Creating Your First Agent

### Quick Agent Setup

```bash
# 1. Create agent directory
mkdir agents/my-agent

# 2. Create basic configuration
cat > agents/my-agent/config.yaml << EOF
description: My first agent
tags: [my-agent, production]

docker:
  base_image: python:3.13-slim

cloud_run:
  service_name: my-agent-service
  additional_flags:
    - --memory=1Gi
    - --cpu=0.5
    - --timeout=300s
EOF

# 3. Create basic agent code
cat > agents/my-agent/agent.py << EOF
#!/usr/bin/env python3
"""My first ADK Agent."""

def main():
    print("Agent ready for deployment!")

if __name__ == "__main__":
    main()
EOF

# 4. Add secrets (optional)
cat > agents/my-agent/.env.secrets << EOF
SERVICE_ACCOUNT="my-agent-sa@project.iam.gserviceaccount.com"
SECRET_NAME="my-agent-api-key"
EOF

# 5. Deploy!
make deploy my-agent
```

> **📚 Detailed examples**: See [README.md - Configuration Examples](README.md#configuration-examples) for production-ready configurations and advanced setups.

## 📋 Available Commands

All the same commands from the standalone project work:

### Agent Management
```bash
make list-agents                    # List your agents
make deploy my-agent               # Deploy specific agent
make deploy-dry my-agent           # Test deployment (dry run)
```

### Agent Engine Management
```bash
make create-agent-engine my-agent  # Create Vertex AI Agent Engine
make list-agent-engines my-agent   # List agent engines
make delete-agent-engine my-agent  # Delete agent engine
```

### Service Management
```bash
make delete my-agent                # Delete Cloud Run service
```

### Testing
```bash
make test-build my-agent           # Test build structure
make test-dockerfile my-agent      # Test Dockerfile generation
```

### Project Setup
```bash
make enable-services               # Enable required Google Cloud APIs
```

## 🔄 Getting Updates

When the deployment engine is improved, you can easily get the latest changes:

```bash
# Update to the latest version
git submodule update --remote

# Or pull latest and update
git pull origin main
git submodule update --init --recursive
```

## 🤝 Contributing

Want to contribute improvements to the deployment engine?

### Option 1: Simple Issues
- Open GitHub Issues for bug reports or feature requests
- The maintainers will implement improvements

### Option 2: Code Contributions
1. Fork the adk-deployment-engine repository
2. Make your changes
3. Submit a Pull Request

### Option 3: Local Development
```bash
# In your sub-module directory
cd adk-deployment-engine

# Add your fork as a remote
git remote add my-fork https://github.com/your-username/adk-deployment-engine.git

# Make changes and push to your fork
git push my-fork my-feature

# Create PR on GitHub
```

## 🎯 Best Practices

### Security
- ✅ Never commit `.env.secrets` files
- ✅ Use different service accounts per agent
- ✅ Use Secret Manager for production secrets
- ✅ Follow principle of least privilege

### Development
- ✅ Start with the example agents in `adk-deployment-engine/agents-examples/`
- ✅ Use `make deploy-dry` to test before deploying
- ✅ Keep your `agents/` directory in `.gitignore`
- ✅ Use descriptive service names

### Configuration
- ✅ Keep configuration in `config.yaml`, not code
- ✅ Use environment variables for changeable values
- ✅ Set appropriate resource limits
- ✅ Test with different configurations

## 🔍 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **"No agents found"** | Check your `AGENTS_DIR` setting and ensure `config.yaml` exists |
| **Environment variable errors** | Verify your `.env` file has required variables |
| **Permission errors** | Check service account permissions and IAM roles |
| **Deployment timeouts** | Increase `--timeout` in your `config.yaml` |

### Debug Commands

```bash
# Verbose deployment
make deploy my-agent --verbose

# Test specific agent
make test-build my-agent
make test-dockerfile my-agent

# Check environment
cat .env
```

## 📚 Advanced Usage

### Custom Agents Directory

Want to use a different name for your agents directory?

```makefile
include adk-deployment-engine/makefile
AGENTS_DIR := my-custom-agents
```

### Multiple Environments

Create different makefiles for different environments:

`makefile.staging`:
```makefile
include adk-deployment-engine/makefile
AGENTS_DIR := staging-agents
```

`makefile.production`:
```makefile
include adk-deployment-engine/makefile
AGENTS_DIR := production-agents
```

Use them like:
```bash
make -f makefile.staging deploy my-agent
make -f makefile.production deploy my-agent
```

## 🎯 Where to Go Next

### Just Starting? 🌱
- Review [README.md - Core Concepts](README.md#core-concepts) to understand how it works
- Check [README.md - Configuration Examples](README.md#configuration-examples) for more agent templates
- Read [README.md - Best Practices](README.md#best-practices) for security tips

### Ready for Production? 🚀
- Set up Secret Manager for production secrets
- Configure different environments (staging/production)
- Implement proper IAM roles and service accounts
- Add monitoring and logging

### Need Help? 🤝
- [README.md - Troubleshooting](README.md#troubleshooting) for common issues
- Open GitHub Issues for bugs or feature requests
- Check the example agents in `adk-deployment-engine/agents-examples/`

---

## 🎉 Success!

You now have:
- ✅ Private agent implementations
- ✅ Professional deployment engine
- ✅ Automatic updates and improvements
- ✅ Same simple interface as standalone
- ✅ Full control over your code

Happy deploying! 🚀