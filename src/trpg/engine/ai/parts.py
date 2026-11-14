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

- **殼縫算背後**（GB-3，GB-1c 待決 6）：AI 的背後估值（``backstab``、無聲留背、繞背、瞬步落點）
  把「貼著巨型頭目 ``counts_as_behind``、還沒破、已露出的部位格」也當成背後格
  （:func:`behind_spot`；引擎的 ``part_behind`` 同一條規則）。一格的頭目不能有綁格部位，所以結果
  和原本的 ``is_behind`` 相同。
- **巨型頭目的部位站位**（GB-3，第 7 節第 2 點）：玩家方、不是召喚物的單位，近戰貼著某個巨型頭目
  未破、已露出、近戰打得到的部位格（``melee_from: any_face`` 時貼任一面），或遠程站在射程夠、看得到
  ``reach: ranged`` 部位（噴口）某一格的位置時，位置價值加 ``giant_spot_bonus``（每名巨型頭目一次；
  :func:`giant_part_spot_extra`）。高台不另加分（高度與弓的高處射程本來就算進去）。
- **巨型頭目護面**（GB-3，D13、T18）：巨型頭目有部位剩血 ≤ ``near_break_permille`` 時，這次動作
  打到的敵人每名「貼著那個部位的格子」（``any_face`` 時貼任一面）的，多加 ``guard_face_bonus``
  （:func:`guard_face_extra`，由 ``scoring._preview_score`` 讀）。

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
from trpg.engine import modifiers
from trpg.engine.actions import Action, Attack, UseSkill
from trpg.engine.events import EventBase, PartBroken, PartDamaged
from trpg.engine.part_breaks import live_part, part_tiles
from trpg.engine.parts import current_phase_id, part_targets
from trpg.engine.rules.combat import attack_reach
from trpg.engine.rules.facing import is_behind
from trpg.engine.rules.footprint import adjacent, is_giant, nearest_tile
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.skills.targeting import resource_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Team

__all__ = [
    "behind_spot",
    "circle_back_extra",
    "giant_part_spot_extra",
    "guard_back_extra",
    "guard_face_extra",
    "part_score",
    "part_variants",
    "picks_parts",
    "silent_behind_extra",
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
        1 for e in enemies if e.parts and adjacent(unit, e) and _open_behind_at(unit.xy, e)
    )


