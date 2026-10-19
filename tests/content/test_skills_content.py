"""技能資料檔與 schema 的驗證（docs/phases/Phase2A計畫.md 3.1–3.5、5.5 第 6 條）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.library import load_library
from trpg.content.skills import (
    REQUIRED_CONDITIONS,
    REQUIRED_SHAPES,
    SKELETON_IDS,
    SkillDef,
    default_affects,
)
from trpg.shared.errors import ContentError

SHAPES = ("self", "single", "line", "cone", "cross", "square3", "ring", "ground_tile")


def _skill(**overrides: Any) -> dict[str, Any]:
    """灰燼誓約（規格 3.2 的範例）為基礎的技能資料。"""
    data: dict[str, Any] = yaml.safe_load(
        (PROJECT_ROOT / "content/skills/skill_ashen_oath.yaml").read_text("utf-8")
    )
    data.update(overrides)
    return data


def _lib_with(tmp_path: Path, skill: dict[str, Any] | None = None, **units: Any) -> Path:
    """複製 content/ 到暫存資料夾，加入一個技能（檔名 = id）與修改過的單位範本。"""
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    if skill is not None:
        (root / "skills" / f"{skill['id']}.yaml").write_text(
            yaml.safe_dump(skill, allow_unicode=True), encoding="utf-8"
        )
    for unit_id, changes in units.items():
        path = root / "units" / f"{unit_id}.yaml"
        data = yaml.safe_load(path.read_text("utf-8"))
        data.update(changes)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return root


def _rejects(tmp_path: Path, fragment: str, skill: dict[str, Any]) -> None:
    root = _lib_with(tmp_path / str(skill["id"]), skill)
    with pytest.raises(ContentError) as info:
        load_library(root)
    message = str(info.value)
    assert skill["id"] in message, message
    assert fragment in message, message


def test_all_demo_skills_load_and_cover_shapes_and_primitives() -> None:
    lib = library()
    skills = list(lib.skills.values())
    assert len(skills) >= 12
    assert {s.shape.type for s in skills} == set(REQUIRED_SHAPES)
    assert {s.category for s in skills} == {"weapon", "spell"}
    assert {s.weapon_req for s in skills} == {"melee", "ranged", "focus", "any"}
    used = {e.type for s in skills for e in s.effects}
    # destroy_object、raise_terrain、lower_terrain 由測試專用技能覆蓋
    assert used >= set(lib.ruleset.primitives.by_id()) - {
        "destroy_object",
        "raise_terrain",
        "lower_terrain",
    }
    assert all(s.skeleton in SKELETON_IDS for s in skills)
    assert lib.ruleset.skill_def("skill_ashen_oath").name_zh == "灰燼誓約"


def test_ashen_oath_example_matches_spec() -> None:
    skill = library().skills["skill_ashen_oath"]
    assert (skill.tier, skill.rarity, skill.kind, skill.skeleton) == (2, "rare", "active", "area")
    assert (skill.category, skill.weapon_req, skill.ap_cost, skill.scaling_attr.value) == (
        "spell",
        "focus",
        2,
        "int",
    )
    assert skill.shape.type == "cone" and skill.shape.size == 3
    assert [e.type for e in skill.effects] == ["damage", "create_surface"]
    assert (skill.cost.mana, skill.cost.cooldown) == (12, 2)
    assert skill.provenance.origin == "builtin" and skill.provenance.bound
    assert not skill.provenance.tradeable


def test_default_affects_follow_primitive_harmfulness() -> None:
    prims = library().ruleset.primitives.by_id()
    assert default_affects(prims["damage"]) == "enemies"
    assert default_affects(prims["heal"]) == "allies"
    assert default_affects(prims["create_surface"]) == "tiles"
    assert default_affects(prims["teleport"]) == "self"


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"category": "weapon", "weapon_req": "focus"}, "weapon_req 只能是 melee、ranged"),
        ({"category": "spell", "weapon_req": "melee"}, "weapon_req 只能是 focus、any"),
        ({"ap_cost": None}, "ap_cost 必須是 1 到 3"),
        ({"ap_cost": 4}, "ap_cost 必須是 1 到 3"),
        ({"kind": "passive", "ap_cost": 2}, "ap_cost 必須為 null"),
        ({"skeleton": "blob"}, "未知的骨架"),
        ({"id": "ashen"}, "id"),
        ({"cost": {"mana": 1, "cooldown": 7}}, "cooldown"),
        ({"effects": []}, "效果原語必須有 1 到 4 個"),
        ({"tier": 6}, "tier"),
    ],
)
def test_schema_rejections_have_chinese_messages(overrides: dict[str, Any], fragment: str) -> None:
    with pytest.raises(ValidationError) as info:
        SkillDef.model_validate(_skill(**overrides))
    assert fragment in str(info.value)


def test_more_than_four_effects_rejected() -> None:
    effects = [{"type": "damage", "dice": "1d4", "element": "fire"}] * 5
    with pytest.raises(ValidationError, match="效果原語必須有 1 到 4 個，收到 5 個"):
        SkillDef.model_validate(_skill(effects=effects))
    four = SkillDef.model_validate(_skill(effects=effects[:4]))
    assert len(four.effects) == 4


@pytest.mark.parametrize("distance", [0, 3])
@pytest.mark.parametrize("kind", ["push", "pull"])
def test_push_and_pull_distance_limited_to_two(kind: str, distance: int) -> None:
    effects = [{"type": kind, "distance": distance}]
    with pytest.raises(ValidationError, match="推擊與拉扯的距離必須是 1 到 2 格"):
        SkillDef.model_validate(_skill(effects=effects))


def test_spell_damage_requires_dice_and_element_and_weapon_damage_forbids_dice() -> None:
    with pytest.raises(ValidationError, match="法術技的傷害必須指定 dice 與 element"):
        SkillDef.model_validate(_skill(effects=[{"type": "damage", "dice": "1d6"}]))
    weapon = _skill(category="weapon", weapon_req="melee", scaling_attr="str")
    weapon["effects"] = [{"type": "damage", "dice": "1d6"}]
    with pytest.raises(ValidationError, match="武器技的傷害骰來自武器"):
        SkillDef.model_validate(weapon)


def test_unknown_primitive_rejected_at_load(tmp_path: Path) -> None:
    skill = _skill(id="skill_t_unknown", effects=[{"type": "meteor"}])
    _rejects(tmp_path, "未知的效果原語 'meteor'", skill)


def test_unknown_shape_rejected_at_load(tmp_path: Path) -> None:
    skill = _skill(id="skill_t_shape", shape={"type": "spiral", "size": 3})
    _rejects(tmp_path, "未知的形狀 'spiral'", skill)


def test_unknown_trap_shape_rejected_at_load(tmp_path: Path) -> None:
    """Phase 2F-1 3.2：TrapSpec.shape 不再是 Literal，而是在載入時對照 shapes 內容檢查。"""
    data: dict[str, Any] = yaml.safe_load(
        (PROJECT_ROOT / "content/skills/skill_bear_trap.yaml").read_text("utf-8")
    )
    data["id"] = "skill_t_trap_shape"
    data["trap"]["shape"] = "spiral"
    _rejects(tmp_path, "trap.shape：未知的形狀 'spiral'", data)


def test_shape_parameter_out_of_range_rejected_at_load(tmp_path: Path) -> None:
    _rejects(
        tmp_path,
        "cone 的 size 必須在 2–4，收到 9",
        _skill(id="skill_t_r", shape={"type": "cone", "size": 9}),
    )
    _rejects(tmp_path, "缺少參數 size", _skill(id="skill_t_m", shape={"type": "cone"}))
    _rejects(
        tmp_path,
        "不接受參數 radius",
        _skill(id="skill_t_x", shape={"type": "cone", "size": 3, "radius": 1}),
    )


def test_primitive_parameter_problems_rejected_at_load(tmp_path: Path) -> None:
    surface = {"type": "create_surface", "surface": "fire", "distance": 1}
    _rejects(
        tmp_path,
        "效果 create_surface 不接受參數 distance",
        _skill(id="skill_t_p1", effects=[surface]),
    )
    _rejects(
        tmp_path,
        "未知的狀態 'frozen'",
        _skill(id="skill_t_p2", effects=[{"type": "apply_status", "status": "frozen"}]),
    )
    _rejects(
        tmp_path,
        "未知的物件 'tower'",
        _skill(id="skill_t_p3", effects=[{"type": "create_obstacle", "object": "tower"}]),
    )
    _rejects(
        tmp_path,
        "缺少必要參數 surface",
        _skill(id="skill_t_p4", effects=[{"type": "create_surface"}]),
    )


def test_teleport_only_with_ground_tile_and_self_affects(tmp_path: Path) -> None:
    _rejects(
        tmp_path,
        "teleport 只能搭配形狀 ground_tile",
        _skill(
            id="skill_t_tp", shape={"type": "single", "range": 3}, effects=[{"type": "teleport"}]
        ),
    )
    _rejects(
        tmp_path,
        "teleport 只能對施放者",
        _skill(
            id="skill_t_tp2",
            shape={"type": "ground_tile", "range": 3},
            effects=[{"type": "teleport", "affects": "enemies"}],
        ),
    )


def test_unit_weapon_incompatible_with_skill_rejected_at_load(tmp_path: Path) -> None:
    # 法師的武器是法器；弓手的箭技需要遠程武器
    root = _lib_with(tmp_path, hero_mage={"skills": ["skill_piercing_shot"]})
    with pytest.raises(ContentError) as info:
        load_library(root)
    message = str(info.value)
    assert "hero_mage.yaml" in message
    assert "需要遠程武器，但單位的武器是法器" in message


def test_unit_skill_slots_exceeded_rejected_at_load(tmp_path: Path) -> None:
    seven = [
        "skill_fire_bolt",
        "skill_ashen_oath",
        "skill_blink",
        "skill_chain_lightning",
        "skill_summon_tide",
        "skill_stone_wall",
        "skill_sanctuary",
    ]
    root = _lib_with(tmp_path, hero_mage={"skills": seven})
    with pytest.raises(ContentError) as info:
        load_library(root)
    assert "主動技能超過欄位上限：7 個（上限 6）" in str(info.value)


def test_unit_unknown_skill_rejected_at_load(tmp_path: Path) -> None:
    root = _lib_with(tmp_path, hero_mage={"skills": ["skill_nope"]})
    with pytest.raises(ContentError, match="未知的技能 'skill_nope'"):
        load_library(root)


def test_any_weapon_skill_compatible_with_every_weapon_class() -> None:
    lib = library()
    blink = lib.skills["skill_blink"]
    assert blink.weapon_req == "any"
    from trpg.content.skills import weapon_problem  # noqa: PLC0415

    assert all(weapon_problem(blink, c) is None for c in ("melee", "ranged", "focus"))
    assert weapon_problem(lib.skills["skill_fire_bolt"], "melee") is not None


def test_skill_files_must_be_named_after_their_id(tmp_path: Path) -> None:
    root = _lib_with(tmp_path)
    data = _skill(id="skill_other")
    (root / "skills" / "skill_wrong_name.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(ContentError, match="檔名必須與 id 相同"):
        load_library(root)


def test_shape_table_must_define_every_engine_shape(tmp_path: Path) -> None:
    root = _lib_with(tmp_path)
    path = root / "skill_shapes.yaml"
    data = yaml.safe_load(path.read_text("utf-8"))
    data["shapes"] = [s for s in data["shapes"] if s["id"] != "chain"]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="缺少引擎實作的形狀：chain"):
        load_library(root)


# ---------------------------------------------------------------------------
# 條件（Phase 2A-2 6.1）
# ---------------------------------------------------------------------------


def test_condition_table_defines_every_engine_condition_with_a_harshness() -> None:
    table = library().ruleset.conditions
    assert {c.id for c in table.conditions} == set(REQUIRED_CONDITIONS)
    assert {c.harshness for c in table.conditions} == {"common", "harsh"}


def test_demo_skills_use_conditions_at_both_levels() -> None:
    skills = list(library().skills.values())
    assert any(s.condition is not None for s in skills)
    assert any(e.condition is not None for s in skills for e in s.effects)


@pytest.mark.parametrize(
    ("condition", "fragment"),
    [
        ({"type": "moon_phase"}, "未知的條件 'moon_phase'"),
        ({"type": "target_hp_below"}, "缺少必要參數 permille"),
        ({"type": "target_hp_below", "permille": 1000}, "必須在 1–999"),
        ({"type": "height_advantage", "permille": 300}, "不接受參數 permille"),
        ({"type": "target_has_status", "status": "petrified"}, "未知的狀態 'petrified'"),
        ({"type": "target_on_surface"}, "缺少必要參數 surface"),
    ],
)
@pytest.mark.parametrize("level", ["skill", "effect"])
def test_condition_problems_are_rejected_at_load(
    tmp_path: Path, condition: dict[str, Any], fragment: str, level: str
) -> None:
    data = _skill(id="skill_t_bad_condition")
    if level == "skill":
        data["condition"] = condition
    else:
        data["effects"] = [{**data["effects"][0], "condition": condition}]
    _rejects(tmp_path, fragment, data)


def test_a_valid_condition_loads_and_unknown_condition_fields_are_rejected() -> None:
    ok = SkillDef.model_validate(
        _skill(condition={"type": "target_on_surface", "surface": "water"})
    )
    assert ok.condition is not None and ok.condition.surface is not None
    with pytest.raises(ValidationError):
        SkillDef.model_validate(_skill(condition={"type": "self_hp_below", "bogus": 1}))
