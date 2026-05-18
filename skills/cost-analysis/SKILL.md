---
name: cost-analysis
description: >
  Use this skill whenever the user wants to estimate, analyze, or optimize the cost of a Torque
  environment or blueprint. Triggers include: "how much does this environment cost",
  "estimate cost of my blueprint", "is this environment over-provisioned", "right-size my Torque environment",
  "cost of grains", "expensive grain", "reduce Torque environment cost", "cheaper instance type for Torque",
  "cost optimization for Torque blueprint", "estimate AWS spend for this blueprint", "cost analysis Torque",
  "Torque environment too expensive", "compare cost of two blueprints". Also trigger when the user asks about
  Torque environment cost reporting, budget alerts, or selecting cost-efficient grain configurations.
  Always use this skill — do NOT estimate Torque costs from memory alone; fetch live environment / blueprint
  data and ground estimates in current cloud pricing where possible.
---

# Torque Cost Analysis

Estimate and optimize the cost of Torque environments and blueprints. Pair with `aws-best-practices` for
cloud-side guidance and `torque-blueprint` for YAML-level changes.

**Before running any Torque API helper script, read `${CLAUDE_PLUGIN_ROOT}/skills/torque-api/SKILL.md` (its script manifest is authoritative — never guess script names from patterns) and run the chosen script with `--help` to see its actual arg names.**

---

## Step 1 — Determine the target

Ask the user which they want analyzed:

1. **A running environment** — need environment URL or ID + API token.
2. **A blueprint YAML** — file path or content in the conversation.
3. **A comparison** — two blueprints, or current vs proposed config.

If unclear, ask before proceeding.

---

## Step 2 — Gather data

### For a running environment

Fetch full env details:
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_environment.py" \
  --space <SPACE> --id <ENV_ID>
```
From the parsed JSON extract:
- `grains[]` — kind, status, inputs, outputs (for resource counts: instance counts, disk sizes, replicas).
- `labels` — for cost allocation.
- `start_time`, `end_time` — duration so far and scheduled end.

For a blueprint (not yet launched), fetch its YAML with `get_blueprint_yaml.py` and parse declared grain inputs / defaults instead.

### For a blueprint YAML

Parse the blueprint and extract per-grain:
- Resource sizing inputs: instance types, disk sizes, replica counts, machine sizes.
- Provider regions (regional price differences matter).
- Helm chart values that affect resource requests/limits.
- Shell grain commands that provision resources outside Terraform/Helm visibility — flag these as "unknown cost surface".

---

## Step 3 — Estimate cost

Use these heuristics, ordered by accuracy:

1. **Terraform plan output** — if a `terraform plan` JSON is available (Torque scripts hook `post-tf-plan` writes it), parse `resource_changes` for full resource list. Most accurate.
2. **Resource inputs in the grain spec** — read declared instance types / disk sizes / replicas, look up current on-demand pricing.
3. **Defaults from the module / chart** — when inputs are not overridden, assume module defaults. Note this assumption explicitly.

For each priced item, fetch current pricing — do not rely on memory:

| Provider | Pricing source |
|---|---|
| AWS | https://aws.amazon.com/ec2/pricing/on-demand/ + https://aws.amazon.com/rds/pricing/ |
| Azure | https://azure.microsoft.com/en-us/pricing/calculator/ |
| GCP | https://cloud.google.com/products/calculator |

Convert all prices to per-hour and per-month (730h) for comparison.

---

## Step 4 — Present the analysis

Format the output as:

```
ENV: <name>  blueprint: <bp>  region: <region>  duration: <hours>

Grain          Kind        Resources                  Est. $/hr   $/month
--------------------------------------------------------------------------
<grain-1>      terraform   2× t3.large EC2            $0.166      $121
<grain-2>      helm        3× pods (1 CPU, 2Gi mem)   shared      —
<grain-3>      terraform   db.t3.medium RDS, 100GB    $0.082      $60
                                                     --------    -------
                                                      $0.248      $181

Notes:
- Pricing source: AWS us-east-1 on-demand, fetched <date>.
- Grain-2 cost shared with cluster, not standalone.
- Grain-3 storage uses default 100GB gp3 — verify against blueprint default.
```

Always include:
- Date of pricing fetch (prices change).
- Assumptions (region defaults, on-demand vs reserved, included vs excluded items).
- Confidence level per line (high / medium / low / unknown).
- Excluded items: data transfer, snapshots, load balancer hours when not specified.

---

## Step 5 — Optimization suggestions

After the cost breakdown, offer prioritized cost reductions:

1. **Right-sizing** — flag instances larger than apparent need (e.g., `t3.2xlarge` for a dev grain).
2. **Instance family** — suggest Graviton equivalents (`m7g` vs `m7i`) when workload supports ARM.
3. **Spot / preemptible** — for non-production or fault-tolerant grains.
4. **Termination scheduling** — if the env has no end-time, recommend `duration` input or scheduled teardown.
5. **Shared resources** — call out grains that duplicate infrastructure (e.g. two RDS instances where one would do).
6. **Storage tiering** — `gp3` over `gp2`, S3 Intelligent-Tiering for unpredictable patterns.

For each suggestion: estimated saving, blueprint YAML change needed, risk level.

When suggesting a YAML change, link to or invoke the `torque-blueprint` skill to actually produce the diff.

---

## Step 6 — Compare blueprints (if applicable)

When comparing two blueprints or before/after states:

```
            Current    Proposed   Delta
--------------------------------------------
Compute     $121       $86        -$35  (-29%)
Database    $60        $42        -$18  (-30%)
Storage     $12        $12         $0
--------    -------    -------    -------
Total       $193       $140       -$53  (-27%)
```

---

## Boundaries

- Cost estimates are **not authoritative billing**. Always tell the user to verify against the cloud provider's billing dashboard before making budget decisions.
- Never invent prices. If pricing fetch fails, state "pricing unavailable" for that line rather than guess.
- For workloads using committed-use discounts, savings plans, or enterprise agreements — the user's effective rate is lower. Ask before applying public pricing.
- Helm / Kubernetes grain costs depend on shared cluster capacity. Report as "shared" unless dedicated nodes are evident.

---

## Reference

- AWS Compute Optimizer (right-sizing): https://aws.amazon.com/compute-optimizer/
- Torque blueprint inputs / outputs: handled by `torque-blueprint` skill.
- AWS Well-Architected cost pillar: handled by `aws-best-practices` skill.
