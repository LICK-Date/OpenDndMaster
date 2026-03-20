from __future__ import annotations

from .state import GMState


SYSTEM_PROMPT = """你是一名文字冒险游戏主持人。你必须严格遵守以下要求：
1. 使用简体中文输出。
2. 只能返回一个 JSON 对象，不允许返回 Markdown、标题、解释、代码块或额外文本。
3. JSON 必须且只能包含以下五个字符串字段：scene、npc_reaction、resolution、consequence、new_situation。
4. 叙事必须服从世界记忆与本回合状态，不能杜撰与状态冲突的事实。
5. 不代替玩家说话，不替玩家做决定，不给编号选项列表。
6. 不直接暴露隐藏名声数值，只通过世界反馈体现。
7. 每个字段都必须是完整自然语言段落，不能为空字符串。
8. 避免使用“系统”“模块”“判定为某类行动”“写回记忆”“更新数值”这类出戏的程序化措辞，要像真正的主持人直接描写世界。"""


OUTPUT_SCHEMA_HINT = """输出示例：
{
  \"scene\": \"...\",
  \"npc_reaction\": \"...\",
  \"resolution\": \"...\",
  \"consequence\": \"...\",
  \"new_situation\": \"...\"
}"""


def build_narrative_messages(state: GMState) -> list[dict[str, str]]:
    memory = state["memory"]
    world = memory["world"]
    player = memory["player_profile"]
    target_npc = memory["npc_records"].get(state.get("target_npc_id", ""), {})
    recent_events = "\n".join(f"- {item}" for item in world.get("recent_events", [])[-5:]) or "- 无"
    npc_summary = "无明确目标 NPC"
    if target_npc:
        npc_summary = (
            f"姓名：{target_npc.get('name', '未知')}\n"
            f"职业：{target_npc.get('profession', '未知')}\n"
            f"当前状态：{target_npc.get('current_status', '未知')}\n"
            f"对玩家关系：{target_npc.get('relationship_to_player', '未知')}\n"
            f"好感度：{target_npc.get('favorability', 0)}"
        )

    user_prompt = f"""请基于以下状态生成本回合叙事 JSON。

{OUTPUT_SCHEMA_HINT}

世界信息：
- 世界名：{world.get('world_name', 'Unknown')}
- 当前城市：{world.get('current_city', 'Unknown')}
- 世界基调：{world.get('tone', 'Unknown')}

玩家信息：
- 玩家名：{player.get('name', 'Unknown')}
- 当前位置：{player.get('status', {}).get('location', 'Unknown')}
- 当前行动：{state['player_input']}
- 意图总结：{state['intent_summary']}

目标 NPC：
{npc_summary}

局势结果摘要：
- 是否需要判定：{state.get('needs_roll', False)}
- 结果摘要：{state['roll']['summary']}

后续影响摘要：
{chr(10).join(f'- {item}' for item in state['consequences'])}

最近事件：
{recent_events}

记住：只能输出一个 JSON 对象，不能输出任何额外说明；语气要像主持人自然叙述世界，不要提到“系统”或“分类”。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
