---
name: new-blueprint
description: Scaffold a new Torque blueprint interactively
argument-hint: [blueprint-name]
---

Help the user create a new Torque blueprint named "$ARGUMENTS".

Read the author-blueprint skill (at `${CLAUDE_PLUGIN_ROOT}/skills/author-blueprint/SKILL.md`) before proceeding. **Before running any helper script, also read `${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.**

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

To ground the draft in real usage patterns from the user's space, scan existing blueprints for references to a given grain:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/get_grain_usage_examples.py" \
  --space <SPACE> --grain <GRAIN_NAME>
```

Returns a JSON list of `{blueprint_name, snippet}` showing how other blueprints reference that grain's outputs. Use it as a hint, not a constraint.
