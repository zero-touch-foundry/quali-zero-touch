# Known Live Issues — Torque Import Endpoints

**Last confirmed: 2026-09-01.** Issues 1–2 were confirmed 2026-08-27 against the `03-Live` space;
engineering was actively working on both as of that date. Issue 3 was confirmed 2026-09-01 against
the `Quali-IL` space, on a vCenter/vSphere import. Re-verify currency before relying on this
document — check whether a repro still fails the same way before assuming it's fixed, and before
assuming it's still broken.

**Update 2026-09-18:** a full `import_using_blueprint` run against `03-Live` (Azure VM, terraform
grain on the `aks-prod` agent) went straight to `202 Accepted` with no 424 or 500 — confirms the
2026-09-01 note under Issue 2 that this may be account/space-state dependent and now fixed for this
space. The account owner also confirms engineering has since addressed both. Treat Issues 1–2 below
as historical for `03-Live` — still worth a quick repro check before assuming they're fixed
everywhere else.

---

## Swagger drift — `backend` on `ImportGrainRequest` is real despite being absent from swagger

**Confirmed live 2026-09-18**, against `03-Live`. The published swagger
(`https://portal.qtorque.io/swagger/latest/swagger.yaml`) defines
`Quali.Colony.Gateway.Api.Model.Requests.ImportGrainRequest` with `additionalProperties: false` and
**no `backend` property at all** — reading the schema literally says a grain-level `backend` in the
`/environments/import` or `/environments/import_using_blueprint` request body would be rejected or
silently dropped.

**This is wrong.** A real, working example
(`TorqueAPIExamples/import_environment.http` in this account) and a live run both confirm
`grains[].backend` is accepted and honored, using snake_case fields matching the cloud's real
backend config, e.g. for Azure:
```json
"backend": {
  "type": "azurerm",
  "resource_group_name": "azure-northeurope-torque-rg-01",
  "storage_account_name": "torquecuratetfstate",
  "container_name": "terraform",
  "key": "terraform/<grain>/terraform.tfstate"
}
```
No `use_oidc`/`client_id`/`tenant_id` fields are needed or accepted here — auth is resolved via the
selected agent's own ambient identity (e.g. an AKS agent's Azure Workload Identity federated
credential), not passed explicitly in the backend object.

**Practical guidance:** don't treat the live swagger as authoritative for whether `backend` is a
valid field on grain import requests — it's already known to drift (see Issue 2's `workflows`
finding below), and this is a second, independent instance of the same kind of drift. Prefer a real
`.http`/`.json` example from the target account, or a live end-to-end test, over the swagger when
the two disagree specifically on this field.

---

## Issue 1 — `FAILED_TO_AUTOGENERATE_BLUEPRINTS` (HTTP 424) on `POST .../environments/import`

**Symptom:**
```json
{
  "errors": [{
    "message": "Failed to autogenerate blueprints for the following assets: <asset-path>",
    "name": "Failed to autogenerate blueprints",
    "code": "FAILED_TO_AUTOGENERATE_BLUEPRINTS"
  }]
}
```

**Server-side call chain** (confirmed via backend stack trace):
```
EnvironmentController.ImportUsingAutoGenBlueprint
 → EnvironmentService.ImportUsingAutoGenBlueprint
 → ImportService.GenerateBlueprintForImport
 → AutoGenerateBlueprintsService.GenerateBlueprintsFromCandidates
 → AutoGenerateBlueprintsApi.GenerateBlueprints   ← InnerServiceHttpException thrown here
```

`AutoGenerateBlueprintsApi.GenerateBlueprints` calls out to a separate internal service; the
exception surfaced to the API caller is just that inner service's generic failure, forwarded with no
richer detail. **Root cause NOT fully isolated on our side.**

**Hypotheses tested and ruled out** (don't re-test these — they were retried against a live account
and produced the identical error):
- `environment_name` containing spaces/dashes — retried with underscores-only, identical failure.
- A hardcoded `backend` block in the asset's `.tf` source conflicting with the API call's
  `grains[].backend` — retried with the backend block commented out of source, identical failure.
- Splitting `required_providers` and `backend` into two separate `terraform {}` blocks in the same
  file — retried merged into one block, identical failure.
- A separate, unrelated Torque feature (a bot-maintained branch + a `torque-generated-sources/`
  folder with per-resource generated-ID subfolders and a `.torque-generated` marker file) was
  initially suspected as the expected location/shape for this asset. **Confirmed by the Torque team
  to be unrelated** — that structure belongs exclusively to a different, "fully managed" curate flow,
  not to this API path. Auto-generated blueprints produced by this endpoint are stored inside Torque
  itself, not committed to any git branch.

