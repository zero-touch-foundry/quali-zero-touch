#!/usr/bin/env python3
"""POST /api/spaces/{space}/environments — run a day-2 workflow.

A "workflow run" is launched as an automation environment whose blueprint is the
workflow itself, with entity_metadata pointing at the target env (or env_resource).

Usage:
  python run_workflow.py --space SPACE --workflow WF_NAME \\
    --target-env ENV_ID [--target-grain GRAIN_NAME] \\
    [--inputs '{"key":"val"}'] [--duration PT30M]

If --target-grain is omitted, entity type defaults to "env" (env-scoped workflow).
With --target-grain, entity type is "env_resource" (grain-scoped workflow).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", required=True)
    p.add_argument("--workflow", required=True, help="Workflow blueprint name")
    p.add_argument("--target-env", required=True, dest="target_env",
                   help="Environment ID the workflow runs on")
    p.add_argument("--target-grain", default=None, dest="target_grain",
                   help="Grain name (env_resource scope). Omit for env scope.")
    p.add_argument("--inputs", default="{}")
    p.add_argument("--duration", default=None, help="ISO-8601, e.g. PT30M")
    p.add_argument("--name", default=None, help="Optional name for the workflow run")
    args = p.parse_args()

    entity_type = "env_resource" if args.target_grain else "env"
    entity_metadata = {"type": entity_type, "environment_id": args.target_env}
    if args.target_grain:
        entity_metadata["resource_name"] = args.target_grain

    body = {
        "environment_name": args.name or f"{args.workflow}-run",
        "blueprint_name": args.workflow,
        "source": {"blueprintName": args.workflow, "repositoryName": "qtorque"},
        "inputs": json.loads(args.inputs),
        "entity_metadata": entity_metadata,
    }
    if args.duration:
        body["duration"] = args.duration

    try:
        _, resp = request("POST", f"/spaces/{args.space}/environments", body=body)
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1
    if isinstance(resp, dict) and "id" in resp:
        print(resp["id"])
    elif isinstance(resp, str):
        print(resp)
    else:
        print(json.dumps(resp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
