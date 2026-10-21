"""守護隊友、換位、瞄準的 AI（Phase 3-21a，最簡單的近似；係數在 ``content/ai_profiles.yaml`` 的
``basic:``）。條件不成立一律 0 分，所以平常的行為不變；數值是平衡階段的初值。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from trpg.content.environment import BasicActionAiRules
from trpg.engine.preview import Preview
from trpg.engine.rules.geometry import manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = ["aim_bonus", "guard_bonus", "swap_score"]

_PERMILLE = 1000


def _nearest_enemy(state: BattleState, unit: UnitState, xy: tuple[int, int]) -> int | None:
    dists = [manhattan(xy, e.xy) for e in state.living_units() if e.team is not unit.team]
    return min(dists) if dists else None


def _hp_permille(unit: UnitState) -> int:
    return unit.hp * _PERMILLE // max(1, unit.max_hp)


def guard_bonus(
    state: BattleState, unit: UnitState, ally: UnitState, rules: BasicActionAiRules
) -> Fraction:
    """守護相鄰隊友比守護自己多出的分數（隊友血量低且被敵人威脅、自己撐得住時）。"""
    if unit.speed == 0 or _hp_permille(unit) < rules.guard_self_hp_permille:
        return Fraction(0)  # 不能移動的單位（木樁、圖騰）維持原本的行為
    if _hp_permille(ally) >= rules.guard_ally_hp_permille:
        return Fraction(0)
    near = _nearest_enemy(state, ally, ally.xy)
    if near is None or near > rules.guard_threat_radius:
        return Fraction(0)
    return Fraction(rules.guard_points)


def swap_score(
    state: BattleState, unit: UnitState, ally: UnitState, rules: BasicActionAiRules
) -> Fraction:
    """與 ``ally`` 換位的分數：把低血量隊友換離前線，或把（較肉的）自己換上前。"""
    if _hp_permille(unit) < rules.swap_self_hp_permille:
        return Fraction(0)
    mine = _nearest_enemy(state, unit, unit.xy)
    theirs = _nearest_enemy(state, unit, ally.xy)
    if mine is None or theirs is None or theirs >= mine or theirs > rules.swap_threat_radius:
        return Fraction(0)  # 隊友不在更前面，或根本沒有被敵人逼近
    rescue = _hp_permille(ally) < rules.swap_rescue_hp_permille
    tank = unit.max_hp * _PERMILLE >= ally.max_hp * rules.swap_tank_ratio_permille
    return Fraction(rules.swap_points if rescue or tank else 0)


def aim_bonus(
    state: BattleState,
    unit: UnitState,
    attacks: Sequence[tuple[Fraction, Preview]],
    rules: BasicActionAiRules,
) -> Fraction:
    """瞄準的分數：AP 剛好夠「瞄準 ＋ 一個昂貴的攻擊」，而其中命中率偏低、有收益的攻擊分數最高者
    ＋ ``aim_points``；沒有這樣的攻擊時 0。``attacks`` 為（分數, 預覽）。"""
    core = state.ruleset.core
    best = Fraction(0)
    for score, preview in attacks:
        cost = preview.ap_cost
        if score <= 0 or cost is None or cost < rules.aim_min_attack_ap:
            continue
        if unit.ap != core.aim_ap_cost + cost:
            continue
        chance = _lowest_hit_chance(preview)
        if chance is None or chance * _PERMILLE >= rules.aim_hit_permille:
            continue
        best = max(best, score)
    return best + rules.aim_points if best > 0 else Fraction(0)


def _lowest_hit_chance(preview: Preview) -> Fraction | None:
    if preview.hit_chance is not None:
        return preview.hit_chance
    chances = [t.hit_chance for t in preview.targets if not t.ally]
    return min(chances) if chances else None
