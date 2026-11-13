"""技能卡的結構化欄位（Phase 6A-1，去文字化②：``docs/archive/art/去文字化移植需求.md`` 第 2 節）。

前端技能卡常駐 3 行（名稱；AP 圓點、冷卻、射程、時機圖示；一行效果數字＋元素／縮放圖示），需要的是
「數字＋單位＋類別」，不是組好的句子。這裡把 :class:`trpg.narrative.skills.SkillCard` 的 ``cost``、
``effects`` 另外拆成 :class:`SkillCardStats`；**舊的句子欄位原樣保留**（給「詳細」與說明卡）。
只加欄位、不改語意：各段的順序與 ``cost``、``effects`` 一一對應（``index``）。

API 回應一律用這裡的 :class:`SkillCard`（敘事層的卡片加上 ``stats``）與 :func:`skill_card`。
"""

from __future__ import annotations

import contextlib
from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.library import ContentLibrary
from trpg.content.skills import EffectSpec, SkillDef
from trpg.narrative import skills as narrative
from trpg.narrative.skills import CardOwner, skill_ap

__all__ = [
    "CostStat",
    "EffectStat",
    "SkillCard",
    "SkillCardStats",
    "card_stats",
    "skill_card",
]

CostKind = Literal[
    "ap",
    "mana",
    "stamina",
    "hp_percent",
    "self_status",
    "overdraft",
    "upkeep",
    "cooldown",
    "uses_per_battle",
    "source",
    "backlash",
]
EffectCategory = Literal[
    "damage", "heal", "shield", "move", "status", "surface", "summon", "stack", "other"
]
TimingKind = Literal["reaction", "trigger", "delayed", "activation"]


class CostStat(BaseModel):
    """代價的一段（和 ``SkillCard.cost`` 的第 ``index`` 段同一件事）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int
    kind: CostKind
    value: int | None
    """數值：AP、法力、耐力、冷卻回合、每場次數、源力、透支 AP、維持費；HP 代價是千分比（‰）；
    施放後狀態是持續回合；失手反噬沒有數值。"""
    unit: str
    """顯示單位（「AP」「法力」「回合」「‰」……）。"""
    label: str
    """圖示旁的短字：「2」「5%」；沒有數值時為空字串。"""


class EffectStat(BaseModel):
    """效果的一段（和 ``SkillCard.effects`` 的第 ``index`` 行同一件事）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int
    type: str
    """效果原語的代碼（同 ``effect_ids``）。"""
    category: EffectCategory
    label: str | None
    """圖示旁的數字：傷害、治療、護盾寫骰子（「3d6」「2d4＋2」），武器傷害寫倍率（「×1.15」），
    位移寫格數，狀態、表面寫回合，層數寫層；沒有適合的數字為 ``None``。"""
    unit: str | None
    """``label`` 的單位（「格」「回合」「輪」「層」）；骰子與倍率為 ``None``。"""
    dice: str | None = None
    multiplier_permille: int | None = None
    """武器傷害的倍率（‰，已乘技能的 ``damage_permille``）；法術傷害打折時也填。"""
    weapon: bool = False
    """武器傷害（骰子來自手上的武器）。"""
    amount: int | None = None
    """位移格數、持續回合、層數等整數（同 ``label`` 的數字）。"""
    element: str | None = None
    """傷害元素代碼（``fire`` 等）；武器傷害沒寫元素為 ``None``。"""
    element_zh: str | None = None
    name_zh: str | None = None
    """狀態、表面、層數的中文名（給圖示的說明）。"""
    affects: str | None = None


