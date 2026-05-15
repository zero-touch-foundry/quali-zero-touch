---
name: run-workflow
description: Run a Torque day-2 workflow on an environment
argument-hint: [environment-name-or-id] [workflow-name]
---

Run a Torque workflow on the environment "$1".

**Before running any helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/torque-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.**

1. **Resolve the environment** — if "$1" looks like an ID, use it directly. Otherwise list environments and find by name:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_environments.py" --space <SPACE> --name "$1"
   ```
   If multiple matches or none, ask the user to clarify.

2. **List available workflows** in the space (workflows are blueprints with `sub_type=workflow`):
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_blueprints.py" --space <SPACE> --sub-type workflow
   ```
   Present them as a numbered list with `name` + `description`.

3. **Choose workflow** — if "$2" was provided, match it against the list. Otherwise ask the user to pick by number or name.

4. **Gather inputs** — fetch the workflow blueprint YAML to read its input definitions:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_blueprint_yaml.py" --space <SPACE> --name <WORKFLOW_NAME>
   ```
   For any required input without a default, ask the user. Show defaults clearly. Mark sensitive inputs (don't echo values).

5. **Confirm** — show a one-line summary before running: environment, workflow, inputs. Wait for explicit user confirmation (e.g. "yes" / "run it"). **Do not run automatically** — workflows can be destructive.

6. **Run**:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/run_workflow.py" \
     --space <SPACE> --workflow <NAME> --target-env <ENV_ID> \
     --inputs '<JSON_OBJECT>'
   ```
   Add `--target-grain <NAME>` if the workflow is scoped to a single grain (env_resource). Script prints the run id on stdout.

7. **Follow-up** — offer to poll status:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_workflow_instantiations.py" --space <SPACE> --id <ENV_ID>
   ```
   Or run `/env-status` after completion.

If no arguments are provided, list environments first, then workflows after one is chosen.
