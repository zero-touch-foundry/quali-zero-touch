---
name: aws-best-practices
description: >
  Use this skill when the user asks about "AWS architecture", "AWS IAM policy",
  "cost optimization", "AWS security", "cloud best practices", "Well-Architected",
  "EC2 sizing", "S3 configuration", "AWS VPC design", "security groups", or needs
  guidance on AWS infrastructure design, security hardening, cost management,
  or operational excellence. Also trigger for AWS-related Torque grain
  configuration (Terraform, CloudFormation, CDK grains targeting AWS).
version: 0.1.0
---

# AWS Best Practices

Provide guidance on AWS architecture, security, cost optimization, and operational patterns relevant to deployment and operation of AWS infrastructure in Quali Torque.

## Architecture Principles

Follow the AWS Well-Architected Framework pillars:

1. **Operational Excellence** — Automate operations, make frequent small reversible changes, anticipate failure.
2. **Security** — Apply security at all layers, enable traceability, automate security best practices.
3. **Reliability** — Automatically recover from failure, scale horizontally, stop guessing capacity.
4. **Performance Efficiency** — Use serverless where appropriate, experiment more often, consider mechanical sympathy.
5. **Cost Optimization** — Adopt a consumption model, measure efficiency, stop spending on undifferentiated heavy lifting.
6. **Sustainability** — Understand your impact, establish sustainability goals, maximize utilization.

## IAM Best Practices

- Apply least-privilege access — grant only permissions required for the task.
- Use IAM roles instead of long-lived access keys.
- Enable MFA for all human users.
- Use AWS Organizations SCPs for guardrails across accounts.
- Rotate credentials regularly; prefer temporary credentials via STS.
- Use policy conditions to restrict access by MFA status, tags, resource scopes, etc'.
- Separate workloads into different AWS accounts (dev, staging, prod).

## Networking & VPC Design

- Prefer private subnets for databases and backend services.
- Warn against placing anything in public subnets except for load balancers and bastion hosts.
- Use VPC endpoints for AWS service access from network-isolated environments.
- Implement security groups as allowlists (no deny rules).
- Use NACLs for subnet-level defense in depth for high security environments.
- Design multi-AZ architectures for high availability.
- Use Transit Gateway for multi-VPC and multi-account connectivity.

## Cost Optimization

- Right-size instances based on actual utilization (use AWS Compute Optimizer).
- Use Savings Plans or Reserved Instances for steady-state workloads.
- Leverage Spot Instances for fault-tolerant batch workloads.
- Enable S3 Intelligent-Tiering for unpredictable access patterns.
- Set up AWS Budgets and Cost Anomaly Detection alerts.
- Delete unused resources: unattached EBS volumes (When not controlled by EKS storage class), old snapshots, idle load balancers.
- Use Graviton instances for better price-performance.

## Security Hardening

- Enable CloudTrail in all regions.
- Enable GuardDuty for threat detection.
- Use AWS Config for compliance monitoring.
- Encrypt data at rest (KMS) and in transit (TLS).
- Enable VPC Flow Logs for network monitoring.
- Use AWS Secrets Manager or Parameter Store for credentials.
- Implement AWS WAF for web application protection.

## Torque + AWS Integration

When configuring Torque grains for AWS:

- Use OIDC or IAM roles for Torque agent authentication (strongly recommend/prefer OIDC).
- Configure remote Terraform backends in S3 with DynamoDB locking.
- Use provider overrides to inject provider block where target cloud account details cannot be parameterized to a pattern.
- Tag all resources through Torque's auto-tagging for cost collection & budgeting.
- In high security environments, place Torque agents in private subnets with VPC endpoints for security.

For detailed grain configuration, refer to the author-blueprint skill.
