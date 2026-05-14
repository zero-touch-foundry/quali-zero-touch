# quali-claude-plugin

Claude Code plugin for [Quali Torque](https://www.quali.com/torque/) — environment-as-a-service for cloud infrastructure. Author blueprints, write governance policies, debug environments, migrate Terragrunt, and integrate Terraform/Ansible — all from Claude.

> **Note**: plugin name (`quali-claude-plugin`) is provisional and may change before marketplace publication.

## Components

### Skills

| Skill | What it does |
|-------|--------------|
| **torque-blueprint** | Create, edit, fix, or review Torque blueprint YAML files — grains, inputs, outputs, dependencies, Liquid templating. |
| **torque-blueprint-reviewer** | Audit blueprints for quality, security, and best practices. Annotated feedback for missing outputs, incorrect `depends-on`, hardcoded secrets, drift-prone configs. |
| **torque-workflow** | Create, edit, fix, or review Torque workflow YAML — day-2 ops, env/space scopes, triggers, contract.json, bindings. |
| **torque-rego** | Write and review Torque OPA/Rego governance policies — environment lifecycle, consumption, Terraform plan control, approval channels. |
| **torque-debug-env** | Diagnose failed or stuck environments using the Torque REST API — fetches live grain state, activity feed, error logs. Requires a Torque environment URL + API token. |
| **torque-ready-terraform** | Write, review, or refactor Terraform/OpenTofu code as reusable, parameterized Torque grains with proper outputs and provider versioning. |
| **torque-ready-ansible** | Write or convert Ansible playbooks to be Torque-compatible — outputs, dynamic inventory, teardown, `export_torque_outputs`. |
| **torque-terragrunt-migrate** | Migrate Terragrunt projects to Torque blueprints — dependency blocks → `depends-on`, remote_state → Torque backend, generate blocks → provider-overrides. |
| **torque-cost-analysis** | Estimate and optimize Torque environment / blueprint cost — per-grain breakdown, right-sizing suggestions, before/after comparisons. |
| **aws-best-practices** | AWS architecture, IAM, cost optimization, security hardening — Well-Architected guidance tailored to Torque workloads. |
| **k8s-operations** | Kubernetes troubleshooting, manifest authoring, cluster management — useful when investigating Torque Helm/K8s grains. |

### Commands

| Command | Description |
|---------|-------------|
| `/env-status [name]` | Check a Torque environment's health and grain states. |
| `/launch-env [blueprint]` | Launch a new environment from a blueprint, interactively gathering inputs. |
| `/new-blueprint [name]` | Scaffold a new Torque blueprint with the `torque-blueprint` skill. |
| `/deploy-check [file]` | Pre-deployment validation — server-side via `validate_blueprint_yaml` MCP tool + design review via `torque-blueprint-reviewer`. |
| `/run-workflow [env] [workflow]` | Run a Torque day-2 workflow on an environment, with input prompting and confirmation. |
| `/catalog [filter]` | List published blueprints (catalog items) available to launch in the current space. |
| `/torque-quickstart` | First-time user walkthrough — auth check, space selection, first launch or first blueprint. |
| `/blueprint-from-asset [path]` | Scaffold a Torque blueprint from an existing IaC asset (Terraform, OpenTofu, Helm, Ansible, K8s, CloudFormation, Terragrunt). Auto-detects type. |

### MCP server

| Server | Purpose |
|--------|---------|
| **TorqueMCP** | Torque API access — blueprints, environments, workflows, validation, launch operations. |

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com/claude-code) installed
- A Torque account with API access ([generate a token](https://docs.qtorque.io/api))
- `node` available (for the `npx`-based MCP server)

### Authentication

The TorqueMCP server reads a bearer token from the `TORQUE_API_TOKEN` environment variable.

**Recommended** — set it in the Claude Code app: **Settings → Environment** → add `TORQUE_API_TOKEN=<your-token>`.

**Alternative** — shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
export TORQUE_API_TOKEN="your-torque-api-token"
```

> ⚠️ Do **not** commit your token to `.mcp.json` or anywhere in this repository. The `${AUTH_TOKEN}` placeholder in `.mcp.json` is resolved from the `TORQUE_API_TOKEN` environment variable at runtime.

### Install the plugin

This plugin is not yet published to the Anthropic marketplace. To install locally:

```bash
# Clone the repo
git clone <repo-url> quali-claude-plugin
cd quali-claude-plugin

# Install as a local Claude Code plugin
claude plugin install ./
```

(Marketplace installation instructions will be added when published.)

## Usage examples

**Author a new blueprint:**
```
/new-blueprint my-web-stack
```
or, naturally:
> "Write a Torque blueprint that deploys an EKS cluster with a Helm chart for our app."

**Validate before deploying:**
```
/deploy-check blueprints/my-stack.yaml
```

**Debug a failing environment:**
> "My environment at https://portal.qtorque.io/.../env/abc123 is stuck. Here's my token: ... — what failed?"

**Write a governance policy:**
> "Write a Rego policy that blocks environments longer than 8 hours unless tagged `long-running: true`."

**Migrate from Terragrunt:**
> "Convert this `terragrunt.hcl` to a Torque blueprint."

**Review a blueprint:**
> "Review blueprints/prod.yaml for security and best practices."

## Repo layout

```
.
├── .claude-plugin/plugin.json   # plugin manifest
├── .mcp.json                    # TorqueMCP server config
├── .github/ISSUE_TEMPLATE/      # bug + feature request templates
├── assets/icon.png              # marketplace icon (placeholder)
├── AGENTS.md                    # orientation for AI coding agents working on this repo
├── commands/                    # slash commands (8)
└── skills/                      # skills (11 total — Torque + AWS + k8s + cost analysis)
```

## Contributing

Skills under `skills/torque-*` mirror the public [torque-ai-skills repo](https://github.com/QualiTorque) and should stay in sync. Don't fork them here; PR upstream.

Generic skills (`aws-best-practices`, `k8s-operations`) are plugin-local — edit directly.

## License

Pending — license file will be added before public release.
