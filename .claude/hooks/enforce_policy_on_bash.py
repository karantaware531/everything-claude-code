#!/usr/bin/env python3
"""
enforce_policy_on_bash.py \u2014 PreToolUse(Bash) hook.

Hard enforcement of .claude/policies/security.yaml shell patterns. Complements
(and upgrades) the advisory policy_guard: this hook runs BEFORE the Bash tool
and can block execution (exit 2) when a denied pattern is matched.

Closes the "policy_guard is advisory, not enforced" gap from CLAUDE.md \u00a74.

Stdin (from Claude Code):
    {"session_id","transcript_path","cwd","hook_event_name":"PreToolUse",
     "tool_name":"Bash","tool_input":{"command":"...","description":"..."}}

Exit codes:
    0  \u2014 allow (and fail-open on any error)
    2  \u2014 BLOCK; stderr is surfaced to Claude as the rejection reason

Disable with AGENTIC_OS_HOOKS_DISABLED=1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
POLICY_GUARD = ROOT / "tools" / "policy_guard.py"


def main() -> int:
    if os.environ.get("AGENTIC_OS_HOOKS_DISABLED"):
        return 0

    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0  # fail-open on malformed stdin

    if event.get("tool_name") != "Bash":
        return 0

    cmd = (event.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # Consult policy_guard.
    if not POLICY_GUARD.exists():
        return 0  # fail-open if policy layer not present
    try:
        result = subprocess.run(
            [sys.executable, str(POLICY_GUARD), "--action", f"shell:{cmd}"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0  # fail-open

    if result.returncode == 0:
        return 0  # allowed

    # Denied \u2014 parse the verdict for the reason and block.
    reason = "policy_guard denied this command"
    try:
        verdict = json.loads(result.stdout)
        reason = verdict.get("reason") or reason
    except json.JSONDecodeError:
        pass

    # stderr is shown to Claude as the block reason; exit 2 blocks the tool.
    print(f"[hook:enforce_policy_on_bash] BLOCKED: {reason}", file=sys.stderr)
    print(f"[hook:enforce_policy_on_bash] command='{cmd[:200]}'", file=sys.stderr)
    print("[hook:enforce_policy_on_bash] Disable this hook with AGENTIC_OS_HOOKS_DISABLED=1 "
          "if you know why you want to bypass.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
