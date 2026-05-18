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
| **debug-env** | Diagnose failed or stuck environments using the Torque REST API — fetches live grain state, activity feed, error logs. Requires a Torque environment URL + API token. |
| **torque-ready-terraform** | Write, review, or refactor Terraform/OpenTofu code as reusable, parameterized Torque grains with proper outputs and provider versioning. |
| **reusable-ansible** | Write or convert Ansible playbooks to be Torque-compatible — outputs, dynamic inventory, teardown, `export_torque_outputs`. |
| **terragrunt-migrate** | Migrate Terragrunt projects to Torque blueprints — dependency blocks → `depends-on`, remote_state → Torque backend, generate blocks → provider-overrides. |
| **cost-analysis** | Estimate and optimize Torque environment / blueprint cost — per-grain breakdown, right-sizing suggestions, before/after comparisons. |
| **aws-best-practices** | AWS architecture, IAM, cost optimization, security hardening — Well-Architected guidance tailored to Torque workloads. |
| **k8s-operations** | Kubernetes troubleshooting, manifest authoring, cluster management — useful when investigating Torque Helm/K8s grains. |

### Commands (user-invocable skills)

These ship as skills under `skills/command-*/` and can be invoked directly with `/` (slash) or by natural language matching their description. Per the early-2026 Claude Code change, slash commands and skills are now one unified system — no separate `commands/` directory.

| Slash | Description |
|-------|-------------|
| `/env-status [name]` | Check a Torque environment's health and grain states. |
| `/launch-env [blueprint]` | Launch a new environment from a blueprint, interactively gathering inputs. |
| `/new-blueprint [name]` | Scaffold a new Torque blueprint with the `torque-blueprint` skill. |
| `/deploy-check [file]` | Pre-deployment validation — server-side blueprint validation (`POST /spaces/{space}/validations/blueprints`) + design review via `torque-blueprint-reviewer`. |
| `/run-workflow [env] [workflow]` | Run a Torque day-2 workflow on an environment, with input prompting and confirmation. |
| `/catalog [filter]` | List published blueprints (catalog items) available to launch in the current space. |
| `/torque-quickstart` | First-time user walkthrough — auth check, space selection, first launch or first blueprint. |
| `/blueprint-from-asset [path]` | Scaffold a Torque blueprint from an existing IaC asset (Terraform, OpenTofu, Helm, Ansible, K8s, CloudFormation, Terragrunt). Auto-detects type. |

### Torque API integration

The plugin talks to Torque via its REST API. A shared **`torque-api`** skill at `skills/torque-api/` centralizes the Python helper (`torque_api.py`, stdlib only), per-endpoint example scripts, and endpoint/response/error references. All other skills call those scripts — no skill makes raw HTTP calls.

Currently wrapped endpoints (one example script each):

- list spaces, blueprints, catalog, environments, workflow instantiations
- get blueprint YAML (qtorque built-in or external repo)
- validate blueprint YAML (server-side)
- launch environment (from registered blueprint or standalone YAML)
- run day-2 workflow
- find grain usage examples across blueprints

To extend with a new Torque API operation, see `skills/torque-api/SKILL.md` — the extension recipe is mechanical (add a row to `endpoints.md`, drop an example script, reference it from the consuming skill).

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com/claude-code) installed
- A Torque account with API access — token obtained from the Torque portal (see below)
- Python 3.8+ on `PATH` (helper scripts are stdlib only — no `pip install` needed)

### Step 1 — Get a Torque API token

1. Sign in to the Torque portal at the URL for your account.
2. Open the **My Token** page:
   - SaaS: <https://portal.qtorque.io/my-token>
   - Dedicated / on-prem: `https://<your-tenant-host>/my-token`
3. Copy the token shown on that page. **Save it now** — the portal will not show it again.

