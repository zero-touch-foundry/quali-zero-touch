---
name: zero-touch-api
description: >
  Canonical reference for calling the Torque REST API directly from skills.
  Use this skill whenever another skill needs to fetch from or post to Torque
  (list spaces / blueprints / environments / catalog, validate or launch
  blueprints, run workflows, inspect grain status for debugging) and you need
  to know the exact endpoint, payload shape, response structure, or error
  semantics. Also use when extending the plugin with a new Torque API
  operation — this skill documents the conventions every example script
  must follow.
---

# Torque API helper

This skill is **infrastructure for other skills**. It centralizes:

1. A stdlib-only Python helper (`scripts/torque_api.py`) that handles auth, host resolution, JSON encoding, and typed error mapping.
2. A library of thin per-endpoint example scripts under `scripts/examples/`.
3. References that describe endpoint paths, request/response shapes, and error semantics.

Every Torque-skill in this plugin calls Torque through these scripts. **No raw `curl` or `urllib` calls anywhere else in the plugin.**

## Quick start (when invoking from another skill)

1. **MANDATORY credential gate — run this BEFORE the first Torque API call, every session, regardless of what the user asked for.** Do not run any example/helper script until this passes. Even if the user's first request is "how many spaces do I have", check credentials first; do not call a script and react to a 401.

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/torque_api.py" configure --show
   ```

   - **Credentials present** (masked token shown) → proceed to step 2.
   - **Nothing configured** → **actually call the `Skill` tool with `zero-touch-quickstart`** (Phase 1 setup). This is a real tool call, not a paraphrase: do NOT hand-roll your own token prompt / host form. A hand-rolled form gets the host list and my-token link wrong (this is exactly the bug that shipped a portal-only form). Quickstart is the single source of truth for setup — token persistence via `configure --token-stdin`, host handling, `chmod 600`. After it completes, re-run `configure --show` to confirm, then continue with the user's original request.

   **If — and only if — the `Skill` tool is unavailable** and you must collect credentials inline, mirror quickstart exactly. Ask which host, offering these options **in this order**:
   1. **stackautomation.cisco.com**
   2. **portal.qtorque.io**
   3. **Self-hosted / other** — ask for the hostname.

   My-token link is `https://<chosen-host>/my-token` (e.g. `https://stackautomation.cisco.com/my-token`) — never hardcode portal. Persist with `configure --token-stdin` (add `--host <host>` for anything other than portal.qtorque.io). Never pass the token inline per call.

   This gate exists because users invoke task skills directly (e.g. "list my spaces") without running quickstart first. The gate makes setup happen once and persist — not get re-improvised on every cold start.

   > The host list above is a mirror of `zero-touch-quickstart` Step 1a — keep the two in sync if either changes.

2. **Pick the right script from the "Script manifest" table below.** Do not guess script names from filename patterns — the manifest is authoritative.
3. **Always run the chosen script with `--help` first** to see its exact arg names, defaults, and behavior. Skip this step and you will hallucinate flags that don't exist.
4. Use server-side filter params (`--status`, `--name`, `--sub-type`, etc.) wherever the script offers them. Never fetch all records and filter the JSON yourself — server filters are faster, return less data, and avoid misclassifying ambiguous states.
5. Run it via Bash — no `export` needed; helper reads the config file:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/get_environments.py" --space my-space
   ```

6. The script prints JSON to stdout on success and `ERROR HTTP <code>` + body to stderr on failure (non-zero exit code).
7. Parse the JSON, use `references/response_shapes.md` to know which fields to surface, use `references/errors.md` to map error codes to user-facing fixes.

## Direct helper usage (ad-hoc calls)

For endpoints not yet wrapped in an example script, call the helper CLI directly:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/torque_api.py" \
  GET /spaces/my-space/environments

python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/torque_api.py" \
  POST /spaces/my-space/validations/blueprints \
  --body '{"blueprintName":"foo","blueprintRaw64":"c3BlY192ZXJzaW9uOiAyCg=="}'
```

The helper:
- selects a credential **profile**: `--profile` flag → `TORQUE_PROFILE` env → config `default =` marker → the sole profile → `default`,
- resolves token via `TORQUE_API_TOKEN` env → selected profile's `token`,
- resolves host via `TORQUE_API_HOST` env → selected profile's `host` → `portal.qtorque.io`,
- auto-prepends `/api/` to the path (write `/spaces`, not `/api/spaces`),
- maps 401/403/404/422 to typed exceptions / stderr messages.

