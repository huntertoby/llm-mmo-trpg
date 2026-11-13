"""本場條件不成立的技能（LW-2，``docs/design/06-技能.md`` 6.37「提示與標灰」、玩法決定 #156；
BS-2 加「要拿匕首類」，06 6.21.1 C2、08 8.11）。

有些條件**整場固定**，不成立時整場都不會成立，介面要把帶這種條件的技能標灰並說明原因。這裡只讀
狀態、不推進戰鬥，也不改任何規則。兩種來源：

- :data:`STICKY_CONDITIONS`：整場固定的施放者條件（例：獨狼 ``lone_wolf`` 開戰那一刻就定死），
  用引擎公開的 ``condition_met`` 判斷。
- :data:`WEAPON_NEEDS`（BS-2）：要拿特定武器才可能生效的效果——無聲（``silent_strike``）只在手持
  匕首或雙匕首時生效；「兩下都中」（``all_strikes_hit``）只有雙匕首打得出來（08 8.11 算作雙匕首
  親和）。換裝只在城鎮與營火，戰鬥中手上的武器（形態中看進入前的武器）整場不變，所以和獨狼一樣
  算整場固定。條件本身（「兩下都中」）會隨戰況變，只有「沒拿那種武器」這一半是固定的。

之後別的整場固定條件加進對應的表與 :data:`OFF_REASON_ZH` 即可，前端照
``BattleResponse.skills_off`` 畫，不必改。

- 技能層級的條件（``skill.condition``、第二段的條件）不成立＝整招（被動整個）不會生效
  （``whole``）；只在效果或修正規則上的＝招照樣能用，只有那一部分不會發動。被動修正技能的每條
  規則都是無聲時，沒拿匕首類＝整個被動不會生效。
- ``effects``：不會發動的第一段效果的位置（``skill.effects`` 的索引，和技能卡 ``stats.effects`` 的
  ``index`` 同一套），前端把卡片上那幾個效果數字也標灰（LW-2 驗收可修 2）。
- ``any_of`` 的條件只有每個分支都是 :data:`STICKY_CONDITIONS` 時才判斷（混了會變動的分支時，
  之後可能成立，不標）。
"""

from __future__ import annotations

from trpg.api.schemas import SkillOffOut
from trpg.content.keyword_derive import AFFINITY_BY_CONDITION
from trpg.content.skills import GRANT_SKILL, ConditionSpec, EffectSpec, SkillDef, has_silent_rule
from trpg.engine.modifiers import SILENT_WEAPONS
from trpg.engine.rules.forms import held_weapon
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

__all__ = [
    "ALL_STRIKES_HIT",
    "OFF_REASON_ZH",
    "SILENT_STRIKE",
    "STICKY_CONDITIONS",
    "WEAPON_NEEDS",
    "skills_off",
    "sticky_conditions",
    "sticky_kinds",
]

STICKY_CONDITIONS: frozenset[str] = frozenset({"lone_wolf"})
"""整場固定的施放者條件（不成立時整場都不會成立）。"""

SILENT_STRIKE = "silent_strike"
ALL_STRIKES_HIT = "all_strikes_hit"

WEAPON_NEEDS: dict[str, frozenset[str]] = {
    SILENT_STRIKE: SILENT_WEAPONS,
    ALL_STRIKES_HIT: frozenset({AFFINITY_BY_CONDITION[ALL_STRIKES_HIT]}),
}
"""要拿特定武器才可能生效的東西（BS-2）→ 要拿的武器（手上武器的 ID 在其中才可能成立）。"""

OFF_REASON_ZH: dict[str, str] = {
    "lone_wolf": "開戰時身邊有隊友，獨狼本場不成立",
    SILENT_STRIKE: "要拿匕首類（匕首或雙匕首），無聲本場不成立",
    ALL_STRIKES_HIT: "要拿雙匕首，「兩下都中」本場不成立",
}
"""種類 → 標灰原因（繁體中文）。"""


def _is_sticky(spec: ConditionSpec) -> bool:
    return all(part.type in STICKY_CONDITIONS for part in spec.alternatives())


