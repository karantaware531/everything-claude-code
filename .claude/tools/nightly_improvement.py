#!/usr/bin/env python3
"""nightly_improvement.py - Daily self-improvement loop.

Authorized by Council session v5.6 (2026-04-24).

Every scheduled fire (default: 16:03 local daily):
1. Fetch current versions of 10 canonical Claude Code docs.
2. Diff against cached synthesis at .claude/notes/concepts/claude-code-best-practices-v5.4.md.
3. Generate proposals for gaps / new features -> .claude/notes/concepts/proposals/nightly-<YYYY-MM-DD>.md.
4. Submit to Consensus Council via protocol envelope -> observability/traces.json.
5. Tier-1-2 changes: auto-apply + log. Tier-3+: surface to user next session.
6. Summary -> memory/logs.json with outcome=nightly_improvement_run.

Kill switch: AGENTIC_OS_NIGHTLY_DISABLED=1
Dry-run: python .claude/tools/nightly_improvement.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REPO = ROOT.parent
NOTES = ROOT / "notes"
MEMORY = ROOT / "memory"
TRACES = ROOT / "observability" / "traces.json"
PROPOSALS_DIR = NOTES / "concepts" / "proposals"
CACHED_SYNTHESIS = NOTES / "concepts" / "claude-code-best-practices-v5.4.md"

DOC_URLS = [
    "https://code.claude.com/docs/en/overview",
    "https://code.claude.com/docs/en/features-overview",
    "https://code.claude.com/docs/en/claude-directory",
    "https://code.claude.com/docs/en/context-window",
    "https://code.claude.com/docs/en/memory",
    "https://code.claude.com/docs/en/permission-modes",
    "https://code.claude.com/docs/en/best-practices",
    "https://code.claude.com/docs/en/sub-agents",
    "https://code.claude.com/docs/en/agent-teams",
    "https://code.claude.com/docs/en/hooks-guide",
]

SEARCH_QUERIES: list[str] = [
    # Agentic AI — General
    "Claude Code best practices 2025",
    "agentic AI development patterns 2025",
    "LLM agent orchestration best practices",
    "multi-agent system design patterns",
    "ReAct agent loop improvements",
    "LLM tool use best practices",
    "autonomous AI agent production patterns",
    "AI agent memory management strategies",
    # .claude folder & CLAUDE.md
    "CLAUDE.md best practices examples",
    ".claude folder structure best practices",
    "Claude Code hooks examples",
    "Claude Code sub-agents patterns",
    "Claude Code memory files tips",
    "Claude Code settings.json configuration",
    # MCP
    "MCP server best practices 2025",
    "Model Context Protocol new tools",
    "FastMCP server patterns",
    "MCP tool schema design",
    # Skills & Agents
    "Claude Code skills system",
    "Claude Code agent registry patterns",
    "LLM skill routing best practices",
    # Observability
    "LLM observability tracing production",
    "Langfuse tracing best practices",
    "AI agent audit logging patterns",
    # Security
    "prompt injection defense techniques 2025",
    "LLM agent security guardrails",
    "agentic AI trust boundaries",
    # Stack-specific
    "LangGraph ReAct node optimization",
    "Temporal workflow AI agent patterns",
    "Ollama tool calling production tips",
    "AWS Bedrock agent best practices",
    # Domain-specific
    "AI compliance surveillance automation",
    "trade alert enrichment AI patterns",
    "market manipulation detection AI",
]

# Council roster (per CLAUDE.md §5)
COUNCIL = ["critic", "evaluator", "security", "reflection", "knowledge_validator"]


def log_traces(entry: dict) -> None:
    """Append a protocol envelope to observability/traces.json."""
    try:
        TRACES.parent.mkdir(parents=True, exist_ok=True)
        if TRACES.exists():
            data = json.loads(TRACES.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(entry)
        TRACES.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass  # never fail on observability


def log_memory(entry: dict) -> None:
    """Append an outcome record to memory/logs.json."""
    lg = MEMORY / "logs.json"
    try:
        if lg.exists():
            data = json.loads(lg.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {"version": 1, "entries": []}
        else:
            data = {"version": 1, "entries": []}
        data.setdefault("entries", []).append(entry)
        lg.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def fetch_url(url: str, timeout: int = 20) -> str | None:
    """Fetch a URL; return text content or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "agentic-os-nightly-improvement/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return raw.decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                return raw.decode("latin-1", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]


