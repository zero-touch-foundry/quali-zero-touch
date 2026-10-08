#!/usr/bin/env python3
"""Inventory and resource-picker shapes: YAML (blueprint/workflow) vs REST.

Pure helpers shared by the inventory example scripts. Stdlib only.

Why this exists: the Torque REST API and the blueprint YAML spell the same
resource picker differently, and the REST side fails silently.

  YAML (kebab-case)                     REST (snake_case)
  resource-selector:                    "resource_selector": {
    provider-name: X                      "provider_name": "X",
    provider-type: intersight             "provider_type": "intersight",
    type: compute.Blade                   "type": "compute.Blade",
    reservable-only: true                 "reservable_only": true,
    attributes:                           "attributes": [
      - Model: UCSX-210C-M6                 {"name": "Model", "value": "UCSX-210C-M6"}],
    any-of:                               "any_of": [
      - type: compute.RackUnit              {"type": "compute.RackUnit"}]}
  depends-on: 'Target, Region'          "depends_on": ["Target", "Region"]

Over REST a kebab key, an unknown key, a nested any-of or a `reservable-only`
inside an any-of item is ignored without an error (the picker widens or
returns 0 rows); a `- Key: value` attribute fails with an internal error.
So the converters below are strict: they refuse every key they do not know.

  selector_yaml_to_rest(dict) -> dict      strict; raises ShapeError
  input_yaml_to_rest(name, dict) -> dict   input definition for inputs_allowed_values
  iter_resources(type, provider=None, page=80, ...)  pages GET /api/resource
  load_yaml_inputs(path_or_text) -> dict   the `inputs:` mapping of a YAML file

Run `python inventory_shapes.py --self-test` to check the conversions, the
stdlib YAML reader and the pager on fixtures (no network, no token).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

# GET /api/resource rejects paging_info.take > 80 with 422 MAX_PAGE_SIZE_EXCEEDED.
MAX_PAGE_SIZE = 80

# YAML selector key -> REST key. Anything else is refused.
SELECTOR_KEYS = {
    "type": "type",
    "provider-name": "provider_name",
    "provider-type": "provider_type",
    "attributes": "attributes",
    "reservable-only": "reservable_only",
    "any-of": "any_of",
}
# Keys an any-of item may carry. reservable-only and any-of are top-level only:
# inside an item the REST evaluator ignores them.
ANY_OF_ITEM_KEYS = ("type", "provider-name", "provider-type", "attributes")
SCALAR_KEYS = ("type", "provider-name", "provider-type")

# Input-definition keys that influence the allowed values and are sent.
INPUT_KEYS_SENT = ("type", "depends-on", "resource-selector")


class ShapeError(ValueError):
    """A YAML shape that cannot be converted to the REST shape safely."""


# ---------------------------------------------------------------- conversions

def _accepted(keys) -> str:
    return ", ".join(keys)


def _attr_value(name: str, value: Any, where: str) -> str:
    if value is None:
        raise ShapeError(f"{where}: attribute '{name}' has no value")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    raise ShapeError(f"{where}: attribute '{name}' must be a scalar, got {type(value).__name__}")


def _attributes_to_rest(items: Any, where: str) -> List[Dict[str, str]]:
    if isinstance(items, dict):
        raise ShapeError(
            f"{where}: attributes must be a list of single-key items "
            "('- Model: X'), not a mapping")
    if not isinstance(items, list) or not items:
        raise ShapeError(f"{where}: attributes must be a non-empty list of '- Key: value' items")
    out = []
    for i, item in enumerate(items):
        at = f"{where}.attributes[{i}]"
        if not isinstance(item, dict):
            raise ShapeError(f"{at}: expected '- Key: value', got {item!r}")
        if set(item) == {"name", "value"}:
            raise ShapeError(
                f"{at}: {{name, value}} is the REST spelling; in YAML write "
                f"'- {item['name']}: {item['value']}'")
        if len(item) != 1:
            raise ShapeError(
                f"{at}: one attribute per item ('- Key: value'); this item has "
                f"{len(item)} keys: {_accepted(item)}")
        (name, value), = item.items()
        out.append({"name": str(name), "value": _attr_value(str(name), value, at)})
    return out


def _bool(value: Any, where: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise ShapeError(f"{where}: reservable-only must be true or false, got {value!r}")


def _check_keys(sel: Dict[str, Any], allowed, where: str) -> None:
    for key in sel:
        if key in allowed:
            continue
        rest_to_yaml = {v: k for k, v in SELECTOR_KEYS.items()}
        if key in rest_to_yaml and rest_to_yaml[key] in allowed:
            raise ShapeError(
                f"{where}: '{key}' is the REST spelling; in YAML write '{rest_to_yaml[key]}'")
        if where.endswith("]") and key in ("reservable-only", "any-of"):
            raise ShapeError(
                f"{where}: '{key}' is not allowed inside an any-of item (the REST "
                f"evaluator ignores it there); set it at the top of the selector")
        raise ShapeError(
            f"{where}: unknown selector key '{key}'. Accepted: {_accepted(allowed)}")


def _scalar(value: Any, key: str, where: str) -> str:
    if value is None or isinstance(value, (dict, list)) or str(value).strip() == "":
        raise ShapeError(f"{where}: '{key}' must be a non-empty string")
    return str(value)


def selector_yaml_to_rest(selector: Dict[str, Any], where: str = "resource-selector") -> Dict[str, Any]:
    """Convert a YAML `resource-selector` mapping to the REST `resource_selector`.

    Strict: unknown keys, REST spellings, nested any-of, reservable-only inside
    any-of, a scalar at both levels, an empty selector and malformed attributes
    all raise ShapeError. Liquid templates ('{{ .inputs.X }}') pass through.
    """
    if not isinstance(selector, dict):
        raise ShapeError(f"{where}: expected a mapping, got {type(selector).__name__}")
    if not selector:
        raise ShapeError(f"{where}: empty selector would match the whole inventory")
    _check_keys(selector, tuple(SELECTOR_KEYS), where)
    rest: Dict[str, Any] = {}
    for key, value in selector.items():
        if key in SCALAR_KEYS:
            rest[SELECTOR_KEYS[key]] = _scalar(value, key, where)
        elif key == "attributes":
            rest["attributes"] = _attributes_to_rest(value, where)
        elif key == "reservable-only":
            rest["reservable_only"] = _bool(value, f"{where}.reservable-only")
    if "any-of" in selector:
        items = selector["any-of"]
        if not isinstance(items, list) or not items:
            raise ShapeError(f"{where}: any-of must be a non-empty list of selectors")
        out = []
        for i, item in enumerate(items):
            at = f"{where}.any-of[{i}]"
            if not isinstance(item, dict) or not item:
                raise ShapeError(f"{at}: expected a non-empty mapping")
            _check_keys(item, ANY_OF_ITEM_KEYS, at)
            both = [k for k in SCALAR_KEYS if k in item and k in selector]
            if both:
                raise ShapeError(
                    f"{at}: '{both[0]}' is set both at the top and inside any-of; "
                    "set it in one place")
            conv: Dict[str, Any] = {}
            for key, value in item.items():
                if key == "attributes":
                    conv["attributes"] = _attributes_to_rest(value, at)
                else:
                    conv[SELECTOR_KEYS[key]] = _scalar(value, key, at)
            out.append(conv)
        rest["any_of"] = out
    return rest


def split_depends_on(value: Any, where: str = "depends-on") -> List[str]:
    """YAML depends-on is a comma-separated string; REST wants a list."""
    if value is None:
        return []
    if isinstance(value, list):
        names = [str(v).strip() for v in value]
    elif isinstance(value, str):
        names = [v.strip() for v in value.split(",")]
    else:
        raise ShapeError(f"{where}: expected a comma-separated string, got {value!r}")
    return [n for n in names if n]


def input_yaml_to_rest(name: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    """Build the REST input definition that inputs_allowed_values evaluates.

    Sends name, type, depends_on (a list; without it a selector that templates
    another input fails with VALUE_CANT_BE_RESOLVED) and resource_selector.
    Other input keys (description, display-name, style, ...) do not affect the
    allowed values and are not sent; see ignored_input_keys().
    """
    if not isinstance(definition, dict):
        raise ShapeError(f"inputs.{name}: expected a mapping")
    for rest_key, yaml_key in (("resource_selector", "resource-selector"),
                               ("depends_on", "depends-on")):
        if rest_key in definition:
            raise ShapeError(
                f"inputs.{name}: '{rest_key}' is the REST spelling; in YAML write '{yaml_key}'")
    if not definition.get("type"):
        raise ShapeError(f"inputs.{name}: no 'type'")
    rest: Dict[str, Any] = {"name": name, "type": str(definition["type"])}
    deps = split_depends_on(definition.get("depends-on"), f"inputs.{name}.depends-on")
    if deps:
        rest["depends_on"] = deps
    if "resource-selector" in definition:
        rest["resource_selector"] = selector_yaml_to_rest(
            definition["resource-selector"], f"inputs.{name}.resource-selector")
    return rest


def ignored_input_keys(definition: Dict[str, Any]) -> List[str]:
    return [k for k in definition if k not in INPUT_KEYS_SENT]


# ---------------------------------------------------------------- inventory pager

def iter_resources(
    type: str,
    provider: Optional[str] = None,
    page: int = MAX_PAGE_SIZE,
    extra_query: Optional[Dict[str, Any]] = None,
    request_fn: Optional[Callable[..., Tuple[int, Any]]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield every inventory record of `type` (optionally one provider).

    Pages GET /api/resource with paging_info.skip/take (take is capped at 80;
    81+ is a 422 MAX_PAGE_SIZE_EXCEEDED). Sorted by name so pages are stable,
    de-duplicated by id. Accepts both {"resources": [...]} and a bare list.
    TorqueError from the request propagates to the caller.
    """
    if not 1 <= page <= MAX_PAGE_SIZE:
        raise ValueError(f"page must be 1..{MAX_PAGE_SIZE} (GET /api/resource caps take at 80)")
    if request_fn is None:
        from torque_api import request as request_fn  # noqa: WPS433 (lazy: keeps --self-test offline)
    seen = set()
    skip = 0
    while True:
        query: Dict[str, Any] = {
            "type": type,
            "paging_info.skip": skip,
            "paging_info.take": page,
            "sort_by": "name",
            "sort_direction": 0,
        }
        if provider:
            query["provider"] = provider
        if extra_query:
            query.update(extra_query)
        _, resp = request_fn("GET", "/resource", query=query)
        if isinstance(resp, dict):
            batch = resp.get("resources") or []
            full_count = (resp.get("paging_info") or {}).get("full_count")
        else:
            batch = resp or []
            full_count = None
        for rec in batch:
            rid = rec.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            yield rec
        skip += page
        if not batch or len(batch) < page:
            return
        if full_count is not None and skip >= full_count:
            return


