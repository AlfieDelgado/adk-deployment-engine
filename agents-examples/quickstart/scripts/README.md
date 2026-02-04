# Deployment Hooks for Agents

This directory contains custom scripts that can be configured to run automatically during deployment.

## Configuration-Based Hooks

Hooks are configured in `config.yaml` under the `hooks:` section:

```yaml
hooks:
  # Pre-deployment hooks - run before deployment starts
  pre_deploy:
    - scripts/mcp-sync.sh        # Sync MCP configuration
    - scripts/validate-env.sh    # Validate environment

  # Post-deployment hooks - run after successful deployment
  post_deploy:
    - scripts/health-check.sh    # Run health checks
    - scripts/notify.sh          # Send notifications
```

### Automatic Execution Examples

```bash
# All configured hooks run automatically when you deploy:
make deploy quickstart          # Runs pre_deploy hooks → deploys → runs post_deploy hooks
make deploy quickstart dev      # Runs pre_deploy hooks → deploys to dev → runs post_deploy hooks
```

### Skipping Hooks

To skip automatic hook execution:

```bash
make deploy quickstart SKIP_HOOKS=true
```

## Manual Hook Execution

You can manually run any script using the `run-hook` command:

```bash
make run-hook <agent-name> <hook-path>
```

### Examples

```bash
# Manually run MCP sync script
make run-hook quickstart scripts/mcp-sync.sh

# Run health check script
make run-hook quickstart scripts/health-check.sh

# Run validation script
make run-hook quickstart scripts/validate-env.sh
```

### Listing Available Hooks

To see all hooks configured for an agent:

```bash
make run-hook quickstart
```

This will display all hooks defined in `config.yaml`.

## Available Scripts

### Configured Hooks (in config.yaml)

**Pre-deployment:**
- **`scripts/mcp-sync.sh`** - Sync MCP configuration with upstream
- **`scripts/validate-env.sh`** - Validate environment variables

**Post-deployment:**
- **`scripts/health-check.sh`** - Run health checks after deployment
- **`scripts/notify.sh`** - Send deployment notifications

### Additional Utility Scripts

These scripts are available but not configured to run automatically:

- **`scripts/mcp-install.sh`** - Install MCP servers locally
- **`scripts/mcp-verify.sh`** - Verify MCP server connectivity

Run them manually:
```bash
make run-hook quickstart scripts/mcp-install.sh
make run-hook quickstart scripts/mcp-verify.sh
```

## Creating Custom Hooks

### Step 1: Create the Script

Create a new `.sh` file in this directory:

```bash
#!/bin/bash
# Script Description
# This script does something useful

set -e  # Exit on error

echo "🔧 Running custom script..."
echo "📋 Agent: $1"
echo ""

# Your script logic here

echo "✅ Script completed successfully!"
```

### Step 2: Make it Executable

```bash
chmod +x scripts/your-script.sh
```

### Step 3: Configure in config.yaml

Add the script to the appropriate hook stage in `config.yaml`:

```yaml
hooks:
  pre_deploy:
    - scripts/your-script.sh    # Runs before deployment
  # OR
  post_deploy:
    - scripts/your-script.sh    # Runs after deployment
```

## Common Hook Use Cases

### Pre-deployment Hooks
- **Environment Validation** - Check required environment variables
- **Dependency Checks** - Verify all dependencies are installed
- **MCP Operations** - Sync MCP configuration, verify connectivity
- **Unit Tests** - Run test suite before deployment
- **Configuration Validation** - Validate config files

### Post-deployment Hooks
- **Health Checks** - Verify service is responding correctly
- **Smoke Tests** - Run basic functionality tests
- **Notifications** - Send Slack/email notifications
- **Documentation Updates** - Update deployment logs
- **Monitoring Setup** - Configure monitoring and alerts

### Manual Utility Scripts
- **MCP Management** - Install, configure, verify MCP servers
- **Testing** - Run integration tests, E2E tests
- **Database Operations** - Run migrations, seed data
- **Backup/Restore** - Backup or restore data

## Tips

- Scripts receive the **agent name** as the first argument (`$1`)
- Use `set -e` to exit on errors
- Provide helpful error messages with emojis (❌ for errors, ✅ for success)
- Return appropriate exit codes (0 for success, non-zero for failure)
- Hook execution stops if any script fails (ensures deployments don't proceed with errors)
- Scripts run from the project root directory


```bash
#!/bin/bash
# Script Description
# This script does something useful

set -e  # Exit on error

echo "🔧 Running custom script..."
echo "📋 Agent: $1"
echo ""

# Your script logic here

echo "✅ Script completed successfully!"
```

## Common Use Cases

### Pre-deployment Checks
- Validate environment variables
- Check configuration files
- Run unit tests
- Verify dependencies

### Post-deployment Tasks
- Health checks
- Send notifications
- Update documentation
- Run smoke tests

### MCP Operations
- Install MCP servers
- Sync configurations
- Verify connectivity
- Test MCP tools

### Testing Utilities
- Integration tests
- End-to-end tests
- Performance benchmarks
- Security scans

## Tips

- Scripts receive the agent name as the first argument (`$1`)
- Use `set -e` to exit on errors
- Use emoji prefixes for better readability (🔧, ✅, ❌, etc.)
- Provide helpful error messages
- Log important actions
- Return appropriate exit codes
