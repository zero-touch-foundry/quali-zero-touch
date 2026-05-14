---
name: torque-blueprints
description: >
  Use this skill when the user asks to "create a blueprint", "write a blueprint",
  "design a Torque blueprint", "add a grain", "configure blueprint inputs",
  "set up blueprint outputs", or needs help with Torque blueprint YAML syntax,
  grain configuration, Liquid templating, or blueprint structure. Also trigger
  when the user mentions specific grain types like Terraform, Helm, Kubernetes,
  Ansible, Shell, CloudFormation, ArgoCD, CDK, OpenTofu, or Terragrunt in
  a Torque blueprint context.
version: 0.1.0
---

# Torque Blueprint Authoring

Guide users through creating, editing, and troubleshooting Torque blueprint YAML files.

## Blueprint Basics

Torque blueprints are YAML files (`.yaml` extension, NOT `.yml`) stored in a `/blueprints` folder in a connected Git repository. They define environments composed of infrastructure-as-code components called **grains**.

Every blueprint starts with:

```yaml
spec_version: 2
description: What this environment provides

inputs:
  # User-configurable parameters

outputs:
  # Values exposed after environment launch

grains:
  # Infrastructure components
```

## Inputs

Inputs let end-users customize environments. Supported types: `string`, `agent`, `parameter`, `credentials`, `file`, `input-source`.

Key properties per input: `type`, `default`, `allowed-values`, `description`, `sensitive` (masks value), `pattern` (regex), `validation-description`, `style` (radio | duration | multi-select).

For file inputs, also specify `max-size-MB`, `max-files`, `allowed-formats`.

Reference inputs inside grains with Liquid: `{{ .inputs.input_name }}`.

## Outputs

Outputs expose values to users and downstream automation:

```yaml
outputs:
  endpoint:
    value: '{{ .grains.my_app.outputs.url }}'
    quick: true
    kind: link
```

`quick: true` shows the output in the Quick Access section. `kind: link` renders it as a clickable URL.

## Grains

Each grain has: `kind` (technology type), `spec` (configuration block with source, agent, inputs, outputs, etc.), and optionally `depends-on` for ordering.

### Supported grain kinds

terraform, helm, kubernetes, ansible, shell, cloudformation, blueprint, cloudshell, cdk, argocd, opentofu, terragrunt, custom.

### Common grain properties

- **source**: `store` (repo name) + `path` (folder path), with optional `branch`, `tag`, or `commit`
- **agent**: deployment runner, with optional `storage-size`, `runner-namespace`, `service-account`, `node-selector`
- **inputs/outputs**: data flow between grains
- **depends-on**: deployment ordering (grains without dependencies deploy in parallel)
- **env-vars**: environment variables for the grain's execution
- **tags**: auto-tagging control with `auto-tag: true/false`

## Liquid Templating

Torque uses Shopify Liquid for dynamic values:

- Blueprint inputs: `{{ .inputs.var_name }}`
- Grain outputs: `{{ .grains.grain_name.outputs.output_name }}`
- Parameter store: `{{ .params.param_name }}`
- Built-in attributes: `envId`, `blueprintName`, `ownerEmail`, `environmentName`, `accountName`, `spaceName`
- Filters: `downcase`, `strip`, `key_access`

## Blueprint Authoring Workflow

When helping a user create a blueprint:

1. Clarify what the environment should contain (which cloud resources, apps, services).
2. Determine which grain types are needed.
3. Ask about inputs the end-user should be able to customize.
4. Draft the blueprint YAML with proper structure.
5. Add outputs for any values users need (URLs, connection strings, etc.).
6. Set `depends-on` for grains that require ordered deployment.
7. Validate the YAML structure.

When the user selects a grain and asks to connect it to another resource, first use the `get_grain_usage_examples` tool (via Torque MCP) to find example usages, then use `get_blueprint_yaml` to see how grains connect. Use `get_current_torque_space` to determine the active space.

For detailed grain-type-specific configuration, read the appropriate reference file in `references/`.
