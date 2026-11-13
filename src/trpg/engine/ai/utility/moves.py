"""效用 AI 的候選篩選：攻擊物件是否值得預覽、移動的虛擬分數、冰面滑行成本與有風險的移動。

自 :mod:`trpg.engine.ai.utility` 拆出（Phase R1c），內容未改。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import (
    AiWeights,
)
from trpg.content.maps import MAX_HEIGHT
from trpg.engine.actions import (
    Attack,
    Move,
)
from trpg.engine.ai.utility.position import _enemies, _Scene, _scene, _unit_position_value
from trpg.engine.ice_slide import path_slide_risks
from trpg.engine.ids import PRONE
from trpg.engine.infusion import template_of
from trpg.engine.rules.footprint import dist_to
from trpg.engine.rules.geometry import (
    chebyshev,
)
from trpg.engine.rules.race import fall_immune
from trpg.engine.state import BattleState, UnitState, reaction_limit
from trpg.shared.types import Pos, Surface, Team

_ALWAYS_PREVIEW_TAGS = ("explosive", "conductive", "blocks_sight")
_OBJECT_NEAR_ENEMY = 2


def worth_previewing(state: BattleState, scene: _Scene, action: Attack) -> bool:
    """攻擊物件的便宜篩選：只有可能帶來收益的物件才跑完整 ``preview``。

    - 易爆（連鎖爆炸）、導電（雷電擴散）、阻擋視線（打掉後視線改變）的物件一律評估；
    - 其他物件只在 2 格（切比雪夫距離）內有敵人時評估（橋上的敵人、掩護後的敵人、點燃後
      波及的範圍）。

    被略過的物件攻擊不會傷到敵人、不會改變行動者的位置價值，分數不會是正的，因此不影響選擇。
    攻擊單位一律評估。
    """
    if action.target_object_id is None:
        return True
    obj = state.objects[action.target_object_id]
    tags = state.ruleset.object_def(obj.kind).tags
    if any(tag in tags for tag in _ALWAYS_PREVIEW_TAGS):
        return True
    return any(chebyshev(obj.xy, e.xy) <= _OBJECT_NEAR_ENEMY for e in scene.enemies)


def virtual_move_score(
    state: BattleState,
    unit: UnitState,
    move: Move,
    w: AiWeights,
    before: Fraction,
    *,
    scene: _Scene | None = None,
) -> Fraction:
    """不跑引擎的移動分數：把行動者直接放到目的地後的位置價值 − 動作前的位置價值。

    對沒有風險的移動（:func:`is_risky_move` 為假）而言，這就是完整 ``preview`` 的分數。
    """
    moved = unit.clone()
    moved.pos = move.path[-1]
    return _unit_position_value(state, moved, w, scene) - before


def ice_slip_cost(
    state: BattleState,
    unit: UnitState,
    move: Move,
    w: AiWeights,
    points: int,
    *,
    scene: _Scene | None = None,
) -> Fraction:
    """冰面滑倒的期望代價（#123，Phase 6E-2；確定性）：路徑上每次滑行檢定（依序，前面都通過才會
    擲到）× 失敗率 ×（``points`` ＋ 終點與滑行停點的位置價值差〔下限 0〕）。沒有冰面時為 0。"""
    path = tuple((p.x, p.y) for p in move.path)
    risks = path_slide_risks(state, unit, path)
    if not risks:
        return Fraction(0)
    if scene is None:
        scene = _scene(state, unit)
    dest = unit.clone()
    dest.pos = move.path[-1]
    planned = _unit_position_value(state, dest, w, scene)
    cost = Fraction(0)
    reach = Fraction(1)
    for risk in risks:
        fallen = unit.clone()
        fallen.pos = Pos(x=risk.stop[0], y=risk.stop[1])
        lost = max(Fraction(0), planned - _unit_position_value(state, fallen, w, scene))
        cost += reach * risk.chance * (points + lost)
        reach *= 1 - risk.chance
    return cost


def reactive_enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    """可能對 ``unit`` 藉機攻擊的敵人：存活、本輪反應次數未用完、有「敵人離開相鄰格」的反應規則
    （不檢查耐力與武器，寧可多算）。相鄰以佔格算（GB-1b，巨型單位）。"""
    core = state.ruleset.core
    return [
        e
        for e in _enemies(state, unit)
        if e.reactions_used < reaction_limit(core, e)
        and any(rule.when.event == "enemy_leaves_adjacent" for rule in e.reactions)
    ]


def _detonates_on_arrival(state: BattleState, unit: UnitState, move: Move) -> bool:
    """會自爆的召喚物（爆裂傀儡，3-33e2a）：路徑上有一步走到敵人相鄰（引擎會在那一步自爆）。"""
    template = template_of(state, unit)
    if template is None or template.detonate is None:
        return False
    foes = [u for u in state.living_units() if u.team is not unit.team]
    return any(dist_to(f, (p.x, p.y)) == 1 for p in move.path[1:] for f in foes)


def is_risky_move(
    state: BattleState, unit: UnitState, move: Move, enemies: list[UnitState] | None = None
) -> bool:
    """移動是否可能有「位置改變」以外的後果（需要完整 ``preview`` 才能評分）。

    - 倒地（先站起來）；
    - 路徑上離開某個「本輪還能反應、且有藉機攻擊規則」的敵人的相鄰格（可能被藉機攻擊）；
    - 走上有進入效果的表面（燃燒、冰面滑倒檢定）；
    - 往下的落差達到墜落門檻（有「輕身」的單位不算，#138：不會摔傷）；
    - 撤離勝利條件下，我方走上出口格。
    """
    if unit.has_status(PRONE) or _detonates_on_arrival(state, unit, move):
        return True
    if enemies is None:
        enemies = reactive_enemies(state, unit)
    rules = state.ruleset
    min_drop = rules.core.fall_damage_min_drop
    if fall_immune(rules, unit):
        min_drop = MAX_HEIGHT + 1  # 輕身（#138）：往下多少層都不是風險
    objective = state.objective
    exits = objective.tiles if objective.kind == "escape" and unit.team is Team.ALLY else ()
    path = move.path
    last = len(path) - 1
    prev_height = state.tile(path[0].x, path[0].y).height
    for i, pos in enumerate(path):
        xy = (pos.x, pos.y)
        if i < last:
            nxt = (path[i + 1].x, path[i + 1].y)
            if any(dist_to(e, xy) == 1 and dist_to(e, nxt) != 1 for e in enemies):
                return True
        if i == 0:
            continue
        tile = state.tile(*xy)
        if tile.surface is not Surface.NONE and rules.surface_def(tile.surface).on_enter:
            return True
        if prev_height - tile.height >= min_drop:
            return True
        if xy in exits:
            return True
        prev_height = tile.height
    return False
