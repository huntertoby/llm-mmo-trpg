"""白板產生（Phase 3W-4，06 6.34.1）：單一效果模式、白板定義的驗證、三選一種類比例、候選產生器。"""

from __future__ import annotations

from collections import Counter

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import (
    WHITEBOARD_KINDS,
    compose_whiteboard,
    is_whiteboard,
    whiteboard_keywords,
    whiteboard_problems,
)
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates, pick_whiteboard_kind

LIB = library()
RULES = LIB.composer.whiteboard
SEEDS = range(6)
WEAPON_CLASSES = (None, "melee", "ranged", "focus")


def _exclusive(skill: SkillDef) -> tuple[str, ...]:
    return derive_keywords(skill, LIB.keywords, exclusive_only=True).all()


def _recipes() -> list[tuple[str, str]]:
    return [(k, r.id) for k in WHITEBOARD_KINDS for r in RULES.recipes(k)]


# ---------------------------------------------------------------------------
# 單一效果模式
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", WHITEBOARD_KINDS)
def test_every_keyword_with_recipes_composes_valid_whiteboards(kind: str) -> None:
    """每個有配方的（種類, 關鍵字）、每種武器大類、多個種子：做得出白板，通過驗證器與白板定義，
    且恰好製造配方的那一個關鍵字。"""
    for keyword in sorted(whiteboard_keywords(LIB, kind)):
        for seed in SEEDS:
            for weapon_class in WEAPON_CLASSES:
                skill = compose_whiteboard(
                    seed, kind=kind, keyword=keyword, weapon_class=weapon_class, library=LIB
                )
                assert skill.kind == kind and skill.tier == RULES.tier
                assert validate_skill(skill, LIB) == []
                assert whiteboard_problems(skill, LIB) == []
                assert _exclusive(skill) == (keyword,)
                if weapon_class is not None:
                    assert weapon_problem(skill, weapon_class, {}) is None


def test_active_whiteboards_use_the_default_cost() -> None:
    """主動白板：AP 2、冷卻 0～2、沒有每場次數／自身狀態／透支；單體或小範圍的形狀。"""
    seen_shapes: set[str] = set()
    for keyword in sorted(whiteboard_keywords(LIB, "active")):
        for seed in range(10):
            skill = compose_whiteboard(seed, keyword=keyword, library=LIB)
            assert skill.ap_cost == RULES.ap_cost
            assert (skill.cost.cooldown or 0) <= RULES.cooldown.max
            assert skill.cost.uses_per_battle is None and skill.cost.overdraft is None
            assert skill.cost.self_status is None
            assert len(skill.effects) == 1 and skill.condition is None
            seen_shapes.add(skill.shape.type)
    assert seen_shapes <= {"single", "ground_tile", "cross", "square3"}
    assert {"single", "cross"} <= seen_shapes


def test_passive_and_reaction_whiteboards_have_their_own_fields() -> None:
    passive = compose_whiteboard(1, kind="passive", keyword="ignite", library=LIB)
    assert passive.kind == "passive" and passive.trigger is not None
    assert passive.ap_cost is None and passive.rarity == "epic"  # 被動的觸發時機要 epic
    reaction = compose_whiteboard(1, kind="reaction", keyword="charged", library=LIB)
    assert reaction.kind == "reaction" and reaction.reaction is not None
    assert reaction.ap_cost is None


def test_whiteboard_budget_ratio_is_inside_the_tuning_window() -> None:
    """預算 70～100%（同階規則）；組合器收在 75～95%。"""
    for kind in WHITEBOARD_KINDS:
        for keyword in sorted(whiteboard_keywords(LIB, kind)):
            for seed in range(5):
                skill = compose_whiteboard(seed, kind=kind, keyword=keyword, library=LIB)
                ratio = skill_budget(skill, LIB).ratio
                assert 0.70 <= ratio <= 1.0, (skill.id, ratio)