def load_cached_hashes() -> dict:
    """Load the previous run's doc hashes."""
    cache_file = MEMORY / "nightly_doc_hashes.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_cached_hashes(hashes: dict) -> None:
    (MEMORY / "nightly_doc_hashes.json").write_text(
        json.dumps(hashes, indent=2), encoding="utf-8"
    )


def diff_docs() -> dict:
    """Fetch each doc, compare hash to previous run, return dict of changed docs."""
    previous = load_cached_hashes()
    current: dict[str, str] = {}
    changed: dict[str, dict] = {}
    errors: list[str] = []

    for url in DOC_URLS:
        content = fetch_url(url)
        if content is None:
            errors.append(url)
            continue
        h = content_hash(content)
        current[url] = h
        if previous.get(url) != h:
            # First run: previous is empty -> everything "changed"
            change_kind = "new" if previous.get(url) is None else "modified"
            changed[url] = {
                "hash": h,
                "previous_hash": previous.get(url),
                "change_kind": change_kind,
                "content_sample": content[:500],
            }

    save_cached_hashes(current)
    return {"changed": changed, "errors": errors, "total_fetched": len(current)}


def _ddg_search(query: str, limit: int = 5) -> list[str]:
    """Return up to `limit` result URLs from DuckDuckGo HTML search (no API key)."""
    encoded = urllib.parse.urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{encoded}"
    html = fetch_url(url)
    if not html:
        return []
    urls: list[str] = []
    for href in re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', html):
        if href.startswith("//duckduckgo.com/l/"):
            m = re.search(r"[?&]uddg=([^&]+)", href)
            if m:
                href = urllib.parse.unquote(m.group(1))
        if href.startswith("http"):
            urls.append(href)
        if len(urls) >= limit:
            break
    return urls


