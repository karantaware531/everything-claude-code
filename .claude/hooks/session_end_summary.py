#!/usr/bin/env python3
"""session_end_summary.py — SessionEnd hook: emit a final session summary.

Runs on clean exit (logout, resume, clear, prompt_input_exit, bypass_permissions_disabled).
Writes a summary to ~/.claude/session-data/session-end-<timestamp>.json — a complement
to /save-session (which is user-driven) and precompact_state_saver.py (compaction-driven).

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
MEMORY = ROOT / "memory"
SESSION_DIR = Path.home() / ".claude" / "session-data"


def _safe_json(p: Path) -> dict | list | None:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return None


def _load_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def main() -> int:
    if DISABLED:
        return 0

    event = _load_event()
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    history = _safe_json(MEMORY / "agent_history.json")
    if isinstance(history, dict):
        entries = history.get("entries", [])
    elif isinstance(history, list):
        entries = history
    else:
        entries = []
    logs = _safe_json(MEMORY / "logs.json")
    if isinstance(logs, dict):
        log_entries = logs.get("entries", [])
    elif isinstance(logs, list):
        log_entries = logs
    else:
        log_entries = []
    goals = _safe_json(MEMORY / "goals_state.json") or {}

    summary = {
        "saved_at": now.isoformat(),
        "trigger": "session-end",
        "reason": event.get("reason", "unknown"),
        "goal_at_end": goals.get("current_goal"),
        "total_agent_invocations": len(entries),
        "total_logged_tasks": len(log_entries),
        "last_3_agents": [
            e.get("agent") for e in entries[-3:] if isinstance(e, dict)
        ],
        "last_3_outcomes": [
            e.get("outcome") for e in log_entries[-3:] if isinstance(e, dict)
        ],
    }

    out = SESSION_DIR / f"session-end-{timestamp}.json"
    try:
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass  # never fail on exit

    return 0


if __name__ == "__main__":
    sys.exit(main())
