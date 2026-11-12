"""閃現選項的「前 → 後」差異清單（FL-1a；``docs/phases/閃現蓄力調查.md`` 5.1）。

比對閃現前的技能與選項套用後的技能 **卡片上的數字**（:func:`~trpg.api.skill_cards.card_stats`：AP、
冷卻、射程、半徑、大小、各項代價、每個效果的骰子／倍率／回合（格數、層數）），另加狀態強度
（``magnitude_permille``）與接續段的效果。每一列是一個欄位的「前值、後值、方向」：

- ``better``／``worse``：強度欄位變強／變弱（數字大＝強；骰子比平均）；
- ``cost``：代價欄位（AP、冷卻、法力、耐力……）變了，升或降看前後值；
- ``new``：新加的效果或欄位（前值為 ``None``）。拿掉的效果記 ``worse``（後值為 ``None``）。

只列有變的欄位；順序固定（技能層級 → 代價 → 效果 → 接續段）。前端畫「前 → 後」用，不進規則。
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from fractions import Fraction
from typing import Literal

from trpg.api.run_schemas import StatChangeOut
from trpg.api.skill_cards import CostStat, EffectStat, card_stats, effect_stat
from trpg.content.library import ContentLibrary
from trpg.content.skills import EffectSpec, SkillDef

__all__ = ["flash_changes"]

Direction = Literal["better", "worse", "cost", "new"]

_CATEGORY_ZH = {
    "damage": "傷害",
    "heal": "治療",
    "shield": "護盾",
    "move": "位移",
    "status": "狀態",
    "surface": "表面",
    "summon": "召喚",
    "stack": "層數",
    "other": "效果",
}
_COST_ZH = {
    "ap": "AP",
    "mana": "法力",
    "stamina": "耐力",
    "hp_percent": "HP 代價",
    "self_status": "施放後狀態",
    "overdraft": "透支",
    "upkeep": "維持費",
    "cooldown": "冷卻",
    "uses_per_battle": "每場次數",
    "source": "源力",
    "backlash": "失手反噬",
}
_AMOUNT_ZH = {"回合": "回合", "格": "距離", "輪": "持續", "層": "層數"}
_BUFF_ROUNDS_ZH = {"grant_skill": "獲得技能回合", "zone": "區域回合"}
"""卡片數字沒有回合、但蓄力與輕巧會調回合的增益原語（FL-1c 第 6 點）的列名。"""
_NEUTRAL_MAGNITUDE = 1000
_MAGNITUDE_TYPES = frozenset({"apply_status", "create_surface", "enter_form"})


def _row(
    field: str,
    label_zh: str,
    before: object,
    after: object,
    direction: Direction,
    *,
    effect_index: int | None = None,
) -> StatChangeOut:
    return StatChangeOut(
        field=field,
        label_zh=label_zh,
        effect_index=effect_index,
        before=None if before is None else str(before),
        after=None if after is None else str(after),
        direction=direction,
    )


def _compare(old: Fraction | int, new: Fraction | int) -> Direction:
    return "better" if new > old else "worse"


def _shape_rows(
    before: SkillDef, after: SkillDef, library: ContentLibrary
) -> Iterator[StatChangeOut]:
    old, new = card_stats(library, before), card_stats(library, after)
    for field, label in (("range", "射程"), ("radius", "半徑"), ("size", "大小")):
        a, b = getattr(old, field), getattr(new, field)
        if a == b:
            continue
        if a is None:
            yield _row(field, label, a, b, "new")
        elif b is None:
            yield _row(field, label, a, b, "worse")
        else:
            yield _row(field, label, a, b, _compare(a, b))


def _cost_label(cost: CostStat | None) -> str | None:
    if cost is None:
        return None
    return cost.label or (None if cost.value is None else str(cost.value)) or "有"


def _cost_rows(
    before: SkillDef, after: SkillDef, library: ContentLibrary
) -> Iterator[StatChangeOut]:
    old = {c.kind: c for c in card_stats(library, before).costs}
    new = {c.kind: c for c in card_stats(library, after).costs}
    order = list(dict.fromkeys([*old, *new]))
    for kind in order:
        a, b = old.get(kind), new.get(kind)
        if a is not None and b is not None and (a.value, a.label) == (b.value, b.label):
            continue
        yield _row(f"cost.{kind}", _COST_ZH.get(kind, kind), _cost_label(a), _cost_label(b), "cost")


def _times(permille: int | None) -> str | None:
    return None if permille is None else f"×{permille / 1000:g}"


def _dice_mean(spec: EffectSpec) -> Fraction:
    if spec.dice is None:
        return Fraction(0)
    return Fraction(spec.dice.count * (spec.dice.sides + 1), 2) + (spec.flat_bonus or 0)


def _same_effect(a: EffectSpec, b: EffectSpec) -> bool:
    return (a.type, a.status, a.surface, a.stack, a.form, a.unit) == (
        b.type,
        b.status,
        b.surface,
        b.stack,
        b.form,
        b.unit,
    )


def _name(stat: EffectStat) -> str:
    return stat.name_zh or _CATEGORY_ZH[stat.category]


def _magnitude(spec: EffectSpec) -> int | None:
    if spec.type not in _MAGNITUDE_TYPES:
        return None
    return spec.magnitude_permille or _NEUTRAL_MAGNITUDE


def _pair_rows(
    prefix: str,
    index: int,
    pair: tuple[tuple[EffectSpec, EffectStat], tuple[EffectSpec, EffectStat]],
) -> Iterator[StatChangeOut]:
    (old_spec, old), (new_spec, new) = pair
    where = f"{prefix}[{index}]"
    name = _name(new)
    if old.dice != new.dice and old.dice is not None and new.dice is not None:
        direction = _compare(_dice_mean(old_spec), _dice_mean(new_spec))
        yield _row(
            f"{where}.dice", f"{name}骰子", old.dice, new.dice, direction, effect_index=index
        )
    if old.multiplier_permille != new.multiplier_permille:
        a, b = old.multiplier_permille, new.multiplier_permille
        direction = "new" if a is None else ("worse" if b is None else _compare(a, b))
        yield _row(
            f"{where}.multiplier_permille",
            f"{name}倍率",
            _times(a),
            _times(b),
            direction,
            effect_index=index,
        )
    if old.amount != new.amount:
        a, b = old.amount, new.amount
        what = _AMOUNT_ZH.get(new.unit or old.unit or "", "數值")
        direction = "new" if a is None else ("worse" if b is None else _compare(a, b))
        yield _row(f"{where}.amount", f"{name}{what}", a, b, direction, effect_index=index)
    buff = _BUFF_ROUNDS_ZH.get(new_spec.type)
    if (
        buff is not None
        and old.amount is None
        and new.amount is None
        and old_spec.duration is not None
        and new_spec.duration is not None
        and old_spec.duration != new_spec.duration
    ):
        # FL-1c 第 6 點：增益的回合（暫時給技能、持續區域）卡片數字不列，但蓄力、輕巧會調它
        a, b = old_spec.duration, new_spec.duration
        yield _row(f"{where}.amount", buff, a, b, _compare(a, b), effect_index=index)
    a_mag, b_mag = _magnitude(old_spec), _magnitude(new_spec)
    if a_mag is not None and b_mag is not None and a_mag != b_mag:
        yield _row(
            f"{where}.magnitude_permille",
            f"{name}強度",
            f"{a_mag}‰",
            f"{b_mag}‰",
            _compare(a_mag, b_mag),
            effect_index=index,
        )


def _effect_rows(
    prefix: str,
    old: Sequence[tuple[EffectSpec, EffectStat]],
    new: Sequence[tuple[EffectSpec, EffectStat]],
) -> Iterator[StatChangeOut]:
    for index in range(max(len(old), len(new))):
        a = old[index] if index < len(old) else None
        b = new[index] if index < len(new) else None
        if a is not None and b is not None and _same_effect(a[0], b[0]):
            yield from _pair_rows(prefix, index, (a, b))
            continue
        if a is not None:
            label = a[1].label or _name(a[1])
            yield _row(f"{prefix}[{index}]", _name(a[1]), label, None, "worse", effect_index=index)
        if b is not None:
            label = b[1].label or _name(b[1])
            yield _row(f"{prefix}[{index}]", _name(b[1]), None, label, "new", effect_index=index)


def _effects(
    library: ContentLibrary, skill: SkillDef, specs: Sequence[EffectSpec]
) -> list[tuple[EffectSpec, EffectStat]]:
    return [(spec, effect_stat(library, skill, i, spec)) for i, spec in enumerate(specs)]


def flash_changes(
    library: ContentLibrary, before: SkillDef, after: SkillDef
) -> tuple[StatChangeOut, ...]:
    """``before``（閃現前）到 ``after``（選項套用後）卡片數字的差異清單（見模組說明）。"""
    rows = [
        *_shape_rows(before, after, library),
        *_cost_rows(before, after, library),
        *_effect_rows(
            "effects",
            _effects(library, before, before.effects),
            _effects(library, after, after.effects),
        ),
        *_effect_rows(
            "followup",
            _effects(library, before, before.followup.effects if before.followup else ()),
            _effects(library, after, after.followup.effects if after.followup else ()),
        ),
    ]
    return tuple(rows)
