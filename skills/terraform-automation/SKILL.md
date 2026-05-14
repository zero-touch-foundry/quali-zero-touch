---
name: terraform-automation
description: >
  Use this skill when the user asks about "Terraform module", "Terraform state",
  "tfvars", "Terraform backend", "Terraform workspace", "Terraform provider",
  "Terraform plan", "Terraform apply", "Terraform import", "remote state",
  "state locking", "Terraform debugging", "HCL", "terraform init", or needs
  help writing, reviewing, or troubleshooting Terraform code. Also trigger when
  the user needs Terraform modules that integrate with Torque environments, AWS,
  or Kubernetes. For Torque-specific Terraform grain configuration, this skill
  complements the torque-blueprints skill.
version: 0.1.0
---

# Terraform Automation

Guide users through writing, reviewing, debugging, and structuring Terraform configurations — standalone or as Torque grains.

---

## Module Structure

A well-structured Terraform module contains:

```
my-module/
├── main.tf          # Core resources
├── variables.tf     # Input variable declarations
├── outputs.tf       # Output value declarations
├── versions.tf      # Required providers and Terraform version
├── locals.tf        # Local values (optional)
└── README.md        # Module documentation
```

Use child modules for reusable components. Keep root modules thin orchestrators that call child modules:

```hcl
module "vpc" {
  source  = "./modules/vpc"
  region  = var.region
  cidr    = var.vpc_cidr
}
```

---

## Variables and Outputs

### Variable best practices

- Always provide `description` and `type`. Use `default` only when a value is truly optional.
- Use `sensitive = true` for secrets; this prevents values appearing in plan output.
- Use `validation` blocks to catch bad inputs early:

```hcl
variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}
```

### Output best practices

- Mark outputs `sensitive = true` if they expose credentials or connection strings.
- Use `description` on every output so callers know what they're getting.
- Expose only what downstream consumers actually need — don't output internal IDs that have no external use.

---

## Providers

Declare providers in `versions.tf` with version constraints:

```hcl
terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}
```

For **multi-account / multi-region** deployments, use provider aliases:

```hcl
provider "aws" {
  alias  = "us_east"
  region = "us-east-1"
}

provider "aws" {
  alias  = "eu_west"
  region = "eu-west-1"
}

resource "aws_s3_bucket" "eu_bucket" {
  provider = aws.eu_west
  bucket   = "my-eu-bucket"
}
```

When used as a **Torque grain**, use `provider-overrides` in the blueprint instead of hardcoding provider values — this allows Torque to inject the correct account credentials at runtime. Refer to the torque-blueprints skill for the `provider-overrides` syntax.

---

## State Management

### Remote backends

Always use a remote backend in shared or production environments. S3 with DynamoDB locking is the standard for AWS workloads:

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "envs/prod/network/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

Key guidelines:
- Use a unique `key` path per environment and component to avoid state collisions.
- Enable `encrypt = true` on S3 backends; use KMS for stricter compliance.
- The DynamoDB table must have `LockID` as its partition key (type `S`).
- Never store the backend bucket itself in Terraform state — bootstrap it separately.

### Torque + remote state

When running as a Torque grain, configure the backend via the grain's `backend` block in the blueprint YAML instead of hardcoding it in `versions.tf`. This lets Torque manage state isolation per environment. See the torque-blueprints skill for the full `backend` block syntax.

### Partial backend configuration (`-backend-config`)

For secrets (access keys, tokens) that shouldn't live in source control, use partial config:

```hcl
# In versions.tf — omit sensitive values
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}
```

Then pass the secret at init time:

```bash
terraform init -backend-config="dynamodb_table=my-lock-table" \
               -backend-config="access_key=$TF_VAR_access_key"
```

---

## Workspaces

Workspaces create isolated state files within the same backend — useful for ephemeral environments or per-developer sandboxes:

```bash
terraform workspace new staging
terraform workspace select staging
terraform plan
```

Reference the current workspace in HCL:

```hcl
locals {
  env = terraform.workspace  # "staging", "prod", etc.
}

resource "aws_s3_bucket" "data" {
  bucket = "myapp-${local.env}-data"
}
```

**Limitation**: Workspaces share the same code and provider config. For strong environment isolation (different accounts, regions, or backends), prefer separate root module directories over workspaces.

---

## Resource Dependencies and `depends_on`

Terraform infers dependencies from references automatically. Only use explicit `depends_on` when a dependency exists that Terraform cannot detect (e.g., a resource relies on a side-effect, not an attribute):

