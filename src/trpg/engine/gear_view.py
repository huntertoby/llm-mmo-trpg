"""裝備加成的來源摘要（Phase 3G-G4，唯讀；給英雄面板與單位資訊顯示）。

只讀 :class:`~trpg.engine.gear_state.GearState`（開戰時已算好的遞減後加值）與規則包的硬上限，
不參與任何結算：每一行是「某個數值 ＋ 實際值 ＋ 來自哪些物品的哪些詞條 ＋ 遞減與截斷的說明」。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from trpg.content.equipment import CostAffix, StatAffix
from trpg.content.skills import condition_text
from trpg.engine.gear_state import BonusStat, GearAffix, GearBonus, GearState
from trpg.engine.state import UnitState
from trpg.shared.types import Attribute, Element

__all__ = ["GearTotalView", "gear_totals"]

_FULL = 1000
_PERMILLE_STATS: frozenset[str] = frozenset(
    {"damage_permille", "defense_permille", "damage_taken_permille"}
)

_STAT_LABEL: dict[str, str] = {
    "hit": "命中",
    "damage_permille": "傷害",
    "defense_permille": "防禦",
    "damage_taken_permille": "受到的傷害",
    "cooldown_delta": "技能冷卻",
    "turn_start_hp_loss": "回合開始失去 HP",
    "max_hp": "最大 HP",
    "move": "移動",
}


class GearTotalView(BaseModel):
    """英雄面板的一行裝備加成。

    - ``value``：實際值（遞減後、套上限後）；``permille`` 為真時單位是千分比。
    - ``before_cap``：遞減後、套上限前的值；``capped`` 為真代表被上限截斷。
    - ``condition_zh``：條件數值才有（例如「高處」）。
    - ``sources_zh``：每一條貢獻的詞條，格式「物品名：詞條文字（權重）」。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    label_zh: str
    value: int
    before_cap: int
    capped: bool
    permille: bool
    text_zh: str
    note_zh: str
    condition_zh: str | None = None
    sources_zh: tuple[str, ...] = ()


def _signed(value: int, *, permille: bool) -> str:
    if permille:
        return f"{value / 10:+g}%"
    return f"{value:+d}"


def _source_text(gear: GearState, entry: GearAffix) -> str:
    names = {i.slot: i.name_zh for i in gear.items}
    name = names.get(entry.slot, entry.item_id)
    text = entry.affix.name_zh
    if entry.value is not None:
        raw = f"{entry.value / 10:g}%" if entry.affix.value_unit == "permille" else str(entry.value)
        text = text.replace("{n}", raw)
    weight = "" if entry.weight_permille == _FULL else f"（遞減：{entry.weight_permille / 10:g}%）"
    if entry.weight_permille == 0:
        weight = "（遞減：不生效）"
    return f"{name}：{text}{weight}"


def _stat_key(affix: StatAffix) -> str:
    if affix.stat == "attribute":
        return f"attr:{affix.attribute.value if affix.attribute else ''}"
    if affix.stat == "element_resist":
        return f"resist:{affix.element.value if affix.element else ''}"
    return affix.stat


def _entry_keys(entry: GearAffix) -> list[str]:
    """這條詞條貢獻到哪些 ``merged`` 的鍵。"""
    affix = entry.affix
    if isinstance(affix, StatAffix) and affix.stat != "defense":
        return [_stat_key(affix)]
    if isinstance(affix, CostAffix) and any(p.stat == "move" for p in affix.parts):
        return ["move"]
    return []


def _merged_label(key: str) -> str:
    kind, _, name = key.partition(":")
    if kind == "attr":
        return Attribute(name).display_name
    if kind == "resist":
        return f"{Element(name).display_name}抗性"
    return _STAT_LABEL.get(key, key)


def _merged_lines(gear: GearState, move_cap: int) -> list[GearTotalView]:
    before = dict(gear.uncapped)
    lines: list[GearTotalView] = []
    for key, value in gear.merged:
        raw = before.get(key, value)
        permille = key.startswith("resist:")
        sources = tuple(_source_text(gear, e) for e in gear.affixes if key in _entry_keys(e))
        capped = raw != value
        label = _merged_label(key)
        note = "來自裝備"
        if len(sources) > 1:
            note += "；同類詞條已依遞減疊加"
        if capped:
            cap_text = _signed(move_cap, permille=False) if key == "move" else ""
            shown = _signed(raw, permille=permille)
            note += f"；截斷：{label}加成合計上限 {cap_text}（截斷前 {shown}）"
        lines.append(
            GearTotalView(
                key=key,
                label_zh=label,
                value=value,
                before_cap=raw,
                capped=capped,
                permille=permille,
                text_zh=f"{label} {_signed(value, permille=permille)}",
                note_zh=note,
                sources_zh=sources,
            )
        )
    return lines


def _bonus_entries(gear: GearState, bonus: GearBonus) -> Iterable[GearAffix]:
    return (e for e in gear.affixes if e.affix.id == bonus.affix_id)


def _bonus_lines(gear: GearState, damage_cap: int) -> list[GearTotalView]:
    groups: dict[tuple[BonusStat, str | None, bool], list[GearBonus]] = defaultdict(list)
    for bonus in gear.bonuses:
        cond = None if bonus.condition is None else condition_text(bonus.condition)
        groups[(bonus.stat, cond, bonus.negate)].append(bonus)
    damage_total = sum(b.amount for b in gear.bonuses if b.stat == "damage_permille")
    lines: list[GearTotalView] = []
    for (stat, cond, negate), bonuses in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")
    ):
        total = sum(b.amount for b in bonuses)
        permille = stat in _PERMILLE_STATS
        capped = stat == "damage_permille" and damage_total > damage_cap
        value = min(total, damage_cap) if stat == "damage_permille" else total
        label = _STAT_LABEL[stat]
        condition = None if cond is None else (f"不是「{cond}」" if negate else cond)
        note = "來自裝備"
        if condition is not None:
            note += f"；條件成立時才生效：{condition}"
        if capped:
            note += (
                f"；截斷：全身傷害加成合計上限 {_signed(damage_cap, permille=True)}"
                f"（所有傷害加成合計 {_signed(damage_total, permille=True)}）"
            )
        sources = tuple(
            dict.fromkeys(_source_text(gear, e) for b in bonuses for e in _bonus_entries(gear, b))
        )
        lines.append(
            GearTotalView(
                key=f"{stat}:{cond or ''}:{int(negate)}",
                label_zh=label,
                value=value,
                before_cap=total,
                capped=capped,
                permille=permille,
                text_zh=f"{label} {_signed(value, permille=permille)}",
                note_zh=note,
                condition_zh=condition,
                sources_zh=sources,
            )
        )
    return lines


def gear_totals(unit: UnitState, *, damage_cap: int, move_cap: int) -> tuple[GearTotalView, ...]:
    """單位的裝備加成來源摘要（沒有裝備時為空）。``damage_cap``、``move_cap`` 為規則包的硬上限。"""
    gear = unit.gear
    if not gear.items:
        return ()
    return tuple(_merged_lines(gear, move_cap) + _bonus_lines(gear, damage_cap))
