from __future__ import annotations

import json
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


JSON_SECTION_KEYS = [
    ("scene", "场景描述"),
    ("npc_reaction", "NPC行为与反应"),
    ("resolution", "判定过程与结果"),
    ("consequence", "后果"),
    ("new_situation", "新局势与引导"),
]


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
    npc_name = state.get("target_npc_name") or (
        memory["npc_index"][0]["name"] if memory["npc_index"] else "旁观者"
    )
    location = player_profile["status"]["location"]

    scene = (
        f"{world['current_city']} 的 {location} 里，空气里混着木柴、酒气与低声交谈。"
        f" 你刚刚采取的行动是“{state['player_input']}”。"
    )
    npc_reaction = (
        f"{npc_name}抬眼打量了你一下，像是在衡量你的来意和分量。"
        f" 她没有急着表态，只把注意力短暂地压在你身上，等着看你下一步会怎么走。"
    )
    resolution = state["roll"]["summary"]
    consequence = " ".join(state["consequences"])
    new_situation = (
        "局面已经出现新的缝隙与压力。"
        " 周围人的视线、环境细节以及说话停顿中暴露出的犹豫，"
        " 都在暗示后续可以继续追击、暂时收手，或转向另一条更隐蔽的路径。"
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
    except LLMClientError as exc:
        return {
            "narrative_sections": fallback_sections,
            "narrative_source": "template",
            "narrative_error": str(exc),
            "final_response": fallback_response,
        }

