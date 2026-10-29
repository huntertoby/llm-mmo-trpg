"""預算計算（Phase 2B-2 4.2；驗收 2）：手算案例與 ``skill_budget`` 的結果完全相等。

``tier_budget`` 取自 ``core.yaml``（T1 ＝ 14、T2 ＝ 18）；每個案例的註解列出手算過程。
"""

from __future__ import annotations

from fractions import Fraction as F
from typing import Any

import pytest

from tests.skillgen.helpers import lib, skill, skill_raw
from trpg.content.skills import EffectSpec
from trpg.skillgen.budget import BudgetError, skill_budget

T1, T2 = 14, 15


def _spell(**overrides: Any) -> Any:
    data: dict[str, Any] = {
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "cost": {},
        "ap_cost": 2,
    }
    data.update(overrides)
    return skill(**data)


def test_tier_budget_comes_from_core_yaml() -> None:
    assert lib().ruleset.core.tier_budget == {1: 14, 2: 18, 3: 23, 4: 29, 5: 36}


# ---------------------------------------------------------------------------
# 手算案例
# ---------------------------------------------------------------------------


def test_hand_case_1_weapon_skill() -> None:
    """武器技：傷害 ×1.8 ＝ 1.8 × 7 ＝ 12.6；單體 ×1；AP 2 ×1；折抵 冷卻 2（+100）＋法力 4（+20）
    ＝ +120‰；可用 ＝ 14 × 1 × 1.12 ＝ 15.68；比例 ＝ 12.6 ÷ 15.68 ＝ 45/56。"""
    report = skill_budget(skill(), lib())
    assert [e.points for e in report.effects] == [F(63, 5)]
    assert report.raw == report.total == F(63, 5)
    assert report.allowance_permille == 120
    assert report.usable == F(14) * F(112, 100) == F(392, 25)
    assert report.ratio == F(45, 56)
    assert report.ok and not report.over_budget and not report.too_weak


def test_hand_case_2_spell_skill_with_dice_average() -> None:
    """法術技：3d6 平均 10.5；單體；階級 2（18）、AP 2、冷卻 1（+50）＋法力 10（+50）＝ +100‰；
    可用 ＝ 18 × 1.1 ＝ 19.8；比例 ＝ 10.5 ÷ 19.8 ＝ 35/66。"""
    s = _spell(
        tier=2,
        effects=[{"type": "damage", "dice": "3d6", "element": "fire"}],
        cost={"mana": 10, "cooldown": 1},
    )
    report = skill_budget(s, lib())
    assert report.total == F(21, 2)
    assert report.usable == F(99, 5)
    assert report.ratio == F(35, 66)


def test_hand_case_3_affects_all_target_coefficient() -> None:
    """敵我不分：2d6（7）× 錐形 2（1.3）× 對象 0.8 ＝ 7.28；AP 1（0.5）、無代價、T1：
    可用 ＝ 14 × 0.5 ＝ 7；比例 ＝ 7.28 ÷ 7 ＝ 26/25。"""
    s = _spell(
        ap_cost=1,
        shape={"type": "cone", "size": 2},
        effects=[{"type": "damage", "dice": "2d6", "element": "fire", "affects": "all"}],
    )
    report = skill_budget(s, lib())
    (effect,) = report.effects
    assert (effect.base, effect.shape, effect.target) == (F(7), F(13, 10), F(4, 5))
    assert report.total == F(182, 25)
    assert report.usable == F(7)
    assert report.ratio == F(26, 25) and report.over_budget


def test_hand_case_4_effect_and_skill_conditions() -> None:
    """效果條件：第二個傷害帶 target_has_status（common 0.85）→ 7 ＋ 7 × 0.85 ＝ 12.95；
    技能條件 self_hp_below（harsh 0.6）→ total ＝ 12.95 × 0.6 ＝ 7.77；AP 2、無代價：可用 14。"""
    s = skill(
        effects=[
            {"type": "damage", "multiplier_permille": 1000},
            {
                "type": "damage",
                "multiplier_permille": 1000,
                "condition": {"type": "target_has_status", "status": "burning"},
            },
        ],
        condition={"type": "self_hp_below", "permille": 300},
        cost={},
    )
    report = skill_budget(s, lib())
    assert [e.condition for e in report.effects] == [F(1), F(17, 20)]
    assert report.raw == F(259, 20)
    assert report.condition_multiplier == F(3, 5)
    assert report.total == F(777, 100)
    assert report.usable == F(14)
    assert report.allowance_parts == ()


