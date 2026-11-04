"""路徑預覽（Phase 6A-4b；``docs/design/05-戰鬥.md`` 5.10 路徑提示）：
``preview_path(state, unit_id, path=..., dest=...) -> PathPreview``。

給定行動單位與移動路徑（格子序列；或只給終點，取本回合的最短路徑），回傳路徑上每一格的預估事件
與實際停點，給畫面畫路徑提示（分段變色、結果小牌、實際停點、「到不了」）。畫面不自己算規則。

做法：與 :func:`trpg.engine.preview.preview` 相同，用 **同一套引擎** 在狀態複本上模擬
（:func:`trpg.engine.battle.simulate_preview`）：

- ``min``（最少後果）：檢定（冰面滑倒、抵抗）對移動者有利、藉機攻擊落空、傷害骰取最小；
- ``max``（最多後果）：檢定失敗、藉機攻擊命中、傷害骰取最大、``prompt`` 反應使用。

兩次模擬都出現的事件為「確定」（``certain``），只在其中一次出現的為「可能」。預覽 **不擲骰**、
不改動傳入的狀態與 ``rng_state``。只有 :attr:`PathPreview.certain` 為真（模擬沒有經過任何分歧點）
時，才保證與實際結算完全一致。

- 路徑不合法（移動點數不足、被敵人或牆擋住、停在有人的格子）時，取 **最長的合法前段** 模擬，
  之後的格子標「到不了」（``unreachable``），``reason`` 為完整路徑不合法的原因。
- 隱藏陷阱：與一般預覽相同，先以 :func:`trpg.engine.traps.strip_hidden_traps` 移除移動者陣營
  看不見的陷阱——預覽不洩漏看不見的陷阱，所以踩到未發現的陷阱時實走會與預覽不同。
- 冰面滑倒並滑行（#123，Phase 6E-2）：自己走進一段連續冰面的第一格擲一次敏捷檢定，失敗沿走進來
  的方向滑到冰面外的第一格（最多 3 格）、停下倒地（:mod:`trpg.engine.ice_slide`）。
  :attr:`PathPreview.slip_runs` 每段一筆：段的範圍、第一格的滑倒機率（精確計算，不擲骰），與失敗時
  的 **單一停點與滑行路徑**——用同一套引擎另跑一次「只有這段的檢定失敗、其餘照最少後果」的模擬
  （:func:`trpg.engine.battle.simulate_slide_failure`），所以停點與實走一致（含撞牆、撞單位、
  高度差、致命地形前停下、滑過陷阱；倒在友軍格時滑回空格，見 ``battle._slide_back_if_stacked``）。
- 冰面檢定與其他分歧點的組合（Phase 6E-2b）：「最少／最多後果」兩次模擬只涵蓋「全部有利／
  全部不利」，漏掉「冰面失敗但陷阱抵抗成功」（滑出冰外）或「過了冰但陷阱定身」這類組合。
  路徑上有 N 次滑行檢定時另跑分支：第 k 次失敗（之前的通過）× 其餘取最少／最多後果，以及
  全部通過 × 其餘取最多後果。這些分支的停點收進 :attr:`PathPreview.stops`，事件併入每一格
  （只在部分分支出現的為「可能」）。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

from trpg.engine.actions import Move
from trpg.engine.battle import (
    ACTION_HANDLERS,
    acting_unit,
    plan_move,
    simulate_preview,
    simulate_slide_failure,
)
from trpg.engine.context import Ctx
from trpg.engine.events import (
    CheckRolled,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    ReactionTriggered,
    StatusApplied,
    SurfaceChanged,
    SurfaceEntered,
    TrapTriggered,
    UnitDowned,
    UnitEscaped,
    UnitFell,
    UnitMoved,
    UnitSlid,
    UnitStoodUp,
)
from trpg.engine.ice_slide import slide_check_def
from trpg.engine.ids import PRONE
from trpg.engine.results import ResolveResult
from trpg.engine.rules.movement import find_path, is_flying
from trpg.engine.rules.race import slip_immune
from trpg.engine.rules.statuses import is_rooted, skip_turn_status
from trpg.engine.state import BattleState, UnitState
from trpg.engine.traps import strip_hidden_traps
from trpg.engine.turns import finish_resolution
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Surface, UnitId

__all__ = [
    "PathEvent",
    "PathEventKind",
    "PathPreview",
    "PathStep",
    "SlipRun",
    "StepReach",
    "preview_path",
]

type XY = tuple[int, int]

type PathEventKind = Literal[
    "stood_up",
    "surface",
    "slip_check",
    "trap",
    "damage",
    "status",
    "reaction",
    "displaced",
    "surface_changed",
    "fell",
    "deadly",
    "downed",
    "escaped",
    "stopped",
]
"""路徑上一格的預估事件種類：

