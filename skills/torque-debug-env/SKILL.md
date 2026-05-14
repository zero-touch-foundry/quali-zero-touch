---
name: torque-debug
description: >
  Use this skill whenever the user wants to debug, investigate, or diagnose a failed, stuck, or
  erroring Torque environment deployment. Triggers include: "my Torque environment failed",
  "environment deployment failed", "why did my environment fail", "debug Torque environment",
  "environment stuck in deploying", "grain failed", "Torque error", "help me fix my environment",
  "environment error", "deployment error in Torque", "my blueprint deployment failed", "Torque shows
  error", "check environment logs", "investigate environment failure", "environment not becoming active".
  The user will typically provide a Torque environment URL (which encodes the space name and environment
  ID) and an API token. Claude will use the Torque REST API to automatically fetch environment state,
  iterate over grains, identify failures, retrieve the activity feed log, and provide expert diagnosis
  and fix steps. Always use this skill when asked about a failing Torque environment — never rely on
  memory alone; always fetch live data first.
---

# Torque Environment Debugger — SKILL.md

## API Reference
Live Swagger spec (always fetch to check for new endpoints):
`https://portal.qtorque.io/swagger/latest/swagger.yaml`

---

## Step 1 — Collect Connection Details

### Parse from a URL (preferred)
Torque environment URLs have the form:
```
https://portal.qtorque.io/<space_name>/environments/<environment_id>
https://<account>.qtorque.io/<space_name>/environments/<environment_id>
```
Extract: **hostname**, **space_name**, **environment_id**.

### Manual fallback
Ask the user for:
- **API token** — generated at: Help → Community Integrations → any CI tool → Configure → Generate New Token, or using the API documentation page at https://portal.qtorque.io/api_reference
- **Space name**
- **Environment ID**

All API calls use:
```
Authorization: Bearer <token>
Content-Type: application/json
```

---

## Step 2 — Fetch Environment Details

### Call A — Get environment details (primary)
```
GET https://{hostname}/api/spaces/{space_name}/environments/{environment_id}
```
Returns: `EnvironmentResponse` — the single most important call. Contains overall status, blueprint
name, all grain statuses, grain errors, outputs, inputs used.

**Key fields to extract from the response:**
- `status` — overall environment status string (e.g. `Launching`, `Active`, `Deployment_Failed`, `Terminated`)
- `details.errors` — top-level error list if any
- `grains[]` — array of grain objects, each containing:
  - `name` — grain name as defined in the blueprint
  - `kind` — grain type (`terraform`, `helm`, `shell`, `kubernetes`, etc.)
  - `status` — per-grain status
  - `errors[]` — per-grain error messages (the most useful field for diagnosis)
  - `progress` — deployment progress percentage
  - `depends_on` / `depends-on` — dependency chain

### Call B — Get activity feed log (secondary, very useful)
```
GET https://{hostname}/api/settings/environmentfeed?sandbox_id={environment_id}
```
Returns: array of `EnvironmentFeedResponse` — this is exactly what the Torque UI shows in the
environment's activity/event feed. Contains timestamped events, grain-level log messages, and
error details that may be richer than the grain `errors[]` field alone.

**This endpoint is account-scoped (not space-scoped) and takes `sandbox_id` as a query param.**

### Call C — Get runner info (if agent/runner issues are suspected)
```
GET https://{hostname}/api/spaces/{space_name}/environments/runner/{environment_id}
```
Returns runner pod and agent information. Useful when the error points to the compute layer.

### Call D — List agents in space (if agent-not-found errors appear)
```
GET https://{hostname}/api/spaces/{space_name}/agents
```
Returns all agents associated with the space — confirms whether the agent referenced in the
blueprint actually exists and is available.

---

## Step 3 — Identify the Failing Grain

