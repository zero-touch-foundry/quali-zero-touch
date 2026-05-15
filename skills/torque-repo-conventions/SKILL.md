---
name: torque-repo-conventions
description: "Use this skill whenever the user is organizing, scaffolding, or restructuring a Torque (Quali Torque) repository — i.e. deciding where blueprints, Terraform modules, Helm charts, Ansible playbooks, shell scripts, workflows, or Rego policies should live within a repo. Triggers include: 'how do I organize my Torque repo', 'Torque project structure', 'where should blueprints live', 'starting a new Torque project', 'Torque repo best practices', 'Torque folder layout', 'set up a Torque monorepo', 'split blueprints across repos', 'Torque repo conventions', 'directory structure for Torque', 'where do I put my Terraform for Torque'. Also trigger PROACTIVELY whenever another Torque skill is about to scaffold new IaC assets and a blueprint together in a greenfield project — invoke this skill BEFORE writing files to lock in the canonical layout. Always use this skill — do NOT improvise folder layouts from memory alone."
---

# Torque Repo Conventions Skill

## Overview

This skill owns **cross-cutting, repo-wide layout conventions** for Torque projects. It does NOT cover:
- How to write a blueprint YAML → use `torque-blueprint`
- How to structure a Terraform module's internal files → use `torque-ready-terraform`
- How to structure an Ansible playbook's internal files → use `torque-ready-ansible`
- How to write a workflow YAML → use `torque-workflow`
- How to write a Rego policy → use `torque-rego`

This skill answers: **where in the repo does each artifact live, and how should multiple artifacts relate to each other?**

---

## When to Invoke

**Always invoke FIRST in these situations:**
- User starts a new Torque project from scratch ("greenfield")
- User asks "how should I organize…" / "where should X live"
- Another Torque skill is about to create both a blueprint AND its grain assets in the same flow
- User is refactoring or restructuring an existing Torque repo

**Skip this skill when:**
- The repo layout already exists and the user is adding to it — just follow the existing pattern, don't impose this one
- Only editing a single existing file with no new directories

---

## Canonical Repo Layout

```
<torque-repo>/
  blueprints/
    <blueprint-name>.yaml          ← flat, one YAML per blueprint
    <other-blueprint>.yaml
  terraform/
    <module-name>/                 ← one folder per module
      main.tf
      variables.tf
      outputs.tf
      versions.tf
      README.md
    <other-module>/
  opentofu/                        ← only if using OpenTofu grains
    <module-name>/
  helm/
    <chart-name>/                  ← Helm chart folders
      Chart.yaml
      values.yaml
      templates/
  ansible/
    <playbook-name>/               ← one folder per playbook
      playbook.yml
      inventory/
      roles/
  kubernetes/
    <manifest-set>/                ← raw k8s manifests
      deployment.yaml
      service.yaml
  scripts/
    <script-name>.sh               ← shell-grain scripts, flat
  cloudformation/
    <template-name>.yaml           ← flat
  workflows/
    <workflow-name>.yaml           ← Torque day-2 workflow YAML, flat
  policies/
    <policy-name>.rego             ← OPA/Rego governance policies, flat
  README.md
```

### Rules

1. **Blueprints are flat under `blueprints/`** — NOT `blueprints/<name>/blueprint.yaml`. One YAML file per blueprint.
2. **Grain assets are grouped by kind** at the repo root (`terraform/`, `helm/`, `ansible/`, `scripts/`, …) — NOT colocated under a blueprint folder.
3. **One folder per module** for kinds that need multiple files (`terraform/<module>/`, `helm/<chart>/`, `ansible/<playbook>/`).
4. **One file per artifact** for single-file kinds (`scripts/`, `workflows/`, `policies/`, `cloudformation/`).
5. **Module folder name = `path:` value** in the blueprint `source:` block (e.g. `path: terraform/rds` ↔ folder `terraform/rds/`).

---

## Why This Layout

