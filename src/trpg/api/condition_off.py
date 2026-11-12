"""本場條件不成立的技能（LW-2，``docs/design/06-技能.md`` 6.37「提示與標灰」、玩法決定 #156）。

有些施放者條件**整場固定**（例：獨狼 ``lone_wolf`` 開戰那一刻就定死），不成立時整場都不會成立，
介面要把帶這種條件的技能標灰並說明原因。這裡只讀狀態、不推進戰鬥，也不改任何規則：

- :data:`STICKY_CONDITIONS`：會被標灰的條件種類。之後別的整場固定條件（例 BS-2「要拿匕首類」）
  加進這張表與 :data:`OFF_REASON_ZH` 即可，前端照 ``BattleResponse.skills_off`` 畫，不必改。
- 技能層級的條件（``skill.condition``、第二段的條件）不成立＝整招（被動整個）不會生效
  （``whole``）；只在效果或修正規則上的＝招照樣能用，只有那一部分不會發動。
- ``any_of`` 的條件只有每個分支都是 :data:`STICKY_CONDITIONS` 時才判斷（混了會變動的分支時，
  之後可能成立，不標）。
"""

from __future__ import annotations

from trpg.api.schemas import SkillOffOut
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import BattleState
from trpg.shared.types import UnitId

__all__ = [
    "OFF_REASON_ZH",
    "STICKY_CONDITIONS",
    "skills_off",
    "sticky_conditions",
    "sticky_kinds",
]

STICKY_CONDITIONS: frozenset[str] = frozenset({"lone_wolf"})
"""整場固定的施放者條件（不成立時整場都不會成立）。"""

OFF_REASON_ZH: dict[str, str] = {
    "lone_wolf": "開戰時身邊有隊友，獨狼本場不成立",
}
"""條件種類 → 標灰原因（繁體中文）。"""


def _is_sticky(spec: ConditionSpec) -> bool:
    return all(part.type in STICKY_CONDITIONS for part in spec.alternatives())


def sticky_conditions(skill: SkillDef) -> list[tuple[ConditionSpec, bool]]:
    """``skill`` 用到的整場固定條件與它是不是技能層級（``True``＝整招看它）。"""
    found: list[tuple[ConditionSpec, bool]] = []
    if skill.condition is not None:
        found.append((skill.condition, True))
    if skill.followup is not None and skill.followup.condition is not None:
        found.append((skill.followup.condition, False))
    found += [
        (e.condition, False)
        for e in skill.iter_effects(include_followup=True, include_modifiers=True)
        if e.condition is not None
    ]
    found += [(r.condition, False) for r in skill.modifiers if r.condition is not None]
    return [(spec, whole) for spec, whole in found if _is_sticky(spec)]


def sticky_kinds(skill: SkillDef) -> tuple[str, ...]:
    """``skill`` 用到的整場固定條件種類（排序、不重複）。"""
    return tuple(
        sorted({part.type for spec, _ in sticky_conditions(skill) for part in spec.alternatives()})
    )


def _off_reason(kinds: list[str]) -> str:
    return "；".join(OFF_REASON_ZH.get(kind, f"條件「{kind}」本場不成立") for kind in kinds)


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
        off = [
            (spec, whole)
            for spec, whole in sticky_conditions(skill)
            if not condition_met(state, unit, spec, here)
        ]
        if not off:
            continue
        kinds = sorted({part.type for spec, _ in off for part in spec.alternatives()})
        found.append(
            SkillOffOut(
                skill_id=skill_id,
                conditions=tuple(kinds),
                whole=any(whole for _, whole in off),
                reason_zh=_off_reason(kinds),
            )
        )
    return tuple(found) or None
