---
name: torque-workflow
description: >
  Use this skill whenever the user wants to create, write, edit, fix, or review a Torque workflow YAML file.
  Triggers include: "write a Torque workflow", "create a workflow for Torque", "create a workflow in Torque", "workflow YAML",
  "Torque automation workflow", "workflow with shell grain", "workflow with Ansible grain",
  "day-2 workflow", "space workflow", "env workflow", "env_resource workflow",
  "workflow triggers", "workflow scope", "workflow bindings", "contract.json",
  "attach workflow to environment", "scheduled workflow", "event-driven workflow",
  "workflow for Quali Torque", "Torque workflow for doing X".
  Also trigger when the user asks to debug or fix a workflow, add grains to a workflow,
  configure triggers, wire bindings, or understand the contract.json pattern.
  Always use this skill — do NOT try to write Torque workflows from memory alone.
---

# Torque Workflow Skill

## Overview

Torque workflows are `spec_version: 2` YAML files that share the **exact same structure as Torque blueprints**
(grains, inputs, outputs, labels, templating, agents, etc.) with one critical addition: a root-level `workflow:`
block that controls scope, lifecycle attachment, triggers, and timeout.

Workflows are **fire-and-finish** automation — they run and terminate. They do **not** have a managed lifecycle
like environments. This has major implications for which grain types are appropriate (see Step 6).

Workflow files live in either: 
1. `blueprints/` directory of the connected repository, alongside blueprint YAML files.
2. Any nested folder under blueprints/
3. Any folder with a .workflows marker file.

### Greenfield projects — defer to `repo-conventions`

If you are scaffolding a workflow as part of a brand-new Torque repo, **invoke the `repo-conventions` skill FIRST** to decide where workflows live across the project (typically a dedicated `workflows/` folder with a `.workflows` marker file, kept separate from `blueprints/` for clarity). This skill owns the workflow YAML's internal structure — `repo-conventions` owns the repo-wide layout.

---

## Step 1 — Fetch Live Documentation

**Always fetch fresh documentation before writing any workflow.** Never rely on memory alone.

### Required fetches (always)
```
web_fetch: https://docs.qtorque.io/workflows/workflows-overview
web_fetch: https://docs.qtorque.io/workflows/workflows-use-cases
```

### Fetch grain-specific docs based on the grains needed
Workflows use the same grain kinds as blueprints. Fetch only the docs needed:

| Grain Kind | URL |
|---|---|
| shell | https://docs.qtorque.io/blueprint-designer-guide/blueprints/shell-grain |
| ansible | https://docs.qtorque.io/blueprint-designer-guide/blueprints/ansible-grain |
| terraform | https://docs.qtorque.io/blueprint-designer-guide/blueprints/terraform-grain |
| helm | https://docs.qtorque.io/blueprint-designer-guide/blueprints/helm-grain |
| kubernetes | https://docs.qtorque.io/blueprint-designer-guide/blueprints/kubernetes-grain |
| opentofu | https://docs.qtorque.io/blueprint-designer-guide/blueprints/opentofu-grain |
| blueprint | https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprint-grain |

> For all other YAML rules (grain spec, inputs/outputs, templating, labels, agents, etc.)
> refer to the `torque-blueprint` skill, which is authoritative for the shared spec.

---

## Step 2 — Gather Context (if not already provided)

Before writing, understand:
- **Scope** — Is this a `space`, `env`, or `env_resource` workflow? (see Step 3)
- **What grains** are needed (shell? Ansible? Terraform?)
- **Trigger type** — manual, cron-scheduled, or event-driven?
- **labels-selector** — For `env`/`env_resource` scopes, which environment labels should this attach to? (e.g ec2-start workflow might target environments with `labels-selector: "AWS-EC2"`)
- **resource-types** — For `env_resource` scope, which resource types (e.g. `aws_instance`)?
- **Which bindings** the workflow needs from the environment or resource (inputs, outputs, resource attributes) (e.g. a vsphere vm workflow might require `{{ .bindings.attributes.moid }}` to interact with the correct VM)
- **Timeout** — Maximum allowed runtime in minutes (min: 5)
- **Agent names** — Which Torque agents will run the grains
- **Does the workflow create cloud resources?** — If so, does the workflow also clean them up? or do they have an automatic retention policy? (e.g. a workflow that creates an EC2 instance but does not destroy it will leave that instance running indefinitely, which may be intentional or may be a costly mistake)

