"""主題合併（R2）。

原 ``test_whiteboard_3w4.py``：

白板產生（Phase 3W-4，06 6.34.1）：單一效果模式、白板定義的驗證、三選一種類比例、候選產生器。

原 ``test_whiteboard_3w4b.py``：

白板配方補齊（Phase 3W-4b，06 6.34.1、6.34.9）：潮濕／倒地／撞擊例外、召喚白板、2 階起的陷阱／
姿態／位移、3 階的修正型被動與雙屬性縮放、反應位移、被動新核心、通用池。

原 ``test_whiteboard_3w2b.py``：

Phase 3W-2b 第 6 點：3W-4b 補配方（06 6.34.1，3664e63f）。

潮濕被動／反應、倒地反應、撞擊被動、標記被動：每個配方在各階級做得出來、通過白板定義與預算窗、推導
出對的關鍵字，放進戰鬥真的照卡片結算；創角選召喚物時優先給遠程的基本召喚物。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from functools import cache

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_new_triggers import _push, _wall_scene
from tests.engine.test_passive_triggers import always
from tests.engine.test_reaction_skills import duel
from trpg.content.composer_rules import WhiteboardRecipe
from trpg.content.skills import SkillDef, TriggerSpec, weapon_problem
from trpg.engine import Attack, BattleState, EndTurn, resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.effects import run_effects
from trpg.engine.events import (
    DamageDealt,
    ReactionTriggered,
    SkillTriggered,
    StatusApplied,
    TrapPlaced,
    UnitMoved,
    UnitSummoned,
)
from trpg.engine.preview import preview
from trpg.narrative.skills import skill_card
from trpg.roguelite.start import starting_skill
from trpg.shared.rng import Rng
from trpg.shared.types import Surface, Team, UnitId
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
)
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates, pick_whiteboard_kind
from trpg.skillgen.whiteboard_check import whiteboard_keywords_of, whiteboard_problems

# --- 原 test_whiteboard_3w4.py ---

LIB = library()
GENERIC = LIB.composer.whiteboard.generic_keyword
RULES = LIB.composer.whiteboard
SEEDS = range(6)
WEAPON_CLASSES = (None, "melee", "ranged", "focus")


def _exclusive(skill: SkillDef) -> tuple[str, ...]:
    return whiteboard_keywords_of(skill, LIB)


def _recipes() -> list[tuple[str, str]]:
    return [(k, r.id) for k in WHITEBOARD_KINDS for r in RULES.recipes(k)]


# ---------------------------------------------------------------------------
# 單一效果模式
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", WHITEBOARD_KINDS)
def test_every_keyword_with_recipes_composes_valid_whiteboards(kind: str) -> None:
    """每個有配方的（種類, 關鍵字）、每種武器大類、多個種子：做得出白板，通過驗證器與白板定義，
    且恰好製造配方的那一個關鍵字。"""
    for keyword in sorted(whiteboard_keywords(LIB, kind, RULES.tier)):
        for seed in SEEDS:
            for weapon_class in WEAPON_CLASSES:
                skill = compose_whiteboard(
                    seed, kind=kind, keyword=keyword, weapon_class=weapon_class, library=LIB
                )
                assert skill.kind == kind and skill.tier == RULES.tier
                assert validate_skill(skill, LIB) == []
                assert whiteboard_problems(skill, LIB) == []
                assert keyword in (*_exclusive(skill), GENERIC, "summon")
                if weapon_class is not None:
                    assert weapon_problem(skill, weapon_class, {}) is None


def test_active_whiteboards_use_the_default_cost() -> None:
    """主動白板：AP 2、冷卻 0～2、沒有每場次數／自身狀態／透支；單體或小範圍的形狀。"""
    seen_shapes: set[str] = set()
    for keyword in sorted(whiteboard_keywords(LIB, "active", RULES.tier) - {"summon", GENERIC}):
        for seed in range(10):
            skill = compose_whiteboard(seed, keyword=keyword, library=LIB)
            # 3W-9：1 階的隆地只升一格（AP 1，同自身類白板）
            want = RULES.self_ap_cost if skill.effects[0].type == "raise_terrain" else RULES.ap_cost
            assert skill.ap_cost == want
            assert (skill.cost.cooldown or 0) <= RULES.cooldown.max
            assert skill.cost.uses_per_battle is None and skill.cost.overdraft is None
            assert skill.cost.self_status is None
            assert skill.condition is None
            seen_shapes.add(skill.shape.type)
    # BAL-19f（#110）：白板加直線、錐形、環形（連鎖 3 階）
    assert seen_shapes <= {"single", "ground_tile", "cross", "square3", "line", "cone", "ring"}
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
        for keyword in sorted(whiteboard_keywords(LIB, kind, RULES.tier)):
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
    with pytest.raises(ComposeError, match="沒有關鍵字 form"):
        compose_whiteboard(1, keyword="form", library=LIB)  # 形態不可組合
    with pytest.raises(ComposeError, match="未知的白板種類"):
        compose_whiteboard(1, kind="stance", library=LIB)
    with pytest.raises(ComposeError, match="沒有關鍵字 form"):
        compose_whiteboard(1, kind="reaction", keyword="form", library=LIB)


def test_weapon_class_focus_only_gets_spells() -> None:
    for seed in SEEDS:
        skill = compose_whiteboard(seed, keyword="concealed", weapon_class="focus", library=LIB)
        assert skill.category == "spell"


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_whiteboards_use_the_hero_tier_budget(tier: int) -> None:
    """#72：白板用角色目前階級的預算；3×3 要 2 階才開放（十字 1 階就有）。"""
    shapes: set[str] = set()
    made = 0
    for kind in WHITEBOARD_KINDS:
        for keyword in sorted(whiteboard_keywords(LIB, kind, RULES.tier)):
            for seed in range(4):
                try:
                    skill = compose_whiteboard(
                        seed, kind=kind, keyword=keyword, tier=tier, library=LIB
                    )
                except ComposeError:  # 弱的單一效果在高階湊不到預算下限：呼叫端退回手寫池
                    continue
                made += 1
                assert skill.tier == tier and whiteboard_problems(skill, LIB, tier) == []
                assert validate_skill(skill, LIB) == []
                shapes.add(skill.shape.type)
    assert made >= 50
    assert ("square3" in shapes) == (tier >= 2)
    assert whiteboard_problems(compose_whiteboard(1, keyword="ignite", library=LIB), LIB, 2)


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
    assert "必須是 2 階" in "；".join(whiteboard_problems(board, LIB, 2))
    assert "AP 必須是 2" in _problems(board.model_copy(update={"ap_cost": 3}))
    cost = board.cost.model_copy(update={"cooldown": 3})
    assert "冷卻最多 2" in _problems(board.model_copy(update={"cost": cost}))
    cost = board.cost.model_copy(update={"uses_per_battle": 1})
    assert "不能有每場次數" in _problems(board.model_copy(update={"cost": cost}))
    wide = board.shape.model_copy(update={"type": "allies_in_radius"})  # BAL-19f：環形算簡單
    assert "形狀必須簡單" in _problems(board.model_copy(update={"shape": wide}))
    two = board.model_copy(update={"effects": (*board.effects, *board.effects)})
    assert "只能有 1 個核心效果" in _problems(two)


