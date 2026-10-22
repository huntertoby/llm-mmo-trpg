"""``trpg.sim.attack_flow_report``（Phase 3-32a）：普攻流 vs 技能流弓手的三情境對照模擬。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.sim.attack_flow_report import (
    BUILDS,
    SCENARIOS,
    format_attack_flow,
    run_attack_flow,
    summarize,
)


def test_attack_flow_sim_is_deterministic_and_covers_every_cell() -> None:
    lib = library()
    a = run_attack_flow(lib, seeds=1)
    b = run_attack_flow(lib, seeds=1)
    assert [x.metrics for x in a] == [x.metrics for x in b]
    assert all(x.metrics is not None for x in a)
    summaries = summarize(a)
    assert [(s.scenario, s.build) for s in summaries] == [
        (sc.id, build) for sc in SCENARIOS for build in BUILDS
    ]
    assert all(s.battles == 1 and s.failed == 0 for s in summaries)
    labels = {s.id: s.label_zh for s in SCENARIOS}
    names = {b.id: b.name_zh for b in lib.builds.builds}
    text = format_attack_flow(summaries, labels, names)
    assert "長戰單體" in text and "普攻流弓手" in text and "技能流弓手" in text
    assert "未完成（例外或動作上限）：0 場" in text
