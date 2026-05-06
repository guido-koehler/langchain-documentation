# LangChain Multi-Agent Evaluation — Executive Summary

> **Audience:** Product Owner  
> **Source:** [langchain-multi-agent-evaluation.md](./langchain-multi-agent-evaluation.md)  
> **Last updated:** 2026-05-06

---

## What Are We Evaluating?

The feasibility of using **LangChain/LangGraph** to automate recurring development workflows in `tj-sales` — such as code reviews, i18n translations, CI/CD failure analysis, and feature scaffolding — through a set of specialised, orchestrated AI agents.

---

## Agentic IDEs vs. Custom LangGraph Workflow

These two approaches are **complementary, not competing**:

| | Agentic IDEs (GitHub Copilot, Cursor) | Custom LangGraph Workflow |
|---|---|---|
| **Who uses it?** | Individual developer, interactively | Automated pipeline, no human present |
| **Runs unattended?** | ❌ Requires an active developer session | ✅ Webhook- or schedule-triggered |
| **Jira / GitHub Actions aware?** | ❌ No — developer must copy context manually | ✅ Full REST API integration |
| **Convention enforcement?** | Implicit — often forgets rules between sessions | Explicit — rules encoded in versioned files, always applied |
| **Observability / audit trail?** | Minimal — proprietary black box | Full trace per run via LangSmith |
| **Setup time?** | Minutes | 2–12 weeks (phased) |
| **Cost model** | Monthly SaaS per seat | Pay-per-token (Azure OpenAI) |

**Rule of thumb:** use GitHub Copilot when a developer is present and steering; use LangGraph when the task must run automatically, reliably, and repeatably.

---

## Key Advantages

- Automates boilerplate-heavy tasks (CQRS scaffolding, translations, release notes)
- Integrates natively with existing Azure OpenAI, Python `ai/`, and Service Bus infrastructure
- Enforces architectural conventions on every run — reducing review load
- Supports iterative loops (e.g. compile → fix → recompile) that agentic IDEs cannot express

## Key Risks

- **Non-determinism** — LLM output varies; generated code must always be human-reviewed before merge
- **Maintenance burden** — convention changes must be reflected in agent prompts
- **Cost** — a full scaffold workflow may cost €0.50–€2.00 per run in Azure OpenAI tokens

---

## Expected Effort (Phased Roadmap)

| Phase | Agent | Effort | Risk |
|---|---|---|---|
| 1 | Code Review Agent | **2 weeks** | Low |
| 2 | Translation Agent | **1 week** | Low |
| 3 | CI/CD Monitor Agent | **2 weeks** | Medium |
| 4 | Backend Scaffold Agent | **3 weeks** | Medium |
| 5 | Full Feature Workflow (end-to-end) | **4 weeks** | Higher |

**Total: ~12 weeks** to full automation. Phases 1–3 deliver value quickly (~5 weeks) with near-zero risk of broken code.

---

## Recommendation

Start with **Phase 1–3** (read-only agents) to build confidence and tooling. Use GitHub Copilot for interactive coding sessions in parallel. Semi-autonomous mode — *agents open PRs, humans merge* — is the recommended operating model.
