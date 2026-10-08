#!/usr/bin/env python3
"""POST /api/spaces/{space}/catalog/inputs_allowed_values — evaluate a resource picker.

Shows what the launch form would offer for a `type: resource` input, without
launching anything. The input definition is read in its YAML shape (from a
blueprint/workflow file, or --selector as JSON with the same kebab-case keys),
converted strictly to the REST shape, and evaluated by the server:

  YAML                                   REST (what this script sends)
  depends-on: Target                     "depends_on": ["Target"]
  resource-selector:                     "resource_selector": {
    provider-name: '{{ .inputs.T }}'       "provider_name": "{{ .inputs.T }}",
    reservable-only: true                  "reservable_only": true,
    attributes: [ {Model: X} ]             "attributes": [{"name": "Model", "value": "X"}],
    any-of: [ {type: compute.Blade} ]      "any_of": [{"type": "compute.Blade"}]}

The REST side ignores what it does not know (a kebab key, an unknown key, a
nested any-of, reservable-only inside any-of) and widens or empties the list
without an error, so unknown selector keys are refused here before any call.

--with-value NAME=VALUE fills inputs_with_values for a picker that depends on
another input (a target input's value is the target name; a resource input's
value is a reference id). Each is sent as
{"definition": {"name": NAME, "type": <type from the YAML, else string>}, "value": VALUE};
a bare string is rejected by the server (400 MALFORMED_REQUEST_PARAMETER).
Without depends-on the server cannot resolve '{{ .inputs.X }}' in the selector
(VALUE_CANT_BE_RESOLVED); with --selector, depends_on is the --with-value names.

Usage:
  python get_input_allowed_values.py --space S --yaml workflow.yaml --input Node \\
      --with-value Target=my-k8s-target
  python get_input_allowed_values.py --space S \\
      --selector '{"type": "compute.Blade", "reservable-only": true, "attributes": [{"Model": "UCSX-210C-M6"}]}'
  python get_input_allowed_values.py ... --dry-run     # print the REST request, call nothing

Output: a table of value (reference id) and display_value, or the raw response
entry with --json. Count to stderr. Exit 1 on an API error or when the server
reports errors for the input; exit 2 when the YAML shape is refused locally.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from torque_api import request, TorqueError  # noqa: E402
from inventory_shapes import (  # noqa: E402
    ShapeError, ignored_input_keys, input_yaml_to_rest, load_yaml_inputs, selector_yaml_to_rest,
)


def _parse_with_values(pairs, yaml_inputs):
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ShapeError(f"--with-value {pair!r}: expected NAME=VALUE")
        name, value = pair.split("=", 1)
        name = name.strip()
        definition = (yaml_inputs or {}).get(name)
        itype = str(definition.get("type")) if isinstance(definition, dict) and definition.get("type") else "string"
        out[name] = {"definition": {"name": name, "type": itype}, "value": value}
    return out


def _build_body(args):
    """Return (body, notes) or raise ShapeError."""
    notes = []
    yaml_inputs = None
    if args.yaml:
        yaml_inputs = load_yaml_inputs(args.yaml)
        if args.input not in yaml_inputs:
            raise ShapeError(f"no input {args.input!r} in {args.yaml}; inputs: {', '.join(yaml_inputs) or '(none)'}")
        raw = yaml_inputs[args.input]
        definition = input_yaml_to_rest(args.input, raw)
        if definition["type"] != "resource" or "resource_selector" not in definition:
            raise ShapeError(f"inputs.{args.input} is type {definition['type']!r} without a resource-selector; "
                             "this script evaluates resource pickers")
        dropped = ignored_input_keys(raw)
        if dropped:
            notes.append(f"not sent (no effect on allowed values): {', '.join(dropped)}")
    else:
        try:
            selector = json.loads(args.selector)
        except json.JSONDecodeError as e:
            raise ShapeError(f"--selector is not valid JSON: {e}")
        definition = {"name": args.input or "Resource", "type": "resource"}
        if args.with_value:
            definition["depends_on"] = [p.split("=", 1)[0].strip() for p in args.with_value]
        definition["resource_selector"] = selector_yaml_to_rest(selector, "--selector")
    with_values = _parse_with_values(args.with_value, yaml_inputs)
    missing = [d for d in definition.get("depends_on", []) if d not in with_values]
    if missing:
        notes.append(f"depends on {', '.join(missing)} but no --with-value given; "
                     "a selector that templates it will not resolve")
    return {"input_definitions": [definition], "inputs_with_values": with_values}, notes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", required=True, help="Space whose catalog evaluates the input.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--yaml", metavar="FILE", help="Blueprint or workflow YAML that defines the input.")
    src.add_argument("--selector", metavar="JSON",
                     help="A resource-selector in the YAML shape (kebab-case keys, '- Key: value' attributes) as JSON.")
    p.add_argument("--input", help="Input name (required with --yaml; with --selector only labels the request).")
    p.add_argument("--with-value", action="append", metavar="NAME=VALUE",
                   help="Value of another input the picker depends on. Repeatable.")
    p.add_argument("--dry-run", action="store_true", help="Print the REST request body and exit; no API call.")
    p.add_argument("--json", action="store_true", help="Print the raw response entry instead of a table.")
    args = p.parse_args()
    if args.yaml and not args.input:
        p.error("--yaml needs --input NAME")

    try:
        body, notes = _build_body(args)
    except (ShapeError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return 0

    try:
        _, resp = request("POST", f"/spaces/{args.space}/catalog/inputs_allowed_values", body=body)
    except TorqueError as e:
        print(f"ERROR HTTP {e.status}: {e.body}", file=sys.stderr)
        return 1

    entry = resp[0] if isinstance(resp, list) and resp else (resp if isinstance(resp, dict) else {})
    values = entry.get("allowed_values") or []
    errors = entry.get("errors") or []

    if args.json:
        print(json.dumps(entry, indent=2))
    elif values:
        rows = [(v.get("value", ""), v.get("display_value", "")) for v in values]
        width = max(len("VALUE"), *(len(str(r[0])) for r in rows))
        print(f"{'VALUE'.ljust(width)}  DISPLAY VALUE")
        for value, display in rows:
            print(f"{str(value).ljust(width)}  {display}")
    print(f"{len(values)} allowed value(s)", file=sys.stderr)
    if entry.get("has_more"):
        print("note: has_more is true; the server returned a partial list", file=sys.stderr)
    for err in errors:
        print(f"ERROR {err.get('code')}: {err.get('message')}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
