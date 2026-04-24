#!/usr/bin/env python3
"""
repo_ingestor.py — ingest a GitHub repository into the wiki's raw/ layer.

What it does:
    1. Shallow-clones the target repo (git clone --depth=1) into a temp directory.
    2. Extracts README(s) and a curated set of representative source files.
    3. Writes a single markdown bundle to .claude/wiki/raw/github/<owner>-<repo>.md.
    4. Optionally triggers wiki_compiler.py on the freshly written raw file.
    5. Logs the ingestion to .claude/memory/logs.json.

Raw is immutable — re-ingesting an already-seen repo will write a new timestamped
file rather than overwriting, preserving historical context.

Usage:
    python repo_ingestor.py --url https://github.com/owner/repo
    python repo_ingestor.py --url <url> --no-compile
    python repo_ingestor.py --url <url> --max-files 15 --max-bytes-per-file 50000

Stdlib only. Requires `git` on PATH.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
RAW_GITHUB = ROOT / "wiki" / "raw" / "github"
LOGS = ROOT / "memory" / "logs.json"
WIKI_COMPILER = ROOT / "tools" / "wiki_compiler.py"

DEFAULT_MAX_FILES = 20
DEFAULT_MAX_BYTES_PER_FILE = 40_000
DEFAULT_CLONE_TIMEOUT = 120  # seconds

# Extensions prioritised in this order. Keep the list small — we're building a
# knowledge dossier, not mirroring the source tree.
SOURCE_EXTENSIONS = [
    ".md",   # extra READMEs, docs
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".yaml",
    ".yml",
    ".toml",
]

SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv", ".next", "target", "vendor"}


def sh(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)


def parse_owner_repo(url: str) -> tuple[str, str]:
    """Extract owner and repo from a GitHub URL. Accepts https:// and git@."""
    cleaned = url.strip().rstrip("/").removesuffix(".git")
    m = re.search(r"[:/]([^/:]+)/([^/]+)$", cleaned)
    if not m:
        raise ValueError(f"Cannot parse owner/repo from URL: {url}")
    return m.group(1), m.group(2)


def shallow_clone(url: str, dst: Path, timeout: int) -> None:
    result = sh(["git", "clone", "--depth=1", "--single-branch", url, str(dst)], timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr.strip() or result.stdout.strip()}")


