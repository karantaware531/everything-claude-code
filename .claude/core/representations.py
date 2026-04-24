#!/usr/bin/env python3
"""
representations.py \u2014 embedding INTERFACE for the agentic system.

HONEST SCOPE: this is an interface, not a real embedder. Without pip deps,
genuine semantic embeddings (sentence-transformers, OpenAI embeddings, etc.)
are out of reach. The default backend is `sha-placeholder`: deterministic,
fast, and *useless for semantic similarity* \u2014 documented as such.

The contribution here is the **interface**. Future Phase 3 work plugs in a
real backend by setting:

    AGENTIC_OS_EMBEDDING_BACKEND=<name>

and registering it in `BACKENDS` below.

Public surface:

    embed(text)               -> list[float]   # always 32-dim
    similarity(a, b)          -> float in [0, 1]    # cosine
    backend()                 -> str           # which backend is active

CLI:
    python representations.py --embed "hello"
    python representations.py --similarity "hello" "hello"
    python representations.py --backend
    python representations.py --self-test

Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

VECTOR_DIM = 32
TFIDF_DIM = 512

ROOT = Path(__file__).resolve().parents[1]  # .claude/
CORPUS_DF = ROOT / "memory" / "corpus_df.json"

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "by", "for", "with", "as", "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "it", "its", "this", "that", "these", "those", "i",
    "you", "he", "she", "we", "they", "them", "their", "our", "my", "me", "us",
    "do", "does", "did", "will", "would", "should", "can", "could", "may",
    "might", "must", "so", "than", "then", "into", "from", "up", "down", "out",
    "over", "under",
}


def _tokenise(text: str) -> list[str]:
    # lowercase \u2192 strip punctuation \u2192 split \u2192 drop stopwords + short tokens
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def _bucket(token: str) -> int:
    """Hash a token into a fixed dim via SHA-256 \u2192 int \u2192 modulo."""
    h = hashlib.sha256(token.encode("utf-8")).digest()
    # Take first 4 bytes as big-endian int
    return int.from_bytes(h[:4], "big") % TFIDF_DIM


def _load_df() -> dict:
    if not CORPUS_DF.exists():
        return {"version": 1, "doc_count": 0, "document_frequency": {}}
    try:
        return json.loads(CORPUS_DF.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "doc_count": 0, "document_frequency": {}}


def _keyword_tfidf_embed(text: str) -> list[float]:
    """
    Keyword-TFIDF backend. Tokenise, hash into TFIDF_DIM buckets, weight by
    inverse document frequency from the streaming corpus table (if available).

    This is a genuine semantic signal (topical overlap) \u2014 not neural, but
    useful, deterministic, and dependency-free.
    """
    tokens = _tokenise(text)
    if not tokens:
        return [0.0] * TFIDF_DIM

    # Term frequency
    tf: dict[int, float] = {}
    for t in tokens:
        b = _bucket(t)
        tf[b] = tf.get(b, 0.0) + 1.0
    # Normalise TF
    max_tf = max(tf.values())
    for b in tf:
        tf[b] /= max_tf

    df = _load_df()
    n_docs = max(1, int(df.get("doc_count", 0)))
    df_table = df.get("document_frequency", {}) or {}

    vec = [0.0] * TFIDF_DIM
    for t in set(tokens):
        b = _bucket(t)
        df_count = int(df_table.get(t, 1))
        idf = math.log(1.0 + n_docs / df_count)
        vec[b] += tf.get(b, 0.0) * idf

    # L2-normalise
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def update_corpus(text: str) -> dict:
    """Incorporate a document into the streaming DF table."""
    tokens = set(_tokenise(text))
    df = _load_df()
    df["doc_count"] = int(df.get("doc_count", 0)) + 1
    df_table = df.setdefault("document_frequency", {})
    for t in tokens:
        df_table[t] = int(df_table.get(t, 0)) + 1
    df["updated_at"] = _now_iso()
    CORPUS_DF.parent.mkdir(parents=True, exist_ok=True)
    tmp = CORPUS_DF.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(df, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(CORPUS_DF)
    return {"doc_count": df["doc_count"], "unique_tokens": len(df_table)}


def _now_iso() -> str:
    from datetime import datetime, timezone  # local import \u2014 stdlib-only elsewhere
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha_embed(text: str) -> list[float]:
    """
    Placeholder: SHA-256 of the input text \u2192 32 floats in [0, 1].
    Useful only for cache-key-style identity. NOT semantic.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # 32 bytes \u2192 32 floats. Each byte / 255 \u2192 [0, 1].
    return [b / 255.0 for b in digest]