- ``stood_up`` 倒地者先站起；``surface`` 走進有進入效果的表面（``surface``）；
- ``slip_check`` 表面的檢定（冰面滑倒；``chance`` 為失敗機率，``status_id`` 為失敗的狀態）；
- ``trap`` 觸發已知的陷阱（``other_id`` 為放置者，``detail`` 為陷阱技能）；
- ``damage`` 移動者受到傷害（``amount_min``／``amount_max``；``other_id`` 來源，``detail`` 原因）；
- ``status`` 移動者得到狀態（``status_id``：``burning`` 點燃、``root`` 定身、``prone`` 倒地……）；
- ``reaction`` 敵人的反應（``other_id`` 為反應者，``detail`` 為反應 ID；藉機攻擊也在這裡）；
- ``displaced`` 被移離路徑（``pos`` 為新位置，``detail`` 為移動方式：滑回空格、陷阱推擊……）；
- ``surface_changed`` 移動中某格的表面改變（``pos``、``surface`` 為新表面）；
- ``fell`` 墜落；``deadly`` 進入致命地形；``downed`` 倒下；``escaped`` 撤離；
- ``stopped`` 移動在這一格中止（``detail``：``downed``／``escaped``／``prone``／``rooted``／
  跳過回合的狀態 ID／``displaced``）。

離開一格時引發的事件（藉機攻擊）記在離開的那一格。
"""

type StepReach = Literal["certain", "possible", "interrupted", "unreachable"]
"""這一格走不走得到：``certain`` 一定走到；``possible`` 只在一次模擬走到（看骰子）；
``interrupted`` 路徑合法，但兩次模擬都在之前被打斷；``unreachable`` 超出合法的前段（到不了）。"""


@dataclass(frozen=True, slots=True)
class PathEvent:
    kind: PathEventKind
    certain: bool
    """兩次模擬都出現（``False`` 為「可能」：看骰子或反應的決定）。"""
    other_id: UnitId | None = None
    status_id: str | None = None
    surface: Surface | None = None
    pos: XY | None = None
    amount_min: int | None = None
    """傷害的最小值；只在最多後果的模擬出現（例如藉機攻擊命中才會受傷）時為 ``None``。"""
    amount_max: int | None = None
    chance: Fraction | None = None
    """``slip_check`` 的失敗機率（精確計算，不擲骰）。"""
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class PathStep:
    pos: XY
    index: int
    """在路徑中的位置（0 為起點）。"""
    surface: Surface
    """這一格目前的表面（冰、油、火、水＝潮濕、毒……；畫路徑分段顏色用）。"""
    trap: bool
    """這一格有移動者看得見的敵方陷阱。"""
    reach: StepReach
    events: tuple[PathEvent, ...]


@dataclass(frozen=True, slots=True)
class SlipRun:
    """路徑上一段連續的冰面（6A-4f；#123 起只在第一格檢定一次）：畫面合成一張小牌。"""

    start: int
    """第一格（擲檢定的那一格）在路徑中的位置（``PathStep.index``）。"""
    end: int
    """這段冰在路徑上的最後一格（含；只算合法前段）。"""
    chance: Fraction
    """第一格的滑倒機率（精確計算，不擲骰）。這段之前被其他事件打斷的情況不另外計入。"""
    fail_stop: XY
    """滑倒時的停點（滑行後倒地的格子；倒在友軍格上時為滑回的空格）。"""
    slide_path: tuple[XY, ...]
    """滑倒時的滑行路徑：含起點（滑倒的那一格）與滑行的停點；只有起點＝一格都沒滑。"""
    stop_reason: str
    """滑行停下的原因（``unit_slid.stop_reason``：``off_ice``、``wall``、``unit``……；不會滑倒的段
    為 ``immune``）。"""
    status_id: str | None
    """失敗得到的狀態（冰面為 ``prone``；不會滑倒的段為 ``None``）。"""
    immune: bool = False
    """移動者不會在這種表面滑倒（矮人、鱗族；05 5.10「冰 N 格・不會滑倒」）：不擲、不滑。"""
    stop_trap: bool = False
    """失敗的停點上有移動者看得見的敵方陷阱（小牌加「（滑到陷阱）」）。"""
    stop_surface: Surface | None = None
    """失敗的停點上的表面（冰與無表面以外，例如火、毒）。"""

    @property
    def tiles(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True, slots=True)
