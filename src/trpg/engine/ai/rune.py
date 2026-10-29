"""刻印的 AI（Phase 3-23，最簡單的近似；係數在 ``ai_profiles.yaml`` 的 ``rune:``）：先刻再引。

- **只在有讀取技能時才刻**（:func:`has_rune_reader`）：行動者的技能中有帶 ``on_own_rune`` 條件的
  效果，或原語 ``detonate_runes``。沒有讀取技能的刻印只是白費 AP，不納入候選。
- **選位置**（:func:`rune_estimate`，不跑引擎）：影響範圍內的格子依「離最近的敵人多遠」計分——敵人
  腳下 3、相鄰 2、距離 2 為 1（敵人會停留的地方），已經有自己的符文的格子不算；沒有分數就不納入。
- **評分**（:func:`rune_gains`）：預覽事件中新刻下的符文，每格價值 ＝ ``inscribe_points`` ×
  ``damage`` 權重 × 距離比例（腳下 1000‰、相鄰 ``adjacent_permille``、距離 2 ``near_permille``）。
- **讀取加分**（:func:`read_gains`）：讀取技能打到「站在自己符文上」的敵人時，每個目標加
  ``read_points`` × ``damage`` 權重（傷害本身由預覽計算；這是對「先刻再引」的額外鼓勵）。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from trpg.content.environment import AiProfile
from trpg.content.skills import DETONATE_RUNES, INSCRIBE, SkillDef
from trpg.engine.events import EventBase, RuneInscribed, RuneRemoved
from trpg.engine.gear.enhance import rune_affixes
from trpg.engine.preview import Preview
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rune_queries import own_runes_at
from trpg.engine.state import BattleState, UnitState

__all__ = ["has_rune_reader", "is_inscribe_skill", "read_gains", "rune_estimate", "rune_gains"]

_PERMILLE = 1000
_CELL_SCORES = {0: 3, 1: 2, 2: 1}
"""格子離最近的敵人的距離 → 分數（敵人腳下 3、相鄰 2、距離 2 為 1；更遠 0）。"""


def is_inscribe_skill(skill: SkillDef) -> bool:
    return any(e.type == INSCRIBE for e in skill.effects)


def _reads_runes(skill: SkillDef) -> bool:
    """技能讀取符文：有 ``detonate_runes``，或技能／效果的條件是 ``on_own_rune``。"""
    if skill.condition is not None and skill.condition.type == "on_own_rune":
        return True
    return any(
        e.type == DETONATE_RUNES or (e.condition is not None and e.condition.type == "on_own_rune")
        for e in skill.effects
    )


def _modifier_reads_runes(skill: SkillDef) -> bool:
    """修正型被動讀取符文（Phase 3-31）：規則條件是 ``on_own_rune``，或命中後引爆符文。"""
    return any(
        (rule.condition is not None and rule.condition.type == "on_own_rune")
        or any(e.type == DETONATE_RUNES for e in rule.change.on_hit_effects or ())
        for rule in skill.modifiers
    )


def _gear_reads_runes(unit: UnitState) -> bool:
    """裝備的普攻符文詞條讀取符文（Phase 3-31）：讀取加傷或單格引爆。"""
    return bool(rune_affixes(unit, "read") or rune_affixes(unit, "detonate"))


def has_rune_reader(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 的技能中有沒有讀取符文的（包含暫時獲得的技能、修正型被動與裝備的普攻符文詞條）。"""
    rules = state.ruleset
    if _gear_reads_runes(unit):
        return True
    for sid in unit.all_skills:
        skill = rules.skill_def(sid)
        if _reads_runes(skill) or (skill.is_modifier and _modifier_reads_runes(skill)):
            return True
    return False


def _enemy_distance(state: BattleState, unit: UnitState, xy: XY) -> int | None:
    """``xy`` 離最近的敵人的曼哈頓距離；沒有敵人時 ``None``。"""
    distances = [manhattan(xy, o.xy) for o in state.living_units() if o.team is not unit.team]
    return min(distances) if distances else None


def _cell_score(distance: int | None) -> int:
    return 0 if distance is None else _CELL_SCORES.get(distance, 0)


def rune_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, tiles: Sequence[XY], origin: XY
) -> Fraction | None:
    """刻印技能選取的便宜估計：影響範圍內可刻的格子，依離敵人的距離計分的總和；沒有讀取技能或
    沒有分數時 ``None``（不納入候選）。平手以與施放者的距離判定。"""
    if not has_rune_reader(state, unit):
        return None
    score = 0
    for xy in tiles:
        if own_runes_at(state, unit.id, xy):
            continue
        score += _cell_score(_enemy_distance(state, unit, xy))
    if score <= 0:
        return None
    return Fraction(score) - Fraction(manhattan(unit.xy, origin), _PERMILLE)


def rune_gains(
    state: BattleState, actor: UnitState, events: Sequence[EventBase], profile: AiProfile
) -> Fraction:
    """預覽事件中新刻下的符文的預估收益（``state`` 為動作前的狀態）；沒有讀取技能時為 0。"""
    inscribed = [e for e in events if isinstance(e, RuneInscribed) and e.owner_id == actor.id]
    if not inscribed or not has_rune_reader(state, actor):
        return Fraction(0)
    rules = profile.rune
    gains = Fraction(0)
    for e in inscribed:
        distance = _enemy_distance(state, actor, (e.pos.x, e.pos.y))
        share = {0: _PERMILLE, 1: rules.adjacent_permille, 2: rules.near_permille}.get(
            distance if distance is not None else 99, 0
        )
        gains += Fraction(profile.weights.damage * rules.inscribe_points * share, _PERMILLE)
    return gains


def read_gains(
    state: BattleState, actor: UnitState, skill: SkillDef, p: Preview, profile: AiProfile
) -> Fraction:
    """讀取技能打到站在自己符文上的敵人的額外加分：有 ``on_own_rune`` 條件的技能看被打的敵人腳下；
    引爆看被引爆的符文格上站著的敵人（``state`` 為動作前的狀態）。"""
    if not _reads_runes(skill):
        return Fraction(0)
    points = Fraction(profile.weights.damage * profile.rune.read_points)
    count = 0
    if any(e.type == DETONATE_RUNES for e in skill.effects):
        for e in p.min_events:
            if isinstance(e, RuneRemoved) and e.reason == "detonated" and e.owner_id == actor.id:
                other = state.unit_at(e.pos.x, e.pos.y)
                count += other is not None and other.team is not actor.team
    else:
        for target in p.targets:
            other = state.units.get(target.unit_id)
            if other is not None and not target.ally and other.team is not actor.team:
                count += bool(own_runes_at(state, actor.id, other.xy))
    return points * count
