"""效用 AI 的位置價值：戰術指令的有效化、場面快照（:class:`_Scene`）、走路步數與
:func:`position_value`。

自 :mod:`trpg.engine.ai.utility` 拆出（Phase R1c），內容未改。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import (
    AiWeights,
    OrderBonuses,
)
from trpg.engine.actions import (
    Action,
)
from trpg.engine.ai.leader import far_from_leader_extra
from trpg.engine.ai.objective import objective_cost
from trpg.engine.ai.orders import (
    FocusTarget,
    HoldPosition,
    Protect,
    RetreatTo,
    TacticalOrder,
    UseEnvironment,
    validate_order,
)
from trpg.engine.ai.parts import (
    behind_spot,
    circle_back_extra,
    giant_part_spot_extra,
    guard_back_extra,
    silent_behind_extra,
)
from trpg.engine.ai.weapon_range import (
    best_distance,
    damage_permille_at,
    is_close_range,
    is_far_range,
)
from trpg.engine.ai.zone import hostile_zone_at
from trpg.engine.effects.world import unit_push_block
from trpg.engine.formation import formation_permille
from trpg.engine.ids import BOSS_TAG, SHIELD_GUARD
from trpg.engine.preview import Preview
from trpg.engine.rules.combat import (
    HALF_COVER,
    attack_problem,
    cover_object_between,
    guard_between,
    guard_blocks,
    is_concealed,
    is_height_limited,
    protects_ranged,
)
from trpg.engine.rules.facing import FACING_VECTORS, facing_between
from trpg.engine.rules.footprint import adjacent, dist_to, nearest_tile, tiles_of, unit_dist
from trpg.engine.rules.geometry import (
    XY,
    axis_direction,
    has_line_of_sight,
    manhattan,
    neighbors4,
)
from trpg.engine.rules.movement import (
    is_deadly,
    is_standable,
    step_cost,
)
from trpg.engine.rules.race import fall_immune
from trpg.engine.rules.statuses import forced_target_sources
from trpg.engine.skills.conditions import is_flanked
from trpg.engine.state import BattleState, UnitState
from trpg.engine.weapon_traits import pierce_line_targets
from trpg.shared.types import ObjectId, Surface, UnitId

_KEEP_DISTANCE = 2
_PERMILLE_AI = 1000
_FORMATION_STEP = 100
"""陣法站位：倍率每 100‰ 算 1 單位的 ``formation`` 權重（Phase 5A-M2）。"""
_DOWNED_PENALTY = 1000
_ESCAPED_BONUS = 1000


type OrdersSource = Callable[[BattleState, UnitId], tuple[TacticalOrder, ...]]
"""``(狀態, 行動者 ID) -> 該單位適用的戰術指令``（見 :mod:`trpg.engine.ai.orders`）。"""


@dataclass(frozen=True, slots=True)
class OrderContext:
    """一次決策中，行動者適用的有效戰術指令（已驗證）與加成數值。"""

    bonuses: OrderBonuses
    focus: UnitId | None = None
    hold: tuple[XY, int] | None = None
    retreat: XY | None = None
    ward: UnitId | None = None
    env: bool = False


def resolve_orders(
    state: BattleState,
    unit: UnitState,
    orders: tuple[TacticalOrder, ...],
    bonuses: OrderBonuses,
) -> OrderContext | None:
    """濾掉無效指令（:func:`~trpg.engine.ai.orders.validate_order`；保護自己也無效），
    全部無效或沒有指令時回傳 ``None``（此時評分與沒有指令完全相同）。"""
    focus: UnitId | None = None
    hold: tuple[XY, int] | None = None
    retreat: XY | None = None
    ward: UnitId | None = None
    env = False
    for order in orders:
        if validate_order(state, unit.team, order) is not None:
            continue
        match order:
            case FocusTarget(target=target):
                focus = target
            case HoldPosition(at=at, radius=radius):
                hold = (at, radius)
            case RetreatTo(at=at):
                retreat = at
            case Protect(ward=target) if target != unit.id:
                ward = target
            case UseEnvironment():
                env = True
            case _:
                pass
    if focus is None and hold is None and retreat is None and ward is None and not env:
        return None
    return OrderContext(bonuses, focus, hold, retreat, ward, env)


def _order_weights(w: AiWeights, orders: OrderContext | None) -> AiWeights:
    """指令調整後的權重：撤退時 ``approach``、``threat`` 視為 0；保護時 ``protect`` 至少為
    ``protect_min``。"""
    if orders is None:
        return w
    update: dict[str, int] = {}
    if orders.retreat is not None:
        update.update(approach=0, threat=0)
    if orders.ward is not None:
        update["protect"] = max(w.protect, orders.bonuses.protect_min)
    return w.model_copy(update=update) if update else w


@dataclass(frozen=True, slots=True)
class ActionScore:
    action: Action
    score: Fraction
    preview: Preview | None


def _enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    return [u for u in state.living_units() if u.team is not unit.team]


def _taunter(state: BattleState, unit: UnitState) -> UnitState | None:
    """嘲諷 ``unit`` 的敵人（``forces_target`` 狀態的來源，還在場上時）；沒有時為 ``None``。"""
    for uid in sorted(forced_target_sources(state.ruleset, unit)):
        source = state.units.get(uid)
        if source is not None and source.alive and source.team is not unit.team:
            return source
    return None


def _harmful(state: BattleState, xy: tuple[int, int]) -> bool:
    surface = state.tile(*xy).surface
    if surface is Surface.NONE:
        return False
    definition = state.ruleset.surface_def(surface)
    start = definition.on_turn_start
    enter = definition.on_enter
    if start is not None:
        if start.damage is not None and start.damage.only_tag is None:
            return True
        if start.apply_status is not None:
            return True
    return enter is not None and enter.apply_status is not None


def _ward(state: BattleState, unit: UnitState, orders: OrderContext | None = None) -> XY | None:
    """最需要保護的友方（HP 比例最低，同比例依 ID）的位置；沒有其他友方時為 ``None``。
    保護指令（``orders.ward``）指定了對象時固定用它。"""
    if orders is not None and orders.ward is not None:
        return state.units[orders.ward].xy
    allies = [u for u in state.living_units() if u.team is unit.team and u.id != unit.id]
    if not allies:
        return None
    return min(allies, key=lambda u: (Fraction(u.hp, u.max_hp), u.id)).xy


def position_value(
    state: BattleState,
    unit_id: UnitId,
    w: AiWeights,
    orders: OrderContext | None = None,
    *,
    walk: _Walk | None = None,
) -> Fraction:
    """行動者在 ``state`` 中所在位置的價值（``orders``：戰術指令的調整，見
    :func:`resolve_orders`；``walk``：同一次決策共用的走路步數，省略時重新計算）。"""
    unit = state.units[unit_id]
    return _unit_position_value(
        state, unit, _order_weights(w, orders), _scene(state, unit, orders, walk)
    )


class _Walk:
    """一次決策開始時，每名敵人到各格的走路步數（只看地形與物件，不看單位；單位走路的
    規則見 :func:`~trpg.engine.rules.movement.step_cost`）。

    動作後的狀態裡，敵人若被推開，沿用原位置的步數再加上被推開的距離；動作後新出現的單位
    （召喚物）沒有步數，改用曼哈頓距離。
    """

    __slots__ = ("dist", "origin")

    def __init__(self, state: BattleState, enemies: list[UnitState]) -> None:
        self.origin: dict[UnitId, XY] = {e.id: e.xy for e in enemies}
        self.dist: dict[UnitId, dict[XY, int]] = {
            e.id: _steps_to(state, tiles_of(e)) for e in enemies
        }

    def to(self, enemy: UnitState, xy: XY) -> int | None:
        """``xy`` 走到 ``enemy`` 的步數；不連通時為 ``None``，沒有紀錄的單位用曼哈頓距離。"""
        steps = self.dist.get(enemy.id)
        if steps is None:
            return dist_to(enemy, xy)
        base = steps.get(xy)
        if base is None:
            return None
        return base + dist_to(enemy, self.origin[enemy.id])


def _steps_to(state: BattleState, targets: tuple[XY, ...]) -> dict[XY, int]:
    """從 ``targets``（單位的佔格；巨型單位是 9 格，走到任一佔格旁就算到，GB-1b）反向的廣度優先
    搜尋：每個能走到那裡的格子的步數。"""
    dist = dict.fromkeys(targets, 0)
    queue = deque(targets)
    while queue:
        cur = queue.popleft()
        for nxt in neighbors4(state, cur):
            if (
                nxt not in dist
                and is_standable(state, nxt)
                and step_cost(state, nxt, cur) is not None
            ):
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)
    return dist


def _approach_distance(scene: _Scene, xy: XY) -> int:
    """``xy`` 到最近敵人（有集火目標時為目標）的距離：走得到的敵人用走路步數，全都走不到時
    退回曼哈頓距離。"""
    targets = scene.enemies if scene.focus is None else [scene.focus]
    walk = scene.walk
    if walk is not None:
        steps = [d for e in targets if (d := walk.to(e, xy)) is not None]
        if steps:
            return min(steps)
    return min(dist_to(e, xy) for e in targets)


def _boss_distance(unit: UnitState, scene: _Scene, xy: XY) -> int:
    """近戰單位到最近 Boss 的距離（BAL-9 ``boss_approach``）；非近戰武器、沒有 Boss、有集火
    目標時為 0。"""
    if scene.focus is not None or not unit.weapon.is_melee:
        return 0
    bosses = [e for e in scene.enemies if BOSS_TAG in e.tags]
    if not bosses:
        return 0
    walk = scene.walk
    best: int | None = None
    for boss in bosses:
        d = walk.to(boss, xy) if walk is not None else None
        d = dist_to(boss, xy) if d is None else d
        best = d if best is None else min(best, d)
    return best or 0


@dataclass(frozen=True, slots=True)
class _Scene:
    """同一次決策中不隨行動者位置改變的資料（虛擬移動評分時共用）。"""

    enemies: list[UnitState]
    ward: XY | None
    orders: OrderContext | None = None
    focus: UnitState | None = None
    """集火目標（還在場上時）；``approach`` 改以它計算。"""
    walk: _Walk | None = None


def _scene(
    state: BattleState,
    unit: UnitState,
    orders: OrderContext | None = None,
    walk: _Walk | None = None,
) -> _Scene:
    """決策的共用資料；``walk`` 省略時重新計算（一次決策內請共用同一個）。"""
    focus = None
    if orders is not None and orders.focus is not None:
        target = state.units.get(orders.focus)
        if target is not None and target.alive:
            focus = target
    taunter = _taunter(state, unit)
    if taunter is not None:  # 嘲諷優先於集火指令：接近改以嘲諷者計算
        focus = taunter
    enemies = _enemies(state, unit)
    if walk is None and enemies:
        walk = _Walk(state, enemies)
    return _Scene(enemies, _ward(state, unit, orders), orders, focus, walk)


def _enemy_terms(state: BattleState, unit: UnitState, w: AiWeights, scene: _Scene) -> int:
    """位置價值中與敵人有關的部分：接近、威脅、保持距離、掩護、被壓制、夾擊（Phase 3D-8c）。"""
    xy, enemies = unit.xy, scene.enemies
    value = -w.approach * _approach_distance(scene, xy)
    if w.boss_approach:
        value -= w.boss_approach * _boss_distance(unit, scene, xy)
    if w.threat:
        value += w.threat * sum(1 for e in enemies if attack_problem(state, unit, e) is None)
    if w.keep_distance:
        # 隱蔽的敵人必須走到 2 格內才打得到（concealed_ranged_max_distance），所以遠程單位為了
        # 攻擊而進入 2 格內不扣分；否則兩名隱蔽的弓手會互相等待到平手（dark_forest 種子 7）
        keep = _keep_radius(unit)
        close = sum(1 for e in enemies if dist_to(e, xy) <= keep and not is_concealed(state, e))
        value -= w.keep_distance * close
    if w.cover:
        value += w.cover * _covered_from(state, unit, xy, enemies)
    if w.screen and unit.has_tag(SHIELD_GUARD):  # 盾兵（RG-1）：站到遠程同伴前面
        value += w.screen * _screened_allies(state, unit, xy, enemies)
    if w.exposed:
        value -= w.exposed * _outgunned_by(state, unit, enemies)
    if w.flank:
        value += w.flank * _flanked_count(state, unit, enemies)
    if w.giant_spot_bonus:  # GB-3：巨型頭目的部位站位
        value += giant_part_spot_extra(state, unit, w, enemies)
    if w.prefer_far_from_leader:  # GB-3（T17）：殼縫餘燼蜥追離頭目遠的人
        value += far_from_leader_extra(state, unit, w, enemies)
    return value + _facing_terms(state, unit, w, enemies) + _weapon_terms(state, unit, w, enemies)


def _keep_radius(unit: UnitState) -> int:
    """保持距離的半徑：一般 2 格；近距離武器（BAL-5 B19，霰彈槍）只避開比最佳距離更近的敵人。"""
    weapon = unit.weapon
    if not is_close_range(weapon, _KEEP_DISTANCE):
        return _KEEP_DISTANCE
    best = best_distance(weapon)
    return _KEEP_DISTANCE if best is None else best - 1


def _close_range_term(
    state: BattleState, unit: UnitState, w: AiWeights, enemies: list[UnitState]
) -> int:
    """近距離武器的站位（BAL-5 B19）：打得到的敵人中距離傷害千分比最高者 × ``close_range``
    ÷ 1000。"""
    weapon = unit.weapon
    weight = 0
    if w.close_range and is_close_range(weapon, _KEEP_DISTANCE):
        weight = w.close_range
    elif w.far_range and is_far_range(weapon, _KEEP_DISTANCE):
        weight = w.far_range  # 遠距加成武器（BAL-8 火槍）：同樣的算式，偏好遠距
    if not weight:
        return 0
    best = max(
        (
            damage_permille_at(weapon, unit_dist(unit, e))
            for e in enemies
            if attack_problem(state, unit, e) is None
        ),
        default=0,
    )
    return weight * best // _PERMILLE_AI


def _knock_collides(state: BattleState, unit: UnitState, enemy: UnitState) -> bool:
    """``unit`` 從現在的位置普攻相鄰的 ``enemy`` 並震退時，會不會撞到東西或掉進致命地形。"""
    direction = axis_direction(enemy.xy[0] - unit.xy[0], enemy.xy[1] - unit.xy[1])
    if direction is None or attack_problem(state, unit, enemy) is not None:
        return False
    nxt = (enemy.xy[0] + direction[0], enemy.xy[1] + direction[1])
    if unit_push_block(state, enemy.xy, nxt, enemy.id) is not None:
        return True
    return is_deadly(state, nxt)


def _weapon_terms(
    state: BattleState, unit: UnitState, w: AiWeights, enemies: list[UnitState]
) -> int:
    """位置價值中與武器特性有關的部分（Phase 3-24a1）：長柄武器偏好在觸及距離出手（不貼臉）、
    震退武器偏好能撞擊的角度。"""
    weapon = unit.weapon
    value = 0
    if w.reach_spacing and weapon.is_melee and weapon.range > 1:
        for e in enemies:
            distance = unit_dist(unit, e)
            if distance == 1:
                value -= w.reach_spacing
            elif distance <= weapon.range and attack_problem(state, unit, e) is None:
                value += w.reach_spacing
    if w.line_up and weapon.pierce_line > 0:
        value += w.line_up * max(
            (
                len(pierce_line_targets(state, unit, e))
                for e in enemies
                if attack_problem(state, unit, e) is None
            ),
            default=0,
        )
    if w.knock_angle and weapon.knockback > 0:
        value += w.knock_angle * sum(
            1 for e in enemies if adjacent(unit, e) and _knock_collides(state, unit, e)
        )
    return value + _close_range_term(state, unit, w, enemies)


def _facing_terms(
    state: BattleState, unit: UnitState, w: AiWeights, enemies: list[UnitState]
) -> int:
    """位置價值中與朝向有關的部分（Phase 3D-8d，敵我同一套）：近戰單位站在相鄰敵人的背後格
    （背刺位置）加分；背對相鄰的近戰敵人扣分——結束移動時的朝向以「面向最近的敵人」近似
    （同距離取 ID 較小者），背後格站著近戰敵人時扣 ``back_exposed``；有部位的頭目背後部位快破時
    再多扣 ``guard_back_bonus``（PB-1b，:func:`~trpg.engine.ai.parts.guard_back_extra`）；玩家方近戰
    站在「背後有能打的部位」的頭目背後格加 ``circle_back_bonus``（PB-1b2 繞背，
    :func:`~trpg.engine.ai.parts.circle_back_extra`）。"""
    value = circle_back_extra(unit, w, enemies) if w.circle_back_bonus else 0
    if w.silent_behind:  # BS-1：無聲留背
        value += silent_behind_extra(state, unit, w, enemies)
    if w.backstab and unit.weapon.is_melee:
        # GB-3：貼著巨型頭目「算從背後」的部位格（殼縫）也算背刺位置（behind_spot）
        value += w.backstab * sum(
            1 for e in enemies if adjacent(unit, e) and behind_spot(unit.xy, e)
        )
    if w.back_exposed:
        nearest = min(enemies, key=lambda e: (unit_dist(unit, e), e.id))
        facing = facing_between(unit.xy, nearest.xy)
        if facing is not None:
            dx, dy = FACING_VECTORS[facing]
            back = state.unit_at(unit.xy[0] - dx, unit.xy[1] - dy)
            if back is not None and back.team is not unit.team and back.weapon.is_melee:
                value -= w.back_exposed + guard_back_extra(unit, w)  # 背後部位快破（PB-1b）
    return value


def _unit_position_value(
    state: BattleState, unit: UnitState, w: AiWeights, scene: _Scene | None = None
) -> Fraction:
    """``unit`` 的位置價值；``unit`` 可以是「放到別的格子」的虛擬複本（位置以 ``unit.xy`` 為準，
    其他單位以 ``state`` 為準）。``scene`` 為同一決策中共用的敵人清單與保護對象。"""
    if unit.escaped:
        return Fraction(_ESCAPED_BONUS * max(w.objective, 1))
    if unit.downed:
        return Fraction(-_DOWNED_PENALTY)
    if scene is None:
        scene = _scene(state, unit)
    xy = unit.xy
    value = _enemy_terms(state, _loaded(unit), w, scene) if scene.enemies else 0
    value += w.height * state.tile(*xy).height
    if w.light_body_height and fall_immune(state.ruleset, unit):  # 輕身（#138）：主動找高處
        value += w.light_body_height * state.tile(*xy).height
    if w.protect and scene.ward is not None:
        value -= w.protect * manhattan(xy, scene.ward)
    value -= objective_cost(state, unit, w)
    if scene.orders is not None:
        value -= _order_penalty(scene.orders, xy)
    if _harmful(state, xy) or (state.zones and hostile_zone_at(state, xy, unit.team)):
        value -= w.hazard  # 有害表面，或敵方會傷害自己的持續區域（Phase 3D-5）
    if w.formation:  # 陣法（Phase 5A-M2）：待在同門範圍內，落單扣分
        value += w.formation * (formation_permille(state, unit) - _PERMILLE_AI) // _FORMATION_STEP
    return Fraction(value)


def _loaded(unit: UnitState) -> UnitState:
    """位置價值用的「已裝填」複本（BAL-5 B19）：彈匣空的武器只差 1 AP 的裝填，站位的威脅、近距離、
    被壓制等仍以裝填後計算；否則開火讓彈匣變空，位置價值就像「打不到任何敵人」，單發火器（霰彈槍、
    火槍）的普攻分數被扣成負的而不開火。"""
    if unit.weapon.magazine <= 0 or unit.ammo > 0:
        return unit
    loaded = unit.clone()
    loaded.ammo = unit.weapon.magazine
    return loaded


def _flanked_count(state: BattleState, unit: UnitState, enemies: list[UnitState]) -> int:
    """``unit`` 目前位置緊貼著、而且對面站著友方（夾擊，Phase 3D-8c）的敵人數。"""
    return sum(1 for e in enemies if adjacent(unit, e) and is_flanked(state, unit, e))


def _order_penalty(orders: OrderContext, xy: XY) -> int:
    """守位與撤退指令的位置扣分。"""
    penalty = 0
    if orders.hold is not None:
        at, radius = orders.hold
        penalty += orders.bonuses.hold_weight * max(0, manhattan(xy, at) - radius)
    if orders.retreat is not None:
        penalty += orders.bonuses.retreat_weight * manhattan(xy, orders.retreat)
    return penalty


def _outgunners(state: BattleState, unit: UnitState, enemies: list[UnitState]) -> list[UnitState]:
    """現在就能攻擊到 ``unit``、而 ``unit`` 打不到的敵人（射程更長、或被煙幕與隱蔽遮住）。
    雙方互相打得到的對射不算，所以不會讓弓手不敢進入射擊位置。"""
    return [
        e
        for e in enemies
        if unit_dist(e, unit) <= e.weapon.range
        and attack_problem(state, e, unit) is None
        and attack_problem(state, unit, e) is not None
    ]


def _outgunned_by(state: BattleState, unit: UnitState, enemies: list[UnitState]) -> int:
    return len(_outgunners(state, unit, enemies))


def _covered_from(state: BattleState, unit: UnitState, xy: XY, enemies: list[UnitState]) -> int:
    """在射程內看得到 ``xy``、且從其位置看過來 ``xy`` 受到半掩護的敵人數。

    射程外的敵人不算：掩護只在對方打得到自己時才有意義。否則雙方各躲在掩護後、彼此都在射程外時，
    離開掩護的扣分會壓過 ``approach`` 的收益，造成永遠不接近的僵局（``lava_crossing`` 種子 19）。

    盾兵掩護（RG-1）也算：``unit`` 是遠程、同陣營的盾兵擋在那個敵人那一側（只對遠程敵人）。
    """
    guarded = state.ruleset.core.shield_guard_hit_penalty > 0 and protects_ranged(state, unit)
    return sum(
        1
        for e in enemies
        if dist_to(e, xy) <= e.weapon.range
        and (
            cover_object_between(state, nearest_tile(e, xy), xy) is not None
            or (
                guarded
                and not is_height_limited(state, e)
                and guard_between(state, nearest_tile(e, xy), unit, at=xy) is not None
            )
        )
        and has_line_of_sight(state, nearest_tile(e, xy), xy, lob=e.weapon.lob, viewer=e)
    )


def _screened_allies(state: BattleState, unit: UnitState, xy: XY, enemies: list[UnitState]) -> int:
    """盾兵（RG-1，#162）站在 ``xy`` 時替幾名相鄰的遠程同伴擋住至少一名打得到他們的遠程敵人
    （幾何同 :func:`~trpg.engine.rules.combat.guard_blocks`；同伴以 ``state`` 的位置為準）。"""
    if state.ruleset.core.shield_guard_hit_penalty <= 0:
        return 0
    shooters = [e for e in enemies if not is_height_limited(state, e)]
    count = 0
    for ally in state.units_sorted():
        if (
            ally.id == unit.id
            or not ally.alive
            or ally.team is not unit.team
            or dist_to(ally, xy) != 1
            or not protects_ranged(state, ally)
        ):
            continue
        if any(
            unit_dist(e, ally) <= e.weapon.range
            and guard_blocks(state, nearest_tile(e, ally.xy), ally.xy, xy)
            for e in shooters
        ):
            count += 1
    return count


def _in_cover(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 四方向相鄰處有未摧毀的半掩護物件（「躲在掩護後」）。"""
    for nxt in neighbors4(state, unit.xy):
        oid = state.tile(*nxt).object_id
        if oid is not None and HALF_COVER in state.ruleset.object_def(state.objects[oid].kind).tags:
            return True
    return False


def _cover_objects_near_enemies(state: BattleState, actor: UnitState) -> set[ObjectId]:
    """緊鄰（四方向）敵人的半掩護物件。"""
    result: set[ObjectId] = set()
    for e in _enemies(state, actor):
        for nxt in neighbors4(state, e.xy):
            oid = state.tile(*nxt).object_id
            if (
                oid is not None
                and HALF_COVER in state.ruleset.object_def(state.objects[oid].kind).tags
            ):
                result.add(oid)
    return result
