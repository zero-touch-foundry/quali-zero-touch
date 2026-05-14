---
name: ansible-automation
description: >
  Use this skill when the user asks about "Ansible playbook", "Ansible role",
  "Ansible collection", "inventory management", "Ansible vault", "playbook patterns",
  "configuration management", "Ansible best practices", or needs help writing,
  reviewing, or debugging Ansible playbooks. Also trigger when the user needs
  Ansible automation that integrates with Torque environments, AWS, or Kubernetes.
  For Torque-specific Ansible grain configuration, this skill complements the
  torque-blueprints skill.
version: 0.1.0
---

# Ansible Automation

Guide users through Ansible playbook authoring, best practices, and integration with Torque and cloud infrastructure.

## Playbook Structure

Organize playbooks following Ansible best practices:

```
project/
├── inventories/
│   ├── production/
│   │   ├── hosts.yml
│   │   └── group_vars/
│   └── staging/
├── roles/
│   └── role-name/
│       ├── tasks/main.yml
│       ├── handlers/main.yml
│       ├── templates/
│       ├── files/
│       ├── vars/main.yml
│       └── defaults/main.yml
├── playbooks/
│   ├── deploy.yml
│   └── teardown.yml
├── requirements.yml
└── ansible.cfg
```

## Writing Best Practices

- Use roles for reusable, modular automation.
- Keep playbooks focused — one purpose per playbook.
- Use `ansible-vault` for all sensitive data (passwords, keys, tokens).
- Define variables in `defaults/main.yml` (overridable) vs `vars/main.yml` (fixed).
- Use `handlers` for service restarts triggered by configuration changes.
- Prefer `template` (Jinja2) over `copy` for files needing variable substitution.
- Use `block/rescue/always` for error handling.
- Tag tasks for selective execution (`--tags deploy`, `--skip-tags debug`).
- Use `check` mode (`--check`) to preview changes before applying.

## Idempotency

Every task should be safe to run multiple times without side effects:

- Use Ansible modules (not `shell`/`command`) whenever possible.
- For `shell`/`command`, add `creates` or `removes` conditions.
- Use `changed_when` and `failed_when` to control task status accurately.
- Test with `--check --diff` to verify idempotent behavior.

## Inventory Management

- Use YAML inventory format over INI for clarity.
- Group hosts by function (webservers, databases) and environment (prod, staging).
- Use `group_vars` and `host_vars` for per-group and per-host configuration.
- For dynamic inventories, use inventory plugins (AWS EC2, Azure, GCP).

## Collections & Roles

- Install external dependencies via `requirements.yml`.
- Pin collection and role versions for reproducibility.
- Use `ansible-galaxy` to install and manage dependencies.
- Common collections: `amazon.aws`, `community.general`, `kubernetes.core`, `ansible.posix`.

## Torque Integration

Ansible grains in Torque have specific patterns:

- Inputs are provided as extra-vars, serialized to `/var/run/ansible/inputs/inputs.json`.
- Use `export-torque-outputs` module to pass results to other grains.
- Define `on-destroy` playbooks for clean teardown.
- Auto-installs from `requirements.yaml`/`requirements.yml` in module root.
- Use `inventory-file` in the grain spec for dynamic inventory from other grain outputs.
- Pre-playbook scripts handle vault file creation or environment setup.

For the Torque-specific grain YAML syntax, refer to the torque-blueprints skill's grain reference.

## Common Patterns

### AWS provisioning with Ansible

Use `amazon.aws` collection modules. Authenticate via environment variables or `aws_profile`. Combine with Terraform for infrastructure + Ansible for configuration.

### Kubernetes management with Ansible

Use `kubernetes.core` collection. Authenticate via kubeconfig. Useful for complex deployment orchestration that goes beyond simple manifest application.

### Configuration drift detection

Run playbooks in check mode on a schedule to detect configuration drift. Report changes without applying them.
