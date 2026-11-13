"""頭目部位的中文說明（PB-1a；05 5.12.2 第 12 點「每個部位寫『破掉會：……』」）。

戰鬥紀錄（:mod:`trpg.narrative.events`）與之後的介面（PB-1c）共用：每一項破壞效果一句。
"""

from __future__ import annotations

from trpg.content.library import Ruleset
from trpg.content.parts import (
    BossPart,
    ControlBreak,
    InterruptChargeBreak,
    PartBreakEffect,
    SealSkillBreak,
    StatDownBreak,
    StopMechanicBreak,
)
from trpg.shared.types import ResistGroup

__all__ = ["break_effect_zh", "break_lines_zh"]

_STAT_ZH = {
    "move": ("移動", "格"),
    "armor": ("護甲", "點"),
    "hit": ("命中", "點"),
    **{f"resist.{g.value}": (f"{g.display_name}抗性", "‰") for g in ResistGroup},
}


def _skill_name(rules: Ruleset, skill_id: str) -> str:
    try:
        return rules.skill_def(skill_id).name_zh
    except KeyError:
        return skill_id


def _status_name(rules: Ruleset, status_id: str) -> str:
    try:
        return rules.status_def(status_id).name_zh
    except KeyError:
        return status_id


def break_effect_zh(rules: Ruleset, effect: PartBreakEffect) -> str:
    """一項破壞效果的中文（例「封住「霧遁」（正在蓄力就一起打斷）」）。"""
    match effect:
        case SealSkillBreak():
            return f"封住「{_skill_name(rules, effect.skill)}」（正在蓄力就一起打斷）"
        case InterruptChargeBreak():
            return "打斷正在蓄力的強招"
        case StatDownBreak() if effect.stat == "damage_dealt":
            whole, tenth = divmod(effect.amount, 10)
            return f"造成的傷害降為 {whole}{f'.{tenth}' if tenth else ''}%"
        case StatDownBreak():
            name, unit = _STAT_ZH[effect.stat]
            return f"{name} −{effect.amount}{unit}"
        case ControlBreak():
            return f"陷入「{_status_name(rules, effect.status)}」（照頭目原本的免疫）"
        case StopMechanicBreak():
            return f"停止「{_status_name(rules, effect.status)}」，之後也加不上"


def break_lines_zh(rules: Ruleset, part: BossPart) -> tuple[str, ...]:
    """部位 ``on_break`` 每一項的中文（依順序）。"""
    return tuple(break_effect_zh(rules, e) for e in part.on_break)
