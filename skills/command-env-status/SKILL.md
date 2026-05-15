---
name: env-status
description: Check a Torque environment's health and status
argument-hint: [environment-name]
---

Check the health and status of the Torque environment "$ARGUMENTS".

**Before running any helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/torque-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.** Response shape in `skills/torque-api/references/response_shapes.md` (see "GET /spaces/{space}/environments/{env_id}").

1. Resolve the env id. If "$ARGUMENTS" looks like a name, find it:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_environments.py" --space <SPACE> --name "$ARGUMENTS"
   ```
   If no name was provided, list all envs in the space and ask the user which to check.
2. Fetch full details:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_environment.py" --space <SPACE> --id <ENV_ID>
   ```
3. From the parsed JSON: report top-level `status`, `blueprint_name`, and iterate `grains[]` — for each grain print `name`, `kind`, `status`, and any `errors[]`.
4. If any grain is in a failed or degraded state (`Failed`, `Error`, `Deployment_Failed`, `Inactive`), surface its `errors[]` text verbatim. For deeper diagnosis, hand off to `torque-debug-env`.
5. If Kubernetes tools are available, check pod status and resource utilization for the environment's namespace.
6. Summarize the overall health in a table: grain name, kind, status, issues.
7. If there are problems, suggest specific next steps to investigate or resolve them (or invoke `torque-debug-env` directly with the env URL).