### `configure` subcommand

Manage the config file (`~/.config/quali-zero-touch/config` on Unix, `%APPDATA%\quali-zero-touch\config` on Windows, `chmod 600`):

```bash
# Show current state (active profile, token masked)
... torque_api.py configure --show

# Write token via stdin (avoids shell history / transcript leak) — default profile
printf '%s' "$TOKEN" | ... torque_api.py configure --token-stdin

# Set self-hosted host
... torque_api.py configure --host tenant.example.com

# Both at once
printf '%s' "$TOKEN" | ... torque_api.py configure --token-stdin --host tenant.example.com

# Wipe everything
... torque_api.py configure --clear
```

Skills writing the token should always use `--token-stdin` and pipe via `printf '%s' "<TOKEN>"` — never put the raw token in argv.

#### Multiple accounts / targets (profiles)

A **profile** is an alias for one (token, host) pair. Single-account users never touch this — the first credential written lands in `default` and is used automatically. Add more only when the user wants a second account/target (e.g. a Stack Automation account alongside portal):

```bash
# Add a named profile (own token + host)
printf '%s' "$TOKEN" | ... torque_api.py configure --token-stdin --profile stackautomation --host stackautomation.cisco.com

# List profiles (marks default + active)
... torque_api.py configure --list

# Change which profile bare calls use
... torque_api.py configure --set-default stackautomation

# Use a specific profile for one call (helper CLI)
... torque_api.py --profile stackautomation GET /spaces

# ...or for an example script (route via env — scripts have no --profile flag)
TORQUE_PROFILE=stackautomation python .../examples/get_spaces.py --names-only

# Remove one profile (keeps the rest)
... torque_api.py configure --clear stackautomation
```

When the user phrases intent per-account ("how many spaces on my **stackautomation** account"), map the account name to a profile: select it with `--profile stackautomation` (helper CLI) or `TORQUE_PROFILE=stackautomation` (example scripts). If no such profile exists yet, offer to add it via `configure --profile`.

## Script manifest

Authoritative list of every example script + the operation it wraps. **This is the source of truth — do not guess filenames from patterns. Always check this table first, then run `--help` on the chosen script before invoking it.**

| Operation | Script | Key args |
|---|---|---|
| List spaces | `get_spaces.py` | `[--names-only]` |
| List blueprints in space | `get_blueprints.py` | `--space SPACE [--sub-type workflow]` |
| Get blueprint YAML (qtorque built-in) | `get_blueprint_yaml.py` | `--space SPACE --name NAME` |
| Get blueprint YAML (external repo) | `get_blueprint_yaml.py` | `--space SPACE --name NAME --repo REPO --branch BR` |
| Validate blueprint YAML | `validate_blueprint.py` | `--space SPACE --name NAME (--file PATH \| --yaml STR)` |
| List catalog items | `get_catalog.py` | `--space SPACE [--search S] [--only-favorites]` |
| List environments in space | `get_environments.py` | `--space SPACE [--name FILTER] [--status STATUS]` |
| Get environment details | `get_environment.py` | `--space SPACE --id ENV_ID` |
| List instantiated workflows on env | `get_workflow_instantiations.py` | `--space SPACE --id ENV_ID` |
| Launch env (registered blueprint) | `launch_env.py` | `--space S --name N --from-registered REPO/BP --inputs JSON [--duration ISO8601]` |
| Launch env (standalone YAML) | `launch_env.py` | `--space S --name N --from-standalone PATH --inputs JSON [--duration ISO8601]` |
| Run day-2 workflow | `run_workflow.py` | `--space S --workflow W --target-env ID [--target-grain G] [--inputs JSON]` |
| Find grain usage examples | `get_grain_usage_examples.py` | `--space SPACE --grain NAME` |

For server-side filtering, use the script's own filter args (`--name`, `--status`, `--sub-type`, etc.) rather than fetching all + filtering in Python. Server is faster, returns less data, avoids ambiguous-state misclassification.

If the operation isn't in this table, it isn't wrapped yet — use the helper CLI directly (see "Direct helper usage" below) or write a new example script per the extension recipe.

## Files

