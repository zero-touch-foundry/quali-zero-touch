---
name: torque-ready-terraform
description: "Use this skill whenever the user is writing, reviewing, or refactoring Terraform or OpenTofu code that will run inside Torque (Quali Torque) as a grain. Triggers include: mentions of 'Terraform', 'Torque', 'grain', 'blueprint', 'module', 'tf module', 'tofu', 'opentofu', or requests to make Terraform / OpenTofu code 'Torque-ready', 'Torque-compatible' or make it into a good 'building block'. Also trigger when the user asks about parameterizing Terraform / OpenTofu resources or assets for Torque, Terraform grain outputs, provider versioning for Torque, or converting existing Terraform to Torque assets. Use for reviewing existing Terraform code, converting living infrastructure configs to reusable Torque grains, parameterizing resources, defining outputs, or fixing provider version constraints."

---

# Making Terraform Torque-Ready

## The Core Difference: Living Config vs. Reusable Asset

Most Terraform code in the wild is a **living configuration** — it manages a single, ongoing deployment. A `terraform apply` updates the same state file, and values like an S3 bucket name or RDS instance identifier are hardcoded because they are expected to never change post deployment.

Torque treats Terraform differently. Each Terraform module is a **reusable asset** (grain) that:
- Can be launched **multiple times simultaneously**, each as part of a separate, isolated environment
- Receives all variable inputs from the blueprint or workflow at launch time
- Exposes selected outputs to downstream grains or blueprint consumers
- Is expected to be destroyed cleanly when the environment ends

A module that worked perfectly as a living config may **break** in Torque the moment a second environment is launched — because two environments cannot share some unique resource attribute values, such as a hardcoded S3 bucket name, IAM role name, or any other globally unique resource attribute.

---

## How Torque Executes a Terraform Grain

When a Torque environment launches a Terraform grain, the following happens:

1. **Source Fetch**: Torque clones the repo and checks out the path specified in the blueprint's `source` section.
2. **Variable Injection**: Torque writes all grain `inputs` as Terraform variables (via a generated `.tfvars.json` file).
3. **Init, Plan + Apply**: Torque runs `terraform init` followed by auto-scanning the tf module and adding auto tags, then `terraform plan`, and eventually `terraform apply --auto-approve` if the terraform plan adhered to the active OPA policies.
4. **Output Collection**: Torque reads the `terraform output -json` results and ingests the outputs as grain outputs based on Blueprint YAML definition, making them available to downstream grains.
5. **Destroy on Termination**: When the environment ends, Torque runs `terraform destroy -auto-approve` using the same variable inputs.

**Key insight**: A Torque-ready module is nothing more than a well-structured, fully-parameterized Terraform module. It does not require any Torque-specific code — only good parameterization discipline and clean output definitions.

---

## Greenfield projects — defer to `repo-conventions` for repo layout

This skill owns the **internal** structure of a Terraform module folder (`main.tf` / `variables.tf` / `outputs.tf` / `versions.tf` / `README.md`). It does NOT own **where in the repo** that folder lives.

If you are creating a Terraform module from scratch as part of building a new Torque project — i.e. there is no existing repo layout to follow — **invoke the `repo-conventions` skill FIRST** to lock in the canonical location (`terraform/<module-name>/` at repo root), then return here for the module's internal files.

Do NOT improvise paths like `blueprints/<blueprint-name>/terraform/` — that violates convention and hides reuse.

---

## The 8 Rules

Apply all 8 rules when writing or reviewing a Terraform module. Then use the checklist at the end to verify.

### Rule 1: Parameterize All Uniqueness-Constrained Attributes

Any resource attribute that must be globally or regionally unique **must** be a variable. Hardcoding these guarantees a collision the moment a second environment is launched.

**Common uniqueness-constrained attributes by provider:**

| Provider | Resource | Must-Parameterize Attributes |
|----------|----------|------------------------------|
| AWS | `aws_s3_bucket` | `bucket` |
| AWS | `aws_iam_role` / `aws_iam_policy` | `name` |
| AWS | `aws_db_instance` | `identifier` |
| AWS | `aws_elasticache_cluster` | `cluster_id` |
| AWS | `aws_lb` | `name` |
| Azure | `azurerm_resource_group` | `name` |
| Azure | `azurerm_storage_account` | `name` |
| GCP | `google_storage_bucket` | `name` |
| GCP | `google_sql_database_instance` | `name` |
| VMware vSphere | `vsphere_virtual_machine` | `name` |

**Pattern**: Use a `name_prefix` or `env_id` input and construct unique names from it:

