#!/usr/bin/env python3
"""notification.py — Notification hook: desktop notify when Claude needs input.

Fires when Claude pauses for user action (permission approval, elicitation, etc.).
On Windows: uses msg.exe fallback. On macOS: osascript. On Linux: notify-send.
No-op if no notifier is available; always exit 0 (never blocks).

Disable: AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"


def _load_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def _notify(title: str, message: str) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{message}" with title "{title}"'],
                capture_output=True, timeout=5, check=False,
            )
        elif system == "Linux":
            if shutil.which("notify-send"):
                subprocess.run(
                    ["notify-send", title, message],
                    capture_output=True, timeout=5, check=False,
                )
        elif system == "Windows":
            # Best-effort: powershell toast notification
            ps_cmd = (
                f'$ErrorActionPreference="SilentlyContinue"; '
                f'[Windows.UI.Notifications.ToastNotificationManager,'
                f'Windows.UI.Notifications,ContentType=WindowsRuntime] | Out-Null; '
                f'Write-Host "[{title}] {message}"'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, timeout=5, check=False,
            )
    except Exception:  # noqa: BLE001
        pass  # never fail the hook


def main() -> int:
    if DISABLED:
        return 0

    event = _load_event()
    msg = event.get("message") or "Claude Code needs your attention"
    _notify("Agentic OS", msg[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
