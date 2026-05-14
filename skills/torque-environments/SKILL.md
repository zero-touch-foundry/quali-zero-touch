---
name: torque-environments
description: >
  Use this skill when the user asks to "check my environment", "environment status",
  "troubleshoot environment", "debug environment", "environment health", "launch environment",
  "extend environment", "end environment", or needs help managing Torque environments,
  investigating resource issues, running workflows, or performing environment operations
  via the Torque MCP.
version: 0.1.0
---

# Torque Environment Management

Guide users through managing, monitoring, and troubleshooting Torque-managed cloud environments using the Torque MCP and complementary tools.

## Core Concepts

- **Torque Environment**: A managed cloud environment containing multiple applications and resources, launched from a blueprint.
- **Blueprint**: The YAML template defining an environment's configuration.
- **MCP (Management Control Plane)**: The Torque API for querying state, managing resources, and running workflows.
- **Grains**: Individual infrastructure components within an environment.

## Information Gathering Strategy

Combine all available sources when answering environment questions:

1. Use Torque MCP tools to query environment state, resources, and metadata.
2. Cross-reference with blueprint files if available in the workspace.
3. Use complementary MCP tools (Kubernetes, AWS) for deeper resource inspection.
4. If data is incomplete, ask the user to specify the environment ID or name.

## Environment Operations

### Get environment info

Retrieve via Torque MCP: name, status, blueprint, cluster, resource allocation, applications, services, and versions. Provide a resource allocation summary (CPU, memory, storage). Reference the underlying blueprint to confirm expected vs. actual configuration.

### Check environment health

1. Query the environment status via Torque MCP.
2. Use Kubernetes MCP or `kubectl` to check pod status and retrieve logs for problematic elements.
3. Summarize health metrics: uptime, service status, error logs, resource utilization.
4. Identify failed or degraded components and suggest next steps.

### Launch and manage environments

Use Torque MCP to launch, extend, or end environments. Always confirm destructive actions (ending an environment) with the user before proceeding.

### Run workflows

Execute Torque workflows for maintenance, updates, or custom operations. Suggest relevant workflows when multiple options exist.

### Port forwarding

1. Identify the target application and ports from environment details.
2. Use Kubernetes tools to establish port forwarding.
3. Verify user permissions and prerequisites.
4. Provide clear commands for safe port access.

## Troubleshooting Workflow

When a user reports a problem:

1. Gather context — environment name/ID, symptoms, recent changes.
2. Query environment status and grain states via Torque MCP.
3. Pull logs from affected components using Kubernetes or cloud provider tools.
4. Identify bottlenecks, failures, or misconfigurations.
5. Recommend specific fixes — configuration adjustments, resource scaling, service restarts.
6. If root cause is unclear, propose a stepwise diagnostic plan.

## Response Guidelines

- Provide clear, step-by-step guidance.
- Suggest executable commands or MCP actions.
- Include warnings for sensitive operations (resource changes, environment termination).
- When multiple solutions exist, present options and let the user choose.
