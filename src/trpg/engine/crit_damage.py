"""暴擊傷害倍率（CR-1，``docs/design/05-戰鬥.md`` 5.4.2，#178）。

暴擊時照常擲原本的傷害骰，再多擲一組同樣顆數；多擲的那組乘（倍率 − 100%），無條件捨去
（:func:`trpg.engine.rules.combat.crit_extra_total`）。屬性加成、固定值不放大。

倍率由攻擊方在擲骰時算好，放進 :class:`~trpg.engine.effects.models.DamageEffect` 的
``crit_permille``（:func:`crit_damage_permille`）：

1. 武器基礎：普攻看攻擊用的武器（形態中是天生武器）、武器技看手上的武器，武器的
   ``crit_permille``；沒填（或法術技）照 ``core.crit_damage.base_permille``（2000‰）。單位檔另填的
   倍率在開戰時已寫進單位的武器（:meth:`~trpg.content.library.ContentLibrary.weapon_of`）。
2. 裝備數值詞條「暴擊傷害 +N%」（:func:`~trpg.engine.gear.core.gear_crit_damage_permille`；同一詞條
   開戰時已照 08 8.21.5.3 遞減）。
3. 修正技（修正型被動）的 ``crit_damage_permille``
   （:func:`~trpg.engine.modifiers.crit_damage_bonus`；同一招的複本遞減）；被動觸發等不受修正的施放不算。
4. 這招自帶的倍率（``SkillDef.crit_permille``）比基礎倍率多出的部分。
5. 種族環境被動的數值類 ``stats.crit_damage_permille``（#179，
   :func:`~trpg.engine.rules.race.race_crit_damage_permille`）。

全部相加，最後套全身上下限 ``core.crit_damage.min_permille``～``max_permille``（150%～300%）。
敵我用同一套規則。

角色面板（CR-1b，05 5.4.2 第 8 點）用 :func:`crit_damage_breakdown` 列出來源；它和
:func:`crit_damage_permille` 共用 :func:`_raw_sources`，最後倍率一定相同。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.battle import WeaponDef
from trpg.content.skills import SkillDef
from trpg.engine.gear.core import gear_crit_damage_permille
from trpg.engine.modifiers import Use, crit_damage_bonus, crit_damage_bonus_parts
from trpg.engine.rules.forms import held_weapon
from trpg.engine.rules.race import race_crit_damage_permille
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "CritDamageBreakdown",
    "CritDamageSource",
    "crit_damage_breakdown",
    "crit_damage_detail_zh",
    "crit_damage_permille",
    "crit_weapon",
]

_GEAR_CARRIER_PREFIX = "skill_gear_"
"""裝備規則改變的包裝技能 ID 前綴（:func:`trpg.engine.activations._gear_rule_carrier`）。"""


@dataclass(frozen=True, slots=True)
class CritDamageSource:
    """暴擊傷害倍率的一項來源（‰）：``weapon`` 是基礎值（沒有武器時是規則的基礎），其他是加減量。"""

    kind: Literal["weapon", "gear", "race", "modifier", "skill"]
    permille: int
    name_zh: str = ""
    gear_carrier: bool = False
    """``modifier`` 來自裝備的規則改變（不是技能）。"""


@dataclass(frozen=True, slots=True)
class CritDamageBreakdown:
    """暴擊傷害倍率與來源：``raw`` 是相加的結果，``total`` 是套完全身上下限的最後倍率。"""

    sources: tuple[CritDamageSource, ...]
    raw: int
    total: int
    min_permille: int
    max_permille: int


@dataclass(frozen=True, slots=True)
class _Raw:
    weapon: WeaponDef | None
    base: int
    gear: int
    race: int
    modifier: int
    skill: int

    @property
    def sum(self) -> int:
        return self.base + self.gear + self.race + self.modifier + self.skill


def crit_weapon(unit: UnitState, skill: SkillDef | None) -> WeaponDef | None:
    """決定基礎倍率的武器：普攻是 ``unit.weapon``（形態中是天生武器）、武器技是手上的武器；
    法術技不看武器（``None``）。"""
    if skill is None:
        return unit.weapon
    return held_weapon(unit) if skill.category == "weapon" else None


def crit_damage_permille(
    state: BattleState,
    unit: UnitState,
    *,
    use: Use | None = None,
    subject: Subject | None = None,
    skill: SkillDef | None = None,
) -> int:
    """``unit`` 這一次攻擊的暴擊傷害倍率（‰，已套全身上下限）。

    ``skill``：施放的技能（普攻為 ``None``）；``use``：受修正規則影響的動作（被動觸發等不受修正的
    施放為 ``None``）；``subject``：這次攻擊的目標（修正規則的條件看它）。"""
    rules = state.ruleset.core.crit_damage
    total = _raw_sources(state, unit, use=use, subject=subject, skill=skill).sum
    return max(rules.min_permille, min(rules.max_permille, total))


def _raw_sources(
    state: BattleState,
    unit: UnitState,
    *,
    use: Use | None,
    subject: Subject | None,
    skill: SkillDef | None,
) -> _Raw:
    """各來源的數字（結算與角色面板共用）。"""
    rules = state.ruleset.core.crit_damage
    weapon = crit_weapon(unit, skill)
    own = None if weapon is None else weapon.crit_permille
    modifier = 0
    if use is not None:
        modifier = crit_damage_bonus(state, unit, use, _target(unit, subject))
    return _Raw(
        weapon=weapon,
        base=rules.base_permille if own is None else own,
        gear=gear_crit_damage_permille(unit),
        race=race_crit_damage_permille(state.ruleset, unit),
        modifier=modifier,
        skill=0
        if skill is None or skill.crit_permille is None
        else skill.crit_permille - rules.base_permille,
    )


def _target(unit: UnitState, subject: Subject | None) -> Subject:
    return subject if subject is not None else Subject(unit, unit.xy)


def crit_damage_breakdown(
    state: BattleState,
    unit: UnitState,
    *,
    use: Use | None = None,
    subject: Subject | None = None,
    skill: SkillDef | None = None,
) -> CritDamageBreakdown:
    """:func:`crit_damage_permille` 加上來源（CR-1b，角色面板「▸ 詳細」）：武器（一定列）、裝備
    詞條、種族、修正技（每招一項）、技能自帶；是 0 的不列。``total`` 和 :func:`crit_damage_permille`
    同一組參數的結果相同。修正技每招各自捨去，加起來可能和合計差 1‰（只影響顯示的拆項）。"""
    rules = state.ruleset.core.crit_damage
    raw = _raw_sources(state, unit, use=use, subject=subject, skill=skill)
    sources = [
        CritDamageSource("weapon", raw.base, "" if raw.weapon is None else raw.weapon.name_zh)
    ]
    sources += [CritDamageSource("gear", raw.gear)] if raw.gear else []
    sources += [CritDamageSource("race", raw.race)] if raw.race else []
    if use is not None and raw.modifier:
        sources += [
            CritDamageSource(
                "modifier",
                amount,
                source.name_zh,
                gear_carrier=source.id.startswith(_GEAR_CARRIER_PREFIX),
            )
            for source, amount in crit_damage_bonus_parts(state, unit, use, _target(unit, subject))
        ]
    sources += [CritDamageSource("skill", raw.skill)] if raw.skill else []
    return CritDamageBreakdown(
        sources=tuple(sources),
        raw=raw.sum,
        total=max(rules.min_permille, min(rules.max_permille, raw.sum)),
        min_permille=rules.min_permille,
        max_permille=rules.max_permille,
    )


def _pct(permille: int) -> str:
    return f"{permille / 10:g}%"


def _signed_pct(permille: int) -> str:
    return f"{permille / 10:+g}%"


def _source_zh(source: CritDamageSource, *, names: bool) -> str:
    if source.kind == "weapon":
        if not source.name_zh:
            return f"基礎 {_pct(source.permille)}"
        return f"武器「{source.name_zh}」{_pct(source.permille)}"
    if source.kind == "modifier":
        label = "詞條" if source.gear_carrier else "修正技"
        if names and source.name_zh:
            return f"{label}「{source.name_zh}」{_signed_pct(source.permille)}"
        return f"{label} {_signed_pct(source.permille)}"
    label = {"gear": "詞條", "race": "種族", "skill": "技能自帶"}[source.kind]
    return f"{label} {_signed_pct(source.permille)}"


def crit_damage_detail_zh(breakdown: CritDamageBreakdown, *, names: bool = True) -> str:
    """角色面板「▸ 詳細」的來源（05 5.4.2 第 8 點），例「武器「戰斧」200%・詞條 +10%・種族 +25%・
    修正技「〇〇」+25%（全身上限 300%）」；被上下限截掉時最後寫「・頂到上限 300%」或
    「・最低 150%」。

    ``names``：``False`` 時修正技不寫技能名（觀看者看不到這個單位的技能；同一個標籤合併成一項）。"""
    sources = breakdown.sources if names else _merge_unnamed(breakdown.sources)
    text = "・".join(_source_zh(s, names=names) for s in sources)
    if breakdown.raw > breakdown.max_permille:
        return f"{text}・頂到上限 {_pct(breakdown.max_permille)}"
    if breakdown.raw < breakdown.min_permille:
        return f"{text}・最低 {_pct(breakdown.min_permille)}"
    return f"{text}（全身上限 {_pct(breakdown.max_permille)}）"


def _merge_unnamed(sources: tuple[CritDamageSource, ...]) -> tuple[CritDamageSource, ...]:
    """不寫名字時，修正技（技能與裝備規則各一項）合併成一項，放在第一個修正技的位置。"""
    out: list[CritDamageSource] = []
    for source in sources:
        if source.kind != "modifier":
            out.append(source)
            continue
        at = next(
            (
                i
                for i, s in enumerate(out)
                if s.kind == "modifier" and s.gear_carrier == source.gear_carrier
            ),
            None,
        )
        if at is None:
            out.append(CritDamageSource("modifier", source.permille, "", source.gear_carrier))
        else:
            merged = out[at].permille + source.permille
            out[at] = CritDamageSource("modifier", merged, "", source.gear_carrier)
    return tuple(s for s in out if s.kind != "modifier" or s.permille != 0)
