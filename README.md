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
- A Torque account with API access — token obtained from the Torque portal (see below)

No Node.js / `npx` required — the MCP server uses Claude Code's built-in HTTP transport.

### Step 1 — Get a Torque API token

1. Sign in to the Torque portal at the URL for your account (SaaS: `https://portal.qtorque.io`; dedicated/on-prem: your tenant URL).
2. Open **My Account → Personal API Tokens** (or **Space Settings → Integrations → API Tokens** for a space-scoped token).
3. Click **Generate Token**, copy the value. **Save it now** — the portal will not show it again.

For details and token scope guidance, see the [Torque API docs](https://docs.qtorque.io/api).

### Step 2 — Set the token before launching Claude Code

The TorqueMCP server reads `TORQUE_API_TOKEN` from your environment at session start. Pick one option:

**Option A (recommended) — shell profile**

Add to `~/.zshrc`, `~/.bash_profile`, or equivalent:

```bash
export TORQUE_API_TOKEN="paste-your-token-here"
```

Restart your terminal, then run `claude`.

**Option B — per-session**

```bash
TORQUE_API_TOKEN="paste-your-token-here" claude
```

**Option C — `.env` loader**

If you use [direnv](https://direnv.net/) or similar, add `export TORQUE_API_TOKEN=...` to `.envrc` for the project. Do **not** commit `.envrc`.

> ⚠️ Never commit the token to `.mcp.json`, `.envrc`, dotfiles, or any file pushed to a repo. The `${TORQUE_API_TOKEN}` placeholder in `.mcp.json` is resolved at runtime from your environment.

### Step 3 (on-prem / dedicated only) — Override the Torque URL

SaaS users skip this. If your Torque is a dedicated or self-hosted instance, also set:

```bash
export TORQUE_MCP_URL="https://torque.acme.internal/mcp"
```

The default is `https://portal.qtorque.io/mcp`.

### Step 4 — Verify

Run `claude`, then in the session:

```
/torque-quickstart
```

The quickstart command verifies authentication, lists your spaces, and surfaces fix-it instructions if anything is wrong.

### Install the plugin (Claude Code CLI)

This plugin is not yet on the Anthropic marketplace. Three local-install options:

**Option 1 — session-scoped (fastest for testing)**

```bash
git clone <repo-url> quali-claude-plugin
cd quali-claude-plugin
claude --plugin-dir .
```

The plugin loads for that session only.

**Option 2 — zip-based**

```bash
cd quali-claude-plugin
./pack.sh
claude --plugin-dir dist/quali-claude-plugin-0.1.0.zip
```

**Option 3 — persistent via a local marketplace**

See the marketplace setup snippets in the [Claude Desktop install section](#install-in-claude-desktop-code--cowork-tabs) — the same marketplace folder works for the CLI:

```bash
/plugin marketplace add ~/quali-local
/plugin install quali-claude-plugin@quali-local
```

(Marketplace installation instructions for the public Anthropic marketplace will be added when published.)

### Install in Claude Desktop (Code / Cowork tabs)

Claude Desktop's **Code** tab (and **Cowork** tab) host the full Claude Code runtime, so plugins, slash commands, skills, and `.mcp.json` MCP servers all work the same as the CLI. The **Chat** tab is conversation-only and does not run plugins.

**Step 1 — build a zip**

From the plugin root:

```bash
./pack.sh
```

Produces `dist/quali-claude-plugin-<version>.zip` with a clean top-level folder layout. Share that zip or use it for the next steps.

**Step 2 — install in Claude Desktop**

Open Claude Desktop → **Code** tab → **+** button next to the prompt → **Plugins**. Two options:

- **Upload zip** — point at the file produced by `pack.sh`. Simplest path.
- **Add local marketplace** — for iterative dev. Create a marketplace folder once:

  macOS / Linux:
  ```bash
  PLUGIN_PATH="/full/path/to/quali-claude-plugin"
  mkdir -p ~/quali-local/.claude-plugin
  cat > ~/quali-local/.claude-plugin/marketplace.json <<EOF
  {
    "name": "quali-local",
    "plugins": [
      { "name": "quali-claude-plugin", "source": "$PLUGIN_PATH" }
    ]
  }
  EOF
  ```

  Windows (PowerShell):
  ```powershell
  $PluginPath = "C:\full\path\to\quali-claude-plugin"
  $MarketDir  = "$HOME\quali-local\.claude-plugin"
  New-Item -ItemType Directory -Force -Path $MarketDir | Out-Null
  @"
  {
    "name": "quali-local",
    "plugins": [
      { "name": "quali-claude-plugin", "source": "$PluginPath" }
    ]
  }
  "@ | Set-Content -Encoding UTF8 "$MarketDir\marketplace.json"
  ```

  Then in Claude Desktop's plugin UI, add the marketplace path (`~/quali-local` or `%USERPROFILE%\quali-local`) and install `quali-claude-plugin` from it.

**Step 3 — set env vars**

Claude Desktop reads env vars from the OS environment at app launch.

- **macOS**: add `export TORQUE_API_TOKEN="..."` (and optional `export TORQUE_MCP_URL="..."`) to `~/.zshenv`. `.zshenv` loads for all zsh processes including those spawned by GUI apps; `.zshrc` loads only for interactive shells and is **not** read when launching Claude Desktop from Finder. Log out and back in, or restart, after editing.
- **Linux**: same idea — use `~/.profile` (loaded at login) rather than `~/.bashrc` (interactive-only). Log out and back in.
- **Windows**: open **Settings → System → About → Advanced system settings → Environment Variables**. Add `TORQUE_API_TOKEN` (and optional `TORQUE_MCP_URL`) under **User variables**. Click OK, then fully quit Claude Desktop (right-click tray icon → **Quit**, not just closing the window) and reopen it.

**Step 4 — verify**

In the Code tab, type `/torque-quickstart`. It checks the env var, surfaces fix-it instructions if missing, then calls `get_spaces` to confirm end-to-end auth.

**Chat tab — MCP only, no plugin**

The Chat tab does not run plugins, but you can still register the Torque MCP server there for the 12 Torque tools (no slash commands, no skills). Edit Claude Desktop's MCP config:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "TorqueMCP": {
      "type": "http",
      "url": "https://portal.qtorque.io/mcp",
      "headers": {
        "Authorization": "Bearer PASTE_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Restart Claude Desktop. Replace the URL for on-prem / dedicated tenants.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Claude Code logs "MCP server `TorqueMCP` failed to start" or "config parse error" | `TORQUE_API_TOKEN` env var is unset | Set it (see [Authentication](#step-2--set-the-token-before-launching-claude-code)) and restart Claude Code. Claude Code fails silently at config-parse time when required env vars are missing without defaults. |
| MCP tools return `401 Unauthorized` | Token invalid, expired, or wrong account | Regenerate at the Torque portal. Confirm you copied it without leading/trailing whitespace. |
| MCP tools return `403 Forbidden` on specific tools | Token is space-scoped but tool is account-wide (or vice versa) | Use a personal API token, or scope your space token to the correct space. |
| MCP tools time out / `connection refused` | Wrong `TORQUE_MCP_URL` for an on-prem/dedicated instance | Confirm the URL with your Torque admin. Must include the `/mcp` suffix. |
| `/launch-env` shows no blueprints | Token scoped to a space without published blueprints | Run `/catalog` against another space, or check **Catalog** in the portal. |
| Tool list is empty / Claude doesn't see Torque tools | Plugin not loaded, or MCP entry didn't load | `claude plugin list` to verify the plugin is installed. Check `~/.claude.json` or session logs for parse errors. |

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
