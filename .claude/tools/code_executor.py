#!/usr/bin/env python3
"""
code_executor.py — runs untrusted Python in an isolated subprocess.

Usage:
    python code_executor.py --source "print(2+2)"
    python code_executor.py --file snippet.py
    python code_executor.py --file snippet.py --timeout 5

Safety posture:
    1. Static denylist on dangerous tokens (open, os.system, subprocess, socket, eval, exec, __import__).
    2. Runs in a subprocess so the parent interpreter is insulated from sys.exit / segfaults.
    3. Hard wall-clock timeout (default 10s, max 60s).
    4. Captures stdout/stderr; no shared filesystem handles.

This is defense-in-depth, not a full sandbox. The real isolation comes from
the Claude Code agent permission model and the read-only default in CLAUDE.md.
Never feed arbitrary user input to this tool without a trust boundary upstream.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_TIMEOUT = 60
DEFAULT_TIMEOUT = 10
MAX_SOURCE_LEN = 50_000  # bytes

# Tokens that make a snippet ineligible for execution.
# Regex because "open(" is a call; bare "open" would false-positive on comments.
DENY_PATTERNS = [
    (r"\bopen\s*\(", "file I/O via open()"),
    (r"\bos\.system\b", "shell via os.system"),
    (r"\bos\.popen\b", "shell via os.popen"),
    (r"\bsubprocess\b", "subprocess module"),
    (r"\bsocket\b", "network via socket"),
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"__import__\s*\(\s*['\"]os['\"]", "dynamic import of os"),
    (r"__import__\s*\(\s*['\"]subprocess['\"]", "dynamic import of subprocess"),
    (r"\bcompile\s*\(", "compile()"),
    (r"\bglobals\s*\(\s*\)\s*\[", "globals() mutation"),
    (r"\bbuiltins\b", "builtins access"),
]


def scan(source: str) -> list[str]:
    """Return a list of rejection reasons; empty list == allowed."""
    reasons: list[str] = []
    if len(source.encode("utf-8")) > MAX_SOURCE_LEN:
        reasons.append(f"source exceeds {MAX_SOURCE_LEN} bytes")
    for pattern, label in DENY_PATTERNS:
        if re.search(pattern, source):
            reasons.append(f"disallowed token: {label}")
    return reasons


def execute(source: str, timeout: int) -> dict:
    """Run source in a subprocess. Return structured result."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(source)
        tmp = Path(tf.name)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-S", str(tmp)],  # -I: isolated; -S: no site
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "stderr": (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            "timed_out": True,
        }
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", type=str, help="inline Python source")
    group.add_argument("--file", type=Path, help="path to a Python file")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"timeout seconds (max {MAX_TIMEOUT})")
    args = parser.parse_args(argv)

    if args.timeout < 1 or args.timeout > MAX_TIMEOUT:
        print(f"ERROR: timeout must be in [1, {MAX_TIMEOUT}]", file=sys.stderr)
        return 2

    source = args.source if args.source else args.file.read_text(encoding="utf-8")

    reasons = scan(source)
    if reasons:
        print(json.dumps({"ok": False, "rejected": True, "reasons": reasons}, indent=2))
        return 3

    result = execute(source, args.timeout)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
