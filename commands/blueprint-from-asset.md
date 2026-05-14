---
description: Scaffold a Torque blueprint from an existing IaC asset (Terraform, OpenTofu, Helm, Ansible, K8s, CloudFormation, Terragrunt)
argument-hint: [path-to-asset]
---

Generate a Torque blueprint that wraps the IaC asset at @$1.

## Step 1 — Detect asset type

Inspect the path "$1":

| Heuristic | Asset type | Grain kind |
|---|---|---|
| Contains `*.tf` files, no `terragrunt.hcl` | Terraform | `terraform` |
| Contains `*.tf` + `versions.tf` referencing `opentofu` provider, or `*.tofu` files | OpenTofu | `opentofu` |
| Contains `terragrunt.hcl` | Terragrunt | `terragrunt` (or migrate — see below) |
| Contains `Chart.yaml` | Helm chart | `helm` |
| Contains `*.yaml`/`*.yml` with `apiVersion:` + `kind:` (Deployment, Service, etc.) | K8s manifests | `kubernetes` |
| Contains `playbook.yml` or `site.yml` or `roles/` dir | Ansible | `ansible` |
| Contains `template.yaml` with `AWSTemplateFormatVersion` | CloudFormation | `cloudformation` |
| Contains `cdk.json` | AWS CDK | `cdk` |
| Contains `*.sh` w/ no other IaC markers | Shell scripts | `shell` |

If multiple types are detected, ask the user which one to wrap (or whether to compose them as multiple grains in one blueprint — common pattern: TF for infra + Ansible for config).

If type can't be determined, ask the user.

## Step 2 — Inspect the asset

Read the source files to extract:

- **Terraform/OpenTofu** — `variables.tf` (inputs), `outputs.tf` (outputs), `versions.tf` (provider versions), `*.tfvars` (defaults).
- **Helm** — `values.yaml` (inputs), `Chart.yaml` (name, version), notable templates that reference services / ingresses.
- **K8s manifests** — list of resources, target namespace, env-var dependencies.
- **Ansible** — `vars/`, `defaults/`, role list, hosts pattern.
- **CloudFormation** — Parameters block, Outputs block, region requirements.

Note assets the blueprint will need to expose to users (e.g., region, instance size, replicas) and outputs worth surfacing (e.g., endpoint URLs, IDs).

## Step 3 — Generate blueprint

Invoke the `torque-blueprint` skill to produce the YAML. Pass it:
- The detected grain kind.
- Extracted inputs (mapped to Torque blueprint inputs with types and defaults).
- Extracted outputs (mapped to grain outputs + optionally blueprint outputs with `kind: link` for URLs).
- A reasonable `source.store` placeholder (`# TODO: replace with your Torque-connected repo name`).
- An `agent` input of `type: agent`.

For multi-asset directories, also wire `depends-on` between grains.

For Terragrunt assets specifically, hand off to the `torque-terragrunt-migrate` skill — it does dependency-block and remote_state conversion that's beyond a basic wrap.

For Terraform/OpenTofu assets, also invoke `torque-ready-terraform` skill to flag any module-side changes needed (e.g., missing outputs, hardcoded values that should be variables).

For Ansible, invoke `torque-ready-ansible` skill for similar pre-flight refactor suggestions.

## Step 4 — Validate

After generating the blueprint, run `/deploy-check` on the result. Report and fix any issues before presenting the final YAML.

## Step 5 — Present

Show:
1. The complete blueprint YAML.
2. A short list of what was inferred vs. assumed.
3. TODO markers for user-supplied values (repo name, agent name).
4. Any module-side refactors recommended by the `torque-ready-*` skills.
