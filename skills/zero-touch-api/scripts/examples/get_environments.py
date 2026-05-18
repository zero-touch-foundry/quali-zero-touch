#!/usr/bin/env python3
"""GET /api/spaces/{space}/environments — list environments in a space.

Usage: python get_environments.py --space SPACE [--name FILTER] [--status STATUS]
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
    p.add_argument("--name", default=None, help="Filter by environment name (substring on server)")
    p.add_argument("--status", default=None, help="Filter by status (Active, Launching, ...)")
    args = p.parse_args()

    query = {}
    if args.name:
        query["name"] = args.name
    if args.status:
        query["status"] = args.status

    try:
        _, envs = request(
            "GET", f"/spaces/{args.space}/environments", query=query or None
        )
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    print(json.dumps(envs, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
