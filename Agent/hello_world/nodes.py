"""
Nodes for the Hello World self-correction agent.

Graph topology:
                        ┌─────────────────────────────┐
                        ▼                             │  (feedback != "" and
    START ──► generate_node ──► validate_node         │   attempt_count < max)
                                    │
                                    └──► END  (feedback == "" or max attempts reached)

Node responsibilities
─────────────────────
generate_node   Calls the LLM to produce (or improve) the result.
                On subsequent calls it receives the validator's feedback and
                asks the LLM to fix the previous attempt.

validate_node   Checks the result against a simple rule set and writes
                human-readable feedback.  Empty feedback = acceptable output.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from .llm import get_llm
from .state import HelloWorldState


# ── Generate ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful coding assistant.
When asked to write code:
- Output ONLY the code block (no prose outside the code fence).
- Use a triple-backtick fence with the language tag, e.g. ```python.
- Make the code correct and runnable.
"""


def generate_node(state: HelloWorldState) -> dict:
    """
    Call the LLM to generate (or re-generate) the result.

    On the first attempt the prompt is the raw task.
    On subsequent attempts the validator's feedback is appended so the LLM
    can self-correct.
    """
    llm = get_llm()

    if state["attempt_count"] == 0 or not state["feedback"]:
        user_content = state["task"]
    else:
        user_content = (
            f"Previous attempt:\n{state['result']}\n\n"
            f"Feedback (fix these issues):\n{state['feedback']}\n\n"
            f"Original task: {state['task']}"
        )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)

    return {
        "result": response.content,
        "attempt_count": state["attempt_count"] + 1,
        # Clear feedback so the router doesn't re-enter the loop on stale data
        "feedback": "",
    }


# ── Validate ──────────────────────────────────────────────────────────────────

def validate_node(state: HelloWorldState) -> dict:
    """
    Validate the generated result against a minimal rule set.

    Rules (deliberately simple for a Hello World demo):
    1. The output must contain a code fence (```).
    2. The output must contain the words 'Hello' and 'World' (case-insensitive).

    Returns empty feedback if the output is acceptable; otherwise returns a
    description of what needs to be fixed so generate_node can self-correct.
    """
    result = state["result"]
    issues: list[str] = []

    if "```" not in result:
        issues.append(
            "The response must be wrapped in a triple-backtick code fence (e.g. ```python ... ```)."
        )

    if "hello" not in result.lower() or "world" not in result.lower():
        issues.append(
            "The output must print (or display) the text 'Hello, World!'."
        )

    feedback = "\n".join(f"- {issue}" for issue in issues)
    return {"feedback": feedback}


# ── Router (used as conditional edge) ─────────────────────────────────────────

def should_retry(state: HelloWorldState) -> str:
    """
    Routing function called after validate_node.

    Returns:
        "retry"  → route back to generate_node for self-correction
        "done"   → route to END
    """
    has_feedback = bool(state["feedback"].strip())
    within_limit = state["attempt_count"] < state["max_attempts"]

    if has_feedback and within_limit:
        print(
            f"  ↺  Attempt {state['attempt_count']} failed validation "
            f"(attempt {state['attempt_count']}/{state['max_attempts']}). Retrying…\n"
            f"     Feedback: {state['feedback']}"
        )
        return "retry"

    if has_feedback:
        print(
            f"  ✗  Max attempts ({state['max_attempts']}) reached. "
            "Returning best result so far."
        )
    else:
        print(f"  ✓  Validation passed on attempt {state['attempt_count']}.")

    return "done"
