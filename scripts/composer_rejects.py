"""組合器「驗證失敗退回」統計（Phase 2F-2 4.1）。

對每個啟用的骨架各組 ``--count`` 個技能（明確指定骨架、稀有度隨機），統計重抽（退回）的
次數與原因：嘗試階段丟出的 ``Retry``／``ValidationError``／``BudgetError``，以及 ``validate_skill``
回報的違規規則（例如 ``skeleton.core``）。輸出摘要表（不含時間）。

用法::

    uv run python scripts/composer_rejects.py --count 300
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from pydantic import ValidationError

from trpg.skillgen import random_composer as rc
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_parts import Retry
from trpg.skillgen.validate import validate_skill

_STATS: dict[str, Counter[str]] = {}
_CURRENT = {"skeleton": ""}


def _wrap_attempt(name: str) -> None:
    original = getattr(rc, name)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return original(*args, **kwargs)
        except (Retry, ValidationError, BudgetError) as exc:
            _STATS[_CURRENT["skeleton"]][f"attempt:{type(exc).__name__}"] += 1
            raise

    setattr(rc, name, wrapped)


def _wrap_validate() -> None:
    def wrapped(skill: Any, library: Any) -> Any:
        violations = validate_skill(skill, library)
        for rule in sorted({v.rule for v in violations}):
            _STATS[_CURRENT["skeleton"]][f"validate:{rule}"] += 1
        return violations

    setattr(rc, "validate_skill", wrapped)  # noqa: B010


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=300, help="每個骨架的技能個數（預設 300）")
    args = parser.parse_args(argv)
    for name in ("_attempt", "_attempt_passive", "_attempt_reaction", "_attempt_stance"):
        _wrap_attempt(name)
    _wrap_validate()
    library = rc.default_library()
    skeletons = sorted(s.id for s in library.skeletons.values() if s.enabled)
    print(f"{'骨架':<18}{'組出':>6}{'失敗':>6}{'退回總數':>9}  原因（次數）")
    for skeleton in skeletons:
        _STATS[skeleton] = Counter()
        _CURRENT["skeleton"] = skeleton
        ok = failed = rejected = 0
        for seed in range(args.count):
            try:
                result = rc.compose_with_stats(seed, skeleton=skeleton, library=library)
            except rc.ComposeError:
                failed += 1
                rejected += rc.MAX_ATTEMPTS
                continue
            ok += 1
            rejected += result.attempts - 1
        reasons = ", ".join(f"{k}={v}" for k, v in sorted(_STATS[skeleton].items()))
        print(f"{skeleton:<18}{ok:>6}{failed:>6}{rejected:>9}  {reasons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
