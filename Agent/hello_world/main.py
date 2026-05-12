"""
Entry point for the Hello World self-correction agent.

Run from the Agent/ directory:

    python -m hello_world.main

What this script does
─────────────────────
1. Loads environment variables from .env (including LangSmith keys).
2. Builds the LangGraph graph.
3. Runs the graph with a simple "Hello World" task.
4. Prints the final result.
5. Prints a direct link to the LangSmith trace (when tracing is enabled).
"""
import os
import sys

from dotenv import load_dotenv

# Load .env from the Agent/ directory (one level up from hello_world/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_env_path, override=False)

# ── LangSmith tracing — must be configured BEFORE importing LangChain ──────────
# These env vars are read by the LangChain SDK at import time.
# If LANGSMITH_TRACING is "false" or unset, no data is sent.
_tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
if _tracing_enabled:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))
    os.environ.setdefault(
        "LANGCHAIN_ENDPOINT",
        os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
    )
    os.environ.setdefault(
        "LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "tj-sales-hello-world")
    )

from langsmith import Client  # noqa: E402  (import after env setup)

from .graph import build_graph  # noqa: E402
from .state import HelloWorldState  # noqa: E402


def main() -> None:
    print("═" * 60)
    print("  Hello World — LangGraph Self-Correction Agent")
    print("═" * 60)

    if _tracing_enabled:
        project = os.environ.get("LANGCHAIN_PROJECT", "tj-sales-hello-world")
        _ui_base = os.environ.get(
            "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"
        ).replace("api.smith.langchain.com", "smith.langchain.com")
        print(f"\n  🔭 LangSmith tracing ENABLED  →  project: '{project}'")
        print(f"     Dashboard: {_ui_base}/projects/{project}\n")
    else:
        print("\n  ⚠️  LangSmith tracing DISABLED  (set LANGSMITH_TRACING=true to enable)\n")

    graph = build_graph()

    initial_state: HelloWorldState = {
        "task": "Write a Hello World program in Python.",
        "result": "",
        "feedback": "",
        "attempt_count": 0,
        "max_attempts": 3,
    }

    print(f"  Task: {initial_state['task']}\n")
    print("─" * 60)

    # run_id is returned in the graph output metadata when tracing is enabled
    config = {"run_name": "hello-world-demo"}
    final_state = graph.invoke(initial_state, config=config)

    print("─" * 60)
    print("\n  ✅ Final result:\n")
    print(final_state["result"])
    print(f"\n  Completed in {final_state['attempt_count']} attempt(s).")

    # ── Print LangSmith trace URL ───────────────────────────────────────────────
    if _tracing_enabled:
        _print_trace_url(project=os.environ.get("LANGCHAIN_PROJECT", "tj-sales-hello-world"))

    print("\n" + "═" * 60)


def _print_trace_url(project: str) -> None:
    """
    Fetch the most recent run for this project from LangSmith and print its URL.

    This is a convenience helper for the demo — in production you would capture
    the run_id from the graph output and construct the URL directly.
    """
    try:
        client = Client()
        _ui_base = os.environ.get(
            "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"
        ).replace("api.smith.langchain.com", "smith.langchain.com")
        runs = list(
            client.list_runs(
                project_name=project,
                run_type="chain",
                limit=1,
            )
        )
        if runs:
            run = runs[0]
            url = f"{_ui_base}/public/{run.id}/r"
            print(f"\n  🔗 LangSmith trace: {url}")
    except Exception as exc:  # noqa: BLE001
        print(f"\n  (Could not fetch LangSmith trace URL: {exc})")


if __name__ == "__main__":
    main()
