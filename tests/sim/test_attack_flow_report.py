"""``trpg.sim.attack_flow_report``（Phase 3-32a）：普攻流 vs 技能流弓手的三情境對照模擬。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.sim.attack_flow_report import (
    BUILDS,
    SCENARIOS,
    format_attack_flow,
    format_diagnosis,
    format_new_metrics,
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


def test_new_metrics_and_diagnosis_fields_are_filled_and_deterministic() -> None:
    """3-32d：擊殺輪數、清場輪數、打不出技能的回合、傷害來源與範圍技命中數。"""
    lib = library()
    a = run_attack_flow(lib, seeds=2)
    b = run_attack_flow(lib, seeds=2)
    assert [x.flow for x in a] == [x.flow for x in b]
    assert all(x.flow is not None for x in a)
    by_key = {(x.scenario, x.build, x.seed): x.flow for x in a}
    boss = by_key[("boss", "build_attack_archer", 0)]
    assert boss is not None and boss.has_boss and boss.hero_turns > 0
    assert boss.no_skill_turns == boss.no_skill_mana + boss.no_skill_cooldown
    single = by_key[("single", "build_skill_archer", 0)]
    assert single is not None and not single.has_boss and single.boss_kill_round is None
    for x in a:
        assert x.flow is not None
        if x.flow.clear_round is not None:
            assert 1 <= x.flow.clear_round <= (x.metrics.rounds if x.metrics else 99)
    flows = [x.flow for x in a if x.build == "build_attack_archer" and x.flow is not None]
    attack = next(f for f in flows if f.attack_hits)
    sources = attack.damage_by_source
    assert sources["basic"] + sources.get("combo", 0) + sources["mastery"] > 0
    summaries = summarize(a)
    names = {c.id: c.name_zh for c in lib.builds.builds}
    text = format_new_metrics(summaries, names)
    assert "Boss 擊殺輪數" in text and "範圍清場輪數" in text and "長戰單體 DPR" in text
    diag = format_diagnosis(summaries, names)
    assert "打不出技能的回合" in diag and "平均涵蓋敵人數" in diag
    boss_skill = next(
        s for s in summaries if (s.scenario, s.build) == ("boss", "build_skill_archer")
    )
    assert boss_skill.hero_turns > 0 and 0.0 <= boss_skill.boss_kill_rate <= 1.0
