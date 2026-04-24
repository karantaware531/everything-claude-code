#!/usr/bin/env python3
"""
protocol_validator.py \u2014 stdlib JSON Schema validator for the agent protocol envelope.

Validates messages against core/protocol_schema.json. Implements the narrow
subset of JSON Schema draft-07 we actually use:

    type, required, additionalProperties, properties,
    enum, pattern, minLength, description (ignored).

No external deps. Used by agents (via tool_executor or directly) to catch
malformed envelopes before they hit the bus.

Usage (CLI):
    python protocol_validator.py --message '{"from":"a","to":"b",...}'
    python protocol_validator.py --message-file msg.json
    echo '<json>' | python protocol_validator.py --stdin

Exit codes:
    0 \u2014 valid
    1 \u2014 invalid (reasons on stdout, JSON)
    2 \u2014 usage error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
SCHEMA_PATH = ROOT / "core" / "protocol_schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


TYPE_MAP = {
    "string":  str,
    "number":  (int, float),
    "integer": int,
    "boolean": bool,
    "object":  dict,
    "array":   list,
    "null":    type(None),
}


def _check_type(value: Any, type_spec: str) -> bool:
    expected = TYPE_MAP.get(type_spec)
    if expected is None:
        return True  # unknown types are lenient — not our use case
    if type_spec == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def validate(instance: Any, schema: dict, path: str = "$") -> list[str]:
    """Return a list of error strings; empty list == valid."""
    errors: list[str] = []

    t = schema.get("type")
    if t and not _check_type(instance, t):
        errors.append(f"{path}: expected type {t}, got {type(instance).__name__}")
        return errors  # later checks assume correct type

    if t == "object":
        required = schema.get("required", []) or []
        if isinstance(instance, dict):
            for key in required:
                if key not in instance:
                    errors.append(f"{path}: missing required property '{key}'")

            props = schema.get("properties", {}) or {}
            allow_extra = schema.get("additionalProperties", True)
            if allow_extra is False:
                for key in instance.keys():
                    if key not in props:
                        errors.append(f"{path}: additional property '{key}' not allowed")

            for key, sub_schema in props.items():
                if key in instance:
                    errors.extend(validate(instance[key], sub_schema, f"{path}.{key}"))

    elif t == "array":
        items_schema = schema.get("items")
        if items_schema and isinstance(instance, list):
            for i, item in enumerate(instance):
                errors.extend(validate(item, items_schema, f"{path}[{i}]"))

    # String-specific checks
    if isinstance(instance, str):
        enum = schema.get("enum")
        if enum and instance not in enum:
            errors.append(f"{path}: value '{instance}' not in enum {enum}")

        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, instance):
            errors.append(f"{path}: does not match pattern '{pattern}'")

        min_len = schema.get("minLength")
        if min_len is not None and len(instance) < min_len:
            errors.append(f"{path}: length {len(instance)} < minLength {min_len}")

    # Number-specific checks (minimum/maximum if we ever add them)
    return errors


def _read_input(args: argparse.Namespace) -> Any:
    if args.stdin:
        raw = sys.stdin.read()
    elif args.message_file:
        raw = args.message_file.read_text(encoding="utf-8")
    elif args.message:
        raw = args.message
    else:
        raise SystemExit(2)
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message", type=str, help="JSON string")
    group.add_argument("--message-file", type=Path, help="path to JSON file")
    group.add_argument("--stdin", action="store_true", help="read JSON from stdin")
    args = parser.parse_args(argv)

    try:
        instance = _read_input(args)
    except json.JSONDecodeError as e:
        print(json.dumps({"valid": False, "errors": [f"JSON parse error: {e}"]}, indent=2))
        return 1

    schema = _load_schema()
    errors = validate(instance, schema)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "errors": []}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