```hcl
variable "env_id" {
  description = "Torque environment id, globally unique."
  type        = string
}

resource "aws_s3_bucket" "data" {
  bucket = "${var.env_id}-data"
}

resource "aws_iam_role" "app" {
  name = "${var.env_id}-app-role"
}

resource "aws_db_instance" "main" {
  identifier = "${var.env_id}-db"
  # ...
}
```

**Never do this** (breaks on second launch):

```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-company-data-bucket"   # hardcoded — will collide
}
```

### Rule 2: Parameterize Deployment-Variable Attributes

Beyond uniqueness, any attribute that is **likely to differ** between deployments should be a variable with a sensible default. This is what makes a grain properly reusable across different blueprints and teams.

**Strongly recommended parameterization (advisory):**

- Compute sizing: instance types, node counts, disk sizes
- Engine versions: RDS engine version, ElastiCache engine version, Kubernetes version
- Capacity: min/max autoscaling counts, read/write capacity units
- Feature flags: multi-AZ, deletion protection, encryption at rest
- Regions and environments (when not set at the provider level)

**Required parameterization (enforced):**

- Network placement: VPC ID, subnet IDs, availability zones
- Storage/resource containers: S3 bucket names, Azure storage account names, GCP bucket names, resource groups, projects
<!-- Note: VPC IDs are implied by subnet IDs; best practice is to use data sources to retrieve the VPC ID from subnet IDs when those are provided. -->

Hardcoding network or container attributes will cause collisions and must be parameterized unless the user explicitly acknowledges and requests to retain as intentional.

```hcl
variable "instance_type" {
  description = "EC2 instance type for the application server."
  type        = string
  default     = "t3.medium"
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "multi_az" {
  description = "Enable Multi-AZ for the RDS instance."
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "VPC to deploy resources into."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the deployment."
  type        = list(string)
}
```

### Rule 3: Avoid Over-Parameterization

Not everything should be a variable. Exposing every Terraform attribute as an input creates a module that is harder to use than writing Terraform directly. A grain should have a clear, bounded purpose, and its interface should reflect that.

**Do not parameterize:**

