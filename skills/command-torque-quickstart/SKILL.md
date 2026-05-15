---
name: torque-quickstart
description: >
  First-time Torque user walkthrough — verifies authentication (TORQUE_API_TOKEN), picks a space,
  and branches on intent (launch from catalog / author first blueprint / debug failing environment).
  Use this skill when the user says "I'm new to Torque", "help me get started with Torque",
  "Torque quickstart", "first time using Torque", "how do I set up Torque", "where do I begin with Torque",
  "guide me through Torque", "Torque onboarding", or invokes /torque-quickstart. Also use when the
  user has just installed the plugin and asks how to verify it works. Pre-checks the env var and
  offers to append the export line to the right shell profile before calling any MCP tool.
---

Guide a new Torque user from zero to a launched environment. Adapt to their experience level by asking before assuming.

## Phase 1 — Setup check

### Step 1a — Pre-flight check for `TORQUE_API_TOKEN`

Before calling any MCP tool, verify the env var exists. Run this via Bash:

```bash
test -n "$TORQUE_API_TOKEN" && echo "TOKEN_OK" || echo "TOKEN_MISSING"
```

(On Windows / cmd, use `if defined TORQUE_API_TOKEN echo TOKEN_OK`. In PowerShell: `if ($env:TORQUE_API_TOKEN) { 'TOKEN_OK' } else { 'TOKEN_MISSING' }`.)

If output is `TOKEN_MISSING`:

1. Ask the user: "Do you already have a Torque API token, or do you need to generate one?"
   - If they need one: link to the README's "Step 1 — Get a Torque API token" section and the [Torque API docs](https://docs.qtorque.io/api). Wait for them to obtain one.
2. Once they have a token, **offer to write the export line to their shell profile**:
   - Detect the user's shell: `echo $SHELL` → `/bin/zsh` → `~/.zshenv` (preferred for GUI app inheritance) or `~/.zshrc`. `/bin/bash` → `~/.bash_profile` (macOS) or `~/.profile` (Linux).
   - Ask for the token value. Treat it as sensitive — do not echo it back in plain text in subsequent messages.
   - Confirm: "I'll append `export TORQUE_API_TOKEN=\"<redacted>\"` to `<profile-path>`. Continue?"
   - On confirmation, append the line. Verify the file is not world-readable (`chmod 600` if needed).
   - Remind the user they must restart Claude Code / Claude Desktop for the change to take effect.
3. On Windows, walk the user through **Settings → System → About → Advanced system settings → Environment Variables → User variables** to add `TORQUE_API_TOKEN`. Then restart Claude Desktop fully (quit, not just close).
4. Optionally, ask if they need to set `TORQUE_MCP_URL` (only for on-prem / dedicated Torque tenants).
5. **Stop here** until restart is confirmed.

### Step 1b — Validate live

Once the token is set, call `get_spaces` via the Torque MCP. This single call validates token + URL + network in one step.

- Success → list the spaces and ask which to work in. Proceed to Phase 2.
- Failure → diagnose with the table below and surface the matching fix:

| Error | Likely cause | Fix to surface |
|---|---|---|
| MCP tool not available / Claude can't see Torque tools | Plugin not loaded, or env var still missing because the session wasn't restarted after setting it | Confirm `/help` shows Torque commands. If yes but tools are absent, restart Claude Code / Desktop. |
| 401 Unauthorized | Token invalid / expired | Regenerate at the Torque portal (My Account → Personal API Tokens). Re-run `/torque-quickstart` to update the profile. |
| 403 Forbidden | Token scope mismatch | Use a personal API token, or scope the space token correctly. |
| Connection refused / timeout | Wrong `TORQUE_MCP_URL` or network/VPN issue | For non-SaaS Torque: `export TORQUE_MCP_URL="https://<tenant>/mcp"`. For SaaS: check VPN, corporate proxy, firewall. |

After surfacing the fix, **stop**. Don't continue Phase 2 until `get_spaces` works.

## Phase 2 — Orient

Ask what the user wants to do:

- **A. Launch something that already exists** → Phase 3A
- **B. Author my first blueprint** → Phase 3B
- **C. Debug a failing environment** → Phase 3C
- **D. Just explore** → walk through one item from each.

## Phase 3A — Launch from catalog

1. Run `get_catalog_items` for the chosen space.
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
