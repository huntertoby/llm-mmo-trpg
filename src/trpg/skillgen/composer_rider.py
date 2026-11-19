"""組合器的關鍵字附帶配方（WC-2 第 5.1、5.2 項；#167 第 5 題）。

許願覆蓋表（WC-1）：

- **層數關鍵字**（連擊、怒氣、專注、氣）：組合器一指定層數就固定用蓄力骨架（形狀只有單體、直線、
  錐形，附帶只有層數與狀態），所以「連擊＋範圍／地形／召喚／另一種層數」全是 0。
- **召喚物**：組合器做「利用召喚物」的主動技只會做獻祭骨架，「召喚物＋傷害／控制／位移／地形／範圍」
  全是 0（設計允許「下指令集火」這類）。

:func:`add_rider`：組合器照一般流程組好的主動技（不指定關鍵字），在效果最後多一個「附帶」——層數
關鍵字是累積或消耗那種層數（``add_stack``／``consume_stack``，同蓄力骨架的寫法），召喚物是對自己
施加「號令」（``commanding``：你的召喚物傷害提高，召喚物關鍵字的利用）——再用組合器同一套旋鈕重調
強度（:func:`~trpg.skillgen.composer_tuning.tune`），最後過驗證器（骨架允許的附帶原語、預算窗、
互斥規則）。做不出來回傳 ``None``。亂數只來自呼叫端給的 ``rng``。

組合器（:mod:`trpg.skillgen.random_composer`）在指定這些關鍵字時，用獨立的亂數串流決定要不要改走
這條路（``structure.stack_rider_permille``、``structure.summon_rider_permille``）；沒抽中或做不出來
時照原本的組法，所以既有種子的結果不變。
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_parts import Knob, effect_knobs
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.flash_ops import base_draft
from trpg.skillgen.mechanics import mechanic_tags
from trpg.skillgen.validate import validate_skill

__all__ = [
    "COMMANDING",
    "SUMMON_KEYWORD",
    "add_rider",
    "refresh_tags",
    "rider_effect",
    "rider_keywords",
]

COMMANDING = "commanding"
"""號令（召喚物關鍵字的利用：你的召喚物傷害提高，``statuses.yaml``）。"""
SUMMON_KEYWORD = "summon"
"""召喚物關鍵字。"""
_ADD, _CONSUME = "add_stack", "consume_stack"


def rider_keywords(library: ContentLibrary) -> frozenset[str]:
    """有附帶配方的關鍵字：組合器會抽的層數（``stacks.yaml`` 的 ``composer``）與召喚物。"""
    stacks = {s.id for s in library.ruleset.stacks.stacks if s.composer}
    return frozenset({*stacks, SUMMON_KEYWORD} & set(library.keywords.ids()))


def rider_effect(library: ContentLibrary, keyword: str, rng: Rng) -> dict[str, Any] | None:
    """``keyword`` 的附帶效果（數值之後由旋鈕調）。層數：依 ``builder.builder_permille`` 擲累積或
    消耗（對象照層數的 ``owner``）；召喚物：對自己施加號令。其他關鍵字 ``None``。"""
    if keyword == SUMMON_KEYWORD:
        return {"type": "apply_status", "status": COMMANDING, "affects": "self"}
    stack = next((s for s in library.ruleset.stacks.stacks if s.id == keyword), None)
    if stack is None or not stack.composer:
        return None
    affects = "self" if stack.owner == "self" else "enemies"
    if rng.chance_permille(library.composer.builder.builder_permille):
        return {"type": _ADD, "stack": stack.id, "affects": affects, "amount": 1}
    return {"type": _CONSUME, "stack": stack.id, "affects": affects, "per_stack_permille": 50}


def refresh_tags(library: ContentLibrary, skill: SkillDef) -> SkillDef:
    """組合器技能改過效果後重算標籤：前兩個（主題元素、骨架）照舊，機制標籤
    （:func:`~trpg.skillgen.mechanics.mechanic_tags`）照新的效果。"""
    head = list(skill.tags[:2])
    found = [t for t in mechanic_tags(skill, library.ruleset) if t not in head]
    tags = (*head, *found)
    return skill if tags == skill.tags else skill.model_copy(update={"tags": tags})


def _knobs(category: str, effects: list[dict[str, Any]], library: ContentLibrary) -> list[Knob]:
    """所有效果的強度旋鈕（同組合器：``skill_primitives.yaml`` 的 ``knob``）。"""
    return [
        Knob(index, name, tuple(values), weight)
        for index, effect in enumerate(effects)
        for name, values, weight in effect_knobs(library, effect, category=category, weight=1)
    ]


def add_rider(library: ContentLibrary, skill: SkillDef, keyword: str, rng: Rng) -> SkillDef | None:
    """``skill`` 多一個 ``keyword`` 的附帶效果（見模組說明）；``skill`` 要是主動技、不是陷阱或
    複合技、效果數沒到稀有度的上限，而且還沒有這種附帶。"""
    if (
        skill.kind != "active"
        or skill.trap is not None
        or skill.followup is not None
        or skill.variants
        or len(skill.effects) >= library.budget.rarity[skill.rarity].max_effects
    ):
        return None
    effect = rider_effect(library, keyword, rng)
    if effect is None:
        return None
    base, effects = base_draft(skill)
    same = (effect["type"], effect.get("stack"), effect.get("status"))
    if any((e["type"], e.get("stack"), e.get("status")) == same for e in effects):
        return None
    effects.append(effect)
    knobs = _knobs(skill.category, effects, library)
    try:
        if not tune(rng, library, base, effects, knobs):
            return None
        made = refresh_tags(library, SkillDef.model_validate({**base, "effects": effects}))
    except (ValidationError, BudgetError):
        return None
    return None if validate_skill(made, library) else made
