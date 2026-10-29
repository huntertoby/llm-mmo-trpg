"""種族技的 AI 使用條件（Phase 3R-2，``docs/design/07-角色成長.md`` 7.7）。

效用 AI 的評分（``preview`` 加權）不認識種族技，所以種族技走一條獨立的「條件式」路徑：每個回合
開始（還有 AP 時）先問 :func:`race_ai_action`——有合法的種族技、且符合下面的使用條件就用，沒有才
走一般評分。每種效果一個計分函式（分數 > 0 才用；同分取列舉順序在前的，所以是確定性的）：

- ``bonus_move``（應變）：現在打不到任何敵人，多 2 點移動剛好夠走到射程內；
- ``conceal_self``（林隱）、``immovable``（穩若磐石）、``create_surface`` 自身（炎印）：敵人逼近
  （7／3／2 格內）且還留有行動 AP；
- ``decoy``（狐火誘餌）：敵人逼近、場上沒有自己的誘餌；放在離敵人最遠的合法格；
- ``push``（龍息震退）：錐形內有敵人、沒有友方；把敵人推進岩漿或深淵的方向加分；
- ``pull``（拋錨）：只拉遠程或法術的敵人（近戰敵人自己會走過來）；
- ``restore_choice``（過充）：耐力或法力不到一半且缺口 ≥ 6，回復缺得最多的；
- ``hurl_object``（蠻力投擲）：只丟會爆炸的物件、落點已有火焰、爆炸範圍內有敵無友；
- ``create_surface`` 方陣（潮息）：方陣內至少 2 個敵人、沒有友方。

這些只是「合理的使用時機」，不追求最佳；種族勝率由平衡階段的模擬監看（7.7）。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.engine.actions import UseRaceSkill
from trpg.engine.ids import DECOY_TAG
from trpg.engine.race_skills import race_skill_actions, race_skill_of
from trpg.engine.rules.combat import attack_problem, attack_reach
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.movement import is_deadly
from trpg.engine.skills import shapes
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface

__all__ = ["RACE_EFFECT_SCORERS", "RIDER_ONLY_EFFECTS", "race_ai_action"]

_MIN_AP_AFTER = 2
"""用完種族技後還要能行動（一般動作 1 AP）：回合開始 AP 至少這麼多才用需要「接著行動」的種族技。"""
_RESTORE_MIN_DEFICIT = 6
_MIN_CLUSTER = 2

type _Scorer = Callable[[BattleState, UnitState, UseRaceSkill], int]


def _enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    return [u for u in state.living_units() if u.team is not unit.team and not u.is_summon]


def _nearest(state: BattleState, unit: UnitState) -> int | None:
    distances = [manhattan(unit.xy, e.xy) for e in _enemies(state, unit)]
    return min(distances) if distances else None


def _near_score(limit: int) -> _Scorer:
    """敵人在 ``limit`` 格內、且用完後還能行動時 1 分。"""

    def score(state: BattleState, unit: UnitState, _a: UseRaceSkill) -> int:
        nearest = _nearest(state, unit)
        return int(nearest is not None and nearest <= limit and unit.ap >= _MIN_AP_AFTER)

    return score


def _adapt_score(state: BattleState, unit: UnitState, _a: UseRaceSkill) -> int:
    enemies = _enemies(state, unit)
    if not enemies or unit.ap < _MIN_AP_AFTER:
        return 0
    if any(attack_problem(state, unit, e) is None for e in enemies):
        return 0  # 現在就打得到，不必多走
    gap = min(manhattan(unit.xy, e.xy) for e in enemies) - attack_reach(state, unit)
    return int(unit.move_points < gap <= unit.move_points + 2)


def _decoy_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    skill = race_skill_of(state, unit)
    assert skill is not None
    decoy = next(e for e in skill.effects if e.type == "decoy")  # 第一個效果是 decoy 才會到這裡
    nearest = _nearest(state, unit)
    if nearest is None or nearest > (decoy.ai_trigger_range or 0) or unit.ap < _MIN_AP_AFTER:
        return 0
    if any(u.owner_id == unit.id and u.has_tag(DECOY_TAG) for u in state.living_units()):
        return 0  # 已經有一個誘餌
    assert action.target_pos is not None
    xy = (action.target_pos.x, action.target_pos.y)
    gaps = [manhattan(xy, e.xy) for e in _enemies(state, unit)]
    return min(gaps) + 1


def _push_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    skill = race_skill_of(state, unit)
    assert skill is not None and action.direction is not None
    cells = set(shapes.cone_tiles(state, unit.xy, action.direction, skill.shape.size or 0))
    dx, dy = shapes.DIRECTIONS[action.direction]
    score = 0
    for other in state.living_units():
        if other.id == unit.id or other.xy not in cells:
            continue
        if other.team is unit.team:
            return 0  # 不推到自己人
        score += 2
        if is_deadly(state, (other.xy[0] + dx, other.xy[1] + dy)):
            score += 3  # 推進岩漿或深淵
    return score


def _pull_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    assert action.target_id is not None
    target = state.units[action.target_id]
    if target.weapon.is_melee or target.is_summon:
        return 0
    return 1 + (2 if target.hp * 2 <= target.max_hp else 0)


def _restore_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    current, maximum = (
        (unit.stamina, unit.max_stamina)
        if action.choice == "stamina"
        else (unit.mana, unit.max_mana)
    )
    deficit = maximum - current
    low = maximum > 0 and current * 2 <= maximum
    return deficit if low and deficit >= _RESTORE_MIN_DEFICIT else 0


def _hurl_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    assert action.target_object_id is not None and action.target_pos is not None
    obj = state.objects[action.target_object_id]
    definition = state.object_def(obj)
    dest = (action.target_pos.x, action.target_pos.y)
    if definition.explosion is None or state.tile(*dest).surface is not Surface.FIRE:
        return 0
    radius = definition.explosion.radius
    near = [u for u in state.living_units() if manhattan(u.xy, dest) <= radius]
    if any(u.team is unit.team for u in near):
        return 0
    return len(near)


def _surface_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    skill = race_skill_of(state, unit)
    assert skill is not None
    if skill.shape.type == "self":
        if state.tile(*unit.xy).surface is not Surface.NONE:
            return 0
        return _near_score(2)(state, unit, action)
    assert action.target_pos is not None
    cells = set(shapes.square3_tiles(state, (action.target_pos.x, action.target_pos.y)))
    inside = [u for u in state.living_units() if u.xy in cells]
    if any(u.team is unit.team for u in inside):
        return 0
    return len(inside) if len(inside) >= _MIN_CLUSTER else 0


RACE_EFFECT_SCORERS: dict[str, _Scorer] = {
    "bonus_move": _adapt_score,
    "conceal_self": _near_score(7),
    "decoy": _decoy_score,
    "push": _push_score,
    "pull": _pull_score,
    "immovable": _near_score(3),
    "restore_choice": _restore_score,
    "hurl_object": _hurl_score,
    "create_surface": _surface_score,
}


RIDER_ONLY_EFFECTS = frozenset({"ignore_opportunity_attack"})
"""不單獨決定「要不要用」的效果類型：只作為同一招第一個效果的附帶效果（應變的「移動不觸發藉機
攻擊」）。AI 依第一個效果的計分函式決定；其餘類型必須在 :data:`RACE_EFFECT_SCORERS` 有計分函式
（``primitive_coverage`` 檢查，且內建種族不得以附帶效果開頭）。"""


def race_ai_action(state: BattleState, unit: UnitState) -> UseRaceSkill | None:
    """``unit`` 此刻要不要用種族技；要的話回傳分數最高的合法動作（同分取列舉順序在前的）。"""
    if unit.race is None or unit.is_summon or unit.has_tag(DECOY_TAG):
        return None
    skill = race_skill_of(state, unit)
    if skill is None or skill.effects[0].type in RIDER_ONLY_EFFECTS:
        return None
    scorer = RACE_EFFECT_SCORERS[skill.effects[0].type]
    best: UseRaceSkill | None = None
    best_score = 0
    for action in race_skill_actions(state, unit):
        score = scorer(state, unit, action)
        if score > best_score:
            best, best_score = action, score
    return best