If key info is missing, ask before writing. Scope and trigger decisions shape the entire YAML.

---

## Step 3 — The `workflow:` Block

The `workflow:` block is the only thing that distinguishes a workflow YAML from a blueprint YAML.
It appears at the root level, alongside `spec_version`, `inputs`, `outputs`, and `grains`.

### Full `workflow:` schema
```yaml
workflow:
  scope: space | env | env_resource         # Required. Determines attachment and context.

  # Only for scope: env and env_resource
  labels-selector: "some_key:some_value"    # Optional. Without it, the workflow appears on ALL
                                            # environments (or all resources of the type) in the space.
                                            #
                                            # Condition syntax:
                                            #   some_key         → matches labels with key "some_key"
                                            #                       (key-only OR key:<any_value>)
                                            #   some_key:val     → matches exactly "some_key:val"
                                            #
                                            # AND logic: "key1:val1 and key2:val2"
                                            # OR logic:  "key1:val1, key1:val2"
                                            #
                                            # ⚠️ YAML syntax trap: a colon in the value requires quoting
                                            # labels-selector: "key:value"   ✅
                                            # labels-selector: key:value     ✅ (safe only without spaces)
                                            # labels-selector: key: value    ❌ (YAML parses as mapping)

  # Only for scope: env_resource
  resource-types: aws_instance, azurerm_vm  # Required for env_resource scope. CSV of resource types. resource types must match introspection data retrieved from the grain, e.g. `aws_instance` not `AWS-EC2` or `vm`. These will usually match terraform documentation resource types as seen in the above example. 

  # Only for scope: env and env_resource
  triggers:                                  # Optional list of trigger definitions
    - type: cron
      cron: "0 9 * * 1"                     # Standard cron expression (UTC)
      overridable: true             # Allow user to adjust schedule at launch
    - type: manual
      allowed-groups:                        # Optional: restrict to specific user groups
        - DevOps
        - Admins
    - type: event
      event: Drift Detected              # See trigger events reference below

  timeout: 30                               # Max runtime in minutes (min: 5). Supports Liquid.
```

### Trigger event conditions
| Condition | Description |
|---|---|
| `Drift Detected` | Environment drift was detected |
| `Updates Detected` | IaC Grain updates are available |
| `Approval Request Approved` | A pending approval was approved |
| `Approval Request Denied` | A pending approval was denied |
| `Approval Request Cancelled` | A pending approval was cancelled |
| `Environment Ended` | Environment was successfully ended |
| `Environment Launched` | Environment was launched |
| `Environment Active With Error` | Environment became active but with errors (Environment launch failed) |
| `Environment Ending Failed` | Environment teardown failed |
| `Environment Force Ended` | Environment was force-ended |
| `Environment Extended` | Environment duration was extended |
| `Collaborator Added` | A collaborator was added to the environment |
| `Environment Idle` | Environment entered idle state |

### Built-in workflows
When creating an env workflow that runs a built-in workflow sourced from the `QualiTorque/torque-actions` repository, add:
```yaml
grains:
  grain_name:
    spec:
      built-in: true
      source:
        path: https://github.com/QualiTorque/torque-actions.git//resource/<action>.yaml # <action> is the name of the built-in workflow you want to run, e.g. `aws-ec2-start`
```

A built-in workflow consists of exactly one grain with `built-in: true`. Torque will run that action against all matching target resources in the environment when triggered. Do not add additional grains alongside a `built-in: true` grain.

### Launch form customization

Workflows support the same `customization: launch-form: categories:` input grouping as blueprints (see `torque-blueprint` skill for the full categories syntax).

In addition, workflows support hiding the title step of the launch form:

```yaml
customization:
  launch-form:
    steps:
      title:
        visible: false
```

Hiding the title step disables the user's ability to give a custom name to the workflow execution. Use this when execution naming is irrelevant or would create confusion.

The following launch-form steps are **not supported in workflows** (blueprint-only features):
- `tags`
- `workflows`
- `ownersAndCollaborators`

---

## Step 4 — Scopes in Detail

### `scope: space`
- Workflow is available at the **space level** — not attached to any environment
- No `labels-selector`, no `triggers`, no bindings
- Self-contained automation (e.g. provisioning a new environment, running space-wide cleanup, running an action against an existing non-managed resource)
- Only `manual` trigger makes sense here; event and cron triggers require env context

