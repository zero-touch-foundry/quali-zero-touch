#!/usr/bin/env python3
"""GET /api/spaces/{space}/blueprints — list blueprints in a space.

Usage: python get_blueprints.py --space SPACE [--sub-type workflow]

--sub-type filters by sub_type (e.g. "workflow" returns only workflow blueprints).
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
    p.add_argument("--sub-type", dest="sub_type", default=None,
                   help='Filter sub_type (e.g. "workflow")')
    args = p.parse_args()
    query = {"sub_type": args.sub_type} if args.sub_type else None
    try:
        _, blueprints = request("GET", f"/spaces/{args.space}/blueprints", query=query)
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    print(json.dumps(blueprints, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
