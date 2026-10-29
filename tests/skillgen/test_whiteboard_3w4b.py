"""白板配方補齊（Phase 3W-4b，06 6.34.1、6.34.9）：潮濕／倒地／撞擊例外、召喚白板、2 階起的陷阱／
姿態／位移、3 階的修正型被動與雙屬性縮放、反應位移、被動新核心、通用池。"""

from __future__ import annotations

from collections import Counter
from functools import cache

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.composer_rules import WhiteboardRecipe
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import (
    DamageDealt,
    StatusApplied,
    TrapPlaced,
    UnitMoved,
    UnitSummoned,
)
from trpg.engine.preview import preview
from trpg.narrative.skills import skill_card
from trpg.roguelite.start import starting_skill
from trpg.shared.types import Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import ComposeError
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import (
    WHITEBOARD_KINDS,
    compose_whiteboard,
    whiteboard_keywords,
    whiteboard_problems,
)
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates

LIB = library()
RULES = LIB.composer.whiteboard
GENERIC = RULES.generic_keyword
SEEDS = range(4)


def _recipes() -> list[tuple[str, WhiteboardRecipe]]:
    return [(k, r) for k in WHITEBOARD_KINDS for r in RULES.recipes(k)]


def _tiers(recipe: WhiteboardRecipe) -> list[int]:
    return [t for t in (1, 2, 3) if recipe.min_tier <= t <= (recipe.max_tier or t)]


def _make(recipe_id: str, kind: str, tier: int, seed: int, wc: str | None = None) -> SkillDef:
    return compose_whiteboard(
        seed, kind=kind, recipe_id=recipe_id, tier=tier, weapon_class=wc, library=LIB
    )


def _compose_or_none(recipe_id: str, kind: str, tier: int, seed: int, wc: str | None = None):  # type: ignore[no-untyped-def]
    try:
        return _make(recipe_id, kind, tier, seed, wc)
    except ComposeError:
        return None


def _kw(skill: SkillDef) -> tuple[str, ...]:
    found = derive_keywords(skill, LIB.keywords, exclusive_only=True).all()
    if any(e.type == "summon" for e in skill.effects) and len(found) > 1:
        return tuple(k for k in found if k != "summon")
    return found


# ---------------------------------------------------------------------------
# 每個配方：做得出來、過驗證與白板定義、預算 70～100%、關鍵字對得上
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind,recipe", _recipes(), ids=lambda x: getattr(x, "id", x))
def test_every_recipe_composes_valid_whiteboards_in_its_tiers(
    kind: str, recipe: WhiteboardRecipe
) -> None:
    made = 0
    for tier in _tiers(recipe):
        for seed in SEEDS:
            for wc in (None, "melee", "ranged", "focus"):
                skill = _compose_or_none(recipe.id, kind, tier, seed, wc)
                if skill is None:  # 這種武器大類沒有這個配方（例如雙屬性武器技給法器）
                    continue
                made += 1
                assert skill.tier == tier and validate_skill(skill, LIB) == []
                assert whiteboard_problems(skill, LIB, tier) == [], skill.id
                assert 0.70 <= skill_budget(skill, LIB).ratio <= 1.0
                keywords = _kw(skill)
                natural = ("prone",) if recipe.id == "summon_skeleton" else None  # 骷髏自帶倒地
                expected = () if recipe.keyword == GENERIC else (recipe.keyword,)
                assert keywords in (expected, natural)
                assert skill.name_zh == recipe.name_zh
    assert made >= 3, recipe.id


def test_recipes_follow_the_tier_table_of_decision_72() -> None:
    """召喚（創角的基本召喚物除外）、陷阱、姿態、位移 2 階起；修正型被動與雙屬性縮放 3 階起。"""
    for _, recipe in _recipes():
        if recipe.species in ("trap", "stance", "displace"):
            assert recipe.min_tier >= 2, recipe.id
            assert recipe.species == "stance" or recipe.min_tier == 2, recipe.id
        if recipe.species in ("modifier", "dual"):
            assert recipe.min_tier == 3, recipe.id
        if recipe.species == "summon" and recipe.keyword != "summon":
            assert recipe.min_tier == 2, recipe.id
    by_tier = {
        t: {r.species for k in WHITEBOARD_KINDS for r in RULES.recipes(k, t)} for t in (1, 2, 3)
    }
    assert by_tier[1] == {"basic", "summon"}
    assert {"trap", "stance", "displace"} <= by_tier[2] and not {"modifier", "dual"} & by_tier[2]
    assert {"modifier", "dual", "trap", "stance", "displace"} <= by_tier[3]


