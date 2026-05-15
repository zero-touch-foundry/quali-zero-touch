---
name: launch-env
description: Launch a Torque environment from a blueprint
argument-hint: [blueprint-name]
---

Launch a new Torque environment from the blueprint "$ARGUMENTS".

**Before running any helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/torque-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.** Response shapes in `skills/torque-api/references/response_shapes.md`.

1. Determine the active space. If unknown:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_spaces.py" --names-only
   ```
   Ask the user to pick.
2. If no blueprint name was provided, list catalog items:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_catalog.py" --space <SPACE>
   ```
   Ask the user to choose one.
3. Fetch the blueprint YAML to read its input definitions:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_blueprint_yaml.py" --space <SPACE> --name <BLUEPRINT>
   ```
   Parse the `inputs:` block to find required inputs and defaults.
4. For any required input without a default, ask the user. Present each input with its description and default.
5. Confirm the launch details with the user before proceeding:
   - Blueprint name
   - Environment name (ask if not specified)
   - Input values being used
   - Duration (default ask: `PT2H`)
6. Launch:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/launch_env.py" \
     --space <SPACE> --name <ENV_NAME> \
     --from-registered <REPO>/<BLUEPRINT> \
     --inputs '<JSON>' --duration <ISO8601>
   ```
   Script prints the new environment id on stdout.
7. Report the environment id and initial status. Initial status is usually `Launching`; full state requires a follow-up call.
8. Offer to run `/env-status` (which uses `get_environment.py`) to monitor deployment progress.