def attribute_pairs(record: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """[(name, value)] from a record's attributes list, skipping null values."""
    out = []
    for a in record.get("attributes") or []:
        if isinstance(a, dict) and a.get("value") is not None:
            out.append((str(a.get("name")), a.get("value")))
    return out


# ---------------------------------------------------------------- YAML reading
#
# The plugin is stdlib only, so blueprint YAML is read with PyYAML when it is
# installed and otherwise with the small block-YAML reader below. The reader
# only parses the top-level `inputs:` block: mappings, sequences, plain and
# quoted scalars (multi-line too), flow lists/maps, block scalars (| > and
# chomping variants) and comments. Anchors, aliases and tags are refused.
# Known gap: a blank line inside a multi-line plain/quoted scalar folds to a
# space instead of a newline (only description text is affected; it is not sent).
# Checked against PyYAML on ~600 blueprint/workflow files.

class YamlSubsetError(ShapeError):
    pass


def _strip_comment(line: str) -> str:
    quote = None
    i = 0
    while i < len(line):
        c = line[i]
        if quote == '"' and c == "\\":
            i += 2
            continue
        if quote:
            if c == quote:
                quote = None
        elif c in ("'", '"') and (i == 0 or line[i - 1] in " \t:-[{,"):
            quote = c
        elif c == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def _split_key(content: str) -> Optional[Tuple[str, str]]:
    """'key: value' -> (key, value); None when the line is not a mapping entry."""
    if content[:1] in ("'", '"'):
        q = content[0]
        i = 1
        while i < len(content):
            if content[i] == q:
                if q == "'" and content[i + 1:i + 2] == "'":
                    i += 2
                    continue
                break
            if q == '"' and content[i] == "\\":
                i += 1
            i += 1
        rest = content[i + 1:]
        if rest.startswith(":") and (len(rest) == 1 or rest[1] in " \t"):
            return _scalar_from_text(content[:i + 1]), rest[1:].strip()
        return None
    m = re.match(r"^([^\[\]{},#&*!|>'\"%@`][^#]*?|[^\s:][^:#]*?):(?:\s+|$)(.*)$", content)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


_INT = re.compile(r"^[-+]?(0|[1-9][0-9]*)$")
_FLOAT = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")


_DQ_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
    "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
    "_": "\xa0", "L": " ", "P": " ",
}
_DQ_HEX = {"x": 2, "u": 4, "U": 8}