def test_hand_case_5_synergy_area_and_control() -> None:
    """協同：方陣 3（2.0）的 2d6 傷害 ＝ 14，緩速（3）× 2.0 ＝ 6 → raw 20；標籤 damage／area／
    control → area+control ×1.2 → total 24；折抵 冷卻 3（+150）＋法力 8（+40）＝ +190‰；
    可用 ＝ 14 × 1.19 ＝ 16.66。"""
    s = _spell(
        shape={"type": "square3", "range": 4},
        effects=[
            {"type": "damage", "dice": "2d6", "element": "fire"},
            {"type": "apply_status", "status": "slow"},
        ],
        cost={"mana": 8, "cooldown": 3},
    )
    report = skill_budget(s, lib())
    assert report.raw == F(20)
    assert report.tags == ("damage", "area", "control")
    assert report.synergies == ((("area", "control"), F(6, 5)),)
    assert report.total == F(24)
    assert report.usable == F(14) * F(119, 100)


def test_hand_case_6_cost_allowance_caps() -> None:
    """代價折抵：冷卻 6 回合 ＝ 300（上限）、每場 2 次 ＝ 250、法力 40 ＝ 200 → 上限 150、
    HP 300‰ ＝ 300 → 上限 200；加總 900‰，再以總上限截斷為 500‰（2C-1 3.1）。"""
    s = skill(cost={"mana": 40, "cooldown": 6, "uses_per_battle": 2, "hp_percent": 300})
    report = skill_budget(s, lib())
    assert dict(report.allowance_parts) == {
        "冷卻 6 回合": 300,
        "每場 2 次": 250,
        "法力 40": 150,
        "HP 30%": 200,
    }
    assert report.allowance_raw_permille == 900
    assert report.allowance_capped
    assert report.allowance_permille == 500
    assert report.usable == F(14) * F(3, 2)


def test_total_allowance_cap_comes_from_skill_budget_yaml() -> None:
    assert lib().budget.allowance.total_cap == 500


def test_allowance_below_the_total_cap_is_untouched() -> None:
    """冷卻 4（+200）＋ 法力 10（+50）＝ 250‰ < 500‰：不截斷。"""
    report = skill_budget(skill(cost={"mana": 10, "cooldown": 4}), lib())
    assert report.allowance_permille == report.allowance_raw_permille == 250
    assert not report.allowance_capped


def test_total_allowance_cap_applies_after_each_part_cap() -> None:
    """各項的個別上限先套用（冷卻 300、法力 150＝450），未達 500 → 不截斷；
    再加每場 1 次（400）→ 850 → 截斷為 500。"""
    assert skill_budget(skill(cost={"mana": 99, "cooldown": 6}), lib()).allowance_permille == 450
    report = skill_budget(skill(cost={"mana": 99, "cooldown": 6, "uses_per_battle": 1}), lib())
    assert (report.allowance_raw_permille, report.allowance_permille) == (850, 500)


@pytest.mark.parametrize(("uses", "expected"), [(1, 400), (2, 250), (3, 100), (5, 100)], ids=str)
def test_uses_per_battle_allowance(uses: int, expected: int) -> None:
    report = skill_budget(skill(cost={"uses_per_battle": uses}), lib())
    assert report.allowance_permille == expected


def test_hand_case_7_synergy_stack_and_debuff() -> None:
    """符合多條協同時全部相乘：方陣 ＋ 緩速 ＋ 推擊 1 → area+control ×1.2、area+displace ×1.1
    ＝ ×1.32；傷害 ＋ 虛弱 → damage+debuff ×1.15。"""
    stacked = _spell(
        shape={"type": "square3", "range": 4},
        effects=[
            {"type": "apply_status", "status": "slow"},
            {"type": "push", "distance": 1},
        ],
    )
    report = skill_budget(stacked, lib())
    assert report.raw == F(6) + F(4)  # 緩速 3 × 2.0、推擊 2 × 2.0
    assert report.total == F(10) * F(6, 5) * F(11, 10)
    debuffed = skill(
        effects=[
            {"type": "damage", "multiplier_permille": 1000},
            {"type": "apply_status", "status": "weaken"},
        ]
    )
    report = skill_budget(debuffed, lib())
    assert report.tags == ("damage", "debuff")
    assert report.total == (F(7) + F(4)) * F(23, 20)


