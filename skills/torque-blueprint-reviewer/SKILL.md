---
name: torque-blueprint-reviewer
description: >
  Reviews Torque blueprint YAML files for quality, security, and best practices.
  Checks for: missing outputs, incorrect depends-on ordering, hardcoded values
  that should be inputs, insecure patterns, drift-prone grain configs, unused
  inputs, and common authoring mistakes. Returns annotated YAML with inline
  suggestions and a summary report.

  Use this skill whenever the user asks to review, audit, lint, check, improve,
  or validate a Torque blueprint YAML. Trigger on phrases like "review my blueprint",
  "check this YAML", "is this blueprint correct", "what's wrong with this blueprint",
  "improve this blueprint", "best practices for my blueprint", "does this look right",
  or "any issues here" in a Torque context. Also trigger when users paste or upload
  a blueprint and ask for feedback. Complements validate_blueprint_yaml MCP tool
  with higher-level design, security, and usability checks.
---

# Torque Blueprint Reviewer

You are reviewing a Torque (Quali) blueprint YAML file. Your job is to perform a
structured, opinionated review and return actionable feedback the blueprint author
can act on immediately.

---

## Step 1 — Obtain the Blueprint

The user may:
- **Paste it inline** or upload a `.yaml` file — use it directly.
- **Reference a blueprint by name** — ask for space name, repository name, and branch,
  then fetch it with `TorqueMCP:get_blueprint_yaml`.
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

If the user has provided a space name (or you can infer it), call
`TorqueMCP:validate_blueprint_yaml` to catch schema-level errors the structural
review might miss. To use it, base64-encode the YAML and pass it along with the
blueprint name and space name. Include any validation errors in your report under a
separate **Schema Validation** heading.

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
  correctly and that the nested blueprint exists (if you can check via MCP).
