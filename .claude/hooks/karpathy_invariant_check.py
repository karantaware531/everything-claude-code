#!/usr/bin/env python3
"""
karpathy_invariant_check.py \u2014 PostToolUse(Write|Edit|MultiEdit|NotebookEdit) hook.

After any write, verify the Karpathy invariant holds:

    find .claude/memory -name '*.md'   \u2192  must be empty.

Narrative knowledge belongs in wiki/; memory/ is JSON-only transactional state.

Soft enforcement: prints a warning to stdout (surfaced to Claude) if a .md
file appears under memory/. Does NOT block the tool \u2014 the hook fires after
the write, and erring here would just strand half-done work. Warning gets
Claude's attention to remediate in the next turn.

Exit codes:
    0 always (never blocks).

Disable with AGENTIC_OS_HOOKS_DISABLED=1.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
MEMORY = ROOT / "memory"


def main() -> int:
    if os.environ.get("AGENTIC_OS_HOOKS_DISABLED"):
        return 0
    try:
        _ = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        pass  # still run the invariant check even on malformed stdin

    if not MEMORY.exists():
        return 0

    md_files = list(MEMORY.rglob("*.md"))
    if not md_files:
        return 0

    offenders = [str(p.relative_to(ROOT.parent) if ROOT.parent in p.parents else p)
                 for p in md_files]
    print("[hook:karpathy_invariant] WARNING: markdown files appeared under "
          ".claude/memory/. Knowledge artefacts belong in .claude/wiki/ "
          "(concepts/strategies/experience/...).")
    for p in offenders:
        print(f"  - {p}")
    print("[hook:karpathy_invariant] Suggested fix: move content into wiki/ via "
          "`wiki_compiler.py --raw <staged> --domain <concepts|strategies|experience|...>` "
          "then delete the memory/*.md file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
