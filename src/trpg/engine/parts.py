"""頭目部位的合法性查詢（PB-1a，``docs/design/05-戰鬥.md`` 5.12.2、5.12.3）。

- :func:`part_targets`：純查詢，某個動作（``Attack`` 或 ``UseSkill``，帶 ``target_id``）對目標的
  每個部位能不能選、不能的原因代碼（依部位 ID 排序）。API 與 AI 都用它；``resolve`` 驗
  ``target_part`` 時呼叫同一個函式（:func:`check_target_part`）。
- ``legal_actions`` **不列舉部位變體**（否則效用 AI 的候選截斷會變、實戰結果跟著變；T6）。
- 判定時點（R5）：宣告動作時以當下的位置、朝向、狀態、階段判一次；同一個動作的每一下都打同一個
  部位，部位破了之後剩下的打本體。

能選部位的動作（T7、R1、R9）：普攻（不含蓄力武器的普攻）與單體、對該目標有傷害效果的技能；
召喚物不能選。打得到的條件：

- ``any``：一定可以。
- ``behind``：攻擊者站在目標的背後格（``rules/facing.py::back_xy``），而且這次攻擊是近戰（同背刺的
  ``AttackProfile.melee``）。
- ``high_or_far``：攻擊者所在格比頭目高 ≥ 1 層，或曼哈頓距離 > 3（R7，同濃霧「超過 N 格」）。
- ``disabled``：頭目身上有倒地、暈眩或冰凍（:data:`DISABLED_STATUSES`，照設計文字列 ID）。
- ``exposed_in``：非空時，頭目目前的階段 ID 要在清單內。
- 已破的部位不能選。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.parts import BossPart
from trpg.content.skills import SkillDef
from trpg.engine import modifiers
from trpg.engine.actions import Action, Attack, UseSkill
from trpg.engine.rules.combat import weapon_profile
from trpg.engine.rules.facing import back_xy
from trpg.engine.rules.forms import natural_charge
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skills.targeting import resolve_effects, skill_profile
from trpg.engine.state import BattleState, UnitState
from trpg.engine.variants import target_point, varied_skill

__all__ = [
    "DISABLED_STATUSES",
    "FAR_BEYOND",
    "PART_REASON_ZH",
    "PartReason",
    "PartTarget",
    "check_target_part",
    "current_phase_id",
    "part_targets",
]

FAR_BEYOND = 3
"""``high_or_far`` 的距離條件：曼哈頓距離 > 3（4 格起；R7）。"""

DISABLED_STATUSES: tuple[str, ...] = ("frozen", "prone", "stun")
"""``disabled`` 的條件：頭目身上有其中一個狀態（05 5.12.2 第 8 點「倒地、暈眩或冰凍」）。"""

type PartReason = Literal[
    "summon",
    "charge_attack",
    "area_skill",
    "no_damage",
    "copy_cast",
    "broken",
    "not_exposed",
    "need_behind",
    "need_high_or_far",
    "need_disabled",
]

PART_REASON_ZH: dict[str, str] = {
    "summon": "召喚物不能選部位",
    "charge_attack": "蓄力武器的普攻不能選部位",
    "area_skill": "只有單體招能選部位",
    "no_damage": "這一招對目標沒有傷害，不能選部位",
    "copy_cast": "複製施放的技能不能選部位",
    "broken": "已經破了",
    "not_exposed": "這個階段還沒露出",
    "need_behind": "要從背後近戰才打得到",
    "need_high_or_far": "要從高處（高 1 層以上）或 4 格外才打得到",
    "need_disabled": "要趁頭目倒地、暈眩或冰凍時才打得到",
}
"""原因代碼的中文（``IllegalActionError`` 與介面共用）。"""


@dataclass(frozen=True, slots=True)
class PartTarget:
    """一個部位能不能選：``reason`` 為 ``None`` 時可以選。"""

    part_id: str
    name_zh: str
    reason: PartReason | None

    @property
    def ok(self) -> bool:
        return self.reason is None


def current_phase_id(unit: UnitState) -> str | None:
    """``unit`` 目前的階段 ID（沒有階段時為 ``None``）。"""
    if not unit.phases:
        return None
    return unit.phases[unit.phase_index].id


def part_targets(state: BattleState, action: Action) -> tuple[PartTarget, ...]:
    """``action`` 對目標的每個部位能不能選（依部位 ID 排序）；目標沒有部位、或不是帶 ``target_id``
    的普攻或技能時為空。"""
    if not isinstance(action, (Attack, UseSkill)) or action.target_id is None:
        return ()
    target = state.units.get(action.target_id)
    attacker = state.units.get(action.unit_id)
    if target is None or attacker is None or not target.parts:
        return ()
    shared, melee = _action_reason(state, attacker, target, action)
    return tuple(
        PartTarget(
            part_id=part.id,
            name_zh=part.name_zh,
            reason=shared or _part_reason(state, attacker, target, part, melee=melee),
        )
        for part in sorted(target.parts, key=lambda p: p.id)
    )


def check_target_part(state: BattleState, action: Action) -> str | None:
    """``target_part`` 不合法的原因（繁體中文）；沒有帶或可以選時為 ``None``。"""
    part_id = _requested_part(action)
    if part_id is None:
        return None
    found = next((t for t in part_targets(state, action) if t.part_id == part_id), None)
    if found is None:
        return f"目標沒有部位「{part_id}」"
    if found.reason is not None:
        return f"不能打「{found.name_zh}」：{PART_REASON_ZH[found.reason]}"
    return None


def _requested_part(action: Action) -> str | None:
    if isinstance(action, (Attack, UseSkill)):
        return action.target_part
    return None


def _action_reason(
    state: BattleState, attacker: UnitState, target: UnitState, action: Attack | UseSkill
) -> tuple[PartReason | None, bool]:
    """整個動作不能選部位的原因（``None``＝可以），以及這次攻擊算不算近戰（背後條件用）。"""
    if attacker.is_summon:
        return "summon", False
    if isinstance(action, Attack):
        if natural_charge(state.ruleset, attacker) is not None:
            return "charge_attack", False
        return None, weapon_profile(state, attacker).melee
    return _skill_reason(state, attacker, target, action)


def _skill_reason(
    state: BattleState, attacker: UnitState, target: UnitState, action: UseSkill
) -> tuple[PartReason | None, bool]:
    if action.copy_cast is not None and action.copy_cast.target_part is not None:
        return "copy_cast", False
    skill = _effective_skill(state, attacker, action)
    if skill is None or skill.shape.type != "single":
        return "area_skill", False
    if not _damages(state, skill, enemy=target.team is not attacker.team):
        return "no_damage", False
    return None, skill_profile(state, attacker, skill).melee


def _effective_skill(state: BattleState, unit: UnitState, action: UseSkill) -> SkillDef | None:
    """結算時實際用的技能（戰場變奏、修正規則的變形之後；同 ``interpreter.use_skill``）。"""
    try:
        skill = state.ruleset.skill_def(action.skill_id)
    except KeyError:
        return None
    skill, _variant = varied_skill(state, unit, skill, target_point(state, action))
    return modifiers.shaped_skill(state, unit, skill)


def _damages(state: BattleState, skill: SkillDef, *, enemy: bool) -> bool:
    return any(
        e.type == "damage" and (e.affects == "all" or (enemy and e.affects == "enemies"))
        for e in resolve_effects(state, skill)
    )


def _part_reason(
    state: BattleState, attacker: UnitState, target: UnitState, part: BossPart, *, melee: bool
) -> PartReason | None:
    if part.id in target.broken_parts:
        return "broken"
    if part.exposed_in and current_phase_id(target) not in part.exposed_in:
        return "not_exposed"
    match part.reach:
        case "any":
            return None
        case "behind":
            return None if melee and attacker.xy == back_xy(target) else "need_behind"
        case "high_or_far":
            return None if _high_or_far(state, attacker, target) else "need_high_or_far"
        case "disabled":
            disabled = any(target.has_status(s) for s in DISABLED_STATUSES)
            return None if disabled else "need_disabled"


def _high_or_far(state: BattleState, attacker: UnitState, target: UnitState) -> bool:
    higher = state.tile(*attacker.xy).height - state.tile(*target.xy).height >= 1
    return higher or manhattan(attacker.xy, target.xy) > FAR_BEYOND
