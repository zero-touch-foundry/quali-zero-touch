---
name: torque-rego
description: >
  Use this skill whenever the user wants to create, write, edit, fix, or review a Torque OPA/Rego 
  governance policy. Triggers include: "write a Torque policy", "create a Rego policy for Torque",
  "OPA policy for Torque", "governance policy", "consumption policy", "environment lifecycle policy",
  "terraform plan policy", "deny environments longer than X hours", "limit concurrent environments",
  "restrict instance types", "approval policy for Torque", "cost control policy", "policy to block X",
  "Torque policy that requires approval", "torque.environment package", "torque.consumption package",
  "torque.terraform_plan package".
  Also trigger when the user asks to debug a failing Rego policy, add data parameters, or wire 
  approval channels in a Torque governance context.
  Always use this skill — do NOT try to write Torque Rego policies from memory alone.
---

# Torque Rego Policy Skill

## Overview

Torque uses **OPA (Open Policy Agent)** with `.rego` files for governance. Policies can block 
environment launches, trigger approval workflows, or evaluate Terraform plans during deployment.
You will write correct, well-commented, production-ready Rego policies.

---

## Greenfield projects — defer to `repo-conventions` for repo layout

This skill owns the **content** of a `.rego` policy file (package, rules, helpers, approval channels). It does NOT own **where in the repo** that file lives.

If you are creating a policy from scratch as part of building a new Torque project — i.e. there is no existing repo layout to follow — **invoke the `repo-conventions` skill FIRST** to lock in the canonical location (`policies/<policy-name>.rego` at repo root, flat — one file per policy), then return here for the policy's content.

---

## Step 1 — Fetch Live Documentation

**Always fetch fresh documentation before writing any policy.**

```
web_fetch: https://docs.qtorque.io/governance/policies
```

Also fetch OPA built-in examples for reference:
```
web_fetch: https://github.com/QualiTorque/opa
```

For OPA language reference (if needed):
```
web_fetch: https://www.openpolicyagent.org/docs/latest/policy-reference/
```

---

## Step 2 — Understand What the User Needs

Before writing, clarify:
- **What should the policy do?** (block, require approval, or allow)
- **When should it trigger?** (at catalog click, at launch/extend, or during Terraform plan)
- **What data parameters** will admins configure? (e.g., max duration, allowed regions)
- **Is approval required** or should it hard-deny?
- **What spaces/scope** should it apply to?

---

## Step 3 — Policy Types Reference

Torque supports exactly **3 policy types**, determined by the `package` name:

| Package | Trigger | Use Case |
|---|---|---|
| `torque.consumption` | When user clicks a catalog item | Pre-launch gates (before inputs are filled) |
| `torque.environment` | On environment launch or extend | Input-aware launch/extend controls |
| `torque.terraform_plan` | During Terraform grain deployment | Infrastructure compliance scanning |

### Which type to use?
- **Consumption**: Limit who can even start launching (e.g., "only premium users can launch this") — no input values available yet
- **Environment**: Limit launch based on inputs (e.g., "max duration 3 hours", "only 5 concurrent envs per user")
- **Terraform**: Scan the actual infrastructure (e.g., "no IAM changes", "only allowed instance types")

---

## Step 4 — Policy Syntax Reference

### `torque.environment` policy structure

The policy must return a `result` object with a `decision` field.

```rego
package torque.environment

# Simple deny
result = { "decision": "Denied", "reason": "Duration exceeds 8 hours" } if {
    input.duration_minutes > 480
}

# Default: allow everything not matched by a deny rule
result = { "decision": "Approved" } if {
    not input.duration_minutes > 480
}
```

Decision values: `"Denied"` | `"Manual"` (triggers approval flow) | `"Approved"`

### `torque.consumption` policy structure

Same as environment, but `input.inputs` and `input.workflows` are NOT available.

```rego
package torque.consumption

result = { "decision": "Denied", "reason": "This blueprint requires VIP access" } if {
    not "vip" in input.groups
}

result = { "decision": "Approved" } if {
    "vip" in input.groups
}
```

### `torque.terraform_plan` policy structure

Must have at least one `deny` rule. Uses the Terraform plan JSON as input.

```rego
package torque.terraform_plan

# resources is a helper: groups resource changes by type
resources[resource_type] = all {
    all := [resource | 
        resource := input.resource_changes[_]
        resource.type == resource_type
    ]
}

deny[reason] {
    all := resources["aws_iam_role"]
    count(all) > 0
    reason := "IAM role changes require manual review"
}

deny[reason] {
    resource := input.resource_changes[_]
    resource.type == "aws_instance"
    instance_type := resource.change.after.instance_type
    not instance_type in data.allowed_instance_types
    reason := sprintf("Instance type '%v' is not in the allowed list", [instance_type])
}
```

---

## Step 5 — The `input` Object

### For `torque.environment` and `torque.consumption`