def test_validator_rejects_two_keywords_and_budget_out_of_range() -> None:
    burning = compose_whiteboard(2, keyword="ignite", library=LIB)
    other = compose_whiteboard(2, kind="passive", keyword="charged", library=LIB)
    merged = burning.model_copy(update={"effects": (*burning.effects, *other.effects)})
    assert "最多一個關鍵字" in _problems(merged)
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
    return CandidateRequest(keyword_counts=counts, weapon_class=weapon_class, seed=seed, tier=2)


HELD = {"ignite": 2, "marked": 1, "charged": 1}


@cache
def _composes(keyword: str) -> bool:
    """法器 2 階組得出這個關鍵字的主動白板（KW-2：新方向多了四個關鍵字，種子 7 抽到中毒；中毒的
    主動配方在 2 階湊不到預算下限，候選照設計退回手寫池——既有的缺口，不是這次的改動）。"""
    for seed in range(5):
        try:
            compose_whiteboard(seed, keyword=keyword, tier=2, weapon_class="focus", library=LIB)
        except ComposeError:
            continue
        return True
    return False


def test_candidates_are_whiteboards_in_deepen_bridge_new_order() -> None:
    for seed in range(8):
        found = generate_whiteboard_candidates(LIB, _request(HELD, seed))
        assert [c.kind for c in found] == ["deepen", "bridge", "new"]
        for c in found:
            if not c.keywords:  # 通用池白板（3W-4b）：沒有關鍵字
                assert c.kind == "new" and c.source == "composer" and _exclusive(c.skill) == ()
                continue
            if (
                c.kind == "bridge" and len(c.keywords) == 2
            ):  # 6F-4c：#130 雙關鍵字橋接（利用者白板）
                assert set(c.keywords) <= set(HELD) and c.source == "composer"
                assert is_whiteboard(c.skill, LIB), c.skill.id
                assert set(c.keywords) <= set(derive_keywords(c.skill, LIB.keywords).all())
                continue
            assert len(c.keywords) == 1
            if c.keywords[0] in whiteboard_keywords(LIB, "active", 2) and _composes(c.keywords[0]):
                assert c.source == "composer" and is_whiteboard(c.skill, LIB), c.skill.id
                assert c.keywords[0] in derive_keywords(c.skill, LIB.keywords).all()
            else:  # 沒有白板配方的關鍵字退回手寫池的 1 階技能
                assert c.source == "pool" and c.skill.tier == RULES.tier
        assert found[0].keywords == ("ignite",) and not found[0].fallback
        assert found[1].keywords[-1] in {"marked", "charged"}
        assert not found[2].keywords or found[2].keywords[0] not in HELD
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