class PathPreview:
    unit_id: UnitId
    path: tuple[XY, ...]
    """預覽的路徑（只給終點時為找到的最短路徑；完全沒有路時只有起點與終點）。"""
    legal_length: int
    """合法前段的格數（含起點）；0 表示一步都不能走。"""
    reachable: bool
    """整條路徑合法（終點本回合走得到；之後仍可能被打斷，見 ``stop``）。"""
    reason: str | None
    """路徑不合法的原因（合法時為 ``None``）。"""
    steps: tuple[PathStep, ...]
    stop: XY
    """最少後果時的停點（骰子都有利時會停在哪）。"""
    worst_stop: XY
    """最多後果時的停點；與 ``stop`` 相同時停點是確定的。最多後果的模擬停在 ``stop`` 但冰面分支
    （見 ``stops``）會停在別處時，取第一個不同的停點（6E-2b）。"""
    certain: bool
    """模擬沒有經過任何分歧點：預覽保證與實際結算一致。"""
    move_cost: int
    """合法前段的移動點數（含站起的消耗）。"""
    slip_runs: tuple[SlipRun, ...] = ()
    """路徑上連續有滑倒檢定的格子（冰面）合成的段，依路徑順序（6A-4f）。"""
    stops: tuple[XY, ...] = ()
    """所有模擬分支的停點（不重複；``stop`` 在前，再依分支順序；6E-2b）。路徑上有多段冰、或冰與
    陷阱並存時可能超過兩個（``stop``／``worst_stop`` 兩格放不下）；只有一個時停點是確定的。看不見
    的陷阱、以及多個互相獨立的非冰面分歧點（例如兩個陷阱各自抵抗）的組合不保證涵蓋。"""

    @property
    def stop_certain(self) -> bool:
        return self.stop == self.worst_stop and all(xy == self.stop for xy in self.stops)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def preview_path(
    state: BattleState,
    unit_id: UnitId,
    *,
    path: tuple[Pos, ...] | None = None,
    dest: Pos | None = None,
) -> PathPreview:
    """預覽 ``unit_id`` 沿 ``path``（或走到 ``dest``）的移動；恰好給一個。不修改 ``state``。

    不是這個單位的回合、或戰鬥已結束／暫停中時拋出 :class:`IllegalActionError`。"""
    if (path is None) == (dest is None):
        raise IllegalActionError("路徑預覽要給 path 或 dest 其中一個")
    if unit_id not in state.units:
        raise IllegalActionError(f"找不到單位：{unit_id}")
    unit = acting_unit(state, Move(unit_id=unit_id, path=(state.units[unit_id].pos,)))
    if path is None:
        assert dest is not None
        path = _path_to(state, unit_id, dest)
    requested = tuple((p.x, p.y) for p in path)
    legal, reason, cost = _legal_prefix(state, unit_id, path)
    seen = strip_hidden_traps(state, unit.team)
    traps = frozenset(t.xy for t in seen.traps if t.team is not unit.team)
    if legal == 0:
        steps = tuple(
            _step(seen, requested, i, traps, ("certain" if i == 0 else "unreachable", ()))
            for i in range(len(requested))
        )
        return PathPreview(
            unit_id, requested, 0, False, reason, steps, unit.xy, unit.xy, True, 0, (), (unit.xy,)
        )
    move = Move(unit_id=unit_id, path=path[:legal])
    low, high = simulate_preview(seen, move)
    fails = _SlideFailures(seen, move)
    extra = _slide_branches(seen, move, low, fails) if low is not high else []
    traces = [_trace(r, unit_id, legal) for r in (low, high, *extra)]
    steps = tuple(
        _step(
            seen,
            requested,
            i,
            traps,
            (
                _reach(i, legal, [t.walked for t in traces]),
                _merge_all([t.by_step.get(i, []) for t in traces]),
            ),
        )
        for i in range(len(requested))
    )
    stops = tuple(dict.fromkeys(t.stop for t in traces))
    worst = traces[1].stop
    if worst == traces[0].stop:
        worst = next((xy for xy in stops if xy != worst), worst)
    return PathPreview(
        unit_id=unit_id,
        path=requested,
        legal_length=legal,
        reachable=reason is None,
        reason=reason,
        steps=steps,
        stop=traces[0].stop,
        worst_stop=worst,
        certain=low is high,
        move_cost=cost,
        slip_runs=_slip_runs(seen, move, steps, fails),
        stops=stops,
    )


