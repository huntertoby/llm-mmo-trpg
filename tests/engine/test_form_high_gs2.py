"""GS-2（#172）：高階形態技（06 6.30「形態池名單」最後一點，``docs/形態補招提案.md``）。

- 做出來的 4 招高階利用者：名字、階級、稀有度、預算 70～100%、在形態池裡、不是起始技能；
- 三選一指定「形態」時，3 階、4 階都有招可以出（含史詩）；
- 「只能在形態中施放」與「在形態中才倒地」照實戰。

4 招高階化身（熊王怒吼、影貓潛襲、巨人踐地、龍威降臨）與 4 招的改動（實心環形、看最大 HP 的護盾、
天生武器屬性）在 GS-3（#173）補上，見 ``tests/engine/test_form_high_gs3.py``。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import U1, U2, U3, of
from tests.engine.test_form_pools import BEAR, arena, into_bear, use
from tests.engine.test_passive_triggers import always
from trpg.engine import UseSkill, resolve
from trpg.engine.events import DamageDealt, FormLeft, ShieldGained, StatusApplied
from trpg.roguelite.start import starter_pools
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.candidates import CandidateRequest, generate_candidates, skill_has_keywords
from trpg.skillgen.keywords import is_starter_skill, keyword_pools

FLURRY = "skill_form_wild_flurry"
QUAKE = "skill_form_quake"
PRIMAL = "skill_form_primal_return"
GUARDIAN = "skill_form_guardian"

# 06 6.30 最後一點（#172）：名字、階級、稀有度
HIGH = {
    FLURRY: ("野性連擊", 3, "rare"),
    QUAKE: ("化形震地", 3, "epic"),
    PRIMAL: ("原形歸一", 4, "epic"),
    GUARDIAN: ("化形守護", 4, "epic"),
}


@pytest.mark.parametrize("skill_id", sorted(HIGH))
def test_each_high_form_skill_has_the_listed_name_tier_and_rarity(skill_id: str) -> None:
    skill = library().ruleset.skill_def(skill_id)
    assert (skill.name_zh, skill.tier, skill.rarity) == HIGH[skill_id]
    assert skill.kind == "active" and skill.category == "spell" and skill.weapon_req == "any"
    assert skill.narrative.concept and skill.narrative.cast_flavor


@pytest.mark.parametrize("skill_id", sorted(HIGH))
def test_each_high_form_skill_fits_the_budget_band(skill_id: str) -> None:
    report = skill_budget(library().ruleset.skill_def(skill_id), library())
    assert report.ok, f"{skill_id} {float(report.ratio):.1%}"


def test_the_high_form_skills_are_in_the_form_pool_but_never_starters() -> None:
    lib = library()
    exclusive = keyword_pools(lib, exclusive_only=True)["form"]
    assert set(HIGH) <= set(exclusive)
    for skill_id in HIGH:
        assert not is_starter_skill(lib.skills[skill_id])
    starters = keyword_pools(lib, starter_only=True, exclusive_only=True)["form"]
    assert not set(HIGH) & set(starters)
    assert not set(HIGH) & set(starter_pools(lib)["form"])  # 開局選「形態」照舊只給 1 階化身


def _pinned_form(tier: int, seed: int) -> CandidateRequest:
    return CandidateRequest(
        keyword_counts={"form": 1},
        weapon_class="melee",
        seed=seed,
        tier=tier,
        pinned_keyword="form",
    )


@pytest.mark.parametrize("tier", [3, 4])
def test_offers_pinned_to_form_have_skills_at_tiers_three_and_four(tier: int) -> None:
    lib = library()
    seen: set[str] = set()
    for seed in range(20):
        for candidate in generate_candidates(lib, _pinned_form(tier, seed)):
            assert candidate.keywords[0] == "form"
            assert skill_has_keywords(candidate.skill, ("form",), lib)
            assert candidate.skill.tier == tier
            seen.add(candidate.skill.id)
    wanted = {s for s, (_, t, _) in HIGH.items() if t == tier}
    assert wanted <= seen, seen
    assert any(lib.skills[s].rarity == "epic" for s in seen)


def test_the_flurry_needs_a_form_and_strikes_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=15, die=1)
    state = arena([FLURRY, BEAR])
    with pytest.raises(IllegalActionError, match="需要「你在形態中」"):
        resolve(state, UseSkill(unit_id=U1, skill_id=FLURRY, target_id=U2))
    result = use(into_bear(state), FLURRY, target_id=U2)
    hits = of(result, DamageDealt)  # type: ignore[arg-type]
    assert [h.target_id for h in hits] == [U2, U2]


def _prone(result: object) -> list[str]:
    applied = of(result, StatusApplied)  # type: ignore[arg-type]
    return [e.target_id for e in applied if e.status_id == "prone"]


def test_the_quake_hits_the_ring_and_knocks_down_only_inside_a_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    foes = ((5, 3), (4, 3))  # 第一個在 2 格外，第二個貼身（GS-3 起是實心環形：周圍 2 格都打）
    plain = use(arena([QUAKE, BEAR], foes=foes), QUAKE)
    assert {h.target_id for h in of(plain, DamageDealt)} == {U2, U3}  # type: ignore[arg-type]
    assert {h.multiplier_permille for h in of(plain, DamageDealt)} == {1000}  # type: ignore[arg-type]
    assert _prone(plain) == []
    state = into_bear(arena([QUAKE, BEAR], foes=foes))
    attrs = state.units[U1].attributes
    key = next(k for k in attrs if str(getattr(k, "value", k)) == Attribute.CON.value)
    attrs[key] = 400  # 對抗穩贏
    inside = use(state, QUAKE)
    hits = of(inside, DamageDealt)  # type: ignore[arg-type]
    assert {h.target_id for h in hits} == {U2, U3}
    assert {h.multiplier_permille for h in hits} == {1300}
    assert sorted(_prone(inside)) == [U2, U3]


def test_primal_return_releases_the_form_then_hits_the_ring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=15, die=1)
    state = arena([PRIMAL, BEAR], foes=((5, 3),))
    with pytest.raises(IllegalActionError, match="只能在形態中使用"):
        resolve(state, UseSkill(unit_id=U1, skill_id=PRIMAL))
    result = use(into_bear(state), PRIMAL)
    left = of(result, FormLeft)  # type: ignore[arg-type]
    assert [(e.form_id, e.reason) for e in left] == [("bear", "released")]
    assert [h.target_id for h in of(result, DamageDealt)] == [U2]  # type: ignore[arg-type]


def test_the_guardian_needs_a_form_and_shields_the_caster() -> None:
    state = arena([GUARDIAN, BEAR])
    with pytest.raises(IllegalActionError, match="需要「你在形態中」"):
        resolve(state, UseSkill(unit_id=U1, skill_id=GUARDIAN))
    result = use(into_bear(state), GUARDIAN)
    shielded = [e.unit_id for e in of(result, ShieldGained)]  # type: ignore[arg-type]
    assert U1 in shielded and U2 not in shielded