def test_exception_keywords_now_get_composer_boards_not_the_pool() -> None:
    """3W-4b：潮濕、倒地、撞擊有白板配方，不再退回手寫池。"""
    found = generate_whiteboard_candidates(LIB, _request({"wet": 3, "prone": 1}, 2))
    deepen = found[0]
    assert deepen.keywords == ("wet",) and deepen.source == "composer"
    assert is_whiteboard(deepen.skill, LIB, 2)


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


# --- 原 test_whiteboard_3w4b.py ---

LIB_3W4B = library()
RULES_3W4B = LIB_3W4B.composer.whiteboard
GENERIC_3W4B = RULES_3W4B.generic_keyword
SEEDS_3W4B = range(4)


def _3w4b_recipes() -> list[tuple[str, WhiteboardRecipe]]:
    return [(k, r) for k in WHITEBOARD_KINDS for r in RULES_3W4B.recipes(k)]


def _tiers(recipe: WhiteboardRecipe) -> list[int]:
    return [t for t in (1, 2, 3) if recipe.min_tier <= t <= (recipe.max_tier or t)]


def _make(recipe_id: str, kind: str, tier: int, seed: int, wc: str | None = None) -> SkillDef:
    return compose_whiteboard(
        seed, kind=kind, recipe_id=recipe_id, tier=tier, weapon_class=wc, library=LIB_3W4B
    )


def _compose_or_none(recipe_id: str, kind: str, tier: int, seed: int, wc: str | None = None):  # type: ignore[no-untyped-def]
    try:
        return _make(recipe_id, kind, tier, seed, wc)
    except ComposeError:
        return None


def _kw(skill: SkillDef) -> tuple[str, ...]:
    found = derive_keywords(skill, LIB_3W4B.keywords, exclusive_only=True).all()
    if any(e.type == "summon" for e in skill.effects) and len(found) > 1:
        return tuple(k for k in found if k != "summon")
    return found


