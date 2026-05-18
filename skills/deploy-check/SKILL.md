---
name: deploy-check
description: Pre-deployment validation for a Torque blueprint (server-side + design review)
argument-hint: [blueprint-file-path]
---

Validate the blueprint at @$1 before deployment.

**Before running any helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.**

1. **Server-side validation** — run the authoritative schema check via the Torque REST API:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/validate_blueprint.py" \
     --space <SPACE> --name "$(basename $1 .yaml)" --file "$1"
   ```

   This checks spec_version, grain kinds, schema, and Liquid reference resolution. Parse the resulting JSON `{is_valid, errors, warnings}` (shape in `skills/zero-touch-api/references/response_shapes.md`). Report every `errors[]` entry verbatim with `line` / `column` / `path` when present.

   Exit code 1 = `is_valid: false`. If the space name is not known, ask the user before calling — the endpoint is space-scoped.

2. **Design + security review** — invoke the `blueprint-review` skill on the same file for higher-level checks the server validator does not cover: hardcoded secrets, missing outputs, drift-prone grain configs, unused inputs, missing `depends-on` ordering, insecure patterns.

3. **Summary** — present results as two sections: "Server validation" (pass/fail with errors) and "Design review" (annotated suggestions). For each failure, explain what is wrong and how to fix it.

If `TORQUE_API_TOKEN` is unset or the call fails with a network error (`HTTP 0`), fall back to the `blueprint-review` skill alone and note that server-side validation was skipped. For 401/403/404 surface the fix from `skills/zero-touch-api/references/errors.md` and stop.
