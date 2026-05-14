---
description: Show Torque catalog items (blueprints available to launch)
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