Scan the `grains[]` array from Call A. Look for:
- `status` containing: `Failed`, `Error`, `Timeout`, `Deployment_Failed`, `Inactive`, `Launching` (stalled)
- Non-empty `errors[]` arrays on any grain
- Grains with `progress` stuck at the same value for a long time

**Determine root cause vs downstream failures:**
Grains that use `depends-on` referencing a failed grain will themselves fail. Always trace back
to the grain with no upstream dependency that failed — that is the root cause.

Visualize the chain before diagnosing:
```
infra (❌ FAILED) ──depends-on──> app (❌ blocked) ──depends-on──> monitoring (❌ blocked)
                                                                    ↑ diagnose only infra
```

---

## Step 4 — Diagnose the Error

Match the error text from `grains[].errors[]` or the activity feed against these patterns:

### 4A — Torque Platform / Blueprint Errors
Source: Torque control plane itself, before any IaC runs.

| Error pattern | Meaning | Fix |
|---|---|---|
| `failed to parse blueprint` / `invalid yaml` | YAML syntax error in blueprint | Fix YAML; use `POST /api/spaces/{space}/validations/blueprints` to validate |
| `input X is required` | A required blueprint input was not supplied | Pass all required inputs at launch |
| `grain X not found` (in depends-on) | `depends-on` references a grain name that doesn't exist | Fix grain name in blueprint YAML |
| `circular dependency detected` | Grains form a dependency loop | Restructure `depends-on` to be a DAG |
| `blueprint not found` / `repository not found` | Wrong blueprint name or repo not connected to space | Check Space → Repositories |
| `policy denied` / `Denied by policy` | A governance policy (OPA) blocked the launch | Check Space → Policies; review policy rules |
| `approval required` | A `Manual` policy decision is pending | Approve from the Torque UI |
| `template rendering failed` / `liquid` error | A `{{ }}` Liquid expression in the blueprint resolved to null or wrong type | Check input types; verify `{{ .inputs.x }}` exists |

### 4B — Agent / Runner Errors
Source: The Kubernetes runner pod that executes the grain.

| Error pattern | Meaning | Fix |
|---|---|---|
| `agent X not found` / `no agent available` | Agent name in blueprint doesn't match any agent in the space | Check `GET /api/spaces/{space}/agents`; fix agent name in blueprint |
| `failed to schedule runner pod` / `pod pending` | Kubernetes cluster has insufficient resources | Check node capacity; scale the cluster |
| `service account not found` | `service-account:` in blueprint spec doesn't exist in the runner namespace | Create the service account in K8s or fix its name |
| `namespace X not found` | `runner-namespace` or `target-namespace` does not exist | Create the namespace in Kubernetes or use an existing one |
| `image pull failed` / `ErrImagePull` / `ImagePullBackOff` | Container image for the runner can't be pulled | Check image registry credentials; verify network access from the cluster |
| `OOMKilled` | Runner pod was killed for exceeding memory limits | Increase `storage-size` or node memory; simplify the operation |
| `context deadline exceeded` / `runner timeout` | Agent lost connectivity or pod timed out | Check agent health; look at Kubernetes events for the runner pod |

### 4C — Authentication / Credential Errors
Source: Cloud provider APIs rejecting requests.

| Error pattern | Meaning | Fix |
|---|---|---|
| AWS: `NoCredentialProviders` / `AccessDenied` / `UnauthorizedException` | IAM role or credentials not configured | Check Space → Credentials; verify IAM role ARN and trust policy |
| Azure: `AuthorizationFailed` / `InvalidClientSecret` | Service principal expired or has wrong permissions | Rotate the service principal secret; check RBAC role assignments |
| GCP: `PERMISSION_DENIED` / `UNAUTHENTICATED` | Service account key invalid or missing IAM roles | Regenerate the service account key; add required IAM roles |
| Generic: `credential not found` | The credential name in the blueprint doesn't match any credential in the space | Check Space → Credentials; fix the credential name |
| `403 Forbidden` from cloud | IAM role lacks permission for the operation | Add the required permission to the IAM policy |