# ---------------------------------------------------------------------------
# 每個配方：做得出來、過驗證與白板定義、預算 70～100%、關鍵字對得上
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind,recipe", _3w4b_recipes(), ids=lambda x: getattr(x, "id", x))
def test_every_recipe_composes_valid_whiteboards_in_its_tiers(
    kind: str, recipe: WhiteboardRecipe
) -> None:
    made = 0
    for tier in _tiers(recipe):
        for seed in SEEDS_3W4B:
            for wc in (None, "melee", "ranged", "focus"):
                skill = _compose_or_none(recipe.id, kind, tier, seed, wc)
                if skill is None:  # 這種武器大類沒有這個配方（例如雙屬性武器技給法器）
                    continue
                made += 1
                assert skill.tier == tier and validate_skill(skill, LIB_3W4B) == []
                assert whiteboard_problems(skill, LIB_3W4B, tier) == [], skill.id
                assert 0.70 <= skill_budget(skill, LIB_3W4B).ratio <= 1.0
                keywords = _kw(skill)
                natural = ("prone",) if recipe.id == "summon_skeleton" else None  # 骷髏自帶倒地
                expected = () if recipe.keyword == GENERIC_3W4B else (recipe.keyword,)
                assert keywords in (expected, natural)
                weapon_name = recipe.weapon_name_zh if skill.category == "weapon" else None
                assert skill.name_zh == (weapon_name or recipe.name_zh)  # 6F-1：武器版可另取名
    assert made >= 3, recipe.id


def test_recipes_follow_the_tier_table_of_decision_72() -> None:
    """召喚（創角的基本召喚物除外）、陷阱、姿態、位移 2 階起；修正型被動與雙屬性縮放 3 階起。"""
    for _, recipe in _3w4b_recipes():
        if recipe.species in ("trap", "stance", "displace"):
            assert recipe.min_tier >= 2, recipe.id
            assert recipe.species == "stance" or recipe.min_tier == 2, recipe.id
        if recipe.species in ("modifier", "dual"):
            assert recipe.min_tier == 3, recipe.id
        if recipe.species == "summon":  # 3W-9：召喚 2 階；BAL-19c（#110）：基本召喚物 1 階
            assert recipe.min_tier == (1 if recipe.keyword == "summon" else 2), recipe.id
            assert recipe.creation_tier == (1 if recipe.keyword == "summon" else None), recipe.id
    by_tier = {
        t: {r.species for k in WHITEBOARD_KINDS for r in RULES_3W4B.recipes(k, t)}
        for t in (1, 2, 3)
    }
    assert by_tier[1] == {"basic", "summon"}
    created = {r.species for k in WHITEBOARD_KINDS for r in RULES_3W4B.recipes(k, 1, creation=True)}
    assert created == {"basic", "summon"}
    assert {"trap", "stance", "displace"} <= by_tier[2] and not {"modifier", "dual"} & by_tier[2]
    assert {"modifier", "dual", "trap", "stance", "displace"} <= by_tier[3]


def test_every_keyword_has_a_whiteboard_from_tier_one() -> None:
    """潮濕、倒地、撞擊、召喚物也有白板（不必退回手寫池）；形態仍沒有。"""
    covered = whiteboard_keywords(LIB_3W4B, "active", 1, creation=True)  # 創角例外：召喚物（3W-9）
    every = set(LIB_3W4B.keywords.ids())  # KW-2：16 個關鍵字都檢查（KW-1 只檢查開局可選的 12 個）
    assert every - {"form"} <= covered | {"high_ground"} | {"marked"}
    assert {"combo_point", "fury", "focus", "ki"} <= covered  # KW-2 的層數白板 1 階就有
    assert {"wet", "prone", "collision", "summon"} <= covered


# ---------------------------------------------------------------------------
# 例外、召喚、創角
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", ["wet", "prone", "collision"])
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_exception_keywords_have_exploit_and_maker_boards(keyword: str, tier: int) -> None:
    seen: set[str] = set()
    for seed in range(10):
        skill = compose_whiteboard(seed, keyword=keyword, tier=tier, library=LIB_3W4B)
        types = [e.type for e in skill.effects]
        if types == ["summon"]:  # 2 階起也可能出對應的召喚物（倒地的戰狼、撞擊的石像、潮濕的水精）
            seen |= {"exploit", "maker"}
        elif len(skill.effects) == 1:  # 利用者：條件傷害
            assert types == ["damage"] and skill.effects[0].condition is not None
            seen.add("exploit")
        else:  # 製造者：弱傷害＋製造
            assert types[0] == "damage" and skill.effects[0].condition is None
            seen.add("maker")
    assert seen == {"exploit", "maker"}


