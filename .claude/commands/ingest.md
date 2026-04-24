# /ingest

Pull a GitHub repository (or local file) into the Agentic OS knowledge wiki.

## When to Use
When you want Claude to deeply understand a codebase, paper, doc set, or library
and have that knowledge persist across sessions via the wiki.

## Steps

1. **Receive target** — accept one of:
   - GitHub URL: `https://github.com/OWNER/REPO`
   - Local file path: `/path/to/doc.md` or `/path/to/paper.pdf`

2. **Policy check** — repo_ingestor is the ONLY network-allowed tool.
   Verify the URL is a valid GitHub repo before proceeding.

3. **Ingest** — run repo_ingestor via tool_executor:
   ```bash
   python .claude/tools/repo_ingestor.py --url <URL> --max-files 100
   ```
   Output: raw bundle at `wiki/raw/github/<owner>-<repo>-<timestamp>.md`

4. **Compile concepts** — run wiki_compiler:
   ```bash
   python .claude/tools/wiki_compiler.py \
     --raw wiki/raw/github/<bundle>.md \
     --domain concepts
   ```
   Output: concept files in `wiki/concepts/`, updated `wiki/graph/graph.json`

5. **Update IDF corpus** — for better keyword-TFIDF similarity:
   ```bash
   python .claude/core/representations.py \
     --corpus-update "$(cat wiki/raw/github/<bundle>.md)"
   ```

6. **Curate** — invoke `wiki_curator` to:
   - Link new concepts via `[[wiki-links]]`
   - Update `wiki/index.md`
   - Surface any contradictions with existing concepts

7. **Report** — print:
   ```
   INGESTED: <repo URL>
   CONCEPTS CREATED: <n>
   GRAPH NODES ADDED: <n>
   CONTRADICTIONS FLAGGED: <n> (route to knowledge_validator if any)
   RAW BUNDLE: wiki/raw/github/<slug>.md
   ```

## Notes
- `wiki/raw/**` is IMMUTABLE after ingestion — never edit the bundle.
- Max files per ingest: 100 (configurable via `--max-files`).
- All network calls are logged to `memory/logs.json`.
- If contradiction count > 0, run `/knowledge-validate` next.
