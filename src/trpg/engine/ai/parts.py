"""頭目部位的 AI（PB-1b；``docs/design/05-戰鬥.md`` 5.12.2 第 11 點、``PhasePB-1計畫.md`` 5）。

- **隊友與影子挑部位**（R8、R9）：玩家方（``Team.ALLY``）由效用 AI 控制、不是召喚物的單位，對「目標
  有部位」的普攻與單體技能候選，另外產生每個能選的部位變體（:func:`part_variants`；依部位 ID）。
  目標沒有部位時什麼都不產生，所以沒有部位的戰鬥候選清單逐字不變。
- **部位分**（:func:`part_score`）：破壞效果價值（``on_break`` 各項在 ``parts`` 價值表的值相加）
  × 進度比例（預覽「最少後果」裡這個部位扣到的血 ÷ 部位剩餘血量，上限 1）；這一下「最多後果」能破、
  而且破了能封住頭目下一招或打斷蓄力時，再加 ``priority_bonus``。
- **頭目護背**（D12）：有 ``reach: behind`` 的部位、還沒破、剩餘血量 ≤ 部位最大血量 ×
  ``near_break_permille``‰ 時，位置價值裡「背對攻擊者」的扣分多加 ``guard_back_bonus``
  （:func:`guard_back_extra`，由 ``position._facing_terms`` 讀）。
- **繞背**（PB-1b2）：玩家方近戰、不是召喚物的單位，站在「頭目背後格」，而且頭目有「從背後」
  才打得到、目前階段已露出、還沒破的部位時，位置價值加 ``circle_back_bonus``（每名這樣的頭目一次；
  :func:`circle_back_extra`，由 ``position._facing_terms`` 讀）。移動候選照位置價值排序，所以走得到
  背後格時那一格自然加分；藉機攻擊、危險表面、強招預告範圍照一般站位扣分。

全部是確定性的純查詢；數值在 ``content/ai_profiles.yaml`` 的 ``parts:``（占位，NW-3 開放後由
使用者調）。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import AiWeights, PartAiRules
from trpg.content.parts import (
    BossPart,
    InterruptChargeBreak,
    SealSkillBreak,
    max_part_hp,
)
from trpg.content.skills import CHARGING
from trpg.engine.actions import Action, Attack, UseSkill
from trpg.engine.events import EventBase, PartBroken, PartDamaged
from trpg.engine.part_breaks import live_part
from trpg.engine.parts import current_phase_id, part_targets
from trpg.engine.rules.facing import is_behind
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skills.targeting import resource_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Team

__all__ = [
    "circle_back_extra",
    "guard_back_extra",
    "part_score",
    "part_variants",
    "picks_parts",
]

_PERMILLE = 1000


def picks_parts(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 會不會考慮打部位：玩家方、不是召喚物（R9），而且場上有帶部位的單位。"""
    if unit.is_summon or unit.team is not Team.ALLY:
        return False
    return any(u.parts for u in state.units.values())


def part_variants(state: BattleState, action: Action) -> tuple[Attack | UseSkill, ...]:
    """``action``（沒帶部位的普攻或技能）對目標每個能選的部位的變體（依部位 ID）。"""
    if not isinstance(action, Attack | UseSkill) or action.target_part is not None:
        return ()
    return tuple(
        action.model_copy(update={"target_part": t.part_id})
        for t in part_targets(state, action)
        if t.ok
    )


def part_score(
    state: BattleState,
    action: Attack | UseSkill,
    min_events: tuple[EventBase, ...],
    max_events: tuple[EventBase, ...],
    rules: PartAiRules,
) -> Fraction:
    """部位變體在本體分之外多加的分數（R8；見模組說明）。"""
    target = None if action.target_id is None else state.units.get(action.target_id)
    part = None if target is None else live_part(target, action.target_part)
    if target is None or part is None:
        return Fraction(0)
    remaining = target.part_hp.get(part.id, 0)
    if remaining <= 0:
        return Fraction(0)
    dealt = sum(
        e.amount
        for e in min_events
        if isinstance(e, PartDamaged) and e.target_id == target.id and e.part_id == part.id
    )
    score = break_value(part, rules) * min(Fraction(1), Fraction(dealt, remaining))
    breaks = any(
        isinstance(e, PartBroken) and e.target_id == target.id and e.part_id == part.id
        for e in max_events
    )
    if breaks and (_seals_next_skill(state, target, part) or _interrupts(target, part)):
        score += rules.priority_bonus
    return score


def break_value(part: BossPart, rules: PartAiRules) -> int:
    """破壞效果的價值：``on_break`` 各項在價值表的值相加。"""
    return sum(rules.value_of(e.type) for e in part.on_break)


def _seals_next_skill(state: BattleState, boss: UnitState, part: BossPart) -> bool:
    """破了會封住頭目「下一招」：封的招在目前技能組、還沒封、冷卻外、法力等資源夠。"""
    for spec in part.on_break:
        if not isinstance(spec, SealSkillBreak):
            continue
        if spec.skill not in boss.skills or spec.skill in boss.sealed_skills:
            continue
        try:
            skill = state.ruleset.skill_def(spec.skill)
        except KeyError:
            continue
        if resource_problem(state, boss, skill) is None:
            return True
    return False


def _interrupts(boss: UnitState, part: BossPart) -> bool:
    """破了會打斷正在蓄力的招：``interrupt_charge``，或 ``seal_skill`` 封的正是蓄力中的招。"""
    charging = boss.get_status(CHARGING)
    if charging is None:
        return False
    return any(
        isinstance(spec, InterruptChargeBreak)
        or (isinstance(spec, SealSkillBreak) and spec.skill == charging.skill_id)
        for spec in part.on_break
    )


def guard_back_extra(unit: UnitState, w: AiWeights) -> int:
    """頭目背後的部位快破時，「背對攻擊者」多扣的分數（沒有部位的單位一律 0）。"""
    if not unit.parts or not w.guard_back_bonus:
        return 0
    for part in unit.parts:
        if part.reach != "behind" or part.id in unit.broken_parts:
            continue
        full = max_part_hp(unit.max_hp, part)
        if unit.part_hp.get(part.id, full) * _PERMILLE <= full * w.near_break_permille:
            return w.guard_back_bonus
    return 0


def circle_back_extra(unit: UnitState, w: AiWeights, enemies: list[UnitState]) -> int:
    """繞背（PB-1b2）：``unit`` 站在幾名「背後有能打的部位」的頭目背後格 × ``circle_back_bonus``。

    只算玩家方、近戰、不是召喚物的單位（同 :func:`picks_parts` 與背刺的近戰判斷）；頭目要有
    ``reach: behind``、目前階段已露出、還沒破的部位。沒有部位的戰鬥一律 0。"""
    if not w.circle_back_bonus or unit.is_summon or unit.team is not Team.ALLY:
        return 0
    if not unit.weapon.is_melee:
        return 0
    return w.circle_back_bonus * sum(
        1
        for e in enemies
        if e.parts
        and manhattan(unit.xy, e.xy) == 1
        and is_behind(unit.xy, e)
        and _open_behind_part(e)
    )


def _open_behind_part(boss: UnitState) -> bool:
    """頭目有沒有「從背後」才打得到、目前階段已露出、還沒破的部位。"""
    phase = current_phase_id(boss)
    return any(
        part.reach == "behind"
        and part.id not in boss.broken_parts
        and (not part.exposed_in or phase in part.exposed_in)
        for part in boss.parts
    )
