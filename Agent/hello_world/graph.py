"""
LangGraph graph definition for the Hello World self-correction agent.

Graph topology
──────────────
  START
    │
    ▼
  generate_node   ◄──────────────────┐
    │                                │  "retry"
    ▼                                │
  validate_node ── should_retry() ───┘
                       │
                       │  "done"
                       ▼
                      END

The conditional edge after validate_node either loops back to generate_node
(when feedback is non-empty and max_attempts hasn't been reached) or exits.
"""
from langgraph.graph import END, START, StateGraph

from .nodes import generate_node, should_retry, validate_node
from .state import HelloWorldState


def build_graph() -> StateGraph:
    """Compile and return the self-correction graph."""
    builder = StateGraph(HelloWorldState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)

    # ── Edges ──────────────────────────────────────────────────────────────────
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "validate")

    # Conditional edge: after validation, either retry or finish
    builder.add_conditional_edges(
        "validate",
        should_retry,
        {
            "retry": "generate",
            "done": END,
        },
    )

    return builder.compile()