# Future backends register themselves here. The CLI / library always returns the
# active backend via env var override; default = sha-placeholder.
BACKENDS = {
    "sha-placeholder": {
        "embed": _sha_embed,
        "dim":   VECTOR_DIM,
        "semantic": False,
        "notes": "deterministic SHA-256 hash; NOT a real embedding. Useless for semantic similarity.",
    },
    "keyword-tfidf": {
        "embed": _keyword_tfidf_embed,
        "dim":   TFIDF_DIM,
        "semantic": True,       # topical overlap only; not full neural semantics
        "notes": "Hashed-bucket TF-IDF over tokenised text. Captures topical overlap; "
                 "deterministic, stdlib-only. Populate corpus via update_corpus() for better IDF.",
    },
    # Add real neural backends here. Same shape; different `embed` + `dim`.
    # e.g. "openai-text-embedding-3-small": {"embed": fn, "dim": 1536, "semantic": True, ...}
}


def backend() -> str:
    name = os.environ.get("AGENTIC_OS_EMBEDDING_BACKEND", "sha-placeholder")
    if name not in BACKENDS:
        return "sha-placeholder"
    return name


def embed(text: str) -> list[float]:
    return BACKENDS[backend()]["embed"](text)


def embed_dim() -> int:
    return int(BACKENDS[backend()]["dim"])


def similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [0, 1] (assuming non-negative vectors)."""
    if len(a) != len(b):
        raise ValueError(f"vector dim mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    sim = dot / (na * nb)
    # Clip to [0, 1] (handles tiny numerical excursions).
    return round(max(0.0, min(1.0, sim)), 4)


def _self_test() -> int:
    e1 = embed("hello")
    e2 = embed("hello")
    e3 = embed("world")
    if len(e1) != embed_dim():
        print(json.dumps({"ok": False, "reason": f"dim != {embed_dim()}"}))
        return 1
    if e1 != e2:
        print(json.dumps({"ok": False, "reason": "embed not deterministic"}))
        return 1
    if similarity(e1, e2) < 0.999:
        print(json.dumps({"ok": False, "reason": "self-similarity not ~1"}))
        return 1
    if similarity(e1, e3) > 0.99:
        print(json.dumps({"ok": False, "reason": "different texts unexpectedly identical"}))
        return 1
    print(json.dumps({
        "ok":           True,
        "backend":      backend(),
        "dim":          embed_dim(),
        "self_sim":     similarity(e1, e2),
        "diff_sim":     similarity(e1, e3),
        "is_semantic":  BACKENDS[backend()]["semantic"],
        "notes":        BACKENDS[backend()]["notes"],
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--embed", metavar="TEXT")
    group.add_argument("--similarity", nargs=2, metavar=("A", "B"))
    group.add_argument("--backend", action="store_true")
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--corpus-update", metavar="TEXT",
                       help="incorporate a document into the streaming DF table (improves IDF for keyword-tfidf)")
    args = parser.parse_args(argv)

    if args.embed:
        vec = embed(args.embed)
        print(json.dumps({"backend": backend(), "dim": len(vec), "vector": vec}, indent=2))
        return 0
    if args.similarity:
        a, b = args.similarity
        sim = similarity(embed(a), embed(b))
        print(json.dumps({"a": a, "b": b, "similarity": sim, "backend": backend()}, indent=2))
        return 0
    if args.backend:
        active = backend()
        print(json.dumps({"active": active, "all": list(BACKENDS.keys()),
                          "info": BACKENDS[active]}, indent=2, default=str))
        return 0
    if args.self_test:
        return _self_test()
    if args.corpus_update:
        print(json.dumps(update_corpus(args.corpus_update), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
