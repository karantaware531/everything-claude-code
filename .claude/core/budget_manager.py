#!/usr/bin/env python3
"""
budget_manager.py \u2014 per-task token + time budget allocation and enforcement.

Used by execution_engine: before each node, call `exceeded(task_id)`. If true,
escalate. After each node, call `consume(task_id, tokens, time_ms)` so the
remaining budget reflects actual usage.

State persists to memory/budgets.json:

    active[task_id] = {tokens_allocated, tokens_used,
                       time_seconds_allocated, time_ms_used,
                       allocated_at, status}
    history[]       = closed (released or exceeded) tasks

Defaults from policies/config.yaml (budget.*).

Usage (CLI):
    python budget_manager.py --allocate "t-1" --tokens 1000 --time 60
    python budget_manager.py --consume "t-1" --tokens 200 --time-ms 5000
    python budget_manager.py --exceeded "t-1"
    python budget_manager.py --release "t-1"
    python budget_manager.py --status "t-1"
    python budget_manager.py --list

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
BUDGETS = ROOT / "memory" / "budgets.json"
CONFIG = ROOT / "policies" / "config.yaml"

DEFAULT_TOKENS = 50_000
DEFAULT_TIME_SECONDS = 600
HARD_CAP_TOKENS = 200_000
HARD_CAP_TIME_SECONDS = 1_800


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> dict:
    if not BUDGETS.exists():
        return {"version": 1, "updated_at": None, "active": {}, "history": []}
    try:
        return json.loads(BUDGETS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "updated_at": None, "active": {}, "history": []}


def _save(data: dict) -> None:
    BUDGETS.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    tmp = BUDGETS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(BUDGETS)


def _load_defaults() -> tuple[int, int, int, int]:
    """Return (default_tokens, default_seconds, hard_tokens, hard_seconds)."""
    if not CONFIG.exists():
        return DEFAULT_TOKENS, DEFAULT_TIME_SECONDS, HARD_CAP_TOKENS, HARD_CAP_TIME_SECONDS
    text = CONFIG.read_text(encoding="utf-8")
    in_budget = False
    in_hard = False
    out = [DEFAULT_TOKENS, DEFAULT_TIME_SECONDS, HARD_CAP_TOKENS, HARD_CAP_TIME_SECONDS]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        body = raw.strip().split("#", 1)[0].rstrip()
        if indent == 0:
            in_budget = body.startswith("budget:")
            in_hard = False
            continue
        if not in_budget:
            continue
        if body.startswith("hard_caps:"):
            in_hard = True
            continue
        if ":" not in body:
            continue
        key, _, value = body.partition(":")
        key = key.strip()
        value = value.strip()
        try:
            v = int(value)
        except ValueError:
            continue
        if not in_hard:
            if key == "default_tokens_per_task":
                out[0] = v
            elif key == "default_time_seconds_per_task":
                out[1] = v
        else:
            if key == "tokens":
                out[2] = v
            elif key == "time_seconds":
                out[3] = v
    return tuple(out)  # type: ignore[return-value]


def allocate(task_id: str, tokens: int | None = None, time_seconds: int | None = None) -> dict:
    dt, ds, ht, hs = _load_defaults()
    tokens_allocated = min(int(tokens) if tokens is not None else dt, ht)
    time_allocated = min(int(time_seconds) if time_seconds is not None else ds, hs)

    data = _load()
    data["active"][task_id] = {
        "tokens_allocated":     tokens_allocated,
        "tokens_used":          0,
        "time_seconds_allocated": time_allocated,
        "time_ms_used":         0,
        "allocated_at":         _now(),
        "status":               "open",
    }
    _save(data)
    return {"task_id": task_id, **data["active"][task_id]}


def consume(task_id: str, tokens: int = 0, time_ms: int = 0) -> dict:
    data = _load()
    if task_id not in data["active"]:
        return {"task_id": task_id, "error": "no active budget"}
    b = data["active"][task_id]
    b["tokens_used"]  = int(b.get("tokens_used", 0)) + max(0, int(tokens))
    b["time_ms_used"] = int(b.get("time_ms_used", 0)) + max(0, int(time_ms))
    _save(data)

    remaining_tokens = max(0, b["tokens_allocated"] - b["tokens_used"])
    remaining_time_seconds = max(0.0, b["time_seconds_allocated"] - b["time_ms_used"] / 1000.0)
    return {
        "task_id":          task_id,
        "tokens_used":      b["tokens_used"],
        "time_ms_used":     b["time_ms_used"],
        "remaining_tokens": remaining_tokens,
        "remaining_time_seconds": remaining_time_seconds,
        "status":           b.get("status", "open"),
    }


def exceeded(task_id: str) -> dict:
    data = _load()
    if task_id not in data["active"]:
        return {"task_id": task_id, "exceeded": False, "reason": "no active budget"}
    b = data["active"][task_id]
    over_tokens = b["tokens_used"] > b["tokens_allocated"]
    over_time = (b["time_ms_used"] / 1000.0) > b["time_seconds_allocated"]
    return {
        "task_id":  task_id,
        "exceeded": bool(over_tokens or over_time),
        "tokens_over": over_tokens,
        "time_over":   over_time,
        "tokens_used": b["tokens_used"],
        "tokens_allocated": b["tokens_allocated"],
        "time_seconds_used": round(b["time_ms_used"] / 1000.0, 2),
        "time_seconds_allocated": b["time_seconds_allocated"],
    }


def release(task_id: str, status: str = "released") -> dict:
    data = _load()
    if task_id not in data["active"]:
        return {"task_id": task_id, "error": "no active budget"}
    b = data["active"].pop(task_id)
    b["closed_at"] = _now()
    b["status"] = status
    data.setdefault("history", []).append({"task_id": task_id, **b})
    _save(data)
    return {"task_id": task_id, "released": True, **b}


def status(task_id: str) -> dict:
    data = _load()
    if task_id in data["active"]:
        return {"task_id": task_id, "where": "active", **data["active"][task_id]}
    for h in data.get("history", []):
        if h.get("task_id") == task_id:
            return {"task_id": task_id, "where": "history", **h}
    return {"task_id": task_id, "where": "unknown"}


def list_active() -> dict:
    data = _load()
    return {"count": len(data.get("active", {})), "tasks": list(data.get("active", {}).keys())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--allocate", metavar="TASK_ID")
    group.add_argument("--consume",  metavar="TASK_ID")
    group.add_argument("--exceeded", metavar="TASK_ID")
    group.add_argument("--release",  metavar="TASK_ID")
    group.add_argument("--status",   metavar="TASK_ID")
    group.add_argument("--list",     action="store_true")

    parser.add_argument("--tokens",  type=int, default=None)
    parser.add_argument("--time",    type=int, default=None, help="seconds (allocate)")
    parser.add_argument("--time-ms", type=int, default=0,    help="milliseconds (consume)")
    parser.add_argument("--reason",  type=str, default="released")

    args = parser.parse_args(argv)

    if args.allocate:
        print(json.dumps(allocate(args.allocate, args.tokens, args.time), indent=2)); return 0
    if args.consume:
        print(json.dumps(consume(args.consume, args.tokens or 0, args.time_ms), indent=2)); return 0
    if args.exceeded:
        result = exceeded(args.exceeded)
        print(json.dumps(result, indent=2))
        return 1 if result.get("exceeded") else 0
    if args.release:
        print(json.dumps(release(args.release, args.reason), indent=2)); return 0
    if args.status:
        print(json.dumps(status(args.status), indent=2)); return 0
    if args.list:
        print(json.dumps(list_active(), indent=2)); return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
