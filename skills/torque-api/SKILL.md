---
name: torque-api
description: >
  Canonical reference for calling the Torque REST API directly from skills.
  Use this skill whenever another skill needs to fetch from or post to Torque
  (list spaces / blueprints / environments / catalog, validate or launch
  blueprints, run workflows, inspect grain status for debugging) and you need
  to know the exact endpoint, payload shape, response structure, or error
  semantics. Also use when extending the plugin with a new Torque API
  operation — this skill documents the conventions every example script
  must follow.
---

# Torque API helper

This skill is **infrastructure for other skills**. It centralizes:

1. A stdlib-only Python helper (`scripts/torque_api.py`) that handles auth, host resolution, JSON encoding, and typed error mapping.
2. A library of thin per-endpoint example scripts under `scripts/examples/`.
3. References that describe endpoint paths, request/response shapes, and error semantics.

Every Torque-skill in this plugin calls Torque through these scripts. **No raw `curl` or `urllib` calls anywhere else in the plugin.**

## Quick start (when invoking from another skill)

1. Confirm `TORQUE_API_TOKEN` is set (skills should do a `test -n "$TORQUE_API_TOKEN"` pre-flight; `command-torque-quickstart` walks new users through this).
2. Pick the right example script from the table in `references/endpoints.md`.
3. Run it via Bash:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/get_environments.py" --space my-space
   ```

   (Or from a clone of the repo, the relative `skills/torque-api/scripts/examples/...` path.)

4. The script prints JSON to stdout on success and `ERROR HTTP <code>` + body to stderr on failure (non-zero exit code).
5. Parse the JSON, use `references/response_shapes.md` to know which fields to surface, use `references/errors.md` to map error codes to user-facing fixes.

## Direct helper usage (ad-hoc calls)

For endpoints not yet wrapped in an example script, call the helper CLI directly:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/torque_api.py" \
  GET /spaces/my-space/environments

python "${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/torque_api.py" \
  POST /spaces/my-space/validations/blueprints \
  --body '{"blueprintName":"foo","blueprintRaw64":"c3BlY192ZXJzaW9uOiAyCg=="}'
```

The helper:
- reads `TORQUE_API_TOKEN` and `TORQUE_API_HOST` (default `portal.qtorque.io`),
- auto-prepends `/api/` to the path (write `/spaces`, not `/api/spaces`),
- maps 401/403/404/422 to typed exceptions / stderr messages.

## Files

```
skills/torque-api/
├── SKILL.md                          ← this file
├── scripts/
│   ├── torque_api.py                 ← helper. CLI + importable (request, exceptions)
│   └── examples/                     ← one file per endpoint, all ~20 lines
│       ├── get_spaces.py
│       ├── get_blueprints.py
│       ├── get_blueprint_yaml.py
│       ├── validate_blueprint.py
│       ├── get_catalog.py
│       ├── get_environments.py
│       ├── get_environment.py
│       ├── get_workflow_instantiations.py
│       ├── launch_env.py
│       ├── run_workflow.py
│       └── get_grain_usage_examples.py
└── references/
    ├── endpoints.md                  ← URL table, body shapes for POSTs
    ├── response_shapes.md            ← truncated example responses, fields to parse
    └── errors.md                     ← status code → exception → user-facing fix
```

## Conventions for example scripts

When the user (or another agent) adds a new endpoint:

1. **Helper, not duplication.** Always go through `from torque_api import request, TorqueError`. Never call `urllib.request` directly.
2. **Argparse for inputs.** Required args use `required=True`. Don't read from `sys.argv` directly.
3. **JSON to stdout, errors to stderr.** Print `json.dumps(parsed, indent=2)` on success. On any `TorqueError`, print `ERROR HTTP <status>: <body>` to stderr and `return 1`.
4. **No external deps.** Stdlib only (`json`, `argparse`, `urllib`, `base64`, `re`, `pathlib`). Plugin must work on a vanilla Python 3.8+ install.
5. **Path style.** Write paths starting with `/spaces/...` — helper adds `/api/`. Never hardcode the host.
6. **One file per logical operation.** If an operation needs multiple calls (e.g. `get_grain_usage_examples` = list catalog + N×fetch YAML + regex), one script that orchestrates them is fine.

## Extension recipe (adding a new Torque API operation)

1. Find the endpoint in the [swagger spec](https://portal.qtorque.io/swagger/latest/swagger.yaml).
2. Add a row to `references/endpoints.md` with method, path, body / query, and the script filename you'll create.
3. Add a top-level response shape to `references/response_shapes.md` (truncated example + which fields callers usually parse).
4. Write `scripts/examples/<verb>_<resource>.py` following the conventions above.
5. From the consuming skill (or a new one), reference the script with its `${CLAUDE_PLUGIN_ROOT}/skills/torque-api/scripts/examples/...` path.

No edits to `torque_api.py` are needed unless a new auth mechanism or transport (e.g. SSE) is required.

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `TORQUE_API_TOKEN` | Bearer token. **Required.** | — |
| `TORQUE_API_HOST` | Hostname only (no scheme, no path). | `portal.qtorque.io` |
| `HTTPS_PROXY` / `HTTP_PROXY` | Honored automatically by `urllib`. | — |

For self-hosted / dedicated Torque tenants: `export TORQUE_API_HOST="tenant.example.com"`.

## What this skill does NOT do

- No pagination handling — each example script issues a single request. Endpoints that paginate (catalog when filtered, environments with `paging_info.skip/take`) need per-script logic if/when needed.
- No retry / backoff — if you need polling (e.g. wait for an env to become `Active`), write the loop in the calling skill or in a dedicated script. The helper is raw HTTP.
- No caching — every call hits the API.
