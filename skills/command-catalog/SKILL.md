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

1. Use `get_spaces` if needed to confirm the active space.
2. Use `get_catalog_items` to fetch published blueprints.
3. If "$ARGUMENTS" is provided, filter catalog items by case-insensitive substring match on name or description.
4. Present results as a table: **name**, **description** (truncated to ~80 chars), **inputs required** (count of required inputs without defaults), **tags/labels** if available.
5. After the table, offer two follow-ups:
   - `/launch-env <name>` to launch a blueprint from the catalog.
   - "Show me the YAML for X" — uses `get_blueprint_yaml` for inspection.

If the catalog is empty in this space, suggest:
- Switching spaces (`get_spaces`).
- Publishing a draft blueprint (link to docs).
