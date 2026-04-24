#!/usr/bin/env python3
"""config_change_audit.py — ConfigChange hook: audit log for in-session config mutations.

Fires when settings.json, skills/commands, or agent files change DURING a session.
Appends an audit entry to memory/logs.json with outcome="config_change".

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
LOGS = ROOT / "memory" / "logs.json"


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
    entry = {
        "task_id": "config-change-audit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outcome": "config_change",
        "source": event.get("source", "unknown"),
        "file_path": event.get("file_path", "unknown"),
        "change_kind": event.get("change_kind") or event.get("kind", "unknown"),
    }

    try:
        if LOGS.exists():
            data = json.loads(LOGS.read_text(encoding="utf-8"))
        else:
            data = {"version": 1, "entries": []}
        if not isinstance(data, dict):
            data = {"version": 1, "entries": []}
        data.setdefault("entries", []).append(entry)
        LOGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"[ConfigChange audit] warning: could not write log: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
