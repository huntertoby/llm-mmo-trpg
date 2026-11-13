"""種族技的結算（Phase 3R-2，``docs/design/07-角色成長.md`` 7.7；資料 ``content/races.yaml``）。

種族技是 **動作** ``use_race_skill``，不是技能：不佔技能欄、不經技能解譯器。1 AP、每場限用
``uses_per_battle`` 次（次數記在 ``UnitState.skill_uses``，鍵為種族技 ID）。種族技的效果是 3R-1 的
**封閉效果清單**（:data:`trpg.content.races.RACE_EFFECT_SPECS`），本模組把它們對映到現有的效果原語
（最少新程式的做法）：

=========================  =========================================================
效果                       對映
=========================  =========================================================
``bonus_move``             直接加移動點數
``ignore_opportunity_attack``  狀態 ``race_adapt``（``reactions.opportunity_attacks`` 略過）
``conceal_self``           ``apply_status concealed``
``decoy``                  誘餌單位（:func:`spawn_decoy`；``try_intercept`` 攔下單體攻擊）
``push``／``pull``         ``PushEffect(harmless=True)``（被擋住只停下；``pull`` 不吃獸人減距）
``immovable``              狀態 ``race_stonewall``（``world.push_distance``、``apply_status``）
``restore_choice``         直接回復耐力或法力
``hurl_object``            ``HurlObjectEffect``（不加傷害，其餘照物件規則）
``create_surface``         ``CreateSurfaceEffect``
``leap``                   ``MoveUnitEffect(mode="leap")``（獸躍，#138；:func:`leap_problem`）
=========================  =========================================================

**獸躍**（``leap``，07 7.7 實作細節第 6 點）：跳到 ``range`` 格（曼哈頓）內任一空格——可以平移、
往上最多 ``max_rise`` 層、往下不限；不付移動點數、不觸發藉機攻擊（藉機攻擊只在步行離開相鄰格時
觸發）。「不能越過牆」寫成 :func:`leap_path_clear`：從起點到落點要有一條 **最短路徑**（每一步都讓
曼哈頓距離少 1）中間的格子都不是牆——牆壁地形、同時擋行動與視線的物件（石柱、土牆、冰牆、枯樹），
或比起點高出 ``max_rise`` 層以上的地形（跳不上去的高度也越不過去）；單位、矮牆、木箱這類只擋行動
的物件、深淵與岩漿的缺口都可以越過。不看視線。落地用 ``leap`` 移動：往下 2 層以上照常墜落
（獸耳族有「輕身」，不受傷也不發墜落事件，:func:`trpg.engine.rules.race.fall_immune`）、觸發落點的
陷阱與表面。

合法性檢查（:func:`race_skill_problem`）與列舉（:func:`race_skill_actions`）共用同一組規則，
``legal_actions`` 與 API 因此一致。引擎禁止亂數以外的非確定性：這裡完全不擲骰。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from trpg.content.library import Ruleset
from trpg.content.races import RaceEffect, RaceSkill
from trpg.engine.actions import Direction, UseRaceSkill
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CreateSurfaceEffect,
    EffectBase,
    HurlObjectEffect,
    MoveUnitEffect,
    PushEffect,
)
from trpg.engine.events import RaceSkillUsed, UnitSummoned
from trpg.engine.ids import CONCEALED, DECOY_TAG, RACE_ADAPT, RACE_STONEWALL
from trpg.engine.lifecycle import dismiss_summon, make_unit
from trpg.engine.rules.combat import concealment_problem
from trpg.engine.rules.footprint import dist_to, touches, unit_dist
from trpg.engine.rules.geometry import XY, axis_direction, has_line_of_sight, manhattan
from trpg.engine.rules.landing import LandingBlock, landing_problem
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.rules.statuses import prevents_concealment
from trpg.engine.skills import shapes
from trpg.engine.skills.mobility import self_move_problem
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons.core import insert_in_order, owner_order_index
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import ObjectId, Pos, Surface, UnitId

__all__ = [
    "RACE_EFFECT_EXECUTORS",
    "RACE_EFFECT_PROBLEMS",
    "UNCONDITIONAL_RACE_EFFECTS",
    "decoy_template_ids",
    "do_race_skill",
    "leap_path_clear",
    "leap_problem",
    "race_skill_actions",
    "race_skill_of",
    "race_skill_problem",
    "race_uses_left",
]


_SHAPE_FIELDS: dict[str, tuple[str, ...]] = {
    "self": (),
    "ground_tile": ("target_pos",),
    "square3": ("target_pos",),
    "cone": ("direction",),
    "single": ("target_id",),
    "object_then_tile": ("target_object_id", "target_pos"),
}
"""各形狀（``skill_shapes.yaml``）需要的選取欄位；``restore_choice`` 另外需要 ``choice``。"""
_DIRECTIONS: tuple[Direction, ...] = ("north", "east", "south", "west")
_ALL_FIELDS = ("target_id", "target_object_id", "target_pos", "direction", "choice")


def race_skill_of(state: BattleState, unit: UnitState) -> RaceSkill | None:
    """``unit`` 的種族技；沒有種族時為 ``None``（種族 ID 不存在時拋 ``KeyError``）。"""
    if unit.race is None:
        return None
    return state.ruleset.race_def(unit.race).skill


def decoy_template_ids(rules: Ruleset) -> frozenset[str]:
    """所有種族的誘餌召喚物範本 ID（敘事用來認出誘餌的召喚事件）。"""
    if rules.races is None:
        return frozenset()
    return frozenset(
        e.summon
        for race in rules.races.races
        for e in race.skill.effects
        if e.type == "decoy" and e.summon is not None
    )


def race_uses_left(unit: UnitState, skill: RaceSkill) -> int:
    """本場還能用幾次。"""
    return max(0, skill.uses_per_battle - unit.skill_uses.get(skill.id, 0))


def _reach(skill: RaceSkill) -> int:
    """選取的射程：形狀的 ``range``（種族技的形狀都明寫整數）。"""
    reach = skill.shape.range
    return reach if isinstance(reach, int) else 0


def _required_fields(skill: RaceSkill) -> tuple[str, ...]:
    """選取欄位：形狀需要的，加上任何一個 ``restore_choice`` 效果需要的 ``choice``。"""
    fields = _SHAPE_FIELDS.get(skill.shape.type, ())
    needs_choice = any(e.type == "restore_choice" for e in skill.effects)
    return (*fields, "choice") if needs_choice else fields


def _field_problem(skill: RaceSkill, action: UseRaceSkill) -> str | None:
    required = _required_fields(skill)
    for name in _ALL_FIELDS:
        given = getattr(action, name) is not None
        if name in required and not given:
            return f"{skill.name_zh}必須指定 {name}"
        if given and name not in required:
            return f"{skill.name_zh}不能指定 {name}"
    return None


def race_skill_problem(state: BattleState, unit: UnitState, action: UseRaceSkill) -> str | None:
    """種族技不合法的原因（繁體中文）；合法時 ``None``。順序：有沒有種族技、AP、次數、選取欄位、
    各效果自己的條件（依效果順序，每個效果都檢查，回傳第一個不成立的）。"""
    skill = race_skill_of(state, unit)
    if skill is None:
        return f"{unit.name_zh} 沒有種族技"
    if unit.ap < skill.ap_cost:
        return f"AP 不足：需要 {skill.ap_cost}，剩餘 {unit.ap}"
    if race_uses_left(unit, skill) <= 0:
        return f"{skill.name_zh}本場已用完（限用 {skill.uses_per_battle} 次）"
    problem = _field_problem(skill, action)
    if problem is not None:
        return problem
    for effect in skill.effects:
        checker = RACE_EFFECT_PROBLEMS.get(effect.type)
        problem = None if checker is None else checker(state, unit, skill, effect, action)
        if problem is not None:
            return problem
    return None


# ---------------------------------------------------------------------------
# 各效果的合法性
# ---------------------------------------------------------------------------


def _conceal_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    _action: UseRaceSkill,
) -> str | None:
    if prevents_concealment(state.ruleset, unit):
        return "被揭露中，不能隱蔽"
    if unit.has_status(CONCEALED):
        return "已經在隱蔽中"
    tile = state.tile(*unit.xy)
    requires = effect.requires or ()
    in_grass = "grass" in requires and state.object_has_tag(*unit.xy, "conceal")
    in_dark = "darkness" in requires and tile.surface is Surface.DARKNESS
    if not (in_grass or in_dark):
        return "必須站在草叢或黑暗中才能隱蔽"
    return None


def _tile_problem(state: BattleState, unit: UnitState, xy: XY, reach: int) -> str | None:
    """選取格的共通檢查：地圖內、射程、視線、不是牆壁（:func:`shapes.center_problem`）。"""
    return shapes.center_problem(state, unit.xy, xy, reach)


def _decoy_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    assert action.target_pos is not None
    xy = (action.target_pos.x, action.target_pos.y)
    problem = _tile_problem(state, unit, xy, effect.range or 0)
    if problem is not None:
        return problem
    if state.unit_at(*xy) is not None:
        return f"{xy} 已經有單位"
    if not is_standable(state, xy) or is_deadly(state, xy):
        return f"{xy} 不能放置誘餌"
    return None


def _push_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    assert action.direction is not None
    if not _cone_targets(state, unit, skill, action.direction):
        return "錐形範圍內沒有可以推開的單位"
    return None


def _pull_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    assert action.target_id is not None
    target = state.units.get(action.target_id)
    if target is None or not target.alive:
        return "目標已不在戰場上"
    if target.team is unit.team:
        return "只能拉敵人"
    reach = _reach(skill)
    distance = unit_dist(unit, target)
    if distance > reach:
        return f"目標超出射程：距離 {distance}，射程 {reach}"
    if distance <= 1:
        return "目標已經在身旁"
    if not has_line_of_sight(state, unit.xy, target.xy, viewer=unit):
        return f"視線被阻擋：{unit.name_zh} 看不到 {target.name_zh}"
    return concealment_problem(state, unit, target)


def _hurl_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    assert action.target_object_id is not None and action.target_pos is not None
    obj = state.objects.get(action.target_object_id)
    if obj is None or obj.destroyed:
        return f"找不到物件：{action.target_object_id}"
    definition = state.object_def(obj)
    reach = effect.range or 0
    if "pushable" not in definition.tags:
        return f"{definition.name_zh}無法投擲（不是可推動的物件）"
    distance = dist_to(unit, obj.xy)
    if distance > reach:
        return f"物件超出投擲距離：距離 {distance}，上限 {reach}"
    if not has_line_of_sight(state, unit.xy, obj.xy):
        return f"視線被阻擋：{unit.name_zh} 看不到 {definition.name_zh}"
    dest = (action.target_pos.x, action.target_pos.y)
    if dest == obj.xy:
        return "落點不能是物件原本的格子"
    return _tile_problem(state, unit, dest, reach)


def _surface_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    if skill.shape.type == "self":
        return None
    assert action.target_pos is not None
    center = (action.target_pos.x, action.target_pos.y)
    return _tile_problem(state, unit, center, _reach(skill))


def leap_blocks_at(state: BattleState, xy: XY, top: int) -> bool:
    """獸躍越不過 ``xy``：牆壁地形、同時擋行動與視線的物件（石柱、土牆、冰牆、枯樹），或高於 ``top``
    層的地形。單位、只擋行動的物件（矮牆、木箱、倒木）、深淵與岩漿都不擋。"""
    if shapes.is_wall(state, xy) or state.tile(*xy).height > top:
        return True
    return state.object_has_tag(*xy, "blocks_move") and state.object_has_tag(*xy, "blocks_sight")


def leap_path_clear(state: BattleState, start: XY, dest: XY, top: int) -> bool:
    """從 ``start`` 到 ``dest`` 有沒有一條最短路徑（四方向、每一步都讓曼哈頓距離少 1），中間的格子
    （不含兩端）都不被 :func:`leap_blocks_at` 擋住。``top``：中間格可以越過的最高高度。

    在兩點圍成的長方形裡做單調路徑的動態規劃（確定性，與列舉順序無關）。"""
    width, height = abs(dest[0] - start[0]), abs(dest[1] - start[1])
    sx = 1 if dest[0] >= start[0] else -1
    sy = 1 if dest[1] >= start[1] else -1
    reach: dict[tuple[int, int], bool] = {}
    for j in range(height + 1):
        for i in range(width + 1):
            if i == 0 and j == 0:
                reach[(i, j)] = True
                continue
            cell = (start[0] + sx * i, start[1] + sy * j)
            inner = (i, j) != (width, height)
            if inner and leap_blocks_at(state, cell, top):
                reach[(i, j)] = False
                continue
            reach[(i, j)] = reach.get((i - 1, j), False) or reach.get((i, j - 1), False)
    return reach[(width, height)]


def _leap_reach_problem(
    state: BattleState, unit: UnitState, effect: RaceEffect, dest: XY
) -> str | None:
    """獸躍的前提與距離：能不能動（定身、倒地、速度 0）、地圖範圍、不是原地、在射程內。"""
    problem = self_move_problem(state, unit)
    if problem is not None:
        return problem
    if unit.speed == 0:
        return f"{unit.name_zh} 不能移動"
    if not state.in_bounds(*dest):
        return f"超出地圖範圍：{dest}"
    distance = dist_to(unit, dest)
    if distance == 0:
        return "不能跳到原地"
    reach = effect.range or 0
    if distance > reach:
        return f"目標超出射程：距離 {distance}，射程 {reach}"
    return None


def leap_problem(state: BattleState, unit: UnitState, effect: RaceEffect, dest: XY) -> str | None:
    """獸躍跳到 ``dest`` 不合法的原因（繁體中文）；合法時 ``None``。順序：能不能動、地圖範圍、
    原地、射程、落點（可站、沒有單位、不是致命地形）、高度（最多往上 ``max_rise`` 層）、路徑
    （不越過牆）。"""
    problem = _leap_reach_problem(state, unit, effect, dest)
    if problem is not None:
        return problem
    block = landing_problem(state, dest, mover=unit.id)
    if block is LandingBlock.OCCUPIED:
        return f"{dest} 已經有單位"
    if block is not None or is_deadly(state, dest):
        return f"{dest} 不能站立"
    start_height = state.tile(*unit.xy).height
    rise = state.tile(*dest).height - start_height
    max_rise = effect.max_rise or 0
    if rise > max_rise:
        return f"太高了：高 {rise} 層（最多往上 {max_rise} 層）"
    if not leap_path_clear(state, unit.xy, dest, start_height + max_rise):
        return f"中間隔著牆，跳不過去：{dest}"
    return None


def _leap_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    assert action.target_pos is not None
    return leap_problem(state, unit, effect, (action.target_pos.x, action.target_pos.y))


def _restore_problem(
    state: BattleState,
    unit: UnitState,
    skill: RaceSkill,
    effect: RaceEffect,
    action: UseRaceSkill,
) -> str | None:
    if action.choice not in (effect.resources or ()):
        return f"只能選擇回復{'或'.join(effect.resources or ())}"
    current, maximum = _resource(unit, action.choice)
    if maximum <= 0:
        return "沒有這項資源"
    if current >= maximum:
        return "這項資源已經是滿的"
    return None


def _resource(unit: UnitState, choice: str | None) -> tuple[int, int]:
    return (unit.stamina, unit.max_stamina) if choice == "stamina" else (unit.mana, unit.max_mana)


type _Problem = Callable[[BattleState, UnitState, RaceSkill, RaceEffect, UseRaceSkill], str | None]

RACE_EFFECT_PROBLEMS: dict[str, _Problem] = {
    "conceal_self": _conceal_problem,
    "decoy": _decoy_problem,
    "push": _push_problem,
    "pull": _pull_problem,
    "hurl_object": _hurl_problem,
    "create_surface": _surface_problem,
    "restore_choice": _restore_problem,
    "leap": _leap_problem,
}
UNCONDITIONAL_RACE_EFFECTS = frozenset({"bonus_move", "ignore_opportunity_attack", "immovable"})
"""沒有額外合法性條件的效果類型（只受 AP、次數、選取欄位限制）；其餘類型必須在
:data:`RACE_EFFECT_PROBLEMS` 有檢查函式（``primitive_coverage`` 檢查）。"""


# ---------------------------------------------------------------------------
# 列舉
# ---------------------------------------------------------------------------


def _tile_candidates(state: BattleState, unit: UnitState, skill: RaceSkill) -> list[XY]:
    """選一格的候選（依 ``(y, x)``）：一般是看得到的中心格；獸躍不看視線，射程內每一格都列
    （合法性由 :func:`leap_problem` 判斷）。"""
    reach = _reach(skill)
    if not any(e.type == "leap" for e in skill.effects):
        return shapes.center_candidates(state, unit.xy, reach)
    x0, y0 = unit.xy
    return [
        (x, y)
        for y in range(max(0, y0 - reach), min(state.height, y0 + reach + 1))
        for x in range(max(0, x0 - reach), min(state.width, x0 + reach + 1))
        if 0 < manhattan(unit.xy, (x, y)) <= reach
    ]


def _candidates(state: BattleState, unit: UnitState, skill: RaceSkill) -> Iterator[UseRaceSkill]:
    """依形狀列舉候選動作（確定性順序：方向、單位 ID、物件 ID、格子 ``(y, x)``）。"""
    uid = unit.id
    shape = skill.shape.type
    restore = next((e for e in skill.effects if e.type == "restore_choice"), None)
    if restore is not None:
        for choice in restore.resources or ():
            yield UseRaceSkill(unit_id=uid, choice=choice)
    elif shape == "self":
        yield UseRaceSkill(unit_id=uid)
    elif shape == "cone":
        for direction in _DIRECTIONS:
            yield UseRaceSkill(unit_id=uid, direction=direction)
    elif shape == "single":
        for target in state.units_sorted():
            yield UseRaceSkill(unit_id=uid, target_id=UnitId(target.id))
    elif shape in ("ground_tile", "square3"):
        for x, y in _tile_candidates(state, unit, skill):
            yield UseRaceSkill(unit_id=uid, target_pos=Pos(x=x, y=y))
    elif shape == "object_then_tile":
        tiles = shapes.center_candidates(state, unit.xy, _reach(skill))
        for obj in state.objects_sorted():
            for x, y in tiles:
                yield UseRaceSkill(
                    unit_id=uid, target_object_id=ObjectId(obj.id), target_pos=Pos(x=x, y=y)
                )


def race_skill_actions(state: BattleState, unit: UnitState) -> list[UseRaceSkill]:
    """目前合法的種族技動作（沒有種族、AP 不足或次數用完時為空）。"""
    skill = race_skill_of(state, unit)
    if skill is None or unit.ap < skill.ap_cost or race_uses_left(unit, skill) <= 0:
        return []
    return [
        a for a in _candidates(state, unit, skill) if race_skill_problem(state, unit, a) is None
    ]


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------


def _cone_targets(
    state: BattleState, unit: UnitState, skill: RaceSkill, direction: str
) -> list[UnitState]:
    """錐形內的單位（不含施放者），由遠到近、同距離依 ID（遠的先推，近的才有位置可退）。"""
    size = skill.shape.size or 0
    cells = set(shapes.cone_tiles(state, unit.xy, direction, size))
    found = [u for u in state.living_units() if u.id != unit.id and touches(u, cells)]
    return sorted(found, key=lambda u: (-unit_dist(unit, u), u.id))


def spawn_decoy(ctx: Ctx, owner: UnitState, xy: XY, skill_id: str) -> UnitState:
    """在 ``xy`` 放狐火誘餌：同一個主人同時只有一個（舊的消失）；排在主人之後的先攻順序。"""

    state = ctx.state
    skill = race_skill_of(state, owner)
    assert skill is not None
    effect = next(e for e in skill.effects if e.type == "decoy")
    assert effect.summon is not None and effect.lifetime is not None  # 內容驗證保證
    for old in state.units_sorted():
        if old.owner_id == owner.id and old.has_tag(DECOY_TAG) and old.alive:
            dismiss_summon(ctx, old, "limit")
    summon = state.ruleset.summon_def(effect.summon)
    uid = UnitId(f"unit_{len(state.units) + 1:04d}")
    unit = make_unit(
        uid,
        template=summon.template,
        weapon=summon.weapon,
        team=owner.team,
        pos=Pos(x=xy[0], y=xy[1]),
        name=summon.template.name_zh,
        rules=state.ruleset,
        facing=owner.facing,
        resource_attributes=owner.attributes,  # 資源上限的屬性由施放者推得（BAL-15b，6.29）
    )
    unit.owner_id = owner.id
    unit.level = owner.level
    unit.summon_mode = "hold"
    unit.summon_expires_round = state.round + effect.lifetime
    unit.initiative = owner.initiative
    state.units[uid] = unit
    index = owner_order_index(state, owner.id)
    insert_in_order(state, uid, index)
    ctx.emit(
        UnitSummoned,
        unit_id=uid,
        owner_id=owner.id,
        template_id=effect.summon,
        team=owner.team,
        pos=unit.pos,
        skill_id=skill_id,
        expires_round=unit.summon_expires_round,
        order_index=index,
        orphan=False,
        max_hp=unit.max_hp,
        infusion=None,
    )
    return unit


def _do_bonus_move(ctx: Ctx, unit: UnitState, effect: RaceEffect, _a: UseRaceSkill) -> None:
    unit.move_points += effect.amount or 0


def _do_adapt(ctx: Ctx, unit: UnitState, _e: RaceEffect, _a: UseRaceSkill) -> None:
    execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=RACE_ADAPT, source_id=unit.id)])


def _do_conceal(ctx: Ctx, unit: UnitState, _e: RaceEffect, _a: UseRaceSkill) -> None:
    execute(ctx, [ApplyStatusEffect(target_id=unit.id, status_id=CONCEALED, source_id=unit.id)])


def _do_decoy(ctx: Ctx, unit: UnitState, _e: RaceEffect, action: UseRaceSkill) -> None:
    assert action.target_pos is not None
    skill = race_skill_of(ctx.state, unit)
    assert skill is not None
    spawn_decoy(ctx, unit, (action.target_pos.x, action.target_pos.y), skill.id)


def _do_push(ctx: Ctx, unit: UnitState, effect: RaceEffect, action: UseRaceSkill) -> None:
    assert action.direction is not None
    skill = race_skill_of(ctx.state, unit)
    assert skill is not None
    vector = shapes.DIRECTIONS[action.direction]
    batch: list[EffectBase] = [
        PushEffect(
            source_id=unit.id,
            target_id=target.id,
            direction=vector,
            distance=effect.distance or 0,
            harmless=True,
        )
        for target in _cone_targets(ctx.state, unit, skill, action.direction)
    ]
    for push in batch:  # 由遠到近一個一個推（遠的先讓出位置，近的才推得動）
        execute(ctx, [push])


def _do_pull(ctx: Ctx, unit: UnitState, effect: RaceEffect, action: UseRaceSkill) -> None:
    assert action.target_id is not None
    target = ctx.state.units[action.target_id]
    direction = axis_direction(unit.xy[0] - target.xy[0], unit.xy[1] - target.xy[1])
    if direction is None:
        return
    pull = PushEffect(
        source_id=unit.id,
        target_id=target.id,
        direction=direction,
        distance=effect.distance or 0,
        pull=True,
        harmless=True,
    )
    execute(ctx, [pull])


def _do_stonewall(ctx: Ctx, unit: UnitState, effect: RaceEffect, _a: UseRaceSkill) -> None:
    status = ApplyStatusEffect(
        target_id=unit.id, status_id=RACE_STONEWALL, duration=effect.duration, source_id=unit.id
    )
    execute(ctx, [status])


def _do_restore(ctx: Ctx, unit: UnitState, effect: RaceEffect, action: UseRaceSkill) -> None:
    amount = effect.amount or 0
    if action.choice == "stamina":
        unit.stamina = min(unit.max_stamina, unit.stamina + amount)
    else:
        unit.mana = min(unit.max_mana, unit.mana + amount)


def _do_hurl(ctx: Ctx, unit: UnitState, _e: RaceEffect, action: UseRaceSkill) -> None:
    assert action.target_object_id is not None and action.target_pos is not None
    hurl = HurlObjectEffect(
        source_id=unit.id,
        object_id=action.target_object_id,
        dest=(action.target_pos.x, action.target_pos.y),
        ignite=False,
    )
    execute(ctx, [hurl])


def _do_surface(ctx: Ctx, unit: UnitState, effect: RaceEffect, action: UseRaceSkill) -> None:
    assert effect.surface is not None
    skill = race_skill_of(ctx.state, unit)
    assert skill is not None
    if skill.shape.type == "square3":
        assert action.target_pos is not None
        tiles = shapes.square3_tiles(ctx.state, (action.target_pos.x, action.target_pos.y))
    else:
        tiles = (unit.xy,)
    execute(
        ctx,
        [
            CreateSurfaceEffect(
                source_id=unit.id,
                pos=xy,
                surface=effect.surface,
                duration=effect.duration,
                team=unit.team,
            )
            for xy in tiles
        ],
    )


def _do_leap(ctx: Ctx, unit: UnitState, _e: RaceEffect, action: UseRaceSkill) -> None:
    assert action.target_pos is not None
    dest = (action.target_pos.x, action.target_pos.y)
    execute(ctx, [MoveUnitEffect(source_id=unit.id, unit_id=unit.id, dest=dest, mode="leap")])


type _Executor = Callable[[Ctx, UnitState, RaceEffect, UseRaceSkill], None]

RACE_EFFECT_EXECUTORS: dict[str, _Executor] = {
    "bonus_move": _do_bonus_move,
    "ignore_opportunity_attack": _do_adapt,
    "conceal_self": _do_conceal,
    "decoy": _do_decoy,
    "push": _do_push,
    "pull": _do_pull,
    "immovable": _do_stonewall,
    "restore_choice": _do_restore,
    "hurl_object": _do_hurl,
    "create_surface": _do_surface,
    "leap": _do_leap,
}


def do_race_skill(ctx: Ctx, unit: UnitState, action: UseRaceSkill) -> None:
    """結算 ``use_race_skill``：驗證、付 1 AP、記一次使用、依序結算每個效果。"""
    problem = race_skill_problem(ctx.state, unit, action)
    if problem is not None:
        raise IllegalActionError(problem)
    skill = race_skill_of(ctx.state, unit)
    assert skill is not None and unit.race is not None
    unit.ap -= skill.ap_cost
    unit.skill_uses[skill.id] = unit.skill_uses.get(skill.id, 0) + 1
    ctx.emit(
        RaceSkillUsed,
        unit_id=unit.id,
        race_id=unit.race,
        skill_id=skill.id,
        target_id=action.target_id,
        target_object_id=action.target_object_id,
        target_pos=action.target_pos,
        direction=action.direction,
        choice=action.choice,
        uses_left=race_uses_left(unit, skill),
    )
    for effect in skill.effects:
        RACE_EFFECT_EXECUTORS[effect.type](ctx, unit, effect, action)
