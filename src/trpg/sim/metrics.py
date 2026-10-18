"""單場戰鬥的指標（Phase 2C-1 3.3）與異常偵測用的原始數據。

:func:`battle_metrics` 是純函式：只讀 ``BattleRun`` 的設定、事件與最終狀態，
不呼叫 LLM、不讀時間、不使用亂數。同一場戰鬥必得同樣的 :class:`BattleMetrics`。

定義（與規格 3.3 對照）：

- **傷害** 一律用 *實際扣掉的 HP*（``hp_before − hp_after``，不含溢出）。
  「直接」＝ ``cause == "attack"``（普攻、技能、反應攻擊）；
  「間接」＝ 其他 cause（爆炸、表面、墜落、致命地形、持續傷害……）。
  能追溯 ``source_id`` 的歸給來源單位；追溯不到的歸「環境」（依受害陣營記在
  ``environment_damage``）。打到自己陣營的傷害不計入直接／間接，另記在 ``damage_friendly``。
- **DPR** ＝ 單位造成的（直接＋間接）傷害 ÷ 該單位存活的輪數（該輪開始時仍在場；``max(1, …)``）。
- **控制回合** ＝ 單位在 *自己回合開始時*（``turn_started`` 當下）帶有 stun／root／slow 的次數，
  歸給該狀態最後一次施加者（``status_applied.source_id``）；追溯不到歸環境。
- **墜落與致命地形** 的傷害在引擎裡沒有 ``source_id``，所以在同一個動作內追溯：
  該單位被 *強制位移*（``unit_moved`` 的 ``mode == "forced"``：推、拉、擊退）→ 歸這個動作的行動者；
  或它腳下的物件（木橋）在這個動作內被摧毀而掉進致命地形 → 歸最後打到那個物件的單位。
  追溯不到（自己走進去、橋是被火燒掉的……）歸環境。
- **單一動作** ＝ 一個 ``Step``（玩家／AI 的一個動作，含它觸發的反應與連鎖）所產生的事件。
  動作的邊界由 :class:`StepTrace`（``run_battle`` 的 ``on_step`` 回呼）記錄；沒有記錄的
  ``BattleRun`` 會以重播取得。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.engine.actions import Decision, EndTurn, Step
from trpg.engine.ai import Policy
from trpg.engine.battle import begin_battle, resolve, resume
from trpg.engine.events import (
    AttackRolled,
    ChainLimitReached,
    DamageDealt,
    EventBase,
    Healed,
    RoundStarted,
    ShieldAbsorbed,
    ShieldGained,
    SkillTriggered,
    SkillUsed,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    TriggerLimitReached,
    TurnStarted,
    UnitDowned,
    UnitEscaped,
    UnitSpawned,
)
from trpg.engine.results import ResolveResult
from trpg.engine.runner import DEFAULT_MAX_ACTIONS, BattleRun, run_battle
from trpg.engine.setup import BattleSetup
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team, UnitId

__all__ = [
    "BOSS_BURST_FRACTION_PERMILLE",
    "BOSS_TAG",
    "CONTROL_STATUSES",
    "INDIRECT_ACTION_CAUSES",
    "LONG_BATTLE_ROUNDS",
    "TERRAIN_CAUSE",
    "BattleMetrics",
    "MaxActionsExceeded",
    "SkillMetrics",
    "StepTrace",
    "TrackedRun",
    "UnitInfo",
    "UnitMetrics",
    "battle_metrics",
    "metrics_from_events",
    "run_tracked",
]

CONTROL_STATUSES: tuple[str, ...] = ("stun", "root", "slow")
"""計入「控制回合」的狀態。"""

BOSS_TAG = "boss"
BOSS_BURST_FRACTION_PERMILLE = 600
"""``boss_burst``：單一動作對 Boss 造成 ≥ 最大 HP 的這個千分比。"""
LONG_BATTLE_ROUNDS = 10
"""``long_battle``：輪數 > 這個值。"""
INDIRECT_ACTION_CAUSES: frozenset[str] = frozenset({"status", "surface"})
"""不計入「單一動作傷害」（``boss_burst``、``one_shot``）的 cause：每個單位回合開始時的持續傷害
與站在表面上的傷害，是回合推進的結果，不是那個動作本身造成的。"""
TERRAIN_CAUSE = "deadly_terrain"
"""致命地形是設計好的秒殺（地圖檢查限量），不計入非 Boss 的 ``one_shot``
（否則每個推下深淵都是異常）；對 Boss 仍計入 ``boss_burst``。"""

_USES, _ROLLS, _HITS, _DAMAGE, _HEALED = range(5)

type ResultName = Literal["ally", "enemy", "draw"]


# ---------------------------------------------------------------------------
# 資料模型
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class UnitMetrics(_Model):
    """一個單位在一場戰鬥中的指標。"""

    unit_id: str
    template_id: str
    team: Team
    alive_rounds: int
    turns: int
    ap_spent: int
    damage_direct: int
    damage_indirect: int
    damage_friendly: int
    damage_taken: int
    healing_done: int
    kills: int
    downed: bool
    control_inflicted: dict[str, int]
    """狀態 → 在自己回合開始時帶著該狀態的（被此單位施加的）單位次數。"""
    shield_absorbed: int = 0
    """這個單位身上的護盾吸收的傷害（Phase 2D-1；不計入 ``damage_taken``）。"""
    shield_provided: int = 0
    """這個單位施放的護盾所吸收的傷害（Phase 2D-2；歸給護盾最後一次施加者）。"""
    triggers_fired: int = 0
    """這個單位的被動觸發次數（Phase 2E-1）。"""

    @property
    def damage_dealt(self) -> int:
        return self.damage_direct + self.damage_indirect

    @property
    def dpr(self) -> Fraction:
        return Fraction(self.damage_dealt, max(1, self.alive_rounds))


class SkillMetrics(_Model):
    """一個技能在一場戰鬥中的使用統計。"""

    uses: int = 0
    rolls: int = 0
    hits: int = 0
    damage: int = 0
    healed: int = 0


class BattleMetrics(_Model):
    """一場戰鬥的指標。"""

    seed: int
    result: ResultName
    rounds: int
    actions: int
    """總動作數（含自動結束回合）。"""
    units: tuple[UnitMetrics, ...]
    environment_damage: dict[str, int]
    """追溯不到來源的傷害，依受害陣營（``ally``／``enemy``）。"""
    environment_control: dict[str, int]
    """追溯不到施加者的控制回合，依狀態。"""
    skills: dict[str, SkillMetrics]
    skill_users: dict[str, tuple[str, ...]]
    """技能 → 使用過它的陣營（排序後）。"""
    chain_limit_count: int
    boss_burst: str | None
    """``boss_burst`` 的原因（沒有時為 ``None``）。"""
    one_shot_count: int
    trigger_limit_count: int = 0
    """被動因觸發深度上限而沒有結算的次數（``TriggerLimitReached``；Phase 2E-1）。"""

    def team_damage(self, team: Team, *, direct: bool | None = None) -> int:
        """陣營造成的傷害；``direct`` 為 ``None`` 時直接＋間接。"""
        total = 0
        for unit in self.units:
            if unit.team is not team:
                continue
            if direct is None:
                total += unit.damage_dealt
            else:
                total += unit.damage_direct if direct else unit.damage_indirect
        return total


@dataclass(frozen=True, slots=True)
class UnitInfo:
    """:func:`metrics_from_events` 需要的單位資料（取自最終狀態；測試可手工建構）。"""

    unit_id: UnitId
    template_id: str
    team: Team
    max_hp: int
    tags: tuple[str, ...] = ()

    @property
    def boss(self) -> bool:
        return BOSS_TAG in self.tags


# ---------------------------------------------------------------------------
# 動作邊界與 AP（run_battle 的 on_step 回呼）
# ---------------------------------------------------------------------------


class MaxActionsExceeded(TrpgError):
    """戰鬥超過 ``max_actions`` 個動作仍未結束。"""


class StepTrace:
    """``run_battle(on_step=…)`` 的回呼：記錄每一步結束時的事件累計數與每個單位花掉的 AP。

    ``actors[i]`` 是第 ``i`` 步的行動者（開場與 ``Decision`` 為 ``None``）。
    ``bounds[0]`` 是開場事件的數量，``bounds[i]`` 是第 ``i`` 步結算後的事件累計數，所以第 ``i`` 步
    （``i ≥ 1``）的事件是 ``events[bounds[i-1]:bounds[i]]``。

    AP：非 ``EndTurn``／``Decision`` 的步驟，行動者仍是目前行動者時，AP 的減少量算作花掉的 AP。
    """

    def __init__(self) -> None:
        self.bounds: list[int] = []
        self.actors: list[UnitId | None] = []
        self.ap_spent: dict[UnitId, int] = {}
        self.steps = 0
        self._count = 0
        self._ap: dict[UnitId, int] = {}

    def __call__(self, step: Step | None, result: ResolveResult) -> None:
        self.actors.append(None if step is None or isinstance(step, Decision) else step.unit_id)
        if step is not None:
            self.steps += 1
            if not isinstance(step, EndTurn | Decision):
                unit = result.state.units.get(step.unit_id)
                if unit is not None and result.state.active_unit == step.unit_id:
                    spent = self._ap.get(step.unit_id, 0) - unit.ap
                    if spent > 0:
                        self.ap_spent[step.unit_id] = self.ap_spent.get(step.unit_id, 0) + spent
        self._count += len(result.events)
        self.bounds.append(self._count)
        self._ap = {u.id: u.ap for u in result.state.units.values()}


class TrackedRun(BattleRun):
    """附帶 :class:`StepTrace` 結果的 ``BattleRun``（由 :func:`run_tracked` 建立）。"""

    __slots__ = ("actors", "ap_spent", "bounds")

    def __init__(self, run: BattleRun, trace: StepTrace) -> None:
        super().__init__(run.setup, run.seed, run.state, run.actions, run.events)
        self.bounds = tuple(trace.bounds)
        self.actors = tuple(trace.actors)
        self.ap_spent = dict(trace.ap_spent)


def run_tracked(
    setup: BattleSetup, seed: int, policy: Policy, *, max_actions: int = DEFAULT_MAX_ACTIONS
) -> TrackedRun:
    """:func:`~trpg.engine.runner.run_battle` ＋ 記錄動作邊界；超過 ``max_actions`` 拋出
    :class:`MaxActionsExceeded`（其他例外原樣拋出）。"""
    trace = StepTrace()
    try:
        run = run_battle(setup, seed, policy, on_step=trace, max_actions=max_actions)
    except TrpgError as exc:
        if trace.steps >= max_actions:
            raise MaxActionsExceeded(str(exc)) from exc
        raise
    return TrackedRun(run, trace)


def _trace_by_replay(run: BattleRun) -> StepTrace:
    """沒有記錄動作邊界的 ``BattleRun``：重播一次取得。"""
    trace = StepTrace()
    result = begin_battle(run.setup, run.seed)
    trace(None, result)
    state = result.state
    for step in run.actions:
        result = resume(state, step) if isinstance(step, Decision) else resolve(state, step)
        trace(step, result)
        state = result.state
    if trace.bounds[-1] != len(run.events):
        raise ValueError("重播的事件數與 BattleRun 不一致")
    return trace


# ---------------------------------------------------------------------------
# 指標計算
# ---------------------------------------------------------------------------


@dataclass
class _Acc:
    """單位的累計值。"""

    alive_rounds: int = 0
    turns: int = 0
    direct: int = 0
    indirect: int = 0
    friendly: int = 0
    taken: int = 0
    absorbed: int = 0
    provided: int = 0
    healing: int = 0
    kills: int = 0
    triggers: int = 0
    downed: bool = False
    control: dict[str, int] = field(default_factory=dict)


def metrics_from_events(  # noqa: PLR0912, PLR0915 - 單一事件迴圈，拆開反而難讀
    *,
    seed: int,
    units: Sequence[UnitInfo],
    events: Sequence[EventBase],
    bounds: Sequence[int] | None,
    ap_spent: Mapping[UnitId, int],
    winner: Team | None,
    rounds: int,
    actions: int,
) -> BattleMetrics:
    """由事件序列計算 :class:`BattleMetrics`（純函式）。

    ``units`` 是全部出過場的單位（含援軍）；``bounds`` 是 :class:`StepTrace` 的動作邊界
    （``None`` 時整個事件序列視為同一個動作）。墜落、致命地形、爆炸的傷害來源取自
    ``DamageDealt.source_id``（引擎在推擊、打斷或燒斷橋時帶上來源，Phase 2C-3）；沒有來源的歸環境。
    """
    info = {u.unit_id: u for u in units}
    acc = {u.unit_id: _Acc() for u in units}
    spawned = {e.unit_id for e in events if isinstance(e, UnitSpawned)}
    present = {u.unit_id for u in units if u.unit_id not in spawned}
    statuses: dict[UnitId, dict[str, UnitId | None]] = {}
    last_hit: dict[UnitId, UnitId | None] = {}
    env_damage: dict[str, int] = {}
    env_control: dict[str, int] = {}
    skills: dict[str, list[int]] = {}  # [使用, 擲骰, 命中, 傷害, 治療]
    skill_users: dict[str, set[str]] = {}
    chain_limit = 0
    trigger_limit = 0
    boss_round_one_down = False
    one_shots = 0
    boss_burst_hits: list[str] = []
    shield_owner: dict[UnitId, UnitId | None] = {}

    edges = list(bounds) if bounds else [len(events)]
    slice_index = 0
    slice_damage: dict[UnitId, int] = {}
    slice_terrain: dict[UnitId, int] = {}

    def flush() -> None:
        nonlocal one_shots
        for target_id in sorted(set(slice_damage) | set(slice_terrain)):
            target = info[target_id]
            total = slice_damage.get(target_id, 0)
            if target.boss:
                total += slice_terrain.get(target_id, 0)
                if total * 1000 >= target.max_hp * BOSS_BURST_FRACTION_PERMILLE:
                    boss_burst_hits.append(f"單一動作對 {target_id} 造成 {total}／{target.max_hp}")
            elif total >= target.max_hp:
                one_shots += 1
        slice_damage.clear()
        slice_terrain.clear()

    current: str | None = None
    caster: UnitId | None = None

    for index, event in enumerate(events):
        while slice_index < len(edges) - 1 and index >= edges[slice_index]:
            flush()
            slice_index += 1
        if isinstance(event, RoundStarted):
            for unit_id in present:
                acc[unit_id].alive_rounds += 1
        elif isinstance(event, UnitSpawned):
            present.add(event.unit_id)
        elif isinstance(event, UnitEscaped):
            present.discard(event.unit_id)
        elif isinstance(event, TurnStarted):
            acc[event.unit_id].turns += 1
            for status_id, source in sorted(statuses.get(event.unit_id, {}).items()):
                if status_id not in CONTROL_STATUSES:
                    continue
                if source is not None and source in info:
                    bucket = acc[source].control
                    bucket[status_id] = bucket.get(status_id, 0) + 1
                else:
                    env_control[status_id] = env_control.get(status_id, 0) + 1
        elif isinstance(event, StatusApplied):
            statuses.setdefault(event.target_id, {})[event.status_id] = event.source_id
        elif isinstance(event, StatusRemoved):
            statuses.get(event.target_id, {}).pop(event.status_id, None)
        elif isinstance(event, StatusConverted):
            held = statuses.setdefault(event.target_id, {})
            held.pop(event.from_status, None)
            held[event.to_status] = event.source_id
        elif isinstance(event, UnitDowned):
            present.discard(event.unit_id)
            statuses.pop(event.unit_id, None)
            acc[event.unit_id].downed = True
            killer = last_hit.get(event.unit_id)
            if (
                killer is not None
                and killer in info
                and info[killer].team is not info[event.unit_id].team
            ):
                acc[killer].kills += 1
            if info[event.unit_id].boss and event.round == 1:
                boss_round_one_down = True
        elif isinstance(event, ChainLimitReached):
            chain_limit += 1
        elif isinstance(event, TriggerLimitReached):
            trigger_limit += 1
        elif isinstance(event, SkillTriggered):
            current, caster = event.skill_id, event.unit_id
            skills.setdefault(current, [0, 0, 0, 0, 0])[_USES] += 1
            skill_users.setdefault(current, set()).add(info[event.unit_id].team.value)
            acc[event.unit_id].triggers += 1
        elif isinstance(event, SkillUsed):
            current, caster = event.skill_id, event.unit_id
            skills.setdefault(current, [0, 0, 0, 0, 0])[_USES] += 1
            skill_users.setdefault(current, set()).add(info[event.unit_id].team.value)
        elif isinstance(event, AttackRolled):
            current, caster = event.skill_id, event.attacker_id
            if current is not None:
                entry = skills.setdefault(current, [0, 0, 0, 0, 0])
                entry[_ROLLS] += 1
                entry[_HITS] += 1 if event.hit else 0
        elif isinstance(event, DamageDealt):
            amount = event.hp_before - event.hp_after
            target = info[event.target_id]
            source = event.source_id if event.source_id in info else None
            last_hit[event.target_id] = source
            acc[event.target_id].taken += amount
            acc[event.target_id].absorbed += event.absorbed
            if event.cause == TERRAIN_CAUSE:
                slice_terrain[event.target_id] = slice_terrain.get(event.target_id, 0) + amount
            elif event.cause not in INDIRECT_ACTION_CAUSES:
                slice_damage[event.target_id] = slice_damage.get(event.target_id, 0) + amount
            enemy_hit = source is not None and info[source].team is not target.team
            if source is None:
                env_damage[target.team.value] = env_damage.get(target.team.value, 0) + amount
            elif not enemy_hit:
                acc[source].friendly += amount
            elif event.cause == "attack":
                acc[source].direct += amount
            else:
                acc[source].indirect += amount
            if (
                current is not None
                and event.cause == "attack"
                and event.source_id == caster
                and enemy_hit
            ):
                skills.setdefault(current, [0, 0, 0, 0, 0])[_DAMAGE] += amount
        elif isinstance(event, ShieldGained):
            shield_owner[event.unit_id] = event.source_id
        elif isinstance(event, ShieldAbsorbed):
            owner = shield_owner.get(event.unit_id)
            if owner is not None and owner in acc:
                acc[owner].provided += event.absorbed
        elif isinstance(event, Healed):
            if event.source_id is not None and event.source_id in info:
                acc[event.source_id].healing += event.amount
            if current is not None and event.source_id == caster:
                skills.setdefault(current, [0, 0, 0, 0, 0])[_HEALED] += event.amount
    flush()

    boss_burst: str | None = None
    if boss_round_one_down:
        boss_burst = "Boss 在第 1 輪被擊倒"
    elif boss_burst_hits:
        boss_burst = boss_burst_hits[0]
    result: ResultName = "draw" if winner is None else winner.value
    return BattleMetrics(
        seed=seed,
        result=result,
        rounds=rounds,
        actions=actions,
        units=tuple(
            UnitMetrics(
                unit_id=u.unit_id,
                template_id=u.template_id,
                team=u.team,
                alive_rounds=acc[u.unit_id].alive_rounds,
                turns=acc[u.unit_id].turns,
                ap_spent=ap_spent.get(u.unit_id, 0),
                damage_direct=acc[u.unit_id].direct,
                damage_indirect=acc[u.unit_id].indirect,
                damage_friendly=acc[u.unit_id].friendly,
                damage_taken=acc[u.unit_id].taken,
                healing_done=acc[u.unit_id].healing,
                kills=acc[u.unit_id].kills,
                triggers_fired=acc[u.unit_id].triggers,
                downed=acc[u.unit_id].downed,
                control_inflicted=dict(sorted(acc[u.unit_id].control.items())),
                shield_absorbed=acc[u.unit_id].absorbed,
                shield_provided=acc[u.unit_id].provided,
            )
            for u in units
        ),
        environment_damage=dict(sorted(env_damage.items())),
        environment_control=dict(sorted(env_control.items())),
        skills={
            k: SkillMetrics(uses=v[0], rolls=v[1], hits=v[2], damage=v[3], healed=v[4])
            for k, v in sorted(skills.items())
        },
        skill_users={k: tuple(sorted(v)) for k, v in sorted(skill_users.items())},
        chain_limit_count=chain_limit,
        boss_burst=boss_burst,
        one_shot_count=one_shots,
        trigger_limit_count=trigger_limit,
    )


def battle_metrics(run: BattleRun) -> BattleMetrics:
    """一場戰鬥的指標（純函式；只讀設定、事件與最終狀態）。

    ``run`` 若是 :class:`TrackedRun`（:func:`run_tracked`）直接用它記錄的動作邊界與 AP，
    否則重播一次取得。
    """
    if isinstance(run, TrackedRun):
        bounds: Sequence[int] = run.bounds
        ap_spent: Mapping[UnitId, int] = run.ap_spent
    else:
        trace = _trace_by_replay(run)
        bounds, ap_spent = trace.bounds, trace.ap_spent
    units = [
        UnitInfo(u.id, u.template_id, u.team, u.max_hp, u.tags) for u in run.state.units.values()
    ]
    return metrics_from_events(
        seed=run.seed,
        units=units,
        events=run.events,
        bounds=bounds,
        ap_spent=ap_spent,
        winner=run.state.winner,
        rounds=run.state.round,
        actions=len(run.actions),
    )
