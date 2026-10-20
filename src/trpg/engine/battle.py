"""引擎對外 API：``begin_battle``／``start_battle``、``legal_actions``、``resolve``、``resume``。

- ``resolve`` 是純函式：在狀態複本上結算，不修改傳入的 ``state``；不合法時拋出
  :class:`~trpg.shared.errors.IllegalActionError`（繁體中文原因）。
- 動作處理器以 ``type`` 為鍵註冊在 :data:`ACTION_HANDLERS`
  （Phase 2 擴充新動作時新增一筆）。
- 暫停點：``prompt`` 反應需要玩家決定時，``resolve`` 回傳的狀態帶 ``pending``（顯示到暫停為止的
  結果），``ResolveResult.pending`` 說明在等誰；``resume(state, decision)`` 從動作之前的狀態
  以全部決定重新結算（結算是確定的），只回傳暫停之後的事件。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from trpg.content.skills import SkillDef, skill_slot_problems, weapon_problem
from trpg.engine import modifiers
from trpg.engine.actions import (
    ACTION_ADAPTER,
    Action,
    Attack,
    Decision,
    Defend,
    EndStance,
    EndTurn,
    Interact,
    Move,
    SetReactionMode,
    Shove,
    Trip,
    UseSkill,
)
from trpg.engine.activations import moves_object
from trpg.engine.context import Ctx, GambleBranch, PreviewMode
from trpg.engine.copying import copy_selections, has_copy_effect
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    DamageObjectEffect,
    MoveUnitEffect,
    PushEffect,
    RemoveStatusEffect,
)
from trpg.engine.effects.world import object_push_block, push_distance
from trpg.engine.events import (
    BattleStarted,
    InitiativeRolled,
    InitiativeTieBroken,
    ObjectAttacked,
    ReactionModeSet,
    RoundStarted,
    TurnOrderSet,
    UnitStoodUp,
)
from trpg.engine.ids import DEFENDING, PRONE, TOPPLABLE
from trpg.engine.lifecycle import make_unit
from trpg.engine.maneuvers import contest
from trpg.engine.reactions import (
    PauseForDecision,
    enemy_enters_adjacent_reactions,
    enemy_moves_in_range_reactions,
    opportunity_attacks,
    perform_unit_attack,
)
from trpg.engine.results import ResolveResult
from trpg.engine.rule_changes import pass_through
from trpg.engine.rules.combat import attack_problem, reach_problem
from trpg.engine.rules.facing import face_toward, opening_facing
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.movement import (
    available_move_budget,
    can_only_stand_up,
    fear_blocks_step,
    fear_origins,
    is_deadly,
    is_standable,
    path_map,
    stand_up_cost,
    step_cost,
)
from trpg.engine.rules.statuses import (
    base_attribute,
    effective_attribute,
    is_rooted,
    skip_turn_status,
    stance_status_ids,
)
from trpg.engine.setup import BattleSetup, BattleSetupError, starting_source
from trpg.engine.skill_triggers import collect_move, settle
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.followups import second_problem
from trpg.engine.skills.interpreter import use_skill
from trpg.engine.skills.targeting import (
    SkillArea,
    has_selection,
    selections,
    skill_problem,
)
from trpg.engine.state import (
    BattleState,
    Facing,
    ObjectState,
    PendingResolution,
    Tile,
    UnitState,
    state_from_json,
    state_to_json,
)
from trpg.engine.turns import advance_turn, end_turn, finish_resolution, start_turn
from trpg.shared.errors import IllegalActionError
from trpg.shared.ids import IdAllocator
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, ObjectId, Pos, Team, UnitId

__all__ = [
    "ACTION_HANDLERS",
    "INTERACT_CHOICES",
    "MovePlan",
    "begin_battle",
    "has_only_end_turn",
    "interact_actions",
    "interact_direction",
    "interact_options",
    "interact_problem",
    "legal_actions",
    "legal_actions_with_areas",
    "plan_move",
    "resolve",
    "resolve_with",
    "resume",
    "shove_problem",
    "simulate_preview",
    "start_battle",
]


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


def _place_units(setup: BattleSetup, state: BattleState) -> list[XY]:
    used: set[XY] = set()
    for spawn in setup.units:
        if spawn.position is None:
            continue
        x, y = spawn.position
        if not state.in_bounds(x, y):
            raise BattleSetupError(f"起始位置超出地圖範圍：({x}, {y})")
        if not is_standable(state, (x, y)) or is_deadly(state, (x, y)):
            terrain = setup.ruleset.terrain_def(state.tile(x, y).terrain)
            raise BattleSetupError(f"起始位置不可站立：({x}, {y}) 是{terrain.name_zh}")
        if (x, y) in used:
            raise BattleSetupError(f"起始位置重複：({x}, {y})")
        used.add((x, y))
    result: list[XY] = []
    for spawn in setup.units:
        if spawn.position is not None:
            result.append(spawn.position)
            continue
        free = [
            c for c in setup.map.start_zones[spawn.team] if c not in used and is_standable(state, c)
        ]
        if not free:
            raise BattleSetupError(f"{spawn.team.display_name}起始區的格子不足")
        used.add(free[0])
        result.append(free[0])
    return result


def _initial_board(setup: BattleSetup) -> tuple[list[Tile], dict[ObjectId, ObjectState]]:
    map_def = setup.map
    width = map_def.width
    surfaces = {s.at: s for s in map_def.surfaces}
    tiles: list[Tile] = []
    for y, row in enumerate(map_def.grid()):
        for x, (h, t) in enumerate(row):
            placed = surfaces.get((x, y))
            tiles.append(
                Tile(height=h, terrain=t)
                if placed is None
                else Tile(
                    height=h,
                    terrain=t,
                    surface=placed.surface,
                    surface_remaining=placed.duration,
                )
            )
    objects: dict[ObjectId, ObjectState] = {}
    ids = IdAllocator("obj")
    for placement in map_def.objects:
        definition = setup.ruleset.object_def(placement.kind)
        oid = ObjectId(ids.next())
        x, y = placement.at
        objects[oid] = ObjectState(
            id=oid,
            kind=definition.id,
            pos=Pos(x=x, y=y),
            hp=definition.max_hp,
            max_hp=definition.max_hp,
        )
        tiles[y * width + x] = replace(tiles[y * width + x], object_id=oid)
    return tiles, objects


def _check_loadouts(setup: BattleSetup) -> None:
    """每個單位的技能裝備必須合法：存在、武器相容、不超過欄位上限。"""
    rules = setup.ruleset
    for spawn in setup.units:
        defs: list[SkillDef] = []
        for skill_id in spawn.template.skills:
            try:
                defs.append(rules.skill_def(skill_id))
            except KeyError:
                raise BattleSetupError(f"{spawn.template.name_zh}：未知的技能 {skill_id}") from None
        problems = [weapon_problem(s, spawn.weapon.weapon_class) for s in defs]
        problems += skill_slot_problems(defs, rules.core.skill_slots)
        found = next((p for p in problems if p is not None), None)
        if found is not None:
            raise BattleSetupError(f"{spawn.template.name_zh}：{found}")


def begin_battle(setup: BattleSetup, seed: int) -> ResolveResult:
    """建立初始狀態：放置物件與單位、擲先攻、開始第 1 輪與第一位的回合。回傳狀態與開場事件。"""
    teams = {spawn.team for spawn in setup.units}
    if teams != set(Team):
        raise BattleSetupError("雙方都至少要有一個單位")
    map_def = setup.map
    _check_loadouts(setup)
    tiles, objects = _initial_board(setup)
    state = BattleState(
        map_id=map_def.id,
        map_name_zh=map_def.name_zh,
        width=map_def.width,
        height=map_def.height,
        tiles=tiles,
        ruleset=setup.ruleset,
        units={},
        turn_order=[],
        turn_pos=0,
        active_unit=None,
        round=1,
        max_rounds=setup.max_rounds,
        seed=seed,
        rng_state=Rng(seed).get_state(),
        objects=objects,
        weather=setup.weather,
        objective=setup.effective_objective,
        map_events=map_def.events,
        spawn_templates=dict(setup.spawn_templates),
    )
    positions = _place_units(setup, state)
    names = _unit_names(setup)
    ids = IdAllocator("unit")
    facings = _opening_facings(setup, positions)
    for spawn, (x, y), name in zip(setup.units, positions, names, strict=True):
        uid = UnitId(ids.next())
        state.units[uid] = make_unit(
            uid,
            template=spawn.template,
            weapon=spawn.weapon,
            team=spawn.team,
            pos=Pos(x=x, y=y),
            name=name,
            rules=setup.ruleset,
            facing=facings[spawn.team],
        )
        unit = state.units[uid]
        unit.source = starting_source(spawn, setup.ruleset.core)
        if spawn.hp is not None:  # 開場 HP／法力（Phase 3-5a：一輪存檔帶入；None ＝ 滿）
            unit.hp = min(spawn.hp, unit.max_hp)
        if spawn.mana is not None:
            unit.mana = min(spawn.mana, unit.max_mana)
    state.source_wells = tuple(sorted(map_def.source_wells, key=lambda xy: (xy[1], xy[0])))
    ctx = Ctx(state)
    core = ctx.core
    ctx.emit(BattleStarted, map_id=map_def.id, seed=seed)
    for unit in state.units_sorted():
        roll = ctx.rng.d20()
        modifier = (base_attribute(unit, Attribute.DEX) - core.initiative_attr_base) // (
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


def _opening_facings(setup: BattleSetup, positions: list[XY]) -> dict[Team, Facing]:
    """開場朝向（Phase 3D-8d）：每個陣營面向敵方起始位置（重心）的方向。"""
    by_team: dict[Team, list[XY]] = {team: [] for team in Team}
    for spawn, xy in zip(setup.units, positions, strict=True):
        by_team[spawn.team].append(xy)
    return {
        team: opening_facing(
            team,
            by_team[team],
            [xy for other in Team if other is not team for xy in by_team[other]],
        )
        for team in Team
    }


def _initiative_order(ctx: Ctx) -> list[UnitId]:
    """先攻順序：總值高者先；同值先比敏捷值；仍相同時以戰鬥亂數決定（``docs/專案計畫.md`` 5.0）。

    仍平手的每一組（依單位 ID 排序後）以 ``rng.shuffled`` 洗牌一次，並產生
    ``initiative_tie_broken`` 事件記錄結果。
    """
    units = ctx.state.units_sorted()
    groups: dict[tuple[int, int], list[UnitId]] = {}
    for unit in units:
        groups.setdefault((unit.initiative, base_attribute(unit, Attribute.DEX)), []).append(
            unit.id
        )
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
    if state.pending is not None:
        who = state.units[state.pending.unit_id].name_zh
        raise IllegalActionError(f"結算暫停中：等待 {who} 決定是否使用反應，請使用 resume")
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


def _require_free_to_move(state: BattleState, unit: UnitState, steps: int) -> None:
    """定身時不能走格子；倒地的單位仍可只站起來（``steps == 0``，站起不是移動格子）。"""
    if steps > 0 and is_rooted(state.ruleset, unit):
        raise IllegalActionError(f"{unit.name_zh} 被定身，不能主動移動")


def plan_move(  # noqa: PLR0912
    state: BattleState, unit: UnitState, path: tuple[Pos, ...]
) -> MovePlan:
    """驗證 ``path``；不合法時拋出 :class:`IllegalActionError`。"""
    prone = unit.has_status(PRONE)
    _require_free_to_move(state, unit, max(len(path) - 1, 0))
    if not path:
        raise IllegalActionError("路徑不可為空")
    start = (path[0].x, path[0].y)
    if start != unit.xy:
        raise IllegalActionError(f"路徑必須從目前位置 {unit.xy} 開始，收到 {start}")
    if len(path) == 1 and not prone:
        raise IllegalActionError("路徑至少要移動一格")
    occupancy = state.occupancy()
    fear = fear_origins(state, unit)
    steps: list[tuple[XY, int]] = []
    prev = start
    for pos in path[1:]:
        cur = (pos.x, pos.y)
        if not state.in_bounds(*cur):
            raise IllegalActionError(f"超出地圖範圍：{cur}")
        if abs(cur[0] - prev[0]) + abs(cur[1] - prev[1]) != 1:
            raise IllegalActionError(f"路徑不連續：{prev} → {cur} 不相鄰")
        if fear and fear_blocks_step(fear, prev, cur):
            raise IllegalActionError(
                f"{unit.name_zh} 正在恐懼中，不能靠近恐懼的來源：{prev} → {cur}"
            )
        cost = step_cost(state, prev, cur)
        if cost is None:
            if not is_standable(state, cur):
                obj = state.object_at(*cur)
                if obj is not None and state.object_has_tag(*cur, "blocks_move"):
                    name = state.object_def(obj).name_zh
                    raise IllegalActionError(f"被{name}阻擋：{cur}")
                terrain = state.ruleset.terrain_def(state.tile(*cur).terrain)
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


def _attack_target(state: BattleState, unit: UnitState, target_id: UnitId) -> UnitState:
    target = state.units.get(target_id)
    if target is None:
        raise IllegalActionError(f"找不到目標：{target_id}")
    problem = attack_problem(state, unit, target)
    if problem is not None:
        raise IllegalActionError(problem)
    return target


def object_attack_problem(state: BattleState, unit: UnitState, obj: ObjectState) -> str | None:
    """不能攻擊物件的原因；可以攻擊時回傳 ``None``（不檢查 AP）。"""
    definition = state.object_def(obj)
    if obj.destroyed:
        return f"物件已被摧毀：{definition.name_zh}"
    if "breakable" not in definition.tags or obj.hp is None:
        return f"{definition.name_zh}無法被攻擊"
    return reach_problem(state, unit, obj.xy, definition.name_zh)


def _live_object(state: BattleState, object_id: ObjectId) -> ObjectState:
    obj = state.objects.get(object_id)
    if obj is None or obj.destroyed:
        raise IllegalActionError(f"找不到物件：{object_id}")
    return obj


def maneuver_problem(state: BattleState, unit: UnitState, target: UnitState) -> str | None:
    """技巧動作（推擊、絆倒）的目標問題：必須是相鄰、高度差不超過近戰上限的敵人。"""
    if not target.alive:
        return f"目標已不在戰場上：{target.name_zh}"
    if target.team is unit.team:
        return f"只能對敵方單位使用：{target.name_zh}"
    if manhattan(unit.xy, target.xy) != 1:
        return f"目標必須相鄰：{target.name_zh}"
    limit = state.ruleset.core.melee_height_limit
    diff = abs(state.tile(*unit.xy).height - state.tile(*target.xy).height)
    if diff > limit:
        return f"高度差過大：相差 {diff} 層（上限 {limit} 層）"
    return None


_PUSH_BLOCK_REASONS = {
    "out_of_bounds": "會被推出地圖",
    "occupied": "另一側有單位",
    "obstacle": "另一側被擋住",
    "too_high": "另一側比較高",
}


def action_ap_cost(state: BattleState, unit: UnitState, use: modifiers.Use) -> int:
    """基本動作（普攻、推擊、絆倒、互動）的 AP 成本，含修正規則的 ``ap_delta``（Phase 3C-2）。"""
    core = state.ruleset.core
    base = {
        "attack": core.basic_attack_ap_cost,
        "shove": core.maneuver_ap_cost,
        "trip": core.maneuver_ap_cost,
        "interact": core.interact_ap_cost,
    }[use.action or ""]
    return modifiers.ap_cost(state, unit, use, base)


def shove_split(state: BattleState, unit: UnitState, target: UnitState) -> tuple[int, int]:
    """推擊的 ``(距離, 額外撞擊次數)``：``shove_distance`` 加上修正規則的 ``push_distance_delta``
    （距離截斷在 ``max_displace_distance``，超過的每 1 格改為一次撞擊傷害；steadfast 的減半在
    結算時另外套用）。"""
    base = state.ruleset.core.shove_distance
    subject = Subject(target, target.xy)
    return modifiers.displace_split(state, unit, modifiers.SHOVE, subject, base)


def shove_distance(state: BattleState, unit: UnitState, target: UnitState) -> int:
    """推擊的距離（:func:`shove_split` 的距離部分）。"""
    return shove_split(state, unit, target)[0]


def shove_problem(state: BattleState, unit: UnitState, target: UnitState) -> str | None:
    """推擊推不動的原因（距離減半後為 0）；推得動時回傳 ``None``。

    目標身後第一格被擋（牆、不可走地形、較高格、物件、單位、地圖邊緣）時推擊仍然合法：對抗成功
    則目標不移動、受 1 次撞擊（Phase 3C-3b，``docs/phases/Phase3C計畫.md`` 5.4）。
    """
    distance = push_distance(state, target, shove_distance(state, unit, target))
    if distance <= 0:
        return f"推不動：{target.name_zh} 不為所動（推擊距離減半後為 0 格）"
    return None


type InteractMode = Literal["push", "shove_aside"]
type Side = Literal["left", "right"]

INTERACT_CHOICES: tuple[tuple[InteractMode, Side | None], ...] = (
    ("push", None),
    ("shove_aside", "left"),
    ("shove_aside", "right"),
)
"""互動的所有 ``(mode, side)`` 組合（``legal_actions`` 的列舉順序）。"""


def interact_direction(
    unit_xy: XY, obj_xy: XY, mode: InteractMode = "push", side: Side | None = None
) -> tuple[int, int]:
    """物件的移動方向（單位向量）。

    推：沿「行動者 → 物件」；撥開：垂直於它，``left`` 為逆時針 90°、``right`` 為順時針 90°
    （``y`` 向下，所以朝東（1, 0）的左邊是北（0, −1））。
    """
    dx, dy = _direction(unit_xy, obj_xy)
    if mode == "push":
        return (dx, dy)
    return (dy, -dx) if side == "left" else (-dy, dx)


def object_move_problem(
    state: BattleState, unit: UnitState, obj: ObjectState, direction: tuple[int, int], verb: str
) -> str | None:
    """物件被行動者移動 1 格（推與撥開共用）的問題：可推動、相鄰、高度差不超過
    ``interact_height_limit``、目標格放得下。``verb`` 為錯誤訊息的動詞（「推」或「撥」）。"""
    definition = state.object_def(obj)
    if obj.destroyed:
        return f"物件已被摧毀：{definition.name_zh}"
    if "pushable" not in definition.tags and moves_object(state, unit.id, definition.tags) is None:
        return f"{definition.name_zh}無法推動"
    problem = _adjacent_problem(state, unit, obj)
    if problem is not None:
        return problem
    reason = object_push_block(state, obj.xy, (obj.pos.x + direction[0], obj.pos.y + direction[1]))
    if reason is not None:
        return f"{verb}不動：{definition.name_zh}{_PUSH_BLOCK_REASONS[reason]}"
    return None


def _adjacent_problem(state: BattleState, unit: UnitState, obj: ObjectState) -> str | None:
    """互動的物件必須相鄰、高度差不超過 ``interact_height_limit``。"""
    if manhattan(unit.xy, obj.xy) != 1:
        return f"物件必須相鄰：{state.object_def(obj).name_zh}"
    limit = state.ruleset.core.interact_height_limit
    diff = abs(state.tile(*unit.xy).height - state.tile(*obj.xy).height)
    if diff > limit:
        return f"高度差過大：相差 {diff} 層（上限 {limit} 層）"
    return None


def interact_problem(
    state: BattleState,
    unit: UnitState,
    obj: ObjectState,
    mode: InteractMode = "push",
    side: Side | None = None,
) -> str | None:
    """互動（推或撥開物件）的問題；合法時回傳 ``None``。撥開的訊息為「撥不動」。

    ``topplable`` 物件（Phase 3C-5a）推了會倒下（推倒），不檢查目標格；不能撥開。
    """
    if mode == "shove_aside" and side is None:
        return "撥開必須指定方向（左或右）"
    definition = state.object_def(obj)
    if TOPPLABLE in definition.tags and not obj.destroyed:
        if mode == "shove_aside":
            return f"撥不動：{definition.name_zh}只能推倒，不能撥開"
        return _adjacent_problem(state, unit, obj)
    direction = interact_direction(unit.xy, obj.xy, mode, side)
    return object_move_problem(state, unit, obj, direction, "推" if mode == "push" else "撥")


def interact_options(
    state: BattleState, unit: UnitState
) -> list[tuple[ObjectState, InteractMode, Side | None, str | None]]:
    """相鄰的可推動（或可推倒，Phase 3C-5a）物件的所有互動選項 ``(物件, mode, side, 問題)``；
    合法者的問題為 ``None``。

    給介面顯示「不合法的方向與原因」用；AP 不足時每一項的問題都是 AP 不足。
    """
    cost = action_ap_cost(state, unit, modifiers.INTERACT)
    options: list[tuple[ObjectState, InteractMode, Side | None, str | None]] = []
    for obj in state.objects_sorted():
        tags = state.object_def(obj).tags
        movable = "pushable" in tags or moves_object(state, unit.id, tags) is not None
        if obj.destroyed or (not movable and TOPPLABLE not in tags):
            continue
        if manhattan(unit.xy, obj.xy) != 1:
            continue
        for mode, side in INTERACT_CHOICES:
            problem = interact_problem(state, unit, obj, mode, side)
            if problem is None and unit.ap < cost:
                problem = f"AP 不足：需要 {cost}，目前 {unit.ap}"
            options.append((obj, mode, side, problem))
    return options


def interact_actions(state: BattleState, unit: UnitState) -> list[Interact]:
    """目前合法的互動（物件依 ID 排序，每個物件依 ``INTERACT_CHOICES`` 順序）。"""
    if unit.ap < action_ap_cost(state, unit, modifiers.INTERACT):
        return []
    return [
        Interact(unit_id=unit.id, object_id=obj.id, mode=mode, side=side)
        for obj in state.objects_sorted()
        for mode, side in INTERACT_CHOICES
        if interact_problem(state, unit, obj, mode, side) is None
    ]


def _direction(a: XY, b: XY) -> tuple[int, int]:
    return (b[0] - a[0], b[1] - a[1])


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
    walked: list[XY] = [unit.xy]
    touched: set[UnitId] = set()  # 規則改變 pass_through_apply 這次移動碰過的敵人（3D-6）
    for dest, cost in plan.steps:
        opportunity_attacks(ctx, unit, unit.xy, dest)
        if not unit.alive:
            break
        unit.move_points -= cost
        before = unit.xy
        execute(ctx, [MoveUnitEffect(unit_id=unit.id, dest=dest, mode="walk", cost=cost)])
        enemy_enters_adjacent_reactions(ctx, unit, before)
        enemy_moves_in_range_reactions(ctx, unit)
        if unit.xy == dest:
            pass_through(ctx, unit, touched)
        walked.append(unit.xy)
        if _move_interrupted(ctx, unit, dest):
            break
    _slide_back_if_stacked(ctx, unit, walked)
    if len(walked) > 1 and unit.alive:  # 被動技能 on_move：一次主動移動動作完成後（強制位移不算）
        collect_move(ctx, unit)
        settle(ctx)


def _move_interrupted(ctx: Ctx, unit: UnitState, dest: XY) -> bool:
    """這一步之後要不要中止接下來的移動（Phase 2F-1 3.3）：單位目前的位置不等於這一步的預期格
    （途中被推離，例如陷阱的推擊效果；``MoveUnitEffect`` 本身不檢查，下一步會把單位硬拉回原
    路徑），或單位被定身／暈眩／倒地／死亡／逃離——不再依賴「有陷阱且觸發了 ``TrapTriggered``」
    這種特定事件類型的判斷（取代舊版只在陷阱觸發時才檢查定身／暈眩的做法）。"""
    if not unit.alive or unit.xy != dest:
        return True
    if unit.has_status(PRONE):
        return True
    return is_rooted(ctx.rules, unit) or skip_turn_status(ctx.rules, unit) is not None


def _slide_back_if_stacked(ctx: Ctx, unit: UnitState, walked: list[XY]) -> None:
    """途中倒地（滑倒、被反應擊倒）而停在友軍所在的格子（走路可穿越友軍）時，單位滑回走過的
    最近一個沒有其他單位的格子，避免兩個單位疊在同一格（Phase 2C-3：冰湖地圖暴露的問題）。"""
    if not unit.alive:
        return
    state = ctx.state
    if not any(u.alive and u.id != unit.id and u.xy == unit.xy for u in state.units.values()):
        return
    for back in reversed(walked[:-1]):
        if not any(u.alive and u.id != unit.id and u.xy == back for u in state.units.values()):
            execute(ctx, [MoveUnitEffect(unit_id=unit.id, dest=back, mode="teleport")])
            return


def _do_attack(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Attack)
    cost = action_ap_cost(ctx.state, unit, modifiers.ATTACK)
    _require_ap(unit, cost)
    if action.target_object_id is not None:
        obj = _live_object(ctx.state, action.target_object_id)
        problem = object_attack_problem(ctx.state, unit, obj)
        if problem is not None:
            raise IllegalActionError(problem)
        unit.ap -= cost
        ctx.emit(ObjectAttacked, attacker_id=unit.id, object_id=obj.id)
        face_toward(unit, obj.xy)  # 攻擊後面向目標（Phase 3D-8d）
        weapon = unit.weapon
        state, use = ctx.state, modifiers.ATTACK
        execute(
            ctx,
            [
                DamageObjectEffect(
                    object_id=obj.id,
                    source_id=unit.id,
                    cause="attack",
                    element=modifiers.damage_element(state, unit, use, weapon.element),
                    dice=weapon.dice,
                    flat=weapon.flat,
                    scaled_permille=effective_attribute(ctx.rules, unit, weapon.scaling_attr)
                    * ctx.core.basic_attack_attr_multiplier_permille,
                    min_damage=ctx.core.min_damage_on_hit,
                    multiplier_permille=modifiers.damage_permille(
                        state, unit, use, Subject(None, obj.xy)
                    ),
                )
            ],
        )
        return
    assert action.target_id is not None
    target = _attack_target(ctx.state, unit, action.target_id)
    unit.ap -= cost
    perform_unit_attack(ctx, unit, target, primary=True)


def _do_defend(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Defend)
    cost = ctx.core.defend_ap_cost
    _require_ap(unit, cost)
    if unit.has_status(DEFENDING):
        raise IllegalActionError("已處於防禦姿態")
    unit.ap -= cost
    execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=DEFENDING, source_id=unit.id)])


def _maneuver_target(ctx: Ctx, unit: UnitState, target_id: UnitId) -> UnitState:
    target = ctx.state.units.get(target_id)
    if target is None:
        raise IllegalActionError(f"找不到目標：{target_id}")
    problem = maneuver_problem(ctx.state, unit, target)
    if problem is not None:
        raise IllegalActionError(problem)
    return target


def _do_shove(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Shove)
    cost = action_ap_cost(ctx.state, unit, modifiers.SHOVE)
    _require_ap(unit, cost)
    target = _maneuver_target(ctx, unit, action.target_id)
    problem = shove_problem(ctx.state, unit, target)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= cost
    distance, extra = shove_split(ctx.state, unit, target)
    if contest(ctx, "shove", unit, target, Attribute.STR):
        execute(
            ctx,
            [
                PushEffect(
                    source_id=unit.id,
                    target_id=target.id,
                    direction=_direction(unit.xy, target.xy),
                    distance=distance,
                    extra_collisions=extra,
                )
            ],
        )


def _do_trip(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Trip)
    cost = action_ap_cost(ctx.state, unit, modifiers.TRIP)
    _require_ap(unit, cost)
    target = _maneuver_target(ctx, unit, action.target_id)
    if target.has_status(PRONE):
        raise IllegalActionError(f"目標已經倒地：{target.name_zh}")
    unit.ap -= cost
    if contest(ctx, "trip", unit, target, Attribute.DEX):
        execute(ctx, [ApplyStatusEffect(target_id=target.id, status_id=PRONE, source_id=unit.id)])


def _do_interact(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, Interact)
    cost = action_ap_cost(ctx.state, unit, modifiers.INTERACT)
    _require_ap(unit, cost)
    obj = _live_object(ctx.state, action.object_id)
    problem = interact_problem(ctx.state, unit, obj, action.mode, action.side)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.ap -= cost
    execute(
        ctx,
        [
            PushEffect(
                source_id=unit.id,
                object_id=obj.id,
                direction=interact_direction(unit.xy, obj.xy, action.mode, action.side),
                distance=1,
                how=action.mode,
            )
        ],
    )


def _do_end_stance(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, EndStance)
    stances = stance_status_ids(ctx.rules, unit)
    if not stances:
        raise IllegalActionError(f"{unit.name_zh} 目前沒有姿態可以取消")
    execute(
        ctx,
        [
            RemoveStatusEffect(target_id=unit.id, status_id=status_id, reason="stance_ended")
            for status_id in stances
        ],
    )


def reaction_mode_problem(unit: UnitState, reaction: str) -> str | None:
    """``set_reaction_mode`` 的問題：只能改自己身上已有的反應規則（不在 ``legal_actions``）。"""
    if all(rule.reaction != reaction for rule in unit.reactions):
        return f"{unit.name_zh} 沒有反應規則：{reaction}"
    return None


def _do_set_reaction_mode(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, SetReactionMode)
    problem = reaction_mode_problem(unit, action.reaction)
    if problem is not None:
        raise IllegalActionError(problem)
    unit.reactions = tuple(
        rule.model_copy(update={"mode": action.mode}) if rule.reaction == action.reaction else rule
        for rule in unit.reactions
    )
    ctx.emit(ReactionModeSet, unit_id=unit.id, reaction=action.reaction, mode=action.mode)


def _do_end_turn(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, EndTurn)
    end_turn(ctx)
    advance_turn(ctx)


def _do_use_skill(ctx: Ctx, unit: UnitState, action: Action) -> None:
    assert isinstance(action, UseSkill)
    use_skill(ctx, unit, action)


ACTION_HANDLERS: dict[str, ActionHandler] = {
    "move": _do_move,
    "attack": _do_attack,
    "defend": _do_defend,
    "shove": _do_shove,
    "trip": _do_trip,
    "interact": _do_interact,
    "use_skill": _do_use_skill,
    "end_stance": _do_end_stance,
    "set_reaction_mode": _do_set_reaction_mode,
    "end_turn": _do_end_turn,
}


def resolve_with(
    base: BattleState,
    action: Action,
    decisions: tuple[bool, ...] = (),
    *,
    preview: PreviewMode | None = None,
    gamble: GambleBranch | None = None,
) -> ResolveResult:
    """內部 API：以 ``decisions`` 結算 ``action``（``preview`` 不為 ``None`` 時為預覽模擬；
    ``gamble`` 指定預覽時賭注的分支，Phase 3D-7a）。"""
    ctx = Ctx(base.clone(), decisions=decisions, preview=preview, gamble=gamble)
    actor = ctx.state.units[action.unit_id]
    try:
        ACTION_HANDLERS[action.type](ctx, actor, action)
    except PauseForDecision as pause:
        assert preview is None
        paused = ctx.state
        pending = pause.pending
        paused.pending = PendingResolution(
            action_json=ACTION_ADAPTER.dump_json(action).decode("utf-8"),
            decisions=decisions,
            base_state_json=state_to_json(base),
            events_emitted=len(ctx.events),
            kind=pending.kind,
            unit_id=pending.unit_id,
            reaction=pending.reaction,
            trigger_unit_id=pending.trigger_unit_id,
            skill_id=pending.skill_id,
            copy_skill_id=pending.copy_skill_id,
            trigger_event_seq=pending.trigger_event_seq,
            stamina_cost=pending.stamina_cost,
            mana_cost=pending.mana_cost,
            hp_cost_permille=pending.hp_cost_permille,
        )
        return ResolveResult(paused, ctx.events, pending)
    return finish_resolution(ctx)


def simulate_preview(
    base: BattleState, action: Action, gamble: GambleBranch | None = None
) -> tuple[ResolveResult, ResolveResult]:
    """內部 API：預覽用的「最少後果」與「最多後果」兩次模擬。

    ``min`` 模擬沒有經過任何分歧點（擲骰、檢定、反應決定、強制命中結果）時，``max`` 的結果必定
    相同，直接重用而不再模擬一次（例如沒有藉機攻擊、沒有踩上冰面的移動）。
    """
    low_ctx = Ctx(base.clone(), preview="min", gamble=gamble)
    ACTION_HANDLERS[action.type](low_ctx, low_ctx.state.units[action.unit_id], action)
    low = finish_resolution(low_ctx)
    if not low_ctx.preview_branched():
        return low, low
    return low, resolve_with(base, action, preview="max", gamble=gamble)


def resolve(state: BattleState, action: Action) -> ResolveResult:
    """結算 ``action``，回傳新狀態、事件與 ``pending``。

    ``pending`` 只在等待 ``prompt`` 反應的決定時不為 ``None``。

    不修改傳入的 ``state``。不合法時拋出 :class:`IllegalActionError`。
    """
    _actor(state, action)
    return resolve_with(state, action)


def resume(state: BattleState, decision: Decision) -> ResolveResult:
    """回答暫停中的 ``prompt`` 反應並繼續結算；只回傳暫停之後的事件。不修改傳入的 ``state``。"""
    pending = state.pending
    if pending is None:
        raise IllegalActionError("目前沒有等待中的決定")
    if decision.unit_id != pending.unit_id:
        who = state.units[pending.unit_id].name_zh
        raise IllegalActionError(f"現在等待的是 {who} 的決定")
    base = state_from_json(pending.base_state_json)
    action = ACTION_ADAPTER.validate_json(pending.action_json)
    if pending.kind == "copy_skill":
        return _resume_copy(base, action, decision)
    if pending.kind == "followup" and decision.accept:
        return _resume_followup(state, pending, action, decision)
    result = resolve_with(base, action, (*pending.decisions, decision.accept))
    return ResolveResult(result.state, result.events[pending.events_emitted :], result.pending)


def _resume_copy(base: BattleState, action: Action, decision: Decision) -> ResolveResult:
    """回答 ``copy_skill`` 的選目標（Phase 3C-4b）：放棄時回到施放之前（沒有付任何代價）；否則帶
    著 ``decision.copy_cast`` 重新結算原本的 ``UseSkill``。選取不合法時拋出
    ``IllegalActionError``，暫停中的狀態不變。"""
    if not decision.accept:
        return ResolveResult(base, [], None)
    assert isinstance(action, UseSkill)
    if decision.copy_cast is None:
        raise IllegalActionError("必須指定複製技能的目標（或放棄施放）")
    return resolve_with(base, action.model_copy(update={"copy_cast": decision.copy_cast}))


def _resume_followup(
    state: BattleState, pending: PendingResolution, action: Action, decision: Decision
) -> ResolveResult:
    """接受複合技能第二段的選目標（Phase 3F-4a）：先在暫停的狀態（第一段已結算）檢查
    ``decision.followup_target``，不合法時拋出 ``IllegalActionError``、暫停不變；合法就帶著它
    重新結算原本的 ``UseSkill``（第一段的結果相同），只回傳暫停之後的事件。放棄（``accept=False``）
    走一般的決定流程：重新結算時第二段取用這個決定，發出 ``followup_declined``。"""
    assert isinstance(action, UseSkill)
    pick = decision.followup_target
    if pick is None:
        raise IllegalActionError("必須指定第二段的目標（或放棄第二段）")
    caster = state.units[pending.unit_id]
    skill = modifiers.acting_skill(state, caster, action.skill_id)
    problem = second_problem(state, caster, skill, pick)
    if problem is not None:
        raise IllegalActionError(problem)
    base = state_from_json(pending.base_state_json)
    result = resolve_with(
        base, action.model_copy(update={"followup_target": pick}), pending.decisions
    )
    return ResolveResult(result.state, result.events[pending.events_emitted :], result.pending)


# ---------------------------------------------------------------------------
# 合法動作
# ---------------------------------------------------------------------------


def legal_actions(state: BattleState) -> list[Action]:
    """目前行動者的所有合法動作（確定性順序）。

    順序：攻擊單位（依目標 ID）→ 攻擊物件（依物件 ID）→ 推擊 → 絆倒（依目標 ID）→ 技能 →
    互動（依物件 ID）→ 防禦 → 取消姿態（有姿態時）→ 移動（每個可達格一條最短路徑，依
    ``(y, x)``；倒地時另含「只站起來」）→ 結束回合。``resolve`` 接受任何合法路徑，這裡每個目的地
    只列一條代表路徑。
    暫停中（``pending``）時回傳空串列。
    """
    return legal_actions_with_areas(state)[0]


def legal_actions_with_areas(
    state: BattleState, *, expand_copy: bool = False
) -> tuple[list[Action], dict[int, SkillArea]]:
    """:func:`legal_actions`，另外回傳每個技能動作的影響範圍（以 ``id(action)`` 為鍵）。

    AI 評分技能時需要影響範圍；一併取得可以省下重複計算 :func:`compute_area`。

    ``expand_copy``（Phase 3C-4b，AI 用）：``copy_skill`` 技能依複製技能的每個合法選取各列一個
    完整動作（``UseSkill.copy_cast`` 已填，影響範圍是複製技能的）；預設只列一個沒有
    ``copy_cast`` 的動作，由玩家在結算暫停時再選目標。
    """
    unit = state.active
    if state.ended or unit is None or state.pending is not None:
        return [], {}
    areas: dict[int, SkillArea] = {}
    return _legal_actions(state, unit, areas, expand_copy=expand_copy), areas


def _legal_actions(
    state: BattleState, unit: UnitState, areas: dict[int, SkillArea], *, expand_copy: bool = False
) -> list[Action]:
    core = state.ruleset.core
    actions: list[Action] = []
    if unit.ap >= action_ap_cost(state, unit, modifiers.ATTACK):
        actions.extend(
            Attack(unit_id=unit.id, target_id=target.id)
            for target in state.living_units()
            if attack_problem(state, unit, target) is None
        )
        actions.extend(
            Attack(unit_id=unit.id, target_object_id=obj.id)
            for obj in state.objects_sorted()
            if object_attack_problem(state, unit, obj) is None
        )
    can_shove = unit.ap >= action_ap_cost(state, unit, modifiers.SHOVE)
    can_trip = unit.ap >= action_ap_cost(state, unit, modifiers.TRIP)
    if can_shove or can_trip:
        foes = [t for t in state.living_units() if maneuver_problem(state, unit, t) is None]
        if can_shove:
            actions.extend(
                Shove(unit_id=unit.id, target_id=t.id)
                for t in foes
                if shove_problem(state, unit, t) is None
            )
        if can_trip:
            actions.extend(
                Trip(unit_id=unit.id, target_id=t.id) for t in foes if not t.has_status(PRONE)
            )
    actions.extend(_skill_actions(state, unit, areas, expand_copy=expand_copy))
    actions.extend(interact_actions(state, unit))
    if unit.ap >= core.defend_ap_cost and not unit.has_status(DEFENDING):
        actions.append(Defend(unit_id=unit.id))
    if stance_status_ids(state.ruleset, unit):
        actions.append(EndStance(unit_id=unit.id))
    budget = available_move_budget(state, unit)
    if can_only_stand_up(state, unit):
        actions.append(Move(unit_id=unit.id, path=(unit.pos,)))
    elif budget is not None:
        if unit.has_status(PRONE):
            actions.append(Move(unit_id=unit.id, path=(unit.pos,)))
        pm = path_map(state, unit, budget)
        ends = sorted((xy for xy in pm.cost if pm.can_end_at(xy)), key=lambda p: (p[1], p[0]))
        for xy in ends:
            # 座標物件共用快取（Pos 不可變）
            path = tuple(_pos(x, y) for x, y in pm.path_to(xy))
            actions.append(Move(unit_id=unit.id, path=path))
    actions.append(EndTurn(unit_id=unit.id))
    return actions


def _usable_skills(state: BattleState, unit: UnitState) -> list[SkillDef]:
    skills = [modifiers.acting_skill(state, unit, sid) for sid in sorted(unit.all_skills)]
    return [s for s in skills if s.is_actionable and skill_problem(state, unit, s) is None]


def _skill_actions(
    state: BattleState, unit: UnitState, areas: dict[int, SkillArea], *, expand_copy: bool
) -> list[Action]:
    """可用的技能動作：依技能 ID，再依選取（目標 ID／座標／方向）排序。"""
    actions: list[Action] = []
    for skill in _usable_skills(state, unit):
        for action, area in selections(state, unit, skill):
            if expand_copy and has_copy_effect(skill):
                for copy, copy_area in copy_selections(state, unit):
                    full = action.model_copy(update={"copy_cast": copy})
                    actions.append(full)
                    areas[id(full)] = copy_area
                continue
            actions.append(action)
            areas[id(action)] = area
    return actions


_POS_CACHE: dict[XY, Pos] = {}


def _pos(x: int, y: int) -> Pos:
    """共用的 ``Pos``（不可變，可安全共用）。"""
    pos = _POS_CACHE.get((x, y))
    if pos is None:
        pos = _POS_CACHE[(x, y)] = Pos(x=x, y=y)
    return pos


def has_only_end_turn(state: BattleState) -> bool:
    """``legal_actions(state)`` 是否只剩 ``EndTurn``（不建立動作列表的快速版本）。

    驅動迴圈用它判斷是否自動結束回合。戰鬥已結束或暫停中時回傳 ``False``。
    """
    unit = state.active
    if state.ended or unit is None or state.pending is not None:
        return False
    if stance_status_ids(state.ruleset, unit):
        return False  # 還可以取消姿態（EndStance）
    return not (_has_ap_action(state, unit) or _can_move(state, unit))


def _has_ap_action(state: BattleState, unit: UnitState) -> bool:
    core = state.ruleset.core
    if unit.ap >= core.defend_ap_cost and not unit.has_status(DEFENDING):
        return True
    if unit.ap >= action_ap_cost(state, unit, modifiers.ATTACK):
        if any(attack_problem(state, unit, t) is None for t in state.living_units()):
            return True
        if any(object_attack_problem(state, unit, o) is None for o in state.objects_sorted()):
            return True
    can_shove = unit.ap >= action_ap_cost(state, unit, modifiers.SHOVE)
    can_trip = unit.ap >= action_ap_cost(state, unit, modifiers.TRIP)
    if (can_shove or can_trip) and any(
        maneuver_problem(state, unit, t) is None
        and (
            (can_trip and not t.has_status(PRONE))
            or (can_shove and shove_problem(state, unit, t) is None)
        )
        for t in state.living_units()
    ):
        return True
    if any(has_selection(state, unit, s) for s in _usable_skills(state, unit)):
        return True
    return bool(interact_actions(state, unit))


def _can_move(state: BattleState, unit: UnitState) -> bool:
    if can_only_stand_up(state, unit):
        return True
    budget = available_move_budget(state, unit)
    if budget is None:
        return False
    if unit.has_status(PRONE):
        return True  # 至少可以只站起來
    if budget == 0:
        return False
    pm = path_map(state, unit, budget)
    return any(pm.can_end_at(xy) for xy in pm.cost)
