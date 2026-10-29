"""技能數值的旋鈕（Phase 3W-R2 整理，審查 ③）：完整技能強度（:mod:`~trpg.skillgen.complete`）與
升階重配（:mod:`~trpg.skillgen.skill_tier`）共用的旋鈕蒐集。

兩組旋鈕：

- **強度旋鈕**（:func:`strength_knobs`）：預算器本來就會調的——傷害、治療、護盾、延遲爆炸的骰子或
  倍率、推拉距離（:func:`~trpg.skillgen.evolution.effect_strength_knobs`），加上修正型被動的修正
  幅度與接續段的傷害（:func:`~trpg.skillgen.flash_ops.tuning_extras`）。
- **參數旋鈕**（:func:`param_knobs`）：效果參數上其他的強度旋鈕（``skill_primitives.yaml`` 的
  ``knob``，組合器同源）：狀態與表面的持續回合、累積層數……；預算器的旋鈕除外。

另外提供「只往上加一格」用的工具（:func:`knob_targets`、:func:`next_moves`、:func:`knob_order`），
給完整技能逐格爬升。全部確定性、沒有亂數。
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.composer_parts import Knob, effect_knobs
from trpg.skillgen.evolution import effect_strength_knobs
from trpg.skillgen.flash_ops import Draft, base_draft, tuning_extras

__all__ = [
    "KnobMove",
    "has_strength_knobs",
    "knob_order",
    "knob_targets",
    "next_moves",
    "param_knobs",
    "strength_knobs",
]

_PUSH_PULL = frozenset({"push", "pull"})
_TUNED_FIELDS = frozenset({"dice", "multiplier_permille"})
"""預算器本來就會調的效果欄位（:func:`~trpg.skillgen.evolution.retune` 的旋鈕）。"""
_DICE = re.compile(r"^(\d+)d(\d+)$")


def _extras_op(skill: SkillDef) -> str:
    return "followup" if skill.followup is not None else ""


def strength_knobs(skill: SkillDef, draft: Draft, library: ContentLibrary) -> list[Knob]:
    """``draft``（``skill`` 的草稿）的強度旋鈕。``index`` 指向 :func:`knob_targets` 的清單：效果在
    前，之後是修正規則的 ``change`` 或接續段的效果。"""
    base, effects = draft
    knobs = list(effect_strength_knobs(skill.category, effects, library))
    _, extra = tuning_extras(_extras_op(skill), base, library)
    knobs += [Knob(len(effects) + k.index, k.field, k.values) for k in extra]
    return knobs


def has_strength_knobs(skill: SkillDef, library: ContentLibrary) -> bool:
    """技能有沒有強度旋鈕；沒有的是「點數固定」的結構。"""
    return bool(strength_knobs(skill, base_draft(skill), library))


def param_knobs(
    effects: list[dict[str, Any]], category: str, library: ContentLibrary
) -> list[Knob]:
    """效果參數上的其他強度旋鈕（見模組說明）；預算器本來就會調的骰子、倍率與推拉距離除外。"""
    knobs: list[Knob] = []
    for index, effect in enumerate(effects):
        for name, values, weight in effect_knobs(library, effect, category=category, weight=1):
            if name in _TUNED_FIELDS or (name == "distance" and effect["type"] in _PUSH_PULL):
                continue
            knobs.append(Knob(index, name, tuple(values), weight))
    return knobs


def knob_targets(skill: SkillDef, draft: Draft) -> list[dict[str, Any]]:
    """:func:`strength_knobs` 的 ``index`` 指向的字典：效果，之後接修正規則的 change 或接續段的
    效果（與 ``draft`` 同一批物件，改它就是改草稿）。"""
    base, effects = draft
    if base.get("kind") == "modifier":
        return [*effects, *(m["change"] for m in base["modifiers"])]
    if skill.followup is not None and base.get("followup"):
        return [*effects, *base["followup"]["effects"]]
    return list(effects)


@dataclass(frozen=True, slots=True)
class KnobMove:
    """一個可以往上加的旋鈕：目標清單裡第 ``index`` 個字典的 ``field``，下一格是 ``value``。"""

    index: int
    field: str
    value: Any


def next_moves(knobs: Sequence[Knob], targets: Sequence[dict[str, Any]]) -> Iterator[KnobMove]:
    """每個旋鈕（同一欄位只算一次）從目前的值往上的下一格。"""
    seen: set[tuple[int, str]] = set()
    for knob in knobs:
        if (knob.index, knob.field) in seen or knob.index >= len(targets):
            continue
        seen.add((knob.index, knob.field))
        current = knob_order(targets[knob.index].get(knob.field))
        if current is None:
            continue
        ups = [(o, v) for v in knob.values if (o := knob_order(v)) is not None and o > current]
        if ups:
            yield KnobMove(knob.index, knob.field, min(ups, key=lambda pair: pair[0])[1])


def knob_order(value: Any) -> int | None:
    """旋鈕值的大小：整數照原值、骰子 ``NdM`` 用 ``N × (M + 1)``（平均值 ×2）；其他無法比較。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and (m := _DICE.match(value)) is not None:
        return int(m.group(1)) * (int(m.group(2)) + 1)
    return None
