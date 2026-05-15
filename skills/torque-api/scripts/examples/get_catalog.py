#!/usr/bin/env python3
"""GET /api/spaces/{space}/catalog — list catalog items (published blueprints + grains).

Usage: python get_catalog.py --space SPACE [--search TEXT] [--only-favorites]
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
    p.add_argument("--search", default=None)
    p.add_argument("--only-favorites", action="store_true")
    args = p.parse_args()

    query = {}
    if args.search:
        query["search"] = args.search
    if args.only_favorites:
        query["only_favorites"] = "true"

    try:
        _, items = request(
            "GET", f"/spaces/{args.space}/catalog", query=query or None
        )
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    print(json.dumps(items, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
