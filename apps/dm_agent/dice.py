from __future__ import annotations

import random
from typing import Literal


RollResult = Literal["success", "partial", "failure"]


def roll_d20(rng: random.Random | None = None) -> int:
    roller = rng or random
    return roller.randint(1, 20)


def resolve_threshold_roll(die: int, threshold: int) -> RollResult:
    if die < threshold:
        return "success"
    if die == threshold:
        return "partial"
    return "failure"
