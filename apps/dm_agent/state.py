from __future__ import annotations

from typing import Any, Literal, TypedDict


ActionType = Literal[
    "social",
    "threaten",
    "strength",
    "dexterity",
    "intelligence",
    "talent",
    "narrative",
]

RollResult = Literal["success", "partial", "failure", "not_required"]


class RollOutcome(TypedDict, total=False):
    die: int
    threshold: int
    attribute: str
    result: RollResult
    summary: str


class MemorySnapshot(TypedDict):
    world: dict[str, Any]
    player_profile: dict[str, Any]
    player_markdown: str
    npc_index: list[dict[str, Any]]
    npc_records: dict[str, dict[str, Any]]


class GMState(TypedDict, total=False):
    world_id: str
    workspace_root: str
    player_input: str
    memory: MemorySnapshot
    intent_summary: str
    action_type: ActionType
    needs_roll: bool
    roll_attribute: str
    roll_threshold: int
    target_npc_id: str
    target_npc_name: str
    roll: RollOutcome
    consequences: list[str]
    narrative_sections: list[str]
    final_response: str
