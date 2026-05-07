# LangChain Documentation — AI Coding Agent Instructions

## Repository Purpose

This repository contains the **documentation for the agentic development setup** used in the [tj-sales](C:\Users\Guido.Koehler\source\repos\tj-sales) project. It covers architecture decisions, requirements specifications, and implementation guides for the LangChain/LangGraph-based multi-agent system that automates development workflows for tj-sales.

### Documents in this Repository

| File | Description |
|------|-------------|
| `langchain-agent-implementation-guide.md` | Step-by-step implementation guide for all agents (code review, translation, CI/CD monitor, scaffold, feature workflow, release notes) |
| `langchain-multi-agent-evaluation.md` | Feasibility evaluation and strategic comparison of the multi-agent approach |
| `langgraph-langsmith-requirements.md` | Functional and non-functional requirements for the agentic setup, including Jira and GitHub integrations |

## Related Repository

The **tj-sales** application being served by these agents lives at:

```
C:\Users\Guido.Koehler\source\repos\tj-sales
```

Its own Copilot instructions (architecture, patterns, conventions) are at:

```
C:\Users\Guido.Koehler\source\repos\tj-sales\.github\copilot-instructions.md
```

Always consult the tj-sales `copilot-instructions.md` for details on the target codebase architecture (backend .NET patterns, Angular frontend conventions, module structure, etc.) when writing or reviewing agent implementations that interact with tj-sales code.

## Development Workflow

### Work Organisation — Jira

- All features, bugs, and tasks are tracked as **Jira tickets** inside **Sprints**.
- When implementing or documenting a new agent or workflow, reference the corresponding Jira ticket number in commit messages and PR descriptions (e.g. `TJS-123`).

### Source Control — GitHub

- Code lives in **GitHub repositories**.
- Changes are introduced via **Pull Requests** from feature branches into `main`.
- Branch naming convention follows the Jira ticket: `feature/TJS-123-short-description`.
- PRs require passing CI checks before merge.

### CI/CD — GitHub Actions

- **Automated tests** and **code coverage checks** run on every PR via GitHub Actions.
- Agent implementations in the ai/ layer of tj-sales must maintain or improve test coverage.
- Do not merge code that causes CI to fail.

## Agent System Overview

The agentic setup orchestrates the following agents for the tj-sales project:

| Agent | Responsibility |
|-------|---------------|
| Code Review Agent | Reviews PRs for convention compliance and architecture patterns |
| Translation Agent | Manages i18n translation files across the Angular frontend |
| CI/CD Monitor Agent | Monitors GitHub Actions runs and surfaces failures |
| Backend Scaffold Agent | Generates new .NET modules following tj-sales conventions |
| Frontend Scaffold Agent | Generates Angular micro-frontend components and modules |
| Test Writer Agent | Writes unit and integration tests for new code |
| Feature Planner Agent | Decomposes Jira tickets into implementation tasks |
| Release Notes Agent | Generates release notes from merged PRs and commits |

All agents are orchestrated using **LangGraph** and observed via **LangSmith**.

## Infrastructure — Azure AI Foundry

Agents and LLMs are hosted on **Microsoft Azure AI Foundry** — no separate Azure OpenAI instance is required.

- Models (`claude-sonnet-4-6` for complex tasks, `claude-haiku-4-5` for fast/cheap tasks) are deployed as serverless endpoints inside a **Foundry project**.
- LangChain/LangGraph connects to the Claude models via the [`langchain-anthropic`](https://python.langchain.com/docs/integrations/providers/anthropic/) package, using the Foundry project endpoint as `base_url`.
- Authentication uses an **Azure-issued API key** for the Claude serverless deployments (`AZURE_AI_API_KEY`); injected from Key Vault in production.
- Observability (traces for agent steps, tool calls, LLM calls) flows through **OpenTelemetry → Application Insights**, visible in the Foundry portal under **Observability → Traces**.

### Required packages

```bash
pip install langchain-anthropic langchain-azure-ai[opentelemetry] azure-identity
```

### Required environment variables

```bash
AZURE_AI_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
AZURE_AI_API_KEY=<azure-foundry-api-key-for-claude-deployments>
MODEL_DEPLOYMENT_NAME=claude-sonnet-4-6          # primary: scaffold, review, planning
MODEL_MINI_DEPLOYMENT_NAME=claude-haiku-4-5      # mini: translation, summaries, CI analysis
APPLICATION_INSIGHTS_CONNECTION_STRING=<connection-string>   # for tracing
```

> LangGraph agent logic (graph definition, tools, state) is unchanged when targeting Foundry. Only the model client and hosting entry point differ from a plain Azure OpenAI setup.
