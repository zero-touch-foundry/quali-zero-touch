---
name: import-cloud-resources-as-environment
description: >
  Use this skill to import existing, running cloud resources (AWS, Azure, GCP, or other providers)
  into Torque as a managed environment — an alternative to Torque's built-in curate/codify tool,
  unreliable on non-Torque-curated assets.
  Drives the pipeline: look up live resource details via cloud CLI,
  generate a non-templated Terraform config matching them exactly,
  run a real `terraform import` against a cloud-native backend,
  commit to a Torque-connected repo, sync it, optionally author a minimal blueprint,
  and call Torque's import API.
  Triggers: "import this VM into Torque", "bring my existing cloud resources into Torque",
  "codify this resource", "create a Torque environment from an existing resource", "import
  <resource id> as a Torque environment", "curate this resource manually", "replace Torque's codify tool".
  Never improvise a Terraform import config or Torque import call from memory — verify
  against the live provider schema, plan output, or Torque API/swagger.
---

# Import Cloud Resources as a Torque Environment — SKILL.md

## Overview

This skill replaces Torque's built-in "curate" codify tool with an explicit, verifiable pipeline driven by Claude. 
Torque's embedded codify tool has known failures across various resource types;
This skill trades a one-click black box for a slower but auditable, empirically-verified process:

```
1. Identify & authenticate          → cloud CLI, correct account/subscription/project
2. Look up resource(s)              → live cloud API, never memory
3. Group into grains                → one Terraform root module per grain
4. Decide templating level          → non-templated (default) vs. blueprint inputs
5. Generate Terraform               → empirically verified against real provider schema
6. Provision/reuse a state backend  → cloud-native, OIDC-preferred
7. terraform import → plan loop     → iterate until "No changes"
8. Commit to Torque-connected repo  → follow the REPO's existing convention
9. Sync the repo                    → before referencing new content
10. (Optional) author a blueprint   → minimal, no baked-in backend
11. Call the Torque import API      → import_using_blueprint preferred (see Known Issues)
```

**Read `references/known-issues.md` before Step 11.** Two confirmed-real server bugs currently
affect Torque's import endpoints, plus one documented vCenter/vSphere limitation with a real
opt-out (`tags.auto-tag: false` on the grain) — know all three before you start debugging your own
request as if it were a new problem.

**Read `references/track-a-vs-track-b.md` before Step 0.** An import produces a blueprint and a
Terraform asset that look exactly like every other blueprint and asset in the repo. They are not
the same thing as a normal reusable grain — whether they may ever be relaunched as a second
environment is decided by the user's goal, not by the files, and has to be settled before you
scaffold anything (Step 0, item 7).

**Before running any Torque API call, read `${CLAUDE_PLUGIN_ROOT}/skills/zero-touch-api/SKILL.md`**
and route every HTTP call through its `torque_api.py` helper — do not hand-roll `curl`.

---

## Step 0 — Required Inputs (Gate — Do Not Proceed Until All Seven Are Confirmed)

This skill has already failed partway through a run by silently filling in gaps instead of asking
— an unnamed agent, a backend written into a place it shouldn't have been. **Both were preventable
by treating the inputs below as a hard gate, not something to discover step-by-step while working.**
Check all seven before generating anything. If any are missing, **ask for all of the missing ones
together, in one message** — don't proceed partially and don't trickle questions one at a time.

1. **Cloud/hypervisor credentials.** Either the user supplies credentials for this session (access
   key/secret/session token, service principal, etc.), **or** there's an already-authenticated CLI
   session for the right account/subscription/project. An authenticated CLI session for the *wrong*
   account is worse than none — always confirm identity (Step 1) before trusting it, even if a
   session already exists.
2. **Unique identifier + type for every resource to import**, including whatever region/location/
   resource-group/zone/project scoping is needed to actually resolve full details — not just enough
   to find *a* matching resource, but the specific one intended. If a name is ambiguous without more
   scoping, ask for the missing scoping rather than search broadly or guess which match is meant.
3. **Target backend details, or explicit authorization to create one.** Either the user names an
   existing bucket/storage account/etc. (and its cloud + auth method) to reuse, or explicitly
   authorizes provisioning a new one (which cloud, which auth style — OIDC preferred, see Step 6).
   Do not default to creating a new backend un-asked, and do not silently reuse one you happen to
   find — confirm it's the intended one first.
