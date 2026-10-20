"""複合技能的四種即時第二段（Phase 3F-4a，``docs/design/06-技能.md`` 6.23）：選取與觸發的輔助函式。

結算本身在 :mod:`trpg.engine.skills.interpreter`（``_run_second``）；這裡只放不需要施放狀態的部分：

- ``after_action``（動作 → 位移）、``on_kill``（擊殺 → 接下一段）：第二段從施放者 **目前** 的位置選
  目標。``UseSkill.followup_target`` 帶了就直接用（AI、重播）；沒帶時結算到第二段暫停
  （``Pending.kind == "followup"``），玩家以 ``Decision.followup_target`` 從
  :func:`followup_options` 挑一個。
- ``after_gather``（聚集 → 範圍打擊）：第二段以聚集點為中心
  （:func:`~trpg.engine.skills.targeting.gather_pick`）。
- ``on_hit``（命中 → 加碼段）：第二段自動對第一段命中的同一個目標（:func:`hit_pick`）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from trpg.content.skills import FOLLOWUP_CENTERED, SkillDef
from trpg.engine.actions import FollowupTarget, UseSkill
from trpg.engine.events import DamageDealt, EventBase, UnitDowned
from trpg.engine.rules.combat import AttackRoll
from trpg.engine.rules.facing import facing_between
from trpg.engine.skills.targeting import SkillArea, checked_area, selections
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, UnitId

__all__ = [
    "followup_options",
    "hit_pick",
    "hit_unit",
    "killed_enemy",
    "second_pick",
    "second_problem",
]


def _second(skill: SkillDef) -> SkillDef:
    follow = skill.followup_skill()
    assert follow is not None
    return follow


def second_pick(caster: UnitState, skill: SkillDef, target: FollowupTarget) -> UseSkill:
    """``followup_target`` → 第二段的 ``UseSkill``（從施放者目前的位置施放）；以施放者為中心的
    十字、方陣補上施放者的位置（給了別的格子時拋出 ``IllegalActionError``）。"""
    follow = _second(skill)
    pos = target.target_pos
    if follow.shape.type in FOLLOWUP_CENTERED:
        here = Pos(x=caster.xy[0], y=caster.xy[1])
        if pos is not None and pos != here:
            raise IllegalActionError(
                f"第二段以施放者 {caster.xy} 為中心：followup_target 不用指定 target_pos"
            )
        pos = here
    return UseSkill(
        unit_id=caster.id,
        skill_id=skill.id,
        target_id=target.target_id,
        target_object_id=target.target_object_id,
        target_pos=pos,
        direction=target.direction,
    )


def second_problem(
    state: BattleState, caster: UnitState, skill: SkillDef, target: FollowupTarget
) -> str | None:
    """``target`` 現在不能當第二段選取的原因（繁體中文）；合法時為 ``None``。"""
    try:
        checked_area(state, caster, _second(skill), second_pick(caster, skill, target))
    except IllegalActionError as exc:
        return f"第二段：{exc}"
    return None


def followup_options(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> list[tuple[FollowupTarget, SkillArea]]:
    """第二段從施放者目前的位置所有合法的選取與影響範圍（確定性順序，同
    :func:`~trpg.engine.skills.targeting.selections`）。"""
    return [
        (
            FollowupTarget(
                target_id=pick.target_id,
                target_object_id=pick.target_object_id,
                target_pos=pick.target_pos,
                direction=pick.direction,
            ),
            area,
        )
        for pick, area in selections(state, caster, _second(skill))
    ]


def killed_enemy(state: BattleState, caster: UnitState, events: Sequence[EventBase]) -> bool:
    """``events``（第一段的事件）中，施放者攻擊造成傷害的敵人是否倒下（同技能內 ``on_kill`` 的
    判定）。"""
    hurt = {
        e.target_id
        for e in events
        if isinstance(e, DamageDealt) and e.source_id == caster.id and e.cause == "attack"
    }
    return any(
        isinstance(e, UnitDowned)
        and e.unit_id in hurt
        and state.units[e.unit_id].team is not caster.team
        for e in events
    )


def hit_unit(
    state: BattleState, caster: UnitState, hits: Mapping[str, AttackRoll]
) -> UnitState | None:
    """第一段命中的敵人（依單位 ID 的第一個；單體技能就是被打中的目標）；沒有命中時為 ``None``。"""
    for uid in sorted(hits):
        unit = state.units[UnitId(uid)]
        if hits[uid].hit and unit.team is not caster.team:
            return unit
    return None


def hit_pick(
    state: BattleState, caster: UnitState, skill: SkillDef, target: UnitState
) -> UseSkill | None:
    """「命中 → 加碼段」的選取：對命中的同一個目標——單體選它、直線與錐形朝它的方向、以施放者為
    中心的形狀不用選；算不出方向（同一格）時為 ``None``。"""
    follow = _second(skill)
    targeting = state.ruleset.shape_def(follow.shape.type).targeting
    base = UseSkill(unit_id=caster.id, skill_id=skill.id)
    if targeting == "unit":
        return base.model_copy(update={"target_id": target.id})
    if targeting == "direction":
        facing = facing_between(caster.xy, target.xy)
        return None if facing is None else base.model_copy(update={"direction": facing})
    if targeting == "tile":
        return base.model_copy(update={"target_pos": Pos(x=caster.xy[0], y=caster.xy[1])})
    return base
