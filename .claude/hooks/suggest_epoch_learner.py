#!/usr/bin/env python3
"""
suggest_epoch_learner.py \u2014 Stop hook.

When Claude finishes a response, count how many agent invocations have been
recorded since the last epoch. If >= EPOCH_WINDOW, surface a reminder.

Cheap, non-blocking. Closes the reflection loop without requiring a human to
remember to run epoch_learner manually.

Disable with AGENTIC_OS_HOOKS_DISABLED=1.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
HISTORY = ROOT / "memory" / "agent_history.json"
PROFILE = ROOT / "memory" / "system_profile.json"

EPOCH_WINDOW = 20  # same default as epoch_learner.py


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def main() -> int:
    if os.environ.get("AGENTIC_OS_HOOKS_DISABLED"):
        return 0
    try:
        _ = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        pass

    history = _load(HISTORY, {"entries": []})
    profile = _load(PROFILE, {"updated_at": None, "epoch_count": 0})

    entries = history.get("entries", []) or []
    if not entries:
        return 0

    last_epoch_at = profile.get("updated_at")
    if last_epoch_at:
        try:
            cutoff = datetime.fromisoformat(last_epoch_at.replace("Z", "+00:00"))
        except ValueError:
            cutoff = None
    else:
        cutoff = None

    # Count entries newer than the last epoch's updated_at. If none, fall back
    # to total entries when epoch_count==0.
    if cutoff:
        since_epoch = 0
        for e in entries:
            ts = e.get("timestamp")
            if not ts:
                continue
            try:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if t > cutoff:
                since_epoch += 1
    else:
        since_epoch = len(entries) if int(profile.get("epoch_count", 0)) == 0 else 0

    if since_epoch >= EPOCH_WINDOW:
        print(f"[hook:suggest_epoch_learner] {since_epoch} agent invocations since last epoch "
              f"(threshold: {EPOCH_WINDOW}).")
        print("[hook:suggest_epoch_learner] Recommended: run "
              "`python .claude/core/epoch_learner.py --window 20` to refresh the self-profile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
