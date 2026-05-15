---
name: catalog
description: >
  Show Torque catalog items — published blueprints the user can launch in the current space.
  Use this skill when the user asks "what blueprints can I launch", "show me the Torque catalog",
  "what's available in Torque", "list catalog items", "list published blueprints",
  "find a blueprint for X", "what can I deploy from Torque", "browse Torque catalog",
  or invokes /catalog. Optionally accepts a filter argument to substring-match on
  blueprint name or description. Pair with /launch-env to actually deploy.
argument-hint: [filter]
---

Show the Torque catalog — published blueprints the user can launch in the current space.

**Before running any helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/torque-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.** Response shapes are in `skills/torque-api/references/response_shapes.md`.

1. If the active space is not known, run:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_spaces.py" --names-only
   ```
   and ask the user to pick one.
2. Fetch the catalog:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_catalog.py" --space <SPACE>
   ```
3. If `"$ARGUMENTS"` is provided, filter the parsed JSON by case-insensitive substring match on `name` or `description`.
4. Present results as a table: **name**, **description** (truncated to ~80 chars), **inputs required** (count entries in `inputs[]` where `required` is true and no `default`), **labels** if available.
5. After the table, offer two follow-ups:
   - `/launch-env <name>` to launch a blueprint from the catalog.
   - "Show me the YAML for X" — uses `get_blueprint_yaml.py --space <SPACE> --name X` for inspection.

If the catalog is empty in this space, suggest:
- Switching spaces (re-run `get_spaces.py --names-only`).
- Publishing a draft blueprint (link to docs).
