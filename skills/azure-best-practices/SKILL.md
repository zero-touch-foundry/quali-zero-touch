---
name: azure-best-practices
description: >
  Use this skill when the user asks about "Azure architecture", "Azure RBAC",
  "Azure cost optimization", "Azure security", "cloud best practices", "Well-Architected Azure deployment",
  "VM sizing", "Blob Storage configuration", "Azure VNet design", "Azure NSG rules", or needs
  guidance on Azure infrastructure design, security hardening, cost management,
  or operational excellence. Also trigger for Azure-related Torque grain
  configuration and development (Terraform, ARM, Ansible grains targeting Azure).
version: 0.1.0
---

# Azure Best Practices

Provide guidance on Azure architecture, security, cost optimization, and operational patterns relevant to deployment and operation of Azure infrastructure in Quali Torque.

## Architecture Principles

Follow the Azure Well-Architected Framework pillars:

1. **Reliability** — Design for failure, use availability zones, implement retry and circuit-breaker patterns.
2. **Security** — Apply zero-trust principles, encrypt everything, use managed identities over credentials.
3. **Cost Optimization** — Right-size resources, use reservations for steady state, leverage autoscaling to avoid over-provisioning.
4. **Operational Excellence** — Automate deployments via IaC, use Azure Monitor and alerts, define runbooks.
5. **Performance Efficiency** — Choose the right service tier, scale horizontally, profile before optimizing.
6. **Sustainability** — Maximize utilization, use autoscale and auto-shutdown, prefer PaaS/serverless over IaaS where possible.

## Identity & Access Management

- Use **Managed Identities** instead of service principals with client secrets wherever possible.
- Apply **least-privilege RBAC** — assign the narrowest built-in role that covers the task; create custom roles only when necessary.
- Scope role assignments to the **lowest resource scope** (resource > resource group > subscription > management group).
- Use **Azure Entra ID (formerly Azure AD)** Conditional Access policies and MFA for all human users.
- Use **Privileged Identity Management (PIM)** for just-in-time elevation of privileged roles.
- Use **Azure Policy** to enforce allowed role assignments and prevent standing privileged access.
- Separate workloads across **management groups and subscriptions** (dev, staging, prod) with Azure Policy guardrails at each level.
- Prefer **Workload Identity Federation** (OIDC) for CI/CD and external automation over long-lived client secrets.

## Networking & VNet Design

- Place databases and backend services in **private subnets**; expose only load balancers and application gateways to the internet.
- Use **Network Security Groups (NSGs)** as allowlists on both subnets and NICs; deny-all inbound as the default rule.
- Use **Application Security Groups (ASGs)** to group workloads logically and simplify NSG rule maintenance.
- Use **Azure Private Endpoints** for PaaS service access (Storage, Key Vault, SQL, etc.) from VNet-isolated environments; disable public network access on those services.
- Use **Azure Firewall** or a third-party NVA for centralized east-west and outbound traffic inspection in high-security environments.
- Use **Azure DDoS Protection** (Standard tier) for internet-facing applications.
- Design **multi-region or multi-availability-zone** architectures for high availability; use zone-redundant SKUs where available.
- Use **Azure Virtual WAN** or **VNet Peering + hub-spoke topology** for multi-VNet and multi-subscription connectivity.

## Cost Optimization

- Right-size VMs based on actual CPU/memory utilization using **Azure Advisor** recommendations.
- Purchase **Azure Reserved Instances** or **Azure Savings Plans** for steady-state compute workloads (1- or 3-year terms).
- Use **Azure Spot VMs** for interruptible batch and dev/test workloads.
- Enable **Azure Blob Storage lifecycle management** policies to tier or delete data automatically.
- Set up **Azure Budgets** and **Cost Management alerts** on subscriptions and resource groups.
- Delete unused resources: unattached managed disks, idle public IPs, empty load balancers, orphaned snapshots.
- Use **Arm-based (Ampere Altra) VM SKUs** (e.g., `Dpsv5` series) for better price-to-performance on general workloads.
- Enable **auto-shutdown** on non-production VMs and AKS node pools.

## Security Hardening

- Enable **Microsoft Defender for Cloud** (at least the free tier) on all subscriptions; enable Defender plans for services handling sensitive data.
- Enable **Azure Monitor Activity Logs** and route them to a Log Analytics workspace or storage account for retention.
- Enable **Diagnostic Settings** on all key resources (Key Vault, NSGs, Firewall, AKS) to capture audit and performance logs.
- Encrypt data at rest using **Azure Key Vault**-managed keys (CMK) for sensitive workloads; use platform-managed keys as a minimum.
- Enforce **TLS 1.2+** for all data in transit; disable legacy protocols on storage accounts and databases.
- Store all secrets, certificates, and keys in **Azure Key Vault**, **Torque Credentials** or **Torque Sensitive Parameters**; never commit them to source control or pass as plain-text parameters.
- Apply **Azure Policy** initiatives (e.g., Azure Security Benchmark) to enforce compliance baselines across subscriptions.
- Use **Azure Web Application Firewall (WAF)** on Application Gateway or Azure Front Door for internet-facing web applications.
- Enable **Microsoft Entra ID sign-in logs** and alert on suspicious authentication events.

## Torque + Azure Integration

When configuring Torque grains for Azure:

- Use **Workload Identity Federation** (OIDC) for Torque agent authentication to Azure — this is the strongly preferred method over client secrets or certificates.
- When high security is required, configure remote Terraform backends using **Azure Blob Storage** with a dedicated storage account; Blob Storage provides native lease-based state locking — no separate locking resource is needed.
- Use **provider overrides** in Terraform grains to inject the `azurerm` provider block where subscription/tenant IDs cannot be parameterized to a pattern.
- Tag all resources through Torque's **auto-tagging** for cost collection and to maximize use of tag based budgeting; define a tagging policy in Azure Policy to enforce tag presence.
- Use **Managed Identities** on the Torque agent VM/AKS node pool as the authentication identity when Workload Identity Federation is not available.

For detailed grain configuration, refer to the torque-blueprint skill.
