#!/usr/bin/env python3
"""install_plugins.py — idempotent installer for plugins listed in .claude/plugins-manifest.json.

Rationale: per v5.3 Council decision, we adopt plugins BY REFERENCE, not by copying.
This script reads the manifest and prints the exact `/plugin install ...` commands
the user should run inside Claude Code, OR (with --exec) attempts to run them via
the Claude Code CLI if available on PATH.

Usage:
    py -3 .claude/tools/install_plugins.py              # dry-run; print commands for 'core'
    py -3 .claude/tools/install_plugins.py --all        # core + optional
    py -3 .claude/tools/install_plugins.py --lsp python # add a language LSP
    py -3 .claude/tools/install_plugins.py --exec       # attempt to run commands via `claude` CLI
    py -3 .claude/tools/install_plugins.py --list       # show everything in the manifest

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REPO = ROOT.parent
MANIFEST = ROOT / "plugins-manifest.json"


def _load() -> dict:
    if not MANIFEST.exists():
        print(f"ERROR: {MANIFEST.relative_to(REPO)} missing", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: manifest invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def _collect(manifest: dict, args: argparse.Namespace) -> list[str]:
    plugins = manifest.get("plugins", {})
    selected: list[str] = []

    # Core is always included unless --list (no-op)
    core = plugins.get("core", {})
    for slug in core:
        if not slug.startswith("$"):
            selected.append(slug)

    if args.all:
        optional = plugins.get("optional", {})
        for slug in optional:
            if not slug.startswith("$"):
                selected.append(slug)

    if args.lsp:
        lsps = plugins.get("language-lsps", {})
        lsp_key = args.lsp.lower()
        for slug, info in lsps.items():
            if slug.startswith("$"):
                continue
            lang = info.get("language", "").lower()
            if lsp_key in lang or lsp_key == slug.split("-lsp")[0]:
                selected.append(slug)

    # Deduplicate, preserve order
    seen = set()
    deduped = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def _show_list(manifest: dict) -> None:
    plugins = manifest.get("plugins", {})
    for category, entries in plugins.items():
        if not isinstance(entries, dict):
            continue
        print(f"\n=== {category} ===")
        for slug, info in entries.items():
            if slug.startswith("$"):
                continue
            if isinstance(info, dict):
                why = info.get("why") or info.get("why_skip") or info.get("language") or ""
                print(f"  {slug:55s} {why[:60]}")


def _have_cli() -> bool:
    return shutil.which("claude") is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true",
                        help="Include optional plugins in addition to core.")
    parser.add_argument("--lsp", metavar="LANG",
                        help="Add an LSP plugin by language (e.g. 'python', 'rust', 'typescript').")
    parser.add_argument("--exec", action="store_true",
                        help="Attempt to execute the install commands via `claude` CLI.")
    parser.add_argument("--list", action="store_true",
                        help="Show the full manifest instead of installing.")
    args = parser.parse_args()

    manifest = _load()

    if args.list:
        _show_list(manifest)
        return 0

    to_install = _collect(manifest, args)
    if not to_install:
        print("No plugins selected. Use --all or --lsp <lang>.", file=sys.stderr)
        return 1

    marketplaces = manifest.get("marketplaces", {})

    print(f"\n# Plugin install plan ({len(to_install)} plugin(s))")
    print("#")
    print("# Paste these inside a Claude Code session, OR run this script with --exec if `claude` is on PATH.")
    print("#")

    commands = []
    for slug in to_install:
        # slug looks like "commit-commands@claude-plugins-official"
        if "@" not in slug:
            print(f"# WARN: {slug} lacks @marketplace suffix — skipping")
            continue
        name, _, marketplace = slug.partition("@")
        tmpl = marketplaces.get(marketplace, {}).get(
            "install_command_template",
            "/plugin install {plugin}@" + marketplace,
        )
        cmd = tmpl.format(plugin=name)
        commands.append((slug, cmd))
        print(f"{cmd}")

    if args.exec:
        if not _have_cli():
            print("\nERROR: `claude` CLI not found on PATH. Install Claude Code or paste the commands above into an interactive session.", file=sys.stderr)
            return 2
        print("\n# Executing via `claude` CLI...")
        ok = 0
        for slug, cmd in commands:
            try:
                r = subprocess.run(["claude", cmd], capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    print(f"[OK] {slug}")
                    ok += 1
                else:
                    print(f"[FAIL] {slug}: {r.stderr[:200]}")
            except Exception as e:  # noqa: BLE001
                print(f"[ERROR] {slug}: {e}")
        print(f"\n{ok}/{len(commands)} installed.")
        return 0 if ok == len(commands) else 1

    print(f"\n# Next: paste each line above into a Claude Code session, or re-run with --exec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
