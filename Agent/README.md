# Hello World — LangGraph Self-Correction Agent

A minimal but complete **LangGraph** agent that demonstrates:

- **Stateful graph execution** with a `TypedDict` state
- **Self-correction loop** — the agent retries until its output passes validation (or hits `max_attempts`)
- **LangSmith tracing** — every LLM call, node, and edge transition is recorded and visible in the LangSmith UI

This is a standalone demo. The same patterns are used by all production agents described in [`langchain-agent-implementation-guide.md`](../langchain-agent-implementation-guide.md).

---

## Graph Topology

```
START
  │
  ▼
generate_node   ◄──────────────────────┐
  │                                    │  "retry" (feedback != "" and attempts < max)
  ▼                                    │
validate_node ── should_retry() ───────┘
                     │
                     │  "done"
                     ▼
                    END
```

| Node | Responsibility |
|---|---|
| `generate_node` | Calls the Azure OpenAI service to produce (or fix) the result. On retries, includes the validator's feedback in the prompt. |
| `validate_node` | Checks the result against simple rules (code fence present, contains "Hello World"). Returns human-readable feedback on failure. |
| `should_retry` | Conditional edge router — loops back to `generate_node` if there is feedback and `max_attempts` has not been reached. |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- An **Azure OpenAI** resource with a deployed chat model (e.g. `gpt-5.4`) — [create one here](https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource)
- Either `az login` (recommended for keyless auth) **or** an Azure OpenAI API key for local development
- A **LangSmith** account (free tier is sufficient): [smith.langchain.com](https://smith.langchain.com)

> **Demo vs. production LLM client**  
> This hello-world demo connects to **Azure OpenAI** directly (`*.openai.azure.com`) using `AzureChatOpenAI` from `langchain-openai`. It requires `AZURE_OPENAI_ENDPOINT` and optionally `AZURE_OPENAI_API_KEY`.  
> The production `agents/` package in tj-sales uses **Azure AI Foundry** (`AzureAIChatCompletionsModel` from `langchain-azure-ai`), which connects through a Foundry project endpoint and always uses `DefaultAzureCredential` — no API key needed.  
> The LangGraph patterns (state, nodes, graph, LangSmith tracing) are identical in both.

### 2. Create a virtual environment

```bash
# From the Agent/ directory
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Copy the template
cp .env.example .env

# Then edit .env and fill in your values:
#   AZURE_OPENAI_ENDPOINT      ← Azure OpenAI resource endpoint (*.openai.azure.com)
#   AZURE_OPENAI_API_KEY       ← leave blank if using `az login` (DefaultAzureCredential)
#   AZURE_OPENAI_API_VERSION   ← e.g. "2024-10-21" (default used if omitted)
#   MODEL_DEPLOYMENT_NAME      ← e.g. "gpt-5.4"
#   LANGSMITH_API_KEY          ← get from smith.langchain.com → Settings → API Keys
#   LANGSMITH_TRACING=true
#   LANGSMITH_PROJECT=tj-sales-hello-world
```

### 5. Run the agent

```bash
# From the Agent/ directory
python -m hello_world.main
```

Expected output:

```
════════════════════════════════════════════════════════════
  Hello World — LangGraph Self-Correction Agent
════════════════════════════════════════════════════════════

  🔭 LangSmith tracing ENABLED  →  project: 'tj-sales-hello-world'
     Dashboard: https://smith.langchain.com/projects/tj-sales-hello-world

  Task: Write a Hello World program in Python.

────────────────────────────────────────────────────────────
  ✓  Validation passed on attempt 1.
────────────────────────────────────────────────────────────

  ✅ Final result:

  ```python
  print("Hello, World!")
  ```

  Completed in 1 attempt(s).

  🔗 LangSmith trace: https://smith.langchain.com/public/<run-id>/r
════════════════════════════════════════════════════════════
```

---

## LangSmith — Live Tracing Walkthrough

Once you have run the agent with `LANGSMITH_TRACING=true`, follow these steps to explore the trace:

### Step 1 — Open the project

Go to [smith.langchain.com](https://smith.langchain.com) and open the **`tj-sales-hello-world`** project.

### Step 2 — Open the run

Click the most recent run named **`hello-world-demo`**. You will see a **flame-graph** breakdown of the entire execution.

### Step 3 — Explore the nodes

| What to look for | Where to find it |
|---|---|
| The `generate` node | Expand it → see the full system prompt + user message sent to Azure AI Foundry |
| The `validate` node | See the state snapshot before and after — `feedback` will be `""` on a passing run |
| Token usage & cost | Shown per LLM call in the right panel |
| Latency | Each node's wall-clock time is displayed on the flame bar |

### Step 4 — Trigger the self-correction loop (optional)

To see the retry loop in action, temporarily set `max_attempts=3` and modify `validate_node` in `nodes.py` to always return a non-empty feedback string on the first attempt. Re-run the agent and observe the graph looping back in LangSmith.

### Step 5 — Compare runs

In the LangSmith project view, select two runs and click **"Compare"** to see differences in latency, token usage, and output side by side. This is the same mechanism used to validate prompt changes before deploying to production.

---

## File Structure

```
Agent/
├── .env.example                  ← environment variable template
├── requirements.txt              ← pinned Python dependencies
├── README.md                     ← this file
└── hello_world/
    ├── __init__.py
    ├── state.py                  ← HelloWorldState TypedDict
    ├── llm.py                    ← AzureChatOpenAI client factory (Azure OpenAI — demo only; production agents use AzureAIChatCompletionsModel via langchain-azure-ai)
    ├── nodes.py                  ← generate_node, validate_node, should_retry
    ├── graph.py                  ← StateGraph wiring
    └── main.py                   ← entry point + LangSmith trace URL printer
```

---

## Next Steps

This Hello World agent uses the same building blocks as the production agents:

| Production agent | What it adds on top of this demo |
|---|---|
| **Code Review Agent** | GitHub diff as input, convention rules as validation criteria |
| **Backend Scaffold Agent** | `dotnet build` as the validator instead of a string check |
| **Translation Agent** | JSON key/value files as state, Azure AI Foundry for translation |
| **CI/CD Monitor Agent** | GitHub Actions log as input, Jira API as an output tool |

See [`langchain-agent-implementation-guide.md`](../langchain-agent-implementation-guide.md) for the full implementation of each agent.
