# torque-cowork

A comprehensive DevOps toolkit for Quali, bringing Torque blueprint authoring, environment management, AWS best practices, Kubernetes operations, and Ansible automation into Claude.

## Components

### Skills

| Skill | Triggers on |
|-------|------------|
| **torque-blueprints** | Creating, editing, or troubleshooting Torque blueprint YAML — grain types, inputs, outputs, Liquid templating |
| **torque-environments** | Managing, monitoring, and troubleshooting Torque environments via MCP |
| **aws-best-practices** | AWS architecture, IAM, cost optimization, security hardening |
| **k8s-operations** | Kubernetes troubleshooting, manifest authoring, cluster management |
| **ansible-automation** | Ansible playbook writing, roles, collections, and Torque integration |
| **terraform-automation** | Terraform modules, state management, HCL debugging, and Torque integration |

### Commands

| Command | Description |
|---------|------------|
| `/env-status [name]` | Check a Torque environment's health and grain states |
| `/launch-env [blueprint]` | Launch a new environment from a blueprint |
| `/new-blueprint [name]` | Scaffold a new Torque blueprint interactively |
| `/deploy-check [file]` | Run pre-deployment validation on a blueprint file |

### MCP Servers

| Server | Purpose |
|--------|---------|
| **TorqueMCP** | Torque Management Control Plane — environment queries, workflows, blueprint tools |

## Setup

### Torque MCP Authentication

The Torque MCP server connects to `https://portal.qtorque.io/mcp` using a bearer token.

Set the `TORQUE_API_TOKEN` environment variable with your Torque API token. In the Claude desktop app, go to **Settings → Claude Code → Environment** to add it there — that way it's available to all MCP servers without needing to set it in your shell profile.

Alternatively, add it to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
export TORQUE_API_TOKEN="your-torque-api-token"
```

> **Tip**: You can also hardcode the token directly in `.mcp.json` if this plugin is for personal use, but using an environment variable is recommended when sharing the plugin across the team.

## Usage

**Launch an environment:**
```
/launch-env my-blueprint
```

**Check an environment:**
```
/env-status my-production-env
```

**Create a new blueprint:**
```
/new-blueprint my-new-service
```

**Validate before deploying:**
```
/deploy-check path/to/blueprints/my-blueprint.yaml
```

**Ask about blueprints naturally:**
> "Help me add a Terraform grain for an S3 bucket to my blueprint"

**Troubleshoot environments:**
> "My staging environment is showing errors, can you check what's wrong?"

**Get AWS guidance:**
> "What's the best IAM policy for our Torque agents?"