def search_pass() -> dict:
    """Run SEARCH_QUERIES via DuckDuckGo, fetch unseen URLs, return findings dict."""
    cache_file = MEMORY / "nightly_search_hashes.json"
    try:
        seen: dict[str, str] = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    except Exception:  # noqa: BLE001
        seen = {}

    updated_seen: dict[str, str] = dict(seen)
    found: dict[str, dict] = {}
    errors: list[str] = []
    new_urls = 0

    for query in SEARCH_QUERIES:
        for url in _ddg_search(query, limit=5):
            url_key = content_hash(url)
            if url_key in seen:
                continue
            new_urls += 1
            content = fetch_url(url)
            if content is None:
                errors.append(url)
                updated_seen[url_key] = "error"
                continue
            h = content_hash(content)
            updated_seen[url_key] = h
            found[url] = {
                "query": query,
                "hash": h,
                "previous_hash": None,
                "change_kind": "new",
                "content_sample": content[:500],
            }

    try:
        cache_file.write_text(json.dumps(updated_seen, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    return {"found": found, "errors": errors, "new_urls": new_urls,
            "total_queries": len(SEARCH_QUERIES)}


def generate_proposal(changed: dict, date_str: str) -> Path:
    """Emit a proposal markdown file to .claude/notes/concepts/proposals/."""
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    out = PROPOSALS_DIR / f"nightly-{date_str}.md"

    lines: list[str] = [
        "---",
        "domain: concepts",
        f"slug: nightly-{date_str}",
        f"first_observed: {datetime.now(timezone.utc).isoformat()}",
        f"last_updated: {datetime.now(timezone.utc).isoformat()}",
        "confidence: 0.7",
        "task_id: nightly-improvement-run",
        "supersedes: []",
        "---",
        "",
        f"# Nightly Improvement Proposal - {date_str}",
        "",
        "Automated daily scan of Claude Code canonical docs. Changes detected vs",
        "cached baseline in `.claude/notes/concepts/claude-code-best-practices-v5.4.md`.",
        "",
        f"## Docs changed this run: {len(changed)}",
        "",
    ]

    if not changed:
        lines.append("No changes detected. Baseline is current.")
    else:
        for url, info in changed.items():
            name = url.rsplit("/", 1)[-1]
            lines.append(f"### `{name}` ({info['change_kind']})")
            lines.append(f"- Source: {url}")
            lines.append(f"- Hash: `{info['previous_hash']}` -> `{info['hash']}`")
            lines.append(f"- First 500 chars of current:")
            lines.append("")
            lines.append("```")
            # Neutralize any code fences in sample to prevent markdown breakage
            sample = info["content_sample"].replace("```", "'''")
            lines.append(sample)
            lines.append("```")
            lines.append("")

    lines.extend([
        "",
        "## Proposed Council action",
        "",
        "1. Council reviews this proposal (critic + evaluator at minimum).",
        "2. If diff reveals new canonical feature / pattern not in our system:",
        "   - Tier 1-2 (docs, minor rule updates): auto-apply; log as `nightly_auto_apply`.",
        "   - Tier 3+ (new hooks, constitution edit, new agents): surface to user on next session.",
        "3. If diff is cosmetic only (typo fixes, formatting): log + skip.",
        "",
        "## Routing",
        "",
        "Submitted to Consensus Council via protocol envelope; trace in",
        "`observability/traces.json` with `kind: nightly_proposal`.",
    ])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def submit_to_council(proposal_path: Path, changed: dict) -> dict:
    """Emit a protocol envelope for each Council member. Return synthesis verdict."""
    now = datetime.now(timezone.utc).isoformat()
    task_id = f"nightly-{now[:10]}"
    trace_id = f"nightly-{content_hash(now)}"

    for member in COUNCIL:
        entry = {
            "from": "hook:nightly_improvement",
            "to": member,
            "task_id": task_id,
            "trace_id": f"{trace_id}-{member}",
            "kind": "nightly_proposal",
            "context_ref": content_hash(proposal_path.read_text(encoding="utf-8")),
            "timestamp": now,
            "payload": {
                "proposal_file": str(proposal_path.relative_to(REPO)),
                "changes_detected": len(changed),
                "urls": list(changed.keys()),
            },
            "protocol_version": "1.0",
        }
        log_traces(entry)

    # Synthesis rule: nightly run is advisory. Verdict is always
    # "log + wait for next interactive session for Council deliberation",
    # except when zero changes -> no-op, don't bother Council.
    if not changed:
        return {"verdict": "no_op", "reason": "no changes detected"}
    return {
        "verdict": "await_next_session",
        "reason": "Council members will review proposal on next interactive session. "
                  "Tier-3+ actions require user approval; Council will synthesize findings "
                  "into an amendment proposal if adoption is recommended.",
        "proposal_file": str(proposal_path.relative_to(REPO)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nightly improvement routine (Council-authorized v5.6)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch + diff but don't write proposal or logs.")
    args = parser.parse_args()

    if os.environ.get("AGENTIC_OS_NIGHTLY_DISABLED", "").strip() == "1":
        print("[nightly] kill switch active (AGENTIC_OS_NIGHTLY_DISABLED=1); exiting")
        return 0

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    started = datetime.now(timezone.utc).isoformat()
    print(f"[nightly] {started} starting doc diff sweep")

    result = diff_docs()
    changed = result["changed"]
    errors = result["errors"]

    print(f"[nightly] fetched: {result['total_fetched']}/{len(DOC_URLS)} docs")
    if errors:
        print(f"[nightly] errors fetching: {len(errors)} (URLs unreachable)")
    print(f"[nightly] changes detected: {len(changed)}")

    # Step 1b — search pass
    sr = search_pass()
    print(f"[nightly] search pass: {sr['total_queries']} queries, "
          f"{sr['new_urls']} new URLs, {len(sr['found'])} fetched")
    changed.update(sr["found"])
    errors.extend(sr["errors"])

    if args.dry_run:
        print("[nightly] --dry-run: not writing proposal or logs")
        return 0

    if not changed:
        # No-op: still log the run for observability
        log_memory({
            "task_id": f"nightly-{date_str}",
            "timestamp": started,
            "outcome": "nightly_improvement_run",
            "changes_detected": 0,
            "errors": errors,
            "verdict": "no_op",
        })
        print("[nightly] no changes; logged and exiting")
        return 0

    proposal_path = generate_proposal(changed, date_str)
    print(f"[nightly] proposal written: {proposal_path.relative_to(REPO)}")

    verdict = submit_to_council(proposal_path, changed)
    print(f"[nightly] Council: {verdict['verdict']}")

    # Trigger graphify update so the proposal enters the knowledge graph
    try:
        import subprocess
        subprocess.run(
            ["py", "-3", "-m", "graphify", str(NOTES), "--update"],
            capture_output=True, timeout=120, check=False, cwd=str(REPO)
        )
    except Exception:  # noqa: BLE001
        pass  # non-fatal

    log_memory({
        "task_id": f"nightly-{date_str}",
        "timestamp": started,
        "outcome": "nightly_improvement_run",
        "changes_detected": len(changed),
        "changed_urls": list(changed.keys()),
        "errors": errors,
        "proposal_file": str(proposal_path.relative_to(REPO)),
        "verdict": verdict["verdict"],
    })

    print(f"[nightly] done; summary logged to memory/logs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
