"""隨機組合器的強度調整（``docs/phases/Phase2B計畫.md`` 5.1 的「調整強度」）。

所有旋鈕（骰子、武器倍率、狀態與表面的持續、推拉距離）從最弱開始，隨機挑一個往上調（核心效果的
旋鈕權重較高），直到預算比例達到事先抽好的目標（落在合格區間內）；調一格就超過上限的旋鈕被封鎖。
比例用 :class:`fractions.Fraction` 計算，結果完全確定。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob, set_knob_value
from trpg.skillgen.validate import share_violations

__all__ = ["base_ratio", "tune", "tuning_bounds"]


def tuning_bounds(library: ContentLibrary) -> tuple[Fraction, Fraction]:
    """調整後的比例區間 ``(low, high)``（``skill_composer.yaml``；驗證器的合格區間是 0.70–1.00，
    組合器收在 0.75–0.95）。"""
    rules = library.composer.tuning
    return Fraction(rules.low_permille, 1000), Fraction(rules.high_permille, 1000)


class _Evaluator:
    def __init__(
        self,
        library: ContentLibrary,
        base: dict[str, Any],
        effects: list[dict[str, Any]],
        extra: Sequence[dict[str, Any]] = (),
    ) -> None:
        self.library = library
        self.high = tuning_bounds(library)[1]
        self.jump_share = Fraction(library.composer.tuning.jump_share_permille, 1000)
        self.base = base
        self.effects = effects
        self.targets: list[dict[str, Any]] = [*effects, *extra]
        """旋鈕調整的效果字典：``effects`` 之後接 ``extra``（同一批物件，就地修改）。"""
        self.shares = 0

    def ratio(self) -> Fraction | None:
        """目前旋鈕下的預算比例；結構不合法時為 ``None``。

        骨架的占比限制（核心占比、個別原語的占比）被違反的數量記在 :attr:`shares`；
        調整時不允許讓它變多。
        """
        try:
            skill = SkillDef.model_validate({**self.base, "effects": self.effects})
            report = skill_budget(skill, self.library)
        except (ValidationError, BudgetError):
            return None
        self.shares = len(share_violations(skill, self.library, report))
        return report.ratio


def _apply(knob: Knob, effects: list[dict[str, Any]]) -> None:
    set_knob_value(effects[knob.index], knob.field, knob.value)


def _pick(rng: Rng, knobs: Sequence[Knob]) -> Knob:
    total = sum(k.weight for k in knobs)
    roll = rng.randint(1, total)
    for knob in knobs:
        roll -= knob.weight
        if roll <= 0:
            return knob
    return knobs[-1]  # pragma: no cover - roll 一定在 [1, total]


def _raise(knob: Knob, ev: _Evaluator, ratio: Fraction, target: Fraction) -> tuple[Fraction, bool]:
    """把 ``knob`` 往上調（先試一格估算每格的增量，再依缺口一次跳多格）。

    回傳 ``(新的比例, 是否被接受)``；被拒絕（一格就超過上限）時旋鈕回到原位。
    """
    start = knob.pos
    shares = ev.shares
    knob.pos = start + 1
    _apply(knob, ev.targets)
    one = ev.ratio()
    if one is None or one > ev.high or ev.shares > shares:
        knob.pos = start
        _apply(knob, ev.targets)
        ev.shares = shares
        return ratio, False
    step = one - ratio
    gap = target - one
    if gap > 0 and step > 0 and knob.can_up():
        extra = min(int(gap / step * ev.jump_share), len(knob.values) - 1 - knob.pos)
        if extra > 0:
            knob.pos += extra
            _apply(knob, ev.targets)
            far = ev.ratio()
            if far is not None and far <= ev.high and ev.shares <= shares:
                return far, True
            knob.pos = start + 1
            _apply(knob, ev.targets)
            ev.ratio()
    return one, True


def base_ratio(
    library: ContentLibrary,
    base: dict[str, Any],
    effects: list[dict[str, Any]],
    knobs: list[Knob],
    *,
    extra: Sequence[dict[str, Any]] = (),
) -> Fraction | None:
    """所有旋鈕在最弱時的預算比例（Phase 4-L8b：判斷結構在最低強度下是否已超出預算）；旋鈕會被
    歸零。結構不合法時為 ``None``。"""
    ev = _Evaluator(library, base, effects, extra)
    for knob in knobs:
        knob.pos = 0
        _apply(knob, ev.targets)
    return ev.ratio()


def tune(
    rng: Rng,
    library: ContentLibrary,
    base: dict[str, Any],
    effects: list[dict[str, Any]],
    knobs: list[Knob],
    *,
    extra: Sequence[dict[str, Any]] = (),
    min_ratio: Fraction | None = None,
    target_ratio: Fraction | None = None,
) -> bool:
    """調整旋鈕使比例落在 ``[low, high]``；成功時 ``effects`` 已是最終數值。

    先抽目標比例（均勻分佈在 ``[low, high − margin]``）再往上調，所以整體的比例分佈是均勻的。
    ``extra``（Phase 4-L8）：``base`` 裡其他要調的效果字典（例如複合技能第二段的效果，與
    ``base["followup"]["effects"]`` 是同一批物件）；旋鈕的 ``index`` 超過 ``effects`` 的長度時指向
    ``extra``。隨機組合器不傳，行為不變。

    ``min_ratio``（Phase 3W-2，閃現的強度下限）：最終比例至少要有這麼多——目標比例與上限都跟著抬高
    到它（上限最多再多一個 ``target_margin``，仍受驗證器的 0.70–1.00 窗約束）。

    ``target_ratio``（Phase 3W-9b，升階重配維持原本的比例）：目標比例改用它、不再抽；合格區間放寬到
    驗證器的窗（0.70–1.00）。
    """
    rules = library.composer.tuning
    low, high = tuning_bounds(library)
    ev = _Evaluator(library, base, effects, extra)
    margin = Fraction(rules.target_margin_permille, 1000)
    if min_ratio is not None or target_ratio is not None:
        high = ev.high = Fraction(1)  # 有下限或指定目標時上限放到驗證器的上限（1.00）
    for knob in knobs:
        knob.pos = 0
        _apply(knob, ev.targets)
    ratio = ev.ratio()
    if ratio is None or ratio > high:
        return False
    span = high - low - margin
    target = low + span * Fraction(rng.randint(0, rules.target_steps), rules.target_steps)
    if target_ratio is not None:
        target = target_ratio
        low = Fraction(library.budget.min_ratio_permille, 1000)
    if min_ratio is not None:
        target = max(target, min_ratio)
    blocked: set[int] = set()
    last: Knob | None = None
    while ratio < target:
        live = [k for k in knobs if k.can_up() and id(k) not in blocked]
        if not live:
            break
        knob = _pick(rng, live)
        ratio, accepted = _raise(knob, ev, ratio, target)
        if not accepted:
            blocked.add(id(knob))
        else:
            last = knob
    floor = max(low, min_ratio or low)
    if target_ratio is not None and last is not None and ratio > target:
        ratio = _nearer(last, ev, ratio, target, floor)
    return ratio >= floor and ev.shares == 0


def _nearer(
    knob: Knob, ev: _Evaluator, ratio: Fraction, target: Fraction, floor: Fraction
) -> Fraction:
    """指定目標比例時（3W-9b）：最後調的旋鈕往回一格若更接近目標（且不低於 ``floor``）就退回。"""
    if knob.pos == 0:
        return ratio
    shares = ev.shares
    knob.pos -= 1
    _apply(knob, ev.targets)
    back = ev.ratio()
    if (
        back is not None
        and back >= floor
        and ev.shares <= shares
        and target - back < ratio - target
    ):
        return back
    knob.pos += 1
    _apply(knob, ev.targets)
    ev.ratio()
    return ratio
