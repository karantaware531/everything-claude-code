#!/usr/bin/env python3
"""
environment_sensor.py \u2014 stdlib environment probe.

Tracks (with a TTL cache) which tools are actually available, which shell
dependencies are on PATH, and a coarse view of recent failure rates per tool.
Gives the system situational awareness without ML or external services.

Usage (CLI):
    python environment_sensor.py --probe              # refresh and print state
    python environment_sensor.py --probe --force      # bypass TTL
    python environment_sensor.py --check git          # is `git` reachable?
    python environment_sensor.py --tool-status repo_ingestor

Persists to .claude/memory/environment_state.json.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
ENV_STATE = ROOT / "memory" / "environment_state.json"
TOOL_REGISTRY = ROOT / "tools" / "tool_registry.json"
TOOLS_DIR = ROOT / "tools"
HISTORY = ROOT / "memory" / "agent_history.json"

DEFAULT_TTL_SECONDS = 300

# Shell dependencies the system relies on.
SHELL_DEPS = ["git", "python", "python3"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def _save(state: dict) -> None:
    ENV_STATE.parent.mkdir(parents=True, exist_ok=True)
    state["probed_at"] = _now_iso()
    state["wall_clock"] = _now_iso()
    tmp = ENV_STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(ENV_STATE)


def _is_fresh(state: dict, ttl_seconds: int) -> bool:
    probed_at = state.get("probed_at")
    if not probed_at:
        return False
    try:
        t = datetime.fromisoformat(probed_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    age = (datetime.now(timezone.utc) - t).total_seconds()
    return age < ttl_seconds


def _check_tools() -> dict:
    """For each registered tool, check the file exists and is readable."""
    out: dict = {}
    if not TOOL_REGISTRY.exists():
        return out
    try:
        reg = json.loads(TOOL_REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return out
    for tool in reg.get("tools", []) or []:
        name = tool.get("name")
        rel_path = tool.get("path", "")
        path = ROOT.parent / rel_path if rel_path else None
        out[name] = {
            "path":        str(rel_path),
            "exists":      bool(path and path.exists()),
            "network":     bool(tool.get("network", False)),
            "safety":      tool.get("safety_level"),
        }
    return out


def _check_shell_deps() -> dict:
    return {dep: bool(shutil.which(dep)) for dep in SHELL_DEPS}


def _recent_failures() -> dict:
    """Tally per-tool recent failures from agent_history.json (last 50 entries)."""
    out: dict = {}
    history = _load(HISTORY, {"entries": []})
    entries = history.get("entries", [])[-50:]
    for entry in entries:
        if entry.get("success") is False:
            agent = entry.get("agent", "?")
            out[agent] = int(out.get(agent, 0)) + 1
    return out


def probe(force: bool = False, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict:
    state = _load(ENV_STATE, {
        "version": 1, "probed_at": None, "ttl_seconds": ttl_seconds,
        "tools": {}, "shell_dependencies": {}, "recent_failures": {}, "wall_clock": None,
    })
    if not force and _is_fresh(state, ttl_seconds):
        return {"cached": True, **state}

    state["ttl_seconds"]        = ttl_seconds
    state["tools"]              = _check_tools()
    state["shell_dependencies"] = _check_shell_deps()
    state["recent_failures"]    = _recent_failures()
    _save(state)
    return {"cached": False, **state}


def check_dep(name: str) -> dict:
    return {name: bool(shutil.which(name)), "found_at": shutil.which(name)}


def tool_status(name: str) -> dict:
    state = probe()
    tools = state.get("tools", {}) or {}
    if name not in tools:
        return {"name": name, "registered": False}
    return {"name": name, "registered": True, **tools[name]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--probe", action="store_true")
    group.add_argument("--check", metavar="DEP")
    group.add_argument("--tool-status", metavar="NAME")
    parser.add_argument("--force", action="store_true", help="ignore TTL on --probe")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS)
    args = parser.parse_args(argv)

    if args.probe:
        result = probe(force=args.force, ttl_seconds=args.ttl)
        print(json.dumps(result, indent=2))
        return 0
    if args.check:
        print(json.dumps(check_dep(args.check), indent=2))
        return 0
    if args.tool_status:
        print(json.dumps(tool_status(args.tool_status), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
