#!/usr/bin/env python3
"""
enforce_policy_on_write.py \u2014 PreToolUse(Write|Edit|MultiEdit) hook.

Hard enforcement of .claude/policies/security.yaml file_access.write rules.
Blocks writes to immutable / protected paths:
    * .env and .env.*
    * .git/**
    * .claude/CLAUDE.md
    * .claude/policies/**
    * .claude/wiki/raw/**   (immutable outside explicit ingestion)

Stdin tool_input keys accepted:
    * file_path     (Write, Edit)
    * notebook_path (NotebookEdit, if present)

Exit codes:
    0  \u2014 allow
    2  \u2014 BLOCK; stderr surfaced to Claude

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

TARGET_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _extract_target_path(tool_input: dict) -> str | None:
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if value:
            return str(value)
    # MultiEdit has a top-level file_path too; fall through is fine
    return None


def _normalise(path: str, cwd: str | None) -> str:
    """Turn an absolute path into a repo-relative POSIX path for policy matching."""
    p = Path(path)
    if cwd:
        try:
            rel = p.resolve().relative_to(Path(cwd).resolve())
            return rel.as_posix()
        except (ValueError, OSError):
            pass
    return str(path).replace("\\", "/")


def main() -> int:
    if os.environ.get("AGENTIC_OS_HOOKS_DISABLED"):
        return 0

    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    if event.get("tool_name") not in TARGET_TOOLS:
        return 0

    tool_input = event.get("tool_input") or {}
    target = _extract_target_path(tool_input)
    if not target:
        return 0

    norm = _normalise(target, event.get("cwd"))

    if not POLICY_GUARD.exists():
        return 0
    try:
        result = subprocess.run(
            [sys.executable, str(POLICY_GUARD), "--action", f"write:{norm}"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0

    if result.returncode == 0:
        return 0

    reason = "policy_guard denied this write"
    try:
        verdict = json.loads(result.stdout)
        reason = verdict.get("reason") or reason
    except json.JSONDecodeError:
        pass

    print(f"[hook:enforce_policy_on_write] BLOCKED: {reason}", file=sys.stderr)
    print(f"[hook:enforce_policy_on_write] target='{norm}'", file=sys.stderr)
    print("[hook:enforce_policy_on_write] This protects the constitution, policies, "
          "and wiki/raw immutability. Disable with AGENTIC_OS_HOOKS_DISABLED=1 only "
          "if you genuinely intend to amend a protected file.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