def _double_quoted(body: str) -> str:
    """Decode a YAML double-quoted scalar body (no surrounding quotes).

    `body` may hold raw line breaks from continuation lines: a break folds to
    one space, or to nothing when escaped with a trailing backslash.
    """
    out: List[str] = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\n":
            out.append(" ")
            i += 1
            continue
        if c != "\\":
            out.append(c)
            i += 1
            continue
        nxt = body[i + 1:i + 2]
        if nxt == "\n":  # escaped line break
            i += 2
            continue
        if nxt in _DQ_HEX:
            width = _DQ_HEX[nxt]
            out.append(chr(int(body[i + 2:i + 2 + width], 16)))
            i += 2 + width
            continue
        if nxt not in _DQ_ESCAPES:
            raise YamlSubsetError(f"unknown escape '\\{nxt}' in a double-quoted string")
        out.append(_DQ_ESCAPES[nxt])
        i += 2
    return "".join(out)


def _scalar_from_text(text: str) -> Any:
    """Parse one scalar or single-line-able flow collection.

    `text` may span continuation lines joined with newlines; they fold to
    spaces (double-quoted strings honour escaped line breaks).
    """
    t = text.strip()
    if not t:
        return None
    if t[0] in "&*!":
        raise YamlSubsetError(f"anchors, aliases and tags are not supported: {t!r}")
    if t[0] == "'" and t.endswith("'") and len(t) >= 2:
        return t[1:-1].replace("\n", " ").replace("''", "'")
    if t[0] == '"' and t.endswith('"') and len(t) >= 2:
        return _double_quoted(t[1:-1])
    t = t.replace("\n", " ")
    if t[0] in "[{":
        return _parse_flow(t)
    if t in ("~", "null", "Null", "NULL"):
        return None
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if _INT.match(t):
        return int(t)
    if _FLOAT.match(t) and any(ch.isdigit() for ch in t):
        return float(t)
    return t


