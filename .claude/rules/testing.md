---
paths:
  - "**/*_test.py"
  - "**/test_*.py"
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*.test.js"
  - "tests/**/*.py"
---

# Testing Conventions

## Mandatory before marking any change complete
1. `python .claude/tools/test_runner.py` — full system check (must be green).
2. Targeted module tests first, then full suite.
3. No new lint/type regressions introduced by this change.

## Python
- `pytest` preferred; `unittest` acceptable.
- Test files: `test_<module>.py` or `<module>_test.py`.
- Parametrize with `@pytest.mark.parametrize`; keep fixtures explicit.
- No real network in tests; mock external services.
- No real credentials/tokens; use `conftest.py` fixtures.

## TypeScript / JavaScript
- `vitest` preferred over `jest` for speed; either acceptable.
- Test files colocated: `foo.test.ts` next to `foo.ts`.
- Mock via `vi.mock()` (vitest) / `jest.mock()`.
- Prefer type-level tests for generics (`expect-type`).

## Hard rules (all languages)
- **Never delete or skip a failing test** to make the suite green. Fix the code or fix the test with justification.
- **Write failing test first** for bug fixes (reproducer), then fix.
- **No flaky tests** — intermittent failures must be rooted out, not retried.
- **Assertions are specific**: `assert x == 42`, not `assert x`.
- **One assertion per test** is ideal; multiple OK if all testing one behavior.
