from __future__ import annotations

import json
import re
from typing import Any

from .dice import resolve_threshold_roll, roll_d20
from .llm_client import LLMClientError, OpenAICompatibleClient
from .memory_store import (
    append_session_log,
    apply_reputation_change,
    load_world_memory,
    save_world_memory,
)
from .prompts import build_narrative_messages
from .rules import (
    calculate_threshold,
    classify_action,
    find_target_npc,
    infer_reputation_deltas,
    should_roll,
)
from .state import GMState, RollOutcome


MODEL_SERVICE_UNAVAILABLE_MESSAGE = "当前模型服务不可用"

JSON_SECTION_KEYS = [
    ("scene", "场景描述"),
    ("npc_reaction", "NPC行为与反应"),
    ("resolution", "判定过程与结果"),
    ("consequence", "后果"),
    ("new_situation", "新局势与引导"),
]

ATTRIBUTE_LABEL_TO_KEY = {
    "力量": "strength",
    "敏捷": "dexterity",
    "智力": "intelligence",
    "魅力": "charisma",
    "体质": "constitution",
    "天赋": "talent",
}

ATTRIBUTE_KEY_TO_LABEL = {
    "strength": "力量",
    "dexterity": "敏捷",
    "intelligence": "智力",
    "charisma": "魅力",
    "constitution": "体质",
    "talent": "天赋",
}

PLAYER_NAME_PATTERNS = [
    re.compile(r"(?:我叫|我的名字叫|我的名字是|名字叫|名叫|请叫我)(?P<name>[^\s，。！？,.!?:：]{1,24})"),
]

ATTRIBUTE_VALUE_PATTERN = re.compile(
    r"(?P<label>力量|敏捷|智力|魅力|体质|天赋)\s*(?:[:：=]|是|为)?\s*(?P<value>\d{1,2})"
)


def load_memory_node(state: GMState) -> dict[str, Any]:
    workspace_root = state["workspace_root"]
    world_id = state["world_id"]
    memory = load_world_memory(workspace_root, world_id)
    return {"memory": memory}


def analyze_intent_node(state: GMState) -> dict[str, Any]:
    action_type, intent_summary = classify_action(state["player_input"])
    return {
        "action_type": action_type,
        "intent_summary": intent_summary,
    }


def should_roll_node(state: GMState) -> dict[str, Any]:
    player_profile = state["memory"]["player_profile"]
    npc_records = state["memory"]["npc_records"]
    target_npc_id, target_npc_name = find_target_npc(
        state["player_input"],
        npc_records,
    )
    needs_roll, reason = should_roll(
        player_input=state["player_input"],
        action_type=state["action_type"],
    )
    threshold, attribute = calculate_threshold(
        player_profile=player_profile,
        action_type=state["action_type"],
        player_input=state["player_input"],
        npc_records=npc_records,
        target_npc_id=target_npc_id,
    )
    if not needs_roll:
        threshold = 0
        attribute = ""

    intent_summary = f"{state['intent_summary']} 判定依据：{reason}"
    if target_npc_name:
        intent_summary += f" 目标对象：{target_npc_name}。"

    return {
        "needs_roll": needs_roll,
        "roll_attribute": attribute,
        "roll_threshold": threshold,
        "target_npc_id": target_npc_id,
        "target_npc_name": target_npc_name,
        "intent_summary": intent_summary,
    }


def resolve_action_node(state: GMState) -> dict[str, Any]:
    if not state["needs_roll"]:
        roll: RollOutcome = {
            "attribute": "",
            "threshold": 0,
            "result": "not_required",
            "summary": "眼前的局势还算平稳，你的举动顺着情势自然推进，没有被迫卷入一场非成即败的较量。",
        }
        return {"roll": roll}

    die = roll_d20()
    result = resolve_threshold_roll(die, state["roll_threshold"])
    target_npc_name = state.get("target_npc_name", "")
    if result == "success":
        if target_npc_name:
            summary = f"关键时刻，你拿捏住了分寸，{target_npc_name}面前那点阻力终于松开，事情朝你想要的方向动了。"
        else:
            summary = "关键时刻，你拿捏住了分寸，眼前的阻力终于松开，事情朝你想要的方向动了。"
    elif result == "partial":
        if target_npc_name:
            summary = f"你勉强撬动了{target_npc_name}面前的僵局，事情没有彻底失手，却也留下了明显的代价。"
        else:
            summary = "你勉强撬动了眼前的僵局，事情没有彻底失手，却也留下了明显的代价。"
    else:
        if target_npc_name:
            summary = f"你的分寸终究还是差了一线，{target_npc_name}没有被你带着走，局势反而朝更棘手的方向偏去。"
        else:
            summary = "你的分寸终究还是差了一线，局势没有顺着你的心意发展，反而朝更棘手的方向偏去。"
    roll: RollOutcome = {
        "die": die,
        "threshold": state["roll_threshold"],
        "attribute": state["roll_attribute"],
        "result": result,
        "summary": summary,
    }
    return {"roll": roll}


