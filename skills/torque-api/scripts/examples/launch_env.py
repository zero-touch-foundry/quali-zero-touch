#!/usr/bin/env python3
"""POST /api/spaces/{space}/environments — launch a new environment.

Two source modes:
  --from-registered REPO/BP    : launch from a blueprint registered in a repo
  --from-standalone YAML_FILE  : launch from a standalone (inline) blueprint YAML

Usage examples:
  python launch_env.py --space SPACE --name my-env \\
    --from-registered qtorque/my-bp \\
    --inputs '{"region":"us-east-1"}' --duration PT2H

  python launch_env.py --space SPACE --name my-env \\
    --from-standalone path/to/bp.yaml \\
    --inputs '{"region":"us-east-1"}' --duration PT2H

Returns the new environment id on stdout (one line).
"""
import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", required=True)
    p.add_argument("--name", required=True, help="Environment name")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--from-registered",
        help="REPO/BLUEPRINT  (e.g. qtorque/my-bp)",
    )
    src.add_argument(
        "--from-standalone",
        help="Path to standalone blueprint YAML file",
    )
    p.add_argument("--inputs", default="{}", help="JSON object of input values")
    p.add_argument("--duration", default=None, help="ISO-8601, e.g. PT2H")
    p.add_argument("--scheduled-end-time", default=None,
                   help="ISO-8601 datetime; alternative to --duration")
    p.add_argument("--owner-email", default=None)
    args = p.parse_args()

    body = {
        "environment_name": args.name,
        "inputs": json.loads(args.inputs),
    }
    if args.duration:
        body["duration"] = args.duration
    if args.scheduled_end_time:
        body["scheduled_end_time"] = args.scheduled_end_time
    if args.owner_email:
        body["owner_email"] = args.owner_email

    if args.from_registered:
        if "/" not in args.from_registered:
            print("--from-registered must be REPO/BLUEPRINT", file=sys.stderr)
            return 2
        repo, bp = args.from_registered.split("/", 1)
        body["blueprint_name"] = bp
        body["source"] = {"blueprintName": bp, "repositoryName": repo}
    else:
        yaml_text = Path(args.from_standalone).read_text(encoding="utf-8")
        body["base64_standalone_blueprint"] = base64.b64encode(
            yaml_text.encode("utf-8")
        ).decode("ascii")
        body["blueprint_name"] = args.name

    try:
        _, resp = request("POST", f"/spaces/{args.space}/environments", body=body)
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    # Response is either {"id": "..."} or a bare string id depending on API version.
    if isinstance(resp, dict) and "id" in resp:
        print(resp["id"])
    elif isinstance(resp, str):
        print(resp)
    else:
        print(json.dumps(resp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