- Attributes that define the grain's core identity (e.g., if the grain *is* an EC2 instance, don't parameterize `ami_id` unless cross-region portability is an explicit goal)
- Implementation details that callers should not need to know about (e.g., ENI definitions, lifecycle rules, internal security group rule structures — unless the grain's explicit purpose is to manage those, like parameterizing port numbers for security purposes)
- Values that are fixed by the module's architecture (e.g., the protocol on an internal load balancer listener)
- Attributes for which there is one correct value for all reasonable use cases

**Heuristic**: If you cannot write a one-sentence explanation of *why a blueprint author would want to change this value*, it should not be a variable.

```hcl
# BAD: over-parameterized — no reasonable caller would vary these
variable "eni_device_index" { ... }
variable "eni_delete_on_termination" { ... }
variable "root_volume_delete_on_termination" { ... }
variable "iam_role_path" { ... }

# GOOD: these are genuinely caller-driven
variable "instance_type" { ... }
variable "vpc_id" { ... }
variable "env_id" { ... }
```

### Rule 4: Define Outputs for Consumer-Required Information

Outputs make a grain's results available to downstream grains and blueprint consumers. Define an output for every piece of information that a caller will realistically need to **use** what was deployed.

**Good output candidates:**

- Resource IDs and ARNs (for referencing in IAM policies, downstream grains)
- Endpoints and connection strings (DNS names, URLs, hostnames, ports)
- Names of created resources (when auto-generated or constructed or when names are identifiers)
- Security group IDs (needed by downstream compute grains)

```hcl
output "bucket_name" {
  description = "Name of the created S3 bucket."
  value       = aws_s3_bucket.data.id
}

output "db_endpoint" {
  description = "Connection endpoint for the RDS instance."
  value       = aws_db_instance.main.endpoint
}

output "db_port" {
  description = "Port the RDS instance is listening on."
  value       = aws_db_instance.main.port
}

output "app_security_group_id" {
  description = "Security group ID for the application tier."
  value       = aws_security_group.app.id
}
```

### Rule 5: Avoid Output Overuse

The inverse of Rule 4 also applies. Exporting every attribute of every resource clutters the grain interface and exposes implementation details that consumers should not depend on.

**Do not output:**

- Attributes that are derivable from inputs (e.g., don't output `region` if the caller passed it in) - unless explicitly requested to do so or keep
- Internal identifiers that no downstream system will reference
- Entire resource objects or complex nested structures - unless explicitly requested by the module creator
- Attributes that are only relevant during the apply phase (e.g., plan diffs, state metadata)

**Target**: An `outputs.tf` file with 3–8 outputs is a healthy sign. More than 15 outputs in a single-purpose grain is usually a sign of over-exposure.

```hcl
# BAD: outputs that no caller needs
output "bucket_hosted_zone_id" { ... }        # internal routing detail
output "bucket_region" { ... }                 # caller already knows this
output "iam_role_create_date" { ... }          # lifecycle metadata
output "db_resource_id" { ... }                # same as identifier, already output
```

**Cross-cloud example:** for Azure, do not output storage account endpoint metadata unless a downstream grain needs it; for GCP, avoid exporting raw complex objects such as `google_sql_database_instance` resources unless explicitly required.

### Rule 6: Use Current Provider Versions with Soft Pinning

Torque grains may be launched many times over months or years. Provider version constraints control what gets installed at each `terraform init`.

**Rules for provider versioning:**

- Use `~>` (pessimistic constraint) to allow patch/minor updates while preventing breaking major version changes
- Pin to the **current major version** of each provider (not an old one found in legacy code)
- Always specify a version constraint — an unconstrained provider will pull the latest at every init, which is unpredictable
- Check the Terraform Registry for the current latest version before writing the constraint

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"    # allows 5.x, blocks 6.x
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
```

**Never do this:**

```hcl
# BAD: no version constraint
provider "aws" {
  region = var.region
}

# BAD: over-pinned to an old version
aws = {
  version = "= 3.74.0"
}

# BAD: too broad
aws = {
  version = ">= 2.0"
}
```

### Rule 7: Keep Credentials and Secrets Out of Terraform Code

Terraform code and module source should never contain plain-text credentials, secret values, or API keys.

**Do:**
- Use variable references for secret inputs, not literal secrets.
- Mark secret variables with `sensitive = true`.
- Do not output secrets or credential values.
- Use Torque credential injection, environment-based auth, or provider-supported secret backends instead of hardcoding auth data.

**Do not:**
- Store AWS access keys, service account JSON, tokens, passwords, or client secrets in `.tf` or `.tfvars` files.
- Commit provider auth blocks that embed credentials into module source.

### Rule 8: Do Not Commit Terraform State or Secret-bearing Files

A Torque Terraform grain should treat state and secret inputs as runtime artifacts, not source artifacts.

**Do:**
- Keep `terraform.tfstate`, `terraform.tfstate.backup`, and `.terraform/` out of source control.
- Exclude secret-containing variable files such as `*.tfvars`, `*.tfvars.json`, or any file with sensitive values.
- Add `.gitignore` entries for state, logs, and generated credential files.

**Do not:**
- Commit state files, sensitive `.tfvars` files, or generated provider credential files to the repository.
- Add secret-bearing files to the grain source path used by Torque.

---

## Recommended Module File Structure

```
terraform/<grain-name>/
  main.tf           # Core resource definitions
  variables.tf      # All input variable declarations (with descriptions and defaults)
  outputs.tf        # All output declarations
  README.md         # Documents inputs, outputs, and example usage in Torque
  versions.tf       # Optional: terraform{} block with required_version and required_providers (instead of in start of main.tf)
  providers.tf      # Optional: separate provider definitions to this file (instead of in start of main.tf)
```

Avoid placing everything in a single `main.tf`. A caller reading the blueprint should be able to open `variables.tf` and `outputs.tf` to understand the grain's full interface without reading the implementation.

---

## Complete Torque-Ready Module Template

```hcl
# terraform/app-database/versions.tf

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

```hcl
# terraform/app-database/variables.tf

variable "env_id" {
  description = "Unique name for this environment. Used to namespace all resources."
  type        = string
}

variable "vpc_id" {
  description = "VPC to deploy the database into."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the DB subnet group."
  type        = list(string)
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "15.4"
}

variable "db_name" {
  description = "Name of the initial database to create."
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Master username for the database."
  type        = string
  default     = "dbadmin"
}

variable "db_password" {
  description = "Master password for the database."
  type        = string
  sensitive   = true
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment."
  type        = bool
  default     = false
}

variable "allocated_storage" {
  description = "Allocated storage in GB."
  type        = number
  default     = 20
}
```

```hcl
# terraform/app-database/main.tf

resource "aws_db_subnet_group" "main" {
  name       = "${var.env_id}-db-subnet-group"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  name   = "${var.env_id}-db-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "main" {
  identifier             = "${var.env_id}-db"
  engine                 = "postgres"
  engine_version         = var.db_engine_version
  instance_class         = var.db_instance_class
  allocated_storage      = var.allocated_storage
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  multi_az               = var.multi_az
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
}
```

```hcl
# terraform/app-database/outputs.tf

output "db_endpoint" {
  description = "Connection endpoint for the RDS instance (host:port)."
  value       = aws_db_instance.main.endpoint
}

output "db_host" {
  description = "Hostname of the RDS instance."
  value       = aws_db_instance.main.address
}

output "db_port" {
  description = "Port the RDS instance is listening on."
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "Name of the database."
  value       = aws_db_instance.main.db_name
}

output "db_security_group_id" {
  description = "Security group ID attached to the database (for ingress rules in compute grains)."
  value       = aws_security_group.db.id
}
```

---

## Pre-Commit Checklist

| # | Check | What to look for |
|---|-------|-----------------|
| 1 | No hardcoded unique names | Bucket names, IAM role/policy names, DB identifiers, cluster IDs all use `var.env_id` as a prefix |
| 2 | Deployment-variable attributes are parameterized | Instance types, sizes, engine versions, AZ counts have variables with defaults |
| 3 | No over-parameterization | ENI definitions, lifecycle rules, and internal implementation details are not variables |
| 4 | Outputs cover consumer needs | Endpoints, IDs, hostnames, and security group IDs are exported |
| 5 | No output overuse | Derivable values, internal metadata, and redundant attributes are not exported |
| 6 | Provider versions use `~>` | `versions.tf` uses pessimistic constraint on current major version |
| 7 | `required_version` set | Minimum Terraform version specified in `terraform {}` block |
| 8 | All variables have descriptions | `variables.tf` — every variable has a `description` |
| 9 | Sensitive variables marked | Passwords, tokens, and keys use `sensitive = true` |
| 10 | No secrets in source | Credentials or secret values are not hardcoded in `.tf`/`.tfvars` files |
| 11 | State and generated secret files are ignored | `terraform.tfstate`, `terraform.tfstate.backup`, `.terraform/`, and secret-bearing `*.tfvars` are not committed |
| 12 | Files are split correctly | `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` exist separately |
| 13 | README documents the interface | Inputs, outputs, and an example blueprint snippet are present |

---

## How to Review an Existing Module

When converting an existing Terraform module to be Torque-ready:

1. **Hunt for hardcoded unique names**: Search for string literals in `name`, `bucket`, `identifier`, `cluster_id`, and similar attributes. Replace each with `"${var.env_id}-<suffix>"`.
2. **Review resource sizing attributes**: Find `instance_type`, `instance_class`, `node_count`, `capacity`, `engine_version`. If they are hardcoded, extract them to variables with the current hardcoded value as the default.
3. **Apply the over-parameterization test**: For every existing variable, ask: "Would a blueprint author realistically need to change this?" If not, remove the variable and hardcode a sensible value.
4. **Audit `outputs.tf`**: For each output, confirm a downstream grain or blueprint consumer will need it. Remove outputs that expose internal details or are derivable from inputs.
5. **Check for missing outputs**: Look at every resource. Are its endpoint, ID, or name needed by any plausible downstream grain? If so, add the output.
6. **Inspect the provider block**: Update any outdated version constraints to the current major version with `~>`. Add a `versions.tf` file if one does not exist.
7. **Check for provider configuration in the module**: If the module configures `region`, `credentials`, or other provider settings inline, move those to variables or remove them — the provider should be configured by the caller (blueprint/workspace), not the grain module itself.

---

## Blueprint Reference (For Context Only)

Grain authors do not necessarily write blueprints, but understanding how a Terraform grain is consumed helps write better modules:

```yaml
grains:
  app_database:
    kind: terraform
    spec:
      source:
        store: my-repo
        path: terraform/app-database   # points to the module directory
      agent:
        name: '{{ .inputs.agent }}'
      inputs:     # must match variable names in variables.tf
        - env_id: '{{ .inputs.env_id }}'
        - vpc_id: '{{ .grains.networking.outputs.vpc_id }}'
        - subnet_ids: '{{ .grains.networking.outputs.private_subnet_ids }}'
        - db_instance_class: '{{ .inputs.db_size }}'
        - db_password: '{{ .inputs.db_password }}'
      outputs:    # must match output names in outputs.tf
        - db_endpoint         
        - db_host
        - db_port
        - db_name
        - db_security_group_id
    depends-on: networking
```

**What this means for the module author:**
- `inputs` keys map directly to Terraform variable names — variable names in `variables.tf` must match exactly
- `outputs` keys must exactly match the names declared in `outputs.tf`
- The module must not configure the provider — Torque's agent handles cloud credentials by adding environment variable authentication data
- The module directory (not a `.tf` file) is the source path
