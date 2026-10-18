"""Phase 2B-1 3.2–3.4：抵抗判定、控制遞減、Boss 硬控轉換，以及預覽（驗收 3–6）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    library,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of, script_rolls
from trpg.content.environment import SurfaceTable
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, preview, start_battle
from trpg.engine.control import control_dr_active, plan_status
from trpg.engine.effects import ApplyStatusEffect, run_effects
from trpg.engine.events import (
    StatusApplied,
    StatusConverted,
    StatusResisted,
    StatusSaveRolled,
    SurfaceEntered,
)
from trpg.engine.preview import StatusChance
from trpg.engine.rules.combat import is_hit
from trpg.shared.types import Attribute, Team, UnitId

SINGLE = {"type": "single", "range": 5}
HIT, FAIL, WIN = 19, 3, 19  # 命中骰、讓抵抗成功的骰（攻方失敗）、讓抵抗失敗的骰


def _status_skill(status: str, *, duration: int | None = None) -> SkillDef:
    effect: dict[str, object] = {"type": "apply_status", "status": status}
    if duration is not None:
        effect["duration"] = duration
    return make_skill(SID, SINGLE, [effect])


def _foe_state(status: str = "root", **kw: object) -> BattleState:
    """施放者 U1（法師，智力 16）在 (3, 3)，盜賊 U2 在 (5, 3)。"""
    return battle(_status_skill(status, **kw), [(5, 3)])  # type: ignore[arg-type]


def _action(**fields: object) -> dict[str, object]:
    return {"target_id": U2, **fields}


def _chance(state: BattleState, status: str, *, attack_attr: Attribute, defense: int) -> Fraction:
    rules = library().ruleset
    modifier = rules.hit_table.modifier(state.units[U1].attributes[attack_attr], defense)
    bonus = modifier + rules.core.proficiency
    return Fraction(sum(1 for n in range(1, 21) if is_hit(n, n + bonus, rules.core.hit_target)), 20)


# ---------------------------------------------------------------------------
# 3.2 抵抗判定
# ---------------------------------------------------------------------------


def test_a_failed_save_applies_the_status(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _foe_state()
    script_rolls(monkeypatch, [HIT, WIN])
    result = cast(state, target_id=U2)
    (save,) = of(result, StatusSaveRolled)
    assert (save.status_id, save.attack_attr, save.save_attr) == (
        "root",
        Attribute.INT,
        Attribute.STR,
    )
    assert (save.attack_value, save.defense_value, save.diminished) == (16, 12, False)
    assert save.applied and save.natural == WIN
    assert not of(result, StatusResisted)
    assert [e.status_id for e in of(result, StatusApplied)] == ["root"]
    assert result.state.units[U2].has_status("root")


def test_a_successful_save_resists_the_status(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _foe_state()
    script_rolls(monkeypatch, [HIT, FAIL])
    result = cast(state, target_id=U2)
    (save,) = of(result, StatusSaveRolled)
    assert not save.applied and save.natural == FAIL
    assert [(e.target_id, e.status_id) for e in of(result, StatusResisted)] == [(U2, "root")]
    assert not of(result, StatusApplied)
    assert not result.state.units[U2].has_status("root")
    assert result.state.units[U2].control_dr == {}  # 被抵抗不記錄遞減


def test_the_save_uses_the_ratio_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _foe_state()
    script_rolls(monkeypatch, [HIT, 10])
    (save,) = of(cast(state, target_id=U2), StatusSaveRolled)
    rules = library().ruleset
    assert save.modifier == rules.hit_table.modifier(16, 12)
    assert save.total == 10 + save.modifier + rules.core.proficiency
    assert save.applied == (save.total >= rules.core.hit_target)


def test_the_status_needs_a_hit_before_the_save(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _foe_state()
    script_rolls(monkeypatch, [2])  # 命中骰失手：不會再擲抵抗（骰值用完會讓測試失敗）
    result = cast(state, target_id=U2)
    assert not of(result, StatusSaveRolled) and not of(result, StatusApplied)


def test_statuses_without_save_attr_apply_on_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(_status_skill("bleed"), [(5, 3)])
    script_rolls(monkeypatch, [HIT])
    result = cast(state, target_id=U2)
    assert not of(result, StatusSaveRolled)
    assert result.state.units[U2].has_status("bleed")


def test_no_save_is_rolled_against_allies_or_self() -> None:
    skill = make_skill(
        SID,
        {"type": "allies_in_radius", "radius": 2},
        [{"type": "apply_status", "status": "root", "affects": "allies"}],
    )
    state = battle(skill, allies=[(4, 3)])
    result = cast(state)
    assert not of(result, StatusSaveRolled)
    ally = UnitId("unit_0002")
    assert result.state.units[U1].has_status("root")
    assert result.state.units[ally].has_status("root")
    assert result.state.units[ally].control_dr  # 友方也記錄遞減（成功施加）


def test_statuses_from_surfaces_are_applied_without_a_save() -> None:
    """表面造成的狀態維持現有規則：把火焰表面的進入效果改成定身，進入時不擲抵抗。"""
    lib = library()
    data = lib.ruleset.surfaces.model_dump(mode="json")
    for surface in data["surfaces"]:
        if surface["id"] == "fire":
            surface["on_enter"]["apply_status"] = "root"
    m = make_map("000\n000\n000", ally=[(0, 0)], enemy=[(2, 2)], surfaces=[(1, 1, "fire")])
    setup = make_setup(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 2))])
    ruleset = setup.ruleset.model_copy(update={"surfaces": SurfaceTable.model_validate(data)})
    ruleset.model_post_init(None)
    state = start_battle(setup.model_copy(update={"ruleset": ruleset}), 0)
    from trpg.engine.effects import MoveUnitEffect  # noqa: PLC0415

    result = run_effects(
        state,
        [MoveUnitEffect(unit_id="unit_0001", dest=(1, 1), mode="forced")],  # type: ignore[arg-type]
    )
    assert of(result, SurfaceEntered)
    assert not of(result, StatusSaveRolled)
    assert result.state.units[U1].has_status("root")


# ---------------------------------------------------------------------------
# 3.3 控制遞減
# ---------------------------------------------------------------------------


def test_the_second_root_inside_the_window_uses_150_percent_defense(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _foe_state()
    script_rolls(monkeypatch, [HIT, WIN, HIT, WIN])
    first = cast(state, target_id=U2)
    (a,) = of(first, StatusSaveRolled)
    unit = first.state.units[U2]
    assert unit.control_dr == {"movement": state.round + 2}  # 第 R + 2 輪結束
    second = cast(first.state, target_id=U2)
    (b,) = of(second, StatusSaveRolled)
    rules = library().ruleset
    assert (a.defense_value, a.diminished) == (12, False)
    assert (b.defense_value, b.diminished) == (18, True)  # 12 × 1500‰
    assert a.modifier == rules.hit_table.modifier(16, 12)
    assert b.modifier == rules.hit_table.modifier(16, 18)
    assert b.modifier < a.modifier


def test_the_window_covers_round_r_plus_2_and_then_recovers() -> None:
    state = _foe_state()
    unit = state.units[U2]
    unit.control_dr = {"movement": 3}
    for round_no, expected in ((1, True), (3, True), (4, False)):
        state.round = round_no
        assert control_dr_active(state, unit, "movement") is expected
        plan = plan_status(state, unit, "root")
        assert (plan.diminished, plan.defense_value) == (expected, 18 if expected else 12)


def test_control_groups_do_not_affect_each_other() -> None:
    state = _foe_state()
    unit = state.units[U2]
    unit.control_dr = {"movement": 3}
    assert plan_status(state, unit, "slow").diminished  # 同為 movement
    assert plan_status(state, unit, "root").diminished
    assert not plan_status(state, unit, "stun").diminished  # hard 不受影響
    assert not plan_status(state, unit, "weaken").diminished  # 沒有類別
    unit.control_dr = {"hard": 3}
    assert plan_status(state, unit, "stun").diminished
    assert not plan_status(state, unit, "root").diminished


def test_a_status_application_records_the_diminishing_window_for_its_group() -> None:
    state = _foe_state()
    state.round = 2
    result = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="stun")])
    assert result.state.units[U2].control_dr == {"hard": 4}
    assert result.state.units[U2].has_status("stun")


# ---------------------------------------------------------------------------
# 3.4 Boss 硬控轉換
# ---------------------------------------------------------------------------


def _boss_state(skill_status: str = "stun", **kw: object) -> BattleState:
    boss = no_reactions("bandit_boss")
    return battle(_status_skill(skill_status, **kw), [(5, 3, boss)])  # type: ignore[arg-type]


def test_stun_on_a_boss_becomes_slow(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _boss_state()
    script_rolls(monkeypatch, [HIT, WIN])
    result = cast(state, target_id=U2)
    (conv,) = of(result, StatusConverted)
    assert (conv.target_id, conv.from_status, conv.to_status) == (U2, "stun", "slow")
    (save,) = of(result, StatusSaveRolled)
    assert (save.status_id, save.save_attr) == ("slow", Attribute.DEX)  # 轉換後仍走抵抗判定
    (applied,) = of(result, StatusApplied)
    assert (applied.status_id, applied.duration) == (
        "slow",
        1,
    )  # 持續時間沿用原效果（暈眩的 1 回合）
    boss = result.state.units[U2]
    assert boss.has_status("slow") and not boss.has_status("stun")
    assert boss.control_dr == {"movement": state.round + 2}  # 轉換後的狀態走自己的遞減類別


def test_a_converted_status_keeps_an_explicit_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _boss_state(duration=2)
    script_rolls(monkeypatch, [HIT, WIN])
    (applied,) = of(cast(state, target_id=U2), StatusApplied)
    assert (applied.status_id, applied.duration) == ("slow", 2)


def test_a_converted_status_can_still_be_resisted(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _boss_state()
    script_rolls(monkeypatch, [HIT, FAIL])
    result = cast(state, target_id=U2)
    assert of(result, StatusConverted)
    assert of(result, StatusResisted)
    assert not result.state.units[U2].statuses


def test_a_boss_is_not_converted_for_other_control_or_for_non_bosses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boss_root, plain_stun = _boss_state("root"), _foe_state("stun")
    script_rolls(monkeypatch, [HIT, WIN])
    root = cast(boss_root, target_id=U2)
    assert not of(root, StatusConverted) and root.state.units[U2].has_status("root")
    script_rolls(monkeypatch, [HIT, WIN])
    plain = cast(plain_stun, target_id=U2)
    assert not of(plain, StatusConverted) and plain.state.units[U2].has_status("stun")


def test_the_demo_boss_carries_the_boss_tag_and_the_shield_bash_stuns() -> None:
    """內容層：盜賊頭目帶 boss 標籤（會被轉換）；盾擊施加暈眩且冷卻 ≥ 4。"""
    lib = library()
    assert "boss" in lib.unit("bandit_boss").tags
    bash = lib.ruleset.skill_def("skill_shield_bash")
    assert [e.status for e in bash.effects if e.type == "apply_status"] == ["stun"]
    assert (bash.cost.cooldown or 0) >= 4


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def _preview_action() -> UseSkill:
    return UseSkill(unit_id=U1, skill_id=SID, target_id=U2)


def test_preview_reports_the_resist_chance() -> None:
    state = _foe_state()
    (target,) = preview(state, _preview_action()).targets
    expected = _chance(state, "root", attack_attr=Attribute.INT, defense=12)
    assert target.status_chances == (StatusChance("root", "root", expected),)
    (chance,) = target.status_chances
    assert chance.apply_chance == expected and chance.resist_chance == 1 - expected
    assert 0 < chance.resist_chance < 1


def test_preview_includes_the_diminishing_penalty() -> None:
    state = _foe_state()
    plain = preview(state, _preview_action()).targets[0].status_chances[0]
    state.units[U2].control_dr = {"movement": 3}
    diminished = preview(state, _preview_action()).targets[0].status_chances[0]
    assert diminished.diminished and not plain.diminished
    assert diminished.apply_chance == _chance(state, "root", attack_attr=Attribute.INT, defense=18)
    assert diminished.apply_chance < plain.apply_chance


def test_preview_reports_the_converted_status_for_a_boss() -> None:
    state = _boss_state()
    (chance,) = preview(state, _preview_action()).targets[0].status_chances
    assert (chance.status_id, chance.original_id) == ("slow", "stun")
    boss = state.units[U2]
    assert chance.apply_chance == _chance(
        state, "slow", attack_attr=Attribute.INT, defense=boss.attributes[Attribute.DEX]
    )


def test_preview_omits_statuses_without_a_save() -> None:
    state = battle(_status_skill("bleed"), [(5, 3)])
    assert preview(state, _preview_action()).targets[0].status_chances == ()


@pytest.mark.parametrize(("save_roll", "applied"), [(FAIL, False), (WIN, True)])
def test_preview_matches_the_resolution_with_fixed_rolls(
    monkeypatch: pytest.MonkeyPatch, save_roll: int, applied: bool
) -> None:
    """min 視為抵抗成功、max 視為失敗；固定骰值時實際結算與其中一側一致。"""
    state = _foe_state()
    p = preview(state, _preview_action())
    assert not p.min_state.units[U2].has_status("root")
    assert p.max_state.units[U2].has_status("root")
    assert ("status", U2, "root") in {(o.kind, o.unit_id, o.detail) for o in p.possible}
    script_rolls(monkeypatch, [HIT, save_roll])
    result = cast(state, target_id=U2)
    side = p.max_state if applied else p.min_state
    assert result.state.units[U2].statuses == side.units[U2].statuses
    assert result.state.units[U2].control_dr == side.units[U2].control_dr
