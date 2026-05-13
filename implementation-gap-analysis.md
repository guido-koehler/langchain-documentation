# Implementation Gap Analysis & Action Plan

> **Generated from:** Comparison of `langchain-agent-implementation-guide.md`, `langgraph-langsmith-requirements.md`, `Agent/hello_world/`, and `tj-sales/agents/`  
> **Scope:** Documentation accuracy gaps + code bugs/missing wiring in the tj-sales agent implementation

---

## Overall Verdict

The `tj-sales/agents/` directory is **substantially complete** — all 8 agents, all graphs, all tools, and all config are present and structurally correct. Issues fall into three categories: one documentation accuracy gap, several functional bugs, and a few missing wiring / architecture decisions.

---

## 🔴 Documentation Gap

### DOC-01 — hello_world README describes the wrong LLM client

**Files to update:** `Agent/README.md`, `langchain-agent-implementation-guide.md` (section 4.2)

The hello_world agent intentionally and correctly uses `AzureChatOpenAI` from `langchain_openai`, connecting to a plain Azure OpenAI endpoint (`*.openai.azure.com`). The documentation currently describes this agent as using Azure AI Foundry / `AzureAIChatCompletionsModel` — which is incorrect.

**Current state (code — correct, working):**
```python
# Agent/hello_world/llm.py
from langchain_openai import AzureChatOpenAI

def get_llm() -> AzureChatOpenAI:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    model_name = os.environ["MODEL_DEPLOYMENT_NAME"]
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    ...
```

**Current state (README — incorrect):**
> "LLM client factory (Azure AI Foundry)"

**The distinction that must be documented clearly:**

| | hello_world demo | tj-sales agents/ |
|---|---|---|
| **Package** | `langchain_openai` | `langchain_azure_ai` |
| **Class** | `AzureChatOpenAI` | `AzureAIChatCompletionsModel` |
| **Endpoint** | Azure OpenAI (`*.openai.azure.com`) | Azure AI Foundry project endpoint |
| **Env vars** | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` | `AZURE_AI_PROJECT_ENDPOINT` |
| **Auth** | API key or `DefaultAzureCredential` | `DefaultAzureCredential` only |

**Required changes:**
1. Update `Agent/README.md` — fix the file structure table entry for `llm.py`; update the setup section to list `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` as the required env vars; add a note explaining the demo uses Azure OpenAI directly (simpler setup) while the full `agents/` in tj-sales uses Azure AI Foundry.
2. Update `langchain-agent-implementation-guide.md` section 4.2 — either (a) keep the Foundry-only description and add a note that the hello_world demo uses a simpler Azure OpenAI client, or (b) add a separate subsection documenting both approaches.

---

## 🟡 Functional Bugs

### BUG-01 — Feature workflow checkpointer is `None` in webhook

**File:** `tj-sales/agents/main.py` line ~106

```python
# current (broken for human-in-the-loop)
build_feature_graph(checkpointer=None).ainvoke(...)
```

The feature graph is compiled with `interrupt_before=["open_pr"]`, but without a checkpointer the graph cannot persist state and the interrupt cannot be resumed. The `approve_and_resume()` function requires a checkpointer — the correct pattern already exists in `trigger_feature()`.

**Fix:**
```python
# in the webhook handler, initialise a real checkpointer:
from agents.config.checkpointer import get_checkpointer

async with get_checkpointer() as checkpointer:
    graph = build_feature_graph(checkpointer=checkpointer)
    thread_id = f"feature-{issue_key}"
    background.add_task(
        graph.ainvoke,
        {...},
        config={"configurable": {"thread_id": thread_id}},
    )
```

---

### BUG-02 — Release notes webhook is a stub

**File:** `tj-sales/agents/main.py` lines ~88–91

```python
elif event == "create" and payload.get("ref_type") == "tag":
    tag = payload["ref"]
    logger.info(f"New tag pushed: {tag} — release notes generation triggered")
    # ← generate_release_notes() is never called
```

`release_notes.py` is fully implemented but never invoked from the webhook. Requirements AGT-08 specify that release notes must be generated on a new tag push.

**Fix:** Call `generate_release_notes(new_tag=tag, previous_tag=previous_tag)` in a background task. Retrieve the previous tag from the GitHub API (`/repos/{repo}/tags`) before dispatching.

---

### BUG-03 — `list_merged_prs_since_tag` ignores the `tag` parameter

**File:** `tj-sales/agents/tools/github_tools.py`

```python
@tool
async def list_merged_prs_since_tag(tag: str) -> list[dict]:
    # tag is never used — returns ALL merged PRs
    r = await client.get(..., params={"state": "closed", "base": "main", "per_page": 100})
    return [pr for pr in r.json() if pr.get("merged_at")]
```

**Fix:** Resolve the tag to a commit date via `GET /repos/{repo}/git/refs/tags/{tag}` + `GET /repos/{repo}/git/commits/{sha}`, then filter `merged_at >= tag_commit_date`.

---

### BUG-04 — Translation source/target language mismatch

**File:** `tj-sales/agents/agents/translation.py`

```python
_SOURCE_LANG = "de"   # constant says German is the source
_TARGET_LANGS = ["de"]

