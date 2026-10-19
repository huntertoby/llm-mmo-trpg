"""自動對戰與重播（CLI 與之後的模擬器共用的驅動迴圈）。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import cast

from pydantic import BaseModel, ConfigDict

from trpg.engine.actions import Action, Decision, EndTurn, Step
from trpg.engine.ai import Policy
from trpg.engine.ai.commanded import OrderLogging
from trpg.engine.ai.orders import OrderRecord
from trpg.engine.ai.simple import choose_action
from trpg.engine.battle import begin_battle, has_only_end_turn, resolve, resume
from trpg.engine.events import Event, EventBase
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team, UnitId

__all__ = [
    "DEFAULT_MAX_ACTIONS",
    "LOG_FORMAT",
    "BattleLog",
    "BattleRun",
    "DecisionPolicy",
    "StepLimitExceeded",
    "StopCondition",
    "accept_all",
    "advance",
    "apply_step",
    "auto_step",
    "replay",
    "run_battle",
]

LOG_FORMAT = "trpg-battle-log/14"
"""``/14``（Phase 3C-4a）：源力（單位的 ``source``、``ap_pending``、``ap_granted_round``，
戰鬥狀態的 ``source_wells``，戰鬥設定 ``UnitSpawn.source``）、新事件 ``source_changed``／
``ap_granted``／``death_cheated``、``skill_used.source``、``status_removed`` 的新原因 ``spent``、
三個改寫規則型原語與狀態 ``undying``；擊倒精英會多出 ``source_changed`` 事件，所以 ``/13`` 的
紀錄用新版程式重跑事件會不同。

``/13``（Phase 3C-3b）：表面歸屬（格子的 ``surface_creator``）、新觸發時機 ``on_enter_surface``、
``consume_status`` 原語（``status_removed`` 的新原因 ``consumed``）、基本推擊貼牆也合法並產生撞擊；
``/12`` 的紀錄含有舊的推擊合法性與觸發表，無法由新版程式重播。

``/12``（Phase 3C-3a）：撞擊——推擊遇到障礙或超過距離上限時新增 ``collided`` 事件與
``DamageDealt.cause == "collision"``，規則包加入 ``collision_damage_dice`` 與三個新觸發時機；
``/11`` 的紀錄重播會因撞擊傷害而不同，無法由新版程式重播。

``/11``（Phase 2H-1）：``status_removed`` 的新原因 ``thawed``、規則包的狀態加入
``removed_by_element``、互動規則加入 ``apply_status`` 結果與單位所在格表面條件；``/10`` 的紀錄
無法由新版程式重播。

``/10``（Phase 2E-3）：層數（單位狀態加入 ``stacks``／``stack_expiry``、``stacks_changed``、
規則包的 ``stacks``）、陷阱（戰鬥狀態加入 ``traps``、``trap_placed``／``trap_triggered``／
``trap_expired``）、傷害加成（``damage_dealt`` 的倍率含層數加成）；``/9`` 的紀錄無法重播。

``/9``（Phase 2E-2）：反應技（``reaction_triggered`` 的 ``reaction`` 可以是技能 ID）、替隊友
擋攻擊（``attack_intercepted``）、姿態（``end_stance`` 動作、``status_removed`` 的新原因、規則包的
``stance_ap_cost``）；``/8`` 的紀錄無法重播。

``/8``（Phase 2E-1）：被動技能的觸發（``skill_triggered``、``trigger_limit_reached``；
單位狀態加入 ``trigger_counts``、``hits_landed``；規則包加入 ``skill_triggers``）；
``/7`` 的紀錄無法重播。

``/7``（Phase 2D-1）：護盾（``StatusInstance.amount``、``shield_gained``／``shield_absorbed``、
``damage_dealt.absorbed``）、有效屬性（狀態的屬性加值）與嘲諷；``/6`` 的紀錄無法重播。

``/5``（Phase 2B-1）：新狀態、抵抗判定（``status_save_rolled``）、控制遞減（單位狀態加入
``control_dr``）、Boss 轉換與 ``turn_skipped``；傷害與治療帶狀態倍率，``/4`` 的紀錄無法重播。

