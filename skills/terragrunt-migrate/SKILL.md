---
name: terragrunt-migrate
description: "Migrate Terragrunt projects to Quali Torque blueprints. Use when: converting terragrunt.hcl files to Torque, replacing Terragrunt orchestration with Torque grains, mapping dependency blocks to depends-on, converting remote_state to Torque backend, translating generate blocks to provider-overrides, handling run_cmd and complex locals with shell grains, migrating multi-environment Terragrunt folder structures."
argument-hint: "Describe the Terragrunt config or project structure you want to migrate"
---

# Terragrunt to Torque Migration

## When to Use

- Converting one or more `terragrunt.hcl` files into Torque blueprint YAMLs
- Replacing Terragrunt's orchestration layer (dependencies, remote state, provider generation) with Torque grains
- Migrating a multi-environment Terragrunt folder hierarchy (`live/dev/`, `live/prod/`) to Torque blueprints
- Handling complex Terragrunt patterns: `run_cmd`, dynamic locals, `for_each`, `read_terragrunt_config`
- Planning a phased migration strategy for large Terragrunt monorepos

## Dependency: author-blueprint Skill

This skill handles **migration workflow and decision-making**. For Torque blueprint syntax, grain types, Liquid templating, and YAML structure, the **author-blueprint** skill is required.

**Before starting any migration, resolve the author-blueprint skill using this procedure:**

1. Search for a skill named **`author-blueprint`** in the workspace. The agent's skill discovery will check all standard skill locations automatically.
2. If found locally, read and load it and proceed.
3. If **not** found locally, prompt the user for approval before installing:
   - Ask: *"The **author-blueprint** skill is required but not found in this workspace. May I install it from https://github.com/QualiTorque/Torque-AI-Skills? (yes/no)"*
   - If the user approves:
     - Fetch raw content from: `https://raw.githubusercontent.com/QualiTorque/Torque-AI-Skills/main/torque-blueprint/SKILL.md`
     - Save to: `.github/skills/author-blueprint/SKILL.md`
     - Also fetch referenced files from the same repo path and save them alongside it:
       - `https://raw.githubusercontent.com/QualiTorque/Torque-AI-Skills/main/torque-blueprint/references/grain-types.md` → `.github/skills/author-blueprint/references/grain-types.md`
       - `https://raw.githubusercontent.com/QualiTorque/Torque-AI-Skills/main/torque-blueprint/references/terragrunt-migration.md` → `.github/skills/author-blueprint/references/terragrunt-migration.md`
     - Confirm: *"author-blueprint skill installed. Proceeding with migration..."*
     - Load the installed skill and proceed.
     - If the fetch fails (e.g. no network or repo access), inform the user and stop:
       > *"Could not reach https://github.com/QualiTorque/Torque-AI-Skills. Please install the author-blueprint skill manually and re-run."*
   - If the user declines, stop and inform:
     > *"The author-blueprint skill is required to proceed. Please install it manually under `.github/skills/author-blueprint/SKILL.md` and re-run."*
4. Once loaded, use the author-blueprint skill for all blueprint syntax questions, grain type specs, and Liquid templating rules.

> **Upstream repo:** https://github.com/QualiTorque/Torque-AI-Skills

## Migration Workflow

### Phase 1: Analyze the Terragrunt Project

Before writing any YAML, fully understand the existing setup.

**1.1 Map the folder structure**

Scan the Terragrunt project tree. Identify:
- Root `terragrunt.hcl` (usually contains `remote_state`, `generate` blocks, common locals)
- Environment directories (`live/dev/`, `live/staging/`, `live/prod/`)
- Component directories within each environment (`vpc/`, `rds/`, `app/`, `eks/`)
- Shared includes (`_envcommon/`, `common.hcl`)

**1.2 Build a dependency graph**

For each `terragrunt.hcl` in the project:
1. List `dependency` and `dependencies` blocks → these become `depends-on` in Torque
2. Identify which outputs are consumed from each dependency
3. Draw the DAG — Torque will deploy independent grains in parallel automatically

**1.3 Catalog the Terraform sources**

For each component, note:
- `terraform.source` — the actual TF module (local path, Git URL, registry ref)
- Whether the module needs to be extracted or refactored (e.g., if it relies on Terragrunt-generated files)

**1.4 Inventory complex patterns**

Flag any usage of:
- `run_cmd(...)` — requires a shell grain
- `for_each` on modules — requires multiple grains or shell grain iteration
- `read_terragrunt_config(...)` — extract values into blueprint inputs or parameter store
- `generate` blocks beyond provider/backend — may need shell grain or scripts
- `before_hook` / `after_hook` — map to Torque `scripts`
- `locals` that call functions or reference other configs — simplify into inputs or shell grains

### Phase 2: Design the Blueprint Structure