class SkillCardStats(BaseModel):
    """技能卡常駐 3 行要用的結構化數字（Phase 6A-1）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ap: int | None
    cooldown: int | None
    range: int | None
    """射程（``shape.range``）；武器射程時為 ``None`` 而 ``range_weapon`` 為真；沒有射程（自身、
    光環）為 ``None``。"""
    range_weapon: bool = False
    radius: int | None = None
    size: int | None = None
    timing: TimingKind | None = None
    """時機圖示：反應技、被動觸發、延遲（蓄力）、啟動型傳說；一般主動技為 ``None``。"""
    costs: tuple[CostStat, ...] = ()
    effects: tuple[EffectStat, ...] = ()
    scaling_attrs: tuple[str, ...] = ()
    """縮放屬性代碼（同卡片的 ``scaling_attrs``）。"""


class SkillCard(narrative.SkillCard):
    """API 回應的技能卡：敘事層的卡片（句子欄位不變）加上結構化的 ``stats``。"""

    stats: SkillCardStats


def skill_card(
    library: ContentLibrary,
    skill: SkillDef,
    *,
    mastery_active: bool | None = None,
    owner: CardOwner | None = None,
    ally: bool = True,
) -> SkillCard:
    """:func:`trpg.narrative.skills.skill_card` 加上 :func:`card_stats`。"""
    card = narrative.skill_card(
        library, skill, mastery_active=mastery_active, owner=owner, ally=ally
    )
    stats = card_stats(library, skill, scaling_attrs=card.scaling_attrs, ally=ally)
    return SkillCard(**dict(card), stats=stats)


# ---------------------------------------------------------------------------
# 代價
# ---------------------------------------------------------------------------


def _cost(
    index: int, kind: CostKind, value: int | None, unit: str, label: str | None = None
) -> CostStat:
    shown = label if label is not None else ("" if value is None else str(value))
    return CostStat(index=index, kind=kind, value=value, unit=unit, label=shown)


def cost_stats(
    library: ContentLibrary, skill: SkillDef, *, ally: bool = True
) -> tuple[CostStat, ...]:
    """代價各段，順序同 :func:`trpg.narrative.skills.cost_parts`（含 AP）。"""
    cost = skill.cost
    raw: list[tuple[CostKind, int | None, str, str | None]] = []
    ap = skill_ap(library, skill)
    if ap is not None:
        raw.append(("ap", ap, "AP", None))
    if cost.mana:
        raw.append(
            ("mana", library.ruleset.core.mana_cost(cost.mana) if ally else cost.mana, "法力", None)
        )
    if cost.stamina:
        raw.append(("stamina", cost.stamina, "耐力", None))
    if cost.hp_percent:
        raw.append(("hp_percent", cost.hp_percent, "‰", f"{cost.hp_percent / 10:g}%"))
    if cost.self_status:
        raw.append(("self_status", cost.self_status.duration, "回合", ""))
    if cost.overdraft:
        raw.append(("overdraft", cost.overdraft, "AP", None))
    if skill.stance_upkeep:
        table = library.ruleset.forms
        weapon = skill.category == "weapon"
        per = table.stance_upkeep_stamina if weapon else table.stance_upkeep_mana
        raw.append(("upkeep", skill.stance_upkeep * per, "耐力" if weapon else "法力", None))
    if cost.cooldown:
        raw.append(("cooldown", cost.cooldown, "回合", None))
    if cost.uses_per_battle:
        raw.append(("uses_per_battle", cost.uses_per_battle, "次", None))
    if cost.source:
        raw.append(("source", cost.source, "源力", None))
    if cost.on_miss:
        raw.append(("backlash", None, "", None))
    return tuple(
        _cost(i, kind, value, unit, label) for i, (kind, value, unit, label) in enumerate(raw)
    )


# ---------------------------------------------------------------------------
# 效果
# ---------------------------------------------------------------------------

_DAMAGE_TYPES = frozenset(
    {
        "damage",
        "sacrifice_summon",
        "hurl_object",
        "charge_through",
        "detonate_runes",
        "delayed_damage",
    }
)
_MOVE_TYPES = frozenset(
    {
        "push",
        "pull",
        "leap",
        "dash",
        "teleport",
        "teleport_target",
        "shadowstep",
        "swap",
        "swap_any",
    }
)


def _dice_label(spec: EffectSpec) -> str | None:
    if spec.dice is None:
        return None
    flat = f"＋{spec.flat_bonus}" if spec.flat_bonus else ""
    return f"{spec.dice.count}d{spec.dice.sides}{flat}"


def _damage_stat(skill: SkillDef, index: int, spec: EffectSpec) -> EffectStat:
    discount = skill.damage_permille or 1000
    element = spec.element
    dice = _dice_label(spec)
    if dice is not None:
        label, multiplier = dice, None if skill.damage_permille is None else discount
    else:  # 武器傷害（武器技的 damage 沒有骰子：骰子來自手上的武器）
        multiplier = (spec.multiplier_permille or 1000) * discount // 1000
        label = f"×{multiplier / 1000:g}"
    return EffectStat(
        index=index,
        type=spec.type,
        category="damage",
        label=label,
        unit=None,
        dice=dice,
        multiplier_permille=multiplier,
        weapon=dice is None,
        element=None if element is None else element.value,
        element_zh=None if element is None else element.display_name,
        affects=spec.affects,
    )


def _named(library: ContentLibrary, spec: EffectSpec) -> str | None:
    rules = library.ruleset
    try:
        if spec.status is not None:
            return rules.status_def(spec.status).name_zh
        if spec.surface is not None:
            return rules.surface_def(spec.surface).name_zh
        if spec.stack is not None:
            return rules.stack_def(spec.stack).name_zh
    except KeyError:
        return None
    return None


_PLAIN: dict[str, tuple[EffectCategory, str, str | None]] = {
    **dict.fromkeys(_MOVE_TYPES, ("move", "distance", "格")),
    "apply_status": ("status", "duration", "回合"),
    "create_surface": ("surface", "duration", "回合"),
    "summon": ("summon", "duration", "輪"),
    "add_stack": ("stack", "amount", "層"),
    "consume_stack": ("stack", "", "層"),
}
"""沒有骰子的效果：類別、數字取自哪個欄位（空字串＝沒有數字）、單位。"""


def _plain(library: ContentLibrary, index: int, spec: EffectSpec) -> EffectStat:
    category, field, unit = _PLAIN.get(spec.type, ("other", "", None))
    if category == "stack" and spec.stack is not None:
        with contextlib.suppress(KeyError):  # RG-5：連擊點用「點」
            unit = library.ruleset.stack_def(spec.stack).unit_zh
    value = getattr(spec, field) if field else None
    amount = value if isinstance(value, int) else None
    return EffectStat(
        index=index,
        type=spec.type,
        category=category,
        label=None if amount is None else str(amount),
        unit=None if amount is None else unit,
        amount=amount,
        name_zh=_named(library, spec),
        affects=spec.affects,
    )


def effect_stat(
    library: ContentLibrary, skill: SkillDef, index: int, spec: EffectSpec
) -> EffectStat:
    """一個效果的「數字＋單位＋類別」。"""
    kind = spec.type
    if kind in _DAMAGE_TYPES:
        return _damage_stat(skill, index, spec)
    if kind in ("heal", "shield"):
        dice = _dice_label(spec)
        return EffectStat(
            index=index,
            type=kind,
            category="heal" if kind == "heal" else "shield",
            label=dice,
            unit=None,
            dice=dice,
            affects=spec.affects,
        )
    return _plain(library, index, spec)


def _timing(skill: SkillDef) -> TimingKind | None:
    if skill.reaction is not None:
        return "reaction"
    if skill.trigger is not None:
        return "trigger"
    if skill.followup is not None and skill.followup.release is not None:
        return "delayed"
    if any(e.type == "delayed_damage" for e in skill.effects):
        return "delayed"
    if skill.activation is not None:
        return "activation"
    return None


def card_stats(
    library: ContentLibrary,
    skill: SkillDef,
    *,
    scaling_attrs: tuple[str, ...] = (),
    ally: bool = True,
) -> SkillCardStats:
    """``skill`` 卡片的結構化數字（:class:`SkillCardStats`）。"""
    shape = skill.shape
    rng = shape.range
    return SkillCardStats(
        ap=skill_ap(library, skill),
        cooldown=skill.cost.cooldown,
        range=rng if isinstance(rng, int) else None,
        range_weapon=rng == "weapon",
        radius=shape.radius,
        size=shape.size,
        timing=_timing(skill),
        costs=cost_stats(library, skill, ally=ally),
        effects=tuple(effect_stat(library, skill, i, e) for i, e in enumerate(skill.effects)),
        scaling_attrs=scaling_attrs,
    )
