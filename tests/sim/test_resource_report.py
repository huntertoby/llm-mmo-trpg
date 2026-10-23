"""資源不足回合比例的模擬報表（Phase 3H-2）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.sim.attack_flow_report import SCENARIOS
from trpg.sim.resource_report import (
    ResourceSample,
    format_resources,
    run_resources,
    summarize_resources,
)


def test_summary_counts_turns_and_shortages() -> None:
    samples = [
        ResourceSample("single", "b", 0, won=True, turns=4, mana_short=1, stamina_short=2,
                       any_short=2, mana_left_permille=500, stamina_left_permille=0),
        ResourceSample("single", "b", 1, won=False, turns=6, stamina_short=3, any_short=3,
                       mana_left_permille=1000, stamina_left_permille=200),
        ResourceSample("single", "b", 2, ok=False),
    ]  # fmt: skip
    (cell,) = summarize_resources(samples)
    assert (cell.battles, cell.failed, cell.turns) == (2, 1, 10)
    assert (cell.win_rate, cell.mana_short, cell.stamina_short, cell.any_short) == (
        0.5,
        0.1,
        0.5,
        0.5,
    )
    assert (cell.mana_left, cell.stamina_left) == (0.75, 0.1)
    table = format_resources([cell], {"single": "長戰單體"}, {"b": "測試"})
    assert "| 長戰單體 | 測試 | 2（失敗 1） | 50% | 10 | 10% | 50% | 50% | 75% | 10% |" in table


def test_a_small_run_is_deterministic_and_counts_hero_turns() -> None:
    scenario = (SCENARIOS[0],)
    a = run_resources(library(), scenarios=scenario, builds=("build_skill_archer",), seeds=1)
    b = run_resources(library(), scenarios=scenario, builds=("build_skill_archer",), seeds=1)
    assert a == b
    (sample,) = a
    assert sample.ok and sample.turns > 0
    assert 0 <= sample.any_short <= sample.turns
    assert sample.mana_short + sample.stamina_short >= sample.any_short