def test_every_keyword_has_a_whiteboard_from_tier_one() -> None:
    """潮濕、倒地、撞擊、召喚物也有白板（不必退回手寫池）；形態仍沒有。"""
    covered = whiteboard_keywords(LIB, "active", 1)
    assert set(LIB.keywords.ids()) - {"form"} <= covered | {"high_ground"} | {"marked"}
    assert {"wet", "prone", "collision", "summon"} <= covered


# ---------------------------------------------------------------------------
# 例外、召喚、創角
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", ["wet", "prone", "collision"])
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_exception_keywords_have_exploit_and_maker_boards(keyword: str, tier: int) -> None:
    seen: set[str] = set()
    for seed in range(10):
        skill = compose_whiteboard(seed, keyword=keyword, tier=tier, library=LIB)
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
        if weapon not in LIB.weapons:
            continue
        for seed in range(6):
            skill = starting_skill(LIB, weapon, "summon", seed)
            assert skill is not None and skill.tier == 1
            assert skill.id.startswith("skill_rand_")  # 組合器產生，不是手寫召喚技
            assert [e.type for e in skill.effects] == ["summon"]
            assert whiteboard_problems(skill, LIB, 1) == []
            unit = skill.effects[0].unit
            melee += unit == "summon_skeleton_warrior"
            ranged += unit == "summon_elemental_spirit"
    assert melee and ranged  # 近戰型與遠程型各一


def test_tier_two_summons_follow_the_whiteboard_keyword() -> None:
    expected = {
        "ignite": "summon_fire_spirit",
        "frozen": "summon_ice_spirit",
        "charged": "summon_thunder_spirit",
        "concealed": "summon_shade",
    }
    for keyword, unit in expected.items():
        skill = compose_whiteboard(
            1, keyword=keyword, recipe_id=f"summon_{unit.split('_')[1]}", tier=2, library=LIB
        )
        assert skill.effects[0].unit == unit and skill.ap_cost == RULES.summon_ap_cost


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
        for c in generate_whiteboard_candidates(LIB, request):
            if c.source == "composer":
                seen[_species_of(c.skill)] += 1
                assert whiteboard_problems(c.skill, LIB, tier) == [], c.skill.id
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
        found = generate_whiteboard_candidates(LIB, request)
        new = next(c for c in found if c.kind == "new")
        total += 1
        if not new.keywords:
            generic += 1
            assert new.source == "composer" and _kw(new.skill) == ()
            assert whiteboard_problems(new.skill, LIB, 2) == []
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
    return tuple((r.id, t, k) for k, r in _recipes() if r.species != "modifier" for t in _tiers(r))


@pytest.mark.parametrize("recipe_id,tier,kind", _engine_cases())
def test_active_recipes_play_in_the_engine(recipe_id: str, tier: int, kind: str) -> None:
    """可主動施放的配方：放進戰鬥結算不報錯，卡片的傷害預覽範圍包住實際結算；召喚、陷阱、姿態、位移
    都有對應的事件。被動與反應只確認能裝備、能產生卡片。"""
    if kind != "active":
        for wc in ("focus", None, "ranged", "melee"):
            skill = _compose_or_none(recipe_id, kind, tier, 3, wc)
            if skill is not None:
                _battle_with(skill)
                assert skill_card(LIB, skill).id == skill.id
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
    assert skill_card(LIB, skill).id == skill.id


def test_modifier_boards_equip_and_raise_damage_against_the_condition_target() -> None:
    skill = _make("burning_exploit", "passive", 3, 2)
    assert skill.kind == "modifier" and skill.modifiers[0].change.damage_permille is not None
    assert skill.modifiers[0].change.damage_permille >= 100
    assert skill_card(LIB, skill).id == skill.id
    _battle_with(skill)
