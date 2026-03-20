from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state import MemorySnapshot


DEFAULT_WORLD = {
    "world_name": "Riverside Demo",
    "tone": "grounded fantasy",
    "current_city": "Riverside",
    "factions": ["Town Watch", "River Traders"],
    "recent_events": [],
}

DEFAULT_PLAYER_PROFILE = {
    "name": "Traveler",
    "background": "A wandering adventurer new to town.",
    "attributes": {
        "strength": 16,
        "dexterity": 15,
        "intelligence": 14,
        "charisma": 15,
        "constitution": 14,
        "talent": 13,
    },
    "hidden_reputation": {
        "notoriety": 0,
        "goodwill": 0,
        "heroic": 0,
    },
    "hidden_reputation_meta": {
        "applied_goodwill_tiers": 0,
        "applied_notoriety_tiers": 0,
    },
    "equipment": ["travel cloak", "coin pouch"],
    "history": [],
    "relationships": [],
    "status": {
        "location": "Riverside Inn",
        "injury": "none",
        "wanted": False,
    },
}

DEFAULT_NPC_INDEX = [
    {
        "npc_id": "innkeeper_mara",
        "name": "Mara",
        "file_path": "world_Info/npcs/innkeeper_mara.json",
        "current_status": "alive",
        "city": "Riverside",
        "relationship_summary": "Polite but cautious toward newcomers.",
    }
]

DEFAULT_NPC = {
    "id": "innkeeper_mara",
    "name": "Mara",
    "age": 38,
    "gender": "female",
    "profession": "innkeeper",
    "appearance": "Keeps a clean apron and watches the room carefully.",
    "personality": "Measured, practical, and hard to fool.",
    "background": "Runs the Riverside Inn and hears most town rumors.",
    "alignment": "neutral",
    "goal": "Keep the inn safe and profitable.",
    "secret": "Passes useful information to the Town Watch.",
    "relationship_to_player": "No strong opinion yet.",
    "current_status": "alive",
    "current_city": "Riverside",
    "favorability": 0,
    "social_resistance": 12,
    "attributes": {
        "constitution": 11,
        "willpower": 12,
        "strength": 10,
    },
}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _render_player_markdown(profile: dict[str, Any]) -> str:
    attributes = profile["attributes"]
    reputation = profile["hidden_reputation"]
    status = profile["status"]
    lines = [
        f"# {profile['name']}",
        "",
        f"Background: {profile['background']}",
        "",
        "## Attributes",
        f"- Strength: {attributes['strength']}",
        f"- Dexterity: {attributes['dexterity']}",
        f"- Intelligence: {attributes['intelligence']}",
        f"- Charisma: {attributes['charisma']}",
        f"- Constitution: {attributes['constitution']}",
        f"- Talent: {attributes['talent']}",
        "",
        "## Hidden Reputation",
        f"- Notoriety: {reputation['notoriety']}",
        f"- Goodwill: {reputation['goodwill']}",
        f"- Heroic: {reputation['heroic']}",
        "",
        "## Status",
        f"- Location: {status['location']}",
        f"- Injury: {status['injury']}",
        f"- Wanted: {status['wanted']}",
    ]
    return "\n".join(lines) + "\n"


def get_world_paths(workspace_root: str, world_id: str) -> dict[str, Path]:
    root = Path(workspace_root)
    world_dir = root / "workspace_data" / "worlds" / world_id
    world_info = world_dir / "world_Info"
    npc_dir = world_info / "npcs"
    return {
        "world_dir": world_dir,
        "world_info": world_info,
        "npc_dir": npc_dir,
        "world_json": world_info / "world.json",
        "player_profile": world_info / "player_profile.json",
        "player_md": world_info / "player.md",
        "npc_list": world_info / "NPC_List.json",
        "session_log": world_dir / "session_log.txt",
    }


def ensure_world_exists(workspace_root: str, world_id: str) -> None:
    paths = get_world_paths(workspace_root, world_id)
    paths["npc_dir"].mkdir(parents=True, exist_ok=True)

    if not paths["world_json"].exists():
        _write_json(paths["world_json"], DEFAULT_WORLD)
    if not paths["player_profile"].exists():
        _write_json(paths["player_profile"], DEFAULT_PLAYER_PROFILE)
    if not paths["npc_list"].exists():
        _write_json(paths["npc_list"], DEFAULT_NPC_INDEX)
    if not paths["player_md"].exists():
        paths["player_md"].write_text(
            _render_player_markdown(DEFAULT_PLAYER_PROFILE),
            encoding="utf-8",
        )

    default_npc_path = paths["npc_dir"] / "innkeeper_mara.json"
    if not default_npc_path.exists():
        _write_json(default_npc_path, DEFAULT_NPC)

    if not paths["session_log"].exists():
        paths["session_log"].write_text("", encoding="utf-8")


def _normalize_player_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile.setdefault("attributes", {})
    profile.setdefault("hidden_reputation", {})
    profile.setdefault("hidden_reputation_meta", {})
    profile.setdefault("equipment", [])
    profile.setdefault("history", [])
    profile.setdefault("relationships", [])
    profile.setdefault("status", {})

    profile["attributes"].setdefault("strength", 10)
    profile["attributes"].setdefault("dexterity", 10)
    profile["attributes"].setdefault("intelligence", 10)
    profile["attributes"].setdefault("charisma", 10)
    profile["attributes"].setdefault("constitution", 10)
    profile["attributes"].setdefault("talent", 10)

    profile["hidden_reputation"].setdefault("notoriety", 0)
    profile["hidden_reputation"].setdefault("goodwill", 0)
    profile["hidden_reputation"].setdefault("heroic", 0)
    profile["hidden_reputation_meta"].setdefault("applied_goodwill_tiers", 0)
    profile["hidden_reputation_meta"].setdefault("applied_notoriety_tiers", 0)

    profile["status"].setdefault("location", "Unknown")
    profile["status"].setdefault("injury", "none")
    profile["status"].setdefault("wanted", False)
    return profile


