"""種族技的 AI 使用條件（Phase 3R-2，``docs/design/07-角色成長.md`` 7.7）。

效用 AI 的評分（``preview`` 加權）不認識種族技，所以種族技走一條獨立的「條件式」路徑：每個回合
開始（還有 AP 時）先問 :func:`race_ai_action`——有合法的種族技、且符合下面的使用條件就用，沒有才
走一般評分。每種效果一個計分函式（分數 > 0 才用；同分取列舉順序在前的，所以是確定性的）：

- ``bonus_move``（應變）：現在打不到任何敵人，多走的格數（效果的 ``amount``）剛好夠走到射程內；
- ``conceal_self``（林隱）、``immovable``（穩若磐石）、``create_surface`` 自身（炎印）：敵人逼近
  （各自的格數）且還留有行動 AP；
- ``decoy``（舊狐族的狐火誘餌，#138 退役；效果與計分保留給舊紀錄與自訂種族）：敵人逼近、場上沒有
  自己的誘餌；放在離敵人最遠的合法格；
- ``leap``（獸耳族的獸躍，#138）：跳上 **更高** 的格子、而且落地後打得到敵人才用（主動找高處）；
  分數＝高度差 × ``leap_rise_points`` ＋ 落地後打得到的敵人數 ＋ 越近越好的小加分。
  平移、往下不走條件式路徑（一般評分仍可能把它當成 1 AP 的位移選來用）；
- ``push``（龍息震退）：錐形內有敵人、沒有友方；把敵人推進岩漿或深淵的方向加分；
- ``pull``（拋錨）：只拉遠程或法術的敵人（近戰敵人自己會走過來）；
- ``restore_choice``（過充）：耐力或法力偏低且缺口夠大時，回復缺得最多的；
- ``hurl_object``（蠻力投擲）：只丟會爆炸的物件、落點已有火焰、爆炸範圍內有敵無友；
- ``create_surface`` 方陣（潮息）：方陣內敵人夠多、沒有友方。

門檻與分數在 ``content/ai_profiles.yaml`` 的 ``heuristics.race``（HC-4c；引擎從
``state.ruleset.ai`` 讀）。

這些只是「合理的使用時機」，不追求最佳；種族勝率由平衡階段的模擬監看（7.7）。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.environment import RaceAiRules
from trpg.engine.actions import UseRaceSkill
from trpg.engine.ids import DECOY_TAG
from trpg.engine.race.skills import race_skill_actions, race_skill_of
from trpg.engine.rules.combat import attack_problem, attack_reach
from trpg.engine.rules.footprint import dist_to, unit_dist
from trpg.engine.rules.movement import is_deadly
from trpg.engine.skills import shapes
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Surface

__all__ = ["RACE_EFFECT_SCORERS", "RIDER_ONLY_EFFECTS", "race_ai_action"]

type _Scorer = Callable[[BattleState, UnitState, UseRaceSkill], int]


def _enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    return [u for u in state.living_units() if u.team is not unit.team and not u.is_summon]


def _nearest(state: BattleState, unit: UnitState) -> int | None:
    distances = [unit_dist(unit, e) for e in _enemies(state, unit)]
    return min(distances) if distances else None


def _rules(state: BattleState) -> RaceAiRules:
    return state.ruleset.ai.race


def _near_score(limit: Callable[[RaceAiRules], int]) -> _Scorer:
    """敵人在 ``limit(規則)`` 格內、且用完後還能行動時 1 分。"""

    def score(state: BattleState, unit: UnitState, _a: UseRaceSkill) -> int:
        rules = _rules(state)
        nearest = _nearest(state, unit)
        return int(
            nearest is not None and nearest <= limit(rules) and unit.ap >= rules.min_ap_after
        )

    return score


def _adapt_score(state: BattleState, unit: UnitState, _a: UseRaceSkill) -> int:
    enemies = _enemies(state, unit)
    if not enemies or unit.ap < _rules(state).min_ap_after:
        return 0
    if any(attack_problem(state, unit, e) is None for e in enemies):
        return 0  # 現在就打得到，不必多走
    skill = race_skill_of(state, unit)
    assert skill is not None
    extra = skill.effects[0].amount or 0  # 第一個效果是 bonus_move 才會到這裡；多走的格數
    gap = min(unit_dist(unit, e) for e in enemies) - attack_reach(state, unit)
    return int(unit.move_points < gap <= unit.move_points + extra)


def _decoy_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    skill = race_skill_of(state, unit)
    assert skill is not None
    decoy = next(e for e in skill.effects if e.type == "decoy")  # 第一個效果是 decoy 才會到這裡
    nearest = _nearest(state, unit)
    too_far = nearest is None or nearest > (decoy.ai_trigger_range or 0)
    if too_far or unit.ap < _rules(state).min_ap_after:
        return 0
    if any(u.owner_id == unit.id and u.has_tag(DECOY_TAG) for u in state.living_units()):
        return 0  # 已經有一個誘餌
    assert action.target_pos is not None
    xy = (action.target_pos.x, action.target_pos.y)
    gaps = [dist_to(e, xy) for e in _enemies(state, unit)]
    return min(gaps) + 1


def _push_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    skill = race_skill_of(state, unit)
    assert skill is not None and action.direction is not None
    cells = set(shapes.cone_tiles(state, unit.xy, action.direction, skill.shape.size or 0))
    dx, dy = shapes.DIRECTIONS[action.direction]
    rules = _rules(state)
    score = 0
    for other in state.living_units():
        if other.id == unit.id or other.xy not in cells:
            continue
        if other.team is unit.team:
            return 0  # 不推到自己人
        score += rules.push_enemy_points
        behind = (other.xy[0] + dx, other.xy[1] + dy)  # 6R-1：地圖邊外不查（原本越界會出錯）
        if state.in_bounds(*behind) and is_deadly(state, behind):
            score += rules.push_deadly_points  # 推進岩漿或深淵
    return score


def _pull_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    assert action.target_id is not None
    target = state.units[action.target_id]
    if target.weapon.is_melee or target.is_summon:
        return 0
    rules = _rules(state)
    low = target.hp * 1000 <= target.max_hp * rules.pull_low_hp_permille
    return 1 + (rules.pull_low_hp_points if low else 0)


def _leap_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    if unit.ap < _rules(state).min_ap_after:
        return 0
    enemies = _enemies(state, unit)
    if not enemies:
        return 0
    assert action.target_pos is not None
    dest = (action.target_pos.x, action.target_pos.y)
    rise = state.tile(*dest).height - state.tile(*unit.xy).height
    if rise < 1:
        return 0
    landed = unit.clone()
    landed.pos = action.target_pos
    hits = sum(1 for e in enemies if attack_problem(state, landed, e) is None)
    if hits == 0:
        return 0  # 跳上去打不到人＝白花 1 AP
    skill = race_skill_of(state, unit)
    assert skill is not None
    reach = skill.shape.range if isinstance(skill.shape.range, int) else 0
    return rise * _rules(state).leap_rise_points + hits + (reach + 1 - dist_to(unit, dest))


def _restore_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    current, maximum = (
        (unit.stamina, unit.max_stamina)
        if action.choice == "stamina"
        else (unit.mana, unit.max_mana)
    )
    deficit = (maximum - current) // state.ruleset.core.quantity_scale  # X10-2a：換算前的單位
    rules = _rules(state)
    low = maximum > 0 and current * 1000 <= maximum * rules.restore_low_permille
    return deficit if low and deficit >= rules.restore_min_deficit else 0


def _hurl_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    assert action.target_object_id is not None and action.target_pos is not None
    obj = state.objects[action.target_object_id]
    definition = state.object_def(obj)
    dest = (action.target_pos.x, action.target_pos.y)
    if definition.explosion is None or state.tile(*dest).surface is not Surface.FIRE:
        return 0
    radius = definition.explosion.radius
    near = [u for u in state.living_units() if dist_to(u, dest) <= radius]
    if any(u.team is unit.team for u in near):
        return 0
    return len(near)


def _surface_score(state: BattleState, unit: UnitState, action: UseRaceSkill) -> int:
    skill = race_skill_of(state, unit)
    assert skill is not None
    if skill.shape.type == "self":
        if state.tile(*unit.xy).surface is not Surface.NONE:
            return 0
        return _near_score(lambda r: r.surface_near)(state, unit, action)
    assert action.target_pos is not None
    cells = set(shapes.square3_tiles(state, (action.target_pos.x, action.target_pos.y)))
    inside = [u for u in state.living_units() if u.xy in cells]
    if any(u.team is unit.team for u in inside):
        return 0
    return len(inside) if len(inside) >= _rules(state).min_cluster else 0


RACE_EFFECT_SCORERS: dict[str, _Scorer] = {
    "bonus_move": _adapt_score,
    "conceal_self": _near_score(lambda r: r.conceal_near),
    "decoy": _decoy_score,
    "push": _push_score,
    "pull": _pull_score,
    "immovable": _near_score(lambda r: r.immovable_near),
    "restore_choice": _restore_score,
    "hurl_object": _hurl_score,
    "create_surface": _surface_score,
    "leap": _leap_score,
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
