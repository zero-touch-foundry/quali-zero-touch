#!/usr/bin/env python3
"""Torque REST API helper. Stdlib only.

Two modes:
  CLI:    python torque_api.py GET /spaces
          python torque_api.py POST /spaces/foo/validations/blueprints --body '{...}'
  Import: from torque_api import request, TorqueError
          data = request("GET", "/spaces")

Env:
  TORQUE_API_TOKEN  required, bearer token
  TORQUE_API_HOST   optional, default portal.qtorque.io

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


def _host() -> str:
    return os.environ.get("TORQUE_API_HOST", DEFAULT_HOST).strip().rstrip("/")


def _token() -> str:
    tok = os.environ.get("TORQUE_API_TOKEN", "").strip()
    if not tok:
        raise TorqueAuthError(0, None, "TORQUE_API_TOKEN env var is not set")
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

def _cli() -> int:
    p = argparse.ArgumentParser(description="Torque REST API helper")
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
        "--raw",
        action="store_true",
        help="Print response without pretty-printing",
    )
    args = p.parse_args()

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
        status, parsed = request(
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


if __name__ == "__main__":
    sys.exit(_cli())
