#!/usr/bin/env python3
"""GET /api/resource — list Inventory records of one resource type, all pages.

Inventory holds the records Discovery syncs per provider (provider name ==
target name): Intersight servers, vCenter VMs, Kubernetes nodes, AWS
resources, ... A `type: resource` input offers these records, and its value
is the record's `id` (the Torque reference id, e.g. `Ab12Cd34Ef56`).

Paging: paging_info.take is capped at 80 (81+ is 422 MAX_PAGE_SIZE_EXCEEDED);
this script pages at 80 until the list is exhausted or --max is reached.
Unknown query parameters are ignored by the server (no error), so a filter
spelled wrong returns everything; use the flags below rather than guessing.

Usage:
  python get_inventory_resources.py --type compute.Blade
  python get_inventory_resources.py --type Node --provider my-k8s-target
  python get_inventory_resources.py --type compute.Blade --reservable-only --name-contains 2-1
  python get_inventory_resources.py --type Node --names-only
  python get_inventory_resources.py --type compute.Blade --json

Output: a table (id, name, identifier, reservation status, reserving
environment as space/env_id, excluded, attributes as k=v), one name per line
with --names-only, or the raw records as a JSON array with --json. The record
count goes to stderr. Exit 1 on an API error.

Filters are server-side: --provider (exact), --name-contains (case-insensitive
substring), --reservable-only (reservation_status=available and not excluded
from reserving, i.e. what a `reservable-only: true` picker offers).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402
from inventory_shapes import MAX_PAGE_SIZE, attribute_pairs, iter_resources  # noqa: E402


def _reserver(rec: dict) -> str:
    d = rec.get("reserver_details") or {}
    if not d:
        return "-"
    return f"{d.get('space_name') or '?'}/{d.get('env_id') or '?'}"


def _table(records: list) -> None:
    rows = []
    for r in records:
        attrs = "; ".join(f"{k}={v}" for k, v in attribute_pairs(r))
        rows.append([
            r.get("id") or "",
            r.get("name") or "",
            r.get("identifier") or "",
            r.get("reservation_status") or "",
            _reserver(r),
            "yes" if r.get("excluded_from_reserving") else "no",
            attrs,
        ])
    header = ["ID", "NAME", "IDENTIFIER", "STATUS", "RESERVED BY", "EXCLUDED", "ATTRIBUTES"]
    widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    widths[-1] = 0  # last column is not padded

    def line(cells):
        return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths)).rstrip()

    print(line(header))
    for r, row in zip(records, rows):
        print(line(row))
        if r.get("excluded_from_reserving") and r.get("excluded_from_reserving_reason"):
            print(f"    excluded: {r['excluded_from_reserving_reason']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--type", required=True,
                   help="Resource type, exact (e.g. compute.Blade, compute.RackUnit, Node).")
    p.add_argument("--provider", default=None, help="Provider (= target) name, exact.")
    p.add_argument("--reservable-only", action="store_true",
                   help="Only records that are available and not excluded from reserving.")
    p.add_argument("--name-contains", default=None, help="Case-insensitive substring of the record name.")
    p.add_argument("--max", type=int, default=None, help="Stop after this many records (default: all).")
    p.add_argument("--page-size", type=int, default=MAX_PAGE_SIZE,
                   help=f"Records per request, 1..{MAX_PAGE_SIZE} (default {MAX_PAGE_SIZE}, the server cap).")
    out = p.add_mutually_exclusive_group()
    out.add_argument("--names-only", action="store_true", help="Print one record name per line.")
    out.add_argument("--json", action="store_true", help="Print the raw records as a JSON array.")
    args = p.parse_args()

    if not 1 <= args.page_size <= MAX_PAGE_SIZE:
        p.error(f"--page-size must be 1..{MAX_PAGE_SIZE} (GET /api/resource rejects take > 80)")
    if args.max is not None and args.max < 1:
        p.error("--max must be at least 1")

    extra = {}
    if args.reservable_only:
        extra["reservation_status"] = "available"
        extra["excluded_from_reserving"] = "false"
    if args.name_contains:
        extra["name"] = args.name_contains

    records = []
    try:
        for rec in iter_resources(args.type, provider=args.provider, page=args.page_size,
                                  extra_query=extra, request_fn=request):
            records.append(rec)
            if args.max and len(records) >= args.max:
                break
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(records, indent=2))
    elif args.names_only:
        for r in records:
            print(r.get("name", ""))
    elif records:
        _table(records)
    print(f"{len(records)} record(s)", file=sys.stderr)
    if not records:
        print("note: no records; resource types are exact (compute.Blade, not Blade) and "
              "the provider is the target name", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
