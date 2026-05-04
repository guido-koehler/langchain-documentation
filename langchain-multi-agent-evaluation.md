# LangChain Multi-Agent Orchestration — Evaluation for TJ-Sales Development Automation

> **Status:** Evaluation  
> **Scope:** Can LangChain (with LangGraph) be used to orchestrate multiple AI agents to automate recurring development tasks across the `tj-sales` monorepo?

---

## Table of Contents

1. [Overview](#overview)
2. [Solution Architecture Recap](#solution-architecture-recap)
3. [What Is LangChain/LangGraph?](#what-is-langchainlanggraph)
   - 3.1 [LangGraph Core Concepts: State, Nodes, Edges & Cyclic Graphs](#langgraph-core-concepts)
   - 3.2 [LangSmith Evaluation](#langsmith-evaluation)
4. [Feasibility Assessment](#feasibility-assessment)
5. [Proposed Agent Roles](#proposed-agent-roles)
6. [Workflow Examples](#workflow-examples)
7. [Integration Points](#integration-points)
8. [Advantages](#advantages)
9. [Disadvantages](#disadvantages)
10. [Risk Register](#risk-register)
11. [Recommended Architecture](#recommended-architecture)
12. [Implementation Roadmap](#implementation-roadmap)
13. [Strategic Comparison: Custom Orchestration vs. Agentic IDEs](#strategic-comparison-custom-orchestration-vs-agentic-ides)
14. [Verdict](#verdict)

---

## Overview

This document evaluates whether **LangChain** and its graph-based extension **LangGraph** can orchestrate multiple specialised AI agents to automate development workflows across the `tj-sales` monorepo — a multi-tenant SaaS platform consisting of:

| Component | Technology |
|-----------|-----------|
| **Backend** | .NET 8 · FastEndpoints · Cosmos DB · Modular Monolith |
| **Frontend** | Angular 21 · Nx · Module Federation · Transloco |
| **AI Service** | Python · Azure Service Bus · Azure OpenAI |
| **CI/CD** | GitHub Actions · Helm · Terraform · Azure Kubernetes Service |

---

## Solution Architecture Recap

Understanding the current architecture is critical to assessing where agents add the most value:

- **16 backend modules** (`Activity`, `Catalog`, `Company`, `Competency`, `Contact`, `Disposition`, `DocumentSigning`, `EconomicClassification`, `EmploymentRequirement`, `Finance`, `JobHub`, `LandingPage`, `Matching`, `Talent`, `Tenant`, `User`), each with their own Application / Domain / Endpoints / Infrastructure / Contracts / IntegrationEvents layers.
- **Frontend micro-frontends** (`core`, `sales`, `dispo`, `people`, `login`, `admin`, `contract`, `candidates-landing-page`) using Module Federation, auto-generated OpenAPI clients, and Transloco i18n.
- **AI service** (`ai/`) running Python workers consuming Azure Service Bus messages and calling Azure OpenAI — already contains sentence-transformer embeddings, similarity search, and LLM-powered matching.
- **Shared conventions**: CQRS, Result pattern, FluentValidation, Mapster, Scrutor DI, xUnit / AwesomeAssertions, Vitest, Playwright, GitVersion SemVer.

---

## What Is LangChain/LangGraph?

| | LangChain | LangGraph |
|---|---|---|
| **Purpose** | Framework for building LLM-powered apps with chains, tools, memory, and agents | Graph-based multi-agent orchestration layer built on top of LangChain |
| **Paradigm** | Linear or branching chains | Stateful directed graphs with cycles, conditionals, parallel branches |
| **Language** | Python-first; `langchain-js` available | Python-first |
| **Maturity** | Production-grade since 2023 | Stable since 2024 |
| **Key concepts** | `Tool`, `Agent`, `Chain`, `Memory`, `Callback` | `StateGraph`, `Node`, `Edge`, `Conditional`, `Checkpointer` |

For complex, iterative, multi-step workflows (like development automation), **LangGraph is the right choice** — it enables loops, human-in-the-loop interruptions, parallel execution, and shared state between agents.

---

## LangGraph Core Concepts

### State Management

Every LangGraph workflow is backed by a **shared state object** — a `TypedDict` that all nodes read from and write to. State is:

- **Typed** — defined as a Python `TypedDict`, giving agents structured, predictable data at every step
- **Persistent** — snapshots are saved to a `Checkpointer` (SQLite or Redis) after each node, enabling pause/resume and recovery from failures
- **Immutable per step** — nodes return a partial state dict; LangGraph merges it with the previous snapshot, never mutating it in place

```python
class FeatureState(TypedDict):
    jira_key: str
    plan: FeaturePlan | None
    backend_result: dict | None
    error: str | None
```

### Nodes

A **node** is a plain Python function (sync or async) that receives the current state and returns an updated state fragment. Nodes are the atomic units of work:

- Read files, call APIs, invoke LLMs, run CLI tools
- Return only the keys they changed — LangGraph merges the delta
- Can be retried independently if they fail; failures in one node do not corrupt others

```python
async def backend_node(state: FeatureState) -> FeatureState:
    result = await scaffold_and_verify(...)
    return {**state, "backend_result": result}
```

### Edges

**Edges** define the directed flow between nodes:

| Edge type | API | Use case |
|---|---|---|
| **Direct** | `g.add_edge("a", "b")` | Always go from A to B |
| **Conditional** | `g.add_conditional_edges("a", router_fn, {...})` | Branch based on state (e.g., route to "fix" if build failed) |
| **Parallel** | `langgraph.Send` | Fan-out to multiple nodes simultaneously (e.g., backend + frontend scaffold at the same time) |

Conditional edges are the mechanism for routing on state: whether a build passed, whether a plan returned an error, whether `needs_frontend` is `True`.

### Why Cyclic Graphs Are Crucial for Autonomous Agents

A **linear chain** executes steps in a fixed sequence with no ability to loop back:

```
Input → Step 1 → Step 2 → Step 3 → Output
```

This is sufficient for simple pipelines but fundamentally inadequate for autonomous agents:

| Problem scenario | Linear chain | Cyclic LangGraph |
|---|---|---|
| LLM generates code that does not compile | ❌ Outputs broken code | ✅ Build node detects failure → conditional edge routes back to "fix" node → retries up to N times |
| Tool call fails transiently (network error) | ❌ Entire chain errors out | ✅ Node retries with exponential back-off before propagating failure |
| Human approval required mid-workflow | ❌ Cannot pause mid-chain | ✅ `interrupt_before` pauses the graph; resumes once a developer approves |
| Quality must iterate to a threshold | ❌ Single shot only | ✅ Review node scores output; conditional edge loops until quality gate passes |
| Context shifts (earlier fix changes later inputs) | ❌ Downstream nodes see stale data | ✅ Shared mutable state means later nodes always see the latest values |

**Concrete example in tj-sales:** the Backend Scaffold Agent writes `.cs` files, then calls `dotnet build`. If the build fails, a conditional edge routes back to a fix node that sends the compile errors to the LLM for correction — this loop runs up to `max_fix_attempts` times before escalating. A linear chain cannot express this pattern at all.

---

## LangSmith Evaluation

> **LangSmith** (`smith.langchain.com`) is LangChain's observability and evaluation platform. It is optional for development but strongly recommended before deploying any agent to production.

Enable with two environment variables — no code changes needed:

```dotenv
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=tj-sales-agents
```

### Tracing and Debugging

Every agent run is automatically captured as a **trace** — a hierarchical record of every operation:

| Trace element | What it captures |
|---|---|
| **LLM Call** | Full prompt (system + human messages), completion text, token counts, latency, model name, cost estimate |
| **Tool Invocation** | Tool name, input arguments, return value, execution time |
| **Graph Node** | Node name, input state snapshot, output state delta, wall-clock duration |
| **Nested chain/agent** | Sub-calls within a node, enabling full drill-down |

This makes the agent's decision-making process **fully transparent**:

- Why did the agent route to the "fix" branch instead of "open_pr"?
- Which part of the system prompt caused the LLM to generate an incorrect namespace?
- Which node is responsible for a 45-second latency spike?

LangSmith's UI renders a **flame-graph-style breakdown** per run, making it easy to identify slow nodes, expensive LLM calls, unexpected tool outputs, and state transitions that deviate from expectations.

### Testing and Evaluation Features

Beyond tracing, LangSmith provides a structured **evaluation framework**:

#### Datasets

Collect reference input/output pairs — e.g., a set of Jira ticket descriptions paired with the expected scaffolded file structure. These become regression benchmarks that run on every prompt change.

#### Evaluators

Write custom scoring functions that assess agent output quality programmatically:

```python
from langsmith.evaluation import evaluate

def check_result_pattern(run, example) -> dict:
    """Check if the generated handler uses the Result pattern."""
    code = run.outputs.get("content", "")
    compliant = "Result.Success" in code and "Result.Failure" in code
    return {"score": 1 if compliant else 0, "key": "uses_result_pattern"}

evaluate(
    lambda inputs: run_scaffold_agent(inputs["jira_key"]),
    data="scaffold-benchmark-dataset",
    evaluators=[check_result_pattern],
)
```

#### Comparison Runs

Run two versions of an agent (e.g., different system prompt, `gpt-4o` vs `gpt-4o-mini`, old vs new convention file) against the same dataset and compare scores side-by-side to validate improvements before deploying.

### Benchmarking Agent Performance

Track these metrics over time as agents and prompts evolve:

| Metric | Description | Example target |
|---|---|---|
| **Compilation success rate** | % of scaffolded `.cs` files that build without errors on first attempt | > 90 % |
| **Convention compliance** | % of generated files that pass the convention checklist (Result pattern, FluentValidation, etc.) | > 95 % |
| **Translation accuracy** | Human spot-check score for LLM-generated German translations | > 4 / 5 |
| **CI diagnosis precision** | % of Jira tickets created with a correct root cause identified | > 80 % |
| **End-to-end latency** | Time from Jira webhook received → PR opened | < 5 minutes |
| **Cost per workflow run** | Azure OpenAI token cost per run type | Track trend; set budget alerts |

LangSmith's dashboards aggregate these metrics across runs, making it straightforward to detect regressions after a prompt change or model upgrade.

---

## Feasibility Assessment

### Is it technically possible? ✅

Yes. An orchestration layer implemented in Python (in or alongside `ai/`) can:

1. **Trigger** from Jira webhooks, GitHub webhooks, Azure Service Bus messages, or manual CLI invocations.
2. **Call backend tooling** via CLI (`dotnet build`, `dotnet test`) or REST (the existing API).
3. **Call frontend tooling** via CLI (`pnpm nx run`, `pnpm nx affected`).
4. **Interact with Jira** via the Jira REST API (read tickets, update status, add comments).
5. **Interact with GitHub** via the GitHub API / `gh` CLI (PRs, branch management).
6. **Generate and patch code** using Azure OpenAI (already available in `ai/.env`).
7. **Observe outputs** (test results, lint reports, coverage XML) and make decisions.

### Is it practical? ⚠️ Conditionally

Practicality depends on the level of autonomy required:

| Autonomy Level | Description | Verdict |
|---|---|---|
| **Assisted** | Agent drafts code / analysis, human reviews before any commit | ✅ High value, low risk |
| **Semi-autonomous** | Agent generates code and opens PRs, human approves merge | ✅ Feasible, recommended start |
| **Fully autonomous** | Agent commits, merges, and deploys without human gating | ⚠️ Risky for production systems |

---

## Proposed Agent Roles

A multi-agent system for this codebase would benefit from specialised agents with clearly bounded responsibilities:

### 🔍 1. Feature Planner Agent
**Responsibility:** Decompose a Jira ticket (user story or task) into concrete backend + frontend tasks following the monorepo conventions.

**Tools:**
- Jira REST API (read ticket summary, description, acceptance criteria, linked sub-tasks)
- Codebase search (understand existing patterns in the target module)
- Output: structured task list, file paths, class names following CQRS / FastEndpoints conventions

### 🏗️ 2. Backend Scaffold Agent
**Responsibility:** Generate .NET boilerplate for a new feature slice — Command, Handler, Endpoint, Validator, DTO, Contracts — following the project's vertical slice convention.

**Tools:**
- File system write (create `.cs` files)
- `dotnet build` (verify compilation)
- Project-specific templates: `ICommandHandler<TCommand, TResponse>`, `BaseEndpoint<TRequest, TResponse>`, `FluentValidation`, `Mapster`

### 🎨 3. Frontend Scaffold Agent
**Responsibility:** Generate Angular components, services, and routes following Nx conventions.

**Tools:**
- `pnpm nx generate` (scaffold components)
- `pnpm nx run shared:openapi-gen` (regenerate API client after backend changes)
- Transloco i18n key registration

### 🧪 4. Test Writer Agent
**Responsibility:** Generate xUnit unit/integration tests for backend handlers and Vitest tests for frontend components.

**Tools:**
- Read existing test patterns (e.g., `TenantTestBase`, `CompanyTestBase`)
- File system write
- `dotnet test --filter .UnitTest` (run and validate)
- `pnpm nx run <project>:test`

### 🔎 5. Code Review Agent
**Responsibility:** Perform automated code review on PRs — check for convention violations, missing validation, missing error handling, missing i18n keys, and security issues.

**Tools:**
- GitHub PR diff API
- Static analysis rule check (e.g., always use `Result` pattern, never throw from handlers)
- Post inline review comments via GitHub API

### 🚀 6. CI/CD Monitor Agent
**Responsibility:** Watch GitHub Actions runs, summarise failures, suggest fixes, and optionally auto-create fix PRs.

**Tools:**
- GitHub Actions API (list runs, get logs)
- Log analysis with LLM
- File patch + `git commit` + open PR

### 🌐 7. Translation Agent
**Responsibility:** Detect new i18n keys added in code, generate German translations (or other configured locales), and update Transloco JSON files.

**Tools:**
- Grep for untranslated keys
- Azure OpenAI translation
- File system write to `assets/i18n/{lang}.json`

### 📊 8. Release Notes Agent
**Responsibility:** Summarise merged PRs into human-readable release notes grouped by module.

**Tools:**
- GitHub API (merged PRs since last tag)
- GitVersion (determine next SemVer tag)
- Output: Markdown release notes

---

## Workflow Examples

### Workflow A: New Feature Automation (Semi-Autonomous)

```
Jira Ticket moved to "In Progress"
        │
        ▼
[Feature Planner Agent]
  - Reads ticket via Jira REST API (summary, description, acceptance criteria)
  - Identifies target module (e.g., Talent)
  - Plans: Command, Handler, Endpoint, DTO, Validator, Test
        │
        ├──────────────────┐
        ▼                  ▼
[Backend Scaffold Agent]  [Frontend Scaffold Agent]
  - Creates .cs files      - Runs nx generate
  - Calls dotnet build     - Runs openapi-gen
  - Reports compile errors - Verifies build
        │                  │
        └────────┬─────────┘
                 ▼
         [Test Writer Agent]
           - Writes xUnit tests
           - Runs dotnet test
           - Writes Vitest tests
                 │
                 ▼
         [Code Review Agent]
           - Checks conventions
           - Posts review comments
                 │
                 ▼
         Opens GitHub Pull Request
         (human reviews + merges)
```

### Workflow B: PR Review Automation

```
PR Opened on GitHub
        │
        ▼
[Code Review Agent]
  Checks:
  - Result pattern used?
  - FluentValidation present?
  - No exceptions thrown from handlers?
  - IBranchOfficeAccessService called where needed?
  - i18n keys all present in translation files?
  - OnPush change detection in Angular components?
  - Tests added?
        │
        ▼
Posts review comments on GitHub
```

### Workflow C: CI Failure Recovery

```
GitHub Actions run fails
        │
        ▼
[CI/CD Monitor Agent]
  - Fetches failed job logs
  - Analyses error with LLM
  - Identifies root cause (compile error / test failure / lint)
        │
        ├── If simple fix → patches file → opens fix PR
        └── If complex  → creates Jira ticket with analysis + links to failed run
```

---

## Integration Points

| Trigger | Mechanism | Agent(s) Activated |
|---|---|---|
| Jira ticket moved to "In Progress" | Jira Webhook → Python HTTP endpoint | Planner, Scaffold, Test Writer |
| PR opened/updated | GitHub Webhook | Code Review |
| GitHub Actions run fails | GitHub Webhook or polling | CI/CD Monitor |
| New translation key detected | Pre-commit hook or scheduled scan | Translation |
| Release tag created | GitHub Webhook | Release Notes |
| Manual CLI command | Developer runs `python agents/run.py --task "Add endpoint X"` | All (orchestrated by LangGraph) |

The orchestrator can live inside the existing `ai/` service directory or as a separate `agents/` package alongside it, sharing the existing Azure credentials and Service Bus infrastructure.

---

## Advantages

### 🟢 Technical Advantages

1. **Shared Azure infrastructure** — The project already uses Azure OpenAI, Azure Service Bus, and Azure Monitor. LangChain integrates natively with all of these via `langchain-azure-openai` and `langchain-community` packages.

2. **Existing Python foundation** — The `ai/` service is already Python with `openai`, `pydantic`, `tenacity`, `azure-*` packages. Adding LangGraph is an incremental dependency, not a new language.

3. **LangGraph state machines map perfectly to dev workflows** — Features like "compile → fix → recompile" loops, "review → revise → resubmit" cycles are naturally expressed as cyclic graphs with conditional edges.

4. **Tool abstraction** — Any CLI command (`dotnet build`, `pnpm nx affected`, `gh pr create`) or REST call (GitHub API, internal API) becomes a `Tool` callable by any agent, promoting reuse.

5. **Parallel execution** — LangGraph supports parallel branches, allowing Backend Scaffold Agent and Frontend Scaffold Agent to run simultaneously for the same feature.

6. **Human-in-the-loop checkpoints** — LangGraph's `interrupt_before` / `interrupt_after` mechanism lets agents pause and ask a developer for approval before irreversible actions (committing, deploying).

7. **Structured output** — Azure OpenAI's function calling + LangChain's `with_structured_output` ensures agents return typed Pydantic models rather than free-form strings, making outputs predictable and safe to process programmatically.

8. **Observability via LangSmith** — Full trace visibility into every LLM call, tool invocation, and state transition — complementing the existing Azure Application Insights setup.

9. **Modular agent design** — Each agent is independently testable and deployable. A buggy Translation Agent doesn't affect the CI/CD Monitor Agent.

10. **Convention-encoding** — Project conventions (CQRS patterns, Result pattern, naming rules) can be encoded into agent system prompts and tool schemas, essentially automating code review of architectural rules.

11. **Reduces context-switching** — Developers can describe a feature in natural language and receive a scaffold PR instead of manually creating boilerplate across 6+ files per module.

12. **i18n automation** — The Transloco + German locale requirement is a mechanical task perfectly suited for an LLM agent, reducing translation toil significantly.

### 🟢 Process Advantages

13. **Faster PR turnaround** — Automated convention checks mean human reviewers focus on business logic, not boilerplate issues.

14. **Lower onboarding friction** — New developers can ask the Planner Agent "how do I add a new endpoint to the Talent module?" and get a concrete, project-specific scaffold rather than reading architecture docs.

15. **Consistent output** — Agents produce code that follows conventions every time, unlike human developers who might miss a pattern under time pressure.

16. **Audit trail** — Every agent action (LLM call, tool invocation, file write) is logged, providing traceability for generated code.

---

## Disadvantages

### 🔴 Technical Disadvantages

1. **Python-only orchestration** — LangGraph is Python-first. The .NET backend and Angular frontend are not natively orchestratable from within LangGraph; they must be called as external processes or REST endpoints. This introduces subprocess management overhead.

2. **Non-determinism** — LLM outputs are probabilistic. The same prompt can produce subtly different code on each run. This is particularly problematic for auto-committed code — a small difference in a handler signature can break compilation or behaviour.

3. **Context window limits** — A large module (e.g., Talent with 50+ files) may exceed the LLM's context window when trying to understand patterns before generating new code. Retrieval-Augmented Generation (RAG) over the codebase is required, adding complexity.

4. **Build verification latency** — `dotnet build` of the full solution can take 30–90 seconds. Agent loops that compile after every code change will be slow. Incremental build strategies are needed.

5. **Test generation quality** — LLMs generate plausible-looking tests that may assert the wrong thing (happy-path only, missing edge cases, mocking too broadly). Generated tests require human review.

6. **Cosmos DB / integration test complexity** — Integration tests require a running Cosmos DB Emulator and specific `TestBase` configurations. Agents cannot easily run integration tests in isolation without environment provisioning.

7. **Breaking API changes** — LangChain has a history of breaking changes between versions (`0.x` → `1.x` → `2.x`). Pinning versions and managing upgrades adds maintenance overhead.

8. **Module Federation complexity** — The Nx Module Federation setup with runtime remotes is sufficiently complex that an agent generating routing or remote entry configuration is likely to produce errors requiring manual correction.

9. **Prompt injection risk** — If agents process content from issues or PRs written by external contributors, malicious prompt injection could cause agents to perform unintended actions (leak secrets, open harmful PRs).

10. **Secrets in tool context** — Azure OpenAI keys, GitHub tokens, and Service Bus credentials must be available to the agent runtime. Misconfiguration could expose secrets via LLM tool outputs or logs.

### 🔴 Process Disadvantages

11. **High initial investment** — Building a reliable multi-agent system for this codebase requires encoding all conventions into prompts/tools, writing agent logic, and extensive testing. Estimated effort: 4–8 weeks for a meaningful first version.

12. **Maintenance burden** — Every time a convention changes (new base class, new validation pattern, new module structure), agent prompts and tool schemas must be updated. Otherwise agents generate outdated code.

13. **Cost unpredictability** — Complex workflows with multiple agents, each making several LLM calls, can accumulate significant Azure OpenAI token costs. A single "scaffold new feature" run might cost $0.50–$2.00 depending on context size and model.

14. **Trust and accountability** — Auto-committed, auto-merged code raises questions about who is accountable when generated code causes a production incident. Process and governance must be established before deploying autonomous agents.

15. **Over-reliance risk** — Teams may reduce time spent learning the codebase if agents handle scaffolding, leading to knowledge atrophy and difficulty debugging generated code.

16. **Debugging agent failures** — When a multi-agent pipeline fails at step 4 of 7, diagnosing whether the failure was an LLM hallucination, a tool bug, a permissions issue, or an environmental problem requires strong observability tooling.

17. **Parallel agent conflicts** — Two agents writing to the same file simultaneously (e.g., both Backend Scaffold and Test Writer modifying a `.csproj`) can produce merge conflicts or data loss without proper serialisation.

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Agent commits broken code | Medium | High | Always require human PR review before merge; never auto-merge to `main` |
| R2 | Prompt injection from external PR contributors | Low | High | Sanitise all external input; run agents in read-only mode for external PRs |
| R3 | Azure OpenAI cost overrun | Medium | Medium | Set per-run token budgets; use `gpt-4o-mini` for low-stakes tasks |
| R4 | LangChain breaking changes | High | Low | Pin exact versions; run CI against upgrades in isolation |
| R5 | Agent leaks secrets in LLM context | Low | Critical | Never pass credentials as strings; use environment variable references only |
| R6 | Generated tests that always pass but assert nothing useful | High | Medium | Include test review in Code Review Agent checklist; require coverage gate |
| R7 | Build loop exceeds timeout | Medium | Low | Set hard timeouts; cache `dotnet restore` artifacts |
| R8 | Convention drift (agents generate outdated patterns) | High | Medium | Store conventions as versioned YAML/Markdown loaded at agent startup |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        agents/ (Python)                         │
│                                                                 │
│  ┌─────────────┐    ┌──────────────────────────────────────┐   │
│  │  Triggers   │    │         LangGraph Orchestrator        │   │
│  │             │    │                                       │   │
│  │ Jira        │───▶│  ┌──────────┐    ┌───────────────┐  │   │
│  │ Webhooks    │    │  │ Planner  │───▶│ Backend       │  │   │
│  │             │    │  │ Agent    │    │ Scaffold Agent│  │   │
│  │ GitHub      │───▶│  └──────────┘    └───────────────┘  │   │
│  │ Webhooks    │    │       │                              │   │
│  │             │    │       │          ┌───────────────┐  │   │
│  │ CLI trigger │───▶│       ├─────────▶│ Frontend      │  │   │
│  │             │    │       │          │ Scaffold Agent│  │   │
│  │ Scheduled   │───▶│       │          └───────────────┘  │   │
│  │ cron        │    │       │                              │   │
│  └─────────────┘    │       │          ┌───────────────┐  │   │
│                     │       └─────────▶│ Test Writer   │  │   │
│                     │                  │ Agent         │  │   │
│                     │                  └───────────────┘  │   │
│                     │       │          └───────────────┘  │   │
│                     │       │                              │   │
│                     │       │          ┌───────────────┐  │   │
│                     │       └─────────▶│ Test Writer   │  │   │
│                     │                  │ Agent         │  │   │
│                     │                  └───────────────┘  │   │
│                     │                                      │   │
│                     │  ┌───────────────────────────────┐  │   │
│                     │  │  Code Review / CI Monitor /   │  │   │
│                     │  │  Translation / Release Notes  │  │   │
│                     │  └───────────────────────────────┘  │   │
│                     └──────────────────────────────────────┘   │
│                                                                 │
│  Shared Tools:  dotnet CLI · pnpm/nx CLI · gh CLI · REST API   │
│  Shared State:  LangGraph Checkpointer (SQLite or Redis)        │
│  Observability: LangSmith + Azure Application Insights          │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  tj-sales codebase              GitHub (PRs, Issues,
  (file system writes)            Actions, Reviews)
```

### Directory Layout

```
agents/                          # New directory alongside ai/
├── requirements.txt             # langchain, langgraph, langchain-azure-openai, ...
├── config/
│   └── settings.py              # Agent settings (extends ai/src/config)
├── conventions/
│   ├── backend-patterns.md      # CQRS, Result, FastEndpoints conventions (LLM context)
│   ├── frontend-patterns.md     # Angular, OnPush, Transloco conventions
│   └── test-patterns.md         # xUnit, AwesomeAssertions, Vitest patterns
├── tools/
│   ├── dotnet_tools.py          # build, test, format wrappers
│   ├── nx_tools.py              # nx generate, nx run, openapi-gen wrappers
│   ├── github_tools.py          # PR, issue, review, Actions API wrappers
│   ├── jira_tools.py            # read tickets, update status, create sub-tasks, add comments
│   └── filesystem_tools.py     # read, write, patch file operations
├── agents/
│   ├── planner.py
│   ├── backend_scaffold.py
│   ├── frontend_scaffold.py
│   ├── test_writer.py
│   ├── code_review.py
│   ├── ci_monitor.py
│   ├── translation.py
│   └── release_notes.py
├── graphs/
│   ├── feature_workflow.py      # Planner → Scaffold → Test → Review → PR
│   ├── review_workflow.py       # Code Review workflow
│   └── ci_recovery_workflow.py  # CI failure → diagnose → fix PR
└── main.py                      # Entry point + webhook server
```

---

## Implementation Roadmap

A phased approach is strongly recommended to validate value before full investment:

### Phase 1 — Code Review Agent (2 weeks, low risk)
Start with a read-only agent that reviews PRs and posts comments. Zero risk of broken commits.
- Implement `code_review.py` with GitHub diff + convention checks
- Validate on real PRs; tune prompts

### Phase 2 — Translation Agent (1 week, low risk)
Automate i18n key translation — bounded, mechanical, easily verified.
- Scan for new Transloco keys
- Generate German translations via Azure OpenAI
- Open PR with translation diffs

### Phase 3 — CI/CD Monitor Agent (2 weeks, medium risk)
Watch failing GitHub Actions, summarise, and create Jira tickets.
- Parse workflow logs
- LLM root cause analysis
- Jira ticket creation with failure summary and link to the failed run

### Phase 4 — Backend Scaffold Agent (3 weeks, medium risk)
Generate CQRS boilerplate for new features. Requires robust convention encoding.
- Template-driven generation + LLM for custom logic
- `dotnet build` verification loop

### Phase 5 — Full Feature Workflow (4 weeks, higher risk)
Connect Planner + Backend + Frontend + Test Writer + Code Review into end-to-end LangGraph.
- Human-in-the-loop checkpoint before PR creation
- Full integration testing

---

## Strategic Comparison: Custom Orchestration vs. Agentic IDEs

The third objective of this spike is to determine **when a custom LangGraph orchestration layer is the right tool** versus relying on the growing ecosystem of **Agentic IDEs** such as Cursor, Windsurf, and GitHub Copilot (Workspace / CLI / Copilot Next).

### What Are Agentic IDEs?

| Tool | Description |
|---|---|
| **Cursor** | VS Code fork with deep AI integration — multi-file edit agents, codebase-aware chat, background agents that open PRs |
| **Windsurf** | Codeium-powered IDE with "Cascade" agentic flows — reads and edits entire codebases with minimal prompting |
| **GitHub Copilot (CLI / Copilot Next)** | GitHub Copilot's evolving agentic features — multi-step task execution inside the editor, Copilot Workspace for spec-to-PR flows |

These tools can already:
- Read and understand large codebases via embedding-based retrieval
- Make multi-file changes and run build/test commands
- Open PRs with generated changes
- Explain architectural decisions and suggest refactors

### Comparison Matrix

| Criterion | Agentic IDEs | Custom Orchestration (LangGraph) |
|---|---|---|
| **Setup time** | Minutes (install extension / IDE) | Days to weeks (build tools, test, deploy) |
| **Target persona** | Individual developer — interactive use | Platform / DevOps team — automated pipelines |
| **Execution context** | Developer's local machine / IDE session | Server, container, GitHub Actions, AKS pod |
| **Runs unattended** | ❌ Requires an active human session | ✅ Fully headless — webhook- or schedule-triggered |
| **Jira integration** | ❌ None out of the box | ✅ Full REST API — read tickets, update status, create sub-tasks |
| **GitHub Actions integration** | ❌ Cannot watch CI runs autonomously | ✅ Webhook-driven — fetches logs, posts comments, opens fix PRs |
| **Workflow complexity** | Single or sequential multi-step | Cyclic, conditional, parallel multi-agent |
| **Human-in-the-loop control** | Always present (developer is the loop) | Configurable — `interrupt_before` / `interrupt_after` checkpoints |
| **Observability** | Low — proprietary black box, minimal logs | High — full LangSmith traces + Azure Application Insights |
| **Convention enforcement** | Implicit — inferred from codebase context | Explicit — loaded from versioned Markdown files, deterministic rules |
| **Customisation** | Limited — provider-controlled prompts and tools | Unlimited — you own every prompt, tool schema, and routing rule |
| **Cost model** | Monthly SaaS subscription per seat | Pay-per-token (Azure OpenAI) + compute cost |
| **Audit trail** | None / minimal | Full trace per run stored in LangSmith |
| **Multi-tenant awareness** | ❌ No concept of tenants | ✅ Tenant context can be encoded into state and tool schemas |
| **Vendor lock-in** | High — proprietary tooling | Low — LangChain/LangGraph is MIT-licensed and self-hostable |

### Decision Criteria

#### Use an Agentic IDE when

- The task is **interactive** — a developer is present and wants guided suggestions, inline completions, or assisted refactors
- The scope is **a single coding session** — e.g., "add a new endpoint to the Talent module" where a developer reviews and steers every step
- You need **fast time-to-value** — IDE agents work immediately, zero infrastructure required
- The workflow is **ad hoc and non-recurring** — not a process that repeats hundreds of times a month
- The team does not have capacity to build, test, and maintain custom agent tooling

#### Use Custom LangGraph Orchestration when

- The workflow must run **unattended** — triggered by Jira webhooks, GitHub webhooks, or a nightly cron, with no developer present
- You need **deep integration with internal systems** — Jira REST API, Azure Service Bus, internal backend APIs, Cosmos DB
- The workflow is **complex and iterative** — requiring loops (compile → fix → recompile), parallel branches (backend + frontend scaffolding simultaneously), or conditional routing on tool outputs
- You need **full observability and auditability** — every LLM call, tool invocation, and state transition must be traceable and reproducible
- You want to **encode conventions programmatically** — ensuring every agent-generated file strictly follows CQRS, the Result pattern, and FluentValidation rules, verified automatically
- The operation is **high-stakes** — auto-committing code, creating Jira tickets, triggering deployments — where deterministic, testable behaviour is non-negotiable

### Recommendation for TJ-Sales

The two approaches are **complementary, not mutually exclusive**:

| Layer | Tool | Role |
|---|---|---|
| **Interactive development** | GitHub Copilot CLI | Code writing assistance, quick scaffolding suggestions during active development sessions |
| **Automated background ops** | Custom LangGraph agents | CI failure monitoring, translation automation, release notes generation, nightly convention checks |
| **Semi-autonomous PR creation** | Custom LangGraph agents | Triggered by Jira webhooks; generates scaffold PRs for human review — developers are freed from boilerplate |

**Practical guidance:** start with GitHub Copilot for immediate developer productivity (already in use). Build custom LangGraph agents only for **recurring, automatable workflows** where the up-front investment in tooling compounds over hundreds of automated runs. The phased roadmap (Phase 1–5) respects this principle — beginning with low-risk, read-only automation before tackling full code generation.

---

## Verdict

| Criterion | Assessment |
|---|---|
| **Technical feasibility** | ✅ Feasible — existing Python + Azure OpenAI foundation makes integration straightforward |
| **Highest-value use cases** | Code Review, Translation, CI Monitor, Backend Scaffold |
| **Recommended framework** | **LangGraph** (stateful graphs) over plain LangChain chains |
| **Key prerequisite** | All project conventions must be documented in machine-readable form before agents can enforce them |
| **Recommended autonomy level** | Semi-autonomous — agents open PRs, humans merge |
| **IDE vs. custom framework** | Use Agentic IDEs (GitHub Copilot) for interactive development; use LangGraph for automated, unattended workflows — they are complementary |
| **Overall recommendation** | **Start with Phase 1–3** (read-only and low-risk agents) to build confidence and tooling before tackling full code generation |

LangChain/LangGraph **can** meaningfully automate development workflows for `tj-sales`. The biggest risks are non-determinism in code generation, maintenance of agent conventions, and cost governance — all of which are manageable with the right guardrails. The project is especially well-positioned because the `ai/` service already provides the Azure OpenAI, Python, and Service Bus infrastructure that agents need.

---

*Document authored with GitHub Copilot · Last updated: 2026-04-30*
