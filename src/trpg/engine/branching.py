"""任意動作的分支推演（Phase 7 前置；由路徑預覽 6E-2b／6P-1 的冰面分支抽出）：
``preview_action(state, action) -> ActionPreview``。

用 **同一套引擎** 在狀態複本上模擬（:func:`trpg.engine.battle.simulate_branch`），不擲骰、不改動
傳入的狀態與 ``rng_state``：

1. **兩個極端**：``min``（最少後果：檢定對守方有利、傷害骰取最小、``prompt`` 反應不使用）與
   ``max``（最多後果）。``min`` 沒有經過任何分歧點時兩者相同（``certain``），不再推演。
2. **分歧點**：模擬中擲過的每一次守方檢定（:data:`~trpg.engine.context.CheckKind`：自己的冰面
   滑行、被推進表面的檢定、狀態抵抗——陷阱定身也是——與次要對抗），由 ``Ctx`` 記在
   ``check_log``。只看 ``kinds`` 指定的種類。
3. **分支**：每個分支是一組「這些檢定的結果」（:class:`~trpg.engine.context.CheckOverride`：第
   ``i`` 次最好或最差，沒指定的最好），× 其餘骰子取 ``min``／``max``。從「全部最好」開始，每個
   分支跑完後，把它擲過、還沒指定的檢定逐一改成最差，當成新的分支（樹狀展開：失敗讓後面的檢定
   消失時，例如冰面滑倒後不再走，分支自然變少）。順序依「最差的次數少的先、位置前面的先」，同一
   組結果先 ``min`` 再 ``max``；「全部最好 × ``min``」就是最少後果，不重複。
4. **上限**：兩個極端之外最多跑 ``limit`` 個分支（:data:`MAX_BRANCHES`）。超過時照上面的順序截斷
   （保留最差次數少的組合；兩個極端一定在，最多後果永遠涵蓋），並標 ``truncated``。

隱藏陷阱：分支推演照傳入的狀態模擬，呼叫端要先用 :func:`trpg.engine.traps.strip_hidden_traps`
移除行動者陣營看不見的陷阱（路徑預覽與一般預覽都這樣做），預覽才不洩漏。
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from trpg.engine.actions import Action
from trpg.engine.battle import simulate_branch
from trpg.engine.context import (
    CHECK_KINDS,
    CheckKind,
    CheckOutcome,
    CheckOverride,
    CheckPoint,
    GambleBranch,
    PreviewMode,
)
from trpg.engine.results import ResolveResult
from trpg.engine.state import BattleState

__all__ = ["MAX_BRANCHES", "ActionPreview", "PreviewBranch", "preview_action"]

MAX_BRANCHES = 64
"""兩個極端（最少／最多後果）之外最多推演的分支數。路徑預覽只分冰面滑行檢定，一條路徑最多
1＋2N 個（N 段冰），遠低於上限。"""


@dataclass(frozen=True, slots=True)
class PreviewBranch:
    """一個模擬分支。"""

    mode: PreviewMode
    """``kinds`` 以外的骰子與決定（傷害骰、命中、``prompt`` 反應）取最少或最多後果。"""
    worst: tuple[int, ...] | None
    """``kinds`` 的檢定裡指定為最差的是第幾次（0 起，依擲的順序；其餘最好）；``None`` 為兩個極端
    （沒有覆寫，全部檢定照 ``mode``）。"""
    checks: tuple[CheckPoint, ...]
    """這個分支實際擲過的檢定與採用的結果（全部種類，依序）。"""
    result: ResolveResult


@dataclass(frozen=True, slots=True)
class ActionPreview:
    """分支推演的結果。``branches[0]`` 為最少後果、``branches[1]`` 為最多後果（``certain`` 時與
    ``branches[0]`` 是同一個物件），之後依推演順序（見模組說明）。"""

    branches: tuple[PreviewBranch, ...]
    certain: bool
    """最少後果的模擬沒有經過任何分歧點：預覽保證與實際結算一致。"""
    truncated: bool
    """分支超過上限而截斷（有些檢定結果的組合沒有推演）。"""

    @property
    def low(self) -> PreviewBranch:
        return self.branches[0]

    @property
    def high(self) -> PreviewBranch:
        return self.branches[1]

    @property
    def results(self) -> tuple[ResolveResult, ...]:
        return tuple(b.result for b in self.branches)


def preview_action(
    state: BattleState,
    action: Action,
    *,
    kinds: tuple[CheckKind, ...] = CHECK_KINDS,
    limit: int = MAX_BRANCHES,
    gamble: GambleBranch | None = None,
) -> ActionPreview:
    """推演 ``action`` 在 ``state`` 的所有分支（見模組說明）；不修改 ``state``。

    動作不合法時拋出 :class:`~trpg.shared.errors.IllegalActionError`（與實際結算相同的檢查；是否
    輪到這個單位由呼叫端檢查，見 :func:`trpg.engine.battle.acting_unit`）。"""
    low_result, low_checks, branched = simulate_branch(state, action, "min", gamble=gamble)
    low = PreviewBranch("min", None, low_checks, low_result)
    if not branched:
        return ActionPreview((low, low), certain=True, truncated=False)
    high_result, high_checks, _ = simulate_branch(state, action, "max", gamble=gamble)
    high = PreviewBranch("max", None, high_checks, high_result)
    explorer = _Explorer(state, action, kinds, limit, gamble)
    extra = explorer.explore(low_checks)
    return ActionPreview((low, high, *extra), certain=False, truncated=explorer.truncated)


_MODES: tuple[PreviewMode, ...] = ("min", "max")


def _count(checks: tuple[CheckPoint, ...], kinds: tuple[CheckKind, ...]) -> int:
    return sum(c.kind in kinds for c in checks)


def _pattern(worst: tuple[int, ...]) -> tuple[CheckOutcome, ...]:
    """「第 ``worst`` 次最差、其餘最好」的前段（之後由覆寫的 ``rest`` 補最好）。"""
    length = worst[-1] + 1 if worst else 0
    marks = frozenset(worst)
    return tuple("worst" if i in marks else "best" for i in range(length))


class _Explorer:
    """依「最差的次數、位置」由小到大展開檢定結果的組合（:func:`heapq`，確定性）。"""

    __slots__ = ("_action", "_gamble", "_kinds", "_limit", "_state", "truncated")

    def __init__(
        self,
        state: BattleState,
        action: Action,
        kinds: tuple[CheckKind, ...],
        limit: int,
        gamble: GambleBranch | None,
    ) -> None:
        self._state, self._action, self._kinds = state, action, kinds
        self._limit, self._gamble = limit, gamble
        self.truncated = False

    def explore(self, low_checks: tuple[CheckPoint, ...]) -> list[PreviewBranch]:
        """兩個極端之外的分支。``low_checks``：最少後果（＝全部最好 × ``min``）擲過的檢定。"""
        if _count(low_checks, self._kinds) == 0:
            return []
        out: list[PreviewBranch] = []
        heap: list[tuple[int, tuple[int, ...]]] = [(0, ())]
        queued: set[tuple[int, ...]] = {()}
        while heap:
            _, worst = heapq.heappop(heap)
            for mode in _MODES:
                if not worst and mode == "min":
                    checks = low_checks  # 全部最好 × min ＝ 最少後果，已經有了
                else:
                    if len(out) >= self._limit:
                        self.truncated = True
                        return out
                    branch = self._run(worst, mode)
                    out.append(branch)
                    checks = branch.checks
                for child in self._children(worst, checks):
                    if child not in queued:
                        queued.add(child)
                        heapq.heappush(heap, (len(child), child))
        return out

    def _run(self, worst: tuple[int, ...], mode: PreviewMode) -> PreviewBranch:
        override = CheckOverride.of(self._kinds, outcomes=_pattern(worst), rest="best")
        result, checks, _ = simulate_branch(
            self._state, self._action, mode, override=override, gamble=self._gamble
        )
        return PreviewBranch(mode, worst, checks, result)

    def _children(
        self, worst: tuple[int, ...], checks: tuple[CheckPoint, ...]
    ) -> list[tuple[int, ...]]:
        """這個分支擲過、還沒指定（在最後一個最差之後）的檢定，各自改成最差。"""
        start = worst[-1] + 1 if worst else 0
        return [(*worst, j) for j in range(start, _count(checks, self._kinds))]
