"""隨機技能的執行驗收（Phase 2B-3 5.2、5.3；驗收 2–4）。"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

import pytest

from tests.skillgen.helpers import lib, skill
from trpg.content.skills import SkillDef
from trpg.sim import skill_fuzz
from trpg.sim.skill_fuzz import FuzzReport, check_skill, format_report, run_fuzz

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "skill_fuzz.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("skill_fuzz_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _battle_only(skill: SkillDef) -> bool:
    """沒有合法選取可施放的技能：被動、反應技、不需啟動的修正技能（3C-6b）。"""
    return skill.kind in ("passive", "reaction") or (
        skill.kind == "modifier" and skill.activation is None
    )


def test_one_hundred_seeds_pass_validation_cast_and_run_without_exceptions() -> None:
    report = run_fuzz(lib(), count=100)
    assert report.compose_errors == []
    assert len(report.outcomes) == 100
    assert all(o.violations == 0 for o in report.outcomes)
    assert all(o.castable for o in report.outcomes)
    assert all(o.error is None for o in report.outcomes)
    # 每 10 個挑 1 個打一場；被動（2E-1）、反應技（2E-2）與陷阱（2E-3）每個都打一場
    expected = {
        o.seed
        for o in report.outcomes
        if o.seed % 10 == 0
        or o.skill.kind in ("passive", "reaction")
        or o.skill.skeleton == "trap"
        or (o.skill.kind == "modifier" and o.skill.activation is None)  # 3C-6b：修正技能
    }
    assert {o.seed for o in report.outcomes if o.battle_ran} == expected
    passives = [o for o in report.outcomes if o.skill.kind == "passive"]
    assert passives and sum(o.triggers for o in passives) > 0
    assert all(
        o.triggers == 0
        for o in report.outcomes
        if not _battle_only(o.skill) and o.skill.skeleton != "trap"
    )
    battle_only = {o.seed for o in report.outcomes if _battle_only(o.skill)}
    assert all(o.selections >= 1 for o in report.outcomes if o.seed not in battle_only)


def test_the_summary_is_identical_between_two_runs_and_lists_the_distributions() -> None:
    first = format_report(run_fuzz(lib(), count=30, seed_start=5))
    second = format_report(run_fuzz(lib(), count=30, seed_start=5))
    assert first == second
    for text in (
        "種子 5–34，共 30 個",
        "可施放 30/30",
        "例外 0 個",
        "平均重抽次數",
        "骨架：",
        "稀有度：",
        "階級：",
        "形狀：",
        "預算比例分佈",
    ):
        assert text in first
    assert first.count("%  ") >= 10  # 10 個區間


def test_an_exception_in_resolve_is_collected_with_the_seed_and_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("壞掉了")

    monkeypatch.setattr(skill_fuzz, "resolve", boom)
    report = run_fuzz(lib(), count=3)
    assert all(o.error is not None and "RuntimeError: 壞掉了" in o.error for o in report.outcomes)
    text = format_report(report)
    assert "例外 3 個" in text and "問題：種子 0：" in text and "id: skill_rand_0" in text


def test_a_skill_that_never_becomes_legal_is_reported_as_not_castable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(skill_fuzz, "_DISTANCES", (1,))
    cond = skill(condition={"type": "height_advantage"})
    monkeypatch.setattr(skill_fuzz, "_prepare", lambda *_: None)  # 不布置場面：條件不成立
    outcome = check_skill(lib(), 1, with_battle=False, attempts=1, skill=cond)
    assert not outcome.castable and outcome.error is None


def test_conditions_are_prepared_so_conditional_skills_can_be_cast() -> None:
    cond = skill(condition={"type": "height_advantage"})
    outcome = check_skill(lib(), 1, with_battle=True, attempts=1, skill=cond)
    assert outcome.castable and outcome.error is None and outcome.battle_ran


def test_the_script_prints_the_summary_and_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script()
    assert module.main(["--count", "12"]) == 0
    captured = capsys.readouterr()
    assert "隨機技能驗收：種子 0–11，共 12 個" in captured.out
    assert "執行時間" in captured.err and "執行時間" not in captured.out


def test_the_script_can_show_one_battle(capsys: pytest.CaptureFixture[str]) -> None:
    module = _load_script()
    assert module.main(["--show-battle", "10"]) == 0
    out = capsys.readouterr().out
    assert "id: skill_rand_10" in out and "=== 第 1 輪 ===" in out and "勝方：" in out


@pytest.mark.slow
def test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible() -> None:
    report = run_fuzz(lib(), count=1000)
    assert report.compose_errors == []
    assert all(o.violations == 0 and o.castable and o.error is None for o in report.outcomes)
    skills = [o.skill for o in report.outcomes]
    counts = Counter(s.skeleton for s in skills)
    enabled = {s.id for s in lib().skeletons.values() if s.enabled}
    assert set(counts) == enabled and max(counts.values()) <= 400  # 2E-3：11 種骨架都抽得到
    assert counts["builder_finisher"] > 0 and counts["trap"] > 0
    assert {s.tier for s in skills} == {1, 2, 3, 4, 5}
    assert len({s.rarity for s in skills}) == 4
    assert format_report(report) == format_report(run_fuzz(lib(), count=1000))


def test_a_passive_is_fought_and_its_triggers_are_counted() -> None:
    library = lib()
    ember = library.skills["skill_second_wind"]
    # 3D-8d：朝向與背刺改變了 AI 的走位，種子 3 的戰鬥裡回氣不再觸發；改用會觸發的種子 2
    outcome = check_skill(library, 2, with_battle=False, attempts=1, skill=ember)
    assert outcome.error is None and outcome.castable and outcome.battle_ran
    assert outcome.triggers > 0
    text = format_report(FuzzReport(2, outcomes=[outcome], primitive_ids=(), status_ids=()))
    assert "被動 1 個" in text and "實際觸發過 1 個" in text
