---
name: env-status
description: Check a Torque environment's health and status
argument-hint: [environment-name]
---

Check the health and status of the Torque environment "$ARGUMENTS".

1. Use the Torque MCP to retrieve the environment's metadata: status, blueprint, grains, resources, and any active workflows.
2. For each grain, report its current state (active, deploying, failed, etc.).
3. If any grain is in a failed or degraded state, pull available logs or error details.
4. If Kubernetes tools are available, check pod status and resource utilization for the environment's namespace.
5. Summarize the overall health in a clear table: grain name, kind, status, and any issues.
6. If there are problems, suggest specific next steps to investigate or resolve them.

If no environment name is provided, use the Torque MCP to list available environments and ask the user which one to check.
