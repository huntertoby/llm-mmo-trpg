"""Phase 3W-2：閃現的小變化模板（13 類）——登錄、預算比例、強度下限、角色階級、用法統計排序、
重閃下限、完整技能調整欄、行為一致（卡片＝實戰）、同種子同選項。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
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
from trpg.content.skills import ModifierSpec, ShapeSpec, SkillDef
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import DamageDealt
from trpg.engine.preview import preview
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import (
    apply_variation,
    at_role_tier,
    at_tier,
    derive_chain,
    derive_skill,
)
from trpg.skillgen.flash_offer import FlashRequest, UsageSource, choose, make_offer
from trpg.skillgen.flash_state import COMPLETE_SLOT, Variation, acquire
from trpg.skillgen.flash_trade import MINOR_OPS
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

SEED = 11
TIER = 3
"""代表性測試用最高角色階級（所有模板都開放）。"""
BONUS = 40

# 6.34.4 的十三類（模板 op 家族）：一個都不能少
FAMILIES = {
    "area",
    "range",
    "reshape",
    "multi_hit",
    "followup",
    "element",
    "keyword_imbue",
    "keyword_exploit",
    "extend",
    "kill_refund",
    "charge",
    "light",
    "potency",
}
TRIGGER_OPS = {"trigger_range", "trigger_cap"}
MODIFIER_OPS = {"mod_potency", "mod_range", "mod_keyword", "mod_relax"}


@dataclass(frozen=True)
class Found:
    skill: SkillDef
    variation: Variation
    result: SkillDef

    @property
    def playable(self) -> SkillDef:
        """換成新 ID 的結果（套用變化的結果沿用原 ID，要放進規則包得先換 ID）。"""
        return _renamed(self.result)


def _renamed(skill: SkillDef) -> SkillDef:
    return skill.model_copy(update={"id": f"{skill.id}_fl_test"})


def _minor_ids() -> list[str]:
    return [t.id for t in library().flash.minor]


def _used(skill_id: str):  # type: ignore[no-untyped-def]
    return acquire(skill_id).model_copy(update={"used": True})


@cache
def _pool() -> tuple[SkillDef, ...]:
    """手寫技能（依 ID 排序），後面接 3 招轉型出來的元素姿態（3W-2b：沒有手寫的元素姿態）。"""
    lib = library()
    plain = sorted(lib.skills.values(), key=lambda s: s.id)
    transform = Variation(source="transform", template="to_stance", category="transform")
    stances: list[SkillDef] = []
    for base in ("skill_fire_bolt", "skill_scholars_bolt", "skill_cluster_bolt"):
        if base not in lib.skills:
            continue
        done = apply_variation(
            lib, at_tier(lib.skills[base], TIER), transform, bonus=120, rng=Rng(SEED)
        )
        if done is not None:
            stances.append(done.model_copy(update={"id": f"{base}_stance_test"}))
    # 3W-2b：地形變化需要影響格數比較小的升降地形技能（內容裡的都是十字以上）
    small = lib.skills["skill_sinkhole"].model_copy(
        update={
            "id": "skill_sinkhole_small_test",
            "shape": ShapeSpec.model_validate({"type": "ground_tile", "range": 4}),
        }
    )
    return (*plain, *stances, small, *_bal10b_fixtures(), *_bal10e_fixtures())


def _bal10b_fixtures() -> tuple[SkillDef, ...]:
    """BAL-10b：內容裡沒有的結構——有進入冷卻的變身姿態（進入代價 −1）、命中後冷卻 −1 搭配一條傷害
    加成的修正型被動（冷卻 −1 → −2 時傷害可以往下補）。"""
    lib = library()
    bear = lib.skills["skill_form_bear"]
    form = bear.effects[0].model_copy(update={"magnitude_permille": 1400})
    cooled = bear.model_copy(
        update={
            "id": "skill_form_bear_cooled_test",
            "cost": bear.cost.model_copy(update={"cooldown": 2}),
            "effects": (form,),
        }
    )
    ember = lib.skills["skill_ember_cycle"]
    rules = [
        ModifierSpec.model_validate(
            {
                "applies_to": {"skill_tags": ["fire"]},
                "condition": ember.modifiers[0].condition.model_dump(mode="json", exclude_none=True)
                if ember.modifiers[0].condition is not None
                else None,
                "change": {"cooldown_delta": -1},
            }
        ),
        ModifierSpec.model_validate(
            {"applies_to": {"skill_tags": ["fire"]}, "change": {"damage_permille": 200}}
        ),
    ]
    paired = ember.model_copy(
        update={"id": "skill_ember_cycle_paired_test", "modifiers": tuple(rules)}
    )
    return cooled, paired


def _bal10e_fixtures() -> tuple[SkillDef, ...]:
    """BAL-10e：收回家族要先有「可以收回的部分」——內容裡沒有的結構由閃現先做出來：多段同元素
    傷害（連打）、一次召喚 2 隻（雙生）、觸發距離上限 2 的被動、兩條規則（多一條範圍 +1）的修正型
    被動。"""
    lib = library()
    out: list[SkillDef] = []
    steps = (
        ("skill_fire_bolt", Variation(source="minor", template="multi_hit", category="combo")),
        (
            "skill_summon_spirit",
            Variation(source="major", template="summon_count", category="deepen"),
        ),
        (
            "skill_thorn_skin",
            Variation(source="minor", template="trigger_range", category="trigger"),
        ),
        ("skill_war_avatar", Variation(source="minor", template="mod_range", category="modifier")),
    )
    for base, variation in steps:
        major = variation.source == "major"  # 雙生是第 3 次的大變化（3 階做不出來，先在 2 階做）
        skill = at_tier(lib.skills[base], TIER - 1 if major else TIER)
        bonus = 3 * BONUS if major else BONUS
        done = apply_variation(lib, skill, variation, bonus=bonus, rng=Rng(SEED))
        assert done is not None, (base, variation.template)
        renamed = {"id": f"{base}_bal10e_test", "budget_bonus_permille": None}
        out.append(done.model_copy(update=renamed))
    return tuple(out)


@cache
def _found(template_id: str) -> tuple[Found, ...]:
    """這個模板在 3 招代表性技能（技能 ID 排序後第一批套得上的）上的結果。"""
    lib = library()
    source = UsageSource()
    out: list[Found] = []
    for plain in _pool():
        if len(out) >= 3:
            break
        skill = at_tier(plain, TIER)
        request = FlashRequest(skill, acquire(skill.id), SkillUsage(), SEED, tier=TIER)
        for category in lib.flash.stage_categories("minor"):
            for var in source.ranked(lib, request, category.id, skill):
                if var.template != template_id:
                    continue
                got = apply_variation(lib, skill, var, bonus=BONUS, rng=Rng(SEED).fork(var.key()))
                if got is not None:
                    out.append(Found(skill, var, got))
                    break
            else:
                continue
            break
    return tuple(out)


# ---------------------------------------------------------------------------
# 登錄
# ---------------------------------------------------------------------------


def test_the_thirteen_families_are_all_in_the_data_and_registered() -> None:
    ops = {t.op for t in library().flash.minor}
    assert ops >= FAMILIES, FAMILIES - ops
    assert ops >= TRIGGER_OPS
    assert ops >= MODIFIER_OPS
    assert ops <= set(MINOR_OPS), ops - set(MINOR_OPS)


@pytest.mark.parametrize("template_id", _minor_ids())
def test_every_template_has_representative_skills(template_id: str) -> None:
    assert len(_found(template_id)) >= 1, f"{template_id} 沒有任何技能套得上"


# ---------------------------------------------------------------------------
# 預算比例、強度下限、6.6 硬上限
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_id", _minor_ids())
def test_template_result_is_valid_in_budget_and_never_weaker(template_id: str) -> None:
    lib = library()
    for item in _found(template_id):
        got = item.result
        assert validate_skill(got, lib) == [], (template_id, item.skill.id)  # 含 6.6 硬上限
        report = skill_budget(got, lib)
        assert report.ok, (template_id, item.skill.id, float(report.ratio))
        assert report.bonus_permille == BONUS
        before = budget_power(at_tier(item.skill, TIER), lib)
        assert budget_power(got, lib) >= before, (template_id, item.skill.id)
        assert (got.kind, got.tier) == (item.skill.kind, item.skill.tier)
        playable = _renamed(got)
        assert lib.ruleset.with_skills([playable]).skills.by_id()[playable.id] == playable
        assert skill_card(lib, got).id == got.id


@pytest.mark.parametrize(
    "template_id", ["support_potency", "trigger_potency", "mod_potency", "followup_potency"]
)
def test_effect_plus_templates_are_strictly_stronger(template_id: str) -> None:
    lib = library()
    items = _found(template_id)
    assert items
    for item in items:
        assert budget_power(item.result, lib) > budget_power(at_tier(item.skill, TIER), lib)


def test_range_plus_is_one_farther_and_may_lower_a_die() -> None:
    lib = library()
    item = _found("range_plus")[0]
    assert item.result.shape.range == item.skill.shape.range + 1  # type: ignore[operator]
    # 預算分數不低於變化前，但個別數字可以變小：只檢查沒有違反強度下限
    assert budget_power(item.result, lib) >= budget_power(at_tier(item.skill, TIER), lib)


def test_structural_templates_change_the_structure() -> None:
    lib = library()
    assert (
        len(_found("multi_hit")[0].result.effects) == len(_found("multi_hit")[0].skill.effects) + 1
    )
    assert _found("followup_hit")[0].result.followup is not None
    second = _found("element_second")[0]
    elements = {e.element for e in second.result.effects if e.element is not None}
    assert len(elements) >= 2
    assert any(e.on_kill for e in _found("kill_refund")[0].result.effects)
    charge = _found("cost_charge")[0]
    assert (charge.result.cost.cooldown or 0) > (charge.skill.cost.cooldown or 0)
    assert (charge.result.cost.cooldown or 0) <= 5
    light = _found("cost_light")[0]
    assert (light.result.ap_cost or 0) == (light.skill.ap_cost or 0) - 1
    assert (
        light.result.cost.cooldown or 0
    ) <= 1 or light.result.cost.cooldown == light.skill.cost.cooldown
    for template in ("reshape_square3", "reshape_line6", "reshape_chain"):
        item = _found(template)[0]
        assert item.result.shape.type == item.variation.shape.type  # type: ignore[union-attr]
    assert _found("dual_scaling")[0].result.secondary_scaling_attr is not None
    cap = _found("trigger_cap")[0]
    assert cap.result.trigger.max_per_round == cap.skill.trigger.max_per_round + 1  # type: ignore[union-attr]
    assert lib.flash.minor_template("cost_light") is not None


# ---------------------------------------------------------------------------
# 角色階級
# ---------------------------------------------------------------------------

TIER_TWO = {
    "reshape_square3",
    "followup_hit",
    "element_second",
    "followup_element",
    "support_area_wide",
    "trigger_range_wide",
    "terrain_mid",
}
TIER_THREE = {"reshape_line6", "reshape_chain", "dual_scaling", "terrain_wide"}


def test_template_min_tiers_follow_decision_72() -> None:
    table = library().flash
    tiers = {t.id: t.min_tier for t in table.minor}
    assert all(tiers[t] == 2 for t in TIER_TWO)
    assert all(tiers[t] == 3 for t in TIER_THREE)
    assert all(v == 1 for k, v in tiers.items() if k not in TIER_TWO | TIER_THREE)


@pytest.mark.parametrize("role_tier", [1, 2, 3])
def test_offers_only_use_templates_the_role_tier_allows(role_tier: int) -> None:
    lib = library()
    seen: set[str] = set()
    for skill in sorted(lib.skills.values(), key=lambda s: s.id)[:60]:
        if skill.kind not in ("active", "passive", "reaction", "modifier"):
            continue
        request = FlashRequest(skill, _used(skill.id), SkillUsage(), SEED, tier=role_tier)
        try:
            offer = make_offer(lib, request)
        except ValueError:
            continue
        for option in offer.options:
            template = lib.flash.minor_template(option.variation.template)
            assert template is not None and template.min_tier <= role_tier
            assert option.skill.tier == role_tier  # 預算用傳進來的階級
            seen.add(template.id)
    assert seen
    if role_tier == 1:
        assert not seen & (TIER_TWO | TIER_THREE)
    if role_tier == 3:
        assert seen & (TIER_TWO | TIER_THREE)


def test_same_seed_same_tier_same_offer() -> None:
    lib = library()
    skill = lib.skills["skill_fire_bolt"]
    one = make_offer(lib, FlashRequest(skill, _used(skill.id), SkillUsage(), SEED, tier=2))
    two = make_offer(lib, FlashRequest(skill, _used(skill.id), SkillUsage(), SEED, tier=2))
    assert one == two
    assert one.model_dump_json() == two.model_dump_json()


# ---------------------------------------------------------------------------
# 用法統計排序
# ---------------------------------------------------------------------------


def _ranked(skill_id: str, category: str, usage: SkillUsage, tier: int = 3) -> list[str]:
    lib = library()
    skill = at_tier(lib.skills[skill_id], tier)
    request = FlashRequest(skill, acquire(skill_id), usage, SEED, tier=tier)
    return [v.template for v in UsageSource().ranked(lib, request, category, skill)]


def test_sparse_usage_offers_generic_variations_first() -> None:
    order = _ranked("skill_fire_bolt", "area", SkillUsage(uses=1))
    generic = {t.id for t in library().flash.minor if t.generic}
    assert order[0] in generic


def test_usage_statistics_reorder_a_category() -> None:
    far = SkillUsage(uses=10, targets=10, distance=60)  # 平均目標 1、距離 6
    crowd = SkillUsage(uses=10, targets=30, distance=20)  # 平均目標 3
    assert _ranked("skill_fire_bolt", "area", far)[0] == "range_plus"
    assert _ranked("skill_fire_bolt", "area", crowd)[0] == "area_plus"
    killer = SkillUsage(uses=10, targets=10, distance=10, kills=4)
    assert _ranked("skill_fire_bolt", "extend", killer)[0] == "kill_refund"
    quiet = SkillUsage(uses=10, targets=10, distance=10)
    assert _ranked("skill_fire_bolt", "extend", quiet)[0] != "kill_refund"


def test_keyword_variations_follow_the_usage_signal() -> None:
    usage = SkillUsage(uses=10, targets=10, distance=10, target_keywords={"wet": 8})
    lib = library()
    skill = lib.skills["skill_fire_bolt"]
    request = FlashRequest(skill, acquire(skill.id), usage, SEED, tier=TIER)
    ranked = UsageSource().ranked(lib, request, "element", skill)
    first = next(v for v in ranked if v.template in ("keyword_exploit", "keyword_imbue"))
    assert (first.template, first.keyword) == ("keyword_exploit", "wet")


# ---------------------------------------------------------------------------
# 強度下限：一路閃、重閃、完整技能
# ---------------------------------------------------------------------------


def _walk_powers(skill_id: str, picks: int, tier: int = 2) -> list[Fraction]:
    lib = library()
    base = lib.skills[skill_id]
    state = _used(skill_id)
    powers = [budget_power(at_role_tier(lib, base, tier), lib)]
    for _ in range(picks):
        offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, tier=tier))
        if not offer.options:  # 模板有限：被動、反應可能不到 5 次就沒有合格的變化
            break
        state, skill = choose(state, offer, 0)
        state = state.model_copy(update={"used": True})
        report = skill_budget(skill, lib)
        assert report.ok, (skill_id, float(report.ratio))
        assert validate_skill(skill, lib) == []
        powers.append(budget_power(skill, lib))
    return powers


@pytest.mark.parametrize(
    "skill_id", ["skill_fire_bolt", "skill_radiant_mend", "skill_ember_brand", "skill_reflex_ward"]
)
def test_power_never_drops_along_five_flashes(skill_id: str) -> None:
    # 3W-9：技能先照角色階級（2 階）的預算重配，起點就在預算窗內；被動模板較少，燃燒印記在 2 階
    # 起點較高、強度下限擋掉之後的選項，所以只要求至少閃 1 次（其餘至少 3 次）
    powers = _walk_powers(skill_id, 5)
    least = 2 if skill_id == "skill_ember_brand" else 4
    assert len(powers) >= least, powers
    assert powers == sorted(powers), powers


def test_reflash_keeps_the_replaced_power_as_floor() -> None:
    lib = library()
    base = lib.skills["skill_fire_bolt"]
    state = _used(base.id)
    for _ in range(3):
        offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, tier=2))
        state, _skill = choose(state, offer, 0)
        state = state.model_copy(update={"used": True})
    chain = derive_chain(lib, base, state, SEED, 2)
    old = budget_power(chain[0], lib)
    offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, slot=1, tier=2))
    assert offer.options
    assert all(o.floor_permille == math.ceil(old * 1000) for o in offer.options)
    moved, _skill = choose(state, offer, 0)
    assert moved.record(1).floor_permille == math.ceil(old * 1000)  # type: ignore[union-attr]
    new_chain = derive_chain(lib, base, moved, SEED, 2)
    assert budget_power(new_chain[0], lib) >= old
    assert [budget_power(s, lib) for s in new_chain] == sorted(
        budget_power(s, lib) for s in new_chain
    )
    assert derive_skill(lib, base, moved, SEED, 2) == derive_skill(lib, base, moved, SEED, 2)


def test_complete_skill_adjustment_is_not_weaker_and_replaces() -> None:
    lib = library()
    base = lib.skills["skill_fire_bolt"]
    rules = lib.flash.rules
    state = acquire(base.id, complete=True)
    start = budget_power(derive_skill(lib, base, state, SEED, 1), lib)
    offer = make_offer(
        lib, FlashRequest(base, state, SkillUsage(), SEED, slot=COMPLETE_SLOT, tier=1)
    )
    assert offer.options and offer.cost == 1
    state, first = choose(state, offer, 0)
    assert first.budget_bonus_permille == rules.complete.budget_permille
    assert budget_power(first, lib) >= start
    offer2 = make_offer(
        lib, FlashRequest(base, state, SkillUsage(), SEED, slot=COMPLETE_SLOT, tier=1)
    )
    state2, second = choose(state, offer2, 0)
    assert state2.adjustment is not None and state2.adjustment.reflashes == 1
    assert len(state2.records) == 0  # 換掉、不累積
    assert budget_power(second, lib) >= budget_power(first, lib)
    assert state2.spent == 2


# ---------------------------------------------------------------------------
# 沒有合格選項的類別
# ---------------------------------------------------------------------------


def test_a_focused_category_with_no_option_is_refused_before_paying() -> None:
    lib = library()
    # 只有一條「傷害獲得元素」的修正型被動：沒有幅度、條件、計數或代價可以動（BAL-10b 之後變身姿態
    # 的費用類改成合法，換這招）
    passive = lib.skills["skill_thunder_hand"]
    request = FlashRequest(passive, _used(passive.id), SkillUsage(), SEED, category="modifier")
    with pytest.raises(ValueError, match="沒有合格的變化"):
        make_offer(lib, request)


# ---------------------------------------------------------------------------
# 行為一致：卡片 ＝ 實戰
# ---------------------------------------------------------------------------


def _engine_check(found: Found) -> bool:
    """把套用後的技能放進戰鬥：卡片的傷害預覽範圍包住實際結算；回傳是否真的結算過。"""
    lib = library()
    skill = found.playable
    if skill.weapon_req in ("melee", "ranged"):  # 施放者是拿法器的法師
        return False
    m = make_map("\n".join(["000000000"] * 9), ally=[(0, 4)], enemy=[(2, 4), (3, 4), (3, 5)])
    spawns = [
        spawn(Team.ALLY, (0, 4), caster_template([skill])),
        spawn(Team.ENEMY, (2, 4), no_reactions()),
        spawn(Team.ENEMY, (3, 4), no_reactions()),
        spawn(Team.ENEMY, (3, 5), no_reactions()),
    ]
    battle = give_turn(make_state(m, spawns, skills=[skill]), "unit_0001")
    actions = [
        a for a in legal_actions(battle) if isinstance(a, UseSkill) and a.skill_id == skill.id
    ]
    if not actions:
        return False
    action = actions[0]
    seen = preview(battle, action)
    result = resolve(battle, action)  # 結算不報錯（形狀、目標、效果都合法）
    assert result.state is not None
    dealt = [e for e in result.events if isinstance(e, DamageDealt) and not e.crit]
    targeted = [e for e in dealt if e.target_id == action.target_id] if action.target_id else []
    if targeted and seen.damage is not None and len({e.target_id for e in dealt}) == 1:
        total = sum(e.amount for e in targeted)
        assert seen.damage.minimum <= total <= seen.damage.maximum, (skill.id, total)
    assert skill_card(lib, skill).id == skill.id
    return True


ENGINE_TEMPLATES = [
    "area_plus",
    "range_plus",
    "reshape_shape",
    "reshape_square3",
    "reshape_line6",
    "reshape_chain",
    "multi_hit",
    "followup_hit",
    "element_second",
    "keyword_imbue",
    "keyword_exploit",
    "extend_duration",
    "kill_refund",
    "cost_charge",
    "cost_light",
    "dual_scaling",
    "converge_single",
    "converge_step",
    "refine",
    "refine_merge",
]


def test_active_templates_play_in_the_engine() -> None:
    played = 0
    for template in ENGINE_TEMPLATES:
        for item in _found(template):
            if item.skill.kind == "active" and item.skill.followup is None:
                played += int(_engine_check(item))
    assert played >= 12


def test_preview_range_contains_resolved_damage_for_a_flashed_bolt() -> None:
    lib = library()
    base = lib.skills["skill_fire_bolt"]
    var = Variation(source="minor", template="multi_hit", category="combo")
    got = _renamed(apply_variation(lib, base, var, bonus=BONUS, rng=Rng(SEED)))  # type: ignore[arg-type]
    assert got is not None
    m = make_map("\n".join(["0000000"] * 7), ally=[(0, 0)], enemy=[(4, 0)])
    spawns = [
        spawn(Team.ALLY, (0, 0), caster_template([got])),
        spawn(Team.ENEMY, (4, 0), no_reactions()),
    ]
    battle = give_turn(make_state(m, spawns, skills=[got]), "unit_0001")
    action = next(
        a
        for a in legal_actions(battle)
        if isinstance(a, UseSkill) and a.skill_id == got.id and a.target_id == UnitId("unit_0002")
    )
    seen = preview(battle, action)
    result = resolve(battle, action)
    dealt = [e for e in result.events if isinstance(e, DamageDealt) and not e.crit]
    assert len(dealt) == 2  # 多打一下：同一目標兩段命中
    if seen.damage is not None:
        total = sum(e.amount for e in dealt)
        assert seen.damage.minimum <= total <= seen.damage.maximum
