from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .state import MemorySnapshot


PLAYER_ATTRIBUTE_KEYS = (
    "strength",
    "dexterity",
    "intelligence",
    "charisma",
    "constitution",
    "talent",
)

ATTRIBUTE_DISPLAY_NAMES = {
    "strength": "力量",
    "dexterity": "敏捷",
    "intelligence": "智力",
    "charisma": "魅力",
    "constitution": "体质",
    "talent": "天赋",
}

DEFAULT_WORLD = {
    "world_name": "未命名世界",
    "tone": "等待玩家定义的冒险基调",
    "current_city": "尚未设定",
    "factions": [],
    "recent_events": [],
}

DEFAULT_PLAYER_PROFILE = {
    "name": "未命名",
    "background": "角色尚未创建，请先为角色命名并填写六维属性。",
    "attributes": {
        "strength": None,
        "dexterity": None,
        "intelligence": None,
        "charisma": None,
        "constitution": None,
        "talent": None,
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
    "equipment": [],
    "history": [],
    "relationships": [],
    "status": {
        "location": "世界入口",
        "injury": "none",
        "wanted": False,
    },
}

DEFAULT_NPC_INDEX: list[dict[str, Any]] = []

INITIAL_WORLD_PROMPT = (
    "这是一片尚未成形的世界，故事会从你的选择开始。"
    "在继续之前，你希望在什么样的世界里冒险？"
    "可以告诉我时代、氛围、地点，或者你最想体验的元素。"
)


def _build_default_world(world_id: str) -> dict[str, Any]:
    world = dict(DEFAULT_WORLD)
    world["world_name"] = world_id
    return world


def _build_default_player_profile() -> dict[str, Any]:
    return deepcopy(DEFAULT_PLAYER_PROFILE)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_opening_transcript() -> list[dict[str, str]]:
    return [
        {
            "kind": "gm",
            "speaker": "Dungeon Master",
            "content": INITIAL_WORLD_PROMPT,
        }
    ]


def _format_player_name(name: Any) -> str:
    trimmed = str(name or "").strip()
    return trimmed or "未命名"


def _format_attribute_value(value: Any) -> str:
    if value in {None, "", "??"}:
        return "??"
    return str(value)


def _render_player_markdown(profile: dict[str, Any]) -> str:
    attributes = profile["attributes"]
    reputation = profile["hidden_reputation"]
    status = profile["status"]
    lines = [
        f"# {_format_player_name(profile.get('name'))}",
        "",
        f"背景：{profile.get('background') or '暂无背景信息。'}",
        "",
        "## 属性",
        f"- 力量：{_format_attribute_value(attributes.get('strength'))}",
        f"- 敏捷：{_format_attribute_value(attributes.get('dexterity'))}",
        f"- 智力：{_format_attribute_value(attributes.get('intelligence'))}",
        f"- 魅力：{_format_attribute_value(attributes.get('charisma'))}",
        f"- 体质：{_format_attribute_value(attributes.get('constitution'))}",
        f"- 天赋：{_format_attribute_value(attributes.get('talent'))}",
        "",
        "## 隐藏声望",
        f"- 恶名：{reputation['notoriety']}",
        f"- 善意：{reputation['goodwill']}",
        f"- 英勇：{reputation['heroic']}",
        "",
        "## 当前状态",
        f"- 位置：{status['location']}",
        f"- 伤势：{status['injury']}",
        f"- 通缉：{status['wanted']}",
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
        "session_transcript": world_dir / "session_transcript.json",
    }


def ensure_world_exists(workspace_root: str, world_id: str) -> None:
    paths = get_world_paths(workspace_root, world_id)
    paths["npc_dir"].mkdir(parents=True, exist_ok=True)
    default_player_profile = _build_default_player_profile()

    if not paths["world_json"].exists():
        _write_json(paths["world_json"], _build_default_world(world_id))
    if not paths["player_profile"].exists():
        _write_json(paths["player_profile"], default_player_profile)
    if not paths["npc_list"].exists():
        _write_json(paths["npc_list"], DEFAULT_NPC_INDEX)
    if not paths["player_md"].exists():
        paths["player_md"].write_text(
            _render_player_markdown(default_player_profile),
            encoding="utf-8",
        )

    if not paths["session_log"].exists():
        paths["session_log"].write_text("", encoding="utf-8")
    if not paths["session_transcript"].exists():
        paths["session_transcript"].write_text(
            json.dumps(_build_opening_transcript(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _normalize_player_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile.setdefault("name", "未命名")
    profile.setdefault("background", "角色尚未创建，请先为角色命名并填写六维属性。")
    profile.setdefault("attributes", {})
    profile.setdefault("hidden_reputation", {})
    profile.setdefault("hidden_reputation_meta", {})
    profile.setdefault("equipment", [])
    profile.setdefault("history", [])
    profile.setdefault("relationships", [])
    profile.setdefault("status", {})

    for key in PLAYER_ATTRIBUTE_KEYS:
        profile["attributes"].setdefault(key, None)

    profile["hidden_reputation"].setdefault("notoriety", 0)
    profile["hidden_reputation"].setdefault("goodwill", 0)
    profile["hidden_reputation"].setdefault("heroic", 0)
    profile["hidden_reputation_meta"].setdefault("applied_goodwill_tiers", 0)
    profile["hidden_reputation_meta"].setdefault("applied_notoriety_tiers", 0)

    profile["status"].setdefault("location", "世界入口")
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
        _read_json(paths["player_profile"], _build_default_player_profile())
    )
    npc_index = _read_json(paths["npc_list"], DEFAULT_NPC_INDEX)
    player_markdown = paths["player_md"].read_text(encoding="utf-8-sig")
    snapshot: MemorySnapshot = {
        "world": _read_json(paths["world_json"], _build_default_world(world_id)),
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
    player_markdown = _render_player_markdown(snapshot["player_profile"])
    _write_json(paths["world_json"], snapshot["world"])
    _write_json(paths["player_profile"], snapshot["player_profile"])
    _write_json(paths["npc_list"], snapshot["npc_index"])
    for npc_id, payload in snapshot["npc_records"].items():
        _write_json(paths["npc_dir"] / f"{npc_id}.json", payload)
    paths["player_md"].write_text(player_markdown, encoding="utf-8")
    snapshot["player_markdown"] = player_markdown


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


def load_session_transcript(workspace_root: str, world_id: str) -> list[dict[str, str]]:
    ensure_world_exists(workspace_root, world_id)
    paths = get_world_paths(workspace_root, world_id)
    payload = _read_json(paths["session_transcript"], _build_opening_transcript())
    if not isinstance(payload, list):
        return []
    transcript: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "system").strip() or "system"
        speaker = str(item.get("speaker") or "System").strip() or "System"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        transcript.append({
            "kind": kind,
            "speaker": speaker,
            "content": content,
        })
    return transcript[-80:]


def append_session_transcript(workspace_root: str, world_id: str, entries: list[dict[str, str]]) -> None:
    paths = get_world_paths(workspace_root, world_id)
    transcript = load_session_transcript(workspace_root, world_id)
    for item in entries:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "system").strip() or "system"
        speaker = str(item.get("speaker") or "System").strip() or "System"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        transcript.append({
            "kind": kind,
            "speaker": speaker,
            "content": content,
        })
    paths["session_transcript"].write_text(
        json.dumps(transcript[-80:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