async def translate_missing_keys(source_lang: str = "en"):  # default says English is the source
```

`_SOURCE_LANG` is defined but never used in the function. The function default `source_lang="en"` and `_TARGET_LANGS=["de"]` suggest the intent is `en → de`. `_SOURCE_LANG = "de"` is dead code and contradictory.

**Fix:** Set `_SOURCE_LANG = "en"` to match the function default (or remove the constant entirely).

---

## 🟠 Architecture / Wiring Gaps

### ARC-01 — `build_fix_loop_graph.py` is orphaned dead code

**File:** `tj-sales/agents/graphs/build_fix_loop_graph.py`

This graph is not imported or called anywhere. The same build-fix retry logic is already implemented inline in `backend_scaffold.py` (`scaffold_and_verify()`). The graph was intended to replace the inline approach but was never connected.

**Options:**
- **(A) Remove** `build_fix_loop_graph.py` and keep `scaffold_and_verify()` as-is (simpler, no change to other files).
- **(B) Adopt** the graph: refactor `scaffold_and_verify()` to delegate to `build_build_fix_loop_graph()`, giving the retry loop proper LangGraph traceability in LangSmith.

Option B is architecturally preferable (retry loops become first-class graph nodes, visible in LangSmith traces). Option A is lower risk.

---

### ARC-02 — Translation workflow not reachable from the server

**File:** `tj-sales/agents/graphs/translation_workflow.py`

The translation workflow is a standalone CLI script (`if __name__ == "__main__"`) with no endpoint in `main.py`. Requirements specify triggering on a nightly schedule or pre-commit hook — neither is implemented.

**Fix (pick one):**
- Add a `/trigger/translation` POST endpoint in `main.py` (protected by a shared secret, callable from a cron job or CI pipeline).
- Or document explicitly that the translation workflow is intentionally CLI-only and must be run manually / via a scheduled CI job.

---

### ARC-03 — CI recovery graph missing the fix-PR node

**File:** `tj-sales/agents/graphs/ci_recovery_workflow.py`

Requirements AGT-06 specify: *"optionally open a fix PR"*. The current graph has a single `analyse` node and immediately exits. There is no `fix_pr` node.

**Fix:** Add a conditional `fix_pr` node that calls `create_pull_request` when `analysis["category"] == "build-error"`. Route: `analyse → fix_pr? → END`.

---

## 🔵 Minor Issues

### MIN-01 — Duplicate `import logging` in `agents/main.py`

Lines 12 and 29 both import `logging`. Remove the duplicate.

### MIN-02 — Inconsistent LangSmith project env-var naming

- `hello_world/main.py` reads from `LANGSMITH_PROJECT` → sets `LANGCHAIN_PROJECT`
- `agents/main.py` reads from `LANGCHAIN_PROJECT` → sets `LANGCHAIN_PROJECT`

The `.env.example` for tj-sales names the variable `LANGCHAIN_PROJECT`; the hello_world `.env.example` would name it `LANGSMITH_PROJECT`. Standardise across both repos. Recommendation: use `LANGSMITH_PROJECT` in `.env` files (user-facing), map to `LANGCHAIN_PROJECT` internally (same as hello_world pattern).

### MIN-03 — Missing `[tools]` extra in `requirements.txt`

`langchain-azure-ai[opentelemetry]>=0.1.0` — the `tools` extra is missing. Add `[tools,opentelemetry]` to ensure built-in LangChain tool integrations are available.

---

## What Is Complete and Correct

| Area | Status |
|---|---|
| All 8 agents (planner, backend_scaffold, frontend_scaffold, test_writer, code_review, ci_monitor, translation, release_notes) | ✅ |
| All LangGraph graphs (feature_workflow, review_workflow, ci_recovery, translation_workflow, build_fix_loop) | ✅ |
| All tools (github, jira, dotnet, nx, filesystem) | ✅ |
| Config: settings, LLM client (`AzureAIChatCompletionsModel` + `DefaultAzureCredential`), checkpointer | ✅ |
| FastAPI webhook server with GitHub + Jira handlers | ✅ |
| Human-in-the-loop `interrupt_before=["open_pr"]` declared in feature graph | ✅ (see BUG-01 for wire-up) |
| LangSmith tracing setup | ✅ |
| Conventions folder (backend, frontend, test patterns) | ✅ |
| Evals folder (create_dataset, evaluators, run_eval) | ✅ |
| `.env.example` | ✅ |

---

## Action Order

| # | ID | Priority | Work item |
|---|---|---|---|
| 1 | DOC-01 | 🔴 Doc | Update hello_world README + impl guide to describe `AzureChatOpenAI` correctly and clarify hello_world vs tj-sales LLM distinction |
| 2 | BUG-01 | 🟡 Bug | Fix feature workflow checkpointer in webhook handler |
| 3 | BUG-02 | 🟡 Bug | Wire `generate_release_notes()` into the tag webhook |
| 4 | BUG-03 | 🟡 Bug | Fix `list_merged_prs_since_tag` to filter by tag date |
| 5 | BUG-04 | 🟡 Bug | Fix `_SOURCE_LANG = "en"` in translation agent |
| 6 | ARC-01 | 🟠 Design | Decide on `build_fix_loop_graph.py` (remove vs. adopt) |
| 7 | ARC-02 | 🟠 Design | Add translation trigger endpoint or document CLI-only approach |
| 8 | ARC-03 | 🟠 Design | Add fix-PR node to ci_recovery_workflow |
| 9 | MIN-01–03 | 🔵 Minor | Duplicate import, env-var naming, `[tools]` extra |
