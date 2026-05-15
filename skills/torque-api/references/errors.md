# Torque API error handling

The helper script (`torque_api.py`) raises typed exceptions and the CLI prints `ERROR HTTP <code>` to stderr with the body. Skills should map these to user-facing fixes.

## Status codes

| HTTP | Exception (`torque_api.py`) | Meaning | What to surface to user |
|---|---|---|---|
| 401 | `TorqueAuthError` | Token missing, invalid, or expired | "Regenerate token at `<host>/my-token`. Re-run `configure --token-stdin` with the new value." |
| 403 | `TorqueForbidden` | Token scope insufficient (e.g. space token used for account-wide call) | "Use a personal API token, or scope the space token to the correct space." |
| 404 | `TorqueNotFound` | Space / env / blueprint name wrong, or resource already deleted | "Double-check the name. List spaces with `get_spaces.py` to confirm." |
| 400, 422 | `TorqueValidationError` | Bad request body or params (e.g. missing required input on launch) | Echo the `errors[]` array — usually has field paths. |
| 424 | `TorqueError` | Cloud account linked to space not accessible | "Check Space → Cloud Accounts; credential probably broken." |
| 0 (network) | `TorqueError` with status=0 | DNS / TLS / connection refused | "Check `TORQUE_API_HOST` (currently `<host>`). Confirm VPN / firewall." |

## Network-layer pitfalls

- **TLS errors**: check system clock skew first.
- **Proxy**: `urllib.request` respects `HTTPS_PROXY` / `HTTP_PROXY` env vars. If user is behind a corporate proxy, those must be set.
- **Self-hosted Torque**: `TORQUE_API_HOST` must be the host only (no `https://`, no trailing slash). Example: `tenant.internal.example.com`.

## When debugging

To inspect a raw failing call without changing skill code, run:

```bash
python skills/torque-api/scripts/torque_api.py GET /spaces/MYSPACE/environments
```

The CLI prints the parsed body for 2xx and writes `ERROR HTTP <code>` + body to stderr for non-2xx.

## What NOT to do

- Do not retry on 401/403 — token problems don't fix themselves. Surface immediately.
- Do not silently swallow `TorqueValidationError` — its body contains the user's actionable fix.
- Do not hardcode `https://portal.qtorque.io` in any script or skill. Always go through the helper so the host resolution chain is honored.
- Do not put a raw token in argv (`configure --token "<value>"`) — it leaks into shell history and Claude transcripts. Always use `--token-stdin` with `printf '%s' "<token>" | ... configure --token-stdin`.
