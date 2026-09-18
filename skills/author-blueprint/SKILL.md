---
name: author-blueprint
description: >
  Use this skill whenever the user wants to create, write, edit, fix, or review a Torque blueprint YAML file.
  Triggers include: "write a Torque blueprint", "create a blueprint for Torque", "blueprint YAML", 
  "blueprint with Terraform grain", "blueprint with Helm grain", "blueprint with Shell grain",
  "multi-grain blueprint", "nested blueprint", "Torque environment blueprint", "grain spec",
  "blueprint inputs/outputs", "blueprint for Quali Torque", "Torque blueprint for deploying X".
  Also trigger when the user asks to debug or fix a blueprint, add a grain, wire inputs/outputs 
  between grains, or configure agents/dependencies/labels in a Torque context, or pastes a
  Torque validation error such as "Blueprint YAML file contains syntax error(s) in line X col Y".
  Always use this skill — do NOT try to write Torque blueprints from memory alone.
---

# Torque Blueprint Skill

## Overview

Torque blueprints are spec_version: 2 YAML files that define cloud environments composed of **grains** 
(Terraform, Helm, Shell, Kubernetes, etc.). You will write high-quality, production-ready blueprints.

---

## Mode Check — Authoring, Debugging, or Brownfield/Import?

If the user arrived with **an error message from Torque** — a failed validation, a rejected
upload, a red deployment — you are in **debug mode**. Follow *Debug Mode* below before writing
or judging anything. Steps 1–7 are an authoring pipeline; they are not a triage procedure, and
improvising triage from them is how confident wrong answers get produced.

If the blueprint **wraps an already-existing, already-running resource (or set of resources)**
rather than defining something new — check for this before applying Steps 1–7's normal
assumptions. See *Brownfield/Import Mode* below.

Otherwise, continue to Step 1.

---

## Brownfield/Import Mode — This Blueprint Represents a Fixed Set of Live Resources, Not a Template

### Recognize it

Look for any of these signals before reviewing or writing:
- The user says "import," "brownfield," "already exists," "already running," "codify this
  resource," or mentions `import-cloud-resources-as-environment`.
- The blueprint's `description`, name, or a grain's `source.path` mentions "import" or "imported"
  (e.g. `imported-gke-cluster`).
- The Terraform module the blueprint wraps is entirely literal values with no `variables.tf` — the
  shape `import-cloud-resources-as-environment` and `reusable-terraform`'s brownfield exception
  produce by default.

### Apply different rules — do not "fix" it back toward a normal blueprint

A blueprint produced by a brownfield import represents **a specific, fixed set of live
resources** — one resource or many — not a reusable template. This is not a lesser or unfinished
version of a normal blueprint — it is a different, equally valid category with the opposite
defaults, chosen deliberately by whoever ran the import. Full reasoning, the two-model comparison,
and why it's actually safe: see `import-cloud-resources-as-environment`'s
`references/track-a-vs-track-b.md`.

Concretely, when authoring or reviewing a brownfield/import blueprint:
- **Do not** flag hardcoded/literal resource names, IDs, or a lack of `variables.tf`-style
  parameterization as a defect — that's the intended, correct shape for a Track A import (the
  overwhelming default; see the reference above). Only flag it if the user has explicitly said
  they want this blueprint to also work as a launchable template (Track B).
- **Do not** suggest making the blueprint "more reusable" or removing what looks like duplication
  with another blueprint — a second, differently-named import of a similar resource type is not
  duplication, it's two different live resources.
- **Do not** treat "this can't be relaunched as a second environment" as a bug to fix. It's a
  property of Track A imports, not a gap in the blueprint (see the second-launch mechanism in the
  reference above if the user is worried about this).
