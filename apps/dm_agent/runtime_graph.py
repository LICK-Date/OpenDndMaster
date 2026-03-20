from __future__ import annotations

from collections.abc import Callable
from typing import Any


START = "__start__"
END = "__end__"

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]
RouteFn = Callable[[dict[str, Any]], str]


class CompiledGraph:
    def __init__(
        self,
        nodes: dict[str, NodeFn],
        edges: dict[str, list[str]],
        conditional_edges: dict[str, tuple[RouteFn, dict[str, str]]],
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._conditional_edges = conditional_edges

    def invoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        state = dict(initial_state)
        current = START

        while True:
            next_node = self._next_node(current, state)
            if next_node == END:
                return state

            updates = self._nodes[next_node](state)
            if updates:
                state.update(updates)
            current = next_node

    def _next_node(self, current: str, state: dict[str, Any]) -> str:
        if current in self._conditional_edges:
            router, mapping = self._conditional_edges[current]
            route_key = router(state)
            return mapping[route_key]

        next_nodes = self._edges.get(current, [])
        if not next_nodes:
            return END
        return next_nodes[0]


class StateGraph:
    def __init__(self, _state_type: Any) -> None:
        self._nodes: dict[str, NodeFn] = {}
        self._edges: dict[str, list[str]] = {}
        self._conditional_edges: dict[str, tuple[RouteFn, dict[str, str]]] = {}

    def add_node(self, name: str, fn: NodeFn) -> None:
        self._nodes[name] = fn

    def add_edge(self, source: str, target: str) -> None:
        self._edges.setdefault(source, []).append(target)

    def add_conditional_edges(
        self,
        source: str,
        router: RouteFn,
        mapping: dict[str, str],
    ) -> None:
        self._conditional_edges[source] = (router, mapping)

    def compile(self) -> CompiledGraph:
        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            conditional_edges=self._conditional_edges,
        )