**2.1 Decide on blueprint granularity**

| Terragrunt Pattern | Torque Approach |
|---|---|
| Single `terragrunt.hcl` component | One grain in a blueprint |
| Folder of related components with dependencies | One blueprint with multiple grains |
| Entire environment (`live/dev/`) | One blueprint per environment, or one blueprint with env input |
| Shared infra used across environments | Separate "infra" blueprint, consumed via nested blueprint grain or deployed independently |

**2.2 Map environment-specific configs**

| Strategy | When to Use |
|---|---|
| Single blueprint + `environment` input with `allowed-values` | Environments differ only in variable values |
| Separate blueprints per environment | Environments have different components or topology |
| EaC (Environment-as-Code) files | Need pinned, always-on environments (e.g., production) |

### Phase 3: Convert Component by Component

For each Terragrunt component, follow this conversion sequence:

#### 3.1 Source → `grains.*.spec.source`

```
# Terragrunt
terraform { source = "git::ssh://git@github.com/org/modules.git//vpc?ref=v1.2.0" }

# Torque — if module is in a Torque-connected repo:
source:
  store: my-repo
  path: modules/vpc
  tag: v1.2.0

# Torque — external git source:
source:
  path: github.com/org/modules.git//vpc
```

#### 3.2 Inputs → `grains.*.spec.inputs`

| Terragrunt Input Type | Torque Input Syntax |
|---|---|
| Simple string/number | `- var_name: 'value'` or `- var_name: 42` |
| Map / object | `- var_name: '{ "k1": "v1", "k2": "v2" }'` (JSON string) |
| List | `- var_name: '["a", "b"]'` (JSON string) |
| Reference to dependency output | `- var_name: '{{ .grains.dep_name.outputs.out_name }}'` |
| Reference to local/variable | Extract as blueprint input → `- var_name: '{{ .inputs.my_var }}'` |
| `read_terragrunt_config` value | Extract to blueprint input or Torque parameter store |

#### 3.3 Dependencies → `depends-on` + output wiring

For each `dependency` block:
1. Add the dependency as a grain (or confirm it already exists in the blueprint)
2. Add `depends-on: <grain-name>` to the dependent grain
3. Declare needed outputs on the upstream grain: `outputs: [output_name]`
4. Wire inputs: `- var: '{{ .grains.<upstream>.outputs.<output_name> }}'`

**Index access or complex output manipulation** — use a shell grain:
```yaml
grains:
  extract:
    kind: shell
    depends-on: vpc
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      activities:
        deploy:
          commands:
            - name: pick
              command: |
                RAW='{{ .grains.vpc.outputs.private_subnets }}'
                export first_subnet=$(echo "$RAW" | jq -r '.[0]')
              outputs:
                - first_subnet
```

#### 3.4 Remote State → `grains.*.spec.backend`

```yaml
backend:
  type: "s3"           # s3 | azurerm | gcs | http | remote | cloud
  bucket: "my-bucket"
  region: "us-east-1"
  key-prefix: "torque/component-name"
```

Torque auto-generates unique keys: `{key-prefix}/{environmentId}_{grainName}.tfstate`

Drop `path_relative_to_include()`, `find_in_parent_folders()` — Torque handles this.

#### 3.5 Generate Blocks → `provider-overrides` or `backend`

| Generate Target | Torque Equivalent |
|---|---|
| `generate "provider"` | `provider-overrides` in grain spec |
| `generate "backend"` | `backend` in grain spec |
| Other generated files | `scripts.pre-tf-init` to write files, or shell grain |

#### 3.6 Hooks → Torque `scripts`

| Terragrunt Hook | Torque Script |
|---|---|
| `before_hook` on `init` | `scripts.pre-tf-init` |
| `after_hook` on `plan` | `scripts.post-tf-plan` |
| `before_hook` on `apply` | (no direct equivalent — use `pre-tf-init` or shell grain) |
| `before_hook` on `destroy` | `scripts.pre-tf-destroy` |

#### 3.7 Complex Logic → Shell Grains

Patterns that **require a shell grain**:
- `run_cmd(...)` — execute arbitrary commands
- `for_each` on Terragrunt configs — loop in shell, export structured output
- Conditional module inclusion — compute flags in shell, use as inputs
- Dynamic locals with API calls or file processing

Shell grain template:
```yaml
grains:
  compute:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      activities:
        deploy:
          commands:
            - name: calc
              command: |
                # Your logic here
                export result="computed-value"
              outputs:
                - result
```

### Phase 4: Validate and Iterate

