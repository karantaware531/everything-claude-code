# SPECIALISTS.md — The Specialist Registry (v5.3)

> 84 voltagent specialists + 7 gitnexus + 1 graphify — **all auto-loaded** via Claude Code plugins.
> Our 21 governance/cognitive/execution/meta agents ROUTE tasks here based on domain. Do NOT duplicate these into `.claude/agents/`.

---

## Routing Rule

When a task has a clear domain match below, the Planning Council (v5.7, via `/lead-agent`) assigns the specialist.
When no match, fall back to our generic agents: `code_agent`, `research_agent`, `tool_executor`.
**Governance (critic, evaluator, security, reflection, knowledge_validator) stays ours — never route to voltagent equivalents.**

---

## voltagent-lang (30 language specialists)

| Task domain | Specialist |
|---|---|
| Python (type-safe, async, web APIs) | `voltagent-lang:python-pro` |
| TypeScript (advanced types, generics) | `voltagent-lang:typescript-pro` |
| JavaScript (modern ES2023+, Node.js) | `voltagent-lang:javascript-pro` |
| Go (concurrent, microservices) | `voltagent-lang:golang-pro` |
| Rust (memory safety, zero-cost) | `voltagent-lang:rust-engineer` |
| C++ (C++20/23, template metaprog) | `voltagent-lang:cpp-pro` |
| C# / .NET Core / ASP.NET | `voltagent-lang:csharp-developer`, `voltagent-lang:dotnet-core-expert` |
| .NET Framework 4.8 (legacy) | `voltagent-lang:dotnet-framework-4.8-expert` |
| Java / Spring Boot | `voltagent-lang:java-architect`, `voltagent-lang:spring-boot-engineer` |
| Kotlin (coroutines, multiplatform) | `voltagent-lang:kotlin-specialist` |
| Swift (iOS, macOS, server-side) | `voltagent-lang:swift-expert` |
| PHP 8.3+ / Laravel / Symfony | `voltagent-lang:php-pro`, `voltagent-lang:laravel-specialist`, `voltagent-lang:symfony-specialist` |
| Ruby / Rails | `voltagent-lang:rails-expert` |
| Elixir / OTP / Phoenix | `voltagent-lang:elixir-expert` |
| Django (Python web) | `voltagent-lang:django-developer` |
| FastAPI (async Python) | `voltagent-lang:fastapi-developer` |
| React / Next.js / Angular / Vue | `voltagent-lang:react-specialist`, `voltagent-lang:nextjs-developer`, `voltagent-lang:angular-architect`, `voltagent-lang:vue-expert` |
| Flutter / Expo (mobile) | `voltagent-lang:flutter-expert`, `voltagent-lang:expo-react-native-expert` |
| PowerShell 5.1 / 7+ | `voltagent-lang:powershell-5.1-expert`, `voltagent-lang:powershell-7-expert` |
| SQL (PostgreSQL, MySQL, SQL Server, Oracle) | `voltagent-lang:sql-pro` |

## voltagent-dev-exp (15 developer-experience specialists)

| Task | Specialist |
|---|---|
| Refactoring (preserve behavior, reduce debt) | `voltagent-dev-exp:refactoring-specialist` |
| Legacy system modernization | `voltagent-dev-exp:legacy-modernizer` |
| MCP server design / implementation | `voltagent-dev-exp:mcp-developer` |
| Technical documentation (API, tutorials) | `voltagent-dev-exp:documentation-engineer` |
| README generation (no hallucination) | `voltagent-dev-exp:readme-generator` |
| Dependency audit / vulnerability scan | `voltagent-dev-exp:dependency-manager` |
| Git workflow / branching / merge strategy | `voltagent-dev-exp:git-workflow-manager` |
| Build performance (compile times, scaling) | `voltagent-dev-exp:build-engineer` |
| Developer workflow optimization | `voltagent-dev-exp:dx-optimizer` |
| CLI tool design | `voltagent-dev-exp:cli-developer` |
| Tooling / code generators / build tools | `voltagent-dev-exp:tooling-engineer` |
| PowerShell module architecture | `voltagent-dev-exp:powershell-module-architect` |
| PowerShell UI (WinForms/WPF/TUI) | `voltagent-dev-exp:powershell-ui-architect` |
| Slack app / bot development | `voltagent-dev-exp:slack-expert` |

## voltagent-qa-sec (16 QA & security specialists)

| Task | Specialist |
|---|---|
| Code review (language-agnostic security + performance) | `voltagent-qa-sec:code-reviewer` *(use alongside our `critic`, not instead)* |
| Security audit (vulnerabilities, compliance) | `voltagent-qa-sec:security-auditor` |
| Penetration testing (active exploitation) | `voltagent-qa-sec:penetration-tester` |
| Active Directory security | `voltagent-qa-sec:ad-security-reviewer` |
| PowerShell security hardening | `voltagent-qa-sec:powershell-security-hardening` |
| Compliance (GDPR, HIPAA, PCI, SOC 2, ISO) | `voltagent-qa-sec:compliance-auditor` |
| Accessibility (WCAG, assistive tech) | `voltagent-qa-sec:accessibility-tester` |
| Architecture review (macro design) | `voltagent-qa-sec:architect-reviewer` |
| Chaos engineering / failure experiments | `voltagent-qa-sec:chaos-engineer` |
| Debugging (error analysis, root cause) | `voltagent-qa-sec:debugger` *(fallback if `/debug` needs more depth)* |
| Error detective (cross-service correlation) | `voltagent-qa-sec:error-detective` |
| Performance engineering | `voltagent-qa-sec:performance-engineer` |
| QA strategy / test planning | `voltagent-qa-sec:qa-expert` |
| Test automation (CI/CD integration) | `voltagent-qa-sec:test-automator` |
| AI writing detection / audit | `voltagent-qa-sec:ai-writing-auditor` |

