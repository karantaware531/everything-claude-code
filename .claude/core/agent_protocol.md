# Agent Communication Protocol v1.0

> Every agent-to-agent message in this system MUST conform to this schema.
> Handoffs that don't produce a protocol record are treated as audit gaps
> (surfaced by the reflection agent).

## Message envelope

```json
{
  "from":         "<agent name>",
  "to":           "<agent name>",
  "task_id":      "<string>",
  "trace_id":     "<uuid4-string>",
  "kind":         "request | response | handoff | escalation",
  "context_ref":  "<sha256 hash of the context bundle used>",
  "timestamp":    "<ISO-8601 UTC>",
  "payload":      { ... kind-specific ... },
  "protocol_version": "1.0"
}
```

- `task_id` is assigned by the orchestrator at DAG creation and propagates to every descendant message.
- `trace_id` is per-message; forms a causal chain via `in_reply_to` (payload field).
- `context_ref` lets evaluators and auditors reconstruct *exactly what the agent saw*.

## Message kinds

### `request`
Caller asks a callee to perform work.

```json
{
  "kind": "request",
  "payload": {
    "capability": "<verb-phrase>",
    "input":      { ... typed per the callee's contract ... },
    "expected_output": { ... schema or free-text description ... },
    "deadline_ms": 60000,
    "retries_remaining": 2
  }
}
```

### `response`
Callee returns a result. Must cite the originating request's `trace_id` in `in_reply_to`.

```json
{
  "kind": "response",
  "payload": {
    "in_reply_to": "<request trace_id>",
    "status":      "success | partial | failure",
    "output":      { ... },
    "metrics":     { "duration_ms": 0, "tokens": 0 },
    "sources":     ["raw/github/foo.md", "concepts/bar.md"]
  }
}
```

### `handoff`
One agent passes control to another for a subsequent step. Differs from `request`
in that the current agent cedes ownership rather than awaiting a reply.

```json
{
  "kind": "handoff",
  "payload": {
    "reason":  "<why this agent cannot continue>",
    "context": { ... state to carry forward ... },
    "next":    "<agent name the orchestrator should route to>"
  }
}
```

### `escalation`
Signals that human intervention is required (circuit breaker tripped, irrecoverable evaluator failure, policy violation, etc).

```json
{
  "kind": "escalation",
  "payload": {
    "reason":           "<short classification>",
    "attempted_agents": ["..."],
    "last_error":       "<one-line>",
    "suggested_action": "<what the user might do>",
    "blocking":         true
  }
}
```

## Rules

1. **Every protocol record is appended to `observability/traces.json`.** Missing records are an audit gap.
2. **`from` and `to` must exist in `.claude/registry.json`.** Validator catches orphan references.
3. **`context_ref` must be reproducible.** Compute it as `sha256(json.dumps(context, sort_keys=True, ensure_ascii=False))`.
4. **Escalation is blocking.** The DAG pauses until the user responds.
5. **No free-form strings as `kind`.** The four listed are exhaustive.

## Backwards compatibility

The Claude Code subagent invocation pattern doesn't literally transmit these JSON
envelopes over the wire — they're recorded around each invocation by the execution
engine. Subagents still communicate via natural-language prompt/response; the protocol
layer is a **recording contract**, not a wire protocol. This keeps the system
working with the existing subagent substrate while giving us full auditability.

## Migration

- v1-era invocations (before this protocol) are recorded retroactively by
  `execution_engine` when replaying traces; missing `context_ref` is backfilled as
  `null` and flagged in summary output.