def test_creation_summon_gets_a_summon_whiteboard_not_a_handwritten_skill() -> None:
    melee = ranged = 0
    for weapon in ("one_handed_sword", "fire_staff", "longbow"):
        if weapon not in LIB_3W4B.weapons:
            continue
        for seed in range(6):
            skill = starting_skill(LIB_3W4B, weapon, "summon", seed)
            assert skill is not None and skill.tier == 1
            assert skill.id.startswith("skill_rand_")  # 組合器產生，不是手寫召喚技
            assert [e.type for e in skill.effects] == ["summon"]
            assert whiteboard_problems(skill, LIB_3W4B, 1) == []
            unit = skill.effects[0].unit
            melee += unit == "summon_skeleton_warrior"
            ranged += unit == "summon_elemental_spirit"
    # 3W-2b（06 6.34.1，3664e63f）：選「召喚物」時優先給遠程基本召喚物（推導出來沒有別的關鍵字）；
    # 近戰的骷髏戰士會推導成「倒地」，不符合所選關鍵字，創角不再給
    assert ranged and not melee
    melee_board = compose_whiteboard(
        3, kind="active", tier=2, library=LIB_3W4B, recipe_id="summon_skeleton"
    )  # 3W-9：召喚 2 階起（1 階只給創角）
    assert melee_board.effects[0].unit == "summon_skeleton_warrior"  # 配方仍在，其他情境可出


def test_tier_two_summons_follow_the_whiteboard_keyword() -> None:
    expected = {
        "ignite": "summon_fire_spirit",
        "frozen": "summon_ice_spirit",
        "charged": "summon_thunder_spirit",
        "concealed": "summon_shade",
    }
    for keyword, unit in expected.items():
        skill = compose_whiteboard(
            1, keyword=keyword, recipe_id=f"summon_{unit.split('_')[1]}", tier=2, library=LIB_3W4B
        )
        assert skill.effects[0].unit == unit and skill.ap_cost == RULES_3W4B.summon_ap_cost


# ---------------------------------------------------------------------------
# 階級開放：候選只出該階級有的種類
# ---------------------------------------------------------------------------


def _species_of(skill: SkillDef) -> str:
    first = skill.effects[0].type if skill.effects else ""
    if skill.kind == "stance":
        return "stance"
    if skill.kind == "modifier":
        return "modifier"
    if skill.trap is not None:
        return "trap"
    if first in ("teleport", "swap", "leap"):
        return "displace"
    if skill.secondary_scaling_attr is not None:
        return "dual"
    return "summon" if first == "summon" else "basic"


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_candidates_only_use_species_open_at_the_hero_tier(tier: int) -> None:
    held = {"ignite": 2, "frozen": 1, "charged": 1, "concealed": 1}
    seen: Counter[str] = Counter()
    for seed in range(60):
        request = CandidateRequest(keyword_counts=held, weapon_class="melee", seed=seed, tier=tier)
        for c in generate_whiteboard_candidates(LIB_3W4B, request):
            if c.source == "composer":
                seen[_species_of(c.skill)] += 1
                assert whiteboard_problems(c.skill, LIB_3W4B, tier) == [], c.skill.id
    assert seen["basic"] > 0
    if tier == 1:
        assert set(seen) <= {"basic", "summon"}
    if tier < 3:
        assert not {"modifier", "dual"} & set(seen)
    if tier == 3:
        assert {"trap", "stance", "displace", "summon", "modifier"} & set(seen)