def _extract_player_name(player_input: str) -> str:
    for pattern in PLAYER_NAME_PATTERNS:
        match = pattern.search(player_input)
        if not match:
            continue
        candidate = match.group("name").strip('"“”‘’「」『』')
        if candidate:
            return candidate
    return ""


def _extract_attribute_updates(player_input: str) -> dict[str, int]:
    updates: dict[str, int] = {}
    for match in ATTRIBUTE_VALUE_PATTERN.finditer(player_input):
        label = match.group("label")
        try:
            value = int(match.group("value"))
        except ValueError:
            continue
        if not 1 <= value <= 30:
            continue
        key = ATTRIBUTE_LABEL_TO_KEY[label]
        updates[key] = value
    return updates


def _refresh_player_setup_background(player_profile: dict[str, Any]) -> None:
    attributes = player_profile.get("attributes", {})
    complete = all(attributes.get(key) not in {None, "", "??"} for key in ATTRIBUTE_KEY_TO_LABEL)
    current_background = str(player_profile.get("background") or "").strip()
    if complete:
        if not current_background or "角色尚未创建" in current_background or "角色正在建立中" in current_background:
            player_profile["background"] = "角色已完成基础建卡，可以继续补充背景与故事。"
        return
    if not current_background or "角色尚未创建" in current_background:
        player_profile["background"] = "角色正在建立中，请继续填写名字和六维属性。"


def _apply_player_profile_updates(player_profile: dict[str, Any], player_input: str, consequences: list[str]) -> None:
    updated_attributes: list[str] = []
    new_name = _extract_player_name(player_input)
    current_name = str(player_profile.get("name") or "").strip() or "未命名"
    if new_name and new_name != current_name:
        player_profile["name"] = new_name
        consequences.append(f"你的角色正式有了名字，从这一刻起，你将以“{new_name}”之名被这个世界记住。")

    attribute_updates = _extract_attribute_updates(player_input)
    if attribute_updates:
        attributes = player_profile.setdefault("attributes", {})
        for key, value in attribute_updates.items():
            if attributes.get(key) == value:
                continue
            attributes[key] = value
            updated_attributes.append(f"{ATTRIBUTE_KEY_TO_LABEL[key]} {value}")

    if updated_attributes:
        consequences.append(f"你的角色卡逐渐清晰起来：{'、'.join(updated_attributes)}。")

    if new_name or updated_attributes:
        _refresh_player_setup_background(player_profile)


def _apply_npc_impact(state: GMState, consequences: list[str]) -> None:
    target_npc_id = state.get("target_npc_id", "")
    if not target_npc_id:
        return

    npc_records = state["memory"]["npc_records"]
    target_npc = npc_records.get(target_npc_id)
    if not target_npc:
        return

    roll_result = state["roll"]["result"]
    action_type = state["action_type"]
    npc_name = target_npc.get("name", target_npc_id)

    favorability_delta = 0
    if action_type == "social":
        if roll_result == "success":
            favorability_delta = 1
        elif roll_result == "failure":
            favorability_delta = -1
    elif action_type == "threaten":
        if roll_result == "success":
            favorability_delta = -2
        elif roll_result == "partial":
            favorability_delta = -1
        elif roll_result == "failure":
            favorability_delta = -1
            target_npc["current_status"] = "hostile"

    if favorability_delta:
        target_npc["favorability"] = int(target_npc.get("favorability", 0)) + favorability_delta
        if target_npc["favorability"] >= 2:
            target_npc["relationship_to_player"] = "对玩家明显更信任。"
            consequences.append(f"{npc_name}看你的眼神柔和了些，语气里也多出了一点愿意搭话的余地。")
        elif target_npc["favorability"] <= -2:
            target_npc["relationship_to_player"] = "对玩家保持明显戒备。"
            consequences.append(f"{npc_name}的神情明显冷了下来，连呼吸间都透着掩不住的戒备。")
        elif favorability_delta > 0:
            consequences.append(f"{npc_name}对你的态度松动了一点，至少不再把你当成无关紧要的陌生人。")
        else:
            consequences.append(f"{npc_name}对你的警惕悄悄抬高了一线，话里话外都变得更谨慎了。")


