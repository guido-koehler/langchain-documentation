# Implementation Gap Analysis & Action Plan

> **Generated from:** Comparison of `langchain-agent-implementation-guide.md`, `langgraph-langsmith-requirements.md`, `Agent/hello_world/`, and `tj-sales/agents/`  
> **Scope:** Documentation accuracy gaps + code bugs/missing wiring in the tj-sales agent implementation  
> **Status:** All issues resolved ✅

---

## Overall Verdict

The `tj-sales/agents/` directory is **complete and correct** — all 8 agents, all graphs, all tools, and all config are present and wired. The issues identified during the gap analysis have been fixed.

---

## ✅ Resolved Issues

### DOC-01 — hello_world README described the wrong LLM client

**Files updated:** `Agent/README.md`, `Agent/requirements.txt`, `langchain-agent-implementation-guide.md` (section 1 Prerequisites)

The hello_world demo correctly uses `AzureChatOpenAI` from `langchain_openai`, connecting to a plain Azure OpenAI endpoint (`*.openai.azure.com`). The documentation previously described it as using Azure AI Foundry / `AzureAIChatCompletionsModel` — which was incorrect.

**The distinction documented clearly:**

| | hello_world demo | tj-sales agents/ |
|---|---|---|
| **Package** | `langchain_openai` | `langchain_azure_ai` |
| **Class** | `AzureChatOpenAI` | `AzureAIChatCompletionsModel` |
| **Endpoint** | Azure OpenAI (`*.openai.azure.com`) | Azure AI Foundry project endpoint |
| **Env vars** | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` | `AZURE_AI_PROJECT_ENDPOINT` |
| **Auth** | API key or `DefaultAzureCredential` | `DefaultAzureCredential` only |

**Changes made:**
1. `Agent/README.md` — corrected `llm.py` file-structure entry; updated setup section env vars; added a note explaining the demo uses Azure OpenAI directly while the full `agents/` package uses Azure AI Foundry.
2. `Agent/requirements.txt` — replaced `langchain-azure-ai[opentelemetry]` with `langchain-openai>=0.3.0`.
3. `langchain-agent-implementation-guide.md` section 1 — replaced `AZURE_OPENAI_ENDPOINT`/`AZURE_OPENAI_API_KEY` with `AZURE_AI_PROJECT_ENDPOINT`/`MODEL_DEPLOYMENT_NAME`/`MODEL_MINI_DEPLOYMENT_NAME`; replaced `LANGCHAIN_API_KEY` with `LANGSMITH_API_KEY`.

---

### BUG-01 — Feature workflow checkpointer was `None` in webhook

**File fixed:** `tj-sales/agents/main.py`

The Jira webhook now calls `trigger_feature(issue_key)` directly instead of `build_feature_graph(checkpointer=None).ainvoke(...)`. `trigger_feature` correctly creates an `AsyncSqliteSaver` checkpointer via `get_checkpointer()`, sets a deterministic `thread_id = f"feature-{jira_key}"`, and invokes the graph — enabling the human-in-the-loop `interrupt_before=["open_pr"]` to work correctly.

---

### BUG-02 — Release notes webhook was a stub

**File fixed:** `tj-sales/agents/main.py`

The `create` + `ref_type=tag` webhook handler now dispatches `_trigger_release_notes(tag)` as a background task. The helper fetches the previous tag via `GET /repos/{repo}/tags`, then calls `generate_release_notes(new_tag, previous_tag)`.

---

### BUG-03 — `list_merged_prs_since_tag` ignored the `tag` parameter

**File fixed:** `tj-sales/agents/tools/github_tools.py`

The tool now:
1. Resolves the tag ref to a commit SHA via `GET /repos/{repo}/git/refs/tags/{tag}` (dereferencing annotated tags if needed).
2. Fetches the commit date via `GET /repos/{repo}/git/commits/{sha}`.
3. Filters returned PRs to those whose `merged_at > tag_date`.

---

### BUG-04 — Translation source/target language mismatch

**File fixed:** `tj-sales/agents/agents/translation.py`

`_SOURCE_LANG` was set to `"de"` (dead code, contradicted the function default `source_lang="en"`). Fixed to `_SOURCE_LANG = "en"` to match the function default and the intended `en → de` translation direction.

---

### ARC-01 — `build_fix_loop_graph.py` was orphaned dead code

**File fixed:** `tj-sales/agents/agents/backend_scaffold.py`

`scaffold_and_verify()` now delegates to `build_build_fix_loop_graph()` via a local import (to avoid circular imports). The scaffold → build → fix retry cycle is now expressed as proper LangGraph nodes, giving full LangSmith traceability. The previous inline loop has been removed.

---

### ARC-02 — Translation workflow not reachable from server

**File fixed:** `tj-sales/agents/main.py`

Added `POST /trigger/translation` endpoint. Protected by `Authorization: Bearer <WEBHOOK_SECRET>`. Intended for nightly cron jobs or pre-commit CI pipelines. Dispatches `translate_missing_keys()` as a background task.

---

### ARC-03 — CI recovery graph was missing the fix-issue node

**File fixed:** `tj-sales/agents/graphs/ci_recovery_workflow.py`

Added `open_fix_issue_node` and conditional routing:

```
analyse → route_after_analyse() ──► open_fix_issue (category == "build-error")
                                └──► END (all other categories)