For space-scoped tokens or token-scope guidance, see **Space Settings → Integrations → API Tokens** in the portal, or the [Torque API docs](https://docs.qtorque.io/api).

### Step 2 — Configure credentials (one time)

Run `/torque-quickstart` after installing the plugin (next step) and Claude will walk you through it. The skill writes the token + host to a `chmod 600` config file at:

- Linux/macOS: `~/.config/quali-torque/config`
- Windows: `%APPDATA%\quali-torque\config`

Helper scripts read this file on every call — no need to `export` the token each session. The skill uses `--token-stdin` so the raw token never appears in your shell history or Claude transcript.

If you prefer to do it manually:

```bash
# Token (piped so it stays out of shell history):
printf '%s' "PASTE_YOUR_TOKEN_HERE" | \
  python ~/path/to/plugin/skills/torque-api/scripts/torque_api.py configure --token-stdin

# Self-hosted host (SaaS users skip):
python ~/path/to/plugin/skills/torque-api/scripts/torque_api.py configure --host tenant.example.com

# Inspect (token shown masked):
python ~/path/to/plugin/skills/torque-api/scripts/torque_api.py configure --show

# Wipe:
python ~/path/to/plugin/skills/torque-api/scripts/torque_api.py configure --clear
```

**Env-var overrides** (useful for CI, debugging, swapping tenants) — set either and the helper will use it instead of the config file:

```bash
export TORQUE_API_TOKEN="..."
export TORQUE_API_HOST="tenant.example.com"   # hostname only, no scheme, no path
```

> ⚠️ Never commit the config file or token to any repo.

### Step 3 — Verify

Run `claude`, then in the session:

```
/torque-quickstart
```

The quickstart command verifies authentication, lists your spaces, surfaces fix-it instructions if anything is wrong, and offers to whitelist this plugin's helper scripts in `.claude/settings.local.json` so Claude stops prompting for permission on every API call (see [Permissions](#permissions) below).

### Permissions

The plugin runs Python helper scripts via Bash. By default Claude Code asks the user to approve each invocation, which gets noisy. Two paths to silence the prompts:

1. **Via `/torque-quickstart`** (recommended) — Step 1c offers to merge the plugin's safe-by-design allowlist into your project's `.claude/settings.local.json`. Token writes (`configure --token-stdin`) are intentionally **not** allowlisted — credential changes stay human-in-the-loop.

2. **Manually** — copy `suggested-settings.json` (shipped at the plugin root) into your project's `.claude/settings.local.json`:

   ```bash
   cat "$(claude plugin path quali-claude-plugin)/suggested-settings.json"
   # then merge the permissions.allow array into .claude/settings.local.json
   ```

   The patterns are narrow — they match only files under `torque-api/scripts/` so other Python scripts still prompt:

   ```json
   "permissions": {
     "allow": [
       "Bash(python *torque_api.py:*)",
       "Bash(python3 *torque_api.py:*)",
       "Bash(python *torque-api/scripts/examples/*)",
       "Bash(python3 *torque-api/scripts/examples/*)"
     ]
   }
   ```

`.claude/settings.local.json` is per-project and user-specific (already gitignored in this repo). For team-wide defaults, use `.claude/settings.json` instead.

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

See the [Claude Desktop install section](#install-in-claude-desktop) for marketplace mechanics:

```bash
/plugin marketplace add ~/quali-local
/plugin install quali-claude-plugin@quali-local
```

(Marketplace installation instructions for the public Anthropic marketplace will be added when published.)

### Install in Claude Desktop

Claude Desktop's **Code** tab hosts the full Claude Code runtime — plugins, slash commands, and skills all work. The **Chat** tab is conversation-only and does not run plugins.

> **Cowork tab note:** the Cowork tab only loads plugins from a **git-hosted marketplace** (GitHub owner/repo or git URL), not from a local path or zip. Until this plugin is published to a public GitHub repo, Cowork install is not available. The Code tab works today via zip upload (below).

**Step 1 — build a zip**

```bash
./pack.sh
```

Produces `dist/quali-claude-plugin-<version>.zip`.

**Step 2 — upload in the Code tab**

Open Claude Desktop → **Code** tab → **+** button next to the prompt → **Plugins** → **Add plugin** → select the zip. The plugin loads on next session restart.

The repo also ships a `.claude-plugin/marketplace.json`, so once it's hosted on a public git remote you'll also be able to install via `/plugin marketplace add <owner>/<repo>` — both Code and Cowork. Until then, zip upload is the path.

**Step 3 — configure credentials**

In the Code tab, type `/torque-quickstart`. It will:
- check whether credentials are already configured (`configure --show`),
- if not, ask for the host (SaaS vs self-hosted), point you at `<host>/my-token`, and write the token to the config file via `configure --token-stdin`.

The config file path is OS-default (`~/.config/quali-torque/config` on macOS/Linux, `%APPDATA%\quali-torque\config` on Windows), `chmod 600`. The plugin's helper scripts read it on every call — no shell-profile or env-var setup needed.

**Step 4 — verify**

`/torque-quickstart` finishes by listing your spaces via `get_spaces.py` to confirm end-to-end auth.

## Troubleshooting

Full error reference: `skills/torque-api/references/errors.md`.

| Symptom | Likely cause | Fix |
|---|---|---|
| Script error: `Torque API token not configured` | Config file missing and `TORQUE_API_TOKEN` env unset | Run `/torque-quickstart`, or manually: `printf '%s' "<TOKEN>" \| python skills/torque-api/scripts/torque_api.py configure --token-stdin`. |
| `ERROR HTTP 401` | Token invalid, expired, or wrong account | Regenerate at the Torque portal. Confirm no leading/trailing whitespace. |
| `ERROR HTTP 403` | Token scope mismatch (space-scoped vs account-wide) | Use a personal API token, or scope your space token to the correct space. |
| `ERROR HTTP 0` / connection refused / timeout | Wrong host for an on-prem/dedicated tenant, or VPN/proxy issue | `python skills/torque-api/scripts/torque_api.py configure --host "<tenant-host>"` (hostname only). Verify VPN / proxy. |
| `/launch-env` shows no blueprints | Token scoped to a space without published blueprints | Run `/catalog` against another space, or check **Catalog** in the portal. |
| `python: command not found` | Python 3.8+ not on PATH | Install Python 3 or expose `python3` as `python`. |
| Plugin not visible / Claude doesn't see Torque skills | Plugin not loaded | `claude plugin list` to verify install. Check `~/.claude.json` or session logs for parse errors. |

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
├── .github/ISSUE_TEMPLATE/      # bug + feature request templates
├── assets/icon.png              # marketplace icon (placeholder)
├── AGENTS.md                    # orientation for AI coding agents working on this repo
└── skills/                      # unified skills directory
    ├── torque-api/              # shared API helper (Python, stdlib) + endpoint reference
    │   ├── scripts/torque_api.py
    │   ├── scripts/examples/*.py
    │   └── references/*.md
    ├── command-*/               # user-invocable skills (/env-status, /launch-env, ...)
    └── torque-*, aws-*, k8s-*   # knowledge skills (auto-triggered by description)
```

## Contributing

Skills under `skills/torque-*` mirror the public [torque-ai-skills repo](https://github.com/QualiTorque) and should stay in sync. Don't fork them here; PR upstream.

Generic skills (`aws-best-practices`, `k8s-operations`) are plugin-local — edit directly.

## License

Pending — license file will be added before public release.
