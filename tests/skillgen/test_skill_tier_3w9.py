"""Phase 3W-9：技能預算用角色階級——最低角色階級表、驗證器門檻、稀有度標記、升階重算的行為一致
（卡片數字＝實戰、預算比例在窗內、預算分數不低於升階前）。"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

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
from trpg.content.skill_rules import RetierGrowthRules
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import DamageDealt
from trpg.engine.preview import preview
from trpg.narrative.skills import skill_card
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import at_role_tier
from trpg.skillgen.flash_offer import FlashRequest, make_offer
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.skill_tier import character_tier, retier, retier_report
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import (
    minimum_tier,
    structural_rarity,
    tier_requirements,
    tier_violations,
    validate_skill,
)
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()


def _fresh(skill: SkillDef, **update: object) -> SkillDef:
    """當成「從零產生」的技能（組合器、白板、LLM 的來源；手寫內容不受階級限制）。"""
    provenance = skill.provenance.model_copy(update={"origin": "level_up", "parents": ()})
    return skill.model_copy(update={"provenance": provenance, **update})


# ---------------------------------------------------------------------------
# 最低角色階級表（06 6.34.9）：每階至少各抽幾個
# ---------------------------------------------------------------------------

TABLE = {
    # 3 階：修正型被動、雙屬性縮放、連鎖跳躍、影響 7 格以上的地形
    "skill_attack_mastery": 3,
    "skill_arcane_blade": 3,
    "skill_chain_lightning": 3,
    "skill_earth_collapse": 3,
    # 2 階：召喚、陷阱、姿態、自身位移或互換、3×3、接續段、4～6 格地形
    "skill_summon_war_wolf": 2,  # BAL-19c：基本召喚物（元素之靈、骷髏）1 階，見下面的測試
    "skill_cinder_mine": 2,
    "skill_bulwark_stance": 2,
    "skill_blink": 2,
    "skill_decoy_swap": 2,
    "skill_poison_mist": 2,
    "skill_armor_break_combo": 2,
    "skill_sinkhole": 2,
    # 1 階：其餘（單體傷害＋狀態）
    "skill_fire_bolt": 1,
}


@pytest.mark.parametrize(("skill_id", "tier"), sorted(TABLE.items()))
def test_minimum_tier_follows_the_table(skill_id: str, tier: int) -> None:
    assert minimum_tier(LIB.skills[skill_id], LIB) == tier, tier_requirements(
        LIB.skills[skill_id], LIB
    )


def test_tier_one_covers_push_surface_blow_shockwave_conditions_passives_and_reactions() -> None:
    """推拉、表面、吹送、震波、條件、觸發型被動、反應都是 1 階就有。"""
    found: set[str] = set()
    for skill in LIB.skills.values():
        if minimum_tier(skill, LIB) != 1:
            continue
        types = {e.type for e in skill.effects}
        found |= types & {"push", "pull", "create_surface", "blow_surface", "shockwave"}
        if skill.condition is not None or any(e.condition is not None for e in skill.effects):
            found.add("condition")
        if skill.kind in ("passive", "reaction"):
            found.add(skill.kind)
    assert {"push", "pull", "create_surface", "blow_surface", "shockwave"} <= found
    assert {"condition", "passive", "reaction"} <= found


def test_a_six_long_line_needs_tier_three() -> None:
    line = next(s for s in LIB.skills.values() if s.shape.type == "line" and s.followup is None)
    long_line = line.model_copy(update={"shape": line.shape.model_copy(update={"size": 6})})
    short_line = line.model_copy(update={"shape": line.shape.model_copy(update={"size": 5})})
    assert minimum_tier(long_line, LIB) == 3
    assert all(n.rule != "line" for n in tier_requirements(short_line, LIB))


def test_the_table_lives_in_content() -> None:
    table = LIB.budget.min_character_tier
    assert table.primitives["summon"] == 2 and table.shapes["square3"] == 2
    assert table.kinds["modifier"] == 3 and table.shapes["chain"] == 3
    assert "push" not in table.primitives and "create_surface" not in table.primitives
    assert [(t.min_cells, t.tier) for t in table.terrain_area] == [(4, 2), (7, 3)]


# ---------------------------------------------------------------------------
# 驗證器：只擋「從零產生」的技能；手寫、創角、由既有技能推出來的不擋
# ---------------------------------------------------------------------------


def test_the_validator_gates_fresh_skills_by_their_tier() -> None:
    summon = LIB.skills["skill_summon_war_wolf"]
    assert validate_skill(summon, LIB) == []  # 手寫內容保留原本的階級與內容
    fresh = _fresh(summon)
    assert {v.rule for v in tier_violations(fresh, LIB)} == {"tier.skeleton", "tier.primitive"}
    assert "tier.primitive" in {v.rule for v in validate_skill(fresh, LIB)}
    assert tier_violations(fresh, LIB, 2) == []
    starter = fresh.model_copy(
        update={"provenance": fresh.provenance.model_copy(update={"origin": "starter"})}
    )
    assert tier_violations(starter, LIB) == []  # 創角例外
    derived = fresh.model_copy(
        update={"provenance": fresh.provenance.model_copy(update={"parents": (summon.id,)})}
    )
    assert tier_violations(derived, LIB) == []  # 閃現、轉型、進化：結構保留


def test_rarity_is_only_a_marker() -> None:
    """稀有度不擋（普通的召喚技在 2 階也合法），標記由結構自動算。"""
    summon = _fresh(LIB.skills["skill_summon_war_wolf"], rarity="common")
    assert not [v for v in tier_violations(summon, LIB, 2) if v.rule.startswith("rarity")]
    assert not any(v.rule.startswith("rarity") for v in validate_skill(summon, LIB))
    assert structural_rarity(summon, LIB) == "rare"
    assert structural_rarity(LIB.skills["skill_fire_bolt"], LIB) == "common"


def test_creation_whiteboard_is_exempt_but_offers_are_not() -> None:
    board = compose_whiteboard(1, keyword="summon", tier=1, library=LIB, starter=True)
    assert board.provenance.origin == "starter" and validate_skill(board, LIB) == []
    # 依關鍵字挑的召喚物（點燃 → 火靈）三選一仍 2 階起
    with pytest.raises(Exception, match="白板"):
        compose_whiteboard(1, keyword="ignite", tier=1, library=LIB, recipe_id="summon_fire")
    # BAL-19f 追加：召喚物關鍵字另有號令型武器技白板，法器只會拿到召喚白板
    board = compose_whiteboard(1, keyword="summon", tier=2, library=LIB, weapon_class="focus")
    assert board.effects[0].type == "summon"


def test_basic_summons_open_tier_one_offers() -> None:
    """BAL-19c（#110，06 6.27.4「開放 1 階召喚白板」）：只召喚 1 隻基本召喚物（元素之靈、骷髏戰士）
    時召喚原語與骨架 1 階；其他召喚物、一次 2 隻的仍 2 階。"""
    assert LIB.budget.min_character_tier.basic_summon_units == (
        "summon_elemental_spirit",
        "summon_skeleton_warrior",
    )
    units = set()
    for seed in range(12):
        board = compose_whiteboard(  # BAL-19f 追加：號令型武器技白板不給法器
            seed, keyword="summon", tier=1, library=LIB, weapon_class="focus"
        )
        assert board.provenance.origin == "level_up" and validate_skill(board, LIB) == []
        assert tier_violations(board, LIB) == [] and board.tier == 1
        units.add(board.effects[0].unit)
    assert units == {"summon_elemental_spirit"}  # 骷髏也推導成倒地，選「召喚物」時給元素之靈
    skeleton = compose_whiteboard(3, tier=1, library=LIB, recipe_id="summon_skeleton")
    assert (
        skeleton.effects[0].unit == "summon_skeleton_warrior"
        and validate_skill(skeleton, LIB) == []
    )
    spirit = _fresh(LIB.skills["skill_summon_spirit"])
    assert minimum_tier(spirit, LIB) == 1 and tier_violations(spirit, LIB) == []
    effect = spirit.effects[0]
    pair = spirit.model_copy(
        update={"effects": (effect.model_copy(update={"count": 2, "power_permille": 600}),)}
    )
    assert minimum_tier(pair, LIB) == 2
    wolf = spirit.model_copy(
        update={"effects": (effect.model_copy(update={"unit": "summon_war_wolf"}),)}
    )
    assert {v.rule for v in tier_violations(wolf, LIB)} == {"tier.skeleton", "tier.primitive"}


# ---------------------------------------------------------------------------
# 升階重算：同一招在 1／2／3 階
# ---------------------------------------------------------------------------

DAMAGE_RECIPES = ("fire_bolt", "lightning_bolt", "frost_shard", "shadow_bolt", "fire_burst")


def _ladder(recipe: str, seed: int, weapon_class: str | None = None) -> list[SkillDef]:
    first = compose_whiteboard(
        seed, recipe_id=recipe, tier=1, library=LIB, weapon_class=weapon_class
    )
    second = retier(LIB, first, 2)
    return [first, second, retier(LIB, second, 3)]


@pytest.mark.parametrize("recipe", DAMAGE_RECIPES)
def test_retier_keeps_structure_window_and_power(recipe: str) -> None:
    for seed in range(3):
        ladder = _ladder(recipe, seed)
        for tier, skill in enumerate(ladder, start=1):
            assert skill.tier == tier
            assert skill.id == ladder[0].id and skill.name_zh == ladder[0].name_zh
            assert [e.type for e in skill.effects] == [e.type for e in ladder[0].effects]
            assert skill.shape.type == ladder[0].shape.type
            assert skill_budget(skill, LIB).ok, (recipe, seed, tier)
            assert validate_skill(skill, LIB) == []
        powers = [budget_power(s, LIB) for s in ladder]
        assert powers == sorted(powers) and powers[0] < powers[2], powers


def test_retier_grows_the_dice_like_the_design_example() -> None:
    """6.34.9 的例子：1 階白板 1d6，角色到 2 階後約 1d10——升階後的骰子平均變大。"""
    grew = 0
    for seed in range(6):
        low, high, _ = _ladder("fire_bolt", seed, "focus")
        assert high.effects[0].dice is not None and low.effects[0].dice is not None
        grew += high.effects[0].dice != low.effects[0].dice
    assert grew


def test_retier_is_deterministic_and_same_tier_is_identity() -> None:
    first = compose_whiteboard(4, recipe_id="fire_bolt", tier=1, library=LIB)
    assert retier(LIB, first, 1) is first
    assert retier(LIB, first, 2) == retier(LIB, first, 2)


@pytest.mark.parametrize("tier", [2, 3])
def test_terrain_skills_pass_the_budget_floor_at_higher_tiers(tier: int) -> None:
    """升降地形的點數固定：2／3 階先放大格數（3W-9b），再靠費用或「地形＋落石」配進窗內。"""
    sources = [
        LIB.skills[s] for s in ("skill_sinkhole", "skill_raise_perch", "skill_earth_collapse")
    ]
    sources.append(compose_whiteboard(2, keyword="high_ground", tier=1, library=LIB))
    for skill in sources:
        done = retier(LIB, skill, tier)
        report = retier_report(LIB, skill, done)
        assert report.in_window and not report.problems, (skill.id, float(report.ratio))
        assert report.after >= report.before
        assert any(e.type in ("raise_terrain", "lower_terrain") for e in done.effects)


def test_retier_report_flags_structures_that_cannot_keep_up() -> None:
    """沒有放大旋鈕時（3W-9b 的 ``retier_growth`` 清空），純狀態的白板（淬毒）點數追不上 3 階：數值
    推到最大，標成不在窗內，分數仍不低於升階前。"""
    lib = replace(LIB, budget=LIB.budget.model_copy(update={"retier_growth": RetierGrowthRules()}))
    venom = compose_whiteboard(0, recipe_id="venom", tier=1, library=lib)
    done = retier(lib, venom, 3)
    report = retier_report(lib, venom, done)
    assert not report.in_window and report.after >= report.before


def test_card_numbers_equal_the_engine_at_every_tier() -> None:
    """同一招在 1／2／3 階：卡片上的骰子就是規則包裡的骰子，預覽範圍包含實際傷害。"""
    for skill in _ladder("fire_bolt", 1, "focus"):
        dice = skill.effects[0].dice
        assert dice is not None
        assert any(str(dice) in line for line in skill_card(LIB, skill).effects)
        rules = LIB.ruleset.with_skills([skill])
        assert rules.skills.by_id()[skill.id] == skill
        m = make_map("\n".join(["000000"] * 6), ally=[(0, 0)], enemy=[(3, 0)])
        spawns = [
            spawn(Team.ALLY, (0, 0), caster_template([skill])),
            spawn(Team.ENEMY, (3, 0), no_reactions()),
        ]
        battle = give_turn(make_state(m, spawns, skills=[skill]), "unit_0001")
        target = UnitId("unit_0002")
        action = next(
            a
            for a in legal_actions(battle)
            if isinstance(a, UseSkill) and a.skill_id == skill.id and a.target_id == target
        )
        seen = preview(battle, action)
        dealt = [
            e
            for e in resolve(battle, action).events
            if isinstance(e, DamageDealt) and e.target_id == target
        ]
        if dealt and seen.damage is not None and not dealt[0].crit:
            assert seen.damage.minimum <= dealt[0].amount <= seen.damage.maximum


# ---------------------------------------------------------------------------
# 同源：角色階級一個函式；閃現出題用重配後的技能
# ---------------------------------------------------------------------------


def test_character_tier_is_the_roguelite_table() -> None:
    table = LIB.roguelite.offer_tier_by_level
    assert [character_tier(LIB, level) for level in range(1, len(table) + 1)] == list(table)


def test_flash_offers_start_from_the_retiered_skill() -> None:
    """閃現出題時，技能先照角色階級重配；選項的分數不低於重配後的技能（強度下限）。"""
    base = compose_whiteboard(3, recipe_id="fire_bolt", tier=1, library=LIB)
    start = at_role_tier(LIB, base, 2)
    assert start == retier(LIB, base, 2)
    state = acquire(base.id).model_copy(update={"used": True})
    offer = make_offer(LIB, FlashRequest(base, state, SkillUsage(), 7, tier=2))
    assert offer.options
    floor = budget_power(start, LIB)
    for option in offer.options:
        assert option.skill.tier == 2
        if option.variation.source != "transform":
            assert budget_power(option.skill, LIB) >= floor
    assert all(skill_budget(o.skill, LIB).ratio >= Fraction(7, 10) for o in offer.options)
