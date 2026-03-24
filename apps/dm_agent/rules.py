from __future__ import annotations

from .state import ActionType, RollResult


ACTION_KEYWORDS: list[tuple[ActionType, list[str]]] = [
    ("threaten", ["威胁", "恐吓", "逼迫", "勒索", "恫吓"]),
    ("social", ["请求", "说服", "命令", "交涉", "商量", "劝说", "求助"]),
    ("strength", ["推门", "撞开", "扛起", "搬开", "砸开", "扭打", "强行"]),
    ("dexterity", ["潜行", "跳跃", "攀爬", "闪避", "奔跑", "躲开", "溜进"]),
    ("intelligence", ["调查", "分析", "解谜", "研究", "阅读", "推理", "检查"]),
    ("talent", ["演奏", "制作", "驾驶", "撬锁", "操作器械", "伪装", "雕刻"]),
]

ROLL_EXEMPT_MARKERS = [
    "观察风景",
    "整理背包",
    "休息",
    "看看周围",
    "闲聊",
    "亲密互动",
    "情色",
]

UNCERTAIN_MARKERS = [
    "尝试",
    "潜行",
    "说服",
    "威胁",
    "调查",
    "撬锁",
    "撞开",
    "命令",
    "偷偷",
]

STAKE_MARKERS = [
    "守卫",
    "商人",
    "贵族",
    "雇佣兵",
    "证据",
    "线索",
    "门锁",
    "障碍",
    "巡逻",
]

SHOWWORTHY_MARKERS = [
    "关键",
    "重要",
    "当场",
    "立刻",
    "公开",
    "冒险",
    "危险",
]


def _coerce_score(value: object, fallback: int = 10) -> int:
    if value in {None, "", "??"}:
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def classify_action(player_input: str) -> tuple[ActionType, str]:
    for action_type, keywords in ACTION_KEYWORDS:
        if any(keyword in player_input for keyword in keywords):
            summary = f"玩家的意图更接近 {action_type} 行动：{player_input}"
            return action_type, summary
    return "narrative", f"玩家本回合以叙事推进为主：{player_input}"


def find_target_npc(
    player_input: str,
    npc_records: dict[str, dict],
) -> tuple[str, str]:
    for npc_id, payload in npc_records.items():
        name = payload.get("name", npc_id)
        if name and name in player_input:
            return npc_id, name
    if npc_records:
        first_id = next(iter(npc_records.keys()))
        first_name = npc_records[first_id].get("name", first_id)
        return first_id, first_name
    return "", ""


def should_roll(player_input: str, action_type: ActionType) -> tuple[bool, str]:
    if any(marker in player_input for marker in ROLL_EXEMPT_MARKERS):
        return False, "该行动属于明确可直叙的场景，不需要掷骰。"
    if action_type == "narrative":
        return False, "当前输入更像普通叙事推进，未命中高风险动作。"

    uncertain = any(marker in player_input for marker in UNCERTAIN_MARKERS) or action_type != "narrative"
    has_stakes = any(marker in player_input for marker in STAKE_MARKERS)
    showworthy = any(marker in player_input for marker in SHOWWORTHY_MARKERS) or action_type in {
        "social",
        "threaten",
        "strength",
        "dexterity",
        "intelligence",
        "talent",
    }

    if uncertain and has_stakes and showworthy:
        return True, "该行动同时满足不确定、可能改变局势、值得单独表现三项条件。"

    if uncertain and showworthy and action_type in {"social", "threaten"}:
        return True, "该行动属于高影响互动，先按需要独立判定处理。"

    return False, "当前风险或后果不够明确，暂不单独掷骰。"


def calculate_threshold(
    player_profile: dict,
    action_type: ActionType,
    player_input: str,
    npc_records: dict[str, dict],
    target_npc_id: str,
) -> tuple[int, str]:
    attributes = player_profile["attributes"]
    reputation = player_profile["hidden_reputation"]
    target_npc = npc_records.get(target_npc_id, {}) if target_npc_id else {}

    if action_type == "social":
        threshold = (
            _coerce_score(attributes.get("charisma"))
            + int(reputation["goodwill"])
            + int(reputation["heroic"])
        )
        resistance = _coerce_score(target_npc.get("social_resistance"), fallback=10)
        threshold += 10 - resistance
        threshold += max(-2, min(2, _coerce_score(target_npc.get("favorability"), fallback=0) // 2))
        return max(2, min(20, threshold)), "charisma"

    if action_type == "threaten":
        threshold = (
            _coerce_score(attributes.get("constitution"))
            + int(reputation["notoriety"])
            - int(reputation["goodwill"])
        )
        target_constitution = _coerce_score(target_npc.get("attributes", {}).get("constitution"), fallback=10)
        threshold += 10 - target_constitution
        return max(2, min(20, threshold)), "constitution"

    attribute_map = {
        "strength": "strength",
        "dexterity": "dexterity",
        "intelligence": "intelligence",
        "talent": "talent",
        "narrative": "",
    }
    attribute = attribute_map[action_type]
    if not attribute:
        return 0, ""
    return max(2, min(20, _coerce_score(attributes.get(attribute)))), attribute


def infer_reputation_deltas(
    player_input: str,
    action_type: ActionType,
    roll_result: RollResult,
) -> tuple[int, int, int]:
    goodwill_markers = ["帮助", "救助", "守信", "庇护", "道歉", "扶起", "保护"]
    notoriety_markers = ["抢劫", "诈骗", "背叛", "勒索", "威胁弱者", "敲诈"]
    heroic_markers = ["挺身而出", "挡在前面", "见义勇为", "冒险救人", "护住"]

    notoriety_delta = 0
    goodwill_delta = 0
    heroic_delta = 0

    if any(marker in player_input for marker in goodwill_markers):
        goodwill_delta += 1
    if any(marker in player_input for marker in notoriety_markers):
        notoriety_delta += 1
    if any(marker in player_input for marker in heroic_markers):
        heroic_delta += 1

    if action_type == "threaten" and roll_result in {"success", "partial", "failure"}:
        notoriety_delta += 1
    if action_type == "social" and roll_result == "success":
        goodwill_delta += 1

    return notoriety_delta, goodwill_delta, heroic_delta