def test_whiteboard_is_deterministic_and_seeds_differ() -> None:
    first = compose_whiteboard(5, keyword="ignite", weapon_class="focus", library=LIB)
    assert first == compose_whiteboard(5, keyword="ignite", weapon_class="focus", library=LIB)
    assert first.id == "skill_rand_5"
    variants = {
        compose_whiteboard(s, keyword="ignite", library=LIB).model_dump_json() for s in range(12)
    }
    assert len(variants) > 4


def test_unknown_or_unavailable_requests_raise() -> None:
    with pytest.raises(ComposeError, match="沒有關鍵字 wet"):
        compose_whiteboard(1, keyword="wet", library=LIB)  # 潮濕沒有單一效果配方
    with pytest.raises(ComposeError, match="未知的白板種類"):
        compose_whiteboard(1, kind="stance", library=LIB)
    with pytest.raises(ComposeError, match="沒有關鍵字 collision"):
        compose_whiteboard(1, kind="reaction", keyword="collision", library=LIB)


def test_weapon_class_focus_only_gets_spells() -> None:
    for seed in SEEDS:
        skill = compose_whiteboard(seed, keyword="concealed", weapon_class="focus", library=LIB)
        assert skill.category == "spell"


def test_the_full_composer_is_untouched() -> None:
    """完整模式不受影響（留給完整技能三選一）：同種子仍組出同一招，且不是白板限定的單一效果。"""
    skill = compose_random_skill(3, tier=2, library=LIB)
    assert skill == compose_random_skill(3, tier=2, library=LIB)
    assert skill.tier == 2


# ---------------------------------------------------------------------------
# 白板定義的驗證
# ---------------------------------------------------------------------------


def _board() -> SkillDef:
    return compose_whiteboard(2, keyword="ignite", library=LIB)


def _problems(skill: SkillDef) -> str:
    return "；".join(whiteboard_problems(skill, LIB))


def test_validator_rejects_each_part_of_the_definition() -> None:
    board = _board()
    assert is_whiteboard(board, LIB)
    assert "必須是 1 階" in _problems(board.model_copy(update={"tier": 2}))
    assert "AP 必須是 2" in _problems(board.model_copy(update={"ap_cost": 3}))
    cost = board.cost.model_copy(update={"cooldown": 3})
    assert "冷卻最多 2" in _problems(board.model_copy(update={"cost": cost}))
    cost = board.cost.model_copy(update={"uses_per_battle": 1})
    assert "不能有每場次數" in _problems(board.model_copy(update={"cost": cost}))
    ring = board.shape.model_copy(update={"type": "ring"})
    assert "形狀必須簡單" in _problems(board.model_copy(update={"shape": ring}))
    two = board.model_copy(update={"effects": (*board.effects, *board.effects)})
    assert "只能有 1 個核心效果" in _problems(two)


def test_validator_rejects_two_keywords_and_budget_out_of_range() -> None:
    burning = compose_whiteboard(2, keyword="ignite", library=LIB)
    other = compose_whiteboard(2, kind="passive", keyword="charged", library=LIB)
    merged = burning.model_copy(update={"effects": (*burning.effects, *other.effects)})
    assert "剛好一個關鍵字" in _problems(merged)
    bolt = next(
        s
        for s in (compose_whiteboard(x, keyword="charged", library=LIB) for x in range(30))
        if s.effects[0].type == "damage" and s.effects[0].dice is not None
    )
    for dice in ("1d4", "8d12"):
        data = bolt.model_dump(mode="json")
        data["effects"][0]["dice"] = dice
        edited = SkillDef.model_validate(data)
        assert "預算比例必須在 70%～100%" in _problems(edited), dice


def test_handwritten_skills_with_many_effects_are_not_whiteboards() -> None:
    skill = LIB.skills["skill_ground_finish"]  # 兩個傷害效果（含條件）
    assert not is_whiteboard(skill, LIB)
    assert any("核心效果" in p or "條件" in p for p in whiteboard_problems(skill, LIB))


# ---------------------------------------------------------------------------
# 種類比例（07 7.6）與三選一
# ---------------------------------------------------------------------------


