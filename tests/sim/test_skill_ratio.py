"""NW-2c：比值核心 ``trpg.sim.skill_ratio``（從 ``scripts/t1_skill_ratio.py`` 搬來）。

搬家前後腳本輸出逐字相同的證據在 ``docs/phases/PhaseNW-2c報告.md``（T-C1，實跑一次比 SHA-256）；
這裡只測核心的確定性、情境數與參考線判定（T-C2 的一部分）。
"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.sim.skill_ratio import (
    REFERENCE_LINES,
    RatioJob,
    conditions_of,
    is_measurable,
    measure,
    meta_of,
    range_text,
    ratio_jobs,
    reference_checks,
    scenario_count,
    scenarios_for,
    skill_summary,
    tier1_skills,
    tier1_weapon_skills,
)


@pytest.fixture(scope="module")
def lib() -> ContentLibrary:
    return load_library()


def test_measuring_twice_gives_the_same_row(lib: ContentLibrary) -> None:
    job = RatioJob("bow", "skill_fire_arrow", 2)
    first = measure(lib, job)
    again = measure(lib, job, root="另一個鍵")  # 普攻快取的鍵不同：重算一次也相同
    assert first == again
    assert set(first) == {"weapon", "class", "skill", "basic", "alloc", "scenarios"}
    assert first["scenarios"]["base"]["castable"] is True
    assert first["scenarios"]["base"]["ratio"] > 0


def test_scenario_count_matches_the_scenarios(lib: ContentLibrary) -> None:
    for skill in tier1_weapon_skills(lib):
        wc = str(skill.weapon_req)
        if wc not in ("melee", "ranged"):
            continue
        assert scenario_count(skill) == len(scenarios_for(lib, skill, wc)), skill.id


def test_only_tier1_active_weapon_skills_are_measurable(lib: ContentLibrary) -> None:
    measurable = {s.id for s in lib.skills.values() if is_measurable(s)}
    assert measurable == {s.id for s in tier1_weapon_skills(lib)}
    assert "skill_fire_arrow" in measurable
    assert all(not lib.skills[s].enemy_only for s in measurable)


def test_jobs_are_skill_major_weapon_minor(lib: ContentLibrary) -> None:
    skills = [lib.skills["skill_fire_arrow"], lib.skills["skill_pinpoint_shot"]]
    jobs = ratio_jobs(lib, skills, 3)
    assert [j.skill for j in jobs] == sorted(j.skill for j in jobs)
    assert {j.seeds for j in jobs} == {3}
    only_bow = ratio_jobs(lib, skills, 3, {"bow"})
    assert [(j.weapon, j.skill) for j in only_bow] == [
        ("bow", "skill_fire_arrow"),
        ("bow", "skill_pinpoint_shot"),
    ]


def _row(weapon: str, scenarios: dict[str, float]) -> dict[str, Any]:
    return {
        "weapon": weapon,
        "scenarios": {
            k: {"castable": True, "ratio": v, "ratio_tot": v} for k, v in scenarios.items()
        },
    }


def _meta(**over: Any) -> dict[str, Any]:
    base = {
        "class": "melee",
        "ap": 2,
        "shape": "single",
        "conds": [],
        "variants": [],
        "bound": [],
        "damaging": True,
        "summon": False,
    }
    return base | over


def test_unconditional_line_uses_the_best_weapon() -> None:
    meta = _meta()
    summary = skill_summary(meta, [_row("sword", {"base": 0.85}), _row("axe", {"base": 0.89})])
    [(line, value)] = reference_checks(meta, summary)
    assert line is REFERENCE_LINES["plain"]
    assert value == pytest.approx(0.89)
    assert value is not None and value < line.threshold  # 0.89 → 低於 0.9
    assert not line.tentative


def test_conditional_lines_on_and_off() -> None:
    meta = _meta(conds=["target_has_status:marked"])
    summary = skill_summary(meta, [_row("sword", {"off": 0.55, "on": 1.12})])
    checks = {line.key: value for line, value in reference_checks(meta, summary)}
    on, off = checks["on"], checks["off"]
    assert on == pytest.approx(1.12)
    assert on is not None and on >= REFERENCE_LINES["on"].threshold  # 1.12 → 達標
    assert off == pytest.approx(0.55)
    assert off is not None and off < REFERENCE_LINES["off"].threshold
    assert REFERENCE_LINES["off"].tentative


def test_variants_count_as_conditions_met() -> None:
    meta = _meta(variants=["frost"])
    summary = skill_summary(meta, [_row("sword", {"base": 0.7, "var:frost": 1.3})])
    checks = dict((line.key, value) for line, value in reference_checks(meta, summary))
    assert checks == {"on": pytest.approx(1.3), "off": pytest.approx(0.7)}


def test_one_ap_arrows_use_the_tentative_line() -> None:
    meta = _meta(**{"class": "ranged", "ap": 1})
    summary = skill_summary(meta, [_row("bow", {"base": 0.65})])
    [(line, value)] = reference_checks(meta, summary)
    assert line is REFERENCE_LINES["arrow"]
    assert line.tentative
    assert value is not None and value >= line.threshold


@pytest.mark.parametrize(
    "over", [{"summon": True}, {"damaging": False}, {"shape": "cone"}], ids=str
)
def test_no_line_for_summons_non_damage_and_area(over: dict[str, Any]) -> None:
    meta = _meta(**over)
    summary = skill_summary(meta, [_row("sword", {"base": 0.4})])
    assert reference_checks(meta, summary) == []


def test_range_text() -> None:
    assert range_text([]) == "—"
    assert range_text([0.744, 0.781]) == "0.74～0.78"
    assert range_text([0.5, 0.501]) == "0.50"


# ---------------------------------------------------------------------------
# SR-1：1 階法器法術（category: spell、weapon_req: focus）
# ---------------------------------------------------------------------------


def test_spell_category_is_tier1_active_focus_spells(lib: ContentLibrary) -> None:
    spells = tier1_skills(lib, "spell")
    assert spells, "沒有 1 階法器法術"
    for s in spells:
        assert (s.tier, s.kind, s.category, s.weapon_req) == (1, "active", "spell", "focus")
        assert not s.enemy_only
    ids = {s.id for s in spells}
    assert ids == {s.id for s in lib.skills.values() if is_measurable(s, "spell")}
    assert not ids & {s.id for s in tier1_weapon_skills(lib)}
    # 工坊用的預設（不帶類別）照舊只量武器技
    assert "skill_fire_bolt" in ids
    assert not is_measurable(lib.skills["skill_fire_bolt"])


def test_spell_jobs_use_the_focus_weapons(lib: ContentLibrary) -> None:
    jobs = ratio_jobs(lib, [lib.skills["skill_fire_bolt"]], 2)
    focus = sorted(
        w
        for w, d in lib.weapons.items()
        if d.weapon_class == "focus" and not d.enemy_only and not d.summon_only
    )
    assert focus
    assert [j.weapon for j in jobs] == focus
    for skill in tier1_skills(lib, "spell"):
        assert scenario_count(skill) == len(scenarios_for(lib, skill, "focus")), skill.id


def test_a_spell_is_measured_against_the_focus_basic_attack(lib: ContentLibrary) -> None:
    row = measure(lib, RatioJob("fire_staff", "skill_fire_bolt", 2))
    assert row["class"] == "focus"
    assert row["basic"]["ap"] > 0 and row["basic"]["imm"] > 0
    base = row["scenarios"]["base"]
    assert base["castable"] is True
    assert base["ratio"] > 0
    assert base["ratio_tot"] >= base["ratio"]  # 燃燒的後續傷害
    assert measure(lib, RatioJob("fire_staff", "skill_fire_bolt", 2), root="另一個鍵") == row


@pytest.mark.parametrize(
    ("skill", "cond"),
    [
        ("skill_arc_follow_up", "cast_tag_this_turn:lightning"),
        ("skill_rune_thunderbolt", "on_own_rune:lightning"),
    ],
)
def test_spell_only_conditions_can_be_made_to_hold(
    lib: ContentLibrary, skill: str, cond: str
) -> None:
    assert conditions_of(lib.skills[skill]) == [cond]
    row = measure(lib, RatioJob("lightning_staff", skill, 2))
    off, on = row["scenarios"]["off"], row["scenarios"]["on"]
    assert (off["met"], on["met"]) == (0, 2)  # 施放前用引擎的 condition_met 檢查
    assert on["ratio"] > off["ratio"]


def test_meta_has_the_fields_the_summary_needs(lib: ContentLibrary) -> None:
    meta = meta_of(lib, lib.skills["skill_pinpoint_shot"])
    assert meta["conds"] == ["target_has_status:marked"]
    assert meta["class"] == "ranged"
    assert "bow" in meta["weapons"]
