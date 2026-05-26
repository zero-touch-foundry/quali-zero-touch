#!/usr/bin/env python3
"""List Torque environments, with auto-paging.

With --space:    GET /api/spaces/{space}/environments/v2  (single space)
Without --space: GET /api/operation_hub                   (all spaces, cross-account)

Both use skip/take paging (paging_info.skip / paging_info.take) and the same
status= filter. Multiple statuses are sent as repeated status= params.

Valid status values:
  Active, Active With Error, Launching, Terminating, Terminate Failed, Ended,
  Force Ended, Updating, In Progress, Failed, Success, Launch Cancelled, N/A,
  Awaiting, Scheduled, Releasing, Importing

Usage:
  python get_environments.py --space SPACE [--status "Active,Launching"]
  python get_environments.py [--status "Terminate Failed"]   # all spaces
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402

TAKE = 50


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", default=None, help="Space name. Omit to list across all spaces via operation_hub.")
    p.add_argument("--status", default=None, help="Comma-separated status filter, e.g. 'Active,Launching'.")
    p.add_argument("--limit", type=int, default=None, help="Stop after this many environments (default: all).")
    args = p.parse_args()

    if args.space:
        path = f"/spaces/{args.space}/environments/v2"
        list_key = "environments"
    else:
        path = "/operation_hub"
        list_key = "environment_list"

    statuses = [s.strip() for s in args.status.split(",")] if args.status else None

    collected = []
    skip = 0
    while True:
        query = {
            "paging_info.skip": skip,
            "paging_info.take": TAKE,
            "sort_by": "StartTime",
            "sort_by_direction": 1,
        }
        if not args.space:
            query["all"] = "true"
        if statuses:
            query["status"] = statuses

        try:
            _, resp = request("GET", path, query=query)
        except TorqueError as e:
            print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
            return 1

        # operation_hub returns {environment_list, paging_info}; the v2 space
        # endpoint may return a bare list or the same wrapped shape.
        if isinstance(resp, dict):
            batch = resp.get(list_key) or resp.get("environment_list") or resp.get("environments") or []
            full_count = (resp.get("paging_info") or {}).get("full_count")
        else:
            batch = resp
            full_count = None

        if not batch:
            break
        collected.extend(batch)

        if args.limit and len(collected) >= args.limit:
            collected = collected[: args.limit]
            break
        if full_count is not None and len(collected) >= full_count:
            break
        if len(batch) < TAKE:
            break
        skip += TAKE

    print(json.dumps(collected, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