# ---------------------------------------------------------------------------
# 冰面檢定的分支（6E-2b）
# ---------------------------------------------------------------------------


class _SlideFailures:
    """「第 k 次滑行檢定失敗、其餘最少後果」的模擬（:func:`simulate_slide_failure`），依 k 快取：
    小牌的失敗停點與分支停點共用同一次模擬。"""

    __slots__ = ("_cache", "_move", "_state")

    def __init__(self, state: BattleState, move: Move) -> None:
        self._state, self._move = state, move
        self._cache: dict[int, ResolveResult] = {}

    def get(self, index: int) -> ResolveResult:
        if index not in self._cache:
            self._cache[index] = simulate_slide_failure(self._state, self._move, index)
        return self._cache[index]


class _SlidePassCtx(Ctx):
    """預覽分支「其餘最多後果、滑行檢定照指定」：第 ``slide_fail_at`` 次滑行檢定失敗（``-1`` 為
    都不失敗），其他滑行檢定一律通過；其餘的骰子與檢定（含被推進冰面的檢定）照 ``max``。

    :func:`trpg.engine.ice_slide._roll` 在 ``slide_fail_at`` 有值時先遞增 ``slide_checks`` 再呼叫
    :meth:`check_d20`（被指定失敗的那次不呼叫），所以呼叫時 ``slide_checks`` 增加了就是滑行檢定。"""

    __slots__ = ("_slides_seen",)

    def __init__(self, state: BattleState, fail_at: int) -> None:
        super().__init__(state, preview="max")
        self.slide_fail_at = fail_at
        self._slides_seen = 0

    def check_d20(self) -> int:
        if self.slide_checks > self._slides_seen:
            self._slides_seen = self.slide_checks
            if self.slide_checks - 1 != self.slide_fail_at:
                self.mark_branch()
                return 20
        return super().check_d20()


def _simulate_slide_max(state: BattleState, move: Move, fail_at: int) -> ResolveResult:
    ctx = _SlidePassCtx(state.clone(), fail_at)
    ACTION_HANDLERS[move.type](ctx, ctx.state.units[move.unit_id], move)
    return finish_resolution(ctx)


def _slide_branches(
    state: BattleState, move: Move, low: ResolveResult, fails: _SlideFailures
) -> list[ResolveResult]:
    """最少後果的模擬擲了 N 次滑行檢定時的其他分支：全部通過 × 其餘最多後果，以及第 k 次失敗
    （之前的通過）× 其餘最少／最多後果。沒有滑行檢定時沒有分支。"""
    checks = sum(
        isinstance(e, CheckRolled) and e.slide and e.unit_id == move.unit_id for e in low.events
    )
    if checks == 0:
        return []
    results = [_simulate_slide_max(state, move, -1)]
    for k in range(checks):
        results += [fails.get(k), _simulate_slide_max(state, move, k)]
    return results


def _path_to(state: BattleState, unit_id: UnitId, dest: Pos) -> tuple[Pos, ...]:
    """到 ``dest`` 的路徑：本回合走得到時取最短路徑；走不到時取不限成本的最短路徑（之後由合法前段
    標出到不了的部分）；完全沒有路時只有起點與終點（終點標到不了）。"""
    found = find_path(state, unit_id, dest) or find_path(state, unit_id, dest, unlimited=True)
    if found is not None:
        return tuple(found)
    start = state.units[unit_id].pos
    return (start,) if start == dest else (start, dest)


