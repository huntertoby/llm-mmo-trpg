"""自動對戰與重播（CLI 與之後的模擬器共用的驅動迴圈）。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import cast

from pydantic import BaseModel, ConfigDict

from trpg.engine.actions import Action, Decision, EndTurn, Step
from trpg.engine.ai import Policy
from trpg.engine.ai.commanded import OrderLogging
from trpg.engine.ai.composite import choose_followup
from trpg.engine.ai.orders import OrderRecord
from trpg.engine.ai.simple import choose_action
from trpg.engine.battle import begin_battle, has_only_end_turn, resolve, resume
from trpg.engine.copying import copy_selections
from trpg.engine.events import Event, EventBase
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.ruleset_hash import hash_ruleset
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
    "log_replay_problem",
    "replay",
    "run_battle",
]

LOG_FORMAT = "trpg-battle-log/87"
"""目前的戰鬥紀錄版本（``/87``，Phase 3R-4：鱗族回合開始站水／冰面移動 +1）。版號策略與完整
變更歷程在 ``docs/phases/戰鬥紀錄格式變更.md``：改版時在那份文件加一條，這裡只更新版號與這一行。"""
DEFAULT_MAX_ACTIONS = 20_000

type StepCallback = Callable[[Step | None, ResolveResult], None]
type DecisionPolicy = Callable[[BattleState, Pending], Decision]
"""``prompt`` 反應的決策函式。"""
type StopCondition = Callable[[BattleState, Pending | None], bool]
""":func:`advance` 的停止條件（例如「輪到玩家操控的單位」）。"""


class StepLimitExceeded(TrpgError):
    """自動推進超過步數上限仍未結束（或未輪到玩家）。"""


def accept_all(state: BattleState, pending: Pending) -> Decision:
    """預設：一律使用反應；``copy_skill`` 的選目標取第一個合法的選取（Phase 3C-4b）；複合技能的
    第二段（Phase 3F-4a）由 AI 的簡單估計選（:func:`~trpg.engine.ai.composite.choose_followup`，
    Phase 3F-4b；沒有值得的選取時放棄第二段）。"""
    if pending.kind == "followup":
        return choose_followup(state, pending)
    if pending.kind == "copy_skill":
        caster = state.units[pending.unit_id]
        pick = next(copy_selections(state, caster), None)
        return Decision(
            unit_id=pending.unit_id, accept=pick is not None, copy_cast=pick and pick[0]
        )
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
            ruleset_hash=hash_ruleset(self.setup.ruleset),
        )


class BattleLog(BaseModel):
    """``trpg battle --log-json`` 的輸出格式。``actions`` 是步驟（動作或決定）。"""

    model_config = ConfigDict(extra="forbid")

    format: str
    ruleset_hash: str | None = None
    """內嵌規則包（``setup.ruleset``）的內容雜湊（:func:`~trpg.engine.ruleset_hash.hash_ruleset`；
    Phase 3T-2）。重播前由 :func:`log_replay_problem` 比對；``/85`` 以前的紀錄沒有這個欄位。"""
    seed: int
    setup: BattleSetup
    actions: list[Step]
    events: list[Event]
    final_state: BattleState
    orders: list[OrderRecord] = []
    """戰術指令紀錄（Phase 2C-2）。重播只重播動作，不重新呼叫指揮官；舊紀錄沒有這個欄位。"""


def log_replay_problem(log: BattleLog) -> str | None:
    """``log`` 不能重播的原因（繁體中文）；可以重播時為 ``None``。依序檢查紀錄格式版本、
    ``ruleset_hash`` 是否存在、內嵌規則包的雜湊是否相符（策略見
    ``docs/phases/戰鬥紀錄格式變更.md``）。"""
    if log.format != LOG_FORMAT:
        return (
            f"不支援的紀錄格式 {log.format!r}（目前的引擎是 {LOG_FORMAT!r}）：紀錄的結構或結算規則"
            "在版本之間改變過，舊格式的紀錄無法重播，請用目前的版本重新跑一場"
            "（變更歷程見 docs/phases/戰鬥紀錄格式變更.md）"
        )
    if log.ruleset_hash is None:
        return "紀錄缺少 ruleset_hash，無法確認內嵌的規則包沒有被改過"
    actual = hash_ruleset(log.setup.ruleset)
    if actual != log.ruleset_hash:
        return (
            "紀錄的規則包雜湊不符（紀錄 "
            f"{log.ruleset_hash[:12]}…，內嵌的規則包重新計算為 {actual[:12]}…）："
            "紀錄被修改過，或規則資料的結構在紀錄之後改變，無法確定重播結果一致"
        )
    return None


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
