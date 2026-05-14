---
name: torque-ready-ansible
description: "Use this skill whenever the user is writing, reviewing, or refactoring an Ansible playbook that will run inside Torque (Quali Torque). Triggers include: mentions of 'Ansible', 'playbook', 'Torque', 'grain', 'blueprint', 'inventory-file', 'torque.collections', 'export_torque_outputs', 'on-destroy', or requests to make a playbook 'Torque-ready' or 'Torque-compatible'. Also trigger when the user asks about passing variables to Ansible from Torque, dynamic inventory in blueprints, Ansible grain outputs, or teardown playbooks. Use for writing new playbooks, converting existing ones, reviewing playbooks for Torque compatibility, adding outputs, writing teardown playbooks, or structuring playbook directories."
 
---
 
# Writing Torque-Ready Ansible Playbooks
 
## How Torque Executes an Ansible Grain
 
When a Torque environment launches an Ansible grain, four things happen in order:
 
1. **Inventory Generation**: Torque reads the `inventory-file` section from the blueprint YAML and writes a standard Ansible inventory file. The playbook never ships its own inventory.
2. **Inputs as Extra-Vars**: Torque collects the grain `inputs`, writes them to `/var/run/ansible/inputs/inputs.json`, and passes `--extra-vars @/var/run/ansible/inputs/inputs.json` to `ansible-playbook`.
3. **Playbook Execution**: `ansible-playbook <playbook.yaml> --extra-vars @inputs.json -i <generated-inventory>` plus any `command-arguments` from the blueprint.
4. **Output Collection**: Torque reads outputs exported by `torque.collections.export_torque_outputs` and makes them available to downstream grains.
 
**Key insight**: A well-written playbook does not need to know it is running inside Torque. If it accepts variables via extra-vars and works with a standard inventory, it works both locally and in Torque without modification.
 
---
 
## The 7 Rules
 
Apply all 7 rules when writing or reviewing a playbook. Then use the checklist at the end to verify.
 
### Rule 1: Use Variables, Not Hardcoded Values
 
Every value that might change between environments must be a variable with a sensible default.
 
**Where variables come from in Torque (Ansible precedence order):**
 
| Source | Precedence | Best For |
|--------|-----------|----------|
| Grain `inputs` (extra-vars) | Highest: overrides everything | Names, sizes, regions, feature flags |
| `inventory-file` vars | Group/host var level | Connection info: credentials, endpoints, ansible_user |
| Playbook `vars` section | Play-level defaults | Sensible fallbacks for standalone testing |
 
**Pattern**: Use the Jinja2 `default` filter everywhere:
 
```yaml
vars:
  app_name: "{{ application_name | default('my-app') }}"
  db_engine: "{{ database_engine | default('postgres') }}"
  region: "{{ deploy_region | default('us-east-1') }}"
  env_name: "{{ environment | default('dev') }}"
```
 
**Never hardcode**:
- Credentials (API keys, passwords, tokens)
- Resource names (server names, policy names, DNS records)
- Connection info (IP addresses, endpoints, ports)
 
### Rule 2: Let Torque Own the Inventory
 
The playbook must NOT ship with a static inventory file. Torque generates the inventory from the blueprint's `inventory-file` section at runtime.
 
**Design the `hosts` directive for flexibility:**
 
```yaml
# GOOD: variable host group with a default
- hosts: "{{ target_group | default('web_servers') }}"
  become: true
 
# GOOD: API-only playbooks that run locally
- hosts: localhost
  connection: local
  gather_facts: false
 
# GOOD: all hosts in the provided inventory
- hosts: all
 
# BAD: hardcoded group name without override
- hosts: production_servers
```
 
**How the blueprint creates the inventory** (for reference):
 
```yaml
# Blueprint YAML (written by the blueprint author, not the playbook author):
inventory-file:
  web_servers:
    hosts:
      web1:
        ansible_host: '{{ .grains.provision.outputs.vm_ip }}'
    vars:
      ansible_user: '{{ .inputs.ssh_user }}'
      ansible_become: true
      http_port: '{{ .inputs.http_port }}'
```
 
This generates a standard Ansible inventory. The playbook sees no difference from a manually written inventory file.
 
**Document the contract**: Every playbook README must list expected host groups, required inventory vars, and required extra-vars.
 
### Rule 3: Centralize Credentials with YAML Anchors
 
When your playbook calls an external API, define a single YAML anchor for credentials and reference it in every task:
 
```yaml
vars:
  cloud_auth: &cloud_auth
    access_key: "{{ cloud_access_key }}"
    secret_key: "{{ cloud_secret_key }}"
    region: "{{ cloud_region | default('us-east-1') }}"
 
tasks:
  - name: Create resource
    cloud_module:
      <<: *cloud_auth
      name: "{{ resource_name }}"
    tags: [provision]
```
 
For SSH-based playbooks, connection credentials come entirely from inventory vars (`ansible_host`, `ansible_user`, `ansible_become`, `ansible_ssh_private_key_file`). The playbook does not need to define them.
 