def _parse_flow(text: str) -> Any:
    pos = 0

    def skip_ws() -> None:
        nonlocal pos
        while pos < len(text) and text[pos] in " \t":
            pos += 1

    def parse_value() -> Any:
        nonlocal pos
        skip_ws()
        if pos >= len(text):
            raise YamlSubsetError(f"unterminated flow collection: {text!r}")
        c = text[pos]
        if c == "[":
            pos += 1
            items = []
            skip_ws()
            if text[pos:pos + 1] == "]":
                pos += 1
                return items
            while True:
                items.append(parse_value())
                skip_ws()
                if text[pos:pos + 1] == ",":
                    pos += 1
                    continue
                if text[pos:pos + 1] == "]":
                    pos += 1
                    return items
                raise YamlSubsetError(f"bad flow list: {text!r}")
        if c == "{":
            pos += 1
            out = {}
            skip_ws()
            if text[pos:pos + 1] == "}":
                pos += 1
                return out
            while True:
                key = parse_value()
                skip_ws()
                if text[pos:pos + 1] != ":":
                    raise YamlSubsetError(f"bad flow mapping: {text!r}")
                pos += 1
                out[key] = parse_value()
                skip_ws()
                if text[pos:pos + 1] == ",":
                    pos += 1
                    continue
                if text[pos:pos + 1] == "}":
                    pos += 1
                    return out
                raise YamlSubsetError(f"bad flow mapping: {text!r}")
        if c in ("'", '"'):
            start = pos
            pos += 1
            while pos < len(text):
                if text[pos] == c:
                    if c == "'" and text[pos + 1:pos + 2] == "'":
                        pos += 2
                        continue
                    pos += 1
                    return _scalar_from_text(text[start:pos])
                if c == '"' and text[pos] == "\\":
                    pos += 1
                pos += 1
            raise YamlSubsetError(f"unterminated quote in {text!r}")
        start = pos
        while pos < len(text) and text[pos] not in ",]}":
            if text[pos] == ":" and (pos + 1 >= len(text) or text[pos + 1] in " ,]}"):
                break
            pos += 1
        return _scalar_from_text(text[start:pos])

    value = parse_value()
    skip_ws()
    if pos != len(text):
        raise YamlSubsetError(f"trailing text after flow collection: {text!r}")
    return value