**Practical guidance until fixed:** prefer `import_using_blueprint` (Issue 2 still applies there, but
this specific failure mode does not — it's specific to the auto-generation path).

---

## Issue 2 — `InternalServerError` (HTTP 500) on both `.../environments/import` and `.../environments/import_using_blueprint`

**Symptom:**
```json
{
  "errors": [{
    "message": "could not complete your request because of an internal error",
    "name": "Internal Server Error",
    "code": "InternalServerError"
  }]
}
```

**Root cause — CONFIRMED** via backend stack trace:

```
System.ArgumentNullException: Value cannot be null. (Parameter 'source')
   at System.Linq.Enumerable.Any[TSource](IEnumerable`1 source, Func`2 predicate)
   at EnvironmentWorkflowService.<>c__DisplayClass32_0.<RemoveScheduleForOverridableWorkflowsNotPresentInRequest>b__0(...)
   at EnvironmentWorkflowService.RemoveScheduleForOverridableWorkflowsNotPresentInRequest(
        IEnumerable`1 overridableWorkflows, LaunchWorkflow[] workflowsInRequest, ...)
   at EnvironmentWorkflowService.GetLaunchWorkflows(...)
   at EnvironmentWorkflowService.CreateEnvironmentWorkflowData(...)
   at EnvironmentWorkflowService.AddWorkflows(...)
   at EnvironmentService.Initialize[TLaunchSandbox](...)
   at EnvironmentService.Import(ConsumeContext`1 context)
   at ImportSandboxConsumer.Consume(ConsumeContext`1 context)
```

`RemoveScheduleForOverridableWorkflowsNotPresentInRequest` iterates `overridableWorkflows` (real,
non-empty — workflows the target space/blueprint has marked schedulable/overridable at launch) and
for each one calls `workflowsInRequest.Any(...)`. `workflowsInRequest` (a `LaunchWorkflow[]`) is
**null** on the import code path — `EnvironmentService.Import`'s construction of the internal
`LaunchSandbox` never populates this collection, unlike (presumably) the standard
`POST /environments` launch path.

**Confirmed NOT client-fixable:** checked the live swagger export for both
`ImportEnvironmentFromBlueprintRequest` and the plain `ImportEnvironmentRequest` — neither has a
`workflows` property at all, and both declare `additionalProperties: false`. There is no field on
either request DTO a caller can use to influence `workflowsInRequest`.

**Trigger condition:** the crash fires if and only if `overridableWorkflows` is non-empty — i.e. the
target space/blueprint has **at least one** schedulable/overridable workflow configured, regardless
of which ones, or whether they're individually enabled/disabled (confirmed by testing — toggling
which workflows were enabled did not change the outcome; only "any exist at all" matters, because
LINQ's deferred execution means the crashing predicate is never invoked at all when the source
`.Where()` is iterating an empty collection).

**Practical guidance until fixed:** any import into a space/blueprint with at least one overridable
workflow will 500 regardless of how correct your asset/blueprint/request is. If you need a
success-path repro, target a space/blueprint with **zero** overridable workflows attached (not just
all disabled — genuinely none configured).

**Update 2026-09-01:** an independent import into `03-Live` (an AWS EC2 instance, via
`import_using_blueprint`) went all the way through to `Active` with no 424 or 500 at all — same
call shape that reliably 500'd before. Not confirmed as a fix (could be account/space-state
dependent), but worth re-testing before assuming this is still live.

---

## Known limitation (not a bug) — auto-tagging must be disabled for vCenter/vSphere grains

**Confirmed:** 2026-09-01, against `Quali-IL`, on a vCenter VM import via `import_using_blueprint`.
**This one has a real fix — it is not in the same category as Issues 1–2 above.** First pass at
documenting this wrongly called it an unfixable platform bug; corrected same day once the actual
opt-out was pointed out.

**Symptom:** the environment reaches `Active With Error`; the grain fails specifically at the
`Tagging` stage (after `Prepare`/`Init`/`Import` all succeed), with a generic
`"operation failed. see operation errors"` at the environment level. The real error is only visible
in the stage's own log (`GET /environment/logs/<uuid>` for the `Tagging` activity):

```
$ python3 /tagger/tag_terraform_resources_v2.py ...
[WARNING] Terraform plan failed:
Error: Incorrect attribute value type
  on main_override.tf line 3, in resource "vsphere_virtual_machine" "...":
    tags = {"activity_type" = "other", "torque-environment-id" = "...", ...}
Inappropriate value for attribute "tags": set of string required.
[ERROR] Tagging terraform resources operation has FAILED !!!!!
```

**Root cause:** Torque's post-import tagging step generates an override `.tf` file that injects a
`tags = { <key> = <value>, ... }` map literal into every imported resource, on the assumption that
`tags` is a free-form string-keyed map — true for `aws_instance` and `azurerm_*_virtual_machine`,
but **not** for `vsphere_virtual_machine`: its real schema attribute `tags` is a **set of strings**
(tag-ID references to pre-existing `vsphere_tag` objects in vCenter's separate Tags & Categories
system), not a key-value map at all.

**The fix — disable auto-tagging on the grain, this is a known/documented limitation with an
existing opt-out:**
```yaml
grains:
  <grain_name>:
    kind: terraform
    spec:
      source: {...}
      agent: {...}
      inputs: [...]
      tags:
        auto-tag: false
```
`tags.auto-tag: false` sits directly under the grain's `spec:`, a sibling of `inputs`/`outputs` —
see e.g. `CloudShell 2023_2 GA.yaml` in the `Torque_Bluprints` repo (`Quali-IL`) for the established
real-world precedent. **Any vCenter/vSphere terraform grain should set this proactively** rather
than waiting to hit the Tagging-stage failure first — it's cheap, has no downside for an
already-imported asset (you don't need Torque's auto-generated tracking tags on it), and is the
correct default for this resource type, not a workaround.