def silent_behind_extra(
    state: BattleState, unit: UnitState, w: AiWeights, enemies: list[UnitState]
) -> int:
    """無聲留背（BS-1，#157，06 6.21.1「AI：持有無聲時留在目標背後」）：``unit`` 帶無聲（手持
    匕首類、
    近戰）時，站在幾名相鄰敵人的背後格 × ``silent_behind``——目標不會轉身，所以留在原地連續背刺比
    走開划算。敵我同一套（設計成刺客的精英也適用）；召喚物沒有修正規則，自然是 0。"""
    if not w.silent_behind or not unit.weapon.is_melee:
        return 0
    if not modifiers.silent_strike(state, unit, modifiers.ATTACK):
        return 0
    return w.silent_behind * sum(
        1 for e in enemies if adjacent(unit, e) and behind_spot(unit.xy, e)
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


def _open(boss: UnitState, part: BossPart) -> bool:
    """部位還沒破、目前階段已露出。"""
    if part.id in boss.broken_parts:
        return False
    return not part.exposed_in or current_phase_id(boss) in part.exposed_in


def _touches_part(xy: XY, boss: UnitState, part: BossPart) -> bool:
    """站在 ``xy``（一格）貼著部位的格子（``melee_from: any_face`` 時貼頭目任一面）。"""
    if part.melee_from == "any_face":
        return manhattan(nearest_tile(boss, xy), xy) == 1
    return any(manhattan(xy, t) == 1 for t in part_tiles(boss, part))


def _seam_at(xy: XY, boss: UnitState) -> bool:
    """``xy`` 貼著巨型頭目 ``counts_as_behind``、還沒破、已露出的部位格（GB-1c R4 的殼縫）。"""
    if not is_giant(boss) or not boss.parts:
        return False
    return any(
        part.counts_as_behind and part.tiles and _open(boss, part) and _touches_part(xy, boss, part)
        for part in boss.parts
    )


def behind_spot(xy: XY, enemy: UnitState) -> bool:
    """AI 估值用：近戰站在 ``xy`` 打 ``enemy`` 算不算從背後——背後格（``is_behind``），或貼著巨型頭目
    算從背後的部位格（GB-3，GB-1c 待決 6）。一格的單位＝``is_behind``。"""
    return is_behind(xy, enemy) or _seam_at(xy, enemy)


def _open_behind_at(xy: XY, boss: UnitState) -> bool:
    """繞背的條件：站在背後格而且有 ``reach: behind`` 的開著的部位，或貼著開著的殼縫（GB-3）。"""
    return (is_behind(xy, boss) and _open_behind_part(boss)) or _seam_at(xy, boss)


def giant_part_spot_extra(
    state: BattleState, unit: UnitState, w: AiWeights, enemies: list[UnitState]
) -> int:
    """巨型頭目的部位站位（GB-3，見模組說明）：每名「從這格打得到某個開著的部位」的巨型頭目
    × ``giant_spot_bonus``。近戰看近戰打得到的部位（``reach`` 不是 ``ranged``）有沒有貼著；遠程看
    ``reach: ranged`` 的部位有沒有一格在普攻射程內（含高處射程）而且看得到（巨人自己的身體不擋）。
    只算玩家方、不是召喚物的單位；沒有巨型頭目的戰鬥一律 0。"""
    if not w.giant_spot_bonus or unit.is_summon or unit.team is not Team.ALLY:
        return 0
    melee = unit.weapon.is_melee
    count = 0
    for boss in enemies:
        if not is_giant(boss) or not boss.parts:
            continue
        if any(
            _open(boss, part)
            and part.tiles
            and (
                (melee and part.reach != "ranged" and _touches_part(unit.xy, boss, part))
                or (not melee and part.reach == "ranged" and _shot_at(state, unit, boss, part))
            )
            for part in boss.parts
        ):
            count += 1
    return w.giant_spot_bonus * count


def _shot_at(state: BattleState, unit: UnitState, boss: UnitState, part: BossPart) -> bool:
    """遠程從 ``unit.xy`` 有沒有一格部位格在普攻射程內、而且看得到（同 ``parts._tile_reason``）。"""
    return any(
        manhattan(unit.xy, t) <= attack_reach(state, unit, t)
        and has_line_of_sight(state, unit.xy, t, lob=unit.weapon.lob, viewer=unit, ignore_unit=boss)
        for t in part_tiles(boss, part)
    )


def guard_face_extra(
    state: BattleState, boss: UnitState, w: AiWeights, victims: tuple[UnitState, ...]
) -> int:
    """巨型頭目護面（GB-3，D13、T18）：有部位快破（剩血 ≤ 最大 × ``near_break_permille``‰）時，
    ``victims`` 裡每名貼著那個部位格子的敵人 × ``guard_face_bonus``（一名敵人只算一次）。不是巨型
    頭目、沒有部位時一律 0。"""
    if not w.guard_face_bonus or not is_giant(boss) or not boss.parts:
        return 0
    near = [
        part
        for part in boss.parts
        if part.tiles and _open(boss, part) and _near_break(boss, part, w)
    ]
    if not near:
        return 0
    return w.guard_face_bonus * sum(
        1
        for v in victims
        if v.team is not boss.team and any(_touches_part(v.xy, boss, p) for p in near)
    )


def _near_break(unit: UnitState, part: BossPart, w: AiWeights) -> bool:
    full = max_part_hp(unit.max_hp, part)
    return unit.part_hp.get(part.id, full) * _PERMILLE <= full * w.near_break_permille