class _Lines:
    def __init__(self, text: str):
        self.raw = text.splitlines()
        self.items: List[Tuple[int, str, int]] = []  # (indent, content, raw index)
        for idx, raw in enumerate(self.raw):
            if "\t" in raw[: len(raw) - len(raw.lstrip())]:
                raise YamlSubsetError(f"line {idx + 1}: tab indentation is not YAML")
            stripped = _strip_comment(raw)
            if not stripped.strip() or stripped.strip() in ("---", "..."):
                continue
            self.items.append((len(stripped) - len(stripped.lstrip()), stripped.strip(), idx))


def _block_scalar(lines: _Lines, i: int, parent_indent: int, header: str) -> Tuple[str, int]:
    """Consume a | or > block scalar starting after line i. Returns (text, next i)."""
    style, chomp = header[0], ("-" if "-" in header else "+" if "+" in header else "")
    raw_idx = lines.items[i][2]
    body: List[str] = []
    j = raw_idx + 1
    block_indent = None
    while j < len(lines.raw):
        raw = lines.raw[j]
        if raw.strip():
            ind = len(raw) - len(raw.lstrip())
            if ind <= parent_indent:
                break
            if block_indent is None:
                block_indent = ind
            if ind < block_indent:
                break
            body.append(raw[block_indent:])
        else:
            body.append("")
        j += 1
    while body and body[-1] == "" and chomp != "+":
        body.pop()
    if style == "|":
        text = "\n".join(body)
    else:
        text = ""
        for k, ln in enumerate(body):
            if k == 0:
                text = ln
            elif ln == "" or body[k - 1] == "":
                text += "\n" + ln if ln else ""
            else:
                text += " " + ln
    if chomp != "-" and body:
        text += "\n"
    nxt = i + 1
    while nxt < len(lines.items) and lines.items[nxt][2] < j:
        nxt += 1
    return text, nxt


def _parse_node(lines: _Lines, i: int, indent: int) -> Tuple[Any, int]:
    if lines.items[i][1].startswith("- ") or lines.items[i][1] == "-":
        return _parse_seq(lines, i, indent)
    return _parse_map(lines, i, indent)