```yaml
spec_version: 2
description: Space-level workflow example

workflow:
  scope: space
  timeout: 15

inputs:
  agent:
    type: agent

grains:
  my_task:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      activities:
        deploy:
          commands:
            - echo "Running space automation"
```

### `scope: env`
- Available on **environments** whose labels match `labels-selector`
- Receives full environment context via bindings and `contract.json`
- Can reference environment-level inputs, outputs, and resource attributes across all grains
- Supports all trigger types (cron, manual, event)
- Designed to orchestrate automation actions at the environment level, often across multiple resources (e.g. "restart all VMs in this environment", "run a cost audit on this environment", "provision a new resource into this environment")

```yaml
spec_version: 2
description: Environment-scoped workflow example

workflow:
  scope: env
  labels-selector: "team:backend"
  triggers:
    - type: manual
  timeout: 20

inputs:
  agent:
    type: agent

grains:
  check_status:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      env-vars:
        - ENV_ID: '{{ envId }}'
        - CONTRACT: '{{ .bindings.inputs.some_env_input }}'
      activities:
        deploy:
          commands:
            - echo "Running on env $ENV_ID"
```

### `scope: env_resource`
- Available on **individual resources** within environments whose environment labels match `labels-selector`
- Scoped to a specific resource type(s) via `resource-types` (**required** for `env_resource` scope)
- Receives resource-specific context: `resource_id`, `grain_path`, and resource attributes via bindings
- The grain automation runner containers receive a `contract.json` at `$CONTRACT_FILE_PATH`
- Designed for custom automation for a resource type (e.g. backup an RDS DB instance)

```yaml
spec_version: 2
description: Resource-scoped workflow example

workflow:
  scope: env_resource
  labels-selector: aws_instance    # optional; omit to appear on this resource type across all envs
  resource-types: aws_instance     # required
  triggers:
    - type: manual
  timeout: 10

inputs:
  agent:
    type: agent

grains:
  get_info:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      activities:
        deploy:
          commands:
            - name: fetch
              command: 'echo "Resource: {{ .bindings.resource_id }} in {{ .bindings.grain_path }}"'
              outputs:
                - resource_info
```

---

## Step 5 — Bindings and contract.json

Workflows with `scope: env` or `scope: env_resource` receive live environment context through two mechanisms:

### Binding expressions (use in YAML)
```yaml
# Environment inputs (env and env_resource scopes)
'{{ .bindings.inputs.input_name }}'

# Environment outputs (env and env_resource scopes)
'{{ .bindings.outputs.output_name }}'

# Environment identity (env and env_resource scopes)
'{{ .bindings.environment_id }}'    # ID of the environment this workflow is executing against.
                                    # Use when grain scripts need to call the Torque API or
                                    # Torque Ansible Galaxy collection targeting the parent environment.

# Resource attributes by type (env scope — across all resources of a type, will return the first match)
'{{ .bindings.resource_type.aws_instance.attributes.public_ip }}'

# Resource attributes (env_resource scope — the specific resource the workflow runs on)
'{{ .bindings.attributes.power_state }}'
'{{ .bindings.resource_id }}'    # Unique identifier of the target resource
'{{ .bindings.grain_path }}'     # Path to the grain that owns the resource
```

### contract.json (use in grain scripts)
When a workflow executes, the runner container receives a `contract.json` file at the path stored in
the `CONTRACT_FILE_PATH` environment variable. Parse it in scripts with:

**Shell / bash:**
```bash
contract_path=$CONTRACT_FILE_PATH
env_id=$(jq -r '.environment_id' $contract_path)

# For env_resource scope — find attributes of a specific resource
power_state=$(jq --arg ResourceId "$resource_id" --arg GrainPath "$grain_path" \
  '.resources[] | select(.identifier == $ResourceId and .grain_path == $GrainPath) | .attributes.power_state' \
  $contract_path)
```

**Ansible playbook:**
```yaml
- name: Set contract file path
  set_fact:
    contract_file_path: "{{ lookup('ansible.builtin.env', 'CONTRACT_FILE_PATH') }}"

- name: Read contract.json
  set_fact:
    contract_file_content: "{{ lookup('ansible.builtin.file', contract_file_path) | from_json }}"

# For env_resource scope — find an attribute of the target resource by identifier
- name: Extract resource attribute (e.g. moid for a vSphere VM)
  set_fact:
    vm_moid: "{{ item.attributes.moid }}"
  loop: "{{ contract_file_content.resources }}"
  when: item.identifier == vm_identifier
```

