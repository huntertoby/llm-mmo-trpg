"""技能報表（Phase 2C-3 5.5、5.6-7）：百分位、離群標記、彙總與確定性。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main
from trpg.shared.types import Team
from trpg.sim.batch import BatchReport, BattleOutcome, build_report
from trpg.sim.metrics import BattleMetrics, SkillMetrics, UnitMetrics
from trpg.sim.skill_report import (
    SkillCase,
    build_skill_report,
    demo_cases,
    format_skill_report,
    percentile,
    random_cases,
    run_skill_report,
)


def test_percentile_uses_linear_interpolation() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 0) == 10.0 and percentile(values, 100) == 50.0
    assert percentile(values, 50) == 30.0
    assert percentile(values, 5) == pytest.approx(12.0)
    assert percentile(values, 95) == pytest.approx(48.0)
    assert percentile([7.0], 95) == 7.0 and percentile([], 50) == 0.0
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0  # 不要求已排序


def _batch(skill_id: str, caster: str, dpr_damage: int, uses: int) -> BatchReport:
    unit = UnitMetrics(
        unit_id="unit_0001",
        template_id=caster,
        team=Team.ALLY,
        alive_rounds=4,
        turns=4,
        ap_spent=8,
        damage_direct=dpr_damage,
        damage_indirect=0,
        damage_friendly=0,
        damage_taken=0,
        healing_done=0,
        kills=0,
        downed=False,
        control_inflicted={},
    )
    metrics = BattleMetrics(
        seed=0,
        result="ally",
        rounds=4,
        actions=10,
        units=(unit,),
        environment_damage={},
        environment_control={},
        skills={skill_id: SkillMetrics(uses=uses, rolls=uses, hits=uses, damage=dpr_damage)},
        skill_users={skill_id: ("ally",)},
        chain_limit_count=0,
        boss_burst=None,
        one_shot_count=0,
    )
    return build_report(skill_id, [BattleOutcome(0, metrics)], equipped=[skill_id])


def test_dpr_above_one_point_two_times_the_tier_p95_is_flagged() -> None:
    lib = library()
    # 同為 1 階的 5 個示範技能：DPR（傷害 ÷ 4 輪）= 10、10、10、10、20
    ids = ["skill_cleave", "skill_whirlwind", "skill_bone_crusher", "skill_execute", "skill_blink"]
    damage = [40, 40, 40, 40, 80]
    cases = [SkillCase(lib.skills[i], "demo") for i in ids]
    reports = [_batch(i, "hero_fighter", d, 2) for i, d in zip(ids, damage, strict=True)]
    report = build_skill_report(cases, reports, [0], caster_ids=["hero_fighter"] * 5)
    (tier,) = report.tiers
    assert tier.tier == 1 and tier.skills == 5
    assert tier.p5 == pytest.approx(10.0) and tier.p50 == pytest.approx(10.0)
    # P95 = 10 + (20 − 10) × 0.8 = 18；門檻 21.6 → DPR 20 沒有超過，不標出
    assert tier.p95 == pytest.approx(18.0) and tier.threshold == pytest.approx(21.6)
    assert tier.flagged == ()
    # 最後一個技能加到 DPR 30：P95 = 10 + 20 × 0.8 = 26，門檻 31.2 → 仍不標出（離群者自己拉高 P95）
    reports[-1] = _batch(ids[-1], "hero_fighter", 120, 2)
    again = build_skill_report(cases, reports, [0], caster_ids=["hero_fighter"] * 5)
    assert again.tiers[0].p95 == pytest.approx(26.0) and again.tiers[0].flagged == ()


def test_a_skill_far_above_the_rest_of_its_tier_is_flagged_and_marked_in_the_text() -> None:
    lib = library()
    ids = sorted(k for k, s in lib.skills.items() if s.tier == 1)
    cases = [SkillCase(lib.skills[i], "demo") for i in ids]
    # 17 個 DPR 10、1 個 DPR 100：P95 = 10 + 90 × 0.15 = 23.5 → 門檻 28.2 → 100 被標出
    reports = [_batch(i, "hero_fighter", 40, 1) for i in ids[:-1]]
    reports.append(_batch(ids[-1], "hero_fighter", 400, 1))
    report = build_skill_report(cases, reports, [0], caster_ids=["hero_fighter"] * len(ids))
    assert report.tiers[0].flagged == (ids[-1],)
    assert [r.skill_id for r in report.rows if r.flagged] == [ids[-1]]
    text = format_skill_report(report)
    assert f"{ids[-1]}*" in text and f"{ids[0]}*" not in text
    assert text == format_skill_report(report)


def test_skeleton_summary_averages_dpr_and_usage() -> None:
    lib = library()
    ids = ["skill_cleave", "skill_whirlwind"]  # 都是 area
    cases = [SkillCase(lib.skills[i], "demo") for i in ids]
    reports = [
        _batch("skill_cleave", "hero_fighter", 40, 2),
        _batch("skill_whirlwind", "hero_fighter", 80, 4),
    ]
    report = build_skill_report(cases, reports, [0], caster_ids=["hero_fighter"] * 2)
    (area,) = report.skeletons
    assert (area.skeleton, area.skills) == ("area", 2)
    assert area.mean_dpr == pytest.approx(15.0)  # (10 + 20) / 2
    assert area.mean_uses_per_round == pytest.approx((2 / 4 + 4 / 4) / 2)


def test_random_cases_are_reproducible_and_demo_cases_cover_the_library() -> None:
    lib = library()
    first = [c.skill.id for c in random_cases(lib, 4)]
    assert first == [c.skill.id for c in random_cases(lib, 4)]
    assert [c.seed for c in random_cases(lib, 3, 10)] == [10, 11, 12]
    assert len(demo_cases(lib)) == len(lib.skills)


def test_a_real_small_skill_report_is_deterministic_and_independent_of_jobs() -> None:
    lib = library()
    cases = demo_cases(lib)[:2] + random_cases(lib, 2)
    first = run_skill_report(lib, cases, [0, 1], jobs=1)
    parallel = run_skill_report(lib, cases, [0, 1], jobs=2)
    assert first == parallel
    assert format_skill_report(first) == format_skill_report(parallel)
    assert {r.source for r in first.rows} == {"demo", "random"}
    assert all(r.completed == 2 for r in first.rows)


def test_skills_cli_runs_with_demo_and_random(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sim", "skills", "--random", "2", "--seeds", "1"]) == 0
    captured = capsys.readouterr()
    assert "技能報表：2 個技能" in captured.out and "執行時間" in captured.err
    assert main(["sim", "skills", "--demo", "--random", "1", "--seeds", "1", "--jobs", "2"]) == 0
    assert f"技能報表：{len(library().skills) + 1} 個技能" in capsys.readouterr().out