## voltagent-data-ai (14 data/ML specialists)

| Task | Specialist |
|---|---|
| AI system architecture (model selection → deployment) | `voltagent-data-ai:ai-engineer` |
| LLM systems (fine-tune, RAG, inference) | `voltagent-data-ai:llm-architect` |
| ML engineering (training, serving) | `voltagent-data-ai:ml-engineer`, `voltagent-data-ai:machine-learning-engineer` |
| MLOps (CI/CD for ML, model versioning) | `voltagent-data-ai:mlops-engineer` |
| Data science (models, statistical insight) | `voltagent-data-ai:data-scientist` |
| Data analysis (dashboards, reports) | `voltagent-data-ai:data-analyst` |
| Data engineering (ETL, pipelines) | `voltagent-data-ai:data-engineer` |
| NLP (text processing, translation) | `voltagent-data-ai:nlp-engineer` |
| Reinforcement learning | `voltagent-data-ai:reinforcement-learning-engineer` |
| Database optimization (cross-DB) | `voltagent-data-ai:database-optimizer` |
| PostgreSQL expert (HA, replication) | `voltagent-data-ai:postgres-pro` |
| Prompt engineering (production prompts) | `voltagent-data-ai:prompt-engineer` |

## voltagent-research (9 research specialists)

| Task | Specialist |
|---|---|
| General research + synthesis | `voltagent-research:research-analyst` |
| Search across sources (targeted retrieval) | `voltagent-research:search-specialist` |
| Data discovery / validation | `voltagent-research:data-researcher` |
| Scientific literature + PDF extraction | `voltagent-research:scientific-literature-researcher` |
| Competitive analysis | `voltagent-research:competitive-analyst` |
| Market research (consumer, TAM) | `voltagent-research:market-researcher` |
| Trend analysis (industry shifts, scenarios) | `voltagent-research:trend-analyst` |
| Idea validation (go/no-go, market fit) | `voltagent-research:project-idea-validator` |

## gitnexus (7 codebase-intel skills — complements Graphify)

| Task | Skill |
|---|---|
| Run GitNexus CLI (index, status, clean) | `/gitnexus-cli` |
| Debug: trace error origin | `/gitnexus-debugging` |
| Explore: understand architecture / flows | `/gitnexus-exploring` |
| Guide: GitNexus tool catalogue | `/gitnexus-guide` |
| Impact analysis: "what breaks if I change X?" | `/gitnexus-impact-analysis` |
| Refactoring: safe rename/extract/move | `/gitnexus-refactoring` |

## graphify (1 knowledge-graph skill)

| Task | Command |
|---|---|
| Full knowledge-graph build | `/graphify <path>` |
| Query / explain / path | `/graphify-query`, `/graphify-explain`, `/graphify-path` |

---

## Decision tree (fast lookup)

```
Task arrives
│
├─ Language-specific code (Python/TS/Go/Rust/Java/etc.) ──→ voltagent-lang:<lang>-pro
├─ Language-specific framework (React/Django/Laravel/…)  ──→ voltagent-lang:<framework>
│
├─ Refactor / modernize / migrate ─────────────────────────→ voltagent-dev-exp:refactoring-specialist or legacy-modernizer
├─ Docs / README / API docs ────────────────────────────────→ voltagent-dev-exp:documentation-engineer or readme-generator
├─ Git workflow design ─────────────────────────────────────→ voltagent-dev-exp:git-workflow-manager
├─ Build / compile perf ────────────────────────────────────→ voltagent-dev-exp:build-engineer
│
├─ Security (audit / pentest / compliance) ────────────────→ voltagent-qa-sec:<specialist>
├─ A11y / performance / chaos / test automation ───────────→ voltagent-qa-sec:<specialist>
│
├─ Data / ML / AI engineering ─────────────────────────────→ voltagent-data-ai:<specialist>
├─ Database optimization ───────────────────────────────────→ voltagent-data-ai:database-optimizer or postgres-pro
│
├─ Research (market / competitive / literature) ──────────→ voltagent-research:<specialist>
│
├─ Codebase trace / impact analysis ───────────────────────→ /gitnexus-<subskill>
│
├─ Knowledge query / graph ────────────────────────────────→ graphify_agent or /graphify-query
│
├─ ANY other task ─────────────────────────────────────────→ our 21 agents via /lead-agent → Planning Council → planner → critic → evaluator
```

**Governance is ours. Work is specialist. Planning Council (pre-exec) + Ship Council (post-exec) are non-negotiable regardless of worker.**