def _legal_prefix(
    state: BattleState, unit_id: UnitId, path: tuple[Pos, ...]
) -> tuple[int, str | None, int]:
    """``(合法前段格數, 完整路徑不合法的原因, 前段的移動點數)``；沒有合法前段時格數為 0。

    只用 :func:`trpg.engine.battle.plan_move` 驗證（與實際結算同一套檢查，不修改狀態）。"""
    unit = state.units[unit_id]
    reason: str | None = None
    for length in range(len(path), 0, -1):
        try:
            plan = plan_move(state, unit, path[:length])
        except IllegalActionError as error:
            if reason is None:
                reason = str(error)
            continue
        return length, reason, plan.total
    return 0, reason, 0


# ---------------------------------------------------------------------------
# 事件 → 每一格
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Trace:
    walked: int
    """走了幾步（``walk`` 模式的 ``unit_moved``）。"""
    stop: XY
    by_step: dict[int, list[PathEvent]]


def _trace(result: ResolveResult, unit_id: UnitId, legal: int) -> _Trace:
    """一次模擬的事件依「目前所在的格子」分組（離開一格時的事件記在那一格）。"""
    by_step: dict[int, list[PathEvent]] = defaultdict(list)
    step = 0
    for event in result.events:
        if isinstance(event, UnitMoved) and event.unit_id == unit_id and event.mode == "walk":
            step += 1
            continue
        converted = _convert(event, unit_id)
        if converted is not None:
            by_step[step].append(converted)
    final = result.state.units[unit_id]
    stopped = _stopped_reason(result, final, short=step < legal - 1)
    if stopped is not None:
        by_step[step].append(PathEvent("stopped", True, detail=stopped))
    return _Trace(step, final.xy, dict(by_step))


def _stopped_reason(result: ResolveResult, unit: UnitState, *, short: bool) -> str | None:
    """移動在途中中止的原因（``short``：沒有走完合法前段）；走完時為 ``None``。"""
    if not unit.alive:
        return "downed"
    if unit.escaped:
        return "escaped"
    if not short:
        return None
    rules = result.state.ruleset
    if unit.has_status(PRONE):
        return "prone"
    if is_rooted(rules, unit):
        return "rooted"
    return skip_turn_status(rules, unit) or "displaced"


def _subject(event: EventBase) -> object:
    """事件的主角：受傷／得到狀態的目標、反應的觸發者，其餘為 ``unit_id`` 欄位。"""
    if isinstance(event, DamageDealt | StatusApplied):
        return event.target_id
    if isinstance(event, ReactionTriggered):
        return event.trigger_unit_id
    return getattr(event, "unit_id", None)


def _convert(event: EventBase, unit_id: UnitId) -> PathEvent | None:
    """把模擬事件轉成路徑事件（與移動者無關的事件回傳 ``None``）；``certain`` 先填 ``True``，
    合併兩次模擬時再決定。"""
    if isinstance(event, SurfaceChanged):
        return PathEvent(
            "surface_changed", True, pos=(event.pos.x, event.pos.y), surface=event.after
        )
    if _subject(event) != unit_id:
        return None
    if isinstance(event, DamageDealt):
        amount = event.hp_before - event.hp_after
        return PathEvent(
            "damage",
            True,
            other_id=event.source_id,
            amount_min=amount,
            amount_max=amount,
            detail=event.cause,
        )
    if isinstance(event, StatusApplied):
        return PathEvent("status", True, status_id=event.status_id)
    if isinstance(event, ReactionTriggered):
        return PathEvent("reaction", True, other_id=event.unit_id, detail=event.reaction)
    return _convert_own(event)


def _convert_own(event: EventBase) -> PathEvent | None:  # noqa: PLR0911 - 單純的事件分派
    """``unit_id`` 欄位是移動者的事件。"""
    if isinstance(event, UnitMoved):
        return PathEvent("displaced", True, pos=(event.to_pos.x, event.to_pos.y), detail=event.mode)
    if isinstance(event, CheckRolled):
        failing = max(0, min(20, event.dc - event.modifier - 1))
        return PathEvent(
            "slip_check",
            True,
            status_id=event.fail_status,
            chance=Fraction(failing, 20),
            detail=event.reason,
        )
    if isinstance(event, TrapTriggered):
        return PathEvent("trap", True, other_id=event.owner_id, detail=event.skill_id)
    if isinstance(event, SurfaceEntered):
        return PathEvent("surface", True, surface=event.surface)
    if isinstance(event, UnitStoodUp):
        return PathEvent("stood_up", True)
    if isinstance(event, UnitFell):
        return PathEvent("fell", True, detail=str(event.levels))
    if isinstance(event, EnteredDeadlyTerrain):
        return PathEvent("deadly", True, detail=event.terrain)
    if isinstance(event, UnitDowned):
        return PathEvent("downed", True)
    if isinstance(event, UnitEscaped):
        return PathEvent("escaped", True)
    return None