### 4D — Terraform / OpenTofu / Terragrunt Errors
Source: Terraform/OpenTofu `plan` or `apply` output.

| Error pattern | Meaning | Fix |
|---|---|---|
| `Error: configuring Terraform AWS Provider` | Provider authentication failed | Fix credentials (see 4C above) |
| `Error: Invalid function argument` / `Unsupported attribute` | HCL code bug in the module | Fix the `.tf` source code |
| `Error creating <resource>` | Cloud API rejected the resource create — read the message after this for cloud reason | Fix inputs or cloud-side config (quota, naming, region, etc.) |
| `Error: Cycle` | Terraform-level dependency loop in the module | Refactor the Terraform module |
| `Error acquiring the state lock` | Another process holds the state lock (crashed previous run) | Manually run `terraform force-unlock` or unlock via cloud backend console |
| `Resource already exists` / `AlreadyExistsException` | A resource with the same name was created outside Torque or by a previous run | Import it into state or rename in the blueprint inputs |
| `quota exceeded` / `LimitExceeded` / `ServiceQuotaExceededException` | Cloud service quota hit | Request a quota increase or change region/size |
| `Invalid value for input variable` | Wrong type or value passed to the Terraform module | Fix input values in the blueprint or the launch request |
| Transient errors (rate limits, retries) | Torque auto-retries these for Terraform grains | If it keeps failing, check drift-and-update docs for disabling auto-retry |

### 4E — Helm Errors
Source: Helm chart deployment output.

| Error pattern | Meaning | Fix |
|---|---|---|
| `Error: failed to download` / `chart not found` | Helm chart can't be fetched | Verify `store:` and `path:` in blueprint; check chart repo connectivity from the agent |
| `Error: UPGRADE FAILED: cannot patch` | Kubernetes refuses to patch an existing resource | Delete the conflicting resource, or use helm rollback and redeploy |
| `rendered manifests contain a resource that already exists` | Resource exists outside this Helm release | Delete the pre-existing resource or adopt it |
| `ImagePullBackOff` / `CrashLoopBackOff` | Application pod failing — not Torque's fault | Check pod logs inside Kubernetes directly |
| `Error: timed out waiting for the condition` | Helm waited too long for pods to become ready | Investigate pod events; check readiness probe configuration |

### 4F — Shell / Script Errors
Source: Shell grain or script hooks (`pre-tf-init`, `post-helm-install`, etc.).

| Error pattern | Meaning | Fix |
|---|---|---|
| Non-zero exit code (e.g. `exit status 1`) | Script failed — read the command output above for the actual error | Debug the script commands |
| `command not found` | A tool the script needs is not installed on the agent | Add installation step to `deploy.commands`, or use a custom agent image |
| `Permission denied` | Script file not executable, or accessing a path it shouldn't | Add `chmod +x` or fix the path |
| `No such file or directory` | Wrong path in `source:` or `workspace-directories` not configured | Fix path or add `workspace-directories` to checkout the correct repo |

### 4G — Kubernetes / ArgoCD Errors
Source: `kubectl apply` or ArgoCD sync.

| Error pattern | Meaning | Fix |
|---|---|---|
| `unable to recognize` / `no kind is registered` | Manifest uses an API version not supported by the cluster | Update `apiVersion` in the manifest, or upgrade the K8s cluster |
| `namespaces ... not found` | `target-namespace:` doesn't exist | Create the namespace first (add a shell grain dependency), or use an existing one |
| `Forbidden` / `RBAC` errors | Service account can't create/delete the resources in the manifest | Grant the service account the required ClusterRole or Role |
| ArgoCD: `ComparisonError` / `OutOfSync` | ArgoCD app configuration mismatch | Check the ArgoCD app definition and source path |

### 4H — Network / Repository Errors
Source: Agent trying to reach external services.

