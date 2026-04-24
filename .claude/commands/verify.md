# /verify

Run the 6-phase quality gate before marking any code change complete.

## When to Use
- Before committing any code change.
- Before running /review.
- Before marking a feature or fix as done.
- As the final step of any code_agent task.

## The 6 Phases

### Phase 1: Build
```bash
# Detect project type and run appropriate build
# Python: python -m py_compile <changed files>
# Node/TS: npm run build (or tsc --noEmit)
# Go: go build ./...
# Rust: cargo check
```
**Gate**: build must succeed. Any compile/parse error = FAIL immediately.

### Phase 2: Type Check
```bash
# Python: python -m mypy <changed files> (if mypy available)
# TypeScript: tsc --noEmit
# Go: go vet ./...
```
**Gate**: zero new type errors introduced by this change.

### Phase 3: Lint
```bash
# Python: python -m flake8 <changed files> (or ruff if available)
# JS/TS: npx eslint <changed files>
# Go: golangci-lint run (if available)
```
**Gate**: no new lint violations (existing violations allowed; only regressions fail).

### Phase 4: Test
```bash
# Run targeted tests for the changed module first
# Then run full test suite
python .claude/tools/test_runner.py   # Agentic OS system checks (must be 33/33)
```
**Gate**: no regressions. New functionality must have corresponding tests.

### Phase 5: Security Scan
Check for:
- [ ] No hardcoded secrets, API keys, or tokens in diff
- [ ] No new SQL/shell injection vectors
- [ ] No new unvalidated user inputs at trust boundaries
- [ ] `policy_guard` allows all new write paths

**Gate**: zero security issues introduced.

### Phase 6: Diff Review
Review the final diff:
- [ ] Change matches the stated intent
- [ ] No unintended file modifications
- [ ] No debug code, console.log, or TODO left in production paths
- [ ] Commit message follows conventional commit format

**Gate**: diff is clean and intentional.

## Output Format
```
VERIFY REPORT
─────────────
Phase 1 Build:      [PASS | FAIL] <details>
Phase 2 Type Check: [PASS | FAIL] <details>
Phase 3 Lint:       [PASS | FAIL] <details>
Phase 4 Tests:      [PASS | FAIL] <N/N passed>
Phase 5 Security:   [PASS | FAIL] <details>
Phase 6 Diff:       [PASS | FAIL] <details>

OVERALL: [PASS — safe to commit | FAIL — address before committing]
```

## On FAIL
- Return to code_agent with the specific failure details.
- Do NOT proceed to /review or commit until all 6 phases pass.
- If Phase 4 (tests) fails with test_runner regressions, route to /debug first.
