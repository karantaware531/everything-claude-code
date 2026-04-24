#!/usr/bin/env python3
"""
precompact_state_saver.py — PreCompact hook: save session state before context compaction.

Adapted from everything-claude-code's session persistence architecture.

Context compaction discards the conversation history but keeps the summary.
This hook fires just before compaction, ensuring critical session state is
preserved in a structured format that a future session can load.

What it saves:
  - Current task context (from memory/goals_state.json)
  - Recent agent invocation summary (from memory/agent_history.json)
  - Active budget state (from memory/budgets.json)
  - Session metadata (timestamp, invocation count, last agent used)

Output:
  ~/.claude/session-data/pre-compact-<timestamp>.json
  + a human-readable summary printed to stdout

Exit codes:
  0 = always (this hook never blocks)

Disable: set AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"

# Resolve .claude/ directory relative to this script
HOOKS_DIR = Path(__file__).resolve().parent
ROOT = HOOKS_DIR.parent          # .claude/
MEMORY = ROOT / "memory"

# Session data dir (outside .claude/ to avoid Karpathy invariant — it's in home dir)
SESSION_DIR = Path.home() / ".claude" / "session-data"


def _safe_read_json(path: Path) -> dict | list | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return None


def _get_goals_context() -> dict:
    data = _safe_read_json(MEMORY / "goals_state.json") or {}
    return {
        "current_goal": data.get("current_goal"),
        "subgoals": data.get("subgoals", []),
        "completed_subgoals": data.get("completed_subgoals", []),
    }


def _get_recent_agents(n: int = 10) -> list[dict]:
    data = _safe_read_json(MEMORY / "agent_history.json") or []
    if isinstance(data, list):
        recent = data[-n:] if len(data) > n else data
        return [
            {
                "agent": e.get("agent"),
                "task_id": e.get("task_id"),
                "success": e.get("success"),
                "timestamp": e.get("timestamp"),
            }
            for e in recent
            if isinstance(e, dict)
        ]
    return []


def _get_active_budgets() -> dict:
    data = _safe_read_json(MEMORY / "budgets.json") or {}
    active = data.get("active", {})
    return {
        tid: {
            "tokens_remaining": b.get("tokens_remaining"),
            "time_remaining_s": b.get("time_remaining_s"),
        }
        for tid, b in active.items()
        if isinstance(b, dict)
    } if isinstance(active, dict) else {}


def _count_invocations_since_epoch() -> int:
    profile = _safe_read_json(MEMORY / "system_profile.json") or {}
    history = _safe_read_json(MEMORY / "agent_history.json") or []
    epoch_count = profile.get("epoch_count", 0)
    # Approximate: count entries in history
    return len(history) if isinstance(history, list) else 0


def main() -> int:
    if DISABLED:
        return 0

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "saved_at": now.isoformat(),
        "trigger": "pre-compact",
        "goals": _get_goals_context(),
        "recent_agents": _get_recent_agents(10),
        "active_budgets": _get_active_budgets(),
        "total_invocations": _count_invocations_since_epoch(),
        "resume_hint": (
            "Session was compacted. Check goals.current_goal for where you left off. "
            "Check recent_agents for the last agent called. "
            "Run /save-session after resuming to capture full structured context."
        ),
    }

    out_path = SESSION_DIR / f"pre-compact-{timestamp}.json"
    try:
        out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        print(
            f"[PreCompact] Session state saved: {out_path}\n"
            f"  Goal: {snapshot['goals'].get('current_goal') or 'none set'}\n"
            f"  Last agents: {[a.get('agent') for a in snapshot['recent_agents'][-3:]]}\n"
            f"  Invocations this epoch: {snapshot['total_invocations']}"
        )
    except Exception as e:  # noqa: BLE001
        print(f"[PreCompact] Warning: could not save session state: {e}")

    return 0  # Never block


if __name__ == "__main__":
    sys.exit(main())