def _indexed_conditions(skill: SkillDef) -> list[tuple[ConditionSpec, bool, int | None]]:
    """``skill`` 用到的全部條件：(條件, 是不是技能層級, 第一段效果的索引或 ``None``)。"""
    found: list[tuple[ConditionSpec, bool, int | None]] = []
    if skill.condition is not None:
        found.append((skill.condition, True, None))
    if skill.followup is not None and skill.followup.condition is not None:
        found.append((skill.followup.condition, False, None))
    top = {id(e): i for i, e in enumerate(skill.effects)}
    found += [
        (e.condition, False, top.get(id(e)))
        for e in skill.iter_effects(include_followup=True, include_modifiers=True)
        if e.condition is not None
    ]
    found += [(r.condition, False, None) for r in skill.modifiers if r.condition is not None]
    return found


def sticky_conditions(skill: SkillDef) -> list[tuple[ConditionSpec, bool]]:
    """``skill`` 用到的整場固定條件與它是不是技能層級（``True``＝整招看它）。"""
    return [(spec, whole) for spec, whole, _ in _indexed_conditions(skill) if _is_sticky(spec)]


def sticky_kinds(skill: SkillDef) -> tuple[str, ...]:
    """``skill`` 用到的整場固定條件種類（排序、不重複）。"""
    return tuple(
        sorted({part.type for spec, _ in sticky_conditions(skill) for part in spec.alternatives()})
    )


def _off_reason(kinds: list[str]) -> str:
    return "；".join(OFF_REASON_ZH.get(kind, f"條件「{kind}」本場不成立") for kind in kinds)


class _Off:
    """一招累積的不成立：種類、是否整招、第一段效果的索引。"""

    def __init__(self) -> None:
        self.kinds: set[str] = set()
        self.whole = False
        self.effects: set[int] = set()

    def add(self, kind: str, *, whole: bool, index: int | None) -> None:
        self.kinds.add(kind)
        self.whole = self.whole or whole
        if index is not None:
            self.effects.add(index)


def _gives_silent(state: BattleState, effect: EffectSpec) -> bool:
    if effect.type != GRANT_SKILL or effect.skill is None:
        return False
    try:
        return has_silent_rule(state.ruleset.skill_def(effect.skill))
    except KeyError:
        return False


def _weapon_off(state: BattleState, unit: UnitState, skill: SkillDef, off: _Off) -> None:
    """BS-2：手上的武器（形態中看進入前的武器）不是 :data:`WEAPON_NEEDS` 要的那種時，記下無聲與
    「兩下都中」不會生效的部分。"""
    held = held_weapon(unit).id
    if held not in WEAPON_NEEDS[SILENT_STRIKE]:
        if has_silent_rule(skill):
            only_silent = all(rule.change.silent_strike for rule in skill.modifiers)
            off.add(SILENT_STRIKE, whole=only_silent and not skill.effects, index=None)
        for i, effect in enumerate(skill.effects):
            if _gives_silent(state, effect):
                off.add(SILENT_STRIKE, whole=False, index=i)
        if skill.followup is not None and any(
            _gives_silent(state, e) for e in skill.followup.effects
        ):
            off.add(SILENT_STRIKE, whole=False, index=None)
    if held not in WEAPON_NEEDS[ALL_STRIKES_HIT]:
        for spec, whole, index in _indexed_conditions(skill):
            if any(part.type == ALL_STRIKES_HIT for part in spec.alternatives()):
                off.add(ALL_STRIKES_HIT, whole=whole, index=index)


def skills_off(state: BattleState, unit_id: UnitId) -> tuple[SkillOffOut, ...] | None:
    """``unit_id`` 持有的技能中，整場固定條件不成立的（依技能 ID）；沒有時 ``None``。"""
    unit = state.units.get(unit_id)
    if unit is None:
        return None
    here = Subject(unit, unit.xy)
    found: list[SkillOffOut] = []
    for skill_id in sorted(unit.all_skills):
        try:
            skill = state.ruleset.skill_def(skill_id)
        except KeyError:
            continue
        off = _Off()
        for spec, whole, index in _indexed_conditions(skill):
            if _is_sticky(spec) and not condition_met(state, unit, spec, here):
                for part in spec.alternatives():
                    off.add(part.type, whole=whole, index=index)
        _weapon_off(state, unit, skill, off)
        if not off.kinds:
            continue
        kinds = sorted(off.kinds)
        found.append(
            SkillOffOut(
                skill_id=skill_id,
                conditions=tuple(kinds),
                whole=off.whole,
                reason_zh=_off_reason(kinds),
                effects=tuple(sorted(off.effects)),
            )
        )
    return tuple(found) or None
