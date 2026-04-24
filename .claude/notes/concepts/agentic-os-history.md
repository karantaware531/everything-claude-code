---
domain: concepts
slug: agentic-os-history
first_observed: 2026-04-24T00:00:00Z
last_updated: 2026-04-24T00:00:00Z
confidence: 1.0
---

# Agentic OS - Complete Version History (v1 -> v5.5)

Full evolution record. Live constitution carries only canonical rules; this file carries every what-changed narrative.

## Version summary

| Version | Date | Theme |
|---|---|---|
| v1.0 | bootstrap | orchestrator + agents + wiki |
| v2.0 | - | Core engine, 4-layer hierarchy, knowledge graph, observability, policies, agent protocol, feedback loops, Wiki-is-Primary-Memory |
| v3.0 | - | Adaptive autonomy via 3 epistemic loops (uncertainty, goals, truth); autonomy tiers 1-4; agent evolution (merge) |
| v4.0 | - | Self-modeling: system_profile + wiki/self/, reward.py, values.yaml + critic.values_check, budget_manager, world_model, environment_sensor, architecture_optimizer (tier 4), debate_moderator, representations interface |
| v5.0 | 2026-04-20 | Deliberative: utility.py EU scoring, strategy_generator + strategy_explorer (K candidates), pattern_extractor, wiki/consensus/, consolidator, domain_policies, keyword-tfidf, forecast |
| v5.1 | 2026-04-22 | ECC integration. GateGuard +2.25 quality. PreCompact persistence. Council anti-anchoring. harness_audit. Root CLAUDE.md/AGENTS.md/RULES.md/.mcp.json. 8 new commands. |
| v5.2 | 2026-04-24 | LLM Wiki removed. Graphify v0.5.0. wiki_compiler+wiki_updater+wiki_curator retired. graphify_agent added. 22 agents. |
| v5.3 | 2026-04-24 | Specialist Government: 92 plugin specialists in SPECIALISTS.md (by reference). /commit commands. |
| v5.4 | 2026-04-24 | Anthropic canonical alignment. rules/ path-scoped. skills/ scaffold. 5 new hooks. permissions block. autoMemoryEnabled. .worktreeinclude. 5 governance agents hardened. |
| v5.4.1 | 2026-04-24 | security_reminder_hook: 9 content vuln patterns blocked at Write. |
| v5.4.2 | 2026-04-24 | Remaining 17 agents canonicalized. All 22 carry tools/model/memory/color/maxTurns. |
| **v5.5** | **2026-04-24** | **Lead Agent + Consensus Government.** Constitution 725 to ~200 lines. Orchestrator retired (main session = Lead Agent). Agent Teams enabled. defaultMode=acceptEdits. 5-agent Council with ship veto. rules/permission-modes.md + rules/routing.md. 21 agents. |

## v5.4.1 security patterns detail

Integrated from Anthropic security-guidance plugin. PreToolUse hook blocks 9 content patterns at Write/Edit:

1. JS eval( - arbitrary code execution
2. JS new Function( - dynamic code injection
3. Node child_process.exec and execSync - shell injection
4. React dangerouslySetInnerHTML - XSS
5. DOM .innerHTML = - XSS
6. DOM document.write - XSS
7. Python pickle - deserialization RCE
8. Python os.system - shell injection
9. GitHub Actions dollar-brace-brace github.event dot * in run: blocks - workflow injection

Session-scoped dedup; Windows-portable via tempfile.gettempdir; AGENTIC_OS_HOOKS_DISABLED=1 kill switch.

## Consensus decisions

- v5.3-specialist-integration.md - adopt voltagent by reference
- v5.4-anthropic-best-practices.md - 10 doc alignment
- v5.5-lead-agent-government.md - retire orchestrator, Council veto, acceptEdits, Agent Teams

## Amendment log (tier-4)

| Date | Amendment | Type |
|---|---|---|
| 2026-04-22 | Hooks + sec 5 amended | constitution_amendment |
| 2026-04-22 | security.yaml allowlist | policy_amendment |
| 2026-04-22 | v5.1 sec 33 ECC | constitution_amendment |
| 2026-04-24 | Wiki to Graphify | constitution_amendment |
| 2026-04-24 | v5.3 sec 35 Specialist | constitution_amendment |
| 2026-04-24 | v5.4 sec 36 Anthropic | constitution_amendment |
| 2026-04-24 | v5.4.1 security hook | policy_amendment |
| 2026-04-24 | v5.5 diet + Lead + Council + acceptEdits + Teams | constitution_amendment |

## Honest retirements

Not every v2-v5 feature active: simulation_history (rarely queried), world_model observe/predict (few callers), representations sha-placeholder (fallback), architecture_optimizer (tier 4 rare by design). Remain for back-compat.