1. **Syntax check**: Ensure all Liquid expressions are quoted (`'{{ ... }}'`)
2. **Dependency graph**: Verify no circular `depends-on` chains
3. **Output declarations**: Every output referenced in `{{ .grains.X.outputs.Y }}` must be declared in grain X's `outputs` list
4. **Agent inputs**: Every grain needs `agent.name` — use `'{{ .inputs.agent }}'` with a blueprint-level `agent` type input
5. **Complex objects**: Verify maps/lists are valid JSON strings
6. **Test incrementally**: Deploy one grain at a time in a dev environment before wiring the full graph

## Common Pitfalls

| Pitfall | Solution |
|---|---|
| Forgetting to quote Liquid expressions | Always wrap in single quotes: `'{{ ... }}'` |
| Trying to index into list outputs directly | Use a shell grain with `jq` to extract elements |
| Replicating Terragrunt state key strategy | Use `key-prefix` only — Torque manages the rest |
| Leaving `find_in_parent_folders()` patterns | Remove entirely — blueprints are self-contained |
| Massive single blueprint for entire infra | Split into logical blueprints; use nested blueprint grains for composition |
| Not declaring outputs on upstream grains | Every consumed output must be in the grain's `outputs` list |
| Assuming Terragrunt `mock_outputs` are needed | Torque resolves outputs at runtime — no mocks needed |

## Decision Tree: How to Handle Each Terragrunt Pattern

```
Is the pattern a simple input value?
├─ YES → Blueprint input or hardcoded grain input
└─ NO
   Is it a dependency on another component's output?
   ├─ YES → depends-on + {{ .grains.X.outputs.Y }}
   │   └─ Need to index/transform the output?
   │       ├─ YES → Shell grain with jq
   │       └─ NO → Direct reference
   └─ NO
      Is it remote_state / backend config?
      ├─ YES → grains.*.spec.backend
      └─ NO
         Is it a generate block?
         ├─ YES (provider) → provider-overrides
         ├─ YES (backend) → backend block
         ├─ YES (other)   → pre-tf-init script or shell grain
         └─ NO
            Is it run_cmd / dynamic locals / API calls?
            ├─ YES → Shell grain
            └─ NO
               Is it a hook?
               ├─ YES → Torque scripts (pre-tf-init, post-tf-plan, pre-tf-destroy)
               └─ NO
                  Is it read_terragrunt_config or include?
                  ├─ YES → Extract values into blueprint inputs or parameter store
                  └─ NO → Likely not needed in Torque (e.g., find_in_parent_folders)
```

## Example: Full Migration

### Before (Terragrunt)

```
live/
├── terragrunt.hcl          # root: remote_state, generate provider
├── dev/
│   ├── vpc/terragrunt.hcl  # source=modules/vpc, inputs={cidr, env}
│   ├── rds/terragrunt.hcl  # source=modules/rds, dependency on vpc
│   └── app/terragrunt.hcl  # source=modules/app, dependency on vpc + rds
```

### After (Torque Blueprint)

```yaml
spec_version: 2
description: "Dev environment — VPC + RDS + App"

inputs:
  agent:
    type: agent
  environment:
    type: string
    default: dev
  vpc_cidr:
    type: string
    default: "10.0.0.0/16"

outputs:
  app_url:
    value: '{{ .grains.app.outputs.app_url }}'
    quick: true
    kind: link

grains:
  vpc:
    kind: terraform
    spec:
      source:
        store: my-repo
        path: modules/vpc
      agent:
        name: '{{ .inputs.agent }}'
      backend:
        type: s3
        bucket: my-tf-state
        region: us-east-1
        key-prefix: "torque/vpc"
      inputs:
        - cidr: '{{ .inputs.vpc_cidr }}'
        - environment: '{{ .inputs.environment }}'
      outputs:
        - vpc_id
        - private_subnet_ids

  rds:
    kind: terraform
    depends-on: vpc
    spec:
      source:
        store: my-repo
        path: modules/rds
      agent:
        name: '{{ .inputs.agent }}'
      backend:
        type: s3
        bucket: my-tf-state
        region: us-east-1
        key-prefix: "torque/rds"
      inputs:
        - vpc_id: '{{ .grains.vpc.outputs.vpc_id }}'
        - subnet_ids: '{{ .grains.vpc.outputs.private_subnet_ids }}'
        - environment: '{{ .inputs.environment }}'
      outputs:
        - db_endpoint
        - db_name

  app:
    kind: terraform
    depends-on: vpc, rds
    spec:
      source:
        store: my-repo
        path: modules/app
      agent:
        name: '{{ .inputs.agent }}'
      backend:
        type: s3
        bucket: my-tf-state
        region: us-east-1
        key-prefix: "torque/app"
      inputs:
        - vpc_id: '{{ .grains.vpc.outputs.vpc_id }}'
        - db_endpoint: '{{ .grains.rds.outputs.db_endpoint }}'
        - db_name: '{{ .grains.rds.outputs.db_name }}'
        - environment: '{{ .inputs.environment }}'
      outputs:
        - app_url
```
