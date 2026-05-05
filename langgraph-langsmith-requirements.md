# LangGraph & LangSmith — Requirements for Agentic Development in TJ-Sales

> **Document type:** Requirements Specification  
> **Status:** Draft  
> **Related documents:**  
> - [`langchain-multi-agent-evaluation.md`](./langchain-multi-agent-evaluation.md) — Feasibility evaluation and strategic comparison  
> - [`langchain-agent-implementation-guide.md`](./langchain-agent-implementation-guide.md) — Step-by-step implementation guide

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Stakeholders](#2-stakeholders)
3. [Functional Requirements](#3-functional-requirements)
   - 3.1 [Agent Capabilities](#31-agent-capabilities)
   - 3.2 [Workflow Orchestration](#32-workflow-orchestration)
   - 3.3 [Jira Integration](#33-jira-integration)
   - 3.4 [GitHub Integration](#34-github-integration)
   - 3.5 [Observability & Evaluation](#35-observability--evaluation)
4. [Non-Functional Requirements](#4-non-functional-requirements)
   - 4.1 [Performance](#41-performance)
   - 4.2 [Reliability & Fault Tolerance](#42-reliability--fault-tolerance)
   - 4.3 [Security](#43-security)
   - 4.4 [Maintainability](#44-maintainability)
   - 4.5 [Cost Governance](#45-cost-governance)
5. [Developer Environment Requirements](#5-developer-environment-requirements)
   - 5.1 [Local Toolchain](#51-local-toolchain)
   - 5.2 [Python Environment](#52-python-environment)
   - 5.3 [Python Package Dependencies](#53-python-package-dependencies)
6. [Infrastructure Requirements](#6-infrastructure-requirements)
   - 6.1 [Azure Resources](#61-azure-resources)
   - 6.2 [Deployment Target](#62-deployment-target)
   - 6.3 [State Persistence](#63-state-persistence)
7. [Integration Requirements](#7-integration-requirements)
   - 7.1 [Azure OpenAI](#71-azure-openai)
   - 7.2 [Jira (Atlassian)](#72-jira-atlassian)
   - 7.3 [GitHub](#73-github)
   - 7.4 [LangSmith](#74-langsmith)
8. [Credential & Secrets Requirements](#8-credential--secrets-requirements)
9. [Convention & Knowledge Base Requirements](#9-convention--knowledge-base-requirements)
10. [CI/CD Requirements](#10-cicd-requirements)
11. [Acceptance Criteria](#11-acceptance-criteria)
12. [Out of Scope](#12-out-of-scope)

---

## 1. Purpose & Scope

This document defines the **complete set of requirements** for introducing LangGraph-based AI agents and LangSmith observability into the `tj-sales` development workflow.

### Goal

Enable **Agentic Driven Development** — a model where AI agents autonomously handle recurring, well-defined development tasks (code scaffolding, code review, CI failure triage, i18n translation, release notes) while human developers retain control over merging and architectural decisions.

### In Scope

- A new `agents/` Python package within the `tj-sales` monorepo
- Eight specialised AI agents (Planner, Backend Scaffold, Frontend Scaffold, Test Writer, Code Review, CI/CD Monitor, Translation, Release Notes)
- LangGraph orchestration layer connecting agents into multi-step workflows
- LangSmith tracing, debugging, and evaluation pipeline
- Integration with Jira (planning), GitHub (PRs, Actions), and the existing Azure OpenAI deployment
- Deployment as a containerised service in the existing AKS cluster

### Out of Scope

- Changes to the existing `ai/` Python service
- Modifications to `backend-v2/` or `frontend/` source code
- Replacing human code review entirely
- Fully autonomous deployments to staging or production without human approval

---

## 2. Stakeholders

| Stakeholder | Interest |
|---|---|
| **Development Team** | Reduced boilerplate work; faster feature scaffold turnaround |
| **Tech Lead / Architect** | Convention enforcement; AI-generated code quality; audit trail |
| **DevOps / Platform Engineer** | Deployment, monitoring, cost governance |
| **Product Owner / Scrum Master** | Jira ticket lifecycle automation; sprint velocity improvement |
| **Security Team** | Secrets handling; access control; AI-generated code review |

---

## 3. Functional Requirements

### 3.1 Agent Capabilities

The system MUST provide the following specialised agents:

| ID | Agent | Core Capability | Trigger |
|---|---|---|---|
| AGT-01 | **Feature Planner** | Read a Jira ticket; decompose it into backend + frontend tasks following CQRS/FastEndpoints conventions | Jira webhook (ticket → "In Progress") |
| AGT-02 | **Backend Scaffold** | Generate `.cs` files (Command, Handler, Endpoint, Validator, DTO) for a new feature slice; verify with `dotnet build`; iterate on compile errors | Planner output |
| AGT-03 | **Frontend Scaffold** | Run `pnpm nx generate` for components/services; run `openapi-gen`; register i18n keys | Planner output |
| AGT-04 | **Test Writer** | Generate xUnit unit tests (AwesomeAssertions, AutoFixture, Moq); run `dotnet test --filter .UnitTest` | Backend Scaffold output |
| AGT-05 | **Code Review** | Review PR diffs for convention violations (Result pattern, FluentValidation, IBranchOfficeAccessService, OnPush, i18n); post inline GitHub review comments; post summary to linked Jira ticket | GitHub webhook (PR opened / synchronize) |
| AGT-06 | **CI/CD Monitor** | Fetch failed GitHub Actions logs; perform LLM root-cause analysis; create Jira bug ticket; optionally open a fix PR | GitHub webhook (workflow_run failed) |
| AGT-07 | **Translation** | Detect untranslated Transloco keys in `assets/i18n/`; generate German translations via Azure OpenAI; open a PR | Pre-commit hook or nightly schedule |
| AGT-08 | **Release Notes** | Aggregate merged PRs since last tag; group by module; generate Markdown release notes; prepend to `CHANGELOG.md` | GitHub webhook (tag created) |

### 3.2 Workflow Orchestration

**REQ-WF-01** — The orchestration layer MUST use **LangGraph `StateGraph`** for all multi-step workflows. Plain sequential function calls are not sufficient for workflows requiring loops or conditional branching.

**REQ-WF-02** — Workflows MUST support **cyclic execution**: the build-fix loop in AGT-02 and AGT-04 MUST be expressed as an actual LangGraph cycle (`build_check → fix → build_check`) with a configurable `max_fix_attempts` guard to prevent infinite loops.

**REQ-WF-03** — The Full Feature Workflow (AGT-01 through AGT-05 combined) MUST support **parallel execution** of backend and frontend scaffolding using `langgraph.constants.Send` to fan out from the Planner node.

**REQ-WF-04** — Every stateful workflow MUST use a **LangGraph Checkpointer** (`AsyncSqliteSaver` for single-node, `AsyncRedisSaver` for multi-node/AKS) so that workflows can be paused and resumed without data loss.

**REQ-WF-05** — The Full Feature Workflow MUST implement a **human-in-the-loop checkpoint** using `interrupt_before=["open_pr"]` before any PR is created. Developers MUST be able to inspect the agent's output and resume via a CLI command or Slack/GitHub comment.

**REQ-WF-06** — All LangGraph conditional routing functions MUST be **pure and deterministic** — they MUST NOT call the LLM or external services; routing decisions must be based solely on state values.

**REQ-WF-07** — Every agent MUST handle failure gracefully: on exceeding `max_fix_attempts` or encountering an unrecoverable error, the agent MUST:
1. Open a draft PR with a `needs-human` label containing all work produced so far
2. Post a Jira comment on the originating ticket with the failure summary and PR link
3. Log a structured error entry (JSON) to stdout for Azure Application Insights ingestion

### 3.3 Jira Integration

**REQ-JIRA-01** — The system MUST integrate with the Atlassian Jira REST API (v3) for the following operations:
- Read ticket details (summary, description, acceptance criteria, linked sub-tasks, labels, status)
- Add comments to tickets (progress updates, PR links, failure summaries)
- Create new bug tickets (for CI/CD Monitor: CI failure reports)
- Update ticket status (optional: move to "In Review" when PR is opened)

**REQ-JIRA-02** — Jira webhooks MUST be the primary trigger for the Full Feature Workflow. The webhook server MUST accept `jira:issue_updated` events and start the workflow when a ticket transitions to status **"In Progress"**.

**REQ-JIRA-03** — The Jira project key (e.g. `TJS`) MUST be configurable via the `JIRA_PROJECT_KEY` environment variable — it MUST NOT be hardcoded anywhere in agent code.

**REQ-JIRA-04** — The agent MUST extract the Jira ticket key from PR branch names (pattern: `feature/TJS-\d+-...`) to link code review results back to Jira without requiring additional configuration.

**REQ-JIRA-05** — All Jira API calls MUST use **HTTP Basic Authentication** (user email + API token) and MUST support the Atlassian Document Format (ADF) for rich-text comment bodies.

### 3.4 GitHub Integration

**REQ-GH-01** — The system MUST integrate with the GitHub REST API for the following operations:
- Read PR diffs and metadata (`GET /repos/{owner}/{repo}/pulls/{pull_number}`)
- Post PR reviews with inline comments
- Create pull requests (feature scaffold, fix PRs, translation PRs)
- Read GitHub Actions workflow run logs (for CI/CD Monitor)
- List merged PRs since a tag (for Release Notes)
- Add labels to PRs (e.g., `ai-generated`, `needs-human`)

**REQ-GH-02** — The webhook server MUST handle the following GitHub webhook events:
- `pull_request` → `opened` / `synchronize` → triggers Code Review Agent
- `workflow_run` → `completed` with `conclusion=failure` → triggers CI/CD Monitor
- `create` with `ref_type=tag` → triggers Release Notes Agent

**REQ-GH-03** — Webhook payloads from GitHub MUST be validated using HMAC-SHA256 signature verification against the `WEBHOOK_SECRET` environment variable before processing.

**REQ-GH-04** — All GitHub-triggered workflows MUST be processed **asynchronously** using FastAPI `BackgroundTasks` — the webhook endpoint MUST return HTTP 202 within 1 second.

**REQ-GH-05** — The GitHub PAT MUST have the following minimum scopes: `repo`, `pull_requests`, `actions`, `read:org`.

**REQ-GH-06** — Agent-generated PRs MUST follow the branch naming convention `feature/{JIRA_KEY}-{short-description}` and MUST include the Jira ticket key in the PR title and body.

### 3.5 Observability & Evaluation

**REQ-OBS-01** — All LLM calls, tool invocations, and graph node transitions MUST be automatically traced in **LangSmith** when `LANGSMITH_TRACING=true`. No code-level instrumentation (decorators, wrappers) should be required beyond the environment variable.

**REQ-OBS-02** — LangSmith traces MUST be queryable to answer: why did the agent route to a given node, which prompt produced a specific output, and which node caused a latency spike.

**REQ-OBS-03** — A **benchmark dataset** named `scaffold-benchmark` MUST be maintained in LangSmith containing representative Jira ticket inputs paired with expected output file names. The dataset MUST include at minimum 5 examples covering different modules (Talent, Company, Finance, Tenant, Contact).

**REQ-OBS-04** — The following **evaluator functions** MUST be implemented and run against the benchmark dataset:
- `uses_result_pattern` — every generated handler returns `Result` or `Result<T>`
- `has_fluent_validation` — every generated command has an `AbstractValidator<T>` class
- `build_succeeds` — `dotnet build` returns exit code 0 after scaffolding
- `correct_namespace` — generated files use the correct `Gedat.TimeJobOnline.{Sales|People|Disposition}` namespace

**REQ-OBS-05** — The evaluation suite MUST be runnable via `python -m agents.evals.run_eval` and MUST be automatically triggered by the GitHub Actions workflow `agent-eval.yml` on every PR that modifies code under `agents/`.

**REQ-OBS-06** — A/B comparison between prompt versions MUST be supported via multiple `experiment_prefix` values in LangSmith. Regression in any evaluator score MUST block the PR merge (enforced via the GitHub Actions job exit code).

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement |
|---|---|
| NFR-PERF-01 | End-to-end latency from Jira webhook received to PR opened MUST be **< 5 minutes** for a typical feature ticket (single module, command + endpoint) |
| NFR-PERF-02 | The Code Review Agent MUST post its review to GitHub within **30 seconds** of the PR webhook event |
| NFR-PERF-03 | The Translation Agent MUST process up to 50 new i18n keys within **60 seconds** |
| NFR-PERF-04 | The webhook endpoint MUST accept and acknowledge incoming webhooks within **1 second** (processing happens asynchronously) |
| NFR-PERF-05 | Parallel backend + frontend scaffolding (`Send`-based fan-out) MUST reduce total scaffold time by at least 30% versus sequential execution for tickets requiring both |

### 4.2 Reliability & Fault Tolerance

| ID | Requirement |
|---|---|
| NFR-REL-01 | Every agent node MUST be independently retryable via the LangGraph Checkpointer — a failure in one node MUST NOT require restarting the entire workflow from scratch |
| NFR-REL-02 | All external HTTP calls (Jira REST, GitHub REST, Azure OpenAI) MUST use **exponential back-off retry** with at least 3 attempts (implemented via `tenacity`) |
| NFR-REL-03 | Build-fix cycles MUST have a configurable hard limit (`MAX_FIX_ATTEMPTS`, default 3) to prevent infinite loops |
| NFR-REL-04 | Agent failures MUST produce a recoverable artefact (draft PR or Jira comment) — silent failures are not acceptable |
| NFR-REL-05 | The webhook server MUST remain available even while long-running agent workflows execute in the background |

### 4.3 Security

| ID | Requirement |
|---|---|
| NFR-SEC-01 | All secrets (API keys, tokens) MUST be stored in Azure Key Vault and injected into the container via the CSI Secrets Store driver — they MUST NOT be committed to the repository |
| NFR-SEC-02 | GitHub webhook payloads MUST be validated with HMAC-SHA256 before any processing |
| NFR-SEC-03 | The agent service MUST run with a **dedicated Azure Managed Identity** with least-privilege access to Azure OpenAI and Key Vault — no shared credentials with the backend service |
| NFR-SEC-04 | The GitHub PAT MUST be scoped to the minimum required permissions (see REQ-GH-05) and MUST be rotated at least every 90 days |
| NFR-SEC-05 | AI-generated code MUST NOT be auto-merged — a human reviewer MUST approve all agent-generated PRs before merging |
| NFR-SEC-06 | The agent MUST NOT have write access to `main` or `staging` branches directly — all changes go through PRs |
| NFR-SEC-07 | LangSmith traces MAY contain source code snippets and Jira ticket text — the LangSmith project MUST be scoped to the team's organisation and MUST NOT be public |

### 4.4 Maintainability

| ID | Requirement |
|---|---|
| NFR-MAIN-01 | Convention files (`backend-patterns.md`, `frontend-patterns.md`, `test-patterns.md`) MUST be kept up to date with the codebase and reviewed as part of any architecture decision record (ADR) |
| NFR-MAIN-02 | Each agent MUST be independently testable — unit tests for tool functions MUST mock all external API calls; no live API calls in unit tests |
| NFR-MAIN-03 | The Jira project key, GitHub repo name, Azure OpenAI deployment name, and LangSmith project name MUST all be environment-variable-driven — no hardcoded strings in agent logic |
| NFR-MAIN-04 | The benchmark dataset in LangSmith MUST be extended (by at least 2 examples) whenever a new module is onboarded or a significant architecture change is made |
| NFR-MAIN-05 | All agent code MUST be typed with Python type hints and MUST pass `mypy --strict` without errors |

### 4.5 Cost Governance

| ID | Requirement |
|---|---|
| NFR-COST-01 | High-complexity tasks (scaffold, code review, planner) MUST use the primary deployment (`gpt-4o`); low-complexity tasks (translation, summaries, release notes) MUST use the mini deployment (`gpt-4o-mini`) |
| NFR-COST-02 | PR diffs sent to the Code Review Agent MUST be truncated to a maximum of **30,000 characters** to limit token consumption |
| NFR-COST-03 | LangSmith tracing token counts per run MUST be reviewed monthly; runs exceeding a configurable threshold MUST trigger an Azure Monitor alert |
| NFR-COST-04 | The CI evaluation workflow (`agent-eval.yml`) MUST use the mini deployment to minimise cost per PR |

---

## 5. Developer Environment Requirements

### 5.1 Local Toolchain

All of the following MUST be installed and accessible on `PATH` on any machine developing or running agents:

| Tool | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.11 | Agent runtime |
| **.NET SDK** | 8.x | `dotnet build`, `dotnet test` (called by agent tools) |
| **Node.js** | 20.x | `pnpm nx` CLI (called by Frontend Scaffold Agent) |
| **pnpm** | 9.x | Frontend package manager |
| **GitHub CLI (`gh`)** | Latest stable | Fallback GitHub operations |
| **git** | 2.x | Branch management, commits, pushes |
| **Docker** | 24.x+ | Local container build/run |

### 5.2 Python Environment

**REQ-ENV-01** — The `agents/` package MUST use a **dedicated Python virtual environment** (`.venv`) isolated from the existing `ai/` service to prevent dependency conflicts.

**REQ-ENV-02** — Python 3.11 MUST be used — the same major version as the `ai/` service — to ensure consistency in Azure Container Registry base images.

**REQ-ENV-03** — Environment variables MUST be loaded from `agents/.env` (local development) or injected by the Kubernetes CSI Secrets Store (production). The `.env` file MUST be listed in `.gitignore` — only `.env.example` is committed.

### 5.3 Python Package Dependencies

The following packages MUST be pinned in `agents/requirements.txt`:

| Package | Minimum Version | Purpose |
|---|---|---|
| `langchain` | 1.0.0 | LLM chains, tools, agents |
| `langchain-core` | 1.0.0 | Core abstractions (`@tool`, `BaseMessage`) |
| `langgraph` | 1.0.0 | Stateful graph orchestration |
| `langgraph-checkpoint-sqlite` | 2.0.0 | Async SQLite checkpointer (`AsyncSqliteSaver`) |
| `langchain-openai` | 0.3.0 | Azure OpenAI chat model |
| `langsmith` | 0.3.0 | Tracing and evaluation SDK |
| `httpx` | 0.27.0 | Async HTTP client (Jira, GitHub REST) |
| `PyGithub` | 2.3.0 | GitHub API wrapper |
| `fastapi` | 0.115.0 | Webhook HTTP server |
| `uvicorn[standard]` | 0.30.0 | ASGI server for FastAPI |
| `pydantic` | 2.0.0 | Data validation and settings models |
| `pydantic-settings` | 2.0.0 | Environment-variable-based settings |
| `python-dotenv` | 1.0.0 | `.env` file loading |
| `tenacity` | 9.0.0 | Retry logic with exponential back-off |

Optional (for multi-node AKS deployment):

| Package | Version | Purpose |
|---|---|---|
| `langgraph-checkpoint-redis` | Latest | Distributed checkpointer for multi-pod deployments |

---

## 6. Infrastructure Requirements

### 6.1 Azure Resources

The following Azure resources MUST exist or be provisioned before deploying agents to production:

| Resource | Purpose | Status |
|---|---|---|
| **Azure OpenAI** | LLM inference (`gpt-4o`, `gpt-4o-mini` deployments) | ✅ Already exists (shared with `ai/`) |
| **Azure Kubernetes Service (AKS)** | Hosts the agent service container | ✅ Already exists |
| **Azure Container Registry (ACR)** | Stores the `tj-sales-agents` Docker image | ✅ Already exists |
| **Azure Key Vault** | Stores all secrets (API keys, tokens) | ✅ Already exists |
| **Azure Application Insights** | Ingests structured JSON logs from agent runs | ✅ Already exists |
| **Azure Service Bus** | Optional: decouple webhook triggers from agent execution for high-volume scenarios | ⚠️ Available — not required for MVP |
| **Redis Cache** | Required for multi-pod `AsyncRedisSaver` checkpointer | ⚠️ Required for horizontal scaling; not needed for single-pod MVP |

### 6.2 Deployment Target

**REQ-INFRA-01** — The agent service MUST be deployed as a single **Helm-managed pod** in the `tj-sales` AKS namespace for the MVP phase.

**REQ-INFRA-02** — The agent pod MUST have access to the repository file system. For the MVP, this is achieved by mounting a Persistent Volume (PVC) or using a **git-sync init container** that clones the repository on pod start.

**REQ-INFRA-03** — For code-writing agents (Backend Scaffold, Frontend Scaffold), the preferred approach is an **ephemeral Kubernetes Job** per run: clone → execute → push branch → clean up. This provides better isolation than a long-running pod with a mounted volume.

**REQ-INFRA-04** — The Helm chart values MUST NOT contain any secrets — all secrets MUST be referenced from Key Vault via the CSI driver or Kubernetes Secrets.

**REQ-INFRA-05** — The agent service MUST expose port `8080` for the webhook server and MUST be reachable from GitHub's and Atlassian's webhook IP ranges. An ingress rule or Azure API Management policy MUST be configured accordingly.

### 6.3 State Persistence

| Scenario | Checkpointer | Storage |
|---|---|---|
| **Local development** | `AsyncSqliteSaver` | `{REPO_ROOT}/.agents/checkpoints.db` |
| **Single AKS pod** | `AsyncSqliteSaver` | PVC mounted at `/checkpoints/checkpoints.db` |
| **Multiple AKS pods (horizontal scale)** | `AsyncRedisSaver` | Azure Redis Cache |

**REQ-STATE-01** — Checkpoint data MUST be retained for at least **7 days** to allow developers to resume interrupted workflows.

**REQ-STATE-02** — The `thread_id` for each workflow run MUST be deterministic and traceable — use `feature-{JIRA_KEY}` for feature workflows, `review-{PR_NUMBER}` for code review, `ci-{RUN_ID}` for CI monitor.

---

## 7. Integration Requirements

### 7.1 Azure OpenAI

| Requirement | Detail |
|---|---|
| **Deployments** | Two deployments required: a primary (e.g. `gpt-4o`) for code generation and a mini (e.g. `gpt-4o-mini`) for translation, summaries, and CI analysis |
| **API version** | `2024-08-01-preview` or newer |
| **Temperature** | 0 for all code generation tasks (determinism); 0.3 for natural-language tasks (release notes, translations) |
| **Max retries** | 3 (handled by `AzureChatOpenAI(max_retries=3)`) |
| **Authentication** | API key via `AZURE_OPENAI_API_KEY` for local dev; Managed Identity in production |

### 7.2 Jira (Atlassian)

| Requirement | Detail |
|---|---|
| **API** | Atlassian REST API v3 (`https://{org}.atlassian.net/rest/api/3/`) |
| **Authentication** | HTTP Basic Auth — email address + API token (`JIRA_USER_EMAIL` + `JIRA_API_TOKEN`) |
| **Required permissions** | Read issues, add comments, create issues, transition issue status |
| **Project key** | Configurable via `JIRA_PROJECT_KEY` (default: `TJS`) |
| **Webhook configuration** | Project Settings → Automation → Webhooks: event `Issue updated`, URL `https://{agent-host}/webhooks/jira` |
| **ADF support** | Comments MUST use Atlassian Document Format (ADF) JSON structure for rich-text formatting |

**Jira API Token Setup:**
1. Log in to `id.atlassian.com`
2. Navigate to **Security** → **API tokens** → **Create API token**
3. Label it `tj-sales-agents` and copy the token
4. Store in Azure Key Vault under secret name `jira-api-token`

### 7.3 GitHub

| Requirement | Detail |
|---|---|
| **API** | GitHub REST API v3 and `gh` CLI |
| **Authentication** | Personal Access Token (PAT) stored in `GITHUB_TOKEN` |
| **Required PAT scopes** | `repo` (full), `pull_requests:write`, `actions:read`, `read:org` |
| **Webhook configuration** | Repository Settings → Webhooks → Content type: `application/json`, Events: `Pull requests`, `Workflow runs`, `Branch or tag creation` |
| **Webhook secret** | Random string stored in `WEBHOOK_SECRET`; used for HMAC-SHA256 payload validation |
| **Branch protection** | Agent-created branches MUST be subject to the same branch protection rules as human-created branches (require PR, require passing status checks) |

**GitHub PAT Setup:**
1. Navigate to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Set repository access to `Gedat-GmbH/tj-sales` only (principle of least privilege)
3. Grant: Contents (read/write), Pull Requests (read/write), Actions (read), Metadata (read)
4. Store in Azure Key Vault under secret name `github-pat-agents`

### 7.4 LangSmith

| Requirement | Detail |
|---|---|
| **Account** | LangSmith account at `smith.langchain.com` (team plan recommended for shared dataset access) |
| **API key** | `LANGSMITH_API_KEY` — obtain from LangSmith → Settings → API Keys |
| **Project name** | `tj-sales-agents` (production), `tj-sales-agents-ci` (CI evaluation runs) |
| **Dataset** | `scaffold-benchmark` — created once via `python -m agents.evals.create_dataset` |
| **Tracing toggle** | `LANGSMITH_TRACING=true` enables tracing; set to `false` in unit tests to avoid noise |
| **Data residency** | Verify LangSmith's data residency policy meets GDPR requirements — traces may contain Jira ticket content and code snippets |

---

## 8. Credential & Secrets Requirements

All secrets MUST be stored in **Azure Key Vault** and MUST NOT be committed to the repository. The following secrets MUST be created before deployment:

| Secret Name (Key Vault) | Environment Variable | Description |
|---|---|---|
| `azure-openai-endpoint` | `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource URL |
| `azure-openai-api-key` | `AZURE_OPENAI_API_KEY` | Azure OpenAI access key |
| `github-pat-agents` | `GITHUB_TOKEN` | GitHub PAT for agent operations |
| `jira-api-token` | `JIRA_API_TOKEN` | Atlassian Jira API token |
| `jira-user-email` | `JIRA_USER_EMAIL` | Email of the Jira service account |
| `jira-base-url` | `JIRA_BASE_URL` | Atlassian instance URL |
| `langsmith-api-key` | `LANGSMITH_API_KEY` | LangSmith tracing + evaluation |
| `webhook-secret` | `WEBHOOK_SECRET` | HMAC secret for GitHub webhook validation |

Non-secret configuration (safe to store in Kubernetes ConfigMap or Helm values):

| Variable | Example Value | Description |
|---|---|---|
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` | Primary model deployment name |
| `AZURE_OPENAI_MINI_DEPLOYMENT` | `gpt-4o-mini` | Mini model deployment name |
| `GITHUB_REPO` | `Gedat-GmbH/tj-sales` | Repository identifier |
| `JIRA_PROJECT_KEY` | `TJS` | Jira project key |
| `LANGSMITH_TRACING` | `true` | Enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | `tj-sales-agents` | LangSmith project name |
| `WEBHOOK_PORT` | `8080` | Port the webhook server listens on |

---

## 9. Convention & Knowledge Base Requirements

The agents derive their understanding of tj-sales coding conventions from versioned Markdown files. These files are the **single source of truth** for what the agents enforce.

**REQ-CONV-01** — The following convention files MUST exist at `agents/conventions/` and MUST be kept up to date:

| File | Content |
|---|---|
| `backend-patterns.md` | CQRS pattern, Result pattern, FluentValidation rules, FastEndpoints base classes, DI marker interfaces, namespace mapping (Sales/People/Disposition), error handling |
| `frontend-patterns.md` | OnPush change detection, standalone components, signals vs observables, Transloco i18n key registration, generated API service usage, TailwindCSS styling |
| `test-patterns.md` | xUnit structure, AwesomeAssertions assertions, AutoFixture (`Fake.Create<T>()`), Moq mocking, integration test base classes (`TalentTestBase`, etc.), file naming conventions |

**REQ-CONV-02** — Convention files MUST be reviewed and updated as part of any **Architecture Decision Record (ADR)** or significant pattern change. A stale convention file is a regression risk.

**REQ-CONV-03** — Convention files MUST be loadable at agent startup and injected into LLM system prompts. They MUST be plain UTF-8 Markdown with no binary content.

**REQ-CONV-04** — The LangSmith `scaffold-benchmark` dataset MUST include at least one example from each of the three namespace groups: `Sales`, `People`, `Disposition`. This ensures evaluators catch namespace regressions across all module types.

---

## 10. CI/CD Requirements

### GitHub Actions Workflows

The following workflows MUST be added to `.github/workflows/`:

| Workflow File | Trigger | Purpose |
|---|---|---|
| `agent-eval.yml` | PR touching `agents/**` | Run LangSmith benchmark; fail PR if evaluator scores regress |
| `run-agent.yml` | `workflow_dispatch` (manual) | Trigger any agent task manually from the GitHub Actions UI with a Jira key or task name |

### Docker Image Build

**REQ-CI-01** — The `agents/Dockerfile` MUST be built and pushed to ACR as part of the main CI pipeline whenever code under `agents/` changes.

**REQ-CI-02** — The Docker image MUST include `dotnet` (8.x) and `node` (20.x) installed alongside Python 3.11, as the agent tools invoke these CLIs at runtime.

**REQ-CI-03** — The image MUST be tagged with the Git short SHA (`$(git rev-parse --short HEAD)`) in addition to `latest`.

### Webhook Availability

**REQ-CI-04** — The agent service MUST be publicly reachable via HTTPS for webhook delivery from GitHub and Atlassian. If running behind a private AKS ingress, an Azure API Management or Azure Application Gateway instance MUST forward webhook traffic.

**REQ-CI-05** — The agent service MUST expose a `GET /health` endpoint returning `{"status": "ok"}` for Kubernetes liveness and readiness probes.

---

## 11. Acceptance Criteria

The requirements in this document are considered met when all of the following conditions are verified:

| ID | Acceptance Criterion | Verification Method |
|---|---|---|
| AC-01 | A Jira ticket transitioned to "In Progress" automatically triggers the feature workflow and opens a draft PR within 5 minutes | Manual test with `TJS-TEST-1` ticket |
| AC-02 | The build-fix loop in `build_fix_loop_graph` correctly cycles `build_check → fix → build_check` and exits after 3 failed attempts | Unit test with mocked `dotnet_build` returning 3 failures then success |
| AC-03 | A failing GitHub Actions run creates a Jira bug ticket with the root cause and a link to the failed run within 2 minutes | Manually trigger a failing workflow; observe Jira |
| AC-04 | A PR opened on GitHub receives a code review comment within 30 seconds identifying at least one convention violation in a deliberately incorrect diff | Integration test with a test PR |
| AC-05 | The `scaffold-benchmark` evaluation suite reports ≥ 90% `build_succeeds` score across all examples | Run `python -m agents.evals.run_eval` |
| AC-06 | All 4 evaluators (`uses_result_pattern`, `has_fluent_validation`, `build_succeeds`, `correct_namespace`) pass for at least 4 of 5 benchmark examples | LangSmith UI — experiment results |
| AC-07 | The `agent-eval.yml` GitHub Actions workflow runs automatically on a PR modifying `agents/planner.py` and reports pass/fail | Open a test PR |
| AC-08 | Approving a paused feature workflow via `approve_and_resume(thread_id)` resumes execution and opens the PR | Manual test |
| AC-09 | No secrets appear in any committed file (`.env`, source code, Helm values) | `git grep -r "ghp_\|jira.*token\|openai.*key"` returns no results |
| AC-10 | All LangSmith traces for a complete feature workflow run are queryable and show per-node durations and state deltas | LangSmith UI inspection after AC-01 test |

---

## 12. Out of Scope

The following are explicitly **not** requirements for the initial delivery:

- **Fully autonomous deployment** — Agents will never trigger staging or production deployments. All deployment decisions remain with the CI/CD pipeline and human operators.
- **Modification of `ai/` service** — The existing Python AI service (`ai/`) MUST NOT be modified. Agents run as a separate package.
- **Replacing human code review** — The Code Review Agent supplements human review; it does not replace it. PR merge always requires human approval.
- **Real-time pair programming** — The agent system is batch/event-driven, not interactive. For interactive assistance, GitHub Copilot (CLI or IDE) remains the tool of choice.
- **Multi-repository support** — Initial implementation targets `tj-sales` only. Extension to other repositories is a future concern.
- **Self-updating convention files** — Agents will NOT modify their own convention files. Convention updates require a human developer.

---

*Document authored with GitHub Copilot · Last updated: 2026-05-04*
