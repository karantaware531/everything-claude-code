#!/usr/bin/env python3
"""
tool_registry.py — typed tool catalogue.

Reads .claude/tools/tool_registry.json. Tools are identified by name; each entry
declares capabilities, inputs/outputs, network access, and a safety level
({"safe", "guarded", "unsafe"}).

Agents (especially `tool_executor`) consult this before invoking anything.

Usage (CLI):
    python tool_registry.py --list
    python tool_registry.py --get wiki_compiler
    python tool_registry.py --find "ingest"        # keyword search over capabilities

Usage (library):
    from tool_registry import list_tools, get, find

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REGISTRY = ROOT / "tools" / "tool_registry.json"


def _load() -> dict:
    if not REGISTRY.exists():
        return {"version": 1, "tools": []}
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "tools": []}


def list_tools() -> list[dict]:
    return _load().get("tools", []) or []


def get(name: str) -> dict | None:
    for t in list_tools():
        if t.get("name") == name:
            return t
    return None


def find(keyword: str) -> list[dict]:
    kw = keyword.lower()
    hits: list[dict] = []
    for t in list_tools():
        blob = " ".join([
            str(t.get("name", "")),
            " ".join(t.get("capabilities", []) or []),
        ]).lower()
        if kw in blob:
            hits.append(t)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--get", metavar="NAME")
    group.add_argument("--find", metavar="KEYWORD")
    args = parser.parse_args(argv)

    if args.list:
        tools = list_tools()
        print(json.dumps({"count": len(tools), "tools": [t.get("name") for t in tools]}, indent=2))
        return 0
    if args.get:
        t = get(args.get)
        if not t:
            print(json.dumps({"name": args.get, "found": False}))
            return 1
        print(json.dumps(t, indent=2))
        return 0
    if args.find:
        print(json.dumps({"query": args.find, "hits": find(args.find)}, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
