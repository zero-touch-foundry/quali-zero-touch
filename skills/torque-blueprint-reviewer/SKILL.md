---
name: torque-blueprint-reviewer
description: >
  Reviews Torque blueprint YAML files for quality, security, and best practices.
  Checks for: missing outputs, incorrect depends-on ordering, hardcoded values
  that should be inputs, insecure patterns, drift-prone grain configs, unused
  inputs, and common authoring mistakes. Returns annotated YAML with inline
  suggestions and a summary report.

  Use this skill when the user asks to review, audit, lint, check, improve, or
  validate a Torque blueprint YAML. Triggers: "review my blueprint", "check this
  YAML", "is this blueprint correct", "what's wrong with this blueprint",
  "improve this blueprint", "best practices for my blueprint", "does this look
  right", "any issues here" in a Torque context. Also when users paste or upload
  a blueprint and ask for feedback. Complements server-side validation
  (`POST /spaces/{space}/validations/blueprints`, wrapped by
  `validate_blueprint.py`) with higher-level design and security checks.
---

# Torque Blueprint Reviewer

You are reviewing a Torque (Quali) blueprint YAML file. Your job is to perform a
structured, opinionated review and return actionable feedback the blueprint author
can act on immediately.

**Before running any Torque API helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.**

---

## Step 1 — Obtain the Blueprint

The user may:
- **Paste it inline** or upload a `.yaml` file — use it directly.
- **Reference a blueprint by name** — ask for space name, blueprint name, and (for external repos) repo + branch, then fetch:
  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/get_blueprint_yaml.py" \
    --space <SPACE> --name <BP>            # qtorque built-in repo
  # or, for external repos:
  python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/get_blueprint_yaml.py" \
    --space <SPACE> --name <BP> --repo <REPO> --branch <BRANCH>
  ```
- **Ask you to review "my blueprint"** without providing it — ask them to share it.

Once you have the YAML, proceed to Step 2.

---

## Step 2 — Fetch Live Documentation

Before reviewing, fetch the latest blueprint structure docs so your review is grounded
in the current spec — not stale training data:

```
web_fetch: https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-yaml-structure
```

If the blueprint contains grain types you want to verify specifics for, also fetch the
relevant grain doc (see URL table in `references/review-checklist.md`).

---

## Step 3 — Run the Review

Read the full checklist at **`references/review-checklist.md`** before starting.
Walk through every applicable section of the checklist against the blueprint.

Classify each finding into one of three severity levels:

| Emoji | Severity | Meaning |
|-------|----------|---------|
| 🔴 | **Error** | Will cause deployment failure, security vulnerability, or data loss |
| 🟡 | **Warning** | Likely to cause drift, maintenance burden, or user confusion |
| 🟢 | **Suggestion** | Best-practice improvement, not urgent |

**Review principles:**
- **Be specific.** Don't say "consider parameterizing this." Say which value, why it
  should be an input, and suggest an input name and type.
- **Respect intent.** Constants like `spec_version: 2` are fine hardcoded. Focus on
  values that vary across environments, teams, or deployments.
- **Think in deployment order.** Trace the depends-on graph mentally. Flag cycles,
  missing edges, and unnecessarily sequential chains that block parallelism.
- **Consider the end-user.** Inputs without descriptions make the launch form confusing.
  Missing `quick: true` on important outputs hides them.
- **Security by default.** Secrets must be `sensitive: true`. Agents should not be
  hardcoded in production blueprints. Credentials should use the `credentials` type.

---

## Step 4 — Optionally Validate with Torque

If the user has provided a space name (or you can infer it), run the server-side validator to catch schema-level errors the structural review might miss:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/validate_blueprint.py" \
  --space <SPACE> --name <BP> --file <PATH_TO_YAML>
```

The script base64-encodes the YAML for you and prints `{is_valid, errors, warnings}` as JSON (exit code 1 if invalid). Include any errors in your report under a separate **Schema Validation** heading.

---

## Step 5 — Produce Output

Return two things:

### A) Summary Report

```markdown
## Blueprint Review: <blueprint-name or filename>

### Overview
<1-2 sentence quality assessment>

### Findings

| # | Severity | Category | Finding | Location |
|---|----------|----------|---------|----------|
| 1 | 🔴 Error | Dependency | Grain `app` uses output from `rds` but missing `depends-on` | `grains.app` |
| 2 | 🟡 Warning | Hardcoded | Agent name `eks-prod` is hardcoded | `grains.rds.spec.agent.name` |
| ...

### Detailed Findings

#### 1. 🔴 Grain `app` uses output from `rds` but missing `depends-on`

**What's wrong:** The `app` grain references `{{ .grains.rds.outputs.connection_string }}`
in its inputs, but does not declare `depends-on: rds`. Torque may deploy `app` before
`rds` finishes, causing the output reference to fail.

**Fix:**
​```yaml
app:
  depends-on: rds    # ← add this
  kind: helm
​```

(continue for each finding...)
```

### B) Annotated YAML

The original YAML with inline `# 🔴 REVIEW: ...` / `# 🟡 REVIEW: ...` / `# 🟢 REVIEW: ...`
comments placed directly next to or above the relevant line.

---

## When the Blueprint is Clean

If the blueprint passes all checks, say so clearly. Highlight what the author did well
(proper dependency wiring, good use of inputs, security-conscious patterns). You can
still offer optional polish suggestions.

---

## Edge Cases

- **spec_version: 1** — Flag as deprecated. Recommend migrating to spec_version 2.
  Still review what you can, noting that v1 uses `applications`/`services` instead of `grains`.
- **Very large blueprints (>15 grains)** — Focus on dependency graph, input/output wiring,
  and highest-severity issues first. Offer to deep-dive specific sections.
- **Partial blueprints / snippets** — Review what's visible. Note which checks couldn't
  run due to missing context.
- **Blueprint grain (nested)** — Verify that inner blueprint inputs/outputs are wired
  correctly and that the nested blueprint exists (use `get_blueprint_yaml.py` if you can).