| Error pattern | Meaning | Fix |
|---|---|---|
| `unable to clone repository` / `authentication required` | Git repo not reachable or token expired | Check repo access; rotate the Git provider token in Torque settings |
| `connection refused` / `dial tcp: i/o timeout` | Agent can't reach a cloud endpoint or private service | Check VPC routing, security groups, firewall rules from the agent's cluster |
| `certificate signed by unknown authority` | TLS certificate not trusted | Add the CA cert to the agent, or use a valid public cert |

---

## Step 5 — Output Format

Present findings as:

### 🔍 Environment Summary
- **Environment**: `<name>` (`<id>`)
- **Space**: `<space_name>`
- **Status**: `<overall status>`
- **Blueprint**: `<blueprint name>`
- **Grains**: `<N> total, <M> failed`

### ❌ Failing Grain(s)
For each failing grain (root cause first):
```
Grain:   <grain_name>  (kind: <grain_type>)
Status:  <grain status>
Error:
  <exact error text from API — preserve all whitespace and newlines>
```

### 🧠 Root Cause Analysis
Plain-English explanation:
- Which layer caused it (Torque / Agent / IaC / Cloud / Network)
- Why it happened
- If downstream grains also failed because of this one — note which ones are cascading failures

### 🛠️ Fix Steps
Numbered, specific, actionable steps to resolve the issue. Include:
- Exact location to look (Torque UI path, config file, cloud console)
- What to change
- Whether to retry the environment or make changes first

To retry a grain after fixing without restarting the whole environment:
```
POST https://{hostname}/api/spaces/{space_name}/environments/{environment_id}/reconcile
Body: { "grains": [{ "id": "<grain_name>" }] }
```

### 💡 Prevention (if relevant)
Brief tips to avoid recurrence.

---

## Step 6 — Handling API Errors

| HTTP code | Meaning | Action |
|---|---|---|
| `401` | Token invalid or expired | Generate a new long token at Space → Settings → Integrations → Generate New Token |
| `403` | Token lacks access to this space | User needs at least Viewer role in the space |
| `404` on environment | Wrong ID or space name, or environment already terminated | Double-check URL; confirm env still exists in the UI |
| `424` | Cloud account not accessible | The cloud credential linked to the space is broken; check Space → Cloud Accounts |

If **no `errors[]`** are populated but the environment has failed status, the activity feed (Call B)
will usually have the details. Parse the feed entries chronologically and look for events with
failure-related messages.

If **API access is unavailable entirely**, ask the user to:
1. Open the environment in the Torque UI
2. Click the failed grain
3. Open the "Logs" or "Activity" tab
4. Copy-paste the error text here for analysis

---

## Step 7 — Multi-Grain Triage Order

1. Fetch all grains from the environment response
2. Build the dependency graph from `depends-on` fields
3. Find grains with no upstream `depends-on` that failed — start triage there
4. A grain that failed only because its dependency failed is a **cascading failure**, not the root cause
5. Only diagnose and suggest fixes for the **root cause grain(s)**
6. Mention downstream failures briefly: *"Grains X and Y also failed as a result of this"*

---

## Useful Related Endpoints

| Action | Endpoint |
|---|---|
| Retry (reconcile) a failed grain | `POST /api/spaces/{space}/environments/{env_id}/reconcile` |
| Restart a grain with updated IaC | `POST /api/spaces/{space}/environments/{env_id}/update_v2` |
| Force-terminate a stuck environment | `DELETE /api/spaces/{space}/environments/force/{env_id}` |
| Validate a blueprint before launch | `POST /api/spaces/{space}/validations/blueprints` |
| List agents available in space | `GET /api/spaces/{space}/agents` |
| Export the live environment YAML | `GET /api/spaces/{space}/environments/{env_id}/eac` |
| Get environment list for a space | `GET /api/spaces/{space}/environments` (via operation hub: `GET /api/operation_hub`) |
