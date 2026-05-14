# Torque MCP Usage Guide

Reference for how to interact with Torque environments via the Management Control Plane.

## Available MCP Tools

The Torque MCP provides tools for:

- Querying environment state and metadata
- Listing applications, services, and resources
- Running workflows and remote actions
- Getting grain usage examples for blueprint authoring
- Retrieving blueprint YAML from the repository

## Key Tools

### get_grain_usage_examples

Find example usages of a grain type across blueprints. Use the grain's `kind` value and the current space (from `get_current_torque_space`).

When a user selects a grain and asks to connect it to another resource:
1. Search for examples of the **selected grain** (not the target resource).
2. Use the grain's `kind` property as the search parameter.
3. If results are found, use `get_blueprint_yaml` to see the full connection pattern.

### get_blueprint_yaml

Retrieve the full YAML of a blueprint. Use the current branch as the `branch` parameter.

### get_current_torque_space

Determine which Torque space is active. Pass this to other tools that require a space parameter.

## Cross-Tool Strategy

Combine Torque MCP with other available tools:

- **Kubernetes MCP**: Pod status, logs, resource utilization, port forwarding
- **AWS tools**: Cloud resource details, IAM, networking
- **Git tools**: Blueprint source files, change history

When troubleshooting, always check pod status and retrieve logs for problematic elements as a baseline step.
