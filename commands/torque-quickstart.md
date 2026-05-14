---
description: First-time Torque user walkthrough — authenticate, explore catalog, launch first env, debug
---

Guide a new Torque user from zero to a launched environment. Adapt to their experience level by asking before assuming.

## Phase 1 — Setup check

1. Confirm `TORQUE_API_TOKEN` is set. If missing, point them to the README's Authentication section and stop.
2. Use `get_spaces` via the Torque MCP to confirm connectivity. If it fails, troubleshoot:
   - Token expired? → regenerate at https://portal.qtorque.io
   - Wrong URL? → verify `.mcp.json`
   - Network? → check VPN / corporate proxy.
3. List the spaces the user has access to. Ask which to work in.

## Phase 2 — Orient

Ask what the user wants to do:

- **A. Launch something that already exists** → Phase 3A
- **B. Author my first blueprint** → Phase 3B
- **C. Debug a failing environment** → Phase 3C
- **D. Just explore** → walk through one item from each.

## Phase 3A — Launch from catalog

1. Run `get_catalog_items` for the chosen space.
2. Show a short list (name + description + required inputs count).
3. Pick one with the user. Use `/launch-env <name>` for the rest of the flow.
4. After launch, suggest `/env-status` to follow progress.

## Phase 3B — First blueprint

1. Ask the simplest possible goal: "What's one thing you want to deploy?" (e.g., S3 bucket, EKS cluster, Helm chart).
2. Confirm whether IaC already exists for it (Terraform module, Helm chart, etc.). If yes, invoke `/blueprint-from-asset <path>`. If no, invoke `torque-blueprint` skill to scaffold from scratch.
3. Run `/deploy-check` on the result.
4. Optionally launch with `/launch-env`.

## Phase 3C — Debug

1. Ask for the environment URL (encodes space + env ID).
2. Hand off to `torque-debug-env` skill — it fetches live state, grain status, activity feed.

## Phase 4 — Next steps

After the first task, surface 2–3 follow-ups:
- `/catalog` to discover more blueprints.
- `torque-workflow` skill for day-2 ops.
- `torque-rego` skill for governance.
- `torque-cost-analysis` for spend visibility.

Keep it short. The goal is **one** successful task, not an exhaustive tour.
