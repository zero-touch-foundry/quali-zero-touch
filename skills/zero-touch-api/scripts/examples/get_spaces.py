#!/usr/bin/env python3
"""GET /api/spaces — list spaces visible to the token.

Usage: python get_spaces.py [--names-only]

Output: full JSON array, or one space name per line with --names-only.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--names-only", action="store_true")
    args = p.parse_args()
    try:
        _, spaces = request("GET", "/spaces")
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    if args.names_only:
        for s in spaces or []:
            print(s.get("name", ""))
    else:
        print(json.dumps(spaces, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