# ---------------------------------------------------------------------------
# 其他點數與係數
# ---------------------------------------------------------------------------


def test_ap_coefficients_and_reaction() -> None:
    one, three = skill_budget(skill(ap_cost=1), lib()), skill_budget(skill(ap_cost=3), lib())
    assert (one.ap_coefficient, three.ap_coefficient) == (F(1, 2), F(8, 5))
    reaction = skill(
        kind="reaction", ap_cost=None, skeleton="reaction", reaction={"event": "hit_by_melee"}
    )
    assert skill_budget(reaction, lib()).ap_coefficient == F(3, 5)


def test_duration_scales_status_and_surface_points() -> None:
    def points(effect: dict[str, Any]) -> F:
        s = _spell(shape={"type": "single", "range": 4}, effects=[effect])
        return skill_budget(s, lib()).effects[0].points

    assert points({"type": "apply_status", "status": "poison"}) == 3
    assert points({"type": "apply_status", "status": "poison", "duration": 6}) == 6  # 3 × 6 ÷ 3
    assert points({"type": "apply_status", "status": "concealed", "duration": 4}) == 6  # 3 × 4 ÷ 2
    assert points({"type": "apply_status", "status": "stun", "duration": 1}) == 8
    assert points({"type": "create_surface", "surface": "fire", "duration": 1}) == F(3, 2)
    assert points({"type": "create_surface", "surface": "water", "duration": 6}) == 2  # 1 × 6 ÷ 3
    assert points({"type": "create_surface", "surface": "water"}) == 1  # 預設持續 3 回合
    assert points({"type": "create_surface", "surface": "oil", "duration": 7}) == 2  # 永久表面


def test_structural_primitive_points() -> None:
    def points(effect: dict[str, Any], shape: dict[str, Any] | None = None) -> F:
        s = _spell(shape=shape or {"type": "single", "range": 4}, effects=[effect])
        return skill_budget(s, lib()).effects[0].points

    assert points({"type": "push", "distance": 2}) == 4
    assert points({"type": "pull", "distance": 1}) == 2
    assert points({"type": "knock_prone"}) == 3
    assert points({"type": "destroy_object"}) == 2
    assert points({"type": "create_obstacle", "object": "earth_wall"}) == 3
    assert (
        points({"type": "raise_terrain"}) == points({"type": "lower_terrain"}) == 7
    )  # 3-54e：2 → 7
    assert points({"type": "heal", "dice": "2d6"}) == 7
    # 形狀倍率套用在對象為 tiles 的效果；teleport（self）與 affects: self 一律 1.0
    ground = {"type": "ground_tile", "range": 4}
    assert points({"type": "teleport"}, ground) == 4
    wide = skill_raw(
        shape=skill(shape={"type": "cone", "size": 3}).shape,
        effects=(
            EffectSpec(type="teleport"),
            EffectSpec(type="create_obstacle", object="earth_wall"),
        ),
    )
    teleport, obstacle = skill_budget(wide, lib()).effects
    assert (teleport.points, obstacle.points) == (F(4), F(3) * F(8, 5))


def test_shape_multiplier_table() -> None:
    """4.2 的形狀倍率表。"""
    shapes = lib().ruleset.shapes.by_id()

    def mult(shape_id: str, **params: int) -> F:
        return F(shapes[shape_id].budget.permille_for(dict(params)), 1000)

    assert mult("self") == mult("single") == mult("ground_tile") == 1
    assert mult("line", size=3) == F(14, 10) and mult("line", size=2) == F(12, 10)
    assert [mult("cone", size=n) for n in (2, 3, 4)] == [F(13, 10), F(16, 10), F(2)]
    assert mult("cross") == F(18, 10) and mult("square3") == 2
    assert [mult("ring", radius=n) for n in (1, 2)] == [F(18, 10), F(22, 10)]
    assert mult("chain", jumps=2) == F(15, 10) and mult("chain", jumps=1) == F(125, 100)
    assert mult("allies_in_radius", radius=2) == F(18, 10)


