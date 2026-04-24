# /review

Run a full quality review on the current changes: critic red-teaming, evaluator grading, and security scan.

## When to Use
After writing or editing code. Before marking any feature complete. Before committing.

## Steps

1. **Gather scope** — identify changed files (git diff or recent edits).

2. **Research context** — invoke `research_agent` to read the changed files and identify:
   - All functions/classes modified
   - All callers and dependents of those functions
   - Relevant test files
   - Security boundaries crossed (auth, I/O, network, filesystem)

3. **GateGuard gate** — before proceeding, confirm:
   - [ ] All file dependencies listed
   - [ ] All affected function signatures documented
   - [ ] Schema or type changes identified
   - [ ] Rollback path known

4. **Critic pass** — invoke `critic` agent with full context:
   - Check correctness (logic, edge cases, off-by-one, null handling)
   - Check security (injection, auth bypass, secrets in output, OWASP Top 10)
   - Check values alignment (see `policies/values.yaml`)
   - Severity: CRITICAL / HIGH / MEDIUM / LOW

5. **Evaluator pass** — invoke `evaluator` agent:
   - Grade against: correctness, completeness, hallucination risk
   - Emit uncertainty score
   - Verdict: PASS / FAIL / RETRYABLE

6. **Security agent** (if critic flags any HIGH/CRITICAL security findings):
   - Invoke `security` agent for deep contextual analysis
   - Check prompt injection vectors, novel threat patterns

7. **Report** — produce structured output:
   ```
   REVIEW VERDICT: [PASS | FAIL]
   Critic findings: <count> issues (<count> CRITICAL, <count> HIGH)
   Evaluator score: <0-1>
   Security: [CLEAN | REVIEW NEEDED]
   Required fixes before proceeding: <list or "none">
   ```

8. **On PASS** — update wiki:
   - If a new pattern was discovered: route to `reflection`
   - Log trace to `observability/traces.json`

9. **On FAIL** — return structured critique for the code_agent to address.

## Anti-Patterns
- Do NOT skip the GateGuard gate (step 3) — self-evaluation is unreliable without prior investigation.
- Do NOT run critic before gathering full dependency context (step 2).
- Do NOT pass evaluator verdict to wiki without critic sign-off first.
