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


def test_guaranteed_summoner_packs_summon_on_the_boss_map() -> None:
    lib = library()
    samples = run_summon_sim(
        lib, packs=["dev_summoner", "dev_summoner_bone"], maps=["boss"], seeds=1
    )
    assert all(s.metrics is not None for s in samples)
    for s in summarize(samples):
        assert s.summons_total >= 1 and s.failed == 0


def test_a_summoner_battle_with_growth_and_infusion_replays_identically() -> None:
    """成長、灌注與 Boss ×2 都是確定的：初始狀態 ＋ 動作列表重播得到同一個終局（3-33b）。"""
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415
    from trpg.engine.events import UnitSummoned  # noqa: PLC0415
    from trpg.engine.runner import replay, run_battle  # noqa: PLC0415
    from trpg.engine.state import state_to_json  # noqa: PLC0415
    from trpg.sim.summon_report import _spec  # noqa: PLC0415

    lib = library()
    spec, _ = _spec(lib, "dev_summoner", "boss", 1, 30)
    seed = spec.seeds[0]
    run = run_battle(spec.setup, seed, UtilityAI(lib.ai_profiles))
    again = replay(spec.setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    summoned = [e for e in run.events if isinstance(e, UnitSummoned)]
    assert summoned and all(e.infusion == "ignite" and e.max_hp is not None for e in summoned)
