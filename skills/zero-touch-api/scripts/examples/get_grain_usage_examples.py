#!/usr/bin/env python3
"""Find usage examples of a named grain across blueprints in a space.

Not a single endpoint — an orchestration:
  1. List catalog blueprints in the space.
  2. For each, fetch the editable YAML.
  3. Regex-scan for references to the target grain's outputs.

Usage:
  python get_grain_usage_examples.py --space SPACE --grain GRAIN_NAME

Output: JSON list of {blueprint_name, snippet} objects.

Limitation: only scans blueprints in the "qtorque" built-in repo (others would
need repo+branch params per blueprint, which the catalog list does not expose
uniformly). Use as a best-effort hint, not exhaustive.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", required=True)
    p.add_argument("--grain", required=True, help="Grain name to search for usage of")
    args = p.parse_args()

    try:
        _, catalog = request("GET", f"/spaces/{args.space}/catalog")
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1

    pattern = re.compile(
        r"\{\{\s*\.grains\." + re.escape(args.grain) + r"\.outputs\.[A-Za-z0-9_]+\s*\}\}"
    )

    hits = []
    for item in catalog or []:
        name = item.get("name")
        if not name:
            continue
        try:
            _, resp = request(
                "GET", f"/spaces/{args.space}/blueprints/{name}/editable"
            )
        except TorqueError:
            continue
        yaml_text = resp.get("content") if isinstance(resp, dict) else resp
        if not isinstance(yaml_text, str):
            continue
        for m in pattern.finditer(yaml_text):
            # Capture surrounding 2 lines for context.
            start = yaml_text.rfind("\n", 0, m.start()) + 1
            end = yaml_text.find("\n", m.end())
            if end == -1:
                end = len(yaml_text)
            hits.append({"blueprint_name": name, "snippet": yaml_text[start:end].strip()})

    print(json.dumps(hits, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