def test_new_direction_has_ten_percent_generic_boards() -> None:
    held = {"ignite": 2, "marked": 1, "charged": 1}
    generic = total = 0
    for seed in range(400):
        request = CandidateRequest(keyword_counts=held, weapon_class="melee", seed=seed, tier=2)
        found = generate_whiteboard_candidates(LIB_3W4B, request)
        new = next(c for c in found if c.kind == "new")
        total += 1
        if not new.keywords:
            generic += 1
            assert new.source == "composer" and _kw(new.skill) == ()
            assert whiteboard_problems(new.skill, LIB_3W4B, 2) == []
    assert 0.05 <= generic / total <= 0.16


# ---------------------------------------------------------------------------
# 行為一致：卡片 ＝ 實戰
# ---------------------------------------------------------------------------


def _battle_with(skill: SkillDef):  # type: ignore[no-untyped-def]
    m = make_map(
        "\n".join(["000000000"] * 9), ally=[(0, 4), (0, 3)], enemy=[(1, 4), (2, 4), (2, 5)]
    )
    base = {"melee": "hero_fighter", "ranged": "hero_archer"}.get(skill.weapon_req, "hero_mage")
    spawns = [
        spawn(Team.ALLY, (0, 4), caster_template([skill], base=base)),
        spawn(Team.ALLY, (0, 3), no_reactions()),
        spawn(Team.ENEMY, (1, 4), no_reactions()),
        spawn(Team.ENEMY, (2, 4), no_reactions()),
        spawn(Team.ENEMY, (2, 5), no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[skill]), "unit_0001")


@cache
def _engine_cases() -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (r.id, t, k) for k, r in _3w4b_recipes() if r.species != "modifier" for t in _tiers(r)
    )


@pytest.mark.parametrize("recipe_id,tier,kind", _engine_cases())
def test_active_recipes_play_in_the_engine(recipe_id: str, tier: int, kind: str) -> None:
    """可主動施放的配方：放進戰鬥結算不報錯，卡片的傷害預覽範圍包住實際結算；召喚、陷阱、姿態、位移
    都有對應的事件。被動與反應只確認能裝備、能產生卡片。"""
    if kind != "active":
        for wc in ("focus", None, "ranged", "melee"):
            skill = _compose_or_none(recipe_id, kind, tier, 3, wc)
            if skill is not None:
                _battle_with(skill)
                assert skill_card(LIB_3W4B, skill).id == skill.id
                return
        pytest.skip("這個階級湊不到預算，或只有武器版本")
    skill = None
    for wc in ("focus", None):  # 法器施放者：武器技的配方改用沒有武器需求限制的種子
        skill = _compose_or_none(recipe_id, kind, tier, 3, wc)
        if skill is not None:
            break
    if skill is None:
        pytest.skip("這個階級湊不到預算")
    battle = _battle_with(skill)
    actions = [
        a for a in legal_actions(battle) if isinstance(a, UseSkill) and a.skill_id == skill.id
    ]
    assert actions, skill.id
    action = actions[0]
    seen = preview(battle, action)
    result = resolve(battle, action)
    assert result.state is not None
    events = result.events
    first = skill.effects[0].type if skill.effects else ""
    if first == "summon":
        assert any(isinstance(e, UnitSummoned) for e in events)
    elif skill.trap is not None:
        assert any(isinstance(e, TrapPlaced) for e in events)
    elif skill.kind == "stance":
        assert any(
            isinstance(e, StatusApplied) and e.status_id.startswith("stance_") for e in events
        )
    elif first in ("teleport", "leap"):
        assert any(isinstance(e, UnitMoved) and e.unit_id == "unit_0001" for e in events)
    elif first == "swap":
        assert sum(isinstance(e, UnitMoved) for e in events) >= 2
    dealt = [e for e in events if isinstance(e, DamageDealt) and not e.crit]
    targeted = [e for e in dealt if action.target_id and e.target_id == action.target_id]
    if targeted and seen.damage is not None and len({e.target_id for e in dealt}) == 1:
        total = sum(e.amount for e in targeted)
        assert seen.damage.minimum <= total <= seen.damage.maximum, (skill.id, total)
    assert skill_card(LIB_3W4B, skill).id == skill.id


