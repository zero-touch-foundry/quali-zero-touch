#!/usr/bin/env python3
"""Torque REST API helper. Stdlib only.

Modes:
  CLI request:   python torque_api.py GET /spaces
                 python torque_api.py POST /spaces/foo/validations/blueprints --body '{...}'
  CLI configure: python torque_api.py configure --token TOK [--host HOST] [--profile NAME]
                 python torque_api.py configure --show | --list
                 python torque_api.py configure --set-default NAME
                 python torque_api.py configure --clear [NAME]
  Import:        from torque_api import request, TorqueError
                 data = request("GET", "/spaces")

Profiles (multi-account):
  An alias names a (token, host) pair. Single-account users never see profiles —
  the first credential written lands in 'default' and is used automatically.
  Add more with `configure --profile stackautomation ...`; select per call with
  `--profile` on the helper CLI, or the TORQUE_PROFILE env var (which the example
  scripts inherit, since they all route through this helper).

Credential resolution order:
  Profile: --profile flag → TORQUE_PROFILE env → config `default =` marker
           → the sole profile → 'default'
  Token:   TORQUE_API_TOKEN env var → selected profile's `token` → error
  Host:    TORQUE_API_HOST  env var → selected profile's `host`  → portal.qtorque.io

Config file path (in order):
  $TORQUE_CONFIG_FILE                                          (escape hatch)
  $XDG_CONFIG_HOME/quali-zero-touch/config  or  ~/.config/quali-zero-touch/config  (Unix)
  %APPDATA%\\quali-zero-touch\\config                                (Windows)

Format (sectioned INI; legacy flat files without a section read as 'default'):
  default = stackautomation

  [default]
  token = eyJhbGciOi...
  host  = portal.qtorque.io

  [stackautomation]
  token = eyJ...
  host  = stackautomation.cisco.com

Paths may be given with or without the leading "/api/" — both work.
Responses are parsed as JSON when Content-Type allows; otherwise text is returned.
Errors raise typed exceptions (TorqueAuthError, TorqueForbidden,
TorqueNotFound, TorqueValidationError, TorqueError) carrying status + body.

Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, Optional, Tuple, Union


DEFAULT_HOST = "portal.qtorque.io"


class TorqueError(Exception):
    """Base class. Carries HTTP status and raw response body."""

    def __init__(self, status: int, body: Any, message: str = ""):
        self.status = status
        self.body = body
        super().__init__(message or f"HTTP {status}: {body!r}")


class TorqueAuthError(TorqueError):
    """401 — token missing, invalid, or expired."""


class TorqueForbidden(TorqueError):
    """403 — token scope insufficient."""


class TorqueNotFound(TorqueError):
    """404 — resource (space, env, blueprint) missing."""


class TorqueValidationError(TorqueError):
    """422 / 400 — bad request body or params."""


def _config_path() -> str:
    override = os.environ.get("TORQUE_CONFIG_FILE")
    if override:
        return override
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "quali-zero-touch", "config")


DEFAULT_PROFILE = "default"


def _read_config() -> Dict[str, Any]:
    """Parse the config file into profiles.

    Returns {"profiles": {name: {"token": ..., "host": ...}}, "default": name}.

    Two on-disk shapes are accepted:
      * Legacy flat (no section): bare `token = ` / `host = ` lines map to the
        `default` profile. Existing single-token files keep working untouched.
      * Sectioned INI: `[alias]` headers, each with its own token/host. A bare
        `default = <alias>` line (before any section) marks the active profile.
    """
    path = _config_path()
    profiles: Dict[str, Dict[str, str]] = {}
    default_name = ""
    if not os.path.isfile(path):
        return {"profiles": profiles, "default": default_name}
    current = DEFAULT_PROFILE  # bare keys land in 'default'
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current = line[1:-1].strip().lower()
                    profiles.setdefault(current, {})
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "default" and current == DEFAULT_PROFILE and not profiles.get(DEFAULT_PROFILE):
                    # top-level default marker (only meaningful outside a section)
                    default_name = v.lower()
                    continue
                profiles.setdefault(current, {})[k] = v
    except OSError:
        return {"profiles": {}, "default": ""}
    # drop an empty 'default' profile created by a stray default= marker
    if DEFAULT_PROFILE in profiles and not profiles[DEFAULT_PROFILE]:
        del profiles[DEFAULT_PROFILE]
    return {"profiles": profiles, "default": default_name}


def _resolve_profile_name(cfg: Mapping[str, Any], requested: str = "") -> str:
    """Pick which profile to use: explicit → TORQUE_PROFILE env → config default
    marker → the sole profile → 'default'."""
    profiles = cfg.get("profiles", {})
    name = (requested or os.environ.get("TORQUE_PROFILE", "")).strip().lower()
    if name:
        return name
    if cfg.get("default"):
        return cfg["default"]
    if len(profiles) == 1:
        return next(iter(profiles))
    return DEFAULT_PROFILE


def _active_profile(requested: str = "") -> Dict[str, str]:
    cfg = _read_config()
    name = _resolve_profile_name(cfg, requested)
    return cfg.get("profiles", {}).get(name, {})


# Set by the CLI (--profile) so imported example scripts inherit the choice.
_PROFILE_OVERRIDE = ""


def _write_config(profiles: Mapping[str, Mapping[str, str]], default_name: str = "") -> str:
    """Write the sectioned config file with chmod 600 on POSIX. Returns path."""
    path = _config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = []
    if default_name:
        lines.append(f"default = {default_name}")
        lines.append("")
    for name, vals in profiles.items():
        lines.append(f"[{name}]")
        for k, v in vals.items():
            if v:
                lines.append(f"{k} = {v}")
        lines.append("")
    text = "\n".join(lines).rstrip("\n") + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    finally:
        if os.name != "nt":
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    return path


def _host() -> str:
    env = os.environ.get("TORQUE_API_HOST", "").strip()
    if env:
        return env.rstrip("/")
    cfg = _active_profile(_PROFILE_OVERRIDE).get("host", "").strip()
    if cfg:
        return cfg.rstrip("/")
    return DEFAULT_HOST


def _token() -> str:
    tok = os.environ.get("TORQUE_API_TOKEN", "").strip()
    if not tok:
        tok = _active_profile(_PROFILE_OVERRIDE).get("token", "").strip()
    if not tok:
        raise TorqueAuthError(
            0,
            None,
            "Torque API token not configured. Run the credential gate before any "
            "API call: invoke the `zero-touch-quickstart` skill to collect and "
            "persist a token (writes the config file via `configure --token-stdin`). "
            "Do not pass a token inline per call — it won't persist and leaks into "
            "the transcript. Check state with `torque_api.py configure --show`.",
        )
    return tok


def _normalize_path(path: str) -> str:
    p = path.strip()
    if p.startswith("http://") or p.startswith("https://"):
        return p
    if not p.startswith("/"):
        p = "/" + p
    if not p.startswith("/api/"):
        p = "/api" + p
    return p


def _build_url(path: str, query: Optional[Mapping[str, Any]] = None) -> str:
    p = _normalize_path(path)
    if p.startswith("http"):
        url = p
    else:
        url = f"https://{_host()}{p}"
    if query:
        flat = []
        for k, v in query.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                for item in v:
                    flat.append((k, str(item)))
            else:
                flat.append((k, str(v)))
        if flat:
            sep = "&" if "?" in url else "?"
            url = url + sep + urllib.parse.urlencode(flat)
    return url


def _raise_for_status(status: int, body: Any) -> None:
    if 200 <= status < 300:
        return
    if status == 401:
        raise TorqueAuthError(status, body)
    if status == 403:
        raise TorqueForbidden(status, body)
    if status == 404:
        raise TorqueNotFound(status, body)
    if status in (400, 422):
        raise TorqueValidationError(status, body)
    raise TorqueError(status, body)


def request(
    method: str,
    path: str,
    body: Any = None,
    query: Optional[Mapping[str, Any]] = None,
    timeout: float = 60.0,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> Tuple[int, Union[Any, str]]:
    """Make one Torque API call. Returns (status, parsed_body).

    body: dict/list → JSON-encoded. str/bytes → sent as-is.
    On non-2xx, raises a typed TorqueError subclass.
    """
    url = _build_url(path, query)
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/json",
        "User-Agent": "TorqueAgentCalls/1.0",
    }
    data: Optional[bytes] = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif isinstance(body, str):
            data = body.encode("utf-8")
        elif isinstance(body, bytes):
            data = body
        else:
            raise TypeError(f"Unsupported body type: {type(body).__name__}")
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
            parsed = _parse_body(raw, resp.headers.get("Content-Type", ""))
            _raise_for_status(status, parsed)
            return status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read()
        parsed = _parse_body(raw, e.headers.get("Content-Type", "") if e.headers else "")
        _raise_for_status(e.code, parsed)
        return e.code, parsed  # unreachable
    except urllib.error.URLError as e:
        raise TorqueError(0, None, f"Network error contacting {url}: {e.reason}") from e


def _parse_body(raw: bytes, content_type: str) -> Union[Any, str]:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    ct = (content_type or "").lower()
    if "json" in ct or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


# ---- CLI ----

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _mask_token(tok: str) -> str:
    if not tok:
        return "(unset)"
    if len(tok) <= 8:
        return "***"
    return f"{tok[:4]}…{tok[-4:]}"


def _cli_configure(argv: list) -> int:
    p = argparse.ArgumentParser(
        prog="torque_api.py configure",
        description="Write Torque credentials to the plugin config file.",
    )
    p.add_argument("--token", help="Torque API bearer token")
    p.add_argument("--host", help="Torque API hostname (no scheme). Default: portal.qtorque.io")
    p.add_argument(
        "--profile",
        default="",
        help="Named profile (alias for a token+host pair). Omit to use the default profile. "
        "Use this to store more than one account/target.",
    )
    p.add_argument("--show", action="store_true", help="Print current config (tokens masked) and exit")
    p.add_argument("--list", action="store_true", help="List configured profiles and exit")
    p.add_argument("--set-default", metavar="PROFILE", help="Mark a profile as the default and exit")
    p.add_argument(
        "--clear",
        nargs="?",
        const="\0ALL",
        metavar="PROFILE",
        help="Delete a profile, or the whole config file if no profile given",
    )
    p.add_argument(
        "--token-stdin",
        action="store_true",
        help="Read token from stdin (avoids leaking it into shell history)",
    )
    args = p.parse_args(argv)

    path = _config_path()
    cfg = _read_config()
    profiles: Dict[str, Dict[str, str]] = cfg["profiles"]
    default_name = cfg["default"]

    if args.set_default:
        name = args.set_default.strip().lower()
        if name not in profiles:
            print(f"No such profile: {name}. Configured: {', '.join(profiles) or '(none)'}", file=sys.stderr)
            return 2
        _write_config(profiles, name)
        print(f"Default profile set to '{name}'.")
        return 0

    if args.clear is not None:
        if args.clear == "\0ALL":
            if os.path.isfile(path):
                os.remove(path)
                print(f"Removed {path}")
            else:
                print(f"No config file at {path}")
            return 0
        name = args.clear.strip().lower()
        if name not in profiles:
            print(f"No such profile: {name}", file=sys.stderr)
            return 2
        del profiles[name]
        if default_name == name:
            default_name = ""
        _write_config(profiles, default_name)
        print(f"Removed profile '{name}'.")
        return 0

    if args.list:
        print(f"Config file: {path}")
        if not profiles:
            print("  (no profiles configured)")
        active = _resolve_profile_name(cfg)
        for name, vals in profiles.items():
            marks = []
            if name == default_name:
                marks.append("default")
            if name == active:
                marks.append("active")
            suffix = f"  [{', '.join(marks)}]" if marks else ""
            print(f"  {name}: host={vals.get('host') or DEFAULT_HOST}{suffix}")
        return 0

    if args.show:
        active = _resolve_profile_name(cfg)
        vals = profiles.get(active, {})
        print(f"Config file: {path}")
        print(f"  profile = {active}" + (" (default)" if active == default_name else ""))
        print(f"  token   = {_mask_token(vals.get('token', ''))}")
        print(f"  host    = {vals.get('host', '') or DEFAULT_HOST + ' (default)'}")
        if len(profiles) > 1:
            print(f"  (other profiles: {', '.join(n for n in profiles if n != active)})")
        env_tok = os.environ.get("TORQUE_API_TOKEN", "")
        env_host = os.environ.get("TORQUE_API_HOST", "")
        env_prof = os.environ.get("TORQUE_PROFILE", "")
        if env_tok or env_host or env_prof:
            print("Env overrides (take precedence):")
            if env_prof:
                print(f"  TORQUE_PROFILE   = {env_prof}")
            if env_tok:
                print(f"  TORQUE_API_TOKEN = {_mask_token(env_tok)}")
            if env_host:
                print(f"  TORQUE_API_HOST  = {env_host}")
        return 0

    token = args.token
    if args.token_stdin:
        token = sys.stdin.read().strip()
    if not token and not args.host:
        print("Nothing to write. Provide --token / --token-stdin and/or --host.", file=sys.stderr)
        return 2

    # Which profile are we writing to? Explicit --profile, else the resolved
    # default. First-ever write with no --profile lands in 'default'.
    target = (args.profile or "").strip().lower() or _resolve_profile_name(cfg)
    entry = dict(profiles.get(target, {}))
    if token:
        entry["token"] = token
    if args.host:
        entry["host"] = args.host.strip().rstrip("/")
    profiles[target] = entry
    # First profile written becomes the default automatically.
    if not default_name:
        default_name = target
    written = _write_config(profiles, default_name)
    print(f"Wrote {written}")
    print(f"  profile = {target}" + (" (default)" if target == default_name else ""))
    if "token" in entry:
        print(f"  token   = {_mask_token(entry['token'])}")
    if "host" in entry:
        print(f"  host    = {entry['host']}")
    return 0


def _cli_request(argv: list) -> int:
    p = argparse.ArgumentParser(prog="torque_api.py", description="Torque REST API helper")
    p.add_argument("method", help="HTTP method (GET, POST, PUT, PATCH, DELETE)")
    p.add_argument("path", help="API path, e.g. /spaces or /spaces/foo/environments")
    p.add_argument(
        "--body",
        help="Request body as JSON string, or @file.json to read from file",
        default=None,
    )
    p.add_argument(
        "--query",
        action="append",
        default=[],
        help="Query param key=value (repeatable). e.g. --query sub_type=workflow",
    )
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument(
        "--profile",
        default="",
        help="Use a named credential profile (set via `configure --profile`). "
        "Omit to use the default profile.",
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="Print response without pretty-printing",
    )
    args = p.parse_args(argv)

    if args.profile:
        global _PROFILE_OVERRIDE
        _PROFILE_OVERRIDE = args.profile.strip().lower()

    body: Any = None
    if args.body is not None:
        if args.body.startswith("@"):
            with open(args.body[1:], "r", encoding="utf-8") as f:
                body_text = f.read()
        else:
            body_text = args.body
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError:
            body = body_text  # send as raw string

    query: Dict[str, Any] = {}
    for kv in args.query:
        if "=" not in kv:
            print(f"--query expects key=value, got: {kv}", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        if k in query:
            existing = query[k]
            if isinstance(existing, list):
                existing.append(v)
            else:
                query[k] = [existing, v]
        else:
            query[k] = v

    try:
        _, parsed = request(
            args.method, args.path, body=body, query=query, timeout=args.timeout
        )
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}", file=sys.stderr)
        if e.body is not None:
            if isinstance(e.body, (dict, list)):
                print(json.dumps(e.body, indent=2), file=sys.stderr)
            else:
                print(str(e.body), file=sys.stderr)
        return 1

    if args.raw or isinstance(parsed, str):
        print(parsed if isinstance(parsed, str) else json.dumps(parsed))
    else:
        print(json.dumps(parsed, indent=2))
    return 0


def _cli() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "configure":
        return _cli_configure(argv[1:])
    if argv and argv[0].upper() in HTTP_METHODS:
        return _cli_request(argv)
    # Help / unknown — let request parser print usage.
    return _cli_request(argv)


if __name__ == "__main__":
    sys.exit(_cli())