type _Key = tuple[str, str | None, str | None, Surface | None, XY | None, str | None]


def _key(event: PathEvent) -> _Key:
    """配對兩次模擬的事件：種類與身分欄位相同即為同一件事（數值、``stopped`` 的原因可以不同）。"""
    detail = None if event.kind == "stopped" else event.detail
    return (event.kind, event.other_id, event.status_id, event.surface, event.pos, detail)


def _merge(low: list[PathEvent], high: list[PathEvent]) -> tuple[PathEvent, ...]:
    """同一格兩次模擬的事件合併：依序配對同鍵的事件——都有的為確定（傷害取兩邊的值），只有一邊的
    為可能（只在最多後果出現的傷害沒有最小值）。順序依最少後果，再接只在最多後果出現的。"""
    unmatched: dict[_Key, list[PathEvent]] = defaultdict(list)
    for event in high:
        unmatched[_key(event)].append(event)
    merged: list[PathEvent] = []
    for event in low:
        bucket = unmatched[_key(event)]
        merged.append(_paired(event, bucket.pop(0)) if bucket else replace(event, certain=False))
    leftover = {id(e) for bucket in unmatched.values() for e in bucket}
    merged.extend(
        replace(event, certain=False, amount_min=None) for event in high if id(event) in leftover
    )
    return tuple(merged)


def _merge_all(sims: list[list[PathEvent]]) -> tuple[PathEvent, ...]:
    """同一格所有模擬分支的事件：先合併最少／最多後果（:func:`_merge`），再依序併入其他分支——
    其他分支沒有的事件改為「可能」，只在其他分支出現的接在後面（「可能」，沒有傷害最小值）。"""
    merged = _merge(sims[0], sims[1])
    for extra in sims[2:]:
        merged = _fold(merged, extra)
    return merged


def _fold(merged: tuple[PathEvent, ...], extra: list[PathEvent]) -> tuple[PathEvent, ...]:
    unmatched: dict[_Key, list[PathEvent]] = defaultdict(list)
    for event in extra:
        unmatched[_key(event)].append(event)
    out: list[PathEvent] = []
    for event in merged:
        bucket = unmatched[_key(event)]
        out.append(_widen(event, bucket.pop(0)) if bucket else replace(event, certain=False))
    leftover = {id(e) for bucket in unmatched.values() for e in bucket}
    out.extend(
        replace(event, certain=False, amount_min=None) for event in extra if id(event) in leftover
    )
    return tuple(out)


def _widen(event: PathEvent, other: PathEvent) -> PathEvent:
    """已合併的事件與另一分支的同一件事：傷害範圍取聯集；``stopped`` 的原因不同時算「可能」。"""
    certain = event.certain and event.detail == other.detail
    if event.amount_max is None or other.amount_max is None:
        return replace(event, certain=certain)
    low = None if event.amount_min is None else min(event.amount_min, other.amount_max)
    return replace(
        event, certain=certain, amount_min=low, amount_max=max(event.amount_max, other.amount_max)
    )


def _paired(low: PathEvent, high: PathEvent) -> PathEvent:
    """兩次模擬都有的事件：傷害取兩邊的最小與最大；``stopped`` 的原因不同時算「可能」。"""
    if low.amount_min is None or high.amount_max is None:
        return replace(low, certain=low.detail == high.detail)
    a, b = low.amount_min, high.amount_max
    return replace(low, amount_min=min(a, b), amount_max=max(a, b))


def _reach(index: int, legal: int, walked: list[int]) -> StepReach:
    """``walked``：每個模擬分支走了幾步。"""
    if index >= legal:
        return "unreachable"
    ok = [index <= w for w in walked]
    if all(ok):
        return "certain"
    if any(ok):
        return "possible"
    return "interrupted"


