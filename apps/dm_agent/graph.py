from __future__ import annotations

try:
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:
    from .runtime_graph import END, START, StateGraph

from .nodes import (
    analyze_intent_node,
    apply_consequences_node,
    load_memory_node,
    render_narrative_node,
    resolve_action_node,
    should_roll_node,
)
from .state import GMState


def _route_after_roll_check(state: GMState) -> str:
    if state.get("needs_roll"):
        return "resolve_action"
    return "apply_consequences"


def build_graph():
    graph = StateGraph(GMState)
    graph.add_node("load_memory", load_memory_node)
    graph.add_node("analyze_intent", analyze_intent_node)
    graph.add_node("should_roll", should_roll_node)
    graph.add_node("resolve_action", resolve_action_node)
    graph.add_node("apply_consequences", apply_consequences_node)
    graph.add_node("render_narrative", render_narrative_node)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "analyze_intent")
    graph.add_edge("analyze_intent", "should_roll")
    graph.add_conditional_edges(
        "should_roll",
        _route_after_roll_check,
        {
            "resolve_action": "resolve_action",
            "apply_consequences": "apply_consequences",
        },
    )
    graph.add_edge("resolve_action", "apply_consequences")
    graph.add_edge("apply_consequences", "render_narrative")
    graph.add_edge("render_narrative", END)

    return graph.compile()
