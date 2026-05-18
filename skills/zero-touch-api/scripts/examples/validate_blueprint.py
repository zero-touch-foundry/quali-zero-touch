#!/usr/bin/env python3
"""POST /api/spaces/{space}/validations/blueprints — validate blueprint YAML.

Usage:
  python validate_blueprint.py --space SPACE --name BP --file path/to/bp.yaml
  python validate_blueprint.py --space SPACE --name BP --yaml '$(cat bp.yaml)'

The API expects the YAML base64-encoded under field "blueprintRaw64".
Response shape:
  {"is_valid": bool, "errors": [...], "warnings": [...]}
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
    body = {"blueprintName": args.name, "blueprintRaw64": b64}

    try:
        _, resp = request(
            "POST", f"/spaces/{args.space}/validations/blueprints", body=body
        )
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    print(json.dumps(resp, indent=2))
    # exit 1 if invalid so callers can branch on $?
    if isinstance(resp, dict) and resp.get("is_valid") is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