open_fix_issue → END
```

For build errors, the node opens a GitHub issue via the new `create_github_issue` tool, labelled `ci-failure`, `ai-suggested-fix`, and the affected component. The Jira ticket (created by `ci_monitor`) covers non-build failures. The `CIState` was extended with `fix_issue_url: str | None`.

---

### MIN-01 — Duplicate `import logging` in `agents/main.py`

**File fixed:** `tj-sales/agents/main.py` — second `import logging` on line 29 removed.

---

### MIN-02 — Inconsistent LangSmith project env-var naming

**File fixed:** `tj-sales/agents/main.py`

`os.getenv("LANGCHAIN_PROJECT", ...)` → `os.getenv("LANGSMITH_PROJECT", ...)`. The `.env.example` uses `LANGSMITH_PROJECT` (user-facing); internally it is mapped to `LANGCHAIN_PROJECT` (LangChain SDK env var). This matches the pattern already used in `hello_world/main.py`.

---

### MIN-03 — Missing `[tools]` extra in `requirements.txt`

**File fixed:** `tj-sales/agents/requirements.txt`

`langchain-azure-ai[opentelemetry]` → `langchain-azure-ai[tools,opentelemetry]` to ensure built-in LangChain tool integrations are available.

---

## What Is Complete and Correct

| Area | Status |
|---|---|
| All 8 agents (planner, backend_scaffold, frontend_scaffold, test_writer, code_review, ci_monitor, translation, release_notes) | ✅ |
| All LangGraph graphs (feature_workflow, review_workflow, ci_recovery, translation_workflow, build_fix_loop) | ✅ |
| All tools (github, jira, dotnet, nx, filesystem) | ✅ |
| Config: settings, LLM client (`AzureAIChatCompletionsModel` + `DefaultAzureCredential`), checkpointer | ✅ |
| FastAPI webhook server with GitHub + Jira handlers | ✅ |
| Human-in-the-loop `interrupt_before=["open_pr"]` with real checkpointer | ✅ |
| LangSmith tracing setup | ✅ |
| Conventions folder (backend, frontend, test patterns) | ✅ |
| Evals folder (create_dataset, evaluators, run_eval) | ✅ |
| `.env.example` | ✅ |
| Release notes generation wired to tag webhook | ✅ |
| Translation endpoint (`POST /trigger/translation`) | ✅ |
| CI recovery fix-issue node for build errors | ✅ |
| `build_fix_loop_graph` adopted (LangSmith-traced scaffold→build→fix cycle) | ✅ |

---

