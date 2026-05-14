---
description: Scaffold a new Torque blueprint interactively
argument-hint: [blueprint-name]
---

Help the user create a new Torque blueprint named "$ARGUMENTS".

Read the torque-blueprint skill (at `${CLAUDE_PLUGIN_ROOT}/skills/torque-blueprint/SKILL.md`) before proceeding.

Walk through these steps interactively:

1. Ask what the environment should contain — which cloud resources, applications, and services.
2. Determine which grain types are needed (Terraform, Helm, Kubernetes, Ansible, Shell, CloudFormation, etc.).
3. Ask about user-configurable inputs (regions, instance sizes, app versions, etc.).
4. Ask about outputs the user needs (URLs, connection strings, credentials).
5. Draft the complete blueprint YAML with:
   - `spec_version: 2`
   - Proper inputs with types, defaults, and descriptions
   - Grains with correct kind, source, agent, inputs, outputs
   - `depends-on` for ordered deployment
   - Outputs with `quick: true` for important values
6. Present the YAML for review and iterate based on feedback.

If the Torque MCP is available, use `get_grain_usage_examples` to find real patterns from existing blueprints in the user's space.