- **Do** keep the `backend` block out of the wrapped Terraform module and in the blueprint's
  `spec.backend` (or the import API's `grains[].backend`) exactly as Step 4's Terraform grain
  pattern already shows — this matters even more for imports, since the backend key is fixed to
  one already-existing state file.
- **Do** check whether any input actually affects the resource it targets. An input wired to a
  field pinned by `lifecycle.ignore_changes`, or one the provider only reads at creation time, is
  inert against an already-imported resource — say so plainly in that input's `description` rather
  than presenting it as a normal, effective input.
- **Do** name the blueprint for what it is (`Imported GKE Cluster`, not `GKE Cluster`) — a generic
  name invites exactly the second-launch attempt this mode exists to prevent.
- If the user is doing a fresh import end-to-end (not just editing/reviewing existing import YAML),
  point them at the `import-cloud-resources-as-environment` skill instead of authoring the
  blueprint here in isolation — it owns the full pipeline (resource lookup, grouping, Terraform
  generation, the Track A/B goal question) that this blueprint is only the last step of.

---

## Debug Mode — Torque Rejected a Blueprint

### D1 — Run the authoritative validator FIRST

Do not reason about the error from the YAML alone. Torque's server-side validator is the only
source that knows what Torque actually accepts:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/scripts/examples/validate_blueprint.py" \
  --space <SPACE> --name <BP> --file <PATH_TO_YAML>
```

Ask for the space name if you don't have it — it is usually worth one question to get a real
answer instead of a guess. If you genuinely cannot run it (no space, no token, YAML pasted with
no context), **say so in your first sentence**, before any findings, and treat everything that
follows as unverified.

Secondary check — validate against the published schema:
```
web_fetch: https://raw.githubusercontent.com/QualiTorque/torque-vs-code-extensions/master/client/schemas/blueprint-spec2-schema.json
```

### D2 — Never treat `line N col M` as the root cause

Torque reports a **position, not a diagnosis**. A violation elsewhere in the file routinely
surfaces at an unrelated line, and `additionalProperties: false` failures often anchor to a
parent node rather than the offending key.

**Do not construct an explanation that fits the reported line.** That is backwards reasoning:
the conclusion gets fixed first and a plausible mechanism gets invented to justify it. Enumerate
every violation in the file (D3) *first*, then check which ones the reported position is
consistent with — never the reverse.

### D3 — Enumerate ALL violations before explaining any one

Sweep the entire file against the schema and *Known Schema Gotchas* below, and list every
violation you find. Only then write the explanation. One reported error routinely masks several
real ones, and the reported one is often not the one that matters.

### D4 — Label every finding with its evidence class

Findings are not equally trustworthy. Presenting them in one uniform confident voice is exactly
how a user ends up acting on a guess. Tag each finding:

| Tag | Means |
|---|---|
| **[Confirmed]** | The validator rejected it. Quote the error verbatim. |
| **[Schema]** | Provable from the schema text. Cite the definition and the constraint. |
| **[Inferred]** | Your reasoning only. Nothing confirmed it. |

Rules:
- Order findings **[Confirmed] → [Schema] → [Inferred]**. Inferred goes last, always.
- State the uncertainty **before** the fix, never after. Users act on the fix and skip a trailing caveat.
- Never describe an **[Inferred]** finding in schema language ("the schema requires…",
  "it has to be…") unless you have actually read that constraint in the schema.
- If the user replies *"we use this widely and have never had an issue"* — **believe them.**
  Production evidence outranks your inference. Retract the finding; do not defend it.

### D5 — Check the working-patterns list before calling anything broken

See *Valid Patterns That Look Wrong* below. If the construct appears there, it is not the bug —
keep looking.

---

## Known Schema Gotchas

Verified against `blueprint-spec2-schema.json`. These are the highest-frequency causes of
"syntax error" rejections:

| Construct | Rule | Wrong | Right |
|---|---|---|---|
| Blueprint `outputs:` | `BlueprintOutputObject` is `additionalProperties: false`, `required: [value]`. Only `value`, `kind` (`regular`/`link`) and `quick` are allowed — **`description:` is not a valid key.** | `my_out:` / `  description: "..."` | `my_out:` / `  value: '{{ .grains.g.outputs.X }}'` / `  quick: false` |
| Grain `env-vars:` | `EnvironmentVariable` is a plain key/value map (`patternProperties: ^[A-Za-z0-9_]+`). A `name`/`value` pair **passes schema validation** but silently sets two env vars literally named `name` and `value` — the script never sees the real variable. | `- name: API_KEY` / `  value: 'x'` | `- API_KEY: 'x'` |
| Shell grain outputs | A blueprint output referencing `{{ .grains.g.outputs.X }}` requires grain `g` to list `X` in its own `spec.outputs:` **and** the command to `export X`. Otherwise the value is discarded when the shell exits. | blueprint output alone | grain `outputs: [X]` + `export X` |
| Grain names | Must match `[a-zA-Z0-9-_ ]{3,45}`. | — | — |

## Valid Patterns That Look Wrong

Legal constructs in wide production use. **Do not flag these as bugs.**

- **`agent.name` from a space parameter.** `GrainSpecHostObject.name` is an unconstrained
  `string` — the schema places no restriction on which template namespace may appear there.
  `name: '{{ .params.default_agent }}'` is valid and is a *good* pattern: it lets a space set
  the agent once instead of making every user pick one at launch. The `{{ .inputs.agent }}`
  form used throughout this skill is a **convention, not a requirement**.
- **`.params` inside grain specs.** No documented ordering rule makes space parameters
  unavailable to `agent`, `env-vars` or grain `inputs`, and the pattern is confirmed working in
  production. Do not invent a resolution-order argument to explain an unrelated error.
- **Commented-out `inputs:` blocks.** Inert. Never a validation error.

---

## Step 1 — Fetch Live Documentation

**Always fetch fresh documentation before writing any blueprint.** Never rely on memory alone.

### Required fetches (always)
```
web_fetch: https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-yaml-structure
```

### Fetch grain-specific docs based on the grains needed
Only fetch the docs you actually need for this blueprint:

| Grain Kind | URL |
|---|---|
| terraform | https://docs.qtorque.io/blueprint-designer-guide/blueprints/terraform-grain |
| helm | https://docs.qtorque.io/blueprint-designer-guide/blueprints/helm-grain |
| shell | https://docs.qtorque.io/blueprint-designer-guide/blueprints/shell-grain |
| kubernetes | https://docs.qtorque.io/blueprint-designer-guide/blueprints/kubernetes-grain |
| ansible | https://docs.qtorque.io/blueprint-designer-guide/blueprints/ansible-grain |
| cloudformation | https://docs.qtorque.io/blueprint-designer-guide/blueprints/cloudformation-grain |
| opentofu | https://docs.qtorque.io/blueprint-designer-guide/blueprints/opentofu-grain |
| terragrunt | https://docs.qtorque.io/blueprint-designer-guide/blueprints/terragrunt-grain |
| blueprint (nested) | https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprint-grain |
| argocd | https://docs.qtorque.io/blueprint-designer-guide/blueprints/argocd-grain |
| cdk | https://docs.qtorque.io/blueprint-designer-guide/blueprints/cdk-grain |
| cloudshell | https://docs.qtorque.io/blueprint-designer-guide/blueprints/cloudshell-grain |

### Optionally fetch schema for validation
```
web_fetch: https://raw.githubusercontent.com/QualiTorque/torque-vs-code-extensions/master/client/schemas/blueprint-spec2-schema.json
```

---

## Step 2 — Gather Context (if not already provided)

Before writing, make sure you understand:
- **What grains** are needed (Terraform modules? Helm charts? Shell scripts?)
- **What repo/store names** hold the IaC assets (`store:` values)
- **What paths** within repos point to the modules/charts (`path:` values)
- **What inputs** the user wants to expose (types, defaults, allowed-values)
- **What outputs** need surfacing (links, connection strings, URLs)
- **Agent names** (the Kubernetes agents configured in the Torque account)
- **Dependencies** between grains (what must deploy before what)

If key info is missing, ask before writing. A well-specified blueprint beats a generic one.

### Greenfield projects — defer to `repo-conventions`

If the user has **no existing IaC** and you are about to scaffold both the blueprint AND its grain assets (Terraform module, Helm chart, scripts) in the same flow, **invoke the `repo-conventions` skill FIRST**. It owns the canonical repo layout — where blueprints live, where each grain kind's assets live, naming rules. Do NOT improvise file paths like `blueprints/<name>/blueprint.yaml` or `blueprints/<name>/terraform/` — those violate convention.

After repo layout is decided, return here to write the blueprint YAML, and invoke the relevant per-kind skill (`reusable-terraform`, `reusable-ansible`, …) for the grain assets themselves.

---

## Step 3 — Blueprint Structure Reference

### Minimal valid blueprint
```yaml
spec_version: 2
description: Short description of this environment

inputs:
  agent:
    type: agent
  my_input:
    type: string
    default: "default-value"
    description: "What this input does"

outputs:
  my_output:
    value: '{{ .grains.my_grain.outputs.output_name }}'
    kind: link   # or: regular

grains:
  my_grain:
    kind: terraform   # or helm, shell, kubernetes, etc.
    spec:
      source:
        store: my-repo
        path: terraform/my-module
      agent:
        name: '{{ .inputs.agent }}'
      inputs:
        - variable_name: '{{ .inputs.my_input }}'
      outputs:
        - output_name
```

### Key blueprint sections

**spec_version**: Always `2`.

**description**: Always include — shown in the Torque catalog.

**inputs** — Input types:
- `string` — free text, can have `allowed-values`, `default`, `sensitive`, `pattern`
- `agent` — lets user pick an agent from a dropdown
- `parameter` — pulls allowed-values from parameter store (`parameter-name: my-param`)
- `credentials` — lets user pick credentials
- `file` — file upload (`max-size-MB`, `max-files`, `allowed-formats` required)
- `input-source` — dynamic values from configured source

Input styles: `radio`, `duration` (ISO 8601), `multi-select`

**outputs** — `kind` can be `link` (renders as clickable URL) or `regular`/omitted

**grains.spec.source** — Three ways:
```yaml
# By repo name + path
source:
  store: my-repo-name
  path: folder/to/module

# By branch/tag/commit
source:
  store: my-repo-name
  path: folder/to/module
  branch: main        # OR tag: v1.2.3  OR commit: abc123

# Root of repo
source:
  store: my-repo-name
  path: .
```

**depends-on** — Comma-separated grain names:
```yaml
my_app:
  depends-on: rds, redis
  kind: helm
```

**labels** — Environment metadata (static or dynamic):
```yaml
labels:
  - env: production
  - version: '{{ .inputs.version }}'
```

**Templating engine** — Shopify Liquid syntax:
```yaml
# Input reference
'{{ .inputs.input_name }}'

# Grain output reference (requires depends-on)
'{{ .grains.grain_name.outputs.output_name }}'

# Space / account parameter store.
# Valid throughout a grain spec — including agent.name, env-vars, and grain inputs.
'{{ .params.param_name }}'

# Dynamic attributes
'{{ envId | downcase }}'
'{{ blueprintName }}'
'{{ ownerEmail }}'
'{{ spaceName }}'

# Filters
'{{ .inputs.name | strip | downcase }}'
'bucket-{{ envId | downcase }}'
```

**env-vars** — Grain-level environment variables:
```yaml
env-vars:
  - MY_VAR: 'static-value'
  - DYNAMIC_VAR: '{{ .inputs.some_input }}'
  - FROM_GRAIN: '{{ .grains.other.outputs.something }}'
```

**workspace-directories** — Check out extra repos into the workspace:
```yaml
workspace-directories:
  - source:
      store: config-repo
      name: CONFIG_DIR
      branch: main
```

**metadata** — Display name and self-service flag:
```yaml
metadata:
  display-name: "My Blueprint Display Name"
  self-service: true
```

---

## Step 4 — Grain-Specific Patterns

### Terraform grain
```yaml
my_tf_grain:
  kind: terraform
  tf-version: 1.5.5    # Optional. Max supported: 1.5.5
  spec:
    source:
      store: infra-repo
      path: terraform/my-module
    agent:
      name: '{{ .inputs.agent }}'
    authentication:
      - my-aws-credential   # or '{{ .inputs.creds }}'
    backend:                 # Optional remote state
      type: s3
      bucket: my-tf-state-bucket
      region: us-east-1
      key-prefix: envs/
    inputs:
      - variable_name: '{{ .inputs.input_val }}'
    outputs:
      - output_name
    env-vars:
      - AWS_DEFAULT_REGION: us-east-1
    scripts:
      pre-tf-init:
        source:
          store: scripts-repo
          path: scripts/setup.sh
        arguments: '{{ .inputs.agent }}'
    auto-retry: true   # Default true; set false to disable
```

### Helm grain
```yaml
my_helm_grain:
  kind: helm
  spec:
    source:
      store: helm-charts-repo
      path: charts/my-chart
    agent:
      name: '{{ .inputs.agent }}'
    target-namespace: '{{ .inputs.namespace }}'
    command-arguments: '--version 1.2.3 --wait'
    commands:
      - dep up charts/my-chart   # Pre-deploy commands
    inputs:
      - replicaCount: '{{ .inputs.replicas }}'
      - image.tag: '{{ .inputs.image_tag }}'
    values-files:
      - source:
          store: config-repo
          path: helm/overrides/values.yaml
    scripts:
      post-helm-install:
        source:
          store: scripts-repo
          path: scripts/get-outputs.sh
        arguments: '{{ .inputs.agent }}'
        outputs:
          - endpoint_url
          - service_ip
```

### Shell grain
```yaml
my_shell_grain:
  kind: shell
  spec:
    agent:
      name: '{{ .inputs.agent }}'
    env-vars:
      - MY_ENV_VAR: '{{ .inputs.value }}'
    activities:
      deploy:
        commands:
          - echo "Deploying..."
          - ./scripts/deploy.sh $MY_ENV_VAR
      destroy:
        commands:
          - echo "Destroying..."
          - ./scripts/teardown.sh
```

### Kubernetes grain
```yaml
my_k8s_grain:
  kind: kubernetes
  spec:
    source:
      store: k8s-manifests-repo
      path: manifests/my-app
    agent:
      name: '{{ .inputs.agent }}'
    namespace: '{{ .inputs.namespace }}'
```

### Nested Blueprint grain
```yaml
nested_env:
  kind: blueprint
  spec:
    source:
      store: blueprints-repo
      path: blueprints/my-inner-blueprint.yaml
    inputs:
      - agent: '{{ .inputs.agent }}'
      - region: '{{ .inputs.region }}'
    outputs:
      - connection_string
```

---

## Step 5 — Best Practices

### Always do
- ✅ Include `spec_version: 2` as the first line
- ✅ Write a meaningful `description` — it appears in the catalog
- ✅ Supply the agent via an input of `type: agent` **or** a space parameter
  (`'{{ .params.default_agent }}'`) rather than a hardcoded name — **both are valid**; this is a
  convention, not a schema rule
- ✅ Use `depends-on` when grain B needs outputs from grain A
- ✅ Declare all outputs your grains produce that are useful to users
- ✅ Mark URLs and endpoints with `kind: link` in outputs
- ✅ Use `{{ envId | downcase }}` to make resource names unique per environment — **except in
  Brownfield/Import Mode**, where resource names are fixed to what already exists in the cloud
- ✅ Use `sensitive: true` on password/secret inputs
- ✅ Add `description` to every input — it shows in the launch form
- ✅ Add `allowed-values` when the set of valid values is known
- ✅ Use `default` values to reduce friction for users
- ✅ Add `labels` for cost tracking, ownership, and governance
- ✅ Use `env-vars` for IaC variables that shouldn't be blueprint inputs

### Never do
- ❌ Don't hardcode credentials or secrets in the YAML
- ❌ Don't duplicate grain outputs in inputs — pass them via `{{ .grains.X.outputs.Y }}`
- ❌ Don't reference a grain's output without `depends-on` on that grain
- ❌ Don't use spaces in grain names (grain names: `[a-zA-Z0-9-_ ]{3,45}`)
- ❌ Don't expose the auto-generated `agent.name` input in published blueprints (remove it)
- ❌ Don't use `branch:` tracking for production — prefer `tag:` or `commit:` for stability
- ❌ Don't omit `destroy` in shell grains if resources are created (cleanup is required)
- ❌ Don't call a construct invalid just because this skill's examples don't show it — the
  examples are one idiom, not the full set of what Torque accepts. Check *Valid Patterns That
  Look Wrong* and the schema before flagging anything
- ❌ Don't flag a Brownfield/Import Mode blueprint's literal resource names, lack of
  parameterization, or inability to relaunch as defects — see *Brownfield/Import Mode* above

### Multi-grain architecture patterns
```yaml
# Pattern: Infrastructure → Application
grains:
  database:          # Deploys first (no depends-on)
    kind: terraform
    spec:
      outputs: [connection_string, hostname]

  cache:             # Deploys in parallel with database
    kind: terraform
    spec:
      outputs: [redis_url]

  application:       # Deploys after both infra grains
    depends-on: database, cache
    kind: helm
    spec:
      inputs:
        - db.url: '{{ .grains.database.outputs.connection_string }}'
        - cache.url: '{{ .grains.cache.outputs.redis_url }}'
```

### Input organization with customization
```yaml
customization:
  launch-form:
    categories:
      - name: 'Infrastructure'
        inputs:
          - name: agent
          - name: region
      - name: 'Application'
        inputs:
          - name: image_tag
          - name: replicas
      - name: 'Advanced'
        inputs:
          - name: tf_backend_bucket
            visible: '{% if inputs.enable_remote_state == "true" %} true {% else %} false {% endif %}'
```

---

## Step 6 — Validate Before Presenting

Before presenting the final blueprint, check:
- [ ] `spec_version: 2` present
- [ ] All `depends-on` reference real grain names
- [ ] All `{{ .grains.X.outputs.Y }}` references have corresponding `depends-on: X`
- [ ] All outputs declared in grain `outputs:` list are actually produced by the IaC module
- [ ] Grain `kind:` values are valid: terraform, helm, shell, kubernetes, ansible, cloudformation, blueprint, opentofu, terragrunt, argocd, aws-cdk, cloudshell
- [ ] Agent comes from a `type: agent` input or a space parameter — not a hardcoded name
- [ ] No hardcoded credentials
- [ ] Resource names use `{{ envId }}` for uniqueness where needed
- [ ] Blueprint `outputs:` use only `value` / `kind` / `quick` — **no `description:`**
- [ ] `env-vars:` entries are `- KEY: value` maps, not `- name:` / `value:` pairs
- [ ] Every `{{ .grains.X.outputs.Y }}` has `Y` in grain X's `spec.outputs:` list

---

## Step 7 — Output Format

Present the blueprint as a complete, ready-to-use YAML file with:
1. The full YAML code block
2. A brief explanation of the blueprint's structure and any assumptions made
3. A list of things the user needs to fill in (repo names, paths, actual module variable names)
4. Any relevant next steps (publishing to catalog, adding policies, etc.)

If information is missing to write a complete blueprint, produce the best possible version with clearly marked `# TODO: replace with actual value` comments.

---

## Reference Links

- Full blueprint docs: https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-yaml-structure
- Blueprint overview: https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-overview
- Blueprint examples: https://docs.qtorque.io/example-blueprints/application-orchestration
- Auto-generated blueprints: https://docs.qtorque.io/blueprint-designer-guide/autogenerated-blueprints
- Layouts: https://docs.qtorque.io/blueprint-designer-guide/layouts
- Torque API reference: https://portal.qtorque.io/api_reference
- VSCode schema: https://raw.githubusercontent.com/QualiTorque/torque-vs-code-extensions/master/client/schemas/blueprint-spec2-schema.json
