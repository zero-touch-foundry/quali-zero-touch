---
description: Pre-deployment validation checklist for a blueprint
argument-hint: [blueprint-file-path]
---

Run a pre-deployment validation checklist on the blueprint at @$1.

Check the following and report results:

1. **YAML syntax**: Valid YAML with no parsing errors.
2. **spec_version**: Must be `2`.
3. **Inputs**: All inputs have a type. Sensitive inputs are marked `sensitive: true`. Defaults are provided where appropriate.
4. **Grain structure**: Each grain has `kind` and `spec`. Each spec has `source` (with `store` and `path`) and `agent`.
5. **Liquid references**: All `{{ .inputs.* }}` references match declared inputs. All `{{ .grains.*.outputs.* }}` references point to grains and outputs that exist.
6. **Dependencies**: `depends-on` references exist as grain names. No circular dependencies.
7. **Outputs**: Blueprint outputs reference valid grain outputs.
8. **Naming**: Blueprint file uses `.yaml` extension (not `.yml`). Grain names use valid identifiers.
9. **Security**: No hardcoded credentials, tokens, or secrets in the YAML. Sensitive values use inputs or parameter store references.
10. **Best practices**: Terraform grains have a backend configured. Helm grains specify a target namespace. Ansible grains have an `on-destroy` playbook for clean teardown.

Present results as a checklist with pass/fail for each item. For any failures, explain what's wrong and how to fix it.
