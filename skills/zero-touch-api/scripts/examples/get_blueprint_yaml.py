#!/usr/bin/env python3
"""Fetch blueprint YAML content.

Two repository sources:
  - "qtorque" built-in repo: uses /spaces/{space}/blueprints/{name}/editable
  - External repo: uses /spaces/{space}/repositories/{repo}/blueprints/{name}/{branch}/files

Usage:
  python get_blueprint_yaml.py --space SPACE --name BP                       # qtorque
  python get_blueprint_yaml.py --space SPACE --name BP --repo REPO --branch BR
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--space", required=True)
    p.add_argument("--name", required=True, help="Blueprint name")
    p.add_argument("--repo", default=None, help="External repo name (omit for qtorque built-in)")
    p.add_argument("--branch", default=None, help="Branch (required if --repo set)")
    args = p.parse_args()

    if args.repo and not args.branch:
        print("--branch is required when --repo is provided", file=sys.stderr)
        return 2

    try:
        if not args.repo:
            _, resp = request(
                "GET",
                f"/spaces/{args.space}/blueprints/{args.name}/editable",
            )
            # Response is BlueprintContentResponse: {"content": "...yaml..."}
            if isinstance(resp, dict) and "content" in resp:
                print(resp["content"])
            else:
                print(resp if isinstance(resp, str) else json.dumps(resp, indent=2))
        else:
            _, resp = request(
                "GET",
                f"/spaces/{args.space}/repositories/{args.repo}/blueprints/"
                f"{args.name}/{args.branch}/files",
            )
            # Response is array of file objects; filter where kind == "blueprint"
            files = resp if isinstance(resp, list) else []
            bp_files = [f for f in files if f.get("kind") == "blueprint"]
            if not bp_files:
                print("No blueprint file found in repository response", file=sys.stderr)
                print(json.dumps(files, indent=2), file=sys.stderr)
                return 1
            # Print first blueprint's content (or raw JSON if shape differs)
            first = bp_files[0]
            if isinstance(first.get("content"), str):
                print(first["content"])
            else:
                print(json.dumps(first, indent=2))
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
