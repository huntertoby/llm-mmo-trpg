"""預算與驗證用的資料檔（Phase 2B-2 4.2–4.6）：內容符合規格、錯誤的資料被拒絕。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.library import load_library
from trpg.content.rules import CoreRules
from trpg.content.skill_rules import BudgetRules, SkeletonDef
from trpg.content.skills import SKELETON_IDS, ShapeDef
from trpg.shared.errors import ContentError

ENABLED = {
    "rune",  # Phase 3-23
    "sacrifice",  # Phase 3-24c
    "strike",
    "area",
    "control",
    "displace",
    "aura",
    "combo",
    "passive",
    "reaction",
    "stance",
    "builder_finisher",
    "trap",
    "modifier",
    "consume_status",
    "summon",
}


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    return root


def _edit(path: Path, change: Any) -> None:
    data = yaml.safe_load(path.read_text("utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# 骨架
# ---------------------------------------------------------------------------


def test_all_sixteen_skeletons_have_a_data_file() -> None:
    # 6.9 的 12 種骨架 ＋ Phase 3C-2 的 modifier（修正技能）＋ Phase 3C-3b 的 consume_status
    # ＋ Phase 3-23 的 rune ＋ Phase 3-24c 的 sacrifice
    lib = library()
    assert set(lib.skeletons) == set(SKELETON_IDS) and len(lib.skeletons) == 16
    assert {i for i, s in lib.skeletons.items() if s.enabled} == ENABLED
    for skeleton_id in SKELETON_IDS:
        assert (PROJECT_ROOT / "content" / "skeletons" / f"{skeleton_id}.yaml").is_file()


def test_the_initial_skeleton_structure_matches_the_spec() -> None:
    sk = library().skeletons
    assert sk["strike"].shapes == ("single", "unit_then_tile")  # 3D-8d：一般瞬步（手寫技能）
    assert (sk["strike"].core.primitives, sk["strike"].core.min_share_permille) == (
        ("damage",),
        600,
    )
    assert sk["strike"].secondary.max_count == 1 and sk["strike"].secondary.harmful_only
    assert set(sk["area"].shapes) == {"line", "cone", "cross", "square3", "ring", "chain"}
    assert sk["area"].core.min_share_permille == 500 and sk["area"].secondary.max_count == 2
    assert set(sk["area"].secondary.primitives or ()) == {
        "create_surface",
        "apply_status",
        "push",
        "knock_prone",
        "destroy_object",
        "blow_surface",  # 3-54a
        "shockwave",  # 3-54b
        "clear_surface",  # 3-54c
        "leave_form",  # 3J-4c（解形爆發，手寫專用）
    }
    assert set(sk["control"].core.primitives) == {
        "apply_status",
        "create_surface",
        "create_obstacle",
        "raise_terrain",
        "lower_terrain",
        "steal_buff",  # 3D-1
        "dispel",  # 3D-8a
        "reveal",  # 3D-8a
        "zone",  # 3D-5
        "delayed_damage",  # 3D-8b
        "blow_surface",  # 3-54a
        "shockwave",  # 3-54b
        "clear_surface",  # 3-54c
    }
    assert sk["control"].secondary.max_share_permille == {"damage": 400}
    # 3C-5a：場景物件原語（只給手寫技能，隨機組合器不使用）
    assert set(sk["displace"].core.primitives) == {
        "push",
        "pull",
        "teleport",
        "knock_prone",
        "hurl_object",
        "topple",
        "leap",  # 3D-2
        "swap",  # 3D-2
        "teleport_target",  # 3D-2b
        "swap_any",  # 3D-2b
        "charge_through",  # 3D-2c
        "shadowstep",  # 3D-8d
    }
    assert set(sk["displace"].secondary.primitives or ()) >= {"dash"}
    assert sk["displace"].secondary.max_share_permille == {"damage": 500}
    assert sk["displace"].secondary.max_count == 2
    assert set(sk["aura"].shapes) == {
        "self",
        "single",
        "allies_in_radius",
        "square3",
    }  # 2D-1 加 single
    assert set(sk["aura"].core.primitives) == {
        "heal",
        "shield",
        "cleanse",
        "apply_status",
        "create_surface",
        # 3C-4a：改寫規則型
        "grant_ap",
        "reset_cooldown",
        "cheat_death",
        # 3C-4b
        "redirect_damage",
        "copy_skill",
        "extra_reaction",
        "restore_resource",  # 3D-1
        "zone",  # 3D-5（跟隨型光環）
        "rule_change",  # 3D-6（規則改變型傳說）
        "revive",  # 3D-8b
        "grant_skill",  # 3D-8c
    }
    assert (
        set(sk["aura"].forbid_affects) == {"enemies", "all"} and sk["aura"].secondary.max_count == 1
    )
    assert sk["combo"].requires_condition and sk["combo"].core.min_share_permille == 500
    assert not any(s.requires_condition for k, s in sk.items() if k != "combo")


def test_disabled_skeletons_may_reference_unimplemented_primitives() -> None:
    assert library().skeletons["summon"].core.primitives == ("summon",)


def test_a_missing_skeleton_file_is_rejected(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "skeletons" / "trap.yaml").unlink()
    with pytest.raises(ContentError, match="缺少骨架資料檔：trap"):
        load_library(root)


def test_a_skeleton_with_an_unknown_shape_or_primitive_is_rejected(tmp_path: Path) -> None:
    root = _copy(tmp_path / "a")
    _edit(root / "skeletons" / "strike.yaml", lambda d: d.update(shapes=["blob"]))
    with pytest.raises(ContentError, match="未知的形狀：blob"):
        load_library(root)
    root = _copy(tmp_path / "b")
    _edit(root / "skeletons" / "strike.yaml", lambda d: d["core"].update(primitives=["zap"]))
    with pytest.raises(ContentError, match="未知的原語：zap"):
        load_library(root)


def test_an_enabled_skeleton_needs_core_primitives() -> None:
    data = yaml.safe_load((PROJECT_ROOT / "content/skeletons/strike.yaml").read_text("utf-8"))
    data["core"]["primitives"] = []
    with pytest.raises(ValidationError, match="核心原語"):
        SkeletonDef.model_validate(data)


# ---------------------------------------------------------------------------
# 規則數值
# ---------------------------------------------------------------------------


def test_budget_rules_match_the_spec() -> None:
    b = library().budget
    assert (b.min_ratio_permille, b.max_ratio_permille) == (700, 1000)
    assert b.ap_coefficient_permille == {1: 500, 2: 1000, 3: 1600}
    assert b.reaction_coefficient_permille == 600
    assert b.condition_permille == {"none": 1000, "common": 850, "harsh": 600}
    assert b.all_target_permille == 800
    a = b.allowance
    assert (a.cooldown_per_turn, a.cooldown_cap) == (50, 300)
    assert (a.uses_per_battle, a.uses_default) == ({1: 400, 2: 250}, 100)
    assert (a.mana_per_point, a.mana_cap, a.hp_per_permille, a.hp_cap) == (5, 150, 1, 200)
    assert b.rarity["common"].max_effects == 2 and b.rarity["rare"].max_effects == 4
    assert core().budget_reference_weapon_damage == 7


def core() -> CoreRules:
    return library().ruleset.core


def test_tier_budget_is_a_strictly_increasing_table_of_five_tiers() -> None:
    values = [core().tier_budget[t] for t in range(1, 6)]
    assert values == sorted(set(values)) and len(values) == 5


def test_tier_budget_validation() -> None:
    data = yaml.safe_load((PROJECT_ROOT / "content/rules/core.yaml").read_text("utf-8"))
    for bad in (
        {1: 14, 2: 14, 3: 19, 4: 24, 5: 30},
        {1: 14, 2: 15, 3: 19, 4: 24},
        {1: 0, 2: 5, 3: 9, 4: 12, 5: 15},
    ):
        with pytest.raises(ValidationError, match="tier_budget"):
            CoreRules.model_validate({**data, "tier_budget": bad})


def test_budget_rules_reject_inconsistent_data() -> None:
    data = yaml.safe_load((PROJECT_ROOT / "content/skill_budget.yaml").read_text("utf-8"))
    with pytest.raises(ValidationError, match="min_ratio_permille"):
        BudgetRules.model_validate({**data, "min_ratio_permille": 1000})
    with pytest.raises(ValidationError, match="AP 1、2、3"):
        BudgetRules.model_validate({**data, "ap_coefficient_permille": {1: 500, 2: 1000}})


def test_synergy_and_exclusion_tables() -> None:
    lib = library()
    assert {(s.tags, s.coefficient_permille) for s in lib.synergies.synergies} == {
        (("area", "control"), 1200),
        (("damage", "debuff"), 1150),
        (("area", "displace"), 1100),
    }
    assert [r.id for r in lib.exclusions.rules] == [
        "no_cooldown_big_area",
        "stun_single_long_cooldown",
        "no_push_with_pull",
        "self_shape_no_enemy_effect",
        "no_damage_with_ally_heal",
        "no_repeated_control_group",
        "terrain_needs_earth",  # 3-54b
    ]


def test_unknown_mechanic_tag_in_a_synergy_is_rejected(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(
        root / "skill_synergies.yaml",
        lambda d: d["synergies"].append({"tags": ["area", "magic"], "coefficient_permille": 1100}),
    )
    with pytest.raises(ContentError, match="未知的機制標籤"):
        load_library(root)


def test_an_exclusion_referencing_an_unknown_status_is_rejected(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(
        root / "skill_exclusions.yaml",
        lambda d: d["rules"][1]["when"].update(statuses=["petrify"]),
    )
    with pytest.raises(ContentError, match="未知的狀態 'petrify'"):
        load_library(root)


# ---------------------------------------------------------------------------
# 形狀、稀有度
# ---------------------------------------------------------------------------


def test_shape_budget_validation() -> None:
    cone = yaml.safe_load((PROJECT_ROOT / "content/skill_shapes.yaml").read_text("utf-8"))
    (data,) = [s for s in cone["shapes"] if s["id"] == "cone"]
    with pytest.raises(ValidationError, match="by_value_permille 缺少"):
        ShapeDef.model_validate(
            {**data, "budget": {"param": "size", "by_value_permille": {2: 1300}}}
        )
    with pytest.raises(ValidationError, match="不是這個形狀的參數"):
        ShapeDef.model_validate({**data, "budget": {"param": "radius", "per_unit_permille": 100}})


def test_min_rarity_tables_match_the_spec() -> None:
    rules = library().ruleset
    common_shapes = {"self", "single", "line", "cone", "ring", "allies_in_radius"}
    for shape in rules.shapes.shapes:
        assert shape.min_rarity == ("common" if shape.id in common_shapes else "rare"), shape.id
    rewrites = {  # 3C-4a、4b：改寫規則型為 epic
        "grant_ap",
        "reset_cooldown",
        "cheat_death",
        "redirect_damage",
        "copy_skill",
        "extra_reaction",
    }
    for primitive in rules.primitives.primitives:
        expected = (
            "common"
            if primitive.id in {"damage", "heal", "apply_status", "shield", "cleanse"}
            else "epic"
            if primitive.id in rewrites
            else "legendary"
            if primitive.id == "rule_change"  # 3D-6：只給傳說
            else "rare"
        )
        assert primitive.min_rarity == expected, primitive.id
    common_statuses = {
        "burning",
        "slow",
        "weaken",
        "vulnerable",
        "bleed",
        "poison",
        # 2D-1
        "defending",
        "guarded",
        "empowered",
        "hasted",
        "regenerating",
        "taunted",
        # 2D-2（feared、silenced、blinded 為 rare）
        "marked",
        "stoneskin",  # 3-54d：拿掉最低稀有（和護衛一致）
    }
    for status in rules.statuses.statuses:
        if status.budget_points is not None:
            expected = "common" if status.id in common_statuses else "rare"
            assert status.min_rarity == expected, status.id
    assert {c.min_rarity for c in rules.conditions.conditions} == {"rare"}
