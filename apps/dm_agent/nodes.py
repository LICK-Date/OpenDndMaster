from __future__ import annotations

from typing import Any

from .dice import resolve_threshold_roll, roll_d20
from .memory_store import (
    append_session_log,
    apply_reputation_change,
    load_world_memory,
    save_world_memory,
)
from .rules import (
    calculate_threshold,
    classify_action,
    find_target_npc,
    infer_reputation_deltas,
    should_roll,
)
from .state import GMState, RollOutcome


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
            "summary": "该行动不同时满足“不确定、失败会改变局势、值得单独表现”三项条件，直接进行叙事结算。",
        }
        return {"roll": roll}

    die = roll_d20()
    result = resolve_threshold_roll(die, state["roll_threshold"])
    target_clause = ""
    if state.get("target_npc_name"):
        target_clause = f" 目标 NPC 为 {state['target_npc_name']}。"
    summary = (
        f"本回合触发 d20 判定。掷骰结果为 {die}，"
        f"当前行动使用属性 {state['roll_attribute']}，"
        f"最终阈值为 {state['roll_threshold']}，"
        f"结果判定为 {result}。"
        f"{target_clause}"
    )
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
        elif target_npc["favorability"] <= -2:
            target_npc["relationship_to_player"] = "对玩家保持明显戒备。"
        consequences.append(f"{npc_name} 对玩家的态度发生了变化，并已写回 NPC 记忆。")


def apply_consequences_node(state: GMState) -> dict[str, Any]:
    memory = state["memory"]
    world = memory["world"]
    player_profile = memory["player_profile"]
    consequences: list[str] = []
    player_input = state["player_input"]
    roll = state["roll"]

    if roll["result"] == "success":
        consequences.append("行动成功达成核心目的，局势朝玩家有利的方向偏移。")
    elif roll["result"] == "partial":
        consequences.append("行动勉强成功，但产生了额外代价、压力或隐患。")
    elif roll["result"] == "failure":
        consequences.append("行动失败，世界状态已经出现明确而可持续的后果。")
    else:
        consequences.append("本回合按纯叙事方式结算，没有单独掷骰。")

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
        consequences.append(
            "该行动触发了隐藏名声联动，系统已更新恶名、善名与侠名。"
        )

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


def render_narrative_node(state: GMState) -> dict[str, Any]:
    memory = state["memory"]
    world = memory["world"]
    player_profile = memory["player_profile"]
    npc_name = state.get("target_npc_name") or (
        memory["npc_index"][0]["name"] if memory["npc_index"] else "旁观者"
    )
    location = player_profile["status"]["location"]

    scene = (
        f"场景描述：{world['current_city']} 的 {location} 里，空气里混着木柴、酒气与低声交谈。"
        f" 你刚刚采取的行动是“{state['player_input']}”。"
    )
    npc_reaction = (
        f"NPC行为与反应：{npc_name} 先观察你的语气、姿态与时机，"
        f"随后根据眼前利益、风险和既有态度做出回应。"
        f" 系统将这一步归类为 {state['action_type']} 行动。"
    )
    resolution = f"判定过程与结果：{state['roll']['summary']}"
    consequence = "后果：" + " ".join(state["consequences"])
    new_situation = (
        "新局势与引导：局面已经出现新的缝隙与压力。"
        " 周围人的视线、环境细节以及说话停顿中暴露出的犹豫，"
        " 都在暗示后续可以继续追击、暂时收手，或转向另一条更隐蔽的路径。"
    )

    sections = [scene, npc_reaction, resolution, consequence, new_situation]
    final_response = "\n\n".join(sections)
    return {
        "narrative_sections": sections,
        "final_response": final_response,
    }