```json
{
    "blueprint": {
        "name": "my-bp-name",
        "repository": "my-repo",
        "labels": [],
        "grains": [
            { "kind": "terraform", "name": "myGrain" }
        ]
    },
    "inputs": [                          // NOT available in consumption policies
        {
            "name": "input_name",
            "type": "string",
            "value_v2": {
                "value": "input_value"
            },
            "sensitive": false,
            "description": null
        }
    ],
    "timezone": "Asia/Jerusalem",
    "duration_minutes": 100,             // Requested duration at launch; total duration before extension
    "extend_duration_minutes": 100,      // null if action is "launch"
    "blueprint_avg_hourly_cost": null,
    "space_name": "my_space",
    "user_email": "me@mycorp.com",
    "groups": ["group1", "group2"],
    "roles": {
        "account_roles": ["role1"],
        "space_roles": ["role2"]
    },
    "is_git_environment": false,
    "entity_name": "my-env",
    "action_identifier": {
        "entity_type": "Environment",
        "entity_id": null,
        "action_type": "Launch"          // "Launch" or "Extend"
    },
    "owner_active_environments_in_space": 1,
    "owner_active_environments_in_account": 1,
    "active_environments_in_space": 5,
    "active_environments_in_account": 12
}
```

### Accessing inputs by name

Input values use the `value_v2` schema (nested `value` field):

```rego
# Get a specific input value (note: value is nested under value_v2)
get_input_value(name) = value {
    input_obj := input.inputs[_]
    input_obj.name == name
    value := input_obj.value_v2.value
}
```

---

## Step 6 — The `data` Object

`data` is the admin-configurable values set in the Torque UI when applying the policy.
Define what data keys your policy expects, and document them clearly.

```rego
package torque.environment

# data.max_duration_minutes — set by admin in Torque UI
# data.max_environments_per_user — set by admin in Torque UI

result = { "decision": "Denied", "reason": reason } if {
    input.duration_minutes > data.max_duration_minutes
    reason := sprintf("Duration %v minutes exceeds allowed maximum of %v minutes", 
                      [input.duration_minutes, data.max_duration_minutes])
}
```

When the policy is applied in Torque, the admin fills in `max_duration_minutes` in a form.

---

## Step 7 — Complete Policy Examples

### Example 1: Limit environment duration with approval threshold

```rego
package torque.environment

# data.hard_limit_minutes — environments above this are always denied
# data.approval_limit_minutes — environments above this require approval

result = { "decision": "Denied", "reason": reason } if {
    input.duration_minutes > data.hard_limit_minutes
    reason := sprintf("Environment duration %v min exceeds hard limit of %v min",
                      [input.duration_minutes, data.hard_limit_minutes])
}

result = { "decision": "Manual", "reason": reason } if {
    input.duration_minutes > data.approval_limit_minutes
    input.duration_minutes <= data.hard_limit_minutes
    reason := sprintf("Environment duration %v min requires approval (limit: %v min)",
                      [input.duration_minutes, data.approval_limit_minutes])
}

result = { "decision": "Approved" } if {
    input.duration_minutes <= data.approval_limit_minutes
}
```

### Example 2: Limit concurrent environments per user

```rego
package torque.environment

# data.max_active_per_user — max concurrent environments per user per space

result = { "decision": "Denied", "reason": reason } if {
    input.owner_active_environments_in_space >= data.max_active_per_user
    reason := sprintf("You already have %v active environments in this space (max: %v)",
                      [input.owner_active_environments_in_space, data.max_active_per_user])
}

result = { "decision": "Approved" } if {
    input.owner_active_environments_in_space < data.max_active_per_user
}
```

### Example 3: Restrict access by group

```rego
package torque.consumption

# data.allowed_groups — list of groups allowed to consume this blueprint

result = { "decision": "Denied", "reason": "You are not in an authorized group for this blueprint" } if {
    authorized_groups := {g | g := data.allowed_groups[_]}
    user_groups := {g | g := input.groups[_]}
    count(authorized_groups & user_groups) == 0
}

result = { "decision": "Approved" } if {
    authorized_groups := {g | g := data.allowed_groups[_]}
    user_groups := {g | g := input.groups[_]}
    count(authorized_groups & user_groups) > 0
}
```

### Example 4: Block specific blueprint by name

```rego
package torque.consumption

# data.blocked_blueprints — list of blueprint names to block

result = { "decision": "Denied", "reason": reason } if {
    blocked := {b | b := data.blocked_blueprints[_]}
    input.blueprint.name in blocked
    reason := sprintf("Blueprint '%v' is currently not available for deployment", [input.blueprint.name])
}

result = { "decision": "Approved" } if {
    blocked := {b | b := data.blocked_blueprints[_]}
    not input.blueprint.name in blocked
}
```

### Example 5: Terraform plan — allow only specific AWS regions

```rego
package torque.terraform_plan

# data.allowed_regions — list of allowed AWS regions

deny[reason] {
    resource := input.resource_changes[_]
    resource.change.after.region != null
    not resource.change.after.region in data.allowed_regions
    reason := sprintf("Resource '%v' targets region '%v' which is not allowed. Allowed regions: %v",
                      [resource.address, resource.change.after.region, data.allowed_regions])
}
```

### Example 6: Terraform plan — enforce tagging