```hcl
resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.worker_policy.arn
  # No explicit depends_on needed — Terraform infers from references
}

resource "aws_instance" "app" {
  # Explicit depends_on because app startup relies on the policy being
  # in effect, not on any attribute the policy exposes
  depends_on = [aws_iam_role_policy_attachment.attach]
}
```

---

## Importing Existing Infrastructure

Import resources that were created outside Terraform:

```bash
terraform import aws_vpc.main vpc-0abc123def456
```

For bulk imports (Terraform ≥ 1.5), use an `import` block:

```hcl
import {
  to = aws_vpc.main
  id = "vpc-0abc123def456"
}
```

After import, run `terraform plan` to confirm the imported state matches actual configuration. Reconcile any diffs before committing.

---

## Lifecycle Rules

```hcl
resource "aws_db_instance" "primary" {
  # ...

  lifecycle {
    prevent_destroy       = true   # Block accidental deletion
    create_before_destroy = true   # Zero-downtime replacement
    ignore_changes        = [tags] # Ignore drift on specific attributes
  }
}
```

Use `prevent_destroy = true` on stateful resources (databases, S3 buckets) in production.

---

## For_each and Count

Prefer `for_each` over `count` for collections of distinct resources — it produces stable resource addresses when items are added or removed:

```hcl
variable "buckets" {
  type    = set(string)
  default = ["logs", "backups", "artifacts"]
}

resource "aws_s3_bucket" "store" {
  for_each = var.buckets
  bucket   = "myapp-${each.key}"
}
```

With `count`, removing an element from the middle renumbers all subsequent indices and can trigger unwanted replacements.

---

## Debugging and Troubleshooting

### Logging

```bash
TF_LOG=DEBUG terraform plan      # Verbose provider/API logs
TF_LOG=JSON terraform apply      # Structured JSON output
TF_LOG_PATH=./tf.log terraform plan   # Write logs to file
```

Log levels (least to most verbose): `ERROR`, `WARN`, `INFO`, `DEBUG`, `TRACE`.

### Common errors and fixes

| Error | Likely cause | Fix |
|---|---|---|
| `Error acquiring the state lock` | Previous run crashed; lock not released | Run `terraform force-unlock <LOCK_ID>` |
| `Provider produced inconsistent result` | Provider bug or race condition | Run `terraform apply` again; upgrade provider |
| `Error: Reference to undeclared resource` | Typo in resource name or wrong module path | Check the resource address in `terraform state list` |
| `Backend configuration changed` | Backend block edited without `terraform init` | Run `terraform init -reconfigure` |
| `Cycle in dependency graph` | Circular reference between resources | Use `terraform graph` to visualize and break the cycle |

### Useful diagnostic commands

```bash
terraform validate          # Check HCL syntax
terraform fmt -check        # Verify formatting without changing files
terraform state list        # List all resources in state
terraform state show aws_vpc.main   # Inspect a specific resource's state
terraform graph | dot -Tsvg > graph.svg   # Visualize dependencies
terraform refresh           # Sync state with real infrastructure (use sparingly)
```

---

## Security Best Practices

- Never commit `.tfstate`, `.tfvars` containing secrets, or `*.tfplan` files to source control. Add them to `.gitignore`.
- Use `sensitive = true` on variables and outputs that contain credentials.
- Prefer IAM roles and instance profiles over hardcoded AWS access keys.
- Store secrets in AWS Secrets Manager or Parameter Store; reference them via data sources rather than tfvars.
- Pin provider versions with `~>` constraints to avoid breaking changes from unexpected upgrades.
- Run `terraform plan` in CI before every `apply` and require review of the plan output.

---

## Torque Integration

When Terraform code will run as a Torque grain:

1. **Source location**: Store module code in a Git repository connected to Torque. The grain's `source.store` and `source.path` point to the module folder.
2. **Inputs**: Torque passes grain inputs as Terraform variables automatically. Name them to match your `variable` declarations.
3. **Outputs**: Declare `outputs` in the grain spec; Torque reads them from `terraform output` after `apply`.
4. **Backend**: Configure the `backend` block in the blueprint grain spec — don't hardcode it in the module. This gives each Torque environment its own isolated state file.
5. **Authentication**: Use the grain's `authentication` field to reference Torque credentials (IAM roles, cloud credentials) rather than environment variables.
6. **Lifecycle hooks**: Use `scripts` (`pre-tf-init`, `post-tf-plan`, `pre-tf-destroy`) for custom logic like downloading modules, validating plans with OPA, or sending notifications.
7. **Tagging**: Enable `tags.auto-tag: true` to let Torque automatically tag all AWS resources with environment metadata.

For the full grain YAML syntax, refer to the torque-blueprints skill and `references/grain-types.md`.