def _normalize_npc_record(profile: dict[str, Any]) -> dict[str, Any]:
    profile.setdefault("id", "unknown_npc")
    profile.setdefault("name", profile["id"])
    profile.setdefault("current_status", "alive")
    profile.setdefault("current_city", "Unknown")
    profile.setdefault("favorability", 0)
    profile.setdefault("relationship_to_player", "No strong opinion yet.")
    profile.setdefault("social_resistance", 10)
    profile.setdefault("attributes", {})
    profile["attributes"].setdefault("constitution", 10)
    profile["attributes"].setdefault("willpower", 10)
    profile["attributes"].setdefault("strength", 10)
    return profile


def _load_npc_records(paths: dict[str, Path], npc_index: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    npc_records: dict[str, dict[str, Any]] = {}
    for entry in npc_index:
        npc_id = entry.get("npc_id") or entry.get("id")
        if not npc_id:
            continue
        file_path = entry.get("file_path")
        if file_path:
            candidate = paths["world_dir"] / file_path
        else:
            candidate = paths["npc_dir"] / f"{npc_id}.json"
        payload = _read_json(candidate, {"id": npc_id, "name": entry.get("name", npc_id)})
        npc_records[npc_id] = _normalize_npc_record(payload)
    return npc_records


def load_world_memory(workspace_root: str, world_id: str) -> MemorySnapshot:
    ensure_world_exists(workspace_root, world_id)
    paths = get_world_paths(workspace_root, world_id)
    player_profile = _normalize_player_profile(
        _read_json(paths["player_profile"], DEFAULT_PLAYER_PROFILE)
    )
    npc_index = _read_json(paths["npc_list"], DEFAULT_NPC_INDEX)
    player_markdown = paths["player_md"].read_text(encoding="utf-8")
    snapshot: MemorySnapshot = {
        "world": _read_json(paths["world_json"], DEFAULT_WORLD),
        "player_profile": player_profile,
        "player_markdown": player_markdown,
        "npc_index": npc_index,
        "npc_records": _load_npc_records(paths, npc_index),
    }
    return snapshot


def save_world_memory(
    workspace_root: str,
    world_id: str,
    snapshot: MemorySnapshot,
) -> None:
    paths = get_world_paths(workspace_root, world_id)
    _write_json(paths["world_json"], snapshot["world"])
    _write_json(paths["player_profile"], snapshot["player_profile"])
    _write_json(paths["npc_list"], snapshot["npc_index"])
    for npc_id, payload in snapshot["npc_records"].items():
        _write_json(paths["npc_dir"] / f"{npc_id}.json", payload)
    paths["player_md"].write_text(
        _render_player_markdown(snapshot["player_profile"]),
        encoding="utf-8",
    )


def append_session_log(workspace_root: str, world_id: str, line: str) -> None:
    paths = get_world_paths(workspace_root, world_id)
    with paths["session_log"].open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def apply_reputation_change(
    player_profile: dict[str, Any],
    notoriety_delta: int = 0,
    goodwill_delta: int = 0,
    heroic_delta: int = 0,
) -> None:
    reputation = player_profile["hidden_reputation"]
    meta = player_profile.setdefault("hidden_reputation_meta", {})
    meta.setdefault("applied_goodwill_tiers", 0)
    meta.setdefault("applied_notoriety_tiers", 0)

    reputation["notoriety"] = max(0, reputation["notoriety"] + notoriety_delta)
    reputation["goodwill"] = max(0, reputation["goodwill"] + goodwill_delta)
    reputation["heroic"] = max(0, reputation["heroic"] + heroic_delta)

    current_goodwill_tiers = reputation["goodwill"] // 2
    current_notoriety_tiers = reputation["notoriety"] // 4

    if current_goodwill_tiers < meta["applied_goodwill_tiers"]:
        meta["applied_goodwill_tiers"] = current_goodwill_tiers
    if current_notoriety_tiers < meta["applied_notoriety_tiers"]:
        meta["applied_notoriety_tiers"] = current_notoriety_tiers

    new_goodwill_tiers = current_goodwill_tiers - meta["applied_goodwill_tiers"]
    if new_goodwill_tiers > 0:
        reputation["notoriety"] = max(0, reputation["notoriety"] - new_goodwill_tiers)
        reputation["heroic"] += new_goodwill_tiers
        meta["applied_goodwill_tiers"] += new_goodwill_tiers

    current_notoriety_tiers = reputation["notoriety"] // 4
    if current_notoriety_tiers < meta["applied_notoriety_tiers"]:
        meta["applied_notoriety_tiers"] = current_notoriety_tiers

    new_notoriety_tiers = current_notoriety_tiers - meta["applied_notoriety_tiers"]
    if new_notoriety_tiers > 0:
        reputation["goodwill"] = max(0, reputation["goodwill"] - new_notoriety_tiers)
        reputation["heroic"] = max(0, reputation["heroic"] - new_notoriety_tiers)
        meta["applied_notoriety_tiers"] += new_notoriety_tiers