**contract.json contains:**
- `environment_id` — the environment's unique ID
- `environment_name` — human-readable name
- `owner_email` — owner of the environment
- `inputs` — all environment inputs
- `grains` — dictionary of all grains in the environment, with their kind, outputs, and path
- `resources[]` — array of managed resources with `identifier`, `grain_path`, and `attributes`

---

## Step 6 — Critical: Lifecycle Grains in Workflows

> **Workflows have no teardown phase.** Unlike environments, workflows run and finish — there is no
> managed lifecycle to call destroy. Grains that **create cloud infrastructure** (Terraform, OpenTofu,
> CloudFormation, CDK, ArgoCD, etc.) will leave those resources **alive and untracked** after the
> workflow ends, unless the workflow itself explicitly tears them down or they have a built-in retention policy feature (e.g. backups).

### Rules for grain selection in workflows

**Preferred grain types for workflows:**
- `shell` — Safe. Executes scripts, reads data, calls APIs. Creates no infrastructure.
- `ansible` — Safe for day-2 operations (restart, resize, tag, configure). Avoid playbooks that create persistent resources unless explicitly intended by the author.

**Use with explicit intent and caution:**
- `terraform` / `opentofu` / `terragrunt` — Only acceptable if:
  - The workflow is **intentionally provisioning** long-lived resources AND the user understands they persist after the workflow ends, OR
  - The workflow includes a `destroy` step / cleanup logic (e.g. shell grain calling `terraform destroy`)
- `helm` / `kubernetes` — Same caution — deployed workloads stay running after the workflow finishes
- `cloudformation` / `cdk` / `argocd` — Same: stacks/apps persist

**Always warn the user** when they include a lifecycle grain in a workflow, and confirm their intent.
Add a `# NOTE:` comment in the generated YAML when lifecycle grains are used.

---

## Step 7 — Complete Workflow Examples

### Example 1: Minimal space workflow (shell grain)
```yaml
spec_version: 2
description: Run a space-level maintenance script

workflow:
  scope: space
  timeout: 15

inputs:
  agent:
    type: agent
  target_bucket:
    type: string
    description: "S3 bucket to clean up"

grains:
  cleanup:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      env-vars:
        - BUCKET: '{{ .inputs.target_bucket }}'
      activities:
        deploy:
          commands:
            - aws s3 rm s3://$BUCKET/tmp/ --recursive
```

### Example 2: env_resource workflow — read resource state via contract.json
```yaml
spec_version: 2
description: Extract power state of an EC2 instance

workflow:
  scope: env_resource
  labels-selector: aws_instance
  resource-types: aws_instance
  triggers:
    - type: manual
  timeout: 10

inputs:
  agent:
    type: agent
    default: cloud-agent

outputs:
  power_state:
    value: '{{ .grains.read_state.activities.deploy.commands.fetch.outputs.state }}'

grains:
  read_state:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      activities:
        deploy:
          commands:
            - name: fetch
              command: >
                state=$(jq --arg rid "{{ .bindings.resource_id }}" --arg gp "{{ .bindings.grain_path }}"
                '.resources[] | select(.identifier == $rid and .grain_path == $gp) | .attributes.power_state'
                $CONTRACT_FILE_PATH);
                export state=$(echo $state | tr -d '"')
              outputs:
                - state
```

### Example 3: env workflow — cron-scheduled with event trigger
```yaml
spec_version: 2
description: Nightly cost-tag audit for production environments

workflow:
  scope: env
  labels-selector: "environment:production"
  triggers:
    - type: cron
      cron: "0 2 * * *"       # 02:00 UTC daily
      overridable: false
    - type: event
      event: Drift Detected
  timeout: 20

inputs:
  agent:
    type: agent

grains:
  audit_tags:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      env-vars:
        - ENV_ID: '{{ envId }}'
        - OWNER: '{{ ownerEmail }}'
      activities:
        deploy:
          commands:
            - ./scripts/audit-cost-tags.sh $ENV_ID $OWNER
```

