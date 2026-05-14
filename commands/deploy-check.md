---
description: Pre-deployment validation for a Torque blueprint (server-side + design review)
argument-hint: [blueprint-file-path]
---

Validate the blueprint at @$1 before deployment.

1. **Server-side validation** — call the Torque MCP tool `validate_blueprint_yaml` with the file contents. This is the authoritative check (spec_version, grain kinds, schema, Liquid reference resolution). Report any errors verbatim with line numbers when available.

2. **Design + security review** — invoke the `torque-blueprint-reviewer` skill on the same file for higher-level checks the server validator does not cover: hardcoded secrets, missing outputs, drift-prone grain configs, unused inputs, missing `depends-on` ordering, insecure patterns.

3. **Summary** — present results as two sections: "Server validation" (pass/fail with errors) and "Design review" (annotated suggestions). For each failure, explain what is wrong and how to fix it.

If the Torque MCP is unavailable, fall back to the `torque-blueprint-reviewer` skill alone and note that server-side validation was skipped.
