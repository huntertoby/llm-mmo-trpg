"""效用評分 AI（``docs/專案計畫.md`` 5.9）：對每個合法動作跑 ``preview`` 評分，取最高分。

分數 ＝ 預覽收益 ＋ 命中率 × Σ 權重 × (動作後的位置價值 − 動作前的位置價值)，權重來自
``content/ai_profiles.yaml`` 的行為模式（莽夫、弓手、狡猾、守衛）。分數為正的動作中取最高者，
平手依 ``legal_actions`` 的順序；沒有正分的動作時結束回合。全部以 :class:`~fractions.Fraction`
計算，完全確定。

收益的估計：攻擊主要目標的傷害用預覽的精確期望值；其他傷害（爆炸、擴散……）取最少與最多後果
的平均再乘上命中率；「確定」的連鎖乘上命中率，「只是可能」的擊倒再除以 4。這些是啟發式，
供 Phase 2 以模擬調整。

掩護（Phase 1C）：位置價值的 ``cover`` 為「看得到、且從其位置看過來我受到半掩護」的敵人數；
收益的 ``expose`` 為動作讓幾名敵人離開掩護（被推離或掩護物被摧毀），``cover_damage`` 為對
「緊鄰敵人的掩護物」造成的每點傷害。

接近（Phase 2C-4）：位置價值的 ``approach`` 用「走路的步數」（繞過牆、深淵、岩漿，不看單位）而不是
曼哈頓距離。否則隔著河的雙方，在橋被燒斷、只剩一條繞遠的陸路時，任何一步繞路都會讓距離變大而
沒有正分，永遠不會接近（``lava_crossing`` 的平手）。走路步數每次決策只算一次（:class:`_Walk`）。

效能（Phase 1C 決定 #1）：每次決策只算一次「動作前」的位置價值；``Move`` 先以「直接把行動者放到
目的地」的位置價值（不跑引擎）排序，只保留前 ``move_candidates`` 個（``ai_profiles.yaml``）；
其中有風險的移動（可能被藉機攻擊、踩上有進入效果的表面、墜落、撤離、倒地站起）才跑完整
``preview``。沒有風險的移動結果是確定的（只有位置改變），其分數與完整預覽算出的分數相同。
``preview`` 本身在最少後果的模擬沒有經過分歧點時也只模擬一次。

技能（Phase 2A）：每個技能的選取先以便宜的估計（:func:`skill_estimate`）篩選與排序，每種技能只保留
前 ``skill_candidates`` 個跑完整 ``preview``；分數＝預覽收益（每個目標各自的命中率與期望傷害、治療
實際補到的量、友方誤傷與讓友方站上有害表面的扣分、擊倒對抗的成功率）＋位置價值的變化 −
法力與冷卻的機會成本（``mana``、``cooldown`` 權重）。場地型技能（煙幕、石牆、隱匿）沒有敵人在範圍
內也是候選：只要它可能改變自己的處境（涵蓋自己的格子、或擋在敵人與自己之間），由位置價值的差決定
值不值得。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import AiProfile, AiProfileTable, AiWeights, OrderBonuses
from trpg.content.skills import SkillDef
from trpg.engine.actions import (
    Action,
    Attack,
    Defend,
    EndStance,
    EndTurn,
    Move,
    Shove,
    Trip,
    UseSkill,
)
from trpg.engine.ai.orders import (
    FocusTarget,
    HoldPosition,
    Protect,
    RetreatTo,
    TacticalOrder,
    UseEnvironment,
    validate_order,
)
from trpg.engine.battle import legal_actions, legal_actions_with_areas
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    ObjectDamaged,
    ShieldGained,
    StatusApplied,
    StatusRemoved,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.preview import DamageRange, Preview, preview
from trpg.engine.rules.combat import (
    HALF_COVER,
    attack_problem,
    cover_object_between,
    is_concealed,
)
from trpg.engine.rules.geometry import (
    XY,
    bresenham,
    chebyshev,
    has_line_of_sight,
    manhattan,
    neighbors4,
)
from trpg.engine.rules.movement import is_standable, step_cost
from trpg.engine.rules.statuses import forced_target_sources, shield_amount, stance_status_ids
from trpg.engine.skills.targeting import ResolvedEffect, SkillArea, hp_cost, resolve_effects
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import ObjectId, Surface, Team, UnitId

__all__ = [
    "ActionScore",
    "OrderContext",
    "OrdersSource",
    "UtilityAI",
    "defend_score",
    "is_risky_move",
    "position_value",
    "reactive_enemies",
    "resolve_orders",
    "score_action",
    "virtual_move_score",
    "worth_previewing",
]

_DEFEND_RADIUS = 6
_KEEP_DISTANCE = 2
_POSSIBLE_KILL_DIVISOR = 4
_DOWNED_PENALTY = 1000
_ESCAPED_BONUS = 1000
_ATTACK_CAUSES = ("attack",)
_PRONE = "prone"
_SURFACE_HARM = 8
"""讓友方站上有害的新表面的扣分：相當於這麼多點傷害（乘上 ``friendly_fire``）。"""


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


def _objective_distance(state: BattleState, unit: UnitState) -> int:
    objective = state.objective
    if objective.kind == "eliminate" or not objective.tiles:
        return 0
    if objective.kind == "escape" and unit.team is not Team.ALLY:
        return 0
    return min(manhattan(unit.xy, t) for t in objective.tiles)


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
        self.dist: dict[UnitId, dict[XY, int]] = {e.id: _steps_to(state, e.xy) for e in enemies}

    def to(self, enemy: UnitState, xy: XY) -> int | None:
        """``xy`` 走到 ``enemy`` 的步數；不連通時為 ``None``，沒有紀錄的單位用曼哈頓距離。"""
        steps = self.dist.get(enemy.id)
        if steps is None:
            return manhattan(xy, enemy.xy)
        base = steps.get(xy)
        if base is None:
            return None
        return base + manhattan(self.origin[enemy.id], enemy.xy)


def _steps_to(state: BattleState, target: XY) -> dict[XY, int]:
    """從 ``target`` 反向的廣度優先搜尋：每個能走到 ``target`` 的格子的步數。"""
    dist = {target: 0}
    queue = deque([target])
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
    return min(manhattan(xy, e.xy) for e in targets)


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
    enemies = scene.enemies
    value = 0
    if enemies:
        value -= w.approach * _approach_distance(scene, xy)
        if w.threat:
            value += w.threat * sum(1 for e in enemies if attack_problem(state, unit, e) is None)
        if w.keep_distance:
            # 隱蔽的敵人必須走到 2 格內才打得到（concealed_ranged_max_distance），所以遠程單位為了
            # 攻擊而進入 2 格內不扣分；否則兩名隱蔽的弓手會互相等待到平手（dark_forest 種子 7）
            close = sum(
                1
                for e in enemies
                if manhattan(xy, e.xy) <= _KEEP_DISTANCE and not is_concealed(state, e)
            )
            value -= w.keep_distance * close
        if w.cover:
            value += w.cover * _covered_from(state, xy, enemies)
        if w.exposed:
            value -= w.exposed * _outgunned_by(state, unit, enemies)
    value += w.height * state.tile(*xy).height
    if w.protect and scene.ward is not None:
        value -= w.protect * manhattan(xy, scene.ward)
    if w.objective:
        value -= w.objective * _objective_distance(state, unit)
    if scene.orders is not None:
        value -= _order_penalty(scene.orders, xy)
    if _harmful(state, xy):
        value -= w.hazard
    return Fraction(value)


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
        if manhattan(e.xy, unit.xy) <= e.weapon.range
        and attack_problem(state, e, unit) is None
        and attack_problem(state, unit, e) is not None
    ]


def _outgunned_by(state: BattleState, unit: UnitState, enemies: list[UnitState]) -> int:
    return len(_outgunners(state, unit, enemies))


def _covered_from(state: BattleState, xy: XY, enemies: list[UnitState]) -> int:
    """在射程內看得到 ``xy``、且從其位置看過來 ``xy`` 受到半掩護的敵人數。

    射程外的敵人不算：掩護只在對方打得到自己時才有意義。否則雙方各躲在掩護後、彼此都在射程外時，
    離開掩護的扣分會壓過 ``approach`` 的收益，造成永遠不接近的僵局（``lava_crossing`` 種子 19）。
    """
    return sum(
        1
        for e in enemies
        if manhattan(e.xy, xy) <= e.weapon.range
        and cover_object_between(state, e.xy, xy) is not None
        and has_line_of_sight(state, e.xy, xy)
    )


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


def _last_cause(events: tuple[EventBase, ...]) -> dict[UnitId, str]:
    cause: dict[UnitId, str] = {}
    for e in events:
        if isinstance(e, DamageDealt):
            cause[e.target_id] = e.cause
    return cause


def _useful_damage(damage: DamageRange, hit: Fraction, hp: int) -> Fraction:
    """命中時有用的傷害：超過目標剩餘 HP 的部分是浪費（擊倒另由 ``kill`` 計分）。"""
    return min(damage.expected_if_hit, Fraction(hp)) * hit


def _has_usable_spell(state: BattleState, unit: UnitState) -> bool:
    """單位有法力足夠的法術技（不看冷卻與 AP；沉默只對這樣的單位有價值）。"""
    rules = state.ruleset
    for sid in sorted(unit.skills):
        skill = rules.skill_def(sid)
        if skill.is_active and skill.category == "spell" and unit.mana >= skill.cost.mana:
            return True
    return False


def _wasted_on(state: BattleState, status_id: str, target: UnitState) -> bool:
    """狀態對這個目標沒有價值：沉默（``blocks_spells``）施加在沒有可用法術技的單位上。"""
    return state.ruleset.status_def(status_id).blocks_spells and not _has_usable_spell(
        state, target
    )


def _status_gains(
    state: BattleState,
    actor: UnitState,
    p: Preview,
    profile: AiProfile,
    hit: Fraction,
    *,
    only: UnitId | None = None,
) -> Fraction:
    """對敵人施加狀態的收益。

    - 不需要抵抗判定的狀態（出現在 ``min`` 的 ``StatusApplied``）：``hit`` × 價值；
    - 需要抵抗判定的狀態（``TargetPreview.status_chances``）：該目標的命中率 × 施加成功率 × 價值，
      目標已帶有該狀態時不算（重複施加只是刷新）；
    - 價值：``status_values`` 有列出的狀態＝``damage`` 權重 × 等值傷害點數，其他用 ``status`` 權重；
      沉默施加在沒有可用法術技的目標上價值為 0（Phase 2D-2）。
    """
    w, values = profile.weights, profile.status_values

    def value(status_id: str, target: UnitState) -> Fraction:
        points = values.get(status_id)
        if points is not None and _wasted_on(state, status_id, target):
            return Fraction(0)
        return Fraction(w.status) if points is None else Fraction(w.damage * points)

    gains = Fraction(0)
    applied = {
        (e.target_id, e.status_id)
        for e in p.min_events
        if isinstance(e, StatusApplied)
        and e.target_id in state.units
        and state.units[e.target_id].team is not actor.team
        and (only is None or e.target_id == only)
    }
    for target_id, status_id in sorted(applied):
        gains += hit * value(status_id, state.units[target_id])
    for t in p.targets:
        if t.ally or (only is not None and t.unit_id != only):
            continue
        target = state.units[t.unit_id]
        for chance in t.status_chances:
            if not target.has_status(chance.status_id):
                gains += t.hit_chance * chance.apply_chance * value(chance.status_id, target)
    return gains


def _support_gains(state: BattleState, p: Preview, profile: AiProfile) -> Fraction:
    """友方支援的收益（Phase 2D-1）：護盾、增益與淨化。

    - 護盾：``shield`` × 實際增加的吸收量（新吸收量 − 原吸收量，下限 0；取最少與最多後果的平均）；
    - 增益（``ally_status_values``）：``support`` × 價值 × 新增的持續比例
      （新持續 − 剩餘 ÷ 新持續，下限 0；沒有預設持續的狀態＝尚未帶有時 1，已帶有 0）；
      目標在動作後倒下時為 0；
    - 淨化：``support`` × 被移除的每個狀態在 ``status_values`` 的價值（沒列出的用 3）。
    """
    w = profile.weights
    actor = state.units[p.action.unit_id]
    gains = Fraction(0)
    if w.shield:
        gained = Fraction(0)
        for events in (p.min_events, p.max_events):
            for e in events:
                if isinstance(e, ShieldGained) and state.units[e.unit_id].team is actor.team:
                    gained += max(0, e.total - shield_amount(state.ruleset, state.units[e.unit_id]))
        gains += w.shield * gained / 2
    if w.support:
        gains += _buff_gains(state, actor, p, profile)
    return gains


def _buff_gains(state: BattleState, actor: UnitState, p: Preview, profile: AiProfile) -> Fraction:
    """友方增益與淨化的收益（:func:`_support_gains` 的後半）。"""
    w = profile.weights
    gains = Fraction(0)
    after = p.min_state
    for e in p.min_events:
        if isinstance(e, StatusApplied):
            target = state.units.get(e.target_id)
            points = profile.ally_status_values.get(e.status_id)
            if target is None or target.team is not actor.team or points is None:
                continue
            if not after.units[e.target_id].alive:
                continue
            current = target.get_status(e.status_id)
            if e.duration is None:
                share = Fraction(0 if current is not None else 1)
            else:
                remaining = 0 if current is None or current.remaining is None else current.remaining
                share = Fraction(max(0, e.duration - remaining), e.duration)
            gains += w.support * points * share
        elif isinstance(e, StatusRemoved) and e.reason == "cleansed":
            target = state.units.get(e.target_id)
            if target is not None and target.team is actor.team:
                gains += w.support * profile.status_values.get(e.status_id, 3)
    return gains


def _gains(  # noqa: PLR0912, PLR0915
    state: BattleState,
    actor: UnitState,
    p: Preview,
    profile: AiProfile,
    only: UnitId | None = None,
) -> Fraction:
    """預覽收益。``only`` 給定時只計入對該單位（敵人）的收益——集火指令的加成用。"""
    w = profile.weights
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    team = actor.team
    skill_primary: dict[UnitId, bool] = {}
    if isinstance(p.action, UseSkill):
        foes = [t for t in p.targets if not t.ally]
        if foes:
            hit = sum((t.hit_chance for t in foes), Fraction(0)) / len(foes)
        skill_primary = {t.unit_id: True for t in foes if t.damage is not None}

    def is_enemy(uid: UnitId) -> bool:
        return state.units[uid].team is not team if uid in state.units else False

    primary = None
    if isinstance(p.action, Attack) and p.action.target_id is not None and p.damage is not None:
        primary = p.action.target_id
    gains = Fraction(0)
    # 傷害：主要傷害用精確期望；其他取 min/max 平均 × 命中率
    other_enemy = Fraction(0)
    env_enemy = Fraction(0)
    friendly = Fraction(0)
    for events in (p.min_events, p.max_events):
        seen: set[UnitId] = set()
        for e in events:
            if not isinstance(e, DamageDealt) or e.cause == "deadly_terrain":
                continue  # 致命地形的「傷害」是擊倒本身，由 kill／env_kill 計分
            first = e.target_id not in seen
            if e.cause == "attack" and (
                (e.target_id == primary and first) or e.target_id in skill_primary
            ):
                seen.add(e.target_id)
                continue
            if is_enemy(e.target_id):
                if only is None or e.target_id == only:
                    other_enemy += e.amount - e.absorbed  # 被護盾吸收的不算
                    if e.cause not in _ATTACK_CAUSES:
                        env_enemy += e.amount - e.absorbed
            elif e.target_id in state.units and only is None:
                friendly += e.amount - e.absorbed
    if p.damage is not None and primary is not None and (only is None or primary == only):
        gains += w.damage * _useful_damage(p.damage, hit, state.units[primary].hp)
    for t in p.targets:  # 技能：每個目標各自的命中率與期望傷害
        if t.damage is not None and not t.ally and (only is None or t.unit_id == only):
            gains += w.damage * _useful_damage(t.damage, t.hit_chance, state.units[t.unit_id].hp)
    healed = sum(Fraction(lo + hi, 2) for uid, lo, hi in p.healed if uid in state.units)
    if only is None:
        gains += w.heal * healed
        if isinstance(p.action, UseSkill):  # 防禦動作的 defending 由 ``defend`` 權重計分，不重複算
            gains += _support_gains(state, p, profile)
    gains += w.damage * hit * other_enemy / 2
    gains += w.env_damage * hit * env_enemy / 2
    gains -= w.friendly_fire * friendly / 2
    # 擊倒
    certain_down = {e.unit_id for e in p.min_events if isinstance(e, UnitDowned)}
    possible_down = {e.unit_id for e in p.max_events if isinstance(e, UnitDowned)} - certain_down
    causes = _last_cause(p.max_events) | _last_cause(p.min_events)
    for uid, factor in [(u, hit) for u in sorted(certain_down)] + [
        (u, hit / _POSSIBLE_KILL_DIVISOR) for u in sorted(possible_down)
    ]:
        if only is not None and uid != only:
            continue
        if is_enemy(uid):
            gains += w.kill * factor
            if causes.get(uid, "attack") not in _ATTACK_CAUSES:
                gains += w.env_kill * factor
        elif uid in state.units:
            gains -= w.kill * factor
    # 推擊、狀態、表面
    pushed = {
        e.unit_id
        for e in p.min_events
        if isinstance(e, UnitMoved)
        and e.mode == "forced"
        and is_enemy(e.unit_id)
        and (only is None or e.unit_id == only)
    }
    gains += w.push * hit * len(pushed)
    gains += _status_gains(state, actor, p, profile, hit, only=only)
    for t in p.targets:  # 技能附帶的擊倒：命中率 × 對抗成功率（預覽的 min 只視為失敗）
        if (
            t.knock_chance is not None
            and not t.ally
            and (only is None or t.unit_id == only)
            and not state.units[t.unit_id].has_status(_PRONE)
        ):
            gains += w.status * t.hit_chance * t.knock_chance
    after = p.min_state
    before_harm = sum(
        1
        for u in _enemies(state, actor)
        if (only is None or u.id == only) and _harmful(state, u.xy)
    )
    after_harm = sum(
        1
        for u in after.living_units()
        if u.team is not team and (only is None or u.id == only) and _harmful(after, u.xy)
    )
    gains += w.surface * hit * (after_harm - before_harm)
    if isinstance(p.action, UseSkill) and only is None:  # 讓友方站上有害的新表面（火、毒……）
        gains -= (
            w.friendly_fire
            * _SURFACE_HARM
            * (_harmed_allies(after, actor) - _harmed_allies(state, actor))
        )
    if w.expose or w.cover_damage:
        gains += _cover_gains(state, actor, p, w, hit, only)
    if isinstance(p.action, Defend) and only is None:
        near = sum(1 for e in _enemies(state, actor) if manhattan(actor.xy, e.xy) <= _DEFEND_RADIUS)
        gains += w.defend * near
    return gains


def _harmed_allies(state: BattleState, actor: UnitState) -> int:
    """站在有害表面上的友方數（不含行動者；行動者自己的位置由 ``hazard`` 計分）。"""
    return sum(
        1
        for u in state.living_units()
        if u.team is actor.team and u.id != actor.id and _harmful(state, u.xy)
    )


def _cover_gains(  # noqa: PLR0917
    state: BattleState,
    actor: UnitState,
    p: Preview,
    w: AiWeights,
    hit: Fraction,
    only: UnitId | None = None,
) -> Fraction:
    """推離掩護（``expose``）與破壞敵人的掩護物（``cover_damage``）的收益。"""
    team = actor.team
    before = sum(
        1 for e in _enemies(state, actor) if (only is None or e.id == only) and _in_cover(state, e)
    )
    exposed = Fraction(0)
    for after in (p.min_state, p.max_state):
        now = sum(
            1
            for e in after.living_units()
            if e.team is not team and (only is None or e.id == only) and _in_cover(after, e)
        )
        exposed += before - now
    gains = w.expose * hit * exposed / 2
    if w.cover_damage and only is None:
        shields = _cover_objects_near_enemies(state, actor)
        if shields:
            dealt = sum(
                e.amount
                for events in (p.min_events, p.max_events)
                for e in events
                if isinstance(e, ObjectDamaged) and e.object_id in shields
            )
            gains += w.cover_damage * hit * Fraction(dealt, 2)
    return gains


def score_action(
    state: BattleState,
    action: Action,
    profile: AiProfile,
    *,
    before: Fraction | None = None,
    orders: OrderContext | None = None,
    walk: _Walk | None = None,
) -> ActionScore:
    """單一動作的分數（``EndTurn`` 固定為 0），以完整 ``preview`` 計算。

    ``before`` 為行動者在 ``state`` 的位置價值（省略時重新計算）；``orders`` 為行動者適用的
    戰術指令（:func:`resolve_orders`；``None`` 時與沒有指令的分數完全相同）。
    """
    if isinstance(action, EndTurn):
        return ActionScore(action, Fraction(0), None)
    w = _order_weights(profile.weights, orders)
    if w is not profile.weights:
        profile = profile.model_copy(update={"weights": w})
    actor = state.units[action.unit_id]
    p = preview(state, action)
    if walk is None:
        walk = _scene(state, actor, orders).walk
    if before is None:
        before = position_value(state, actor.id, w, orders, walk=walk)
    after = position_value(p.min_state, actor.id, w, orders, walk=walk)
    # 位置變化只在動作成功時發生（攻擊、技巧動作乘上命中率／成功率）
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    score = _gains(state, actor, p, profile) + hit * (after - before)
    if orders is not None:
        score += _order_bonus(state, actor, p, profile, orders)
    if isinstance(action, UseSkill):
        score -= skill_cost(state, actor, action, w)
    return ActionScore(action, score, p)


def _order_bonus(
    state: BattleState, actor: UnitState, p: Preview, profile: AiProfile, orders: OrderContext
) -> Fraction:
    """集火與利用環境的收益加成：（倍率 − 1）× 對應的預覽收益。"""
    bonus = Fraction(0)
    if orders.focus is not None:
        extra = Fraction(orders.bonuses.focus_permille - 1000, 1000)
        bonus += extra * _gains(state, actor, p, profile, only=orders.focus)
    w = profile.weights
    if orders.env and (w.env_damage or w.env_kill or w.push or w.surface or w.expose):
        # 這些權重全是 0 的行為模式沒有環境收益可以加成（結果必為 0，省下一次 _gains）
        extra = Fraction(orders.bonuses.environment_permille - 1000, 1000)
        zeroed = {
            key: 0
            for key in (
                "damage",
                "kill",
                "status",
                "friendly_fire",
                "heal",
                "defend",
                "cover_damage",
            )
        }
        env_only = profile.model_copy(
            update={"weights": profile.weights.model_copy(update=zeroed), "status_values": {}}
        )
        bonus += extra * _gains(state, actor, p, env_only)
    return bonus


def skill_cost(state: BattleState, actor: UnitState, action: UseSkill, w: AiWeights) -> Fraction:
    """技能的機會成本：法力（不回復）、冷卻（這幾回合不能再用）與 HP 代價（算作對自己的傷害）。"""
    skill = state.ruleset.skill_def(action.skill_id)
    return Fraction(
        w.mana * skill.cost.mana
        + w.cooldown * (skill.cost.cooldown or 0)
        + w.friendly_fire * hp_cost(actor, skill)
    )


def defend_score(state: BattleState, unit: UnitState, w: AiWeights) -> Fraction:
    """防禦的分數：``defend`` × 6 格內的敵人數（防禦只替自己加上狀態，位置不變；與完整
    ``preview`` 的分數相同）。"""
    near = sum(1 for e in _enemies(state, unit) if manhattan(unit.xy, e.xy) <= _DEFEND_RADIUS)
    return Fraction(w.defend * near)


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


def skill_estimate(  # noqa: PLR0917
    state: BattleState,
    unit: UnitState,
    action: UseSkill,
    area: SkillArea,
    scene: _Scene,
    w: AiWeights,
    before: Fraction,
) -> Fraction | None:
    """技能選取（影響範圍為 ``area``）的便宜估計（不跑引擎），用來篩出每個技能最值得完整評分的
    幾個選取；``None`` 表示不納入候選（這是 ``worth_previewing`` 在技能上的對應）。

    - 含 ``teleport``：把行動者放到目標格後的位置價值變化（同 :func:`virtual_move_score`）；
    - 影響範圍內有敵方單位、可破壞物件，或（有治療的技能）受傷的友方：分數 ＝ 敵人數 × 3 ＋
      受傷友方 × 2 − 其他友方 × 3 ＋ 可破壞物件數；
    - 場地型技能（效果只作用在格子或自己身上：煙幕、石牆、隱匿……）沒有上述對象時，看它是否
      可能改變自己的處境（:func:`_field_value`）：涵蓋自己所在的格子，或擋在敵人與自己之間；
    - 其餘不納入。平手以與施放者的距離判定（近者優先，保持確定）。

    估計只決定「誰值得完整預覽」；值不值得施放由預覽的收益、位置價值的差與機會成本決定。
    """
    skill = state.ruleset.skill_def(action.skill_id)
    if skill.kind == "stance" and stance_status_ids(state.ruleset, unit):
        return None  # 已經有姿態：AI 不主動換姿態（也不主動取消，Phase 2E-2）
    if any(e.type == "teleport" for e in skill.effects) and action.target_pos is not None:
        moved = unit.clone()
        moved.pos = action.target_pos
        return _unit_position_value(state, moved, w, scene) - before
    effects = resolve_effects(state, skill)
    score = Fraction(0)
    useful = False
    for uid in area.units:
        other = state.units[uid]
        if other.team is not unit.team:
            score += 3
            useful = True
        elif _supports(state, unit, skill, effects, other):
            score += 2
            useful = True
        elif other.id != unit.id:
            score -= 3
    for xy in area.tiles:
        obj = state.object_at(*xy)
        if obj is not None and obj.hp is not None:
            score += 1
            useful = True
    if not useful:
        field = _field_value(state, unit, area.tiles, scene) if _is_field_skill(effects) else 0
        if field == 0:
            return None
        score = Fraction(field)
    return score - Fraction(manhattan(unit.xy, area.origin), 1000)


def _supports(
    state: BattleState,
    caster: UnitState,
    skill: SkillDef,
    effects: tuple[ResolvedEffect, ...],
    target: UnitState,
) -> bool:
    """技能的支援效果（治療、護盾、淨化、增益）對友方 ``target`` 有沒有用（便宜的估計）。"""
    for resolved in effects:
        helps = resolved.affects in ("allies", "all") or (
            resolved.affects == "self" and target.id == caster.id
        )
        if not helps:
            continue
        spec = skill.effects[resolved.spec_index]
        if resolved.type == "heal" and target.hp < target.max_hp:
            return True
        if resolved.type == "shield":
            return True
        if resolved.type == "cleanse" and any(
            not state.ruleset.status_def(s.status_id).beneficial for s in target.statuses
        ):
            return True
        if resolved.type == "apply_status" and spec.status is not None:
            definition = state.ruleset.status_def(spec.status)
            if not definition.beneficial:
                continue
            current = target.get_status(spec.status)
            duration = spec.duration or definition.duration
            if current is None or (
                duration is not None
                and current.remaining is not None
                and current.remaining < duration
            ):
                return True
    return False


def _is_field_skill(effects: tuple[ResolvedEffect, ...]) -> bool:
    """場地型技能：每個效果都只作用在格子或施放者自己身上。"""
    return all(e.affects in ("tiles", "self") for e in effects)


def _field_value(state: BattleState, unit: UnitState, tiles: tuple[XY, ...], scene: _Scene) -> int:
    """場地型技能的選取可能改變自己處境的程度（Phase 2A-2 決定 #2）。

    位置價值只在「有敵人打得到自己、自己卻打不到」時（``exposed``，:func:`_outgunned_by`）才會被
    煙幕與隱蔽改善，所以只看這些敵人：涵蓋自己的格子 2 分，每名這樣的敵人與自己之間的視線穿過
    影響範圍 1 分。
    """
    threats = _outgunners(state, unit, scene.enemies)
    if not threats:
        return 0
    covered = set(tiles)
    value = 2 if unit.xy in covered else 0
    for enemy in threats:
        if any(xy in covered for xy in bresenham(enemy.xy, unit.xy)[1:-1]):
            value += 1
    return value


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


def reactive_enemies(state: BattleState, unit: UnitState) -> list[XY]:
    """可能對 ``unit`` 藉機攻擊的敵人位置：存活、本輪反應次數未用完、有「敵人離開相鄰格」的
    反應規則（不檢查耐力與武器，寧可多算）。"""
    limit = state.ruleset.core.reactions_per_round
    return [
        e.xy
        for e in _enemies(state, unit)
        if e.reactions_used < limit
        and any(rule.when.event == "enemy_leaves_adjacent" for rule in e.reactions)
    ]


def is_risky_move(
    state: BattleState, unit: UnitState, move: Move, enemies: list[XY] | None = None
) -> bool:
    """移動是否可能有「位置改變」以外的後果（需要完整 ``preview`` 才能評分）。

    - 倒地（先站起來）；
    - 路徑上離開某個「本輪還能反應、且有藉機攻擊規則」的敵人的相鄰格（可能被藉機攻擊）；
    - 走上有進入效果的表面（燃燒、冰面滑倒檢定）；
    - 往下的落差達到墜落門檻；
    - 撤離勝利條件下，我方走上出口格。
    """
    if unit.has_status(_PRONE):
        return True
    if enemies is None:
        enemies = reactive_enemies(state, unit)
    rules = state.ruleset
    min_drop = rules.core.fall_damage_min_drop
    objective = state.objective
    exits = objective.tiles if objective.kind == "escape" and unit.team is Team.ALLY else ()
    path = move.path
    last = len(path) - 1
    prev_height = state.tile(path[0].x, path[0].y).height
    for i, pos in enumerate(path):
        xy = (pos.x, pos.y)
        if i < last:
            nxt = (path[i + 1].x, path[i + 1].y)
            if any(manhattan(xy, e) == 1 and manhattan(nxt, e) != 1 for e in enemies):
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


def _hits_unit(scored: ActionScore, uid: UnitId) -> bool:
    """動作的有害效果是否影響到單位 ``uid``（攻擊、推擊、絆倒的目標；技能的敵方命中目標，或
    預覽中受到傷害者）。"""
    action = scored.action
    if isinstance(action, Attack | Shove | Trip):
        return action.target_id == uid
    p = scored.preview
    if p is None or not isinstance(action, UseSkill):
        return False
    if any(t.unit_id == uid and not t.ally for t in p.targets):
        return True
    return any(
        isinstance(e, DamageDealt) and e.target_id == uid for e in (*p.min_events, *p.max_events)
    )


class UtilityAI:
    """效用評分 AI（可當作 ``Policy`` 使用：``UtilityAI(profiles)(state) -> Action``）。

    行動者的行為模式取 ``UnitState.ai_profile``；``override`` 可強制所有單位使用同一模式
    （測試用）；``move_candidates`` 可覆寫 ``ai_profiles.yaml`` 的候選移動數。
    """

    def __init__(
        self,
        profiles: AiProfileTable,
        *,
        override: str | None = None,
        move_candidates: int | None = None,
        skill_candidates: int | None = None,
        orders: OrdersSource | None = None,
    ) -> None:
        self._profiles = profiles.by_id()
        self._bonuses = profiles.orders
        self.orders: OrdersSource | None = orders
        """戰術指令的來源（Phase 2C-2）；``None`` 時完全不受指令影響。"""
        self._override = override
        self._move_candidates = (
            profiles.move_candidates if move_candidates is None else move_candidates
        )
        self._skill_limit = (
            profiles.skill_candidates if skill_candidates is None else skill_candidates
        )

    def profile_for(self, unit: UnitState) -> AiProfile:
        key = self._override or unit.ai_profile or "brute"
        return self._profiles.get(key, self._profiles["brute"])

    @property
    def move_candidates(self) -> int:
        return self._move_candidates

    @property
    def skill_candidates(self) -> int:
        """每種技能最多跑完整 ``preview`` 的選取數。"""
        return self._skill_limit

    def order_context(self, state: BattleState, unit: UnitState) -> OrderContext | None:
        """``unit`` 此刻適用的有效戰術指令；沒有指令來源或沒有有效指令時為 ``None``。"""
        if self.orders is None:
            return None
        return resolve_orders(state, unit, self.orders(state, unit.id), self._bonuses)

    def rank_all(self, state: BattleState) -> list[ActionScore]:
        """所有合法動作以完整 ``preview`` 計算的分數（依 ``legal_actions`` 的順序；不篩選，
        較慢，供測試與分析使用）。"""
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        profile = self.profile_for(unit)
        ctx = self.order_context(state, unit)
        walk = _scene(state, unit, ctx).walk
        before = position_value(state, unit.id, profile.weights, ctx, walk=walk)
        return [
            score_action(state, a, profile, before=before, orders=ctx, walk=walk)
            for a in legal_actions(state)
        ]

    def rank(self, state: BattleState) -> list[ActionScore]:
        """候選動作的分數（依 ``legal_actions`` 的順序）。

        攻擊單位、推擊、絆倒、互動以完整 ``preview`` 評分；攻擊物件先經
        :func:`worth_previewing` 篩選；防禦直接計算（:func:`defend_score`）；``Move`` 先以
        :func:`virtual_move_score` 排序，只保留前 ``move_candidates`` 個，其中有風險者
        （:func:`is_risky_move`）才跑完整 ``preview``，其餘直接使用虛擬分數（``preview`` 欄位為
        ``None``）。
        """
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        profile = self.profile_for(unit)
        ctx = self.order_context(state, unit)
        w = _order_weights(profile.weights, ctx)
        actions, areas = legal_actions_with_areas(state)
        if all(isinstance(a, EndStance | EndTurn) for a in actions):
            return []  # 只剩結束回合與取消姿態（AI 不取消姿態）：不需要評分
        scene = _scene(state, unit, ctx)
        walk = scene.walk
        before = position_value(state, unit.id, w, ctx, walk=walk)
        scored: dict[int, ActionScore] = {}
        estimates: list[tuple[Fraction, int]] = []
        for index, action in enumerate(actions):
            if isinstance(action, Move):
                estimates.append(
                    (virtual_move_score(state, unit, action, w, before, scene=scene), index)
                )
            elif isinstance(action, Defend):
                scored[index] = ActionScore(action, defend_score(state, unit, w), None)
            elif isinstance(action, Attack) and not worth_previewing(state, scene, action):
                continue
            elif isinstance(action, UseSkill | EndStance):
                continue  # 技能在下面依估計篩選後才評分；AI 不主動取消姿態
            else:
                scored[index] = score_action(
                    state, action, profile, before=before, orders=ctx, walk=walk
                )
        for index in self._skill_candidates(state, unit, actions, areas, scene, w, before):
            scored[index] = score_action(
                state, actions[index], profile, before=before, orders=ctx, walk=walk
            )
        estimates.sort(key=lambda item: (-item[0], item[1]))
        enemies = reactive_enemies(state, unit)
        for estimate, index in estimates[: self._move_candidates]:
            move = actions[index]
            assert isinstance(move, Move)
            if is_risky_move(state, unit, move, enemies):
                scored[index] = score_action(
                    state, move, profile, before=before, orders=ctx, walk=walk
                )
            else:
                scored[index] = ActionScore(move, estimate, None)
        return [scored[i] for i in sorted(scored)]

    def _skill_candidates(  # noqa: PLR0917
        self,
        state: BattleState,
        unit: UnitState,
        actions: list[Action],
        areas: dict[int, SkillArea],
        scene: _Scene,
        w: AiWeights,
        before: Fraction,
    ) -> list[int]:
        """每個技能依便宜的估計（:func:`skill_estimate`）只保留前 ``skill_candidates`` 個選取，
        回傳它們在 ``actions`` 的索引（遞增）。"""
        by_skill: dict[str, list[tuple[Fraction, int]]] = {}
        for index, action in enumerate(actions):
            if isinstance(action, UseSkill):
                est = skill_estimate(state, unit, action, areas[id(action)], scene, w, before)
                if est is not None:
                    by_skill.setdefault(action.skill_id, []).append((est, index))
        chosen: list[int] = []
        for options in by_skill.values():
            options.sort(key=lambda item: (-item[0], item[1]))
            chosen.extend(index for _, index in options[: self._skill_limit])
        return sorted(chosen)

    def __call__(self, state: BattleState) -> Action:
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        ranked = self.rank(state)
        taunter = _taunter(state, unit)
        if taunter is not None:
            # 被嘲諷：只要有分數 > 0、且有害效果影響到嘲諷者的動作，就只在這些動作與移動之間選
            # （移動的 approach 已改以嘲諷者計算）；否則照一般規則行動
            hostile = [s for s in ranked if s.score > 0 and _hits_unit(s, taunter.id)]
            if hostile:
                ranked = [s for s in ranked if isinstance(s.action, Move) or s in hostile]
        best: ActionScore | None = None
        for scored in ranked:
            if scored.score > 0 and (best is None or scored.score > best.score):
                best = scored
        return best.action if best is not None else EndTurn(unit_id=unit.id)
