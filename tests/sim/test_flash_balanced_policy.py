"""均衡玩家的閃現 AI（BAL-2b）：優先閃沒閃過的技能、輪流各技能種類；預設行為不變。"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.engine.helpers import library
from trpg.cli.main import build_parser
from trpg.roguelite.auto import ALL_FLASH_POLICIES, FLASH_POLICIES, FlashPolicy, auto_play
from trpg.roguelite.start import default_start, new_keyword_run
from trpg.roguelite.state import RunState
from trpg.sim.flash_economy import current_economy, with_economy


def _final(policy: FlashPolicy, seed: int, *, win: int | None = None) -> RunState:
    lib = library()
    if win is not None:  # 明確指定每勝點數（不依賴 content 預設）
        lib = with_economy(lib, replace(current_economy(lib), win=win))
    weapon, keywords = default_start(lib, seed)
    run = new_keyword_run(lib, weapon, keywords, seed)
    final, _ = auto_play(lib, run, flash_policy=policy)
    return final


def _flashed(run: RunState) -> list[int]:
    """每個有閃過的技能的閃現次數（依技能 ID 排序）。"""
    return [len(s.records) for _, s in sorted(run.flash.items()) if s.records]


def test_balanced_is_an_option_but_not_a_default_policy() -> None:
    assert FLASH_POLICIES == ("none", "all", "mixed")
    assert ALL_FLASH_POLICIES == ("none", "all", "mixed", "balanced")
    parser = build_parser()
    got = parser.parse_args(["run", "auto", "--seed", "1", "--flash-policy", "balanced"])
    assert got.flash_policy == "balanced"
    assert parser.parse_args(["run", "auto", "--seed", "1"]).flash_policy == "none"


@pytest.mark.slow
def test_balanced_spreads_flashes_over_more_skills_and_is_deterministic() -> None:
    seeds = (4, 6, 7)  # BAL-9c：Boss 戰數值改動後重挑種子（原 1, 2, 3）；斷言不變
    # 差異在點數吃緊（每勝 1 點）時才看得出來；每勝 2 點時兩種策略結果相同（見 BAL-1b 報告）
    spread = {p: [len(_flashed(_final(p, s, win=1))) for s in seeds] for p in ("none", "balanced")}
    assert sum(spread["balanced"]) > sum(spread["none"])
    assert _final("balanced", 6, win=1) == _final("balanced", 6, win=1)
