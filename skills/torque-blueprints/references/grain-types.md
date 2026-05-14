# Grain Type Reference

Detailed configuration for each Torque grain type.

## Terraform Grain

Kind: `terraform`

Pre-installed tools: dotnet, terraform, git, python3, pip3, jq, docker-compose, curl, hcl2json, awscli, kubectl, helm, opa.

### Key properties

- **authentication**: reference credentials by name or input
- **provider-overrides**: inject custom provider blocks dynamically for multi-account deployments
- **backend**: remote state storage — supports S3, GCS, Azure RM, HTTP, Remote, Cloud backends
- **version**: supports Terraform 0.14 through 1.5.5
- **tfvars**: source variable files from repositories
- **tags**: auto-tagging with system and custom tags; disable with `auto-tag: false`
- **scripts**: hooks at `pre-tf-init`, `post-tf-plan`, `pre-tf-destroy`; access `TORQUE_TF_PLAN_JSON_PATH`
- **auto-approve**: defaults true; set false for manual approval on critical changes
- **targets**: selective resource/module deployment
- **termination-mode**: `managed` (destroys resources) or `no-termination` (preserves infrastructure)

### Example

```yaml
grains:
  vpc:
    kind: terraform
    spec:
      source:
        store: my-repo
        path: terraform/vpc
      agent:
        name: my-agent
      authentication:
        - credential-name
      inputs:
        - region: '{{ .inputs.aws_region }}'
        - cidr_block: '10.0.0.0/16'
      outputs:
        - vpc_id
        - subnet_ids
      backend:
        type: s3
        bucket: my-tf-state
        region: us-east-1
      env-vars:
        - TF_LOG: DEBUG
      tags:
        auto-tag: true
```

## Helm Grain

Kind: `helm`

Pre-installed: dotnet, curl, tar, unzip, kubectl, kustomize, helm, awscli.

### Key properties

- **target-namespace**: must exist; cannot match Torque agent namespaces
- **values-files**: multiple values.yaml from different repos
- **post-helm-install**: scripts to generate outputs via exported env vars
- **commands**: prerequisite CLI operations (e.g., `helm dependency update`)
- **command-arguments**: flags for `helm upgrade` (e.g., `--create-namespace`)

### Example

```yaml
grains:
  my-app:
    kind: helm
    spec:
      source:
        store: my-repo
        path: helm/my-app
      agent:
        name: my-agent
      target-namespace: production
      inputs:
        - replicaCount: '{{ .inputs.replicas }}'
        - image.tag: '{{ .inputs.app_version }}'
      commands:
        - dep-update: |
            helm dependency update ./
      post-helm-install:
        - get-endpoint: |
            export ENDPOINT=$(kubectl get svc my-app -n production -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
      outputs:
        - ENDPOINT
```

## Kubernetes Grain

Kind: `kubernetes`

Pre-installed: dotnet, curl, kubectl, jq.

### Key properties

- **target-namespace**: must exist; no concurrent environments from same blueprint on same namespace
- **source**: single manifest file or directory of manifests
- **scripts**: post-deployment scripts to extract resource info and generate outputs

### Example

```yaml
grains:
  manifests:
    kind: kubernetes
    spec:
      source:
        store: my-repo
        path: k8s/manifests
      agent:
        name: my-agent
      target-namespace: staging
      scripts:
        post-kubernetes-install:
          - get-info: |
              export SVC_IP=$(kubectl get svc my-svc -n staging -o jsonpath='{.spec.clusterIP}')
      outputs:
        - SVC_IP
```

## Ansible Grain

Kind: `ansible`

Pre-installed: dotnet, git, python3, pip3, ansible, openssh-client.

### Key properties

- **inventory-file**: dynamic YAML inventory with hosts and group variables
- **command-arguments**: extra flags (vault passwords, tags)
- **scripts**: pre-playbook execution scripts
- **on-destroy**: cleanup playbook for teardown
- **outputs**: use `export-torque-outputs` module to extract results

Inputs are provided as extra-vars, auto-serialized to `/var/run/ansible/inputs/inputs.json`.

Auto-installs requirements from `requirements.yaml` or `requirements.yml` in module root.

### Example

```yaml
grains:
  configure:
    kind: ansible
    depends-on: infra
    spec:
      source:
        store: my-repo
        path: ansible/configure
      agent:
        name: my-agent
      inputs:
        - db_host: '{{ .grains.infra.outputs.db_endpoint }}'
      inventory-file:
        all:
          hosts:
            target:
              ansible_host: '{{ .grains.infra.outputs.instance_ip }}'
              ansible_user: ubuntu
      outputs:
        - app_url
      on-destroy:
        source:
          store: my-repo
          path: ansible/teardown
```

## Shell Grain

Kind: `shell`

Pre-installed: dotnet, python3, pip, curl, wget, jq, git, zip/unzip, kubectl, awscli.

### Key properties

- **activities**: `deploy` (required, even if empty) and `destroy`
- **files**: external scripts from repos
- **commands**: inline bash/python3; each command runs in its own shell
- **outputs**: export env vars matching declared output names

Shell grain outputs use a different reference path: `{{ .grains.grainName.activities.deploy.commands.commandName.outputs.outputName }}`.

### Example

```yaml
grains:
  setup:
    kind: shell
    spec:
      agent:
        name: my-agent
      activities:
        deploy:
          commands:
            - init: |
                export RESULT="environment ready"
        destroy:
          commands:
            - cleanup: |
                echo "cleaning up resources"
      outputs:
        - RESULT
```

## CloudFormation Grain

Kind: `cloudformation`

### Key properties

- **region**: required — AWS region for stack creation
- **authentication**: credentials or service account with AWS role
- **template-storage**: S3 bucket for templates > 50KB or nested stacks
- **stack-name-prefix**: custom naming conventions
- **tags**: auto-tagging with custom additions

Required IAM permissions: S3 (PutObject, GetObject, DeleteObject), CloudFormation (CreateStack, DeleteStack, UpdateStack, DescribeStacks, DescribeStackEvents), plus permissions for template resources.

### Example

```yaml
grains:
  network:
    kind: cloudformation
    spec:
      source:
        store: my-repo
        path: cfn/network.yaml
      agent:
        name: my-agent
      region: '{{ .inputs.aws_region }}'
      authentication:
        - aws-creds
      inputs:
        - VpcCidr: '10.0.0.0/16'
      outputs:
        - VpcId
        - SubnetId
```

## Other Grain Types

**ArgoCD** (`argocd`): GitOps-based continuous delivery grain.
**Blueprint** (`blueprint`): Nested blueprint as a grain for composition.
**CDK** (`cdk`): AWS CDK infrastructure grain.
**OpenTofu** (`opentofu`): Open-source Terraform alternative grain.
**Terragrunt** (`terragrunt`): Terraform wrapper for DRY configurations.
**CloudShell** (`cloudshell`): Quali CloudShell integration grain.
**Custom** (`custom`): User-defined grain type for specialized tooling.
