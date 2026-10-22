"""基本動作：守護、換位、瞄準（Phase 3-21a，玩法 #24；``docs/design/05-戰鬥.md`` 5.2.2）。

- **守護**（``Defend``）：沿用防禦（防禦值 +25%、到自己下回合開始），可選相鄰隊友；轉移承受的結算
  在 :func:`trpg.engine.reactions.try_intercept`，這裡只放合法性與設定；
- **換位**（``Swap``）：與相鄰我方單位互換位置（沿用 ``swap_units``；不觸發藉機攻擊，朝向不變）；
- **瞄準**（``Aim``）：下一次需要擲命中的攻擊命中加值，用掉或回合結束時失效。

所有數值在 ``core.yaml``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.engine.actions import Action, Aim, Defend, Reload, Swap, Vault
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, SwapUnitsEffect
from trpg.engine.events import GuardSet, UnitAimed, WeaponReloaded
from trpg.engine.ids import DEFENDING, PRONE
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.landing import LandingBlock, landing_problem
from trpg.engine.rules.movement import fear_blocks_step, fear_origins, is_standable
from trpg.engine.rules.statuses import is_rooted, skip_turn_status
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, UnitId

__all__ = [
    "VaultPlan",
    "adjacent_allies",
    "aim_problem",
    "do_aim",
    "do_defend",
    "do_reload",
    "do_swap",
    "guard_problem",
    "reload_problem",
    "swap_problem",
    "vault_action",
    "vault_destinations",
    "vault_plan",
    "vault_problem",
]


def adjacent_allies(state: BattleState, unit: UnitState) -> list[UnitState]:
    """與 ``unit`` 相鄰的我方單位（含召喚物；不含自己；依單位 ID）。"""
    return [
        other
        for other in state.units_sorted()
        if other.id != unit.id
        and other.alive
        and other.team is unit.team
        and manhattan(other.xy, unit.xy) == 1
    ]


def _ally_problem(state: BattleState, unit: UnitState, ally_id: UnitId | None) -> str | None:
    ally = None if ally_id is None else state.units.get(ally_id)
    if ally is None or not ally.alive:
        return f"找不到目標：{ally_id}"
    if ally.id == unit.id:
        return "不能指定自己（守護自己請不指定目標）"
    if ally.team is not unit.team:
        return f"{ally.name_zh} 不是隊友"
    if manhattan(ally.xy, unit.xy) != 1:
        return f"{ally.name_zh} 不在相鄰格"
    return None


def guard_problem(state: BattleState, unit: UnitState, ally_id: UnitId | None) -> str | None:
    """守護（含守護自己）不合法的原因；合法時 ``None``。順序：AP、已守護、隊友是否合法。"""
    cost = state.ruleset.core.defend_ap_cost
    if unit.ap < cost:
        return f"AP 不足：需要 {cost}，剩餘 {unit.ap}"
    if unit.has_status(DEFENDING):
        return "已處於守護姿態"
    if ally_id is None:
        return None
    return _ally_problem(state, unit, ally_id)


def do_defend(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Defend)
    problem = guard_problem(ctx.state, unit, action.target_id)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= ctx.core.defend_ap_cost
    execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=DEFENDING, source_id=unit.id)])
    if action.target_id is not None:
        unit.guarding_id = action.target_id
        ctx.emit(GuardSet, unit_id=unit.id, ally_id=action.target_id)


def guard_covers(ctx: Ctx, guardian: UnitState, target: UnitState) -> bool:
    """``guardian`` 現在能不能替 ``target`` 承受一次單體攻擊（守護中、仍相鄰、本輪次數未滿、
    沒有被暈眩等讓他不能行動的狀態）。"""
    return (
        guardian.guarding_id == target.id
        and guardian.has_status(DEFENDING)
        and guardian.id != target.id
        and guardian.alive
        and guardian.guard_transfers < ctx.core.guard_transfers_per_round
        and manhattan(guardian.xy, target.xy) == 1
        and skip_turn_status(ctx.rules, guardian) is None
    )


def swap_problem(state: BattleState, unit: UnitState, ally_id: UnitId) -> str | None:
    """換位不合法的原因：AP、對象、任一方不能移動（定身、速度 0）、高低差會墜落。"""
    core = state.ruleset.core
    if unit.ap < core.swap_ap_cost:
        return f"AP 不足：需要 {core.swap_ap_cost}，剩餘 {unit.ap}"
    problem = _ally_problem(state, unit, ally_id)
    if problem is not None:
        return problem
    ally = state.units[ally_id]
    for mover in (unit, ally):
        if is_rooted(state.ruleset, mover):
            return f"{mover.name_zh} 被定身，不能換位"
        if mover.speed == 0:
            return f"{mover.name_zh} 不能移動，不能換位"
    drop = abs(state.tile(*unit.xy).height - state.tile(*ally.xy).height)
    if drop >= core.fall_damage_min_drop:
        return "高低差太大，不能換位"
    return None


def do_swap(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Swap)
    problem = swap_problem(ctx.state, unit, action.target_id)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= ctx.core.swap_ap_cost
    execute(
        ctx,
        [SwapUnitsEffect(source_id=unit.id, unit_id=unit.id, other_id=action.target_id)],
    )


def aim_problem(state: BattleState, unit: UnitState) -> str | None:
    """瞄準不合法的原因：已經瞄準了（不疊加）、AP 不足。"""
    if unit.aimed:
        return "已經瞄準了"
    cost = state.ruleset.core.aim_ap_cost
    if unit.ap < cost:
        return f"AP 不足：需要 {cost}，剩餘 {unit.ap}"
    return None


def do_aim(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Aim)
    problem = aim_problem(ctx.state, unit)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= ctx.core.aim_ap_cost
    unit.aimed = True
    ctx.emit(UnitAimed, unit_id=unit.id, bonus=ctx.core.aim_hit_bonus)


def reload_problem(state: BattleState, unit: UnitState) -> str | None:
    """裝填不合法的原因（Phase 3-24a2，武器動作）：武器沒有彈匣、彈匣還沒空、AP 不足。"""
    weapon = unit.weapon
    if weapon.magazine <= 0:
        return f"{weapon.name_zh}不用裝填"
    if unit.ammo > 0:
        return "彈匣還沒空，不需要裝填"
    if unit.ap < weapon.reload_ap:
        return f"AP 不足：需要 {weapon.reload_ap}，剩餘 {unit.ap}"
    return None


def do_reload(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Reload)
    problem = reload_problem(ctx.state, unit)
    if problem is not None:
        raise IllegalActionError(problem)
    weapon = unit.weapon
    unit.ap -= weapon.reload_ap
    unit.ammo = weapon.magazine
    ctx.emit(WeaponReloaded, unit_id=unit.id, ammo=unit.ammo, cost=weapon.reload_ap)


# ---------------------------------------------------------------------------
# 攀跳（Phase 3-21b）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VaultPlan:
    """驗證通過的攀跳：``kind`` 為攀爬或跳躍，``over`` 是跳躍越過的格子（攀爬為空）。"""

    kind: Literal["climb", "jump"]
    dest: XY
    over: tuple[XY, ...]


def _unit_on(state: BattleState, xy: XY) -> UnitState | None:
    return next((u for u in state.units_sorted() if u.alive and u.xy == xy), None)


def _landing_problem(state: BattleState, unit: UnitState, dest: XY) -> str | None:
    block = landing_problem(state, dest, mover=unit.id)
    if block is LandingBlock.OUT_OF_BOUNDS:
        return f"超出地圖範圍：{dest}"
    if block is LandingBlock.NOT_STANDABLE:
        return "落點不能站立"
    if block is LandingBlock.OCCUPIED:
        other = _unit_on(state, dest)
        assert other is not None
        return f"落點已有單位：{other.name_zh}"
    return None


def _climb_problem(state: BattleState, unit: UnitState, dest: XY) -> str | None:
    core = state.ruleset.core
    problem = _landing_problem(state, unit, dest)
    if problem is not None:
        return problem
    rise = state.tile(*dest).height - state.tile(*unit.xy).height
    if rise <= core.max_climb_height:
        return "這一格可以直接走上去，不需要攀爬"
    if rise > core.vault_climb_height:
        return f"太高了：高 {rise} 層（攀爬最多 {core.vault_climb_height} 層）"
    return None


def _gap_problem(state: BattleState, xy: XY) -> str | None:
    """跳躍越過的一格：必須是不可站立的缺口（深淵、岩漿），不能有單位或擋路物件。"""
    if not state.in_bounds(*xy):
        return f"超出地圖範圍：{xy}"
    tile = state.tile(*xy)
    if state.object_has_tag(*xy, "blocks_move"):
        return "中間有擋路的物件，跳不過去"
    if _unit_on(state, xy) is not None:
        return "中間有單位，跳不過去"
    if is_standable(state, xy):
        return "中間可以直接走過去，不需要跳躍"
    if not state.ruleset.terrain_def(tile.terrain).deadly:
        return "中間不是缺口（深淵、岩漿），跳不過去"
    return None


def _jump_problem(
    state: BattleState, unit: UnitState, dest: XY, over: tuple[XY, ...]
) -> str | None:
    core = state.ruleset.core
    for gap in over:
        problem = _gap_problem(state, gap)
        if problem is not None:
            return problem
    problem = _landing_problem(state, unit, dest)
    if problem is not None:
        return problem
    rise = state.tile(*dest).height - state.tile(*unit.xy).height
    if rise > core.max_climb_height:
        return "落點太高，跳不上去"
    if -rise >= core.fall_damage_min_drop:
        return "落點太低，跳下去會摔傷"
    return None


def _vault_state_problem(state: BattleState, unit: UnitState) -> str | None:
    """攀跳的先決條件：不被定身、沒倒地、能移動、AP 與移動點數夠。"""
    core = state.ruleset.core
    if is_rooted(state.ruleset, unit):
        return "被定身，不能攀跳"
    if unit.has_status(PRONE):
        return "倒地中，不能攀跳（先站起來）"
    if unit.speed == 0:
        return "不能移動，不能攀跳"
    if unit.ap < core.vault_ap_cost:
        return f"AP 不足：需要 {core.vault_ap_cost}，剩餘 {unit.ap}"
    if unit.move_points < core.vault_move_cost:
        return f"移動點數不足：需要 {core.vault_move_cost}，剩餘 {unit.move_points}"
    return None


def vault_plan(state: BattleState, unit: UnitState, dest: XY) -> VaultPlan | str:
    """``unit`` 攀跳到 ``dest`` 的計畫；不合法時回傳中文原因。順序：狀態、AP 與移動點數、落點
    形式（相鄰＝攀爬；正前方隔 1～``vault_jump_width`` 格缺口＝跳躍）、細節。"""
    problem = _vault_state_problem(state, unit)
    if problem is not None:
        return problem
    dx, dy = dest[0] - unit.xy[0], dest[1] - unit.xy[1]
    dist = abs(dx) + abs(dy)
    if dist == 0 or (dx != 0 and dy != 0):
        return "攀跳的落點必須是相鄰格，或正前方隔著缺口的格子"
    if dist > state.ruleset.core.vault_jump_width + 1:
        return "距離太遠，跳不過去"
    origins = fear_origins(state, unit)
    if origins and fear_blocks_step(origins, unit.xy, dest):
        return f"{unit.name_zh} 正在恐懼中，不能靠近恐懼的來源"
    if dist == 1:
        problem = _climb_problem(state, unit, dest)
        return problem if problem is not None else VaultPlan("climb", dest, ())
    step = ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
    over = tuple((unit.xy[0] + step[0] * i, unit.xy[1] + step[1] * i) for i in range(1, dist))
    problem = _jump_problem(state, unit, dest, over)
    return problem if problem is not None else VaultPlan("jump", dest, over)


def vault_problem(state: BattleState, unit: UnitState, dest: XY) -> str | None:
    """:func:`vault_plan` 的錯誤原因；合法時 ``None``。"""
    plan = vault_plan(state, unit, dest)
    return plan if isinstance(plan, str) else None


_DIRECTIONS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def vault_destinations(state: BattleState, unit: UnitState) -> list[VaultPlan]:
    """目前合法的攀跳（依落點 ``(y, x)`` 排序）：四個方向各看攀爬與每種跳躍寬度。"""
    core = state.ruleset.core
    if _vault_state_problem(state, unit) is not None:
        return []
    plans: list[VaultPlan] = []
    for dx, dy in _DIRECTIONS:
        for dist in range(1, core.vault_jump_width + 2):
            dest = (unit.xy[0] + dx * dist, unit.xy[1] + dy * dist)
            if not state.in_bounds(*dest):
                break
            plan = vault_plan(state, unit, dest)
            if not isinstance(plan, str):
                plans.append(plan)
    return sorted(plans, key=lambda p: (p.dest[1], p.dest[0]))


def vault_action(unit: UnitState, plan: VaultPlan) -> Vault:
    return Vault(unit_id=unit.id, dest=Pos(x=plan.dest[0], y=plan.dest[1]))