def _value_after_key(lines: _Lines, i: int, indent: int, value: str) -> Tuple[Any, int]:
    """Parse the value of a 'key: value' at line i (mapping indent `indent`)."""
    n = len(lines.items)
    if value[:1] in ("|", ">") and re.match(r"^[|>][-+]?[0-9]?[-+]?$", value):
        return _block_scalar(lines, i, indent, value)
    if value == "":
        if i + 1 < n:
            nind, ncontent, _ = lines.items[i + 1]
            if nind > indent:
                return _parse_node(lines, i + 1, nind)
            if nind == indent and (ncontent.startswith("- ") or ncontent == "-"):
                return _parse_seq(lines, i + 1, indent)
        return None, i + 1
    # multi-line plain or quoted scalar: deeper lines continue it
    j = i + 1
    parts = [value]
    while j < n and lines.items[j][0] > indent:
        parts.append(lines.items[j][1])
        j += 1
    return _scalar_from_text("\n".join(parts)), j


def _parse_map(lines: _Lines, i: int, indent: int) -> Tuple[Dict[Any, Any], int]:
    out: Dict[Any, Any] = {}
    n = len(lines.items)
    while i < n:
        ind, content, raw_idx = lines.items[i]
        if ind < indent:
            break
        if ind > indent:
            raise YamlSubsetError(f"line {raw_idx + 1}: unexpected indentation")
        if content.startswith("- ") or content == "-":
            break
        kv = _split_key(content)
        if kv is None:
            raise YamlSubsetError(f"line {raw_idx + 1}: expected 'key: value', got {content!r}")
        key, value = kv
        if key in out:
            raise YamlSubsetError(f"line {raw_idx + 1}: duplicate key {key!r}")
        out[key], i = _value_after_key(lines, i, indent, value)
    return out, i


def _parse_seq(lines: _Lines, i: int, indent: int) -> Tuple[List[Any], int]:
    out: List[Any] = []
    n = len(lines.items)
    while i < n:
        ind, content, raw_idx = lines.items[i]
        if ind != indent or not (content.startswith("- ") or content == "-"):
            if ind > indent:
                raise YamlSubsetError(f"line {raw_idx + 1}: unexpected indentation")
            break
        rest = content[1:].lstrip()
        if not rest:
            if i + 1 < n and lines.items[i + 1][0] > indent:
                item, i = _parse_node(lines, i + 1, lines.items[i + 1][0])
            else:
                item, i = None, i + 1
            out.append(item)
            continue
        item_indent = indent + (len(content) - len(rest))
        if re.match(r"^[|>][-+]?[0-9]?[-+]?$", rest):
            item, i = _block_scalar(lines, i, indent, rest)
        elif rest.startswith("- ") or (_split_key(rest) and rest[0] not in "[{"):
            # '- key: value' (+ continuation keys at item_indent): re-enter as a block
            lines.items[i] = (item_indent, rest, raw_idx)
            item, i = _parse_node(lines, i, item_indent)
        else:
            j = i + 1
            parts = [rest]
            while j < n and lines.items[j][0] > indent:
                parts.append(lines.items[j][1])
                j += 1
            item, i = _scalar_from_text("\n".join(parts)), j
        out.append(item)
    return out, i


def parse_yaml_subset(text: str) -> Any:
    """Parse block YAML (the subset described above). Raises YamlSubsetError."""
    lines = _Lines(text)
    if not lines.items:
        return None
    value, i = _parse_node(lines, 0, lines.items[0][0])
    if i != len(lines.items):
        raise YamlSubsetError(f"line {lines.items[i][2] + 1}: could not parse {lines.items[i][1]!r}")
    return value


def _top_level_block(text: str, key: str) -> Optional[str]:
    """Return the text of the top-level `key:` block (including the key line)."""
    out: List[str] = []
    inside = False
    for raw in text.splitlines():
        top = raw[:1] not in ("", " ", "\t", "#") and _strip_comment(raw).strip() != ""
        if top:
            if inside:
                break
            kv = _split_key(_strip_comment(raw).strip())
            if kv and kv[0] == key:
                inside = True
        if inside:
            out.append(raw)
    return "\n".join(out) if out else None