def _step(
    state: BattleState,
    path: tuple[XY, ...],
    index: int,
    traps: frozenset[XY],
    outcome: tuple[StepReach, tuple[PathEvent, ...]],
) -> PathStep:
    xy = path[index]
    surface = state.tile(*xy).surface if state.in_bounds(*xy) else Surface.NONE
    return PathStep(xy, index, surface, xy in traps, outcome[0], outcome[1])


# ---------------------------------------------------------------------------
# 連續冰面（6A-4f）
# ---------------------------------------------------------------------------


def _slip_check(step: PathStep) -> PathEvent | None:
    return next((e for e in step.events if e.kind == "slip_check" and e.chance is not None), None)


def _run_start(state: BattleState, path: tuple[Pos, ...], index: int) -> bool:
    """第 ``index`` 格是不是一段冰的第一格（會滑行的表面，前一格不是同一種表面）。"""
    if index == 0:
        return False
    here, before = (path[index].x, path[index].y), (path[index - 1].x, path[index - 1].y)
    if slide_check_def(state, here) is None:
        return False
    return state.tile(*before).surface is not state.tile(*here).surface


def _slip_runs(
    state: BattleState, move: Move, steps: tuple[PathStep, ...], fails: _SlideFailures
) -> tuple[SlipRun, ...]:
    """每段冰一筆：擲滑行檢定的段（最少後果的模擬裡依序出現）另跑一次失敗的模擬取停點；不會滑倒的
    單位（矮人、鱗族）走得到的段標 ``immune``。走不到的格子不算在內。"""
    runs: list[SlipRun] = []
    unit = state.units[move.unit_id]
    immune = not is_flying(unit) and any(
        slip_immune(state.ruleset, unit, s.surface) for s in steps if s.surface is Surface.ICE
    )
    nth = 0
    for step in steps:
        if step.index >= len(move.path) or not _run_start(state, move.path, step.index):
            continue
        check = _slip_check(step)
        if check is not None:
            failed = fails.get(nth)
            runs.append(_slip_run(state, move, steps, start=step.index, failed=failed, check=check))
            nth += 1
        elif immune and step.reach in ("certain", "possible"):
            runs.append(_immune_run(steps, len(move.path), step.index))
    return tuple(runs)


def _run_end(steps: tuple[PathStep, ...], legal: int, start: int) -> int:
    end = start
    while end + 1 < legal and steps[end + 1].surface is steps[start].surface:
        end += 1
    return end


def _immune_run(steps: tuple[PathStep, ...], legal: int, start: int) -> SlipRun:
    pos = steps[start].pos
    return SlipRun(
        start=start,
        end=_run_end(steps, legal, start),
        chance=Fraction(0),
        fail_stop=pos,
        slide_path=(pos,),
        stop_reason="immune",
        status_id=None,
        immune=True,
    )


def _slip_run(
    state: BattleState,
    move: Move,
    steps: tuple[PathStep, ...],
    *,
    start: int,
    failed: ResolveResult,
    check: PathEvent,
) -> SlipRun:
    """在第 ``start`` 格擲滑行檢定的段：``failed`` 為只有這次失敗的模擬，取停點與路徑；
    停點上有看得見的敵方陷阱或冰以外的表面時一併標出（小牌寫「滑到陷阱」）。"""
    slid = next(
        (e for e in failed.events if isinstance(e, UnitSlid) and e.unit_id == move.unit_id), None
    )
    path = tuple((p.x, p.y) for p in slid.path) if slid is not None else (steps[start].pos,)
    stop = failed.state.units[move.unit_id].xy
    unit = state.units[move.unit_id]
    surface = state.tile(*stop).surface
    assert check.chance is not None
    return SlipRun(
        start=start,
        end=_run_end(steps, len(move.path), start),
        chance=check.chance,
        fail_stop=stop,
        slide_path=path,
        stop_reason=slid.stop_reason if slid is not None else "interrupted",
        status_id=check.status_id,
        stop_trap=any(t.xy == stop and t.team is not unit.team for t in state.traps),
        stop_surface=None if surface in (Surface.NONE, Surface.ICE) else surface,
    )