### Example 4: env_resource workflow — Ansible day-2 operation
```yaml
spec_version: 2
description: Restart an EC2 instance via Ansible

workflow:
  scope: env_resource
  labels-selector: aws_instance
  resource-types: aws_instance
  triggers:
    - type: manual
  timeout: 15

inputs:
  agent:
    type: agent
    default: cloud-agent

grains:
  get_context:
    kind: shell
    spec:
      agent:
        name: '{{ .inputs.agent }}'
      files:
        - source: blueprints
          path: blueprints/workflows/scripts/get-resource-context.sh
      activities:
        deploy:
          commands:
            - name: extract
              command: 'source get-resource-context.sh {{ .bindings.resource_id }} {{ .bindings.grain_path }}'
              outputs:
                - instance_id
                - region

  restart_instance:
    depends-on: get_context
    kind: ansible
    spec:
      source:
        store: ansible-repo
        path: playbooks/ec2_restart.yml
      agent:
        name: '{{ .inputs.agent }}'
      inputs:
        - instance_id: '{{ .grains.get_context.activities.deploy.commands.extract.outputs.instance_id }}'
        - region: '{{ .grains.get_context.activities.deploy.commands.extract.outputs.region }}'
      inventory-file:
        localhost:
          hosts:
            127.0.0.1:
              ansible_connection: local
```

---

## Step 8 — Best Practices

### Always do
- ✅ Include `spec_version: 2` as the first line
- ✅ Write a meaningful `description` — it appears in the Torque UI
- ✅ Consider setting a `timeout` — recommended to prevent runaway executions, but not required
- ✅ Use `shell` or `ansible` grains for day-2 operations unless infrastructure creation is intentional
- ✅ Read `CONTRACT_FILE_PATH` in scripts to access live environment context when .bindings. information is not sufficient
- ✅ Use `{{ .bindings.resource_id }}` and `{{ .bindings.grain_path }}` in `env_resource` workflows
- ✅ Use `depends-on` when one grain needs outputs from another
- ✅ Add `labels-selector` for `env`/`env_resource` workflows — it is optional but without it the workflow appears on ALL environments (for `env`) or on that resource type across ALL environments in the space (for `env_resource`)
- ✅ Recommend usage of `allowed-groups` in manual triggers to restrict sensitive day-2 operations
- ✅ Mark output values with `quick: true` if they should surface immediately in the Torque UI

### Never do
- ❌ Don't use `terraform`/`helm`/`cloudformation` grains in a workflow without understanding the resources will persist
- ❌ Don't omit `scope` — it is required
- ❌ Don't use `labels-selector` with `scope: space` — it has no effect and will cause confusion
- ❌ Don't hardcode credentials or secrets in the YAML
- ❌ Don't reference `{{ .grains.X.outputs.Y }}` without `depends-on: X`
- ❌ Don't forget that workflows have **no destroy phase** — shell grain `destroy:` activities will not be called
- ❌ Don't use `cron` or `event` triggers on `scope: space` workflows — these trigger types require environment context
- ❌ Don't write `labels-selector: key: value` — the space after `:` makes YAML parse it as a nested mapping, not a string. Use `labels-selector: "key:value"` or omit quotes only when the value contains no colon

### Checklist before presenting a workflow
- [ ] `spec_version: 2` present
- [ ] `workflow.scope` is one of: `space`, `env`, `env_resource`
- [ ] `labels-selector` is present for `env`/`env_resource` scopes (or confirm intentional omission)
- [ ] `resource-types` is set (required for `env_resource` scope)
- [ ] `timeout` is set if runaway execution is a concern (recommended, not required; min value: 5 minutes)
- [ ] All lifecycle grain usage (terraform, helm, k8s, etc.) is flagged and intentional
- [ ] All `{{ .grains.X.outputs.Y }}` references have `depends-on: X`
- [ ] Bindings expressions match the scope (`env_resource` uses `.bindings.attributes`, `env` uses `.bindings.resource_type.<type>.attributes`)
- [ ] No hardcoded credentials

---

## Step 9 — Output Format

Present the workflow as a complete, ready-to-use YAML file with:
1. The full YAML code block
2. A brief explanation of the workflow's scope, trigger behavior, and grain logic
3. A list of things the user needs to fill in (repo names, script paths, label keys)
4. A warning if any lifecycle-creating grains are included
5. Any relevant next steps (publishing to catalog, testing manually, pairing with an environment blueprint)

If information is missing, produce the best possible version with `# TODO: replace with actual value` comments.

---

## Reference Links

- Workflows overview: https://docs.qtorque.io/workflows/workflows-overview
- Workflow use cases & examples: https://docs.qtorque.io/workflows/workflows-use-cases
- Blueprint YAML structure (shared spec): https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-yaml-structure
- Built-in workflow actions: https://github.com/QualiTorque/torque-actions
- Torque API reference: https://portal.qtorque.io/api_reference