def load_yaml_inputs(source: str, force_subset: bool = False) -> Dict[str, Any]:
    """Return the `inputs:` mapping of a blueprint/workflow YAML (path or text).

    A single-line `source` is a file path (OSError if it does not exist).
    Uses PyYAML when installed (unless force_subset), else the stdlib reader.
    """
    text = source if "\n" in source else Path(source).read_text(encoding="utf-8")
    if not force_subset:
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None
        if yaml is not None:
            try:
                doc = yaml.safe_load(text)
            except yaml.YAMLError as e:
                raise ShapeError(f"not valid YAML: {e}")
            inputs = doc.get("inputs") if isinstance(doc, dict) else None
            return inputs if isinstance(inputs, dict) else {}
    block = _top_level_block(text, "inputs")
    if block is None:
        return {}
    parsed = parse_yaml_subset(block)
    inputs = parsed.get("inputs") if isinstance(parsed, dict) else None
    return inputs if isinstance(inputs, dict) else {}


# ---------------------------------------------------------------- self-test

_FIXTURE = """\
spec_version: 2
description: >-
  A workflow. inputs: below
  are the point.
inputs:
  Target:
    type: target
    target-filters:
      cloud-providers:
        - kubernetes
        - openshift   # trailing comment
    description: 'The cluster, through a Target.'
  Node:
    type: resource
    depends-on: Target
    description: The node to act on, from the cluster's Inventory. Nodes held are not offered.
    resource-selector:
      provider-name: '{{ .inputs.Target | split: "/" | last }}'
      type: Node
      reservable-only: true
  Blade:
    type: resource
    depends-on: 'Target, Region'
    style: multi-select
    resource-selector:
      provider-name: intersight-site-a
      reservable-only: true
      attributes:
        - Model: UCSX-210C-M6
        - CPU Count: 2
      any-of:
        - type: compute.Blade
        - type: compute.RackUnit
          attributes:
            - Vendor: "Cisco Systems Inc"
  "Drain Timeout Minutes":
    type: string
    default: '15'
    allowed-values: ['cordon', 'drain', "it's"]
    notes:
      - |
        kept
      - plain
    description: |
      line one
      line two
grains:
  maintenance:
    kind: shell
"""


def _expect_refusal(fn: Callable[[], Any], needle: str) -> None:
    try:
        fn()
    except ShapeError as e:
        assert needle in str(e), f"expected {needle!r} in {e}"
        return
    raise AssertionError(f"expected a refusal mentioning {needle!r}")