### Reusability
A module under `terraform/rds/` can be referenced by `blueprints/dev-app.yaml`, `blueprints/staging-app.yaml`, AND `blueprints/prod-app.yaml`. Colocating it under `blueprints/dev-app/terraform/` hides this reuse and produces drift when teams copy-paste.

### Discoverability
A new engineer opens the repo: `blueprints/` shows everything launchable, `terraform/` shows every reusable module. No hunting through nested folders.

### Refactoring safety
When you rename a blueprint, you do NOT also move its grain assets — they keep their stable `terraform/<module>/` path so other blueprints referencing them keep working.

### Mirrors Torque docs and example repos
The Torque public examples and docs all use this layout. Following it keeps your repo grep-compatible with documentation snippets.

---

## Blueprint → Asset Mapping

```yaml
# blueprints/django-ecs.yaml
grains:
  app:
    kind: terraform
    spec:
      source:
        store: my-torque-repo        # repo registered in Torque
        path: terraform/django-ecs   # folder under repo root
```

The `store:` value is the **repository name as registered in Torque** (Settings → Integrations → Repositories). The `path:` value is the **module folder path inside that repo**, starting from the repo root.

---

## Multi-Repo vs. Monorepo

Two valid patterns:

### Monorepo (recommended for small/medium teams)
One repo, all artifacts as above. Single `store:` value across all blueprints. Simplest mental model.

### Multi-repo (large teams, separate ownership)
- `<team>-blueprints` repo → only `blueprints/`
- `<team>-modules` repo → only `terraform/`, `helm/`, etc.

Each repo registers separately in Torque, gets a distinct `store:` name. Blueprints reference modules across repos via `store: modules-repo, path: terraform/x`.

**Trade-off:** multi-repo improves access control + ownership boundaries but adds friction (two PRs to ship a new blueprint that needs a new module).

---

## Branching and Versioning

- **Module stability:** when blueprints reference a module by `branch: main`, every blueprint run pulls latest. Fine for dev. For prod, pin to `tag: v1.2.3` or `commit: <sha>`.
- **Blueprint versioning:** Torque versions blueprints by git tag/commit when published. Treat `main` as the unstable head; tag releases for catalog stability.
- **Don't reorganize folders without coordination:** moving `terraform/rds/` → `terraform/databases/rds/` breaks every blueprint referencing the old path. Add a redirect or update blueprints in the same PR.

---

## Naming Conventions

- **kebab-case** for folder + file names: `terraform/rds-postgres/`, `blueprints/django-ecs.yaml`
- **Match grain name to module folder name** when reasonable: blueprint grain `rds_postgres` ↔ folder `terraform/rds-postgres/` (underscores in YAML keys are fine; folder name uses dashes per convention)
- **Avoid embedding env names in folder paths** (`terraform/dev-rds/`): the *blueprint* selects the env, the *module* should be env-agnostic
- **README.md per module folder** documenting inputs/outputs/example usage in Torque

---

## When Other Skills Run, Defer to This One First

If you (or another skill) are about to do any of the following in a greenfield context:

- Create a blueprint YAML in `blueprints/<name>/blueprint.yaml`  → **wrong**, use `blueprints/<name>.yaml`
- Create Terraform under `blueprints/<name>/terraform/`  → **wrong**, use `terraform/<name>/`
- Colocate scripts under a blueprint subfolder  → **wrong**, use `scripts/`

Pause, consult this skill's layout, then proceed.

---

## Output Format

When asked to scaffold a layout:

1. Show the proposed directory tree as a code block
2. Note which files are placeholders vs. fully written
3. Explicitly call out the `store:` + `path:` mapping the user will need to wire in their blueprint
4. Cross-reference the relevant per-kind skill (`torque-ready-terraform`, `torque-ready-ansible`, etc.) for the next step

---

## Reference Links

- Torque example repos: https://github.com/QualiTorque
- Blueprint YAML structure: https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-yaml-structure
- Repository integration: https://docs.qtorque.io/admin-guide/integrations