ELEMENTS_9 = ("physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow")


def test_status_and_surface_points_match_the_spec() -> None:
    rules = lib().ruleset
    statuses = {s.id: s.budget_points for s in rules.statuses.statuses}
    assert statuses == {
        "defending": 2,  # 2D-1：技能可以施加防禦
        "infused_fire": 6,  # 3I-6：臨時附魔
        "infused_holy": 6,
        "overdrawn": None,  # 3-50：只能由 cost.overdraft 施加
        "charging": None,  # 3F-4b：延遲段的等待狀態，不能由效果施加
        "prone": 3,
        "burning": 3,
        "concealed": 3,
        "slow": 3,
        "root": 4,
        "stun": 8,
        "frozen": 8,
        "weaken": 4,
        "vulnerable": 4,
        "bleed": 3,
        "poison": 3,
        # 2D-1
        "guarded": 4,
        "empowered": 4,
        "rallied": 4,  # 3-33e1：戰意圖騰的光環
        "hasted": 3,
        "regenerating": 4,
        "shielded": None,  # 只能由 shield 原語施加
        "taunted": 3,  # 2026-10-23 玩法 PM：加 mental 控制類別後 4 → 3
        # 2D-2
        "feared": 5,
        "silenced": 5,
        "blinded": 4,
        "marked": 4,
        # 2E-2：姿態（stance）
        "stance_fury": 11,
        "stance_bulwark": 11,
        # 3W-4b：白板姿態，點數對上 2 階（14）與 3 階（18）的姿態預算
        "stance_guard": 14,
        "stance_flame": 14,
        "stance_frost": 14,
        "stance_ironwall": 18,
        "stance_blaze": 18,
        "stance_glacier": 18,
        "stance_bastion": 21,  # 3W-2b：防守姿態第四級
        # 3W-2b：帶附帶效果的護盾（附帶效果的價值）
        "shielded_thorns": 2,
        "shielded_mending": 2,
        "shielded_wet": 1,
        "shielded_marking": 2,
        # 3W-2b：元素姿態階梯（每個元素 5 級）
        **{
            f"stance_{e}_{n}": points
            for e in ELEMENTS_9
            for n, points in enumerate((15, 17, 19, 22, 28), start=1)
        },
        "undying": None,  # 3C-4a：只能由 cheat_death 原語施加
        "soul_link": None,  # 3C-4b：只能由 redirect_damage 原語施加
        "revealed": None,  # 3D-8a：只能由 reveal 原語施加
        "time_bomb": None,  # 3D-8b：只能由 delayed_damage 原語施加
        "overwatch": 6,  # 3D-8c：監視（反應 overwatch_shot 需要它）
        "armor_broken": None,  # 3-24a1：只能由斧的 armor_break 武器參數施加
        "entangled": None,  # 3I-1：只能由鞭的 entangle 武器參數施加
        "stoneskin": 3,  # 3-54b：石膚（大地）
        "race_adapt": None,  # 3R-2：只能由人類種族技施加
        "race_stonewall": None,  # 3R-2：只能由矮人種族技施加
    }
    surfaces = {s.id.value: s.budget_points for s in rules.surfaces.surfaces}
    assert surfaces == {
        "fire": 3,
        "poison": 3,
        "ice": 3,
        "oil": 2,
        "water": 1,
        "holy": 4,
        "darkness": 2,
        "smoke": 2,  # 3-11：比照 darkness
    }


def test_the_budget_is_exact_not_floating_point() -> None:
    report = skill_budget(skill(), lib())
    for value in (report.raw, report.total, report.usable, report.ratio):
        assert isinstance(value, F)


# ---------------------------------------------------------------------------
# 無法計算
# ---------------------------------------------------------------------------


def test_shielded_cannot_be_applied_by_apply_status() -> None:
    s = skill(effects=[{"type": "apply_status", "status": "shielded"}])
    with pytest.raises(BudgetError, match="shielded"):
        skill_budget(s, lib())


def test_passive_budget_uses_the_trigger_coefficient() -> None:
    library = lib()
    report = skill_budget(library.skills["skill_ember_brand"], library)
    assert report.coefficient_label is not None and "on_hit" in report.coefficient_label
    assert F(7, 10) <= report.ratio <= 1
