"""NW-2a T-A1：白名單的技能對象（``kind: skill``）與招式組欄位。"""

from __future__ import annotations

import pytest

from trpg.api.tuning.objects import concrete_fields, read_data
from trpg.content.loader import bundled_content_dir, load_content_file
from trpg.content.skills import SkillDef
from trpg.content.tuning_fields import (
    BUILTIN_FORBIDDEN,
    FORBIDDEN_SEGMENTS,
    TuningFields,
    effect_type_ids,
    load_tuning_fields,
    target_files,
    tuning_field_problems,
)

CONTENT = bundled_content_dir()


@pytest.fixture(scope="module")
def table() -> TuningFields:
    return load_tuning_fields(CONTENT)


def test_skill_target_covers_every_skill_file_except_gear(table: TuningFields) -> None:
    skill = table.target("skill")
    assert skill is not None
    files = target_files(CONTENT, skill)
    ids = {p.stem for p in files}
    assert (
        len(files) == 409
    )  # LW-1 加 3 招獨狼示範；BS-1 加 2 招（無聲步、影纏）；RG-1 加 3 招瞄準預告
    assert not any(i.startswith("skill_gear_") for i in ids)
    assert all(p.parent.name == "skills" for p in files)
    for path in files:  # 每個檔都合 schema、每個展開的路徑都找得到白名單欄位
        load_content_file(path, SkillDef)
        for field, concrete, _label in concrete_fields(read_data(path), skill):
            assert skill.field_for(concrete) is field


def test_effect_types_are_primitives_and_kinds_are_known(table: TuningFields) -> None:
    known = effect_type_ids(CONTENT)
    skill = table.target("skill")
    assert skill is not None
    for field in skill.all_fields():
        assert set(field.effect_types) <= known, field.path
    assert {"damage", "heal", "refund_ap", "damage_multiplier"} <= known
    assert tuning_field_problems(table, CONTENT) == []


def _paths(skill_id: str, table: TuningFields) -> dict[str, str]:
    skill = table.target("skill")
    assert skill is not None
    data = read_data(CONTENT / "skills" / f"{skill_id}.yaml")
    return {path: field.path for field, path, _l in concrete_fields(data, skill)}


def test_expansion_follows_kinds_existing_only_and_effect_types(table: TuningFields) -> None:
    fire = _paths("skill_fire_arrow", table)
    assert "ap_cost" in fire and "effects[0].multiplier_permille" in fire
    assert "cost.cooldown" in fire  # 沒寫可插入
    assert "effects[0].dice" not in fire  # 武器技沒有骰子（只有已寫的才展開）
    assert "crit_range" not in fire
    pinpoint = _paths("skill_pinpoint_shot", table)
    assert "effects[1].multiplier_permille" in pinpoint  # 區塊式的效果也展開
    passive = next(
        p.stem
        for p in sorted((CONTENT / "skills").glob("*.yaml"))
        if read_data(p).get("kind") == "passive"
    )
    assert "ap_cost" not in _paths(passive, table)  # ap_cost 只給主動
    stance = next(
        p.stem
        for p in sorted((CONTENT / "skills").glob("*.yaml"))
        if read_data(p).get("kind") == "stance"
    )
    assert "stance_upkeep" in _paths(stance, table)
    assert "stance_upkeep" not in fire
    # magnitude_permille 只給已寫的招
    for path in sorted((CONTENT / "skills").glob("*.yaml")):
        data = read_data(path)
        paths = _paths(path.stem, table)
        for concrete in paths:
            if concrete.endswith("magnitude_permille"):
                assert "magnitude_permille" in path.read_text(encoding="utf-8")
        if path.stem.startswith("skill_gear_"):
            continue
        assert data["id"] == path.stem


def test_unit_skill_lists_skip_the_opening_phase(table: TuningFields) -> None:
    unit = table.target("unit")
    assert unit is not None
    data = read_data(CONTENT / "units" / "ashen_heart.yaml")
    paths = {p for _f, p, _l in concrete_fields(data, unit)}
    assert {"skills", "phases[1].skills", "phases[2].skills"} <= paths
    assert "phases[0].skills" not in paths


def test_forbidden_structure_fields_cannot_be_opened() -> None:
    base = {
        "kind": "skill",
        "label_zh": "技能",
        "glob": "skills/*.yaml",
        "fields": [{"path": "ap_cost", "label_zh": "AP", "kind": "int", "note_zh": "說明"}],
    }
    for path, kind in (
        ("tier", "int"),
        ("effects[*].type", "int"),
        ("shape.type", "int"),
        ("budget_bonus_permille", "permille"),
        ("effects[*].dice", "int"),  # 型別不對：骰子不是整數
        ("ap_cost", "dice"),
    ):
        table = TuningFields.model_validate(
            {
                "targets": [
                    {
                        **base,
                        "fields": [
                            *base["fields"],
                            {"path": path, "label_zh": "X", "kind": kind, "note_zh": "說明"},
                        ],
                    }
                ]
            }
        )
        problems = tuning_field_problems(table)
        assert problems, path
    assert "skill_budget.yaml" not in BUILTIN_FORBIDDEN  # 只有例外清單由後端附帶改動
    assert {"type", "tier", "enemy_only", "budget_bonus_permille"} <= FORBIDDEN_SEGMENTS


def test_unknown_effect_type_is_reported() -> None:
    table = TuningFields.model_validate(
        {
            "targets": [
                {
                    "kind": "skill",
                    "label_zh": "技能",
                    "glob": "skills/*.yaml",
                    "fields": [
                        {"path": "ap_cost", "label_zh": "AP", "kind": "int", "note_zh": "x"}
                    ],
                    "effect_sites": ["effects[*]"],
                    "effect_fields": [
                        {
                            "path": "dice",
                            "label_zh": "骰",
                            "kind": "dice",
                            "note_zh": "x",
                            "effect_types": ["no_such_primitive"],
                        }
                    ],
                }
            ]
        }
    )
    assert any("no_such_primitive" in p for p in tuning_field_problems(table, CONTENT))
