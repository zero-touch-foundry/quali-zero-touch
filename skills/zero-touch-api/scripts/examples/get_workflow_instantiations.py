#!/usr/bin/env python3
"""GET /api/spaces/{space}/environments/{env_id}/workflows_v2

Lists workflows that have been instantiated (run history) on the given environment.

Usage: python get_workflow_instantiations.py --space SPACE --id ENV_ID
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
    p.add_argument("--id", required=True, dest="env_id")
    args = p.parse_args()
    try:
        _, resp = request(
            "GET",
            f"/spaces/{args.space}/environments/{args.env_id}/workflows_v2",
        )
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    print(json.dumps(resp, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