def apply_consequences_node(state: GMState) -> dict[str, Any]:
    memory = state["memory"]
    world = memory["world"]
    player_profile = memory["player_profile"]
    consequences: list[str] = []
    player_input = state["player_input"]
    roll = state["roll"]

    if roll["result"] == "success":
        consequences.append("局势明显朝你希望的方向偏了一步，眼前的门缝被你推开了。")
    elif roll["result"] == "partial":
        consequences.append("事情虽成，却带着一点不轻不重的代价，像鞋底粘住的泥，暂时甩不干净。")
    elif roll["result"] == "failure":
        consequences.append("事情没有按你的设想发展，空气里随即多了几分不妙的意味。")
    else:
        consequences.append("这一回合没有激起真正的风浪，事情只是顺着你的举动往前滑去。")

    _apply_player_profile_updates(player_profile, player_input, consequences)

    notoriety_delta, goodwill_delta, heroic_delta = infer_reputation_deltas(
        player_input=player_input,
        action_type=state["action_type"],
        roll_result=roll["result"],
    )
    if notoriety_delta or goodwill_delta or heroic_delta:
        apply_reputation_change(
            player_profile,
            notoriety_delta=notoriety_delta,
            goodwill_delta=goodwill_delta,
            heroic_delta=heroic_delta,
        )
        consequences.append("你这一番举动会悄悄改变旁人日后看待你的方式，只是眼下未必人人都说破。")

    _apply_npc_impact(state, consequences)

    history_line = (
        f"Turn action: {player_input} | action_type: {state['action_type']} | "
        f"outcome: {roll['result']}"
    )
    player_profile["history"].append(history_line)
    player_profile["history"] = player_profile["history"][-20:]
    world["recent_events"].append(history_line)
    world["recent_events"] = world["recent_events"][-10:]

    save_world_memory(state["workspace_root"], state["world_id"], memory)
    append_session_log(state["workspace_root"], state["world_id"], history_line)

    return {"consequences": consequences}


def _render_template_narrative(state: GMState) -> tuple[list[str], str]:
    memory = state["memory"]
    world = memory["world"]
    player_profile = memory["player_profile"]
    world_name = world.get("world_name") or state["world_id"]
    current_city = world.get("current_city") or "未知地域"
    world_tone = world.get("tone") or "未定"
    location = player_profile.get("status", {}).get("location", "未知地点")

    npc_name = state.get("target_npc_name")
    if not npc_name and memory["npc_index"]:
        npc_name = memory["npc_index"][0].get("name") or "某位旁观者"

    scene = (
        f"你正站在“{world_name}”的冒险起点，眼前地点是{location}，它属于{current_city}这一带。"
        f" 这个世界此刻还带着“{world_tone}”的雏形，而你刚刚采取的行动是“{state['player_input']}”。"
    )
    if npc_name:
        npc_reaction = (
            f"{npc_name}最先被你的举动吸引了注意力，对方没有立刻给出全部态度，"
            "而是先观察你的分寸、语气和下一步打算，再决定要把局势往哪里推。"
        )
    else:
        npc_reaction = (
            "周围暂时没有明确的关键人物站出来回应你，最先被惊动的是环境本身。"
            " 细微的声响、气氛里的停顿，以及世界对你行动的反馈，都在提醒你故事已经开始成形。"
        )
    resolution = state["roll"]["summary"]
    consequence = " ".join(state["consequences"])
    new_situation = (
        "新的局势已经展开。"
        " 你既可以顺着刚刚撬开的缺口继续深入，也可以换个方向重新定义这个世界的规则、人物与风险。"
    )
    sections = [scene, npc_reaction, resolution, consequence, new_situation]
    return sections, "\n\n".join(sections)


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMClientError("LLM did not return a JSON object")
    text = text[start:end + 1]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError("LLM returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise LLMClientError("LLM JSON root must be an object")
    return payload


def _parse_json_narrative(raw_text: str) -> tuple[list[str], str]:
    payload = _extract_json_object(raw_text)
    sections: list[str] = []
    rendered: list[str] = []
    for key, _title in JSON_SECTION_KEYS:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LLMClientError(f"LLM JSON missing non-empty field: {key}")
        body = value.strip()
        sections.append(body)
        rendered.append(body)
    extra_keys = set(payload.keys()) - {key for key, _ in JSON_SECTION_KEYS}
    if extra_keys:
        raise LLMClientError(f"LLM JSON returned unexpected fields: {sorted(extra_keys)}")
    return sections, "\n\n".join(rendered)


def _render_service_unavailable_response() -> dict[str, Any]:
    return {
        "narrative_sections": [MODEL_SERVICE_UNAVAILABLE_MESSAGE],
        "narrative_source": "service_unavailable",
        "narrative_error": MODEL_SERVICE_UNAVAILABLE_MESSAGE,
        "final_response": MODEL_SERVICE_UNAVAILABLE_MESSAGE,
    }


def render_narrative_node(state: GMState) -> dict[str, Any]:
    fallback_sections, fallback_response = _render_template_narrative(state)
    client = OpenAICompatibleClient.from_mapping(state.get('llm_config')) or OpenAICompatibleClient.from_env()
    if client is None:
        return {
            "narrative_sections": fallback_sections,
            "narrative_source": "template",
            "final_response": fallback_response,
        }

    try:
        messages = build_narrative_messages(state)
        llm_response = client.generate(messages)
        parsed_sections, parsed_response = _parse_json_narrative(llm_response)
        return {
            "narrative_sections": parsed_sections,
            "narrative_source": "llm",
            "narrative_error": "",
            "final_response": parsed_response,
        }
    except LLMClientError:
        return _render_service_unavailable_response()