def test_modifier_boards_equip_and_raise_damage_against_the_condition_target() -> None:
    skill = _make("burning_exploit", "passive", 3, 2)
    assert skill.kind == "modifier" and skill.modifiers[0].change.damage_permille is not None
    assert skill.modifiers[0].change.damage_permille >= 100
    assert skill_card(LIB_3W4B, skill).id == skill.id
    _battle_with(skill)


# --- 原 test_whiteboard_3w2b.py ---

LIB_3W2B = library()
NEW = {
    "damp_ward": ("passive", "wet"),
    "crash_bonus": ("passive", "collision"),
    "scout_mark": ("passive", "marked"),
    "splash_retort": ("reaction", "wet"),
    "trip_retort": ("reaction", "prone"),
}
U3, U4 = UnitId("unit_0003"), UnitId("unit_0004")


def _3w2b_board(recipe: str, seed: int = 3, tier: int = 1) -> SkillDef:
    """近戰武器能用的白板（戰鬥測試的持有者是戰士）。"""
    kind = NEW[recipe][0]
    return compose_whiteboard(
        seed, kind=kind, tier=tier, library=LIB_3W2B, recipe_id=recipe, weapon_class="melee"
    )


@pytest.mark.parametrize("recipe", sorted(NEW))
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_new_recipes_compose_valid_whiteboards_in_the_budget_window(recipe: str, tier: int) -> None:
    for seed in range(8):
        skill = _3w2b_board(recipe, seed, tier)
        assert validate_skill(skill, LIB_3W2B) == []
        assert whiteboard_problems(skill, LIB_3W2B, tier) == []
        report = skill_budget(skill, LIB_3W2B)
        assert report.min_ratio <= report.ratio <= report.max_ratio
        assert whiteboard_keywords_of(skill, LIB_3W2B) == (NEW[recipe][1],), (recipe, seed)


def _rolled(skill: SkillDef, damage: DamageDealt) -> bool:
    """實擲的骰數＝卡片：法術技是效果寫的骰數；武器技用武器骰（至少一顆）。"""
    effect = next(e for e in skill.effects if e.type == "damage")
    if effect.dice is not None:
        return len(damage.rolls) == effect.dice.count
    return len(damage.rolls) >= 1


def test_splash_retort_hits_the_attacker_and_wets_his_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _3w2b_board("splash_retort")
    always(monkeypatch)
    state = duel([skill])
    result = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    assert of(result, ReactionTriggered)
    back = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert back and _rolled(skill, back[0])  # 卡片的骰數＝實擲的骰數
    foe = result.state.units[U2]
    assert result.state.tile(*foe.xy).surface is Surface.WATER


def test_trip_retort_knocks_the_melee_attacker_prone(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _3w2b_board("trip_retort")
    always(monkeypatch)
    result = answered(resolve(duel([skill]), Attack(unit_id=U2, target_id=U1)))
    assert of(result, ReactionTriggered)
    assert result.state.units[U2].has_status("prone")
    back = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert back and _rolled(skill, back[0])


def test_trip_retort_ignores_ranged_attackers(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _3w2b_board("trip_retort")
    always(monkeypatch)
    state = duel([skill], foe="bandit_archer", foe_xy=(6, 3))
    result = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    assert not of(result, ReactionTriggered)


def test_damp_ward_shields_and_wets_the_owner_once_per_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _3w2b_board("damp_ward")
    always(monkeypatch)
    state = duel([skill])
    first = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    fired = [e for e in of(first, SkillTriggered) if e.skill_id == skill.id]
    assert len(fired) == 1
    me = first.state.units[U1]
    assert first.state.tile(*me.xy).surface is Surface.WATER
    second = answered(resolve(first.state, Attack(unit_id=U2, target_id=U1)))
    assert [e for e in of(second, SkillTriggered) if e.skill_id == skill.id] == []  # 每回合 1 次


def test_crash_bonus_adds_damage_when_a_pushed_unit_collides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _3w2b_board("crash_bonus")
    always(monkeypatch)
    result = run_effects(_wall_scene([skill]), [_push(U1)])
    fired = [e for e in result.events if isinstance(e, SkillTriggered) and e.skill_id == skill.id]
    assert len(fired) == 1 and fired[0].trigger == "on_collision"
    extra = [d for d in result.events if isinstance(d, DamageDealt) and d.cause != "collision"]
    assert [d.target_id for d in extra] == [U2]
    assert _rolled(skill, extra[0])


def _scout_scene(skill: SkillDef, foes: Sequence[tuple[int, int]]) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill], max_hp=999))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=999)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def _next_turn_of_owner(state: BattleState, foes: int) -> list[object]:
    """每個人依序結束回合，直到回到 U1 的下一個回合（回傳這段的所有事件，最後一項是狀態）。"""
    events: list[object] = []
    result = resolve(state, EndTurn(unit_id=U1))
    events += result.events
    for _ in range(foes + 1):
        if result.state.active_unit == U1:
            break
        active = result.state.active_unit
        assert active is not None
        result = answered(resolve(result.state, EndTurn(unit_id=active)))
        events += result.events
    events.append(result.state)
    return events


