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
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.validate import share_violations

__all__ = ["HIGH", "LOW", "tune"]

LOW = Fraction(75, 100)
"""調整後的比例下限（驗證器的合格區間是 0.70–1.00，組合器收在 0.75–0.95）。"""
HIGH = Fraction(95, 100)

_TARGET_STEPS = 100
_JUMP_SHARE = Fraction(3, 5)


class _Evaluator:
    def __init__(
        self, library: ContentLibrary, base: dict[str, Any], effects: list[dict[str, Any]]
    ) -> None:
        self.library = library
        self.base = base
        self.effects = effects
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
    effects[knob.index][knob.field] = knob.value


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
    _apply(knob, ev.effects)
    one = ev.ratio()
    if one is None or one > HIGH or ev.shares > shares:
        knob.pos = start
        _apply(knob, ev.effects)
        ev.shares = shares
        return ratio, False
    step = one - ratio
    gap = target - one
    if gap > 0 and step > 0 and knob.can_up():
        extra = min(int(gap / step * _JUMP_SHARE), len(knob.values) - 1 - knob.pos)
        if extra > 0:
            knob.pos += extra
            _apply(knob, ev.effects)
            far = ev.ratio()
            if far is not None and far <= HIGH and ev.shares <= shares:
                return far, True
            knob.pos = start + 1
            _apply(knob, ev.effects)
            ev.ratio()
    return one, True


def tune(
    rng: Rng,
    library: ContentLibrary,
    base: dict[str, Any],
    effects: list[dict[str, Any]],
    knobs: list[Knob],
) -> bool:
    """調整旋鈕使比例落在 ``[LOW, HIGH]``；成功時 ``effects`` 已是最終數值。

    先抽目標比例（均勻分佈在 ``[LOW, HIGH − 0.02]``）再往上調，所以整體的比例分佈是均勻的。
    """
    ev = _Evaluator(library, base, effects)
    for knob in knobs:
        knob.pos = 0
        _apply(knob, effects)
    ratio = ev.ratio()
    if ratio is None or ratio > HIGH:
        return False
    span = HIGH - LOW - Fraction(2, 100)
    target = LOW + span * Fraction(rng.randint(0, _TARGET_STEPS), _TARGET_STEPS)
    blocked: set[int] = set()
    while ratio < target:
        live = [k for k in knobs if k.can_up() and id(k) not in blocked]
        if not live:
            break
        knob = _pick(rng, live)
        ratio, accepted = _raise(knob, ev, ratio, target)
        if not accepted:
            blocked.add(id(knob))
    return ratio >= LOW and ev.shares == 0