### Rule 4: Export Outputs with torque.collections
 
If the playbook creates resources that downstream grains or blueprint outputs need to reference, export them using `torque.collections.export_torque_outputs`.
 
```yaml
- name: Export outputs to Torque
  torque.collections.export_torque_outputs:
    outputs:
      app_url: "{{ deploy_result.url }}"
      resource_id: "{{ create_result.id }}"
      deploy_status: "{{ 'success' if deploy_result.rc == 0 else 'failed' }}"
  delegate_to: localhost
  run_once: true
  tags: always
  ignore_errors: true   # Allows standalone testing without Torque
```
 
**Critical rules for the export task:**
- `delegate_to: localhost` (must run on the Ansible controller)
- `run_once: true` (avoid duplicate exports in multi-host plays)
- `tags: always` (runs regardless of `--tags` / `--skip-tags` filters)
- `ignore_errors: true` (optional, for graceful standalone testing)
- Use `snake_case` for output names
- Export the minimum needed (IDs, URLs, names), not entire command outputs
 
**Include in requirements.yaml:**
 
```yaml
collections:
  - name: torque.collections
```
 
### Rule 5: Tag Tasks for Selective Execution
 
Tag every task or block so the blueprint author can use `command-arguments: "--tags install"` or `"--skip-tags database"` to run subsets of the playbook.
 
**Tagging strategy:**
- Broad category tags: `install`, `configure`, `deploy`, `validate`, `cleanup`
- Specific tags: `nginx`, `postgres`, `monitoring`, `firewall`, `dns`
- Always tag the output export task with `always`
 
```yaml
tasks:
  - name: Install web server
    apt: name=nginx state=present
    tags: [nginx, install]
 
  - name: Configure web server
    template: src=nginx.conf.j2 dest=/etc/nginx/nginx.conf
    tags: [nginx, configure]
 
  - name: Export outputs
    torque.collections.export_torque_outputs:
      outputs:
        web_url: "http://{{ ansible_host }}:{{ http_port }}"
    delegate_to: localhost
    run_once: true
    tags: always
```
 
### Rule 6: Write a Teardown Playbook for on-destroy
 
When a playbook creates resources, write a companion `teardown.yaml` in the same directory. The Torque Ansible grain's `on-destroy` section references this playbook and runs it when the environment is terminated.
 
```yaml
# teardown.yaml
---
- name: Clean up resources
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Remove DNS record
      community.general.cloudflare_dns:
        zone: "{{ dns_zone }}"
        record: "{{ app_name }}"
        state: absent
      tags: [dns]
 
    - name: Deregister from service registry
      uri:
        url: "{{ registry_url }}/{{ app_name }}"
        method: DELETE
      tags: [registry]
```
 
**Key points:**
- The teardown playbook is fully self-contained; do not assume state from the deploy phase persists.
- It receives its own `inputs` and `inventory-file` from the blueprint's `on-destroy` section.
- Use `state: absent` or DELETE methods to remove resources.
- Use `hosts: localhost` / `connection: local` for API-driven teardown.
 
**How the blueprint references it:**
 
```yaml
on-destroy:
  source:
    store: my-repo
    path: ansible/deploy-app/teardown.yaml
  inputs:
    - app_name: '{{ .inputs.app_name }}'
    - dns_zone: '{{ .inputs.dns_zone }}'
  inventory-file:
    localhost:
      hosts:
        127.0.0.1:
          ansible_connection: local
```
 
### Rule 7: Structure Your Playbook Directory
 
Torque auto-discovers playbooks and auto-installs dependencies from `requirements.yaml` in the playbook directory.
 
```
ansible/<grain-name>/
  playbook.yaml           # Main entry point (Torque source path points here)
  teardown.yaml           # on-destroy playbook (if playbook creates resources)
  requirements.yaml       # Galaxy dependencies (auto-installed by Torque)
  README.md               # Documents host groups, vars, inputs, outputs
  roles/                  # Optional local roles
    <role-name>/
      tasks/main.yaml
      defaults/main.yaml
```
 
---
 
## Complete Torque-Ready Playbook Template
 
Use this as a starting point for any new playbook:
 
