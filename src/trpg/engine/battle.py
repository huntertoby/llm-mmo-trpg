"""引擎對外 API：``start_battle``、``legal_actions``、``resolve``。

- ``resolve`` 是純函式：在狀態複本上結算，不修改傳入的 ``state``；不合法時拋出
  :class:`~trpg.shared.errors.IllegalActionError`（繁體中文原因）。
- 動作處理器以 ``type`` 為鍵註冊在 :data:`ACTION_HANDLERS`
  （Phase 1B、Phase 2 擴充新動作時新增一筆）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from trpg.content.maps import standable
from trpg.engine.actions import Action, Attack, Defend, EndTurn, Move
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageEffect,
    MoveUnitEffect,
    RemoveStatusEffect,
)
from trpg.engine.events import (
    AttackRolled,
    BattleStarted,
    InitiativeRolled,
    InitiativeTieBroken,
    RoundStarted,
    TurnOrderSet,
    UnitStoodUp,
)
from trpg.engine.results import ResolveResult
from trpg.engine.rules.combat import attack_problem, roll_attack
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import (
    available_move_budget,
    path_map,
    stand_up_cost,
    step_cost,
)
from trpg.engine.setup import BattleSetup, BattleSetupError
from trpg.engine.state import BattleState, Tile, UnitState
from trpg.engine.turns import advance_turn, end_turn, finish_resolution, start_turn
from trpg.shared.errors import IllegalActionError
from trpg.shared.ids import IdAllocator
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Pos, Team, UnitId

__all__ = [
    "ACTION_HANDLERS",
    "MovePlan",
    "begin_battle",
    "has_only_end_turn",
    "legal_actions",
    "plan_move",
    "resolve",
    "start_battle",
]

DEFENDING = "defending"
PRONE = "prone"

type ActionHandler = Callable[[Ctx, UnitState, Action], None]


# ---------------------------------------------------------------------------
# 開始戰鬥
# ---------------------------------------------------------------------------


def _unit_names(setup: BattleSetup) -> list[str]:
    """同一範本出現多次時加上編號（盜賊1、盜賊2）。"""
    totals: dict[str, int] = {}
    for spawn in setup.units:
        totals[spawn.template.id] = totals.get(spawn.template.id, 0) + 1
    seen: dict[str, int] = {}
    names = []
    for spawn in setup.units:
        tid = spawn.template.id
        seen[tid] = seen.get(tid, 0) + 1
        names.append(spawn.template.name_zh + (str(seen[tid]) if totals[tid] > 1 else ""))
    return names


def _place_units(setup: BattleSetup, tiles: tuple[Tile, ...]) -> list[XY]:
    width = setup.map.width
    used: set[XY] = set()
    positions: list[XY | None] = []
    for spawn in setup.units:
        if spawn.position is not None:
            x, y = spawn.position
            if not setup.map.in_bounds(x, y):
                raise BattleSetupError(f"起始位置超出地圖範圍：({x}, {y})")
            terrain = setup.ruleset.terrain_def(tiles[y * width + x].terrain)
            if not standable(terrain):
                raise BattleSetupError(f"起始位置不可站立：({x}, {y}) 是{terrain.name_zh}")
            if (x, y) in used:
                raise BattleSetupError(f"起始位置重複：({x}, {y})")
            used.add((x, y))
        positions.append(spawn.position)
    result: list[XY] = []
    for spawn, given in zip(setup.units, positions, strict=True):
        if given is not None:
            result.append(given)
            continue
        free = [c for c in setup.map.start_zones[spawn.team] if c not in used]
        if not free:
            raise BattleSetupError(f"{spawn.team.display_name}起始區的格子不足")
        used.add(free[0])
        result.append(free[0])
    return result


def begin_battle(setup: BattleSetup, seed: int) -> ResolveResult:
    """建立初始狀態：放置單位、擲先攻、開始第 1 輪與第一位的回合。回傳狀態與開場事件。"""
    teams = {spawn.team for spawn in setup.units}
    if teams != set(Team):
        raise BattleSetupError("雙方都至少要有一個單位")
    map_def = setup.map
    tiles = tuple(Tile(height=h, terrain=t) for row in map_def.grid() for h, t in row)
    positions = _place_units(setup, tiles)
    names = _unit_names(setup)
    ids = IdAllocator("unit")
    units: dict[UnitId, UnitState] = {}
    for spawn, (x, y), name in zip(setup.units, positions, names, strict=True):
        uid = UnitId(ids.next())
        t = spawn.template
        units[uid] = UnitState(
            id=uid,
            template_id=t.id,
            name_zh=name,
            team=spawn.team,
            pos=Pos(x=x, y=y),
            hp=t.max_hp,
            max_hp=t.max_hp,
            attributes=dict(t.attributes),
            speed=t.speed,
            armor_bonus=t.armor_bonus,
            weapon=spawn.weapon,
            resist=dict(t.resist),
            element_mods=dict(t.element_mods),
            tags=t.tags,
        )
    state = BattleState(
        map_id=map_def.id,
        map_name_zh=map_def.name_zh,
        width=map_def.width,
        height=map_def.height,
        tiles=tiles,
        ruleset=setup.ruleset,
        units=units,
        turn_order=[],
        turn_pos=0,
        active_unit=None,
        round=1,
        max_rounds=setup.max_rounds,
        seed=seed,
        rng_state=Rng(seed).get_state(),
    )
    ctx = Ctx(state)
    core = ctx.core
    ctx.emit(BattleStarted, map_id=map_def.id, seed=seed)
    for unit in state.units_sorted():
        roll = ctx.rng.d20()
        modifier = (unit.attributes[Attribute.DEX] - core.initiative_attr_base) // (
            core.initiative_attr_divisor
        )
        unit.initiative = roll + modifier
        ctx.emit(
            InitiativeRolled, unit_id=unit.id, roll=roll, modifier=modifier, total=unit.initiative
        )
    state.turn_order = _initiative_order(ctx)
    ctx.emit(TurnOrderSet, order=tuple(state.turn_order))
    ctx.emit(RoundStarted)
    start_turn(ctx, state.turn_order[0])
    return finish_resolution(ctx)


def _initiative_order(ctx: Ctx) -> list[UnitId]:
    """先攻順序：總值高者先；同值先比敏捷值；仍相同時以戰鬥亂數決定（``docs/專案計畫.md`` 5.0）。

    仍平手的每一組（依單位 ID 排序後）以 ``rng.shuffled`` 洗牌一次，並產生
    ``initiative_tie_broken`` 事件記錄結果。
    """
    units = ctx.state.units_sorted()
    groups: dict[tuple[int, int], list[UnitId]] = {}
    for unit in units:
        groups.setdefault((unit.initiative, unit.attributes[Attribute.DEX]), []).append(unit.id)
    order: list[UnitId] = []
    for key in sorted(groups, key=lambda k: (-k[0], -k[1])):
        members = groups[key]
        if len(members) > 1:
            members = ctx.rng.shuffled(members)
            ctx.emit(InitiativeTieBroken, total=key[0], dex=key[1], order=tuple(members))
        order.extend(members)
    return order


def start_battle(setup: BattleSetup, seed: int) -> BattleState:
    """``begin_battle`` 的狀態部分（開場事件請用 :func:`begin_battle` 取得）。"""
    return begin_battle(setup, seed).state


# ---------------------------------------------------------------------------
# 合法性檢查
# ---------------------------------------------------------------------------


def _actor(state: BattleState, action: Action) -> UnitState:
    if state.ended:
        raise IllegalActionError("戰鬥已結束")
    active = state.active
    if active is None:
        raise IllegalActionError("目前沒有行動中的單位")
    if action.unit_id != active.id:
        actor = state.units.get(action.unit_id)
        who = actor.name_zh if actor is not None else action.unit_id
        raise IllegalActionError(f"現在是 {active.name_zh} 的回合，不是 {who}")
    return active


def _require_ap(unit: UnitState, cost: int) -> None:
    if unit.ap < cost:
        raise IllegalActionError(f"AP 不足：需要 {cost}，剩餘 {unit.ap}")


@dataclass(frozen=True, slots=True)
class MovePlan:
    """驗證通過的移動。

    ``steps`` 為每一步的目的格與成本；``stand_up`` 為站起消耗（0 表示不需要）。
    """

    steps: tuple[tuple[XY, int], ...]
    stand_up: int

    @property
    def total(self) -> int:
        return self.stand_up + sum(cost for _, cost in self.steps)


def plan_move(state: BattleState, unit: UnitState, path: tuple[Pos, ...]) -> MovePlan:
    """驗證 ``path``；不合法時拋出 :class:`IllegalActionError`。"""
    prone = unit.has_status(PRONE)
    if not path:
        raise IllegalActionError("路徑不可為空")
    start = (path[0].x, path[0].y)
    if start != unit.xy:
        raise IllegalActionError(f"路徑必須從目前位置 {unit.xy} 開始，收到 {start}")
    if len(path) == 1 and not prone:
        raise IllegalActionError("路徑至少要移動一格")
    occupancy = state.occupancy()
    steps: list[tuple[XY, int]] = []
    prev = start
    for pos in path[1:]:
        cur = (pos.x, pos.y)
        if not state.in_bounds(*cur):
            raise IllegalActionError(f"超出地圖範圍：{cur}")
        if abs(cur[0] - prev[0]) + abs(cur[1] - prev[1]) != 1:
            raise IllegalActionError(f"路徑不連續：{prev} → {cur} 不相鄰")
        cost = step_cost(state, prev, cur)
        if cost is None:
            terrain = state.ruleset.terrain_def(state.tile(*cur).terrain)
            if not standable(terrain):
                raise IllegalActionError(f"無法進入{terrain.name_zh}：{cur}")
            h0, h1 = state.tile(*prev).height, state.tile(*cur).height
            raise IllegalActionError(
                f"高度差過大：{prev} 高度 {h0} → {cur} 高度 {h1}，"
                f"一步最多往上 {state.ruleset.core.max_climb_height} 層"
            )
        other = occupancy.get(cur)
        if other is not None and other.id != unit.id and other.team is not unit.team:
            raise IllegalActionError(f"被敵方單位 {other.name_zh} 阻擋：{cur}")
        steps.append((cur, cost))
        prev = cur
    end_unit = occupancy.get(prev)
    if end_unit is not None and end_unit.id != unit.id:
        raise IllegalActionError(f"不能停在已有單位的格子：{prev}（{end_unit.name_zh}）")
    plan = MovePlan(steps=tuple(steps), stand_up=stand_up_cost(state, unit) if prone else 0)
    if plan.total > unit.move_points:
        raise IllegalActionError(f"移動點數不足：需要 {plan.total}，剩餘 {unit.move_points}")
    return plan


def _attack_target(state: BattleState, unit: UnitState, action: Attack) -> UnitState:
    target = state.units.get(action.target_id)
    if target is None:
        raise IllegalActionError(f"找不到目標：{action.target_id}")
    problem = attack_problem(state, unit, target)
    if problem is not None:
        raise IllegalActionError(problem)
    return target


# ---------------------------------------------------------------------------
# 動作處理器
# ---------------------------------------------------------------------------


def _do_move(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Move)
    plan = plan_move(ctx.state, unit, action.path)
    if plan.stand_up:
        unit.move_points -= plan.stand_up
        execute(ctx, [RemoveStatusEffect(target_id=unit.id, status_id=PRONE, reason="stood_up")])
        ctx.emit(UnitStoodUp, unit_id=unit.id, cost=plan.stand_up)
    for dest, cost in plan.steps:
        unit.move_points -= cost
        execute(ctx, [MoveUnitEffect(unit_id=unit.id, dest=dest, mode="walk", cost=cost)])
        if unit.downed:
            break


def _do_attack(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Attack)
    cost = ctx.core.basic_attack_ap_cost
    _require_ap(unit, cost)
    target = _attack_target(ctx.state, unit, action)
    unit.ap -= cost
    roll = roll_attack(ctx.state, ctx.rng, unit, target)
    ctx.emit(
        AttackRolled,
        attacker_id=unit.id,
        target_id=target.id,
        rolls=roll.rolls,
        advantage=roll.advantage,
        natural=roll.natural,
        attack_value=roll.attack_value,
        defense_value_permille=roll.defense_value_permille,
        hit_modifier=roll.hit_modifier,
        proficiency=roll.proficiency,
        situational=roll.situational,
        total=roll.total,
        target_number=roll.target_number,
        hit=roll.hit,
        crit=roll.crit,
    )
    if not roll.hit:
        return
    weapon = unit.weapon
    multiplier = ctx.core.basic_attack_attr_multiplier_permille
    execute(
        ctx,
        [
            DamageEffect(
                target_id=target.id,
                source_id=unit.id,
                cause="attack",
                element=weapon.element,
                dice=weapon.dice,
                flat=weapon.flat,
                scaled_permille=unit.attributes[weapon.scaling_attr] * multiplier,
                crit=roll.crit,
                min_damage=ctx.core.min_damage_on_hit,
            )
        ],
    )


def _do_defend(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Defend)
    cost = ctx.core.defend_ap_cost
    _require_ap(unit, cost)
    if unit.has_status(DEFENDING):
        raise IllegalActionError("已處於防禦姿態")
    unit.ap -= cost
    execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=DEFENDING, source_id=unit.id)])


def _do_end_turn(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, EndTurn)
    end_turn(ctx)
    advance_turn(ctx)


ACTION_HANDLERS: dict[str, ActionHandler] = {
    "move": _do_move,
    "attack": _do_attack,
    "defend": _do_defend,
    "end_turn": _do_end_turn,
}


def resolve(state: BattleState, action: Action) -> ResolveResult:
    """結算 ``action``，回傳新狀態、事件與 ``pending``（Phase 1A 一律為 ``None``）。

    不修改傳入的 ``state``。不合法時拋出 :class:`IllegalActionError`。
    """
    _actor(state, action)
    ctx = Ctx(state.clone())
    actor = ctx.state.units[action.unit_id]
    ACTION_HANDLERS[action.type](ctx, actor, action)
    return finish_resolution(ctx)


# ---------------------------------------------------------------------------
# 合法動作
# ---------------------------------------------------------------------------


def legal_actions(state: BattleState) -> list[Action]:
    """目前行動者的所有合法動作（確定性順序）。

    順序：攻擊（依目標 ID）→ 防禦 → 移動（每個可達格一條最短路徑，依 ``(y, x)``；倒地時另含
    「只站起來」）→ 結束回合。``resolve`` 接受任何合法路徑，這裡每個目的地只列一條代表路徑。
    """
    unit = state.active
    if state.ended or unit is None:
        return []
    core = state.ruleset.core
    actions: list[Action] = []
    if unit.ap >= core.basic_attack_ap_cost:
        actions.extend(
            Attack(unit_id=unit.id, target_id=target.id)
            for target in state.living_units()
            if attack_problem(state, unit, target) is None
        )
    if unit.ap >= core.defend_ap_cost and not unit.has_status(DEFENDING):
        actions.append(Defend(unit_id=unit.id))
    budget = available_move_budget(state, unit)
    if budget is not None:
        if unit.has_status(PRONE):
            actions.append(Move(unit_id=unit.id, path=(unit.pos,)))
        pm = path_map(state, unit, budget)
        ends = sorted((xy for xy in pm.cost if pm.can_end_at(xy)), key=lambda p: (p[1], p[0]))
        for xy in ends:
            path = tuple(Pos(x=x, y=y) for x, y in pm.path_to(xy))
            actions.append(Move(unit_id=unit.id, path=path))
    actions.append(EndTurn(unit_id=unit.id))
    return actions


def has_only_end_turn(state: BattleState) -> bool:
    """``legal_actions(state)`` 是否只剩 ``EndTurn``（不建立動作列表的快速版本）。

    驅動迴圈用它判斷是否自動結束回合。戰鬥已結束時回傳 ``False``。
    """
    unit = state.active
    if state.ended or unit is None:
        return False
    return not (_has_ap_action(state, unit) or _can_move(state, unit))


def _has_ap_action(state: BattleState, unit: UnitState) -> bool:
    core = state.ruleset.core
    if unit.ap >= core.defend_ap_cost and not unit.has_status(DEFENDING):
        return True
    return unit.ap >= core.basic_attack_ap_cost and any(
        attack_problem(state, unit, target) is None for target in state.living_units()
    )


def _can_move(state: BattleState, unit: UnitState) -> bool:
    budget = available_move_budget(state, unit)
    if budget is None:
        return False
    if unit.has_status(PRONE):
        return True  # 至少可以只站起來
    if budget == 0:
        return False
    pm = path_map(state, unit, budget)
    return any(pm.can_end_at(xy) for xy in pm.cost)
