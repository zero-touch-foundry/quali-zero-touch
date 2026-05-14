---
description: Launch a Torque environment from a blueprint
argument-hint: [blueprint-name]
---

Launch a new Torque environment from the blueprint "$ARGUMENTS".

1. Use `get_current_torque_space` to determine the active space.
2. If no blueprint name was provided, use the Torque MCP to list available blueprints and ask the user to choose one.
3. Use the Torque MCP to retrieve the blueprint's input definitions so you know what parameters are needed.
4. If the blueprint has required inputs, ask the user to provide values for any that don't have defaults. Present the inputs clearly with their descriptions and current defaults.
5. Confirm the launch details with the user before proceeding:
   - Blueprint name
   - Environment name (ask the user if not specified)
   - Input values being used
6. Use the Torque MCP to launch the environment with the confirmed inputs.
7. Report the environment ID and initial status once launched.
8. Offer to run `/env-status` to monitor the deployment progress.