4. **Local repo clone path to commit into, and that repo's Torque-registered logical name** in the
   target space. These are two different things and both are required — the filesystem path you'll
   write files to, *and* the `store:`/`repository_name` value Torque uses for it (frequently **not**
   the same as the git repo's own name):
   ```bash
   python torque_api.py GET /spaces/<space>/repositories
   ```
   Match on `repository_url`, read `name` — never assume repo name == registered store name.
5. **A valid Torque API token for this run, or a pre-configured profile.** Check before asking:
   ```bash
   python torque_api.py configure --show
   ```
   If neither is available, see `zero-touch-quickstart`.
6. **Target Torque space to import into, and the specific agent to use.** Both are the user's call,
   not something to infer. Never silently pick "the only active agent visible" in
   `GET /spaces/<space>/agents`, never reuse whichever agent a previous run happened to use as a
   default. Confirm the named agent is eligible (`active` status, matching cloud/subscription) once
   it's named — but the naming itself must come from the user.
7. **The goal this import is for — Track A (manage the live environment) or Track B (also use it
   as a template for new environments).** Read `references/track-a-vs-track-b.md` and ask the goal
   question there before generating anything. Track A is the default (~99 of 100 imports); if the
   user is unsure, choose it, say so, and state the consequence (the blueprint represents this one
   live environment and is not intended to deploy a second one). Track B changes what gets
   imported (Step 3's grouping) and how it's templated (Step 4) — it must be chosen **before**
   import, never retrofitted silently after the fact.

---

## Step 1 — Identify & Authenticate

Ask the user (don't guess) for enough to uniquely address every resource:

| Cloud | Required identifiers |
|---|---|
| AWS | Account ID, region, resource ID/ARN per resource, IAM role to assume (if cross-account) |
| Azure | Subscription ID, resource group, resource name or full resource ID per resource |
| GCP | Project ID, region/zone, resource name per resource |

**Confirm the CLI's active identity matches the target BEFORE any lookup — do not assume:**

```bash
# AWS — assume role first if the target account differs from the default identity
aws sts get-caller-identity
aws sts assume-role --role-arn <arn> --role-session-name import-session   # if needed

# Azure
az account show --query "{id:id, name:name}" -o tsv
az account set --subscription <target-subscription-id>   # if it doesn't match

# GCP
gcloud config get-value project
gcloud config set project <target-project-id>            # if it doesn't match
```

A subscription/account mismatch here silently produces "resource not found" errors two steps later
that look unrelated — always check first, every time, even if the user "already did it earlier."

(Agent name and Torque space are gated in Step 0, item 6 — don't proceed here without them.)

---

## Step 2 — Look Up Live Resource Details

Never write a Terraform value from memory or by guessing a "typical" shape. Fetch the full live
object for every resource, **and every sub-resource whose fields you'll need but that isn't fully
inlined in the parent's response** (e.g. an Azure VM's OS disk SKU/size lives on the disk resource,
not the VM):

```bash
# Azure — VM example
az vm show --ids <full-resource-id> -d -o json
az disk show --ids <os-disk-resource-id> -o json

# AWS — EC2 example
aws ec2 describe-instances --instance-ids <id>
aws ec2 describe-volumes --volume-ids <id>

# GCP — Compute example
gcloud compute instances describe <name> --zone <zone> --format json
```

Capture every field you'll reference in Terraform, including tags — an exact tag match is often
the difference between a clean `plan` and a spurious diff.

---

## Step 3 — Group Resources Into Grains

Ask the user how they want resources grouped, or propose a grouping and confirm before proceeding.
Reasonable defaults when the user says "you decide":

- Resources that share a lifecycle (created/destroyed together) → one grain.
- Resources of very different blast-radius or ownership (e.g. a shared VNet vs. an app VM) → separate grains.
- A resource and its tightly-coupled dependents (VM + its own OS disk + its own NIC) → one grain; a
  shared/reused dependency referenced by ID (an existing subnet, an existing NSG) → not re-declared
  as a resource at all, just referenced by its literal ID string.

Each grain becomes one Terraform root module (its own provider + backend + resource files) with a
name matching Torque's grain-name constraint: `[a-zA-Z0-9-_ ]{3,45}`.

---

## Step 4 — Decide the Templating Level

This step means two different things depending on the Track chosen in Step 0, item 7 — check
which one applies before asking anything here.

**Track A (the default — manage the live resource(s)):** ask the user which resource attributes
(if any) should become launch-time blueprint inputs, and for which resources — only relevant
if a blueprint will be generated (Step 10). These inputs exist to let the user *update the
live resource(s)*, not to configure a new copy; say so if it isn't already obvious from context.

**Default recommendation: fully non-templated (literal, hardcoded values) for the first cut.** This
mirrors what Torque's own internal curate output actually looks like (flat resource blocks with real
values baked in, no `variables.tf`), is the fastest to verify against "no diff on import," and can be
refactored into templated inputs later once the import itself is proven correct. Templating during
the initial import adds a second axis of things that can silently produce drift.

If the user does want inputs from the start, keep them to attributes safe to vary without changing
resource identity (instance size, tags, replica counts) — never template anything that's part of
the resource's import ID or an immutable/`ForceNew` field for the first pass. If a field is pinned
by `lifecycle.ignore_changes` or only read by the provider at creation time, any input wired to it
is inert against the already-imported resource it targets — either don't expose it, or say plainly
in its `description` that it has no effect here.

**Track B (digital twin / template):** this step is where Track B's parameterization bar
(see `references/track-a-vs-track-b.md`) actually gets met. Every name, range, and per-instance
value that must not collide across copies needs to become an input — hand the module to
`reusable-terraform` for its full Rules 1–5 parameterization pass rather than doing a partial job
here, since a half-parameterized Track B module is worse than a clearly-labeled Track A one.

---

## Step 5 — Generate Terraform (Empirically Verified, Not From Memory)

**This is the step most likely to go wrong if you trust documentation or training data over the
live provider.** Cross-field validators (`ExactlyOneOf`, `AtLeastOneOf`) are frequently invisible in
a static schema dump — the only reliable signal is a real `terraform validate`/`plan` error message.

```bash
# Dump the real schema for reference (attribute-level required/optional/computed)
terraform providers schema -json > schema.json
python3 -c "
import json
s = json.load(open('schema.json'))['provider_schemas']['registry.terraform.io/hashicorp/<provider>']['resource_schemas']['<resource_type>']['block']
print('REQUIRED:', sorted(k for k,v in s['attributes'].items() if v.get('required')))
"
```

Confirmed real-world traps worth knowing before you start (don't rediscover these blind):

- **`azurerm_linux_virtual_machine`**: `admin_username`/`admin_password` show as `optional: true` in
  the static schema, but a runtime validator requires "one of `admin_username`, `os_managed_disk_id`"
  regardless. If the real VM has an `osProfile` (it was deployed from an image), set the real
  `admin_username` (a public, non-secret value) and omit `admin_password` entirely — Azure never
  returns it, and nothing requires it.
- **`azurerm_windows_virtual_machine` / `azurerm_linux_virtual_machine` on an "attach-mode" VM**: if
  the real resource's `storageProfile.osDisk.createOption` is `Attach` (not `FromImage`), there is no
  `osProfile` at all — no admin username exists to recover. Use `os_managed_disk_id` pointing at the
  existing managed disk instead of any identity field. When you do, `os_disk {}` must be stripped
  down to **only** `caching` — `name`, `storage_account_type`, and `disk_size_gb` all conflict with
  `os_managed_disk_id` ("only one of ... can be specified").
- **Unpinned "latest" provider majors change validator behavior between versions.** The same
  `admin_username` validator above did not exist the same way across an azurerm major bump in this
  project. Always pin `required_providers` to an explicit version constraint, and verify against it
  specifically — don't test against whatever happens to already be cached locally.
- Any field the schema calls `computed: true` and you leave unset in config will be populated from
  real state on import with **zero diff risk** — prefer omitting computed fields over guessing a
  literal value for them, unless a validator specifically forces you to set one (as above).
- **`aws_instance.user_data`**: leaving it unset in config when the real instance has `user_data`
  set produces a real (non-cosmetic) diff on `plan` — unlike most omitted-computed-field cases, this
  one does not resolve itself by omission. **Do not "fix" this by fetching the real value and writing
  it into the committed file** — `aws ec2 describe-instance-attribute --attribute userData` will hand
  it back even when it's cloud-init containing a plaintext password (`chpasswd`, SSH keys, etc.).
  Recoverable via the API is not the same as safe to commit. Use
  `lifecycle { ignore_changes = [user_data] }` instead — cloud-init only runs on first boot anyway,
  so ignoring drift on it going forward is correct, not just expedient. This is the general pattern
  for any field that's technically recoverable but secret-bearing: never let "the API will give it to
  me" override "this shouldn't go in git."
- **`aws_instance.user_data_replace_on_change`**: a Terraform-local-only setting with no real AWS
  attribute behind it. `Read()` never populates it from state, so it shows a cosmetic `+` on the
  *first* `plan` after import even when explicitly set to its own default (`false`) in config.
  Bundle it into the same `ignore_changes` as `user_data` rather than running a live `apply` against
  a real resource just to clear a diff that was never going to change anything.
- **Provider source can silently move to a new namespace.** `hashicorp/vsphere` moved to
  `vmware/vsphere` for Terraform 0.13+; `terraform init` still works with the old source (with a
  warning), but use the current one — don't propagate a stale namespace just because an existing
  local example in the repo still uses it.
- **`vsphere_virtual_machine.disk.label` must match the real device's label exactly** (e.g.
  `"Hard disk 1"`), not a conventional placeholder like `"disk0"`. A mismatched label makes
  Terraform delete-and-recreate the whole disk block on plan rather than diff it in place — this is
  a much louder failure mode than most label-mismatch cases, and easy to misread as "the disk is
  wrong" rather than "the label is wrong."
- **`vsphere_virtual_machine.cdrom` must be declared even for an empty/disconnected drive.**
  Omitting the block entirely reads as "delete this device" if the real VM has one (even a real
  optical drive with no media attached, which is extremely common). `client_device = false` (not
  `true`) is usually correct for a disconnected drive — `govc`'s `"Remote device"` summary text is
  misleading and does not mean client-device passthrough.
- **Not every Optional+Computed field that "doesn't have a real infra equivalent" is safe to
  override.** AWS's `user_data_replace_on_change` is genuinely never populated by `Read()` (safe to
  set to any default without creating a diff). vSphere's `wait_for_guest_net_timeout` looks like the
  same category of Terraform-only provisioning knob, but *is* populated by `Read()` with a real
  value from the provider's own state handling — overriding it to a "safe default" created a real
  diff. Don't generalize a lesson about one field to a same-shaped-sounding field on a different
  provider without checking; when in doubt, omit and let `plan` tell you if that was wrong.
- **`vsphere_virtual_machine`'s `sata_controller_count`, `enable_disk_uuid`, `enable_logging`, and
  `tools_upgrade_policy` are Optional+Computed but frequently carry real, non-default values** on an
  existing VM (a SATA controller for a CD-ROM device, VMware Tools settings, etc.) — check the
  actual `plan` diff rather than assuming defaults are fine just because the schema doesn't mark
  them required.

Four more general shapes, not tied to one provider, that recur across every import regardless of
cloud — check for these even when the provider-specific list above doesn't apply:

- **Not every same-named field means the same thing — can destroy the resource.** A cluster
  resource and a node-pool resource can both expose a field called e.g. `initial_node_count`. On
  the node pool it's an ordinary creation-time count; on the cluster it can be a legacy bootstrap
  field for an implicit default pool that **forces replacement**. Before parameterizing any field
  in Step 4 (even a "safe to vary" one), check whether it forces replacement on *this specific
  resource type* — read the provider docs for that resource, not just the field name.
- **Let outside owners own their fields — otherwise, perpetual diff.** When something outside
  Terraform legitimately changes a value (a managed auto-upgrade moving a version forward, a
  scaling workflow changing a node count), Terraform proposes reverting it on every `plan`,
  forever. Name those fields in `lifecycle.ignore_changes` — the same pattern as the `user_data`
  case above, generalized to any externally-owned field, not just secret-bearing ones.
- **Import-generated configuration has no relationships — silent drift.** Import output writes
  literal values everywhere: a cluster references its network as a hardcoded string rather than
  pointing at the network resource beside it, so Terraform knows of no dependency. For
  infrastructure the module should not own (Step 3's "referenced by literal ID" case), consider a
  **data source** instead of a bare literal where practical — the relationship becomes real, and a
  rename surfaces at plan time instead of silently pointing at something that no longer resolves.
- **Moving the backend to the blueprint changes local Terraform runs.** Once the backend lives in
  the blueprint/API call (per this step's file-layout rule) instead of the module, the module
  declares no backend at all. A bare `terraform init` run locally in that directory offers to
  migrate state *out* of remote storage onto local disk — **decline it.** Pass the backend
  explicitly with `-backend-config` flags for local/scratch runs (Step 7), and expect credentials
  to differ too: a module authenticating through an agent's ambient/workload identity cannot
  resolve that identity from a laptop.

### Terraform engine version alignment

Confirm the **exact** Terraform CLI version the target Torque account's engine actually runs before
verifying anything — don't trust a cached number from an unrelated doc (this has been observed to
disagree with what an account admin reports; confirm current truth for the account you're targeting).
Pin locally with `tfenv`:

```bash
echo "<confirmed-version>" > .terraform-version   # e.g. via tfenv, local to the working dir
tfenv install <confirmed-version>                  # if not already installed
```

Run every `init`/`import`/`plan` in this skill under that pinned version, not "whatever's newest."

### File layout

One `terraform {}` block per provider file containing **both** `required_providers` and `backend`
together (don't split them across two separate `terraform {}` blocks in the same file — valid HCL,
but needlessly unusual). One resource file per grain. Match whatever naming convention the target
repo already uses for this kind of asset (check for precedent — e.g. `provider_<cloud>_<region>.tf`
+ `resources_<cloud>.<region>_<id>.tf` — before inventing a new one; see Step 8).

**The `backend` block belongs in exactly one place: the API call (`grains[].backend`) or a
blueprint's `backend:` spec — never in the committed source file, ever.** This has already gone
wrong once (a backend block was left in both the committed asset *and* the API call in the same
run) — treat it as a hard rule, not a judgment call:

- **Do all local `terraform import`/`plan` verification (Step 7) in the scratch working directory**
  (e.g. under a `scratch/` or temp path outside the target repo clone), never directly inside the
  repo you're about to commit from. The backend block lives in that scratch copy only, for exactly
  as long as it takes to get a clean `plan`.
- When copying the verified files into the actual repo path for commit, **copy only the resource
  file(s)**; regenerate or hand-strip the provider file for the repo so it contains
  `required_providers` only — no `backend "..." { ... }` block.
- **Before `git add`, grep the files you're about to stage for a live `backend` block and treat any
  match as a blocker, not a warning:**
  ```bash
  grep -n 'backend "' <path-to-files-about-to-be-committed>/*.tf
  # any match here means STOP — strip it before staging, don't commit and fix later
  ```
- This check belongs in Step 8, immediately before `git add` — not as something to remember to do
  "at some point," since that's exactly how it was missed.

---

## Step 6 — Provision or Reuse a State Backend

Prefer OIDC / workload identity over static credentials wherever the cloud supports it for both the
Terraform provider itself and the state backend:

| Cloud | Backend | Preferred auth | Fallback |
|---|---|---|---|
| AWS | S3 (+ optional DynamoDB lock table) | IAM role via OIDC/IRSA, or `assume_role` | Static access keys |
| Azure | Storage Account + Blob Container | Workload Identity Federation (`use_oidc: true` + `client_id: <app-id>` on the backend block) | Storage account access key (`ARM_ACCESS_KEY` env var — never hardcoded in the file) |
| GCP | GCS bucket | Workload Identity Federation | Service-account JSON key |

**Default to one backend per target cloud, reused across every grain/resource imported for that
cloud** — a distinct `key`/prefix per grain, not a new storage account/bucket per resource, and not
one shared backend across different clouds. Backend type and auth are cloud-specific (an Azure
Storage Account can't hold AWS's OIDC/IRSA trust relationship, etc.), so keeping a dedicated backend
per cloud is what lets OIDC/workload-identity stay the prioritized default regardless of which cloud
is being imported from. Check whether a suitable backend already exists for this account/project (in
that cloud) before creating a new one. Only deviate from one-per-cloud if the user explicitly names a
specific backend to use.

**Every import gets its own key/prefix, and you must verify that key doesn't already hold state
before writing to it — reusing the backend does not mean reusing (or risking a collision on) a
path within it.** A shared backend with a colliding key is exactly how one import's `terraform
init`/`import` ends up silently loaded against — and potentially corrupting — a *different*
environment's state. **Never use a bare/generic default key like `terraform.tfstate` at the bucket
or container root** — that's the single most likely path to already be occupied by something else
in a backend the user pointed you at (this has already happened once: a run defaulted to the plain
`terraform.tfstate` name and overwrote existing content at that key). Always construct a key that's
specific to this grain, e.g. `terraform/<grain-name>/terraform.tfstate` or
`terraform/<resource-id>/terraform.tfstate` — a full path derived from something unique to this
import, never a filename generic enough to plausibly already be in use. Then confirm it's actually
free before proceeding:

```bash
# AWS — expect a 404/"Not Found"; anything else means STOP
aws s3api head-object --bucket <bucket> --key <proposed-key>

# Azure — expect "BlobNotFound"; anything else means STOP
az storage blob show --account-name <account> --container-name <container> --name <proposed-key>

# GCP — expect "No URLs matched"; anything else means STOP
gcloud storage objects describe gs://<bucket>/<proposed-key>
```

If the key already exists, **do not silently pick a different one and move on either** — that's
still guessing on the user's behalf about something that could matter (maybe it's leftover from a
prior run of this same import and reusing it is exactly right; maybe it's someone else's unrelated
state and colliding with it would have been a real incident). Stop and ask.

---

## Step 7 — Import → Plan Loop

**Before `terraform init`: confirm the backend key/prefix collision check from Step 6 actually
happened for this grain.** Don't run `init` against a key you haven't verified is either free or
knowingly-intended-to-be-reused.

```bash
export ARM_ACCESS_KEY=... # or the cloud-appropriate equivalent; never commit this
terraform init -input=false
terraform import '<resource_type>.<name>' '<real-resource-id>'
terraform plan -input=false -no-color
```

Iterate on real `plan`/`import` error text — never pre-emptively add a field because it "seems like
it should be there." Common fix patterns, worst-first:

1. **A block/attribute is missing** → the plan shows it going from a real value to `null`; add it
   with the literal value from Step 2.
2. **A conflicting-arguments error** → two mutually exclusive fields were both set (see the
   `os_managed_disk_id` trap above); remove the one that doesn't apply.
3. **An unset required-by-validator field** → the error names it explicitly (e.g. "one of X, Y must
   be specified"); prefer the option that reflects reality (e.g. `os_managed_disk_id` for an
   attach-mode disk) over fabricating a plausible-looking value for the other option.
4. **A write-only/unrecoverable secret field is required by the validator and there's no alternative
   like `os_managed_disk_id`** → last resort only: a placeholder value plus
   `lifecycle { ignore_changes = [<field>] }`. Prefer omission or an alternative field first; this
   should be rare.

If a bad import needs redoing (wrong ID, wrong resource type): `terraform state rm '<addr>'` then
re-import — don't try to hand-edit the state file.

Stop only when `terraform plan` reports **"No changes."** — that's the actual completion signal for
this step, not "the import command didn't error."

**There is no iteration cap, and no such thing as "close enough."** Don't move on to Step 8, report
this step done, or ask the user to accept a dirty diff because you've tried a few things and the
error is unfamiliar — keep dumping the real schema, reading the actual error text, and adjusting.
This matters most on exactly the provider you know least well, which is precisely when the pull to
cut the loop short is strongest.

`ignore_changes` is scoped to the two documented categories above — a secret-bearing field that's
recoverable but must never be committed, and a Terraform-local-only field `Read()` never populates
— **not a general-purpose way to make a stuck plan look clean.** Reaching for it outside those two
cases doesn't resolve a mismatch, it hides one, and a hidden mismatch is worse than a visible one
because nothing will ever surface it again. If you genuinely exhaust real leads — the error text
stops changing across attempts, or resolving it needs information only the user has (e.g. which of
several ambiguous datastores/networks/resource pools was actually meant) — **stop and ask.** That's
a legitimate outcome. A fabricated clean plan is not.

---

## Step 8 — Commit to the Torque-Connected Repo

**Check for an existing convention in the target repo before inventing one.** Many repos already
have an established (if informal) location and file-naming pattern for this kind of asset — follow
it for consistency even if it differs from Torque's general `repo-conventions` skill guidance for
brand-new modules, since this is accessory/generated-style content, not a hand-authored reusable
module.

**Track A only — carry the "not reusable" signal into the name, not just prose.** `imported-gke-cluster`
tells anyone browsing the repo or catalog what they're looking at; a generic module/folder name
invites exactly the second-launch mistake `references/track-a-vs-track-b.md` walks through. If the
target repo has no existing convention to defer to above, default to an `imported-<resource>` name
(module folder and, in Step 10, blueprint name) — or, when the grain groups several resources
(Step 3), name it for the group/workload as a whole (`imported-app-stack`), not for just one
resource inside it. A dedicated `imported/` tree is also fine if the team prefers hard separation.
Track B assets should NOT carry this signal — they are meant to look like an ordinary reusable
module.

**Never write to, or mimic the folder/branch structure of, anything identified as belonging to
Torque's own internally-managed "fully managed curate" flow** (e.g. a dedicated bot-maintained
branch, or a folder containing per-resource generated-ID subfolders with a `.torque-generated`
marker file). That structure is exclusively Torque's own bookkeeping for a *different* feature —
treat it as read-only and unrelated to this pipeline, even if it looks superficially similar.

**Gate — run this immediately before `git add`, every time, no exceptions:**

```bash
grep -n 'backend "' <new-asset-path>/*.tf
```

Any match is a blocker. Strip it before staging — do not commit and plan to fix it afterward.

```bash
git add <new-asset-path>
git commit -m "..."
git push origin <branch>
```

Stage only the files you intend to add — never a broad `git add -A` in a repo with unrelated
in-flight changes.

---

## Step 9 — Sync the Repo

Torque won't see the new commit until it re-syncs. Force it, then confirm:

```bash
python torque_api.py POST /spaces/<space>/repositories/<repo-name>/update
python torque_api.py GET /spaces/<space>/repositories
# confirm `last_synced` on the target repo advanced past your commit time, and (for Terraform
# assets) that iac_assets_count.Terraform increased
```

Do this again after *any* subsequent push (e.g. a blueprint fix) before retrying an API call that
depends on it — a stale sync is a common source of "why isn't my change taking effect."

---

## Step 10 — (Optional) Author a Blueprint

Skip this step entirely if the user chose "no blueprint" in Step 4 and Known Issue #1 (see
`references/known-issues.md`) doesn't affect the target account — go straight to
`POST .../environments/import` instead.

Otherwise, invoke the `author-blueprint` skill — tell it up front that this is a Track A/B import
blueprint (see `references/track-a-vs-track-b.md`) so it applies the right assumptions instead of
its normal reusable-blueprint defaults. Minimal shape for a single already-imported grain:

```yaml
spec_version: 2
description: >
  <what this wraps>. Represents this specific live resource or set of resources, imported via
  import-cloud-resources-as-environment; not intended to launch a second copy (Track A).
  Expects backend to be supplied at import time.
inputs:
  agent:
    type: agent
grains:
  <grain_name>:
    kind: terraform
    spec:
      source:
        store: <torque-registered-repo-name>
        path: <path-to-the-committed-asset>
      agent:
        name: '{{ .inputs.agent }}'
      inputs: []
```

No hardcoded `backend:` in the blueprint spec (see Step 5). Commit, push, sync (Step 9), then
**confirm registration before calling the import API**:

```bash
python torque_api.py GET /spaces/<space>/blueprints
# find your blueprint by name; confirm `errors: []` and `grains[].name` matches what you'll
# reference in the import call
```

---

## Step 11 — Call the Torque Import API

**Read `references/known-issues.md` first.** Two confirmed/likely-live server bugs currently
affect these endpoints, plus a vCenter/vSphere-specific limitation with a real fix; check whether
any of them apply to the target account/resource type before
assuming a mistake in your own request.

**Validate your request body against the live swagger for the target account/flavor before sending
it** — schemas can differ between Torque flavors (e.g. "stack automation" vs. standard) and drift
from any saved example over time:

```
GET <host>/swagger/latest/swagger.yaml
```
Find the endpoint, resolve its `requestBody` schema `$ref`, and check every field name, type, and
`nullable`/`additionalProperties` setting against what you're about to send — don't rely solely on
a previously-saved `.http` example, however similar it looks.

**Recommended default: `import_using_blueprint`.** It doesn't depend on Torque's internal
auto-blueprint-generation service, which has known reliability issues on externally-placed assets
(Known Issue #1).

```
POST /spaces/<space>/environments/import_using_blueprint
{
  "source": { "blueprint_name": "<name>", "repository_name": "<torque-repo-name>" },
  "environment_name": "Imported Environment - <Resource Name(s)> <Resource Type(s)>",
  "owner_email": "<owner>",
  "grains": [
    {
      "kind": "terraform",
      "name": "<grain-name-matching-blueprint>",
      "agent": { "name": "<agent>" },
      "backend": { "type": "<cloud-backend-type>", ...cloud-specific fields... }
    }
  ],
  "inputs": { "agent": "<agent>" }
}
```

Or, without a blueprint (subject to Known Issue #1):

```
POST /spaces/<space>/environments/import
```
Same shape, minus `source`.

**Grain-level credentials — two distinct concerns, don't conflate them:**
- **Backend access** (the S3/storage-account/GCS credential the Terraform *backend* itself needs):
  add `"authentication": ["<torque-credential-name>"]` to the grain object — a real, schema-backed
  array field on `ImportGrainRequest` (confirmed via live swagger, not assumed). Ask the user which
  credential name to reference; never guess or omit it and hope the agent's ambient identity covers
  it.
- **Provider auth** (what the Terraform *provider itself* needs — a vSphere username/password, a
  database password, anything the module declares as a `variable` with no default): check whether
  the target Torque account already has **account-level parameters** for this before assuming you
  need a new credential store entry. These are referenced from blueprint YAML as
  `{{ .params.<name> }}` and get resolved server-side at launch/import time — the actual secret
  value never has to pass through you, a file you write, or this conversation. Wire them as grain
  `inputs` in the blueprint:
  ```yaml
  inputs:
    - hostname: '{{ .params.vcenter_hostname }}'
    - username: '{{ .params.vcenter_username }}'
    - password: '{{ .params.vcenter_password }}'
  ```
  Ask the user for the parameter names rather than guessing them — don't check a
  `GET /spaces/<space>/settings/credentialstore` result and treat an empty list as "there's nothing,
  I need to invent something": account-level params are a separate store from that endpoint, and
  the right answer is often "ask what already exists" rather than "provision something new."

**Some agents are flaky — expect to retry.** A grain can fail at `Prepare` with something like
`"the remote runner was not found. might be removed by user or failed to be created"` — a
transient compute-layer hiccup on the agent's side, not a config problem. If you see this, and the
agent's own `GET /spaces/<space>/agents` status is `active` with a recent heartbeat, release the
failed environment and simply retry the same call — don't start second-guessing the blueprint or
credentials over a runner-provisioning error.

**Always release a stuck/errored import — never end/terminate it:**
```
DELETE /spaces/<space>/environments/<id>/release?force=true
```
`release` is "end without termination" — the correct way to clean up an import that never got
infrastructure into a state Torque should try to tear down. The regular end/terminate API assumes
Torque fully owns the resource's lifecycle and will attempt to destroy it — exactly wrong for an
import, where the underlying resource existed before Torque touched it and must survive Torque
releasing the environment.

**Timestamp every call you send (UTC) and keep the exact request + response** — if it fails, that
pairing is what makes a backend log/trace lookup possible.

---

## Output Format

When reporting a completed (or attempted) run, structure the summary as:

### ✅ / ❌ Summary
- Resource(s): `<id(s)>`, cloud, region/location
- Grain(s): name → resource(s) mapping
- Templating: non-templated / which inputs exposed
- Backend: type, location, auth method
- Repo: path committed, commit sha
- Import API result: environment id + status, or the exact error + which Known Issue it matches (if any)

### 🧪 Verification Evidence
- `terraform plan` final output (must show "No changes" before claiming success on the IaC side)
- Repo sync confirmation (`last_synced` timestamp)
- Blueprint registration confirmation, if applicable

### ⚠️ Anything Deviated From Defaults
Call out explicitly: non-standard grouping, any placeholder/`ignore_changes` fallback used, any
convention the target repo already had that this run followed instead of the general guidance above.

---

## Never Do

- **Never** scaffold anything before Step 0's seven items are confirmed, including the Track A/B
  goal question (item 7) — see `references/track-a-vs-track-b.md`.
- **Never** present a Track A import blueprint as reusable, or suggest launching a second
  environment from one unless the original environment was released — that's the specific confusion the Track A/B split exists to prevent.
- **Never** parameterize a field (Step 4) without checking whether it forces replacement on that
  specific resource type (Step 5).
- **Never** silently retrofit a completed Track A import into a Track B template — say what it
  costs (both bars in `references/track-a-vs-track-b.md`) and let the user choose.
- **Never** leave a `backend` block in the committed Terraform source — it belongs in the API call
  or the blueprint's `backend:` spec (Step 5, Step 8 gate).
- **Never** expose a blueprint input that can't affect the live resource(s) (an `ignore_changes`-pinned
  or creation-only field) without saying so plainly in its `description` (Step 4).

---

## Reference Links

- Blueprint YAML structure: https://docs.qtorque.io/blueprint-designer-guide/blueprints/blueprints-yaml-structure
- Terraform grain spec: https://docs.qtorque.io/blueprint-designer-guide/blueprints/terraform-grain
- Repo conventions: use the `repo-conventions` skill
- Blueprint authoring: use the `author-blueprint` skill
- Reusable Terraform (Track B parameterization pass): use the `reusable-terraform` skill
- Torque REST API conventions: use the `zero-touch-api` skill
- `references/known-issues.md` (this skill) — live server-side import bugs, check before Step 11
- `references/track-a-vs-track-b.md` (this skill) — goal-surfacing gate, check before Step 0

## Future Work

- Consider exposing this as a `/import-cloud-resources` command once the interaction shape
  (how grouping/templating questions get asked) is validated on a few more real runs.
- Consider a `scripts/` helper (mirroring `zero-touch-api/scripts/examples/`) once the exact set of
  cloud lookup + import calls this skill makes has stabilized.
- Revisit `references/known-issues.md` for currency before every use — these are live bugs being
  actively worked on and may be fixed.