```rego
package torque.terraform_plan

# Ensure all resources have required tags

required_tags := {"Environment", "Owner", "CostCenter"}

deny[reason] {
    resource := input.resource_changes[_]
    resource.change.actions[_] in {"create", "update"}
    resource.change.after.tags != null
    existing_tags := {k | resource.change.after.tags[k]}
    missing := required_tags - existing_tags
    count(missing) > 0
    reason := sprintf("Resource '%v' is missing required tags: %v", [resource.address, missing])
}

deny[reason] {
    resource := input.resource_changes[_]
    resource.change.actions[_] in {"create", "update"}
    resource.change.after.tags == null
    reason := sprintf("Resource '%v' has no tags. Required: %v", [resource.address, required_tags])
}
```

### Example 7: Environment policy — check input values

```rego
package torque.environment

# Deny if an environment input has a disallowed value
# data.allowed_regions — list of allowed deployment regions

result = { "decision": "Denied", "reason": reason } if {
    # Find the "region" input
    region_input := input.inputs[_]
    region_input.name == "region"
    
    # Access value via value_v2 schema
    region_value := region_input.value_v2.value
    
    # Check if the selected region is allowed
    not region_value in data.allowed_regions
    
    reason := sprintf("Region '%v' is not allowed. Allowed regions: %v",
                      [region_value, data.allowed_regions])
}

result = { "decision": "Approved" } if {
    region_input := input.inputs[_]
    region_input.name == "region"
    region_input.value_v2.value in data.allowed_regions
}
```

---

## Step 8 — Restricted Rego Functions

These OPA built-ins are **not supported** in Torque policies:
- `http.send`
- `opa.runtime`
- `rego.parse_module`
- `time.now_ns`
- `trace`

Do **not** use these. All other OPA built-ins are supported.

---

## Step 9 — Best Practices

### Always do
- ✅ Start every policy with the correct package declaration (`torque.environment`, `torque.consumption`, or `torque.terraform_plan`)
- ✅ Include a default `Approved` rule in environment/consumption policies (or every path is evaluated)
- ✅ Use `data.*` for admin-configurable values instead of hardcoding thresholds
- ✅ Write descriptive `reason` strings that include the actual values (use `sprintf`)
- ✅ Comment what each `data.*` key means and its expected type
- ✅ Test logic at https://play.openpolicyagent.org/ before deploying
- ✅ Handle the `extend` action separately if extension rules differ from launch rules
- ✅ For terraform_plan policies, handle both `create` and `update` actions where appropriate

### Never do
- ❌ Don't use the restricted built-in functions listed above
- ❌ Don't hardcode email addresses, group names, or thresholds — use `data.*`
- ❌ Don't write a `torque.terraform_plan` policy without at least one `deny` rule
- ❌ Don't forget the `Approved` fallback in environment/consumption policies — without it, unmatched cases may not be handled correctly
- ❌ Don't reference `input.inputs[_].value` directly — input values use the `value_v2` schema; use `input.inputs[_].value_v2.value` instead
- ❌ Don't reference `input.inputs` in a `torque.consumption` policy — inputs aren't available at that trigger point
- ❌ Don't use `time.now_ns` — it's blocked by Torque

### Pattern: handling Launch vs Extend separately
```rego
package torque.environment

# On launch: limit requested duration
result = { "decision": "Denied", "reason": reason } if {
    input.action_identifier.action_type == "Launch"
    input.duration_minutes > data.max_launch_duration_minutes
    reason := sprintf("Launch duration %v min exceeds max of %v min",
                      [input.duration_minutes, data.max_launch_duration_minutes])
}

# On extend: limit the extension amount
result = { "decision": "Denied", "reason": reason } if {
    input.action_identifier.action_type == "Extend"
    input.extend_duration_minutes > data.max_extend_duration_minutes
    reason := sprintf("Extension of %v min exceeds max extension of %v min",
                      [input.extend_duration_minutes, data.max_extend_duration_minutes])
}

result = { "decision": "Approved" } if {
    input.action_identifier.action_type == "Launch"
    input.duration_minutes <= data.max_launch_duration_minutes
}

result = { "decision": "Approved" } if {
    input.action_identifier.action_type == "Extend"
    input.extend_duration_minutes <= data.max_extend_duration_minutes
}
```

---

## Step 10 — Output Format

Present the policy as:
1. The complete `.rego` file with proper package declaration and comments
2. A **data schema** section: list every `data.*` key the policy uses, its type, and example value
3. Instructions for adding to Torque:
   - Commit `.rego` file to a git repository
   - In Torque: Administration → Policy Repositories → Add Repository
   - Click "Discover Policies" → select this file → "Generate Policies"
   - Configure the data values and assign to spaces
   - Enable the policy
4. A note on which **policy type label** it will get in Torque (Terraform/Environment/Consumption/Approval)

---

## Reference Links

- Torque policy docs: https://docs.qtorque.io/governance/policies
- Torque built-in OPA examples: https://github.com/QualiTorque/opa
- OPA documentation: https://www.openpolicyagent.org/docs/latest/
- OPA playground (test your Rego): https://play.openpolicyagent.org/
- Approval channels: https://docs.qtorque.io/governance/approval-channels