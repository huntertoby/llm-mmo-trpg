"""共用候選產生器：加深、橋接、新方向（Phase 3-24b2，06 6.27.4）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import weapon_problem
from trpg.skillgen.candidates import (
    Candidate,
    CandidateRequest,
    CandidateRules,
    behavior_weights,
    generate_candidates,
    keyword_distribution,
    skill_has_keywords,
)
from trpg.skillgen.keywords import derive_keywords


def _generate(  # noqa: PLR0917 - 測試輔助：位置參數讓呼叫處簡短
    counts: dict[str, int],
    weapon_class: str = "focus",
    seed: int = 1,
    tier: int = 1,
    behavior: dict[str, int] | None = None,
    exclude: frozenset[str] = frozenset(),
) -> tuple[Candidate, ...]:
    request = CandidateRequest(
        keyword_counts=counts,
        weapon_class=weapon_class,
        seed=seed,
        tier=tier,
        behavior=behavior or {},
        exclude=exclude,
    )
    return generate_candidates(library(), request)


def _exclusive(candidate: Candidate) -> tuple[str, ...]:
    return derive_keywords(candidate.skill, library().keywords, exclusive_only=True).all()


HELD = {"ignite": 2, "marked": 1, "charged": 1}


@pytest.mark.parametrize("seed", range(6))
def test_three_candidates_follow_their_definitions(seed: int) -> None:
    """加深帶持有最多的關鍵字、橋接同時帶兩個已持有的、新方向帶還沒有的（只看專屬規則）。"""
    found = _generate(HELD, seed=seed)
    assert [c.kind for c in found] == ["deepen", "bridge", "new"]
    deepen, bridge, new = found
    assert deepen.keywords == ("ignite",) and not deepen.fallback
    assert "ignite" in _exclusive(deepen)
    assert len(bridge.keywords) == 2 and set(bridge.keywords) <= set(HELD) and not bridge.fallback
    assert set(bridge.keywords) <= set(_exclusive(bridge))
    assert len(new.keywords) == 1 and new.keywords[0] not in HELD and not new.fallback
    assert new.keywords[0] in _exclusive(new)
    assert len({c.skill.id for c in found}) == 3


@pytest.mark.parametrize(("weapon_class", "tier"), [("melee", 1), ("ranged", 1), ("focus", 2)])
def test_candidates_respect_weapon_tier_and_exclusions(weapon_class: str, tier: int) -> None:
    held = {"prone": 2, "collision": 1} if weapon_class == "melee" else {"marked": 1, "ignite": 1}
    first = _generate(held, weapon_class, seed=3, tier=tier)
    exclude = frozenset(c.skill.id for c in first)
    again = _generate(held, weapon_class, seed=3, tier=tier, exclude=exclude)
    for candidate in (*first, *again):
        assert weapon_problem(candidate.skill, weapon_class) is None
        assert candidate.skill.tier == tier
        assert candidate.skill.rarity != "legendary"
    assert not exclude & {c.skill.id for c in again}


def test_same_seed_gives_the_same_candidates_and_seeds_vary() -> None:
    a = _generate(HELD, seed=11)
    assert a == _generate(HELD, seed=11)
    assert len({tuple(c.skill.id for c in _generate(HELD, seed=s)) for s in range(8)}) > 1


def test_one_held_keyword_bridges_outward() -> None:
    """持有 1 個關鍵字：橋接退回「持有的 ＋ 一個還沒有的」，標示 fallback。"""
    for seed in range(5):
        deepen, bridge, new = _generate({"ignite": 1}, seed=seed)
        assert deepen.keywords == ("ignite",) and not deepen.fallback
        assert bridge.fallback and bridge.keywords[0] == "ignite"
        assert set(bridge.keywords) <= set(_exclusive(bridge))
        assert new.keywords[0] != "ignite" and not new.fallback


def test_no_held_keyword_falls_back_to_new_directions() -> None:
    """持有 0 個關鍵字（白板主角）：加深與橋接都退回新方向，三個候選帶不同的關鍵字。"""
    found = _generate({}, seed=2)
    assert [c.kind for c in found] == ["deepen", "bridge", "new"]
    assert found[0].fallback and found[1].fallback and not found[2].fallback
    assert len({c.keywords[0] for c in found}) == 3
    for candidate in found:
        assert set(candidate.keywords) <= set(_exclusive(candidate))


def test_every_keyword_held_new_direction_falls_back_to_the_least_held() -> None:
    counts = dict.fromkeys(library().keywords.ids(), 2) | {"summon": 1}
    new = _generate(counts, seed=4)[-1]
    assert new.kind == "new" and new.fallback


def test_behavior_tilts_the_new_direction() -> None:
    """常用推擊（shove）的玩家，新方向較常出撞擊（skill_keywords.yaml 的 actions）。"""
    lib = library()
    assert behavior_weights(lib, {"shove": 5, "trip": 1})["collision"] == 5
    plain = sum(_generate({"ignite": 1}, seed=s)[-1].keywords == ("collision",) for s in range(30))
    tilted = sum(
        _generate({"ignite": 1}, seed=s, behavior={"shove": 40})[-1].keywords == ("collision",)
        for s in range(30)
    )
    assert tilted > plain


def test_behavior_breaks_deepen_ties() -> None:
    deepen = _generate({"ignite": 1, "prone": 1}, behavior={"trip": 9})[0]
    assert deepen.keywords == ("prone",)
    assert _generate({"ignite": 1, "prone": 1})[0].keywords == ("ignite",)


def test_distribution_counts_exclusive_keywords_once_per_skill() -> None:
    lib = library()
    skills = [lib.skills["skill_ember_trail"], lib.skills["skill_fire_bolt"]]
    dist = keyword_distribution(skills, lib)
    assert dist["ignite"] == 2 and dist["marked"] == 1
    # 近戰武器技只靠「通用」規則利用倒地：不算進分布（PM 決定：只看專屬規則）
    cleave = lib.skills["skill_cleave"]
    assert "prone" in derive_keywords(cleave, lib.keywords).all()
    assert keyword_distribution([cleave], lib) == {}
    assert skill_has_keywords(lib.skills["skill_ember_trail"], ("ignite", "marked"), lib)


def test_composer_and_pool_sources_both_used() -> None:
    sources = {c.source for s in range(10) for c in _generate(HELD, seed=s)}
    assert sources == {"pool", "composer"}
    only_pool = generate_candidates(
        library(),
        CandidateRequest(keyword_counts=HELD, weapon_class="focus", seed=1, tier=1),
        CandidateRules(composer_share_permille=0, composer_tries=0),
    )
    assert {c.source for c in only_pool} == {"pool"}


def test_unknown_keyword_is_rejected() -> None:
    with pytest.raises(ValueError, match="未知的關鍵字"):
        _generate({"nope": 1})