def find_readmes(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for p in root.rglob("README*"):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
            candidates.append(p)
    # root README first, then others, capped
    candidates.sort(key=lambda p: (len(p.relative_to(root).parts), str(p)))
    return candidates[:3]


def find_source_files(root: Path, max_files: int) -> list[Path]:
    """Prioritised flat list. Prefer shallow paths, known entrypoints."""
    priority_names = {"main.py", "index.ts", "index.js", "app.py", "server.py",
                      "main.go", "main.rs", "lib.rs", "Cargo.toml", "pyproject.toml",
                      "package.json", "pom.xml", "go.mod"}

    found: list[Path] = []
    # First pass: priority names at shallow depths
    for p in sorted(root.rglob("*"), key=lambda x: (len(x.relative_to(root).parts), str(x))):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name in priority_names:
            found.append(p)
            if len(found) >= max_files:
                return found

    # Second pass: extension-matched files at shallow depths
    for ext in SOURCE_EXTENSIONS:
        if len(found) >= max_files:
            break
        for p in sorted(root.rglob(f"*{ext}"), key=lambda x: (len(x.relative_to(root).parts), str(x))):
            if len(found) >= max_files:
                break
            if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.name.lower().startswith("readme"):
                continue  # already captured
            if p in found:
                continue
            found.append(p)

    return found


def read_trimmed(p: Path, max_bytes: int) -> tuple[str, bool]:
    """Read text, trimming to max_bytes. Returns (text, truncated)."""
    try:
        raw = p.read_bytes()
    except OSError as e:
        return f"<unable to read: {e}>", False
    truncated = len(raw) > max_bytes
    raw = raw[:max_bytes]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return text, truncated


def build_bundle(owner: str, repo: str, url: str, clone_root: Path,
                 readmes: list[Path], sources: list[Path], max_bytes: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        f"# {owner}/{repo}",
        "",
        f"- Source: {url}",
        f"- Ingested: {now}",
        f"- Clone depth: 1",
        "",
        "## READMEs",
        "",
    ]
    if not readmes:
        lines.append("_no README found_")
    else:
        for p in readmes:
            rel = p.relative_to(clone_root).as_posix()
            text, trunc = read_trimmed(p, max_bytes)
            lines.append(f"### `{rel}`" + (" _(truncated)_" if trunc else ""))
            lines.append("")
            lines.append(text.rstrip())
            lines.append("")

    lines.append("## Selected source files")
    lines.append("")
    if not sources:
        lines.append("_no source files selected_")
    else:
        for p in sources:
            rel = p.relative_to(clone_root).as_posix()
            text, trunc = read_trimmed(p, max_bytes)
            fence = p.suffix.lstrip(".") or ""
            lines.append(f"### `{rel}`" + (" _(truncated)_" if trunc else ""))
            lines.append("")
            lines.append(f"```{fence}")
            lines.append(text.rstrip())
            lines.append("```")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _append_log(entry: dict) -> None:
    LOGS.parent.mkdir(parents=True, exist_ok=True)
    if LOGS.exists():
        try:
            data = json.loads(LOGS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"entries": [], "version": 1}
    else:
        data = {"entries": [], "version": 1}
    data.setdefault("entries", []).append(entry)
    tmp = LOGS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(LOGS)


def trigger_compile(raw_path: Path) -> dict:
    if not WIKI_COMPILER.exists():
        return {"compiled": False, "reason": "wiki_compiler.py missing"}
    result = sh([sys.executable, str(WIKI_COMPILER), "--raw", str(raw_path)],
                timeout=120)
    return {
        "compiled": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="GitHub repo URL")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-bytes-per-file", type=int, default=DEFAULT_MAX_BYTES_PER_FILE)
    parser.add_argument("--clone-timeout", type=int, default=DEFAULT_CLONE_TIMEOUT)
    parser.add_argument("--no-compile", action="store_true", help="skip wiki_compiler call")
    args = parser.parse_args(argv)

    try:
        owner, repo = parse_owner_repo(args.url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    RAW_GITHUB.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = RAW_GITHUB / f"{owner}-{repo}-{timestamp}.md"

    with tempfile.TemporaryDirectory(prefix="repo-ingest-") as tmp:
        clone_root = Path(tmp) / repo
        try:
            shallow_clone(args.url, clone_root, args.clone_timeout)
        except subprocess.TimeoutExpired:
            print(f"ERROR: git clone timed out after {args.clone_timeout}s", file=sys.stderr)
            _append_log({"tool": "repo_ingestor", "url": args.url, "outcome": "clone_timeout",
                         "timestamp": datetime.now(timezone.utc).isoformat()})
            return 3
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            _append_log({"tool": "repo_ingestor", "url": args.url, "outcome": "clone_failed",
                         "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
            return 4

        readmes = find_readmes(clone_root)
        sources = find_source_files(clone_root, args.max_files)
        bundle = build_bundle(owner, repo, args.url, clone_root, readmes, sources, args.max_bytes_per_file)
        tmp_out = out_file.with_suffix(".md.tmp")
        tmp_out.write_text(bundle, encoding="utf-8", newline="\n")
        tmp_out.replace(out_file)

    compile_report = {"compiled": False, "skipped": True}
    if not args.no_compile:
        compile_report = trigger_compile(out_file)

    log_entry = {
        "tool": "repo_ingestor",
        "url": args.url,
        "owner": owner,
        "repo": repo,
        "raw_file": str(out_file.relative_to(ROOT.parent) if ROOT.parent in out_file.parents else out_file),
        "files_selected": len(readmes) + len(sources),
        "compiled": compile_report.get("compiled", False),
        "outcome": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_log(log_entry)

    print(json.dumps({
        "raw_file": str(out_file),
        "readmes": [str(p.name) for p in readmes],
        "sources_selected": len(sources),
        "compile": compile_report,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
