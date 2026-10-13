#!/usr/bin/env python3
"""POST /api/spaces/{space}/validations/blueprints — validate blueprint YAML.

Usage:
  python validate_blueprint.py --space SPACE --name BP --file path/to/bp.yaml
  python validate_blueprint.py --space SPACE --name BP --yaml '$(cat bp.yaml)'

Request body (snake_case; camelCase keys are rejected with HTTP 422):
  {"blueprint_name": "<name>", "blueprint_raw_64": "<base64-encoded YAML>"}
Response shape:
  {"errors": [{"code": ..., "message": ..., ...}], "warnings": [...]}

Prints the response JSON on stdout and an "errors: N, warnings: M" summary
(with each message) on stderr. Exit code 1 if there are any errors.
"""
import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--space", required=True)
    p.add_argument("--name", required=True, help="Blueprint name")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="Path to blueprint YAML file")
    src.add_argument("--yaml", help="Inline YAML string")
    args = p.parse_args()

    if args.file:
        yaml_text = Path(args.file).read_text(encoding="utf-8")
    else:
        yaml_text = args.yaml

    b64 = base64.b64encode(yaml_text.encode("utf-8")).decode("ascii")
    body = {"blueprint_name": args.name, "blueprint_raw_64": b64}

    try:
        _, resp = request(
            "POST", f"/spaces/{args.space}/validations/blueprints", body=body
        )
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    print(json.dumps(resp, indent=2))
    resp = resp if isinstance(resp, dict) else {}
    errors = resp.get("errors") or []
    warnings = resp.get("warnings") or []
    print(f"errors: {len(errors)}, warnings: {len(warnings)}", file=sys.stderr)
    for label, items in (("ERROR", errors), ("WARNING", warnings)):
        for item in items:
            if isinstance(item, dict):
                code = item.get("code") or ""
                msg = item.get("message") or json.dumps(item)
            else:
                code, msg = "", str(item)
            print(f"  {label} {code}: {msg}".rstrip(), file=sys.stderr)
    # exit 1 if invalid so callers can branch on $?
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
