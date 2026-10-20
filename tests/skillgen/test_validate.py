"""技能驗證器（Phase 2B-2 4.3–4.6；驗收 3–6）：每條規則至少一個「違規被拒」與一個「合格」測試。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from tests.skillgen.helpers import (
    lib,
    lib_with_rewrite_primitive,
    rules_of,
    skill,
    skill_raw,
    violations,
)
from trpg.content.skills import EffectSpec, SkillDef

DMG = {"type": "damage", "dice": "2d6", "element": "fire"}


def spell(**overrides: Any) -> SkillDef:
    """法術技（AP 2、T1、無代價）；預設 2d6 單體傷害。"""
    data: dict[str, Any] = {
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "shape": {"type": "single", "range": 4},
        "effects": [DMG],
        "cost": {"mana": 6, "cooldown": 2},
    }
    data.update(overrides)
    return skill(**data)


def variant(base_id: str, **overrides: Any) -> SkillDef:
    """以示範技能為底，覆寫欄位。"""
    data = lib().skills[base_id].model_dump(mode="json")
    data.update(overrides)
    return SkillDef.model_validate(data)


def only(s: SkillDef, prefix: str) -> list[str]:
    """違規代碼中以 ``prefix`` 開頭的。"""
    return sorted(r for r in rules_of(s) if r.startswith(prefix))


# ---------------------------------------------------------------------------
# 合格
# ---------------------------------------------------------------------------


def test_the_baseline_skill_is_valid() -> None:
    assert violations(skill()) == []


@pytest.mark.parametrize(
    "skill_id", sorted(lib().skills), ids=lambda sid: sid.removeprefix("skill_")
)
def test_every_demo_skill_passes_validation(skill_id: str) -> None:
    """驗收 6：全部示範技能（含 2B-1 的 4 個）通過驗證，且比例落在 70%–100%。"""
    assert violations(lib().skills[skill_id]) == []


# ---------------------------------------------------------------------------
# 預算區間（驗收 3）
# ---------------------------------------------------------------------------


def test_over_budget_is_rejected_with_the_ratio() -> None:
    found = violations(skill(effects=[{"type": "damage", "multiplier_permille": 3000}]))
    (over,) = [v for v in found if v.rule == "budget.over"]
    assert "超出預算" in over.message and "133.9%" in over.message  # 21 ÷ 15.68
    assert over.skill_id == "skill_test"


def test_too_weak_is_rejected_with_the_ratio() -> None:
    found = violations(skill(effects=[{"type": "damage", "multiplier_permille": 1000}]))
    (weak,) = [v for v in found if v.rule == "budget.weak"]
    assert "過弱" in weak.message and "44.6%" in weak.message  # 7 ÷ 15.68


def test_budget_boundaries_are_inclusive() -> None:
    """可用預算 15.68：×2.24 ＝ 15.68（比例剛好 100%）合格、×2.241 超出；
    ×1.568 ＝ 10.976（剛好 70%）合格、×1.567 過弱。"""

    def rules(permille: int) -> set[str]:
        return rules_of(skill(effects=[{"type": "damage", "multiplier_permille": permille}]))

    assert rules(2240) == set() and rules(1568) == set()
    assert rules(2241) == {"budget.over"} and rules(1567) == {"budget.weak"}


def test_unavailable_budget_is_reported() -> None:
    s = skill(effects=[{"type": "apply_status", "status": "shielded"}])
    assert "budget.unavailable" in rules_of(s)


def test_references_are_checked_first() -> None:
    s = skill(effects=[{"type": "apply_status", "status": "no_such_status"}])
    assert rules_of(s) == {"reference"}


# ---------------------------------------------------------------------------
# 4.3 硬性上限
# ---------------------------------------------------------------------------


def test_more_than_four_effects_are_rejected() -> None:
    five = tuple(EffectSpec(type="damage", multiplier_permille=500) for _ in range(5))
    assert "cap.effects" in rules_of(skill_raw(effects=five))
    four = tuple(EffectSpec(type="damage", multiplier_permille=500) for _ in range(4))
    assert "cap.effects" not in rules_of(skill_raw(effects=four))


def test_push_and_pull_are_capped_at_two_tiles() -> None:
    """推擊與拉扯 ≤ 2 格：由引用檢查（原語參數範圍 1–2，與 2A 載入時同一套）擋下。"""
    for kind in ("push", "pull"):
        far = skill_raw(effects=(EffectSpec(type=kind, distance=3),))
        (v,) = violations(far)
        assert v.rule == "reference" and "1–2" in v.message and "distance" in v.message
        for distance in (1, 2):
            near = skill_raw(effects=(EffectSpec(type=kind, distance=distance),))
            assert "reference" not in rules_of(near)


def test_weapon_req_must_be_a_broad_class() -> None:
    assert "cap.weapon_req" in rules_of(skill_raw(weapon_req="focus"))  # 武器技不能要求法器
    assert "cap.weapon_req" not in rules_of(skill_raw(weapon_req="ranged"))


def test_at_most_one_rule_rewrite_primitive() -> None:
    fake = lib_with_rewrite_primitive()
    two = skill_raw(  # 傳說另有「恰好 1 個核心」（Phase 3D-6，引用檢查），這裡用史詩
        rarity="epic",
        effects=(EffectSpec(type="fake_rewrite"), EffectSpec(type="fake_rewrite")),
        cost=skill().cost.model_copy(update={"uses_per_battle": 1}),
    )
    assert "cap.rule_rewrite" in rules_of(two, fake)
    one = two.model_copy(update={"effects": (EffectSpec(type="fake_rewrite"),)})
    assert "cap.rule_rewrite" not in rules_of(one, fake)


@pytest.mark.parametrize(
    ("cost", "rejected"),
    [
        ({"mana": 5}, True),  # 沒有次數限制也沒有冷卻
        ({"mana": 5, "cooldown": 3}, True),  # 冷卻不到 4
        ({"mana": 5, "uses_per_battle": 2}, True),  # 每場 2 次不算「限一次」
        ({"mana": 5, "uses_per_battle": 1}, False),
        ({"mana": 5, "cooldown": 4}, False),
    ],
    ids=["none", "cd3", "uses2", "once", "cd4"],
)
def test_rule_rewrite_needs_once_per_battle_or_a_long_cooldown(
    cost: dict[str, int], rejected: bool
) -> None:
    fake = lib_with_rewrite_primitive()
    s = skill_raw(
        rarity="legendary",
        effects=(EffectSpec(type="fake_rewrite"),),
        cost=skill().cost.model_copy(update=cost),
    )
    assert ("cap.rule_rewrite_cost" in rules_of(s, fake)) is rejected


def test_a_fake_rule_rewrite_primitive_needs_legendary() -> None:
    fake = lib_with_rewrite_primitive()
    s = skill_raw(
        rarity="rare",
        effects=(EffectSpec(type="fake_rewrite"),),
        cost=skill().cost.model_copy(update={"uses_per_battle": 1}),
    )
    assert "rarity.primitive" in rules_of(s, fake)
    legendary = s.model_copy(update={"rarity": "legendary"})
    assert "rarity.primitive" not in rules_of(legendary, fake)


# ---------------------------------------------------------------------------
# 4.4 互斥規則
# ---------------------------------------------------------------------------

NO_COOLDOWN_SHAPES = [
    ({"type": "square3", "range": 4}, DMG),
    ({"type": "allies_in_radius", "radius": 2}, {"type": "heal", "dice": "1d6"}),
    ({"type": "ring", "radius": 2}, DMG),
    ({"type": "cone", "size": 4}, DMG),
]


@pytest.mark.parametrize(
    ("shape", "effect"), NO_COOLDOWN_SHAPES, ids=["square3", "allies", "ring2", "cone4"]
)
def test_exclusion_1_no_cooldown_forbids_big_areas(
    shape: dict[str, Any], effect: dict[str, Any]
) -> None:
    rule = "exclusion.no_cooldown_big_area"
    assert rule in rules_of(spell(shape=shape, effects=[effect], cost={"mana": 6}))
    assert rule not in rules_of(
        spell(shape=shape, effects=[effect], cost={"mana": 6, "cooldown": 3})
    )


def test_exclusion_1_allows_small_areas_without_a_cooldown() -> None:
    rule = "exclusion.no_cooldown_big_area"
    for shape in ({"type": "cone", "size": 3}, {"type": "ring", "radius": 1}):
        assert rule not in rules_of(spell(shape=shape, cost={"mana": 6}))


def test_exclusion_2_stun_is_single_target_with_a_long_cooldown() -> None:
    rule = "exclusion.stun_single_long_cooldown"
    stun = {"type": "apply_status", "status": "stun", "duration": 1}
    assert rule in rules_of(spell(effects=[stun], cost={"mana": 6, "cooldown": 3}))
    assert rule in rules_of(spell(effects=[stun], cost={"mana": 6}))
    wide = spell(shape={"type": "cone", "size": 2}, effects=[stun], cost={"mana": 6, "cooldown": 4})
    assert rule in rules_of(wide)
    assert rule not in rules_of(spell(effects=[stun], cost={"mana": 6, "cooldown": 4}))


def test_exclusion_3_no_push_with_pull() -> None:
    rule = "exclusion.no_push_with_pull"
    both = [{"type": "push", "distance": 1}, {"type": "pull", "distance": 1}]
    assert rule in rules_of(spell(effects=both))
    assert rule not in rules_of(spell(effects=both[:1]))


def test_exclusion_4_self_shape_has_no_enemy_effects() -> None:
    rule = "exclusion.self_shape_no_enemy_effect"
    assert rule in rules_of(spell(shape={"type": "self"}, effects=[DMG]))
    allies = {"type": "apply_status", "status": "concealed", "duration": 2, "affects": "self"}
    assert rule not in rules_of(spell(shape={"type": "self"}, effects=[allies]))
    assert rule not in rules_of(spell(effects=[DMG]))  # 其他形狀照常對敵方


def test_exclusion_5_damage_and_ally_heal_do_not_mix() -> None:
    rule = "exclusion.no_damage_with_ally_heal"
    heal = {"type": "heal", "dice": "1d6"}
    assert rule in rules_of(spell(effects=[DMG, heal]))
    assert rule in rules_of(spell(effects=[DMG, {**heal, "affects": "self"}]))
    assert rule not in rules_of(spell(effects=[heal]))
    assert rule not in rules_of(spell(effects=[DMG]))


def test_exclusion_6_no_two_statuses_of_the_same_control_group() -> None:
    rule = "exclusion.no_repeated_control_group"
    root, slow, stun = (
        {"type": "apply_status", "status": s, "duration": 1} for s in ("root", "slow", "stun")
    )
    assert rule in rules_of(spell(effects=[root, slow]))  # 都是 movement
    assert rule not in rules_of(spell(effects=[slow, stun], cost={"mana": 6, "cooldown": 4}))


def test_exclusion_messages_name_the_rule_and_the_facts() -> None:
    both = [{"type": "push", "distance": 1}, {"type": "pull", "distance": 1}]
    (v,) = [v for v in violations(spell(effects=both)) if v.rule.startswith("exclusion.")]
    assert "推拉不並存" in v.message and "push、pull" in v.message


# ---------------------------------------------------------------------------
# 4.5 骨架
# ---------------------------------------------------------------------------


def test_each_enabled_skeleton_has_a_valid_example() -> None:
    examples = {
        "strike": skill(),
        "area": variant("skill_cleave"),
        "control": variant("skill_frost_shackle"),
        "displace": variant("skill_gale_kick"),
        "aura": variant("skill_sanctuary"),
        "combo": variant("skill_execute", skeleton="combo"),
        "passive": variant("skill_ember_brand"),
        "reaction": variant("skill_riposte"),
        "stance": variant("skill_fury_stance"),
        "builder_finisher": variant("skill_static_palm"),
        "trap": variant("skill_cinder_mine"),
        "modifier": variant("skill_searing_scar"),
        "consume_status": variant("skill_detonate_burning"),
        "summon": variant("skill_raise_skeleton"),
    }
    assert set(examples) == {s.id for s in lib().skeletons.values() if s.enabled}
    for skeleton_id, example in examples.items():
        assert example.skeleton == skeleton_id
        assert violations(example) == [], skeleton_id


def test_disabled_skeletons_are_rejected() -> None:
    # 3D-4a 啟用了最後一個停用的骨架（summon）；以停用的複本驗證拒絕規則仍有效
    base = lib()
    disabled = base.skeletons["summon"].model_copy(update={"enabled": False})
    library_ = replace(base, skeletons={**base.skeletons, "summon": disabled})
    assert "skeleton.disabled" in rules_of(variant("skill_raise_skeleton"), library_)
    assert "skeleton.disabled" not in rules_of(variant("skill_raise_skeleton"))


def test_strike_structure() -> None:
    assert "skeleton.shape" in rules_of(skill(shape={"type": "cone", "size": 2}))
    assert "skeleton.core" in rules_of(skill(effects=[{"type": "knock_prone"}]))
    weak_core = [{"type": "damage", "multiplier_permille": 500}, {"type": "knock_prone"}]
    assert "skeleton.core_share" in rules_of(skill(effects=weak_core))  # 3.5 ÷ 6.5 ＝ 53.8%
    two_extras = [
        {"type": "damage", "multiplier_permille": 2000},
        {"type": "knock_prone"},
        {"type": "apply_status", "status": "bleed"},
    ]
    assert "skeleton.secondary_count" in rules_of(skill(effects=two_extras))
    heal = [{"type": "damage", "multiplier_permille": 2000}, {"type": "heal", "dice": "1d4"}]
    assert "skeleton.secondary" in rules_of(skill(effects=heal))  # 附帶效果必須是有害原語
    ok = [{"type": "damage", "multiplier_permille": 2000}, {"type": "knock_prone"}]
    assert only(skill(effects=ok), "skeleton") == []


def test_area_structure() -> None:
    cone = {"type": "cone", "size": 2}
    assert "skeleton.shape" in rules_of(spell(skeleton="area"))  # 單體不是範圍
    heal = [DMG, {"type": "heal", "dice": "1d4", "affects": "allies"}]
    assert "skeleton.secondary" in rules_of(spell(skeleton="area", shape=cone, effects=heal))
    three = [
        DMG,
        {"type": "create_surface", "surface": "fire"},
        {"type": "apply_status", "status": "burning"},
        {"type": "knock_prone"},
    ]
    assert "skeleton.secondary_count" in rules_of(spell(skeleton="area", shape=cone, effects=three))
    surface_heavy = [
        {"type": "damage", "dice": "1d4", "element": "fire"},
        {"type": "create_surface", "surface": "holy"},
    ]
    assert "skeleton.core_share" in rules_of(
        spell(skeleton="area", shape=cone, effects=surface_heavy)
    )
    ok = spell(
        skeleton="area", shape=cone, effects=[DMG, {"type": "create_surface", "surface": "fire"}]
    )
    assert only(ok, "skeleton") == []


def test_control_structure() -> None:
    frost = [{"type": "damage", "dice": "2d6", "element": "ice"}, _root()]
    assert "skeleton.secondary_share" in rules_of(
        spell(skeleton="control", effects=frost)
    )  # 7 ÷ 11
    assert "skeleton.core" in rules_of(spell(skeleton="control", effects=[DMG]))
    push = [_root(), {"type": "push", "distance": 1}]
    assert "skeleton.secondary" in rules_of(spell(skeleton="control", effects=push))
    two_damage = [_root(), {**DMG, "dice": "1d4"}, {**DMG, "dice": "1d4"}]
    assert "skeleton.secondary_count" in rules_of(spell(skeleton="control", effects=two_damage))
    light = [_root(), {"type": "damage", "dice": "1d4", "element": "ice"}]
    assert only(spell(skeleton="control", effects=light), "skeleton") == []


def test_displace_structure() -> None:
    push = {"type": "push", "distance": 2}
    big = {"type": "square3", "range": 4}
    assert "skeleton.shape" in rules_of(spell(skeleton="displace", shape=big, effects=[push]))
    heavy = [push, {"type": "damage", "dice": "3d6", "element": "fire"}]
    assert "skeleton.secondary_share" in rules_of(spell(skeleton="displace", effects=heavy))
    crowded = [
        push,
        DMG,
        {"type": "apply_status", "status": "burning"},
        {"type": "create_surface", "surface": "fire"},
    ]
    assert "skeleton.secondary_count" in rules_of(spell(skeleton="displace", effects=crowded))
    assert "skeleton.core" in rules_of(spell(skeleton="displace", effects=[DMG]))
    light = [push, {"type": "damage", "dice": "1d6", "element": "fire"}]
    assert only(spell(skeleton="displace", effects=light), "skeleton") == []


def test_aura_structure() -> None:
    heal = {"type": "heal", "dice": "1d6"}
    radius = {"type": "allies_in_radius", "radius": 2}
    line = {"type": "line", "size": 2}
    assert "skeleton.shape" in rules_of(spell(skeleton="aura", shape=line, effects=[heal]))
    enemy = [heal, {"type": "apply_status", "status": "slow", "affects": "enemies"}]
    assert "skeleton.forbidden_affects" in rules_of(
        spell(skeleton="aura", shape=radius, effects=enemy)
    )
    both = [heal, {"type": "heal", "dice": "1d4", "affects": "all"}]
    assert "skeleton.forbidden_affects" in rules_of(
        spell(skeleton="aura", shape=radius, effects=both)
    )
    assert "skeleton.core" in rules_of(spell(skeleton="aura", shape=radius, effects=[DMG]))
    # 對友方的治療、增益狀態、有益表面都是核心；其他原語（這裡是對友方的推與拉）才算附帶
    two_extras = [
        heal,
        {"type": "push", "distance": 1, "affects": "allies"},
        {"type": "pull", "distance": 1, "affects": "allies"},
    ]
    assert "skeleton.secondary_count" in rules_of(
        spell(skeleton="aura", shape=radius, effects=two_extras)
    )
    ok = spell(skeleton="aura", shape=radius, effects=[heal])
    assert only(ok, "skeleton") == []


def test_aura_core_status_and_surface_must_be_beneficial() -> None:
    radius = {"type": "allies_in_radius", "radius": 2}
    heal = {"type": "heal", "dice": "1d6"}
    burn = {"type": "apply_status", "status": "burning", "affects": "allies"}
    fire = {"type": "create_surface", "surface": "fire", "affects": "allies"}
    assert "skeleton.core_beneficial" in rules_of(
        spell(skeleton="aura", shape=radius, effects=[burn])
    )
    assert "skeleton.core_beneficial" in rules_of(
        spell(skeleton="aura", shape=radius, effects=[fire])
    )
    veil = {"type": "apply_status", "status": "concealed", "affects": "allies"}
    holy = {"type": "create_surface", "surface": "holy", "affects": "allies"}
    for good in (veil, holy):
        assert "skeleton.core_beneficial" not in rules_of(
            spell(skeleton="aura", shape=radius, effects=[heal, good])
        )


def test_beneficial_flags_in_content() -> None:
    rules = lib().ruleset
    statuses = {s.id for s in rules.statuses.statuses if s.beneficial}
    surfaces = {s.id.value for s in rules.surfaces.surfaces if s.beneficial}
    assert statuses == {
        "defending",
        "concealed",
        # 2D-1
        "guarded",
        "empowered",
        "hasted",
        "regenerating",
        "shielded",
        # 2E-2
        "stance_fury",
        "stance_bulwark",
        # 3C-4a
        "undying",
        # 3F-4b：延遲段的等待狀態（有益，不被淨化）
        "charging",
        # 3C-4b
        "soul_link",
        # 3D-8c
        "overwatch",
    }
    assert surfaces == {"holy"}


def test_combo_structure_requires_a_condition() -> None:
    assert "skeleton.condition" in rules_of(skill(skeleton="combo"))
    skill_level = skill(skeleton="combo", condition={"type": "target_hp_below", "permille": 500})
    assert "skeleton.condition" not in rules_of(skill_level)
    effect_level = skill(
        skeleton="combo",
        effects=[
            {"type": "damage", "multiplier_permille": 1000},
            {
                "type": "damage",
                "multiplier_permille": 1500,
                "condition": {"type": "target_has_status", "status": "burning"},
            },
        ],
    )
    assert only(effect_level, "skeleton") == []
    assert "skeleton.shape" in rules_of(
        skill(skeleton="combo", shape={"type": "square3", "range": 3})
    )


def test_a_skill_kind_must_match_its_skeleton() -> None:
    assert "skeleton.kind" in rules_of(
        skill(kind="reaction", ap_cost=None, reaction={"event": "hit_by_melee"})
    )


def _root() -> dict[str, Any]:
    return {"type": "apply_status", "status": "root", "duration": 1}


# ---------------------------------------------------------------------------
# 4.6 稀有度
# ---------------------------------------------------------------------------


def common(**overrides: Any) -> SkillDef:
    return skill(rarity="common", **overrides)


@pytest.mark.parametrize(
    ("overrides", "rule"),
    [
        (
            {"effects": [{"type": "knock_prone"}, {"type": "damage", "multiplier_permille": 2000}]},
            "rarity.primitive",
        ),
        ({"effects": [{"type": "damage", "multiplier_permille": 2000}, _root()]}, "rarity.status"),
        ({"shape": {"type": "cross", "range": 3}, "skeleton": "area"}, "rarity.shape"),
        ({"shape": {"type": "ground_tile", "range": 3}}, "rarity.shape"),
        ({"condition": {"type": "target_hp_below", "permille": 400}}, "rarity.condition"),
        (
            {
                "effects": [
                    {"type": "damage", "multiplier_permille": 1000},
                    {
                        "type": "damage",
                        "multiplier_permille": 1000,
                        "condition": {"type": "height_advantage"},
                    },
                ]
            },
            "rarity.condition",
        ),
        (
            {
                "effects": [
                    {"type": "damage", "multiplier_permille": 1000},
                    {"type": "apply_status", "status": "bleed"},
                    {"type": "apply_status", "status": "weaken"},
                ]
            },
            "rarity.max_effects",
        ),
    ],
    ids=[
        "structural",
        "root",
        "cross",
        "ground_tile",
        "skill_condition",
        "effect_condition",
        "three",
    ],
)
def test_common_skills_cannot_use_rarer_content(overrides: dict[str, Any], rule: str) -> None:
    assert rule in rules_of(common(**overrides))
    assert rule not in rules_of(skill(rarity="rare", **overrides))  # rare 以上可以


def test_common_skills_can_use_numeric_primitives_and_simple_shapes() -> None:
    cases = [
        skill(rarity="common"),
        common(
            effects=[
                {"type": "damage", "multiplier_permille": 2000},
                {"type": "apply_status", "status": "bleed"},
            ]
        ),
        spell(rarity="common", shape={"type": "cone", "size": 3}, skeleton="area"),
        spell(rarity="common", shape={"type": "ring", "radius": 1}, skeleton="area"),
        spell(rarity="common", shape={"type": "line", "size": 3}, skeleton="area"),
    ]
    for s in cases:
        assert only(s, "rarity") == [], s.shape


def test_epic_and_legendary_are_at_least_as_permissive_as_rare() -> None:
    root = [{"type": "damage", "multiplier_permille": 2000}, _root()]
    for rarity in ("rare", "epic", "legendary"):
        # 傳說必須花源力（Phase 3C-4a）；這裡只看稀有度規則
        cost = {"mana": 4, "cooldown": 2, "source": 1} if rarity == "legendary" else None
        extra = {"cost": cost} if cost is not None else {}
        assert only(skill(rarity=rarity, effects=root, **extra), "rarity") == []
    assert lib().budget.rarity["common"].max_effects == 2
    assert lib().budget.rarity["legendary"].max_effects == 4
