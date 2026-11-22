"""GS-3（#173，06 6.30「形態池名單」最後一點）：改 4 招、補 4 招高階化身。

- 補的 4 招（熊王怒吼、影貓潛襲、巨人踐地、龍威降臨）：姿態、法術、不限武器、帶進入時效果、冷卻 3；
- 改的 4 招：化形守護看最大 HP、野性連擊用天生武器屬性、化形震地與原形歸一改成實心環形 2；
- 8 招都在形態池、預算 70～100%、不是起始技能。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import U1, U2, U3, of
from tests.engine.test_form_pools import BEAR, arena, into_bear, use
from tests.engine.test_passive_triggers import always
from trpg.engine import UseSkill
from trpg.engine.events import DamageDealt, FormEntered, ShieldGained, StatusApplied, UnitMoved
from trpg.engine.preview import preview
from trpg.engine.skills.scaling import skill_scaling_value
from trpg.roguelite.start import starter_pools
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.keywords import is_starter_skill, keyword_pools

BEAR_KING = "skill_form_bear_king"
SHADOW_CAT = "skill_form_shadow_cat"
GIANT_STOMP = "skill_form_giant_stomp"
DRAGON_DREAD = "skill_form_dragon_dread"
FLURRY = "skill_form_wild_flurry"
QUAKE = "skill_form_quake"
PRIMAL = "skill_form_primal_return"
GUARDIAN = "skill_form_guardian"

# 06 6.30 最後一點：名字、階級、稀有度、形態
NEW = {
    BEAR_KING: ("熊王怒吼", 3, "epic", "bear"),
    SHADOW_CAT: ("影貓潛襲", 3, "rare", "cat"),
    GIANT_STOMP: ("巨人踐地", 4, "rare", "giant"),
    DRAGON_DREAD: ("龍威降臨", 4, "epic", "dragon"),
}
ALL = (*NEW, FLURRY, QUAKE, PRIMAL, GUARDIAN)


@pytest.mark.parametrize("skill_id", sorted(NEW))
def test_each_new_avatar_is_a_stance_spell_with_an_entry_effect_and_cooldown(
    skill_id: str,
) -> None:
    lib = library()
    skill = lib.ruleset.skill_def(skill_id)
    name, tier, rarity, form = NEW[skill_id]
    assert (skill.name_zh, skill.tier, skill.rarity, skill.form_id) == (name, tier, rarity, form)
    assert skill.kind == "stance" and skill.category == "spell" and skill.weapon_req == "any"
    assert skill.form_entry_effect is not None
    assert skill.form_entry_effect.type in ("apply_status", "push")
    assert skill.cost.cooldown == 3
    assert skill.cost.cooldown >= lib.ruleset.core.skill_limits.min_form_entry_cooldown
    assert skill.narrative.concept and skill.narrative.cast_flavor


@pytest.mark.parametrize("skill_id", sorted(ALL))
def test_each_of_the_eight_fits_the_budget_band(skill_id: str) -> None:
    report = skill_budget(library().ruleset.skill_def(skill_id), library())
    assert report.ok, f"{skill_id} {float(report.ratio):.1%}"


def test_all_eight_are_in_the_form_pool_but_never_starters() -> None:
    lib = library()
    exclusive = keyword_pools(lib, exclusive_only=True)["form"]
    assert set(ALL) <= set(exclusive)
    assert not any(is_starter_skill(lib.skills[s]) for s in ALL)
    assert not set(ALL) & set(starter_pools(lib)["form"])


def test_the_bear_king_weakens_adjacent_foes_after_turning_into_a_bear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    state = arena([BEAR_KING], foes=((4, 3), (5, 3)))
    state.units[U1].attributes = {k: 400 for k in state.units[U1].attributes}  # 對抗穩贏
    result = use(state, BEAR_KING)
    assert [e.form_id for e in of(result, FormEntered)] == ["bear"]  # type: ignore[arg-type]
    weak = [e.target_id for e in of(result, StatusApplied) if e.status_id == "weaken"]  # type: ignore[arg-type]
    assert weak == [U2]  # 周圍 1 格：(5, 3) 在 2 格外


def test_the_dragon_dread_frightens_everyone_within_two_tiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    state = arena([DRAGON_DREAD], foes=((4, 3), (5, 5)))
    state.units[U1].attributes = {k: 400 for k in state.units[U1].attributes}
    result = use(state, DRAGON_DREAD)
    feared = {e.target_id for e in of(result, StatusApplied) if e.status_id == "feared"}  # type: ignore[arg-type]
    assert feared == {U2, U3}


def test_the_giant_stomp_pushes_the_adjacent_foe_one_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    state = arena([GIANT_STOMP], foes=((4, 3),))
    state.units[U1].attributes = {k: 400 for k in state.units[U1].attributes}
    result = use(state, GIANT_STOMP)
    assert any(e.unit_id == U2 for e in of(result, UnitMoved))  # type: ignore[arg-type]
    assert result.state.units[U2].xy == (5, 3)  # type: ignore[attr-defined]


def test_the_shadow_cat_conceals_itself() -> None:
    result = use(arena([SHADOW_CAT]), SHADOW_CAT)
    applied = [e.target_id for e in of(result, StatusApplied) if e.status_id == "concealed"]  # type: ignore[arg-type]
    assert applied == [U1]
    assert result.state.units[U1].form.form_id == "cat"  # type: ignore[attr-defined]


def test_the_guardian_shield_is_the_bear_max_hp_times_permille() -> None:
    state = into_bear(arena([GUARDIAN, BEAR]))
    permille = library().ruleset.skill_def(GUARDIAN).effects[0].max_hp_permille
    assert permille == 150
    result = use(state, GUARDIAN)
    mine = [e for e in of(result, ShieldGained) if e.unit_id == U1]  # type: ignore[arg-type]
    assert [e.amount for e in mine] == [state.units[U1].max_hp * permille // 1000]
    assert mine[0].rolls == ()


def test_the_quake_now_hits_the_adjacent_foe_too(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    result = use(arena([QUAKE, BEAR], foes=((5, 3), (4, 3))), QUAKE)
    assert {h.target_id for h in of(result, DamageDealt)} == {U2, U3}  # type: ignore[arg-type]


def test_primal_return_hits_the_adjacent_foe_too(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    result = use(into_bear(arena([PRIMAL, BEAR], foes=((5, 3), (4, 3)))), PRIMAL)
    assert {h.target_id for h in of(result, DamageDealt)} == {U2, U3}  # type: ignore[arg-type]


def test_the_flurry_reads_the_bear_claws_higher_attribute() -> None:
    state = into_bear(arena([FLURRY, BEAR]))
    unit = state.units[U1]
    skill = library().ruleset.skill_def(FLURRY)
    for key in list(unit.attributes):
        name = str(getattr(key, "value", key))
        unit.attributes[key] = {"str": 30, "con": 120}.get(name, unit.attributes[key])
    assert skill_scaling_value(library().ruleset, unit, skill) == 120  # 熊爪：力量／體質取較高


@pytest.mark.parametrize(("skill_id", "radius"), [(QUAKE, 2), (DRAGON_DREAD, 2), (BEAR_KING, 1)])
def test_the_range_preview_highlights_the_solid_ring(skill_id: str, radius: int) -> None:
    """前端的範圍預覽畫伺服器給的 ``affected_tiles``（``useHighlights.ts``）：實心環形是距離
    1～N 的每一格（地圖 7×7、施放者在 (3, 3)）。化身技另外標出施放者自己（變身作用在自己身上）。"""
    state = arena([skill_id, BEAR])
    skill = library().ruleset.skill_def(skill_id)
    if skill.condition is not None:
        state = into_bear(state)
    tiles = set(preview(state, UseSkill(unit_id=U1, skill_id=skill_id)).affected_tiles)
    ring = {
        (x, y) for x in range(7) for y in range(7) if 1 <= max(abs(x - 3), abs(y - 3)) <= radius
    }
    assert tiles - {(3, 3)} == ring
    assert ((3, 3) in tiles) == (skill.form_id is not None)