``/4``（Phase 2A）：加入 ``use_skill`` 動作與技能事件（``skill_used``、
``skill_cooldown_changed``），``turn_started`` 帶法力，``attack_rolled``／``maneuver_rolled``
帶 ``skill_id``；``/3`` 的紀錄無法重播。

``/3``（Phase 1C）：加入掩護（``attack_rolled.cover``）、``damage_dealt.base_amount``、牆壁地形，
且結算規則改變（表面在腳下立即生效、漏油、推不動的推擊不合法），``/2`` 的紀錄無法重播。

``/2``（Phase 1B）：``actions`` 改為步驟列表（動作或 ``decision``）；狀態加入物件、表面等欄位。
（``/1`` 的紀錄無法以 Phase 1B 的引擎重播。）"""
DEFAULT_MAX_ACTIONS = 20_000

type StepCallback = Callable[[Step | None, ResolveResult], None]
type DecisionPolicy = Callable[[BattleState, Pending], Decision]
"""``prompt`` 反應的決策函式。"""
type StopCondition = Callable[[BattleState, Pending | None], bool]
""":func:`advance` 的停止條件（例如「輪到玩家操控的單位」）。"""


class StepLimitExceeded(TrpgError):
    """自動推進超過步數上限仍未結束（或未輪到玩家）。"""


def accept_all(state: BattleState, pending: Pending) -> Decision:
    """預設：一律使用反應。"""
    return Decision(unit_id=pending.unit_id, accept=True)


class BattleRun:
    """一場自動對戰的結果：最終狀態、步驟列表、全部事件（含開場事件）。"""

    __slots__ = ("actions", "events", "orders", "seed", "setup", "state")

    def __init__(
        self,
        setup: BattleSetup,
        seed: int,
        state: BattleState,
        actions: list[Step],
        events: list[EventBase],
        *,
        orders: list[OrderRecord] | None = None,
    ) -> None:
        self.orders: list[OrderRecord] = [] if orders is None else orders
        """指揮官下達的指令紀錄（Phase 2C-2；沒有指揮官時為空）。"""
        self.setup = setup
        self.seed = seed
        self.state = state
        self.actions = actions
        self.events = events

    def to_log(self) -> BattleLog:
        return BattleLog(
            format=LOG_FORMAT,
            seed=self.seed,
            setup=self.setup,
            actions=self.actions,
            events=cast("list[Event]", self.events),
            final_state=self.state,
            orders=self.orders,
        )


class BattleLog(BaseModel):
    """``trpg battle --log-json`` 的輸出格式。``actions`` 是步驟（動作或決定）。"""

    model_config = ConfigDict(extra="forbid")

    format: str
    seed: int
    setup: BattleSetup
    actions: list[Step]
    events: list[Event]
    final_state: BattleState
    orders: list[OrderRecord] = []
    """戰術指令紀錄（Phase 2C-2）。重播只重播動作，不重新呼叫指揮官；舊紀錄沒有這個欄位。"""


def run_battle(
    setup: BattleSetup,
    seed: int,
    policy: Policy = choose_action,
    *,
    decide: DecisionPolicy = accept_all,
    on_step: StepCallback | None = None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    controllers: Mapping[UnitId | Team, Policy] | None = None,
) -> BattleRun:
    """跑到戰鬥結束。行動者的 policy 依序查：``controllers`` 的單位 ID → 陣營 → ``policy``。

    ``legal_actions`` 只剩 ``EndTurn`` 時（:func:`has_only_end_turn`）自動結束回合，不詢問
    policy。結算暫停（``prompt`` 反應）時以 ``decide`` 回答並 ``resume``。``on_step`` 在開場與
    每一步結算後呼叫（開場時 step 為 ``None``）。超過 ``max_actions`` 步仍未結束時拋出
    :class:`StepLimitExceeded`（設定 ``max_rounds`` 可保證結束）。
    推進迴圈本身是 :func:`advance`（網頁 API 的自動推進共用同一個函式）。
    """
    result = begin_battle(setup, seed)
    if on_step is not None:
        on_step(None, result)
    events: list[EventBase] = list(result.events)

    def record(step: Step | None, step_result: ResolveResult) -> None:
        if on_step is not None:
            on_step(step, step_result)
        events.extend(step_result.events)

    state, _pending, steps = advance(
        result.state,
        None,
        policy,
        decide=decide,
        on_step=record,
        max_actions=max_actions,
        controllers=controllers,
    )
    orders = _collect_orders(policy, controllers)
    return BattleRun(setup, seed, state, steps, events, orders=orders)


def auto_step(
    state: BattleState,
    pending: Pending | None,
    policy: Policy,
    *,
    decide: DecisionPolicy = accept_all,
    controllers: Mapping[UnitId | Team, Policy] | None = None,
) -> Step:
    """自動驅動的下一步：暫停中以 ``decide`` 回答；只剩 ``EndTurn`` 時結束回合；否則問 policy。"""
    if pending is not None:
        return decide(state, pending)
    if has_only_end_turn(state):
        assert state.active_unit is not None
        return EndTurn(unit_id=state.active_unit)
    return _controller_for(state, policy, controllers)(state)


def apply_step(state: BattleState, step: Step) -> ResolveResult:
    """結算一個步驟：決定以 ``resume``、動作以 ``resolve``（與 :func:`replay` 相同）。"""
    if isinstance(step, Decision):
        return resume(state, step)
    action: Action = step
    return resolve(state, action)


def advance(
    state: BattleState,
    pending: Pending | None,
    policy: Policy,
    *,
    decide: DecisionPolicy = accept_all,
    on_step: StepCallback | None = None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    controllers: Mapping[UnitId | Team, Policy] | None = None,
    stop: StopCondition | None = None,
) -> tuple[BattleState, Pending | None, list[Step]]:
    """以 :func:`auto_step` 持續結算，直到戰鬥結束或 ``stop(state, pending)`` 為真。

    回傳 ``(最後狀態, 最後的 pending, 這次結算的步驟)``。``on_step`` 在每一步結算後呼叫
    （呼叫者可以藉此逐步保存進度：超過 ``max_actions`` 步時拋出 :class:`StepLimitExceeded`，
    已結算的步驟都已經通知過）。
    """
    steps: list[Step] = []
    while not state.ended:
        if stop is not None and stop(state, pending):
            break
        if len(steps) >= max_actions:
            raise StepLimitExceeded(f"超過 {max_actions} 個動作仍未結束戰鬥")
        step = auto_step(state, pending, policy, decide=decide, controllers=controllers)
        result = apply_step(state, step)
        if on_step is not None:
            on_step(step, result)
        state = result.state
        pending = result.pending
        steps.append(step)
    return state, pending, steps


def _controller_for(
    state: BattleState, policy: Policy, controllers: Mapping[UnitId | Team, Policy] | None
) -> Policy:
    if not controllers:
        return policy
    unit = state.active
    assert unit is not None
    by_unit = controllers.get(unit.id)
    if by_unit is not None:
        return by_unit
    return controllers.get(unit.team, policy)


def _collect_orders(
    policy: Policy, controllers: Mapping[UnitId | Team, Policy] | None
) -> list[OrderRecord]:
    """會記錄指令的 policy（同一個物件只算一次）的指令紀錄，依輪數與陣營排序（穩定）。"""
    seen: set[int] = set()
    records: list[OrderRecord] = []
    for candidate in (policy, *(controllers or {}).values()):
        if isinstance(candidate, OrderLogging) and id(candidate) not in seen:
            seen.add(id(candidate))
            records.extend(candidate.order_log)
    records.sort(key=lambda r: (r.round, r.team.value))
    return records


def replay(setup: BattleSetup, seed: int, steps: Sequence[Step]) -> BattleRun:
    """以 ``初始狀態 ＋ 步驟列表`` 重播（動作以 ``resolve``、決定以 ``resume``）。"""
    result = begin_battle(setup, seed)
    state = result.state
    events: list[EventBase] = list(result.events)
    for step in steps:
        result = apply_step(state, step)
        state = result.state
        events.extend(result.events)
    return BattleRun(setup, seed, state, list(steps), events)