def self_test() -> int:
    inputs = load_yaml_inputs(_FIXTURE, force_subset=True)
    assert list(inputs) == ["Target", "Node", "Blade", "Drain Timeout Minutes"], list(inputs)
    assert inputs["Target"]["target-filters"]["cloud-providers"] == ["kubernetes", "openshift"]
    assert inputs["Drain Timeout Minutes"]["allowed-values"] == ["cordon", "drain", "it's"]
    assert inputs["Drain Timeout Minutes"]["description"] == "line one\nline two\n"
    assert inputs["Drain Timeout Minutes"]["default"] == "15"
    assert inputs["Drain Timeout Minutes"]["notes"] == ["kept\n", "plain"]

    node = input_yaml_to_rest("Node", inputs["Node"])
    assert node == {
        "name": "Node", "type": "resource", "depends_on": ["Target"],
        "resource_selector": {
            "provider_name": '{{ .inputs.Target | split: "/" | last }}',
            "type": "Node", "reservable_only": True,
        },
    }, node
    assert ignored_input_keys(inputs["Node"]) == ["description"]

    blade = input_yaml_to_rest("Blade", inputs["Blade"])
    assert blade == {
        "name": "Blade", "type": "resource", "depends_on": ["Target", "Region"],
        "resource_selector": {
            "provider_name": "intersight-site-a", "reservable_only": True,
            "attributes": [{"name": "Model", "value": "UCSX-210C-M6"},
                           {"name": "CPU Count", "value": "2"}],
            "any_of": [{"type": "compute.Blade"},
                       {"type": "compute.RackUnit",
                        "attributes": [{"name": "Vendor", "value": "Cisco Systems Inc"}]}],
        },
    }, blade
    assert input_yaml_to_rest("Target", inputs["Target"]) == {"name": "Target", "type": "target"}

    sel = {"type": "Node"}
    _expect_refusal(lambda: selector_yaml_to_rest({"type": "Node", "bogus": 1}), "unknown selector key 'bogus'")
    _expect_refusal(lambda: selector_yaml_to_rest({"provider_name": "x"}), "REST spelling")
    _expect_refusal(lambda: selector_yaml_to_rest({}), "empty selector")
    _expect_refusal(lambda: selector_yaml_to_rest({"type": "T", "attributes": [{"name": "Model", "value": "X"}]}),
                    "'- Model: X'")
    _expect_refusal(lambda: selector_yaml_to_rest({"type": "T", "attributes": [{"A": 1, "B": 2}]}), "one attribute per item")
    _expect_refusal(lambda: selector_yaml_to_rest({"type": "T", "attributes": {"Model": "X"}}), "not a mapping")
    _expect_refusal(lambda: selector_yaml_to_rest({"any-of": [{"any-of": [sel]}]}), "not allowed inside an any-of")
    _expect_refusal(lambda: selector_yaml_to_rest({"any-of": [{"type": "T", "reservable-only": True}]}),
                    "not allowed inside an any-of")
    _expect_refusal(lambda: selector_yaml_to_rest({"type": "T", "any-of": [{"type": "U"}]}), "both at the top")
    _expect_refusal(lambda: selector_yaml_to_rest({"type": "T", "reservable-only": "yes"}), "true or false")
    _expect_refusal(lambda: input_yaml_to_rest("N", {"type": "resource", "resource_selector": sel}), "REST spelling")
    _expect_refusal(lambda: parse_yaml_subset("a: &x 1\nb: *x\n"), "anchors")
    assert selector_yaml_to_rest({"type": "T", "reservable-only": "TRUE"}) == {"type": "T", "reservable_only": True}

    # pager: 170 records -> 80 + 80 + 10, take never above 80, both response shapes
    records = [{"id": f"r{i:03d}", "name": f"n{i:03d}"} for i in range(170)]
    calls: List[Dict[str, Any]] = []

    def fake(method: str, path: str, query: Dict[str, Any]) -> Tuple[int, Any]:
        calls.append(dict(query))
        assert method == "GET" and path == "/resource"
        skip, take = query["paging_info.skip"], query["paging_info.take"]
        assert take <= MAX_PAGE_SIZE
        page = records[skip:skip + take]
        if skip == 0:
            return 200, {"resources": page, "paging_info": {"full_count": len(records)}}
        return 200, page  # bare list on some builds
    got = list(iter_resources("Node", provider="p", request_fn=fake))
    assert [r["id"] for r in got] == [r["id"] for r in records]
    assert [c["paging_info.skip"] for c in calls] == [0, 80, 160], calls
    assert all(c["provider"] == "p" and c["type"] == "Node" for c in calls)
    try:
        list(iter_resources("Node", page=81, request_fn=fake))
        raise AssertionError("page=81 accepted")
    except ValueError:
        pass

    checks = 3
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        assert load_yaml_inputs(_FIXTURE) == inputs, "stdlib reader disagrees with PyYAML"
        checks += 1
    print(f"self-test OK ({checks} groups: YAML reader, conversions + refusals, pager"
          f"{', PyYAML cross-check' if yaml is not None else ''})")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--self-test", action="store_true", help="Run the offline checks (no network, no token) and exit.")
    args = p.parse_args()
    if args.self_test:
        return self_test()
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