def test_kind_ratio_is_70_20_10_and_lives_in_content() -> None:
    assert RULES.kind_permille == {"active": 700, "passive": 200, "reaction": 100}
    counts = Counter(pick_whiteboard_kind(LIB, Rng(seed)) for seed in range(4000))
    assert 0.66 <= counts["active"] / 4000 <= 0.74
    assert 0.16 <= counts["passive"] / 4000 <= 0.24
    assert 0.07 <= counts["reaction"] / 4000 <= 0.13


def _request(
    counts: dict[str, int], seed: int = 1, weapon_class: str = "focus"
) -> CandidateRequest:
    return CandidateRequest(keyword_counts=counts, weapon_class=weapon_class, seed=seed, tier=3)


HELD = {"ignite": 2, "marked": 1, "charged": 1}


def test_candidates_are_whiteboards_in_deepen_bridge_new_order() -> None:
    for seed in range(8):
        found = generate_whiteboard_candidates(LIB, _request(HELD, seed))
        assert [c.kind for c in found] == ["deepen", "bridge", "new"]
        for c in found:
            assert len(c.keywords) == 1 and c.keywords[0] in _exclusive(c.skill)
            if c.keywords[0] in whiteboard_keywords(LIB, "active"):
                assert c.source == "composer" and is_whiteboard(c.skill, LIB), c.skill.id
                assert _exclusive(c.skill) == c.keywords
            else:  # 沒有白板配方的關鍵字退回手寫池的 1 階技能
                assert c.source == "pool" and c.skill.tier == RULES.tier
        assert found[0].keywords == ("ignite",) and not found[0].fallback
        assert found[1].keywords[0] in {"marked", "charged"}
        assert found[2].keywords[0] not in HELD
        assert len({c.skill.id for c in found}) == 3


def test_candidates_are_deterministic_and_depend_on_the_seed() -> None:
    first = generate_whiteboard_candidates(LIB, _request(HELD, 4))
    assert first == generate_whiteboard_candidates(LIB, _request(HELD, 4))
    assert first != generate_whiteboard_candidates(LIB, _request(HELD, 5))


def test_candidate_kinds_follow_the_70_20_10_ratio() -> None:
    counts: Counter[str] = Counter()
    for seed in range(200):
        for c in generate_whiteboard_candidates(LIB, _request(HELD, seed)):
            counts[c.skill.kind] += 1
    total = sum(counts.values())
    assert total >= 580
    assert 0.60 <= counts["active"] / total <= 0.80
    assert 0.12 <= counts["passive"] / total <= 0.28
    assert 0.04 <= counts["reaction"] / total <= 0.18


def test_candidates_with_no_keywords_fall_back_to_new_directions() -> None:
    found = generate_whiteboard_candidates(LIB, _request({}, 3))
    assert [c.kind for c in found] == ["deepen", "bridge", "new"]
    assert found[0].fallback and found[1].fallback and not found[2].fallback
    assert len({c.keywords for c in found}) == 3


def test_keywords_without_recipes_fall_back_to_the_handwritten_pool() -> None:
    found = generate_whiteboard_candidates(LIB, _request({"wet": 3, "prone": 1}, 2))
    deepen = found[0]
    assert deepen.keywords == ("wet",) and deepen.source == "pool"
    assert deepen.skill.id in LIB.skills and deepen.skill.tier == RULES.tier


def test_excluded_and_weapon_incompatible_skills_never_appear() -> None:
    request = _request({"wet": 2, "prone": 1}, 3, weapon_class="melee")
    for c in generate_whiteboard_candidates(LIB, request):
        assert weapon_problem(c.skill, "melee", {}) is None
    banned = generate_whiteboard_candidates(LIB, _request({"wet": 2}, 2))[0].skill.id
    again = generate_whiteboard_candidates(
        LIB,
        CandidateRequest(
            keyword_counts={"wet": 2},
            weapon_class="focus",
            seed=2,
            tier=1,
            exclude=frozenset({banned}),
        ),
    )
    assert banned not in {c.skill.id for c in again}
