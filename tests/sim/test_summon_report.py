"""``trpg.sim.summon_report``（Phase 3-33a）：召喚物現況模擬。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.shared.types import Team
from trpg.sim.summon_report import format_summons, run_summon_sim, summarize


def test_summon_sim_is_deterministic_and_reports() -> None:
    lib = library()
    packs = ["dev_spirit", "dev_blaze"]
    a = run_summon_sim(lib, packs=packs, maps=["open_plain"], seeds=2)
    b = run_summon_sim(lib, packs=packs, maps=["open_plain"], seeds=2)
    assert [x.metrics for x in a] == [x.metrics for x in b]
    assert all(x.metrics is not None for x in a)
    summaries = summarize(a)
    assert [s.pack for s in summaries] == packs
    for sample in a:
        assert sample.metrics is not None
        mine = [r for r in sample.metrics.summons if r.team is Team.ALLY]
        assert len(mine) == sample.metrics.summon_events.get("ally", 0)
        assert sample.metrics.summon_damage(Team.ALLY) <= sample.metrics.team_damage(Team.ALLY)
    blaze = summaries[1]
    assert blaze.summons_total == 0 and blaze.life_rounds_mean is None
    text = format_summons(summaries, {"dev_spirit": "喚靈"})
    assert "喚靈（dev_spirit）" in text and "未完成（例外或動作上限）：0 場" in text