```yaml
---
# ansible/<grain-name>/playbook.yaml
#
# Expected host groups: app_servers (or override via 'target_group')
# Required inventory vars: ansible_user, ansible_become
# Optional inventory vars: ansible_ssh_private_key_file
#
# Grain inputs (extra-vars):
#   app_name       (default: 'my-app')   - Application name
#   app_version    (default: 'latest')   - Version to deploy
#   environment    (default: 'dev')      - Target environment
#   http_port      (default: 8080)       - HTTP listen port
#
# Outputs:
#   app_url       - URL of the deployed application
#   deploy_status - 'success' or 'failed'
 
- name: "Deploy Application"
  hosts: "{{ target_group | default('app_servers') }}"
  become: true
  gather_facts: true
 
  vars:
    app: "{{ app_name | default('my-app') }}"
    version: "{{ app_version | default('latest') }}"
    env: "{{ environment | default('dev') }}"
    port: "{{ http_port | default(8080) }}"
 
  tasks:
    - name: Install application
      package:
        name: "{{ app }}"
        state: present
      tags: [install]
 
    - name: Configure application
      template:
        src: app.conf.j2
        dest: "/etc/{{ app }}/config.yml"
      notify: restart app
      tags: [configure]
 
    - name: Verify application is running
      uri:
        url: "http://localhost:{{ port }}/health"
        status_code: 200
      retries: 5
      delay: 3
      tags: [validate]
 
    - name: Export outputs to Torque
      torque.collections.export_torque_outputs:
        outputs:
          app_url: "http://{{ ansible_host }}:{{ port }}"
          deploy_status: "success"
      delegate_to: localhost
      run_once: true
      tags: always
      ignore_errors: true
 
  handlers:
    - name: restart app
      service:
        name: "{{ app }}"
        state: restarted
```
 
---
 
## Pre-Commit Checklist
 
Run through this list before committing any playbook:
 
| # | Check | What to look for |
|---|-------|-----------------|
| 1 | No hardcoded credentials | Passwords, API keys, tokens come from variables, never literals |
| 2 | Credential anchor defined (if API playbook) | Single YAML anchor, all tasks reference via `<<: *anchor` |
| 3 | Host group is variable | `hosts: "{{ var \| default('GroupName') }}"` or `hosts: localhost` |
| 4 | All configurable values are variables | Names, ports, regions, sizes use `{{ var \| default(value) }}` |
| 5 | Outputs exported | `export_torque_outputs` with `delegate_to: localhost`, `run_once: true`, `tags: always` |
| 6 | Tasks are tagged | Broad + specific tags for selective execution |
| 7 | `requirements.yaml` exists | Lists all Galaxy dependencies including `torque.collections` |
| 8 | `teardown.yaml` exists (if applicable) | Companion with `state: absent` / cleanup logic |
| 9 | README.md documents contract | Host groups, inventory vars, grain inputs, outputs, teardown |
| 10 | No static inventory shipped | Playbook works with any inventory provided at runtime |
| 11 | `gather_facts` set appropriately | `false` for API-only, `true` when you need system facts |
| 12 | `connection` set appropriately | `local` for API calls, default (`ssh`) for remote hosts |
 
---
 
## How to Review an Existing Playbook
 
When converting an existing playbook to be Torque-ready:
 
1. **Find all hardcoded values**: Search for literal strings in module arguments (names, IPs, credentials). Replace each with a variable and add a default in the `vars` section.
2. **Check the `hosts` directive**: If it targets a hardcoded group, wrap it in `{{ target_group | default('OriginalGroup') }}`.
3. **Look for repeated credential blocks**: Consolidate into a single YAML anchor.
4. **Check for `register` results used later**: Any registered result that a downstream grain would need should be exported via `export_torque_outputs`.
5. **Look for resource creation tasks**: Any task that creates infrastructure needs a corresponding cleanup task in `teardown.yaml`.
6. **Verify tags exist**: Every task or logical block should be tagged.
7. **Check for shipped inventory files**: Remove any static inventory. Add a README documenting expected host groups and vars instead.
 
---
 
## Blueprint Reference (For Context Only)
 
Playbook authors do not write blueprints, but understanding the mapping helps write better playbooks:
 
```yaml
grains:
  deploy_app:
    kind: ansible
    spec:
      source:
        store: my-repo                         # Torque repo store name
        path: ansible/deploy-app/playbook.yaml
      agent:
        name: '{{ .inputs.agent }}'
      inventory-file:                          # Generates Ansible inventory
        app_servers:
          hosts:
            server1:
              ansible_host: '{{ .grains.provision.outputs.vm_ip }}'
          vars:
            ansible_user: '{{ .inputs.ssh_user }}'
            ansible_become: true
      inputs:                                  # Become --extra-vars
        - app_name: '{{ .inputs.app_name }}'
        - app_version: '{{ .inputs.version }}'
        - http_port: '{{ .inputs.port }}'
      command-arguments: "--tags install,configure"
      outputs:                                 # Must match export_torque_outputs keys
        - app_url
        - deploy_status
      on-destroy:                              # Runs teardown.yaml on env termination
        source:
          store: my-repo
          path: ansible/deploy-app/teardown.yaml
        inputs:
          - app_name: '{{ .inputs.app_name }}'
        inventory-file:
          localhost:
            hosts:
              127.0.0.1:
                ansible_connection: local
```
 
**What this means for the playbook author:**
- `inputs` keys become top-level Ansible variables
- `inventory-file` becomes a generated Ansible inventory with the exact groups and vars listed
- `outputs` must match the keys passed to `export_torque_outputs`
- `on-destroy` runs `teardown.yaml` with its own separate inputs and inventory
- `command-arguments` can filter tasks via `--tags` or `--skip-tags`
 