```
skills/zero-touch-api/
├── SKILL.md                          ← this file
├── scripts/
│   ├── torque_api.py                 ← helper. CLI + importable (request, exceptions)
│   └── examples/                     ← one file per endpoint (see manifest above)
└── references/
    ├── endpoints.md                  ← URL table, body shapes for POSTs
    ├── response_shapes.md            ← truncated example responses, fields to parse
    └── errors.md                     ← status code → exception → user-facing fix
```

## Conventions for example scripts

When the user (or another agent) adds a new endpoint:

1. **Helper, not duplication.** Always go through `from torque_api import request, TorqueError`. Never call `urllib.request` directly.
2. **Argparse for inputs.** Required args use `required=True`. Don't read from `sys.argv` directly.
3. **JSON to stdout, errors to stderr.** Print `json.dumps(parsed, indent=2)` on success. On any `TorqueError`, print `ERROR HTTP <status>: <body>` to stderr and `return 1`.
4. **No external deps.** Stdlib only (`json`, `argparse`, `urllib`, `base64`, `re`, `pathlib`). Plugin must work on a vanilla Python 3.8+ install.
5. **Path style.** Write paths starting with `/spaces/...` — helper adds `/api/`. Never hardcode the host.
6. **One file per logical operation.** If an operation needs multiple calls (e.g. `get_grain_usage_examples` = list catalog + N×fetch YAML + regex), one script that orchestrates them is fine.

## Extension recipe (adding a new Torque API operation)

1. Find the endpoint in the [swagger spec](https://portal.qtorque.io/swagger/latest/swagger.yaml).
2. Add a row to `references/endpoints.md` with method, path, body / query, and the script filename you'll create.
3. Add a top-level response shape to `references/response_shapes.md` (truncated example + which fields callers usually parse).
4. Write `scripts/examples/<verb>_<resource>.py` following the conventions above.
5. From the consuming skill (or a new one), reference the script with its `${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/...` path.

No edits to `torque_api.py` are needed unless a new auth mechanism or transport (e.g. SSE) is required.

## Credentials & environment variables

Default storage is the config file (managed via `configure` subcommand above). Env vars override the file:

| Var | Purpose | Default |
|---|---|---|
| `TORQUE_PROFILE` | Select a credential profile by name (example scripts inherit this). | config `default` marker |
| `TORQUE_API_TOKEN` | Bearer token. Overrides the selected profile's `token`. | — |
| `TORQUE_API_HOST` | Hostname only (no scheme, no path). Overrides the selected profile's `host`. | `portal.qtorque.io` |
| `TORQUE_CONFIG_FILE` | Override config file path (escape hatch). | OS default (see below) |
| `HTTPS_PROXY` / `HTTP_PROXY` | Honored automatically by `urllib`. | — |

Config file path:
- Linux/macOS: `$XDG_CONFIG_HOME/quali-zero-touch/config` (else `~/.config/quali-zero-touch/config`)
- Windows: `%APPDATA%\quali-zero-touch\config`

Format (sectioned INI). A legacy flat file with no section header still works — its bare keys read as the `default` profile.
```
default = stackautomation

[default]
token = eyJhbGciOi...
host  = portal.qtorque.io

[stackautomation]
token = eyJ...
host  = stackautomation.cisco.com
```

## Silencing per-call permission prompts

Claude Code prompts the user to approve each Bash invocation by default. The plugin ships a narrow allowlist at `${CLAUDE_PLUGIN_ROOT}/suggested-settings.json` covering helper + example scripts (token-write via `configure --token-stdin` is intentionally excluded). Two ways to apply it:

- Run `/zero-touch-quickstart` — Step 1c offers to merge the allowlist into the project's `.claude/settings.local.json`.
- Manually copy the `permissions.allow` array from `suggested-settings.json` into `.claude/settings.local.json`.

The plugin also ships `.claude-plugin/settings.json` with the same allowlist — Claude Code may honor it as a plugin-default someday, but this is undocumented; treat the project-level merge as the source of truth.

## What this skill does NOT do

- No pagination handling — each example script issues a single request. Endpoints that paginate (catalog when filtered, environments with `paging_info.skip/take`) need per-script logic if/when needed.
- No retry / backoff — if you need polling (e.g. wait for an env to become `Active`), write the loop in the calling skill or in a dedicated script. The helper is raw HTTP.
- No caching — every call hits the API.