def test_scout_mark_marks_only_the_nearest_enemy_within_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=20)  # 抵抗判定一定失敗，標記一定上身
    skill = _3w2b_board("scout_mark")
    assert skill.trigger is not None
    assert (skill.trigger.target, skill.trigger.max_distance) == ("nearest_enemy", 3)
    # U2 在 2 格、U3 在 3 格、U4 在 6 格外
    state = _scout_scene(skill, [(5, 3), (6, 3), (3, 6)])
    *events, after = _next_turn_of_owner(state, 3)
    applied = [e for e in events if isinstance(e, StatusApplied) and e.status_id == "marked"]
    assert [e.target_id for e in applied] == [U2]
    assert isinstance(after, BattleState)
    assert after.units[U2].has_status("marked")
    assert not after.units[U3].has_status("marked") and not after.units[U4].has_status("marked")


def test_scout_mark_needs_an_enemy_in_range_and_costs_nothing_otherwise() -> None:
    skill = _3w2b_board("scout_mark")
    state = _scout_scene(skill, [(3, 6)])  # 3 格外（曼哈頓 3 剛好在內）→ 改放 4 格外
    far = _scout_scene(skill, [(0, 0)])
    mana = far.units[U1].mana
    *events, after = _next_turn_of_owner(far, 1)
    assert not [e for e in events if isinstance(e, SkillTriggered)]
    assert isinstance(after, BattleState) and after.units[U1].mana >= mana
    del state


def test_scout_mark_picks_the_lower_id_on_a_distance_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=20)
    skill = _3w2b_board("scout_mark")
    state = _scout_scene(skill, [(5, 3), (1, 3)])  # 都是 2 格
    *events, after = _next_turn_of_owner(state, 2)
    applied = [
        e.target_id for e in events if isinstance(e, StatusApplied) and e.status_id == "marked"
    ]
    assert applied == [U2]
    assert isinstance(after, BattleState)


def test_creation_prefers_the_ranged_basic_summon() -> None:
    """選「召喚物」時推導出來沒有別的關鍵字的遠程基本召喚物優先（近戰骷髏會推導成倒地）。"""
    for seed in range(12):
        skill = compose_whiteboard(
            seed, kind="active", keyword="summon", tier=1, library=LIB_3W2B, starter=True
        )
        assert skill.effects[0].unit == "summon_elemental_spirit"
        assert whiteboard_keywords_of(skill, LIB_3W2B) == ("summon",)


def test_nearest_enemy_trigger_schema() -> None:
    ok = TriggerSpec(event="on_turn_start", target="nearest_enemy", max_distance=3)
    assert ok.max_distance == 3
    with pytest.raises(ValidationError):  # 必須指定幾格內
        TriggerSpec(event="on_turn_start", target="nearest_enemy")
    with pytest.raises(ValidationError):  # self 不能有距離上限
        TriggerSpec(event="on_turn_start", target="self", max_distance=3)
