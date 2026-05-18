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

**Before running any helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.**

## Phase 1 — Setup check

### Step 1a — Pre-flight check for credentials

The plugin stores the API token + host in a config file (`~/.config/quali-torque/config` on Unix, `%APPDATA%\quali-torque\config` on Windows), `chmod 600`. The helper script reads it automatically — no `export` needed per session. The `TORQUE_API_TOKEN` / `TORQUE_API_HOST` env vars still work and override the file when set.

Make sure you let the user know what are you checking for and why, so they understand the value of the step and aren't confused by the questions.

Check current state:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/torque_api.py" configure --show
```

Output is either credentials with the token masked, or a hint that nothing is configured.

If no token is configured:

1. Determine the portal host first so the token link points to the right place:
   - Ask: "Are you on Torque SaaS (portal.qtorque.io) or a dedicated / self-hosted tenant?"
   - SaaS default: `portal.qtorque.io`. For self-hosted, ask for the hostname (no scheme, no path).
2. Ask: "Do you already have a Torque API token, or do you need to generate one?"
   - If they need one, send them directly to the **My Token** page on their portal:
     - SaaS: <https://portal.qtorque.io/my-token>
     - Self-hosted: `https://<their host>/my-token`

     That page shows the token and lets them copy it in one click. Wait for them to copy it.
3. Write the credentials to the config file. **Use `--token-stdin` so the token doesn't appear in the bash command (avoids shell history + transcript leakage).** Treat the token as sensitive — never echo it back in subsequent messages.

   ```bash
   # SaaS:
   printf '%s' "<TOKEN>" | python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/torque_api.py" \
     configure --token-stdin

   # Self-hosted (writes both token + host):
   printf '%s' "<TOKEN>" | python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/torque_api.py" \
     configure --token-stdin --host "<HOSTNAME>"
   ```
4. Confirm with `configure --show` that the masked token appears and the host is right.

Other ways to set credentials (advanced):

- Per-session env vars: `export TORQUE_API_TOKEN="..."` and optional `export TORQUE_API_HOST="..."`. Override the config file when set. Useful for CI, debugging, or temporarily switching tenants.
- To change the host later: `... configure --host "<NEW_HOST>"` (preserves existing token).
- To rotate the token: re-run the `--token-stdin` command with the new value.
- To wipe credentials: `... configure --clear`.

### Step 1b — Validate live

Once the token is set, list spaces. This single call validates token + host + network in one step:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/get_spaces.py" --names-only
```

- Success → list the spaces and ask which to work in. Proceed to Phase 2.
- Failure → diagnose with the table below and surface the matching fix. Full error reference at `skills/zero-touch-api/references/errors.md`.

| Error | Likely cause | Fix to surface |
|---|---|---|
| `ERROR HTTP 401` | Token invalid / expired | Regenerate at the portal's `/my-token` page. Re-run `configure --token-stdin` with the new value. |
| `ERROR HTTP 403` | Token scope mismatch | Use a personal API token, or scope the space token correctly. |
| `ERROR HTTP 0` / connection refused / timeout | Wrong host or network/VPN issue | Self-hosted: `... configure --host "<tenant-host>"`. SaaS: check VPN, corporate proxy, firewall. |
| `Torque API token not configured` | Config file missing and `TORQUE_API_TOKEN` env var unset | Re-run Step 1a (`configure --token-stdin`). |
| `python: command not found` | Python 3.8+ not on PATH | Install Python 3 or set up an alias to `python3`. |

After surfacing the fix, **stop**. Don't continue Phase 2 until `get_spaces.py` works.

### Step 1c — Optional: silence per-call permission prompts

By default Claude Code asks the user to approve each Bash invocation. Since this plugin runs many helper scripts (one per Torque API call), the prompts add up. Offer to add the plugin's script patterns to the project's `.claude/settings.local.json` allowlist (per-project, user-specific, already gitignored).

1. Check whether the allowlist already covers our scripts:
   ```bash
   test -f .claude/settings.local.json && grep -q "zero-touch-api/scripts" .claude/settings.local.json && echo "PERMS_OK" || echo "PERMS_MISSING"
   ```

2. If `PERMS_MISSING`, ask: "Want me to whitelist this plugin's helper scripts in `.claude/settings.local.json` so Claude stops asking for permission per call? (Token writes via `configure --token-stdin` will still prompt.)"

3. On yes, merge these entries into the `permissions.allow` array of `.claude/settings.local.json` (create the file if missing, preserve any existing keys):

   ```json
   {
     "permissions": {
       "allow": [
         "Bash(python *torque_api.py:*)",
         "Bash(python3 *torque_api.py:*)",
         "Bash(python *zero-touch-api/scripts/examples/*)",
         "Bash(python3 *zero-touch-api/scripts/examples/*)"
       ]
     }
   }
   ```

   A canonical copy lives at `${CLAUDE_PLUGIN_ROOT}/suggested-settings.json` — use it as the source. Merge, don't replace; preserve existing `allow` entries. Tell the user the change takes effect on the next tool call (no restart needed for `settings.local.json`).

4. On no, move on. They can copy `suggested-settings.json` manually later.

## Phase 2 — Orient

Ask what the user wants to do:

- **A. Launch something that already exists** → Phase 3A
- **B. Author my first blueprint** → Phase 3B
- **C. Debug a failing environment** → Phase 3C
- **D. Just explore** → walk through one item from each.

## Phase 3A — Launch from catalog

1. Fetch the catalog:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/get_catalog.py" --space <SPACE>
   ```
2. Show a short list (name + description + required inputs count).
3. Pick one with the user. Use `/launch-env <name>` for the rest of the flow.
4. After launch, suggest `/env-status` to follow progress.

## Phase 3B — First blueprint

1. Ask the simplest possible goal: "What's one thing you want to deploy?" (e.g., S3 bucket, EKS cluster, Helm chart).
2. Confirm whether IaC already exists for it (Terraform module, Helm chart, etc.). If yes, invoke `/blueprint-from-asset <path>`. If no, invoke `author-blueprint` skill to scaffold from scratch.
3. Run `/deploy-check` on the result.
4. Optionally launch with `/launch-env`.

## Phase 3C — Debug

1. Ask for the environment URL (encodes space + env ID).
2. Hand off to `debug-env` skill — it fetches live state, grain status, activity feed.

## Phase 4 — Next steps

After the first task, surface 2–3 follow-ups:
- `/catalog` to discover more blueprints.
- `torque-workflow` skill for day-2 ops.
- `torque-rego` skill for governance.
- `cost-analysis` for spend visibility.

Keep it short. The goal is **one** successful task, not an exhaustive tour.
