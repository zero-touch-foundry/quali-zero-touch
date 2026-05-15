---
name: torque-quickstart
description: >
  First-time Torque user walkthrough — verifies authentication (TORQUE_API_TOKEN
  + optional TORQUE_API_HOST), picks a space, and branches on intent (launch from
  catalog / author first blueprint / debug failing environment).
  Use this skill when the user says "I'm new to Torque", "help me get started with Torque",
  "Torque quickstart", "first time using Torque", "how do I set up Torque", "where do I begin with Torque",
  "guide me through Torque", "Torque onboarding", or invokes /torque-quickstart. Also use when the
  user has just installed the plugin and asks how to verify it works. Pre-checks the env vars and
  offers to append the export line to the right shell profile before calling any Torque API.
---

Guide a new Torque user from zero to a launched environment. Adapt to their experience level by asking before assuming.

## Phase 1 — Setup check

### Step 1a — Pre-flight check for `TORQUE_API_TOKEN`

Before calling any Torque API, verify the env var exists. Run this via Bash:

```bash
test -n "$TORQUE_API_TOKEN" && echo "TOKEN_OK" || echo "TOKEN_MISSING"
```

(On Windows / cmd, use `if defined TORQUE_API_TOKEN echo TOKEN_OK`. In PowerShell: `if ($env:TORQUE_API_TOKEN) { 'TOKEN_OK' } else { 'TOKEN_MISSING' }`.)

If output is `TOKEN_MISSING`:

1. Determine the portal host first so the token link points to the right place:
   - Ask: "Are you on Torque SaaS (portal.qtorque.io) or a dedicated / self-hosted tenant?"
   - If self-hosted, ask for the hostname and have them `export TORQUE_API_HOST="<hostname>"` (hostname only — no scheme, no path).
   - Default for SaaS: `portal.qtorque.io`.
2. Ask: "Do you already have a Torque API token, or do you need to generate one?"
   - If they need one, send them directly to the **My Token** page on their portal:
     - SaaS: <https://portal.qtorque.io/my-token>
     - Self-hosted: `https://<their TORQUE_API_HOST>/my-token`

     That page shows the token and lets them copy it in one click. Wait for them to copy it.
3. Offer to export it for the current session (preferred) — `export TORQUE_API_TOKEN="..."`. The user's memory says: prefer `export` over editing shell profile dotfiles.
4. If the user wants persistence across restarts and asks you to write to a profile, only then propose appending to `~/.zshrc` / `~/.bashrc` / `~/.bash_profile` (detect via `$SHELL`). Confirm with the user first. Treat the token as sensitive — do not echo it. After writing, `chmod 600` the file if it's not already private.
5. On Windows, walk the user through **Settings → System → About → Advanced system settings → Environment Variables → User variables** to add `TORQUE_API_TOKEN`. Then restart Claude Code / Claude Desktop fully.

### Step 1b — Validate live

Once the token is set, list spaces. This single call validates token + host + network in one step:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_spaces.py" --names-only
```

- Success → list the spaces and ask which to work in. Proceed to Phase 2.
- Failure → diagnose with the table below and surface the matching fix. Full error reference at `skills/torque-api/references/errors.md`.

| Error | Likely cause | Fix to surface |
|---|---|---|
| `ERROR HTTP 401` | Token invalid / expired | Regenerate at the Torque portal (My Account → Personal API Tokens). Re-export `TORQUE_API_TOKEN`. |
| `ERROR HTTP 403` | Token scope mismatch | Use a personal API token, or scope the space token correctly. |
| `ERROR HTTP 0` / connection refused / timeout | Wrong `TORQUE_API_HOST` or network/VPN issue | Self-hosted: `export TORQUE_API_HOST="<tenant-host>"`. SaaS: check VPN, corporate proxy, firewall. |
| `TORQUE_API_TOKEN env var is not set` | Env var not exported in the current Claude Code session | Re-export in the same shell, then restart Claude Code so it inherits. |
| `python: command not found` | Python 3.8+ not on PATH | Install Python 3 or set up an alias to `python3`. |

After surfacing the fix, **stop**. Don't continue Phase 2 until `get_spaces.py` works.

## Phase 2 — Orient

Ask what the user wants to do:

- **A. Launch something that already exists** → Phase 3A
- **B. Author my first blueprint** → Phase 3B
- **C. Debug a failing environment** → Phase 3C
- **D. Just explore** → walk through one item from each.

## Phase 3A — Launch from catalog

1. Fetch the catalog:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_catalog.py" --space <SPACE>
   ```
2. Show a short list (name + description + required inputs count).
3. Pick one with the user. Use `/launch-env <name>` for the rest of the flow.
4. After launch, suggest `/env-status` to follow progress.

## Phase 3B — First blueprint

1. Ask the simplest possible goal: "What's one thing you want to deploy?" (e.g., S3 bucket, EKS cluster, Helm chart).
2. Confirm whether IaC already exists for it (Terraform module, Helm chart, etc.). If yes, invoke `/blueprint-from-asset <path>`. If no, invoke `torque-blueprint` skill to scaffold from scratch.
3. Run `/deploy-check` on the result.
4. Optionally launch with `/launch-env`.

## Phase 3C — Debug

1. Ask for the environment URL (encodes space + env ID).
2. Hand off to `torque-debug-env` skill — it fetches live state, grain status, activity feed.

## Phase 4 — Next steps

After the first task, surface 2–3 follow-ups:
- `/catalog` to discover more blueprints.
- `torque-workflow` skill for day-2 ops.
- `torque-rego` skill for governance.
- `torque-cost-analysis` for spend visibility.

Keep it short. The goal is **one** successful task, not an exhaustive tour.
