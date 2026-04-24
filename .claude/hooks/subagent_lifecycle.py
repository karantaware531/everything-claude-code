#!/usr/bin/env python3
"""subagent_lifecycle.py — SubagentStart + SubagentStop hook.

Appends a lifecycle event to observability/traces.json for every subagent spawn
and completion. Complements the existing agent_history.json tracking (which is
task-level) with fine-grained subagent invocation tracing.

Exit 0 always; never blocks.
Disable: AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"

ROOT = Path(__file__).resolve().parent.parent  # .claude/
TRACES = ROOT / "observability" / "traces.json"


def _load_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def _append_trace(entry: dict) -> None:
    try:
        TRACES.parent.mkdir(parents=True, exist_ok=True)
        if TRACES.exists():
            data = json.loads(TRACES.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(entry)
        TRACES.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass  # never fail


def main() -> int:
    if DISABLED:
        return 0

    event = _load_event()
    event_name = event.get("hook_event_name") or event.get("event") or "SubagentLifecycle"
    subagent = event.get("subagent") or event.get("agent") or "unknown"

    trace = {
        "from": "hook:subagent_lifecycle",
        "to": subagent,
        "task_id": event.get("task_id", "unknown"),
        "trace_id": f"subagent-{event_name.lower()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "kind": "subagent_lifecycle",
        "context_ref": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "event": event_name,
            "subagent": subagent,
            "duration_ms": event.get("duration_ms"),
            "outcome": event.get("outcome"),
        },
        "protocol_version": "1.0",
    }
    _append_trace(trace)

    return 0


if __name__ == "__main__":
    sys.exit(main())
