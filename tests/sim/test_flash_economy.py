"""靈感經濟掃描（BAL-1）：參數覆寫、解析、確定性、預設值等於現行行為。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.sim.flash_economy import (
    Economy,
    current_economy,
    format_economy_report,
    parse_economy,
    run_economy_sweep,
    with_economy,
)
from trpg.sim.flash_report import simulate_run


def test_defaults_equal_current_behavior() -> None:
    lib = library()
    rules = lib.flash.rules
    assert current_economy(lib) == Economy(
        win=rules.insight_per_win, start=rules.insight_start, preboss=rules.insight_preboss
    )


def test_with_economy_does_not_touch_original() -> None:
    lib = library()
    copy = with_economy(lib, Economy(win=2, start=3, preboss=1))
    assert (copy.flash.rules.insight_per_win, copy.flash.rules.insight_start) == (2, 3)
    assert copy.flash.rules.insight_preboss == 1
    assert current_economy(lib) == Economy(
        lib.flash.rules.insight_per_win,
        lib.flash.rules.insight_start,
        lib.flash.rules.insight_preboss,
    )


def test_default_override_is_identical_to_plain_run() -> None:
    lib = library()
    plain = simulate_run(lib, "none", 1)
    same = simulate_run(with_economy(lib, current_economy(lib)), "none", 1)
    assert plain == same


def test_parse_economy_product_and_defaults() -> None:
    lib = library()
    combos = parse_economy(lib, "win=1,2;start=0,2")
    assert combos == [Economy(1, 0, 0), Economy(1, 2, 0), Economy(2, 0, 0), Economy(2, 2, 0)]
    assert parse_economy(lib, "") == [current_economy(lib)]


@pytest.mark.parametrize("spec", ["bogus=1", "win=", "win=-1", "win=x", "win"])
def test_parse_economy_rejects_bad_spec(spec: str) -> None:
    with pytest.raises(ValueError):
        parse_economy(library(), spec)


def test_sweep_small_deterministic_and_start_bonus_counts() -> None:
    lib = library()
    economies = [Economy(1, 2, 0)]
    first = run_economy_sweep(lib, economies, ["none"], [0, 1], jobs=1)
    again = run_economy_sweep(lib, economies, ["none"], [0, 1], jobs=1)
    assert first == again
    text = format_economy_report(first)
    assert text == format_economy_report(again)
    assert "| 1 | 2 | 0 | none | 2 |" in text
    # 開局 2 點：第一場勝利之後，手上加已花至少 3 點（2 開局 ＋ 1 每勝）
    for run in first[0].runs:
        if run.curve:
            _, held, spent = run.curve[0]
            assert held + spent == 3


def test_preboss_bonus_lands_after_last_normal_battle() -> None:
    lib = library()
    rows = run_economy_sweep(lib, [Economy(1, 0, 2)], ["none"], [0, 1], jobs=1)
    seen = 0
    for run in rows[0].runs:
        for n, held, spent in run.curve:
            if n == 5:  # 第 5 場是最後一場一般戰鬥（battles: 5）
                assert held + spent == 5 + 2
                seen += 1
            elif n < 5:
                assert held + spent == n
    assert seen >= 1
