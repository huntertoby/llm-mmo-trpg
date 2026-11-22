"""重擲（SK-3 原語 ``reroll``，``docs/design/06-技能.md`` 6.38 第 12 點）的純查詢。

重擲只限反應技（唯一的效果、形狀 ``self``），兩個反應事件：

- ``ally_missed_roll``：``core.reroll_ally_range`` 格內（單位距離）的隊友攻擊敵人、命中骰沒中時
  （``attack_rolled`` 之前），讓他重擲一次、取**較好的**。依單位 ID 找第一個願意的隊友。
- ``enemy_hit_roll``：敵人的攻擊命中骰命中你時（``attack_rolled`` 之前、守護者攔截與傷害之前），
  逼他重擲一次、取**較差的**。

結算在 :func:`trpg.engine.reactions.reroll_attack`（普攻 ``_attack_once`` 與技能
``Cast.roll_one`` 擲完命中骰、發 ``attack_rolled`` 之前呼叫）。每輪次數、代價、冷卻照一般反應技；
預覽不重擲（強制結果不變），改由 :func:`possible_rerolls` 列出可能的重擲與重擲後的命中率。
全程只從戰鬥的 ``Rng`` 取亂數（重擲就是再呼叫一次 ``roll_attack``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from trpg.content.skills import REROLL
from trpg.engine.gear.reactions import reaction_available
from trpg.engine.ids import PRONE
from trpg.engine.rules.combat import AttackRoll
from trpg.engine.rules.footprint import unit_dist
from trpg.engine.rules.statuses import skip_turn_status
from trpg.engine.skills.targeting import reaction_problem
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "ALLY_MISSED_ROLL",
    "ENEMY_HIT_ROLL",
    "Keep",
    "RerollInfo",
    "kept_roll",
    "possible_rerolls",
    "reroll_helpers",
]

ALLY_MISSED_ROLL = "ally_missed_roll"
ENEMY_HIT_ROLL = "enemy_hit_roll"

type Keep = Literal["better", "worse"]


@dataclass(frozen=True, slots=True)
class RerollInfo:
    """預覽用：``unit_id`` 可以用反應技 ``skill_id`` 讓 ``target_id`` 這一下的命中骰重擲。

    ``keep``：``better``（我方隊友讓你重擲）或 ``worse``（對方逼你重擲）；``hit_chance`` 是重擲後
    的命中率（取較好＝1 − 失手率²；取較差＝命中率²）；``auto``：自動反應（``prompt`` 時要對方決定，
    不一定會用）。"""

    unit_id: str
    skill_id: str
    target_id: str
    keep: Keep
    hit_chance: Fraction
    auto: bool


def _key(roll: AttackRoll) -> tuple[bool, bool, int]:
    return (roll.crit, roll.hit, roll.total)


def kept_roll(keep: Keep, first: AttackRoll, second: AttackRoll) -> tuple[AttackRoll, bool]:
    """依 ``keep`` 取較好或較差的一次（比暴擊、命中、總值；相同時留第一次）。回傳（採用的那次,
    是不是第二次）。"""
    better = _key(second) > _key(first)
    worse = _key(second) < _key(first)
    take_second = better if keep == "better" else worse
    return (second, True) if take_second else (first, False)


def _reroll_skill(state: BattleState, unit: UnitState, event: str) -> tuple[str, bool] | None:
    """``unit`` 第一條事件為 ``event``、目前可用的重擲反應技（技能 ID, 是不是自動）；沒有就
    ``None``。只做不需要 ``Ctx`` 的檢查（深度上限在結算時才查）。"""
    if not unit.alive or skip_turn_status(state.ruleset, unit) is not None:
        return None
    if unit.has_status(PRONE):  # 倒地中不能反應（KD-1，05 5.13 第 1 點）
        return None
    for rule in unit.reactions:
        if rule.mode == "off" or rule.when.event != event or rule.reaction not in unit.skills:
            continue
        skill = state.ruleset.skill_def(rule.reaction)
        if not any(e.type == REROLL for e in skill.effects):
            continue
        if not reaction_available(state.ruleset.core, unit, rule.reaction):
            continue
        if reaction_problem(state, unit, skill) is not None:
            continue
        return skill.id, rule.mode == "auto"
    return None


def reroll_helpers(state: BattleState, attacker: UnitState) -> list[UnitState]:
    """「隊友擲失手時」可能出手的隊友：同陣營、不是攻擊者自己、``core.reroll_ally_range`` 格內，
    依單位 ID。"""
    reach = state.ruleset.core.reroll_ally_range
    return [
        u
        for u in state.units_sorted()
        if u.id != attacker.id
        and u.alive
        and u.team is attacker.team
        and unit_dist(u, attacker) <= reach
    ]


def possible_rerolls(
    state: BattleState, attacker: UnitState, target: UnitState, hit_chance: Fraction
) -> tuple[RerollInfo, ...]:
    """``attacker`` 打 ``target`` 時可能發生的重擲（預覽用；不取亂數、不改狀態）：目標的「敵人擲中
    你時」與攻擊者身旁隊友的「隊友擲失手時」（各取第一個可用的）。"""
    if target.team is attacker.team:
        return ()
    found: list[RerollInfo] = []
    worse = _reroll_skill(state, target, ENEMY_HIT_ROLL)
    if worse is not None:
        found.append(RerollInfo(target.id, worse[0], attacker.id, "worse", hit_chance**2, worse[1]))
    for helper in reroll_helpers(state, attacker):
        better = _reroll_skill(state, helper, ALLY_MISSED_ROLL)
        if better is not None:
            chance = 1 - (1 - hit_chance) ** 2
            found.append(RerollInfo(helper.id, better[0], attacker.id, "better", chance, better[1]))
            break
    return tuple(found)
