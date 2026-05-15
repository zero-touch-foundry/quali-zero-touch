# Torque REST endpoints used by the plugin

Authoritative URL/method/body table. Paths are written **without** the `/api/` prefix — the helper script adds it. Replace `{...}` placeholders.

Host: from `TORQUE_API_HOST` env var (default `portal.qtorque.io`).
Auth: `Authorization: Bearer $TORQUE_API_TOKEN` on every request.
Body content-type: `application/json` for POST/PUT/PATCH.

Live swagger: <https://portal.qtorque.io/swagger/latest/swagger.yaml>

## Endpoints

| Purpose | Method | Path | Body / Query | Example script |
|---|---|---|---|---|
| List spaces | GET | `/spaces` | — | `get_spaces.py` |
| List blueprints in space | GET | `/spaces/{space}/blueprints` | query `sub_type=workflow` to filter | `get_blueprints.py` |
| List workflows (= blueprints with sub_type=workflow) | GET | `/spaces/{space}/blueprints?sub_type=workflow` | — | `get_blueprints.py --sub-type workflow` |
| Get blueprint YAML (qtorque built-in repo) | GET | `/spaces/{space}/blueprints/{name}/editable` | — | `get_blueprint_yaml.py` |
| Get blueprint YAML (external repo) | GET | `/spaces/{space}/repositories/{repo}/blueprints/{name}/{branch}/files` | — | `get_blueprint_yaml.py --repo --branch` |
| Validate blueprint YAML | POST | `/spaces/{space}/validations/blueprints` | `{"blueprintName": "...", "blueprintRaw64": "<base64-yaml>"}` | `validate_blueprint.py` |
| List catalog items | GET | `/spaces/{space}/catalog` | optional `search`, `only_favorites` | `get_catalog.py` |
| List environments | GET | `/spaces/{space}/environments` | optional `name`, `status` | `get_environments.py` |
| Get environment details (for polling, grain status, debug) | GET | `/spaces/{space}/environments/{env_id}` | — | `get_environment.py` |
| List instantiated workflows on env | GET | `/spaces/{space}/environments/{env_id}/workflows_v2` | — | `get_workflow_instantiations.py` |
| Launch env from registered blueprint | POST | `/spaces/{space}/environments` | see "Launch env body" below | `launch_env.py --from-registered` |
| Launch env from standalone YAML | POST | `/spaces/{space}/environments` | see "Launch env body" below | `launch_env.py --from-standalone` |
| Run day-2 workflow | POST | `/spaces/{space}/environments` | workflow-shaped CreateEnvRequest with `entity_metadata` | `run_workflow.py` |

## Useful endpoints for debug / day-2 (not yet wrapped as example scripts)

| Purpose | Method | Path | Notes |
|---|---|---|---|
| Environment activity feed | GET | `/settings/environmentfeed?sandbox_id={env_id}` | Account-scoped. Richer than `grains[].errors`. Best diagnostic source. |
| Runner / agent info for env | GET | `/spaces/{space}/environments/runner/{env_id}` | Useful for compute-layer errors. |
| List agents in space | GET | `/spaces/{space}/agents` | Confirm referenced agent exists. |
| Reconcile (retry) failed grain | POST | `/spaces/{space}/environments/{env_id}/reconcile` | Body: `{"grains":[{"id":"<grain>"}]}` |
| Update env with new IaC | POST | `/spaces/{space}/environments/{env_id}/update_v2` | |
| Force-terminate stuck env | DELETE | `/spaces/{space}/environments/force/{env_id}` | Irreversible. |
| Export env-as-code YAML | GET | `/spaces/{space}/environments/{env_id}/eac` | |

## Launch env body

`POST /spaces/{space}/environments`:

```json
{
  "environment_name": "my-env",
  "blueprint_name": "my-blueprint",
  "source": { "blueprintName": "my-blueprint", "repositoryName": "qtorque" },
  "base64_standalone_blueprint": null,
  "inputs": { "region": "us-east-1" },
  "owner_email": "user@example.com",
  "duration": "PT2H",
  "scheduled_end_time": null,
  "labels": {}
}
```

Provide **either** `source` (registered) **or** `base64_standalone_blueprint` (inline YAML), not both. For workflow runs, add:

```json
{
  "entity_metadata": {
    "type": "env",                 // or "env_resource"
    "environment_id": "<env-id>",
    "resource_name": "<grain-name>"  // only when type=env_resource
  }
}
```

Time format: ISO-8601. Durations like `PT30M`, `PT2H`. Datetimes like `2026-05-15T18:00:00Z`.

## Response cues

- **Lists** return JSON arrays at the top level (spaces, blueprints, catalog, environments).
- **POST /environments** returns 202 with `{"id": "...", "name": "...", "status": "..."}` (or bare string id in some versions — example scripts handle both).
- **Validate** returns `{"is_valid": bool, "errors": [...], "warnings": [...]}`.
- **Env details** root `status` field is the polling signal (`Active`, `Launching`, `Deployment_Failed`, `Terminated`, ...).
