# Track A vs. Track B — What Is This Import Actually For?

An import produces a blueprint and a Terraform asset that look exactly like every other
blueprint and asset in the repo. They are not the same thing, and the difference is decided
by the user's goal — not by the files. Surface the goal before scaffolding anything (see
Step 0 in `SKILL.md`).

---

## The goal question (ask before writing anything)

> What do you want this import to do for you?
>
> **(A) Manage this resource (or set of resources)** — see what it costs, schedule it down when
> idle, run day-2 workflows against it, change its configuration, detect drift.
>
> **(B) Use it as a source for new environments** — a digital twin of an existing set of resources, or turning
> a long-running environment into something launchable on demand.

Route by the answer:

| The user says | Track |
|---|---|
| "see what it costs", "schedule it off at night", "stop paying for idle" | **A** |
| "change its size / version / config from Torque", "run a workflow on it" | **A** |
| "detect drift", "know when someone changes it by hand" | **A** |
| "get visibility", "bring it under management", vague / unsure | **A** (default — say so) |
| "spin up a dev copy of prod", "digital twin", "clone this environment" | **B** |
| "make this launchable on demand", "templatize this app", "ephemeral copies" | **B** |

**Track A is the overwhelming default — roughly 99 of 100 imports.** If the user is unsure,
choose A, say you are choosing it, and state the consequence: *the resulting blueprint
represents this specific set of live resource(s) — one resource or many — and is not intended
to deploy a second copy of it.*

If the answer is "both," that is Track B — and Track B has to be committed to **before** the
import (Step 3 grouping and Step 4 templating both change), not retrofitted after.

---

## Track A: the blueprint represents a fixed set of live resources

### The rule

> A blueprint produced by a brownfield import represents a specific, fixed set of live
> resources — whether that's a single VM or a whole application stack. It is not intended to
> deploy a second copy of that set.

Parameterizing it (Step 4) is still worth doing — but **not so the user can launch copies**.
Inputs exist so the user can *change inputs to update the infrastructure that already
exists*. That is their entire purpose. Say this out loud to the user; it is the single
correction that dissolves most brownfield confusion.

### Why it cannot double as a template

This is not a platform restriction. It falls out of a decision the user already made
correctly when choosing what to import.

Most imports exist to get visibility and control over something already running. 
Cost is by far the most common driver, then day-two modification, workflows, and drift detection. 
None of that requires codifying the network the workload sits in, the IAM bindings it
authenticates with, or the security rules around it. Those already exist and already work —
so the import covers the handful of high-value, cost-incurring resources worth managing, and
correctly leaves the rest alone (Step 3's grouping guidance).

A blueprint that genuinely *creates* an environment has no such luxury: nothing exists yet,
so every supporting piece has to be in the configuration.

> **The real reason:** an import blueprint cannot clone its resources because the user never
> codified the things a clone would need — and for what they were doing, they were right not to.

### Two models, easily mistaken for one

| | Greenfield / Track B — blueprint as template | Brownfield (Track A) — blueprint as a fixed resource set |
|---|---|---|
| **Purpose** | Deploy many independent environments from one definition | Bring an existing, running resource (or set of resources) under management |
| **Relaunching** | Expected; that is the point | Not supported — fails on conflicts, harmlessly |
| **Inputs exist to** | Configure each new copy independently | Update infrastructure that already exists |
| **State** | Fresh, isolated state file per environment | Bound to the one state file (per grain) describing the live resources |
| **Resource naming** | Parameterized or suffixed to avoid collisions | Fixed — the names already exist in the cloud |
| **Scope** | Everything the workload needs: networking, security, IAM | Just the resources worth visibility and control; supporting infra correctly left out |

### If someone launches a second environment anyway

Users ask this with real urgency — *"the state already exists, won't Terraform apply changes
to production?"* Walk them through the mechanism. Nothing here is enforced by Torque; it
falls out of how Terraform and the cloud provider already behave.

1. Someone launches a second environment from the import blueprint.
2. Torque computes a **fresh state key** for that environment. It points at an empty state file.
3. Terraform reads that empty state, sees no resources recorded, and plans to **create** everything
   the configuration declares — one resource or many.
4. It asks the provider to create each resource using the name already baked into its configuration.
5. Depending on the resource type, the provider may reject the create: **that name is already
   taken.** The launch fails. The live resources are never touched. For any resource whose name
   isn't uniqueness-constrained, creation would likely still fail on a different missing
   dependency — a security group, subnet, or IAM role the import correctly never codified (see
   "Why it cannot double as a template" above).

> **Why this is safe, not lucky:** Terraform only destroys what is recorded in its state. 
> An empty state has nothing to destroy, so it can never produce a destroy plan for resources it
> did not create.

The only way to make Terraform destroy a pre-existing resource is to deliberately import that
resource into a state file and then run a destroy against it. An accidental second launch
fails at the create step, well before anything is at risk.

### Naming and placement should carry the constraint

`Imported GKE Cluster` / `imported-gke-cluster` tells anyone browsing the catalog what they're
looking at. A generic name invites exactly the second launch the asset cannot support. Carry
the same signal into the folder name (`terraform/imported-gke-cluster/`) alongside the
canonical layout from `repo-conventions` — see Step 8 for the exact convention-check gate.

When the import covers several resources grouped into one grain (Step 3), name for the group or
workload as a whole (`imported-app-stack`), not for just one resource inside it — the same
"not reusable" signal has to cover everything the grain actually wraps.

---

## Track B: digital twin / templatizing

A single blueprint *can* be both the source of an imported environment and a template for
copies. That is legitimate. It is rare — call it one import in a hundred — and it is never
discovered after the fact; it has to be chosen before the import (Step 3 grouping decisions
depend on it).

Two independent bars have to be cleared. Most imports clear neither. Check both explicitly
with the user before importing:

**Bar one — completeness.** Everything the workload depends on has to be captured:
networking, security, IAM, address ranges, the lot — not just the high-value resources an
ordinary (Track A) import focuses on. If a piece is missing, a copy built from the
configuration will not stand up.

**Bar two — parameterization.** Every name, every range, and every value that must be unique
per instance has to become an input, so two instances can coexist without colliding. Rare on
its own, because import-generated configuration (Step 5) is written entirely in literals by default.

Legitimate reasons to take this on:

- **A digital twin.** Production exists, dev or staging does not. Import the real thing, parameterize it, stand up a right-sized clone from the same definition.
- **Templatizing an application environment.** Turn a long-running environment into something launched and torn down on demand.

If the user is asking about Track B **after** an import already happened, tell them plainly:
retrofitting an existing import into a template is usually more work than building the
template from scratch. Offer both paths and let them choose — never retrofit silently.

For Track B, hand the module to `reusable-terraform` for the parameterization pass (its
standard Rules 1–5 apply in full — Track B is exactly the case its brownfield exception does
**not** cover), and run `blueprint-review` / `/deploy-check` on the result.
