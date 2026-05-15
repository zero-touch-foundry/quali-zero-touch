---
name: run-workflow
description: Run a Torque day-2 workflow on an environment
argument-hint: [environment-name-or-id] [workflow-name]
---

Run a Torque workflow on the environment "$1".

1. **Resolve the environment** — if "$1" looks like an ID, use it directly. Otherwise use the Torque MCP `get_environments` tool to find an environment by name in the current space. If multiple matches or none, ask the user to clarify.

2. **List available workflows** — use `get_workflows` to retrieve the workflows attached to this environment (or its blueprint scope). Present them as a numbered list with name + short description.

3. **Choose workflow** — if "$2" was provided, match it against the list. Otherwise ask the user to pick by number or name.

4. **Gather inputs** — inspect the chosen workflow's input definitions. For any required input without a default, ask the user. Show defaults clearly. Mark sensitive inputs (don't echo values).

5. **Confirm** — show a one-line summary before running: environment, workflow, inputs. Wait for explicit user confirmation (e.g. "yes" / "run it"). **Do not run automatically** — workflows can be destructive.

6. **Run** — invoke `run_workflow` with the gathered inputs. Report the workflow execution ID and initial status.

7. **Follow-up** — offer to poll `get_instantiated_workflows` to monitor progress, or run `/env-status` after completion.

If no arguments are provided, list environments first, then workflows after one is chosen.
