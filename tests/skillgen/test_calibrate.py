"""``scripts/calibrate_tier_budget.py``：校準腳本重現 ``core.yaml`` 的 T1、T2。"""

from __future__ import annotations

import importlib.util
import sys
from fractions import Fraction
from pathlib import Path
from types import ModuleType

import pytest

from tests.known_budget_exceptions import RANGE_BUDGET_EXCEPTIONS
from tests.skillgen.helpers import lib

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "calibrate_tier_budget.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("calibrate_tier_budget", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_every_shipped_skill_is_inside_its_tier_window() -> None:
    """示範技能調整後，每個技能的合格區間都包含 ``core.yaml`` 的 tier_budget。
    （校準當時、技能尚未調整時的結果是 T1 ＝ 14、T2 ＝ 15，見 Phase2B-2報告。）"""
    script = _load()
    windows = script.implied_windows(lib())
    assert sorted(windows) == [1, 2]  # 只有階級 1、2 有示範技能
    core = lib().ruleset.core.tier_budget
    for tier, all_entries in windows.items():
        # 裝備授予的技能（3G-G3b，標籤 gear）的預算算在詞條上，不參與階級預算校準
        entries = [
            e
            for e in all_entries
            if not e[0].startswith("skill_gear_") and e[0] not in RANGE_BUDGET_EXCEPTIONS
        ]
        assert script.count_ok(entries, core[tier]) == len(entries)


def test_windows_follow_the_ratio_bounds() -> None:
    script = _load()
    for entries in script.implied_windows(lib()).values():
        for _, low, high in entries:
            assert high == low / Fraction(7, 10)  # 上限 ＝ 下限 ÷ 0.7


def test_the_script_prints_a_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert _load().main(["--min", "10", "--max", "16"]) == 0
    out = capsys.readouterr().out
    assert "最佳（嚴格遞增）：T1=" in out and "階級 2：" in out and "候選值 → 合格技能數" in out
