"""NW-1a T-A1：數值工坊的白名單 ``content/tuning_fields.yaml``。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir, load_content_file
from trpg.content.registry import KNOWN_CONTENT_FILES
from trpg.content.tuning_fields import (
    TUNING_FIELDS_FILE,
    TuningFields,
    format_path,
    load_tuning_fields,
    parse_path,
    path_matches,
    target_files,
    tuning_field_problems,
)
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.roguelite.save import ruleset_hash
from trpg.shared.errors import ContentError
from trpg.world.save import content_digest

CONTENT = bundled_content_dir()


@pytest.fixture(scope="module")
def table() -> TuningFields:
    return load_tuning_fields(CONTENT)


def test_bundled_whitelist_has_no_problems(table: TuningFields) -> None:
    assert tuning_field_problems(table, CONTENT) == []
    unit = table.target("unit")
    assert unit is not None
    paths = {f.path for f in unit.fields}
    assert {"max_hp", "speed", "armor_bonus", "max_mana", "stamina", "level"} <= paths
    assert {f"attributes.{a}" for a in ("str", "dex", "con", "int", "wis", "wil")} <= paths
    assert "phases[*].trigger.permille" in paths
    assert "phases[*].mana_restore" in paths  # BAL-21a 欄位（NW-1b 開放；開場階段不展開）
    assert all(f.label_zh for f in unit.fields)


def test_every_unit_file_validates_and_summons_are_not_targets(table: TuningFields) -> None:
    unit = table.target("unit")
    assert unit is not None
    files = target_files(CONTENT, unit)
    assert len(files) > 50
    ids = {p.stem for p in files}
    assert {"ashen_heart", "sect_mist_lock_master", "rift_shard_lord"} <= ids
    assert not any(i.startswith(("sim_", "hero_", "gear_tester", "training_dummy")) for i in ids)
    assert all(p.parent.name == "units" for p in files)  # units/summons/ 不開
    for path in files:
        template = load_content_file(path, UnitTemplate)
        assert not template.summon
        for phase_index, phase in enumerate(template.phases):
            if phase.trigger is not None and phase.trigger.kind == "hp_below":
                concrete = f"phases[{phase_index}].trigger.permille"
                assert unit.field_for(concrete) is not None


def _table(**target: object) -> TuningFields:
    base: dict[str, object] = {
        "kind": "unit",
        "label_zh": "敵人",
        "glob": "units/*.yaml",
        "fields": [{"path": "max_hp", "label_zh": "HP", "kind": "int", "note_zh": "說明"}],
    }
    return TuningFields.model_validate({"targets": [{**base, **target}]})


@pytest.mark.parametrize(
    ("path", "why"),
    [
        ("max_hpp", "對不到"),
        ("attributes.luck", "對不到"),
        ("resist.fire", "對不到"),  # 抗性分組沒有 fire（元素在 element_mods）
        ("name_zh", "不開"),
        ("weapon", "不開"),
        ("phases[*].id", "不開"),
        ("phases[*].trigger", "對不到"),  # 不是整數
        ("doll.rarity", "不開"),
    ],
)
def test_wrong_field_paths_are_rejected(path: str, why: str) -> None:
    bad = _table(fields=[{"path": path, "label_zh": "X", "kind": "int", "note_zh": "說明"}])
    problems = tuning_field_problems(bad)
    assert len(problems) == 1 and why in problems[0] and path in problems[0]


def test_forbidden_files_cannot_be_selected() -> None:
    assert "禁止表" in tuning_field_problems(_table(glob="skill_icon_*.yaml"))[0]
    assert "禁止表" in tuning_field_problems(_table(glob="rules/hit_table.yaml"))[0]
    table = TuningFields.model_validate(
        {**_table().model_dump(), "forbidden_files": ["units/ashen_heart.yaml"]}
    )
    assert tuning_field_problems(table) == []  # 沒給資料夾時只看 glob
    assert tuning_field_problems(table, CONTENT) == ["unit：units/ashen_heart.yaml 在禁止表內"]


def test_duplicate_paths_and_bad_hint_range_are_rejected() -> None:
    field = {"path": "max_hp", "label_zh": "HP", "kind": "int", "note_zh": "說明"}
    assert "重複" in tuning_field_problems(_table(fields=[field, field]))[0]
    bad = {**field, "hint_min": 5, "hint_max": 1}
    assert "建議範圍" in tuning_field_problems(_table(fields=[bad]))[0]


def test_load_raises_with_reasons(tmp_path: Path) -> None:
    (tmp_path / TUNING_FIELDS_FILE).write_text(
        "targets:\n  - {kind: unit, label_zh: 敵人, glob: units/*.yaml, fields: "
        "[{path: max_hpp, label_zh: X, kind: int, note_zh: 說明}]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="max_hpp"):
        load_tuning_fields(tmp_path)


def test_paths_round_trip() -> None:
    assert parse_path("phases[1].trigger.permille") == ("phases", 1, "trigger", "permille")
    assert format_path(("phases", 1, "trigger", "permille")) == "phases[1].trigger.permille"
    assert format_path(parse_path("phases[*].trigger.permille")) == "phases[*].trigger.permille"
    assert path_matches("phases[*].trigger.permille", "phases[2].trigger.permille")
    assert not path_matches("phases[*].trigger.permille", "phases.trigger.permille")
    assert not path_matches("max_hp", "max_hp.x")
    with pytest.raises(ValueError, match="格式"):
        parse_path("Max-HP")


def test_whitelist_is_not_content_and_does_not_change_digests(
    content_library: ContentLibrary, tmp_path: Path
) -> None:
    """第 0 節第 9 點：白名單不登記、不進 ``library.files``；拿掉它三個 digest 都不變。"""
    assert all(f.relative_path != TUNING_FIELDS_FILE for f in KNOWN_CONTENT_FILES)
    assert all(p.name != TUNING_FIELDS_FILE for p, _ in content_library.files)
    copy = tmp_path / "content"
    shutil.copytree(CONTENT, copy)
    (copy / TUNING_FIELDS_FILE).unlink()
    without = load_library(copy)
    assert ruleset_hash(without) == ruleset_hash(content_library)
    assert content_digest(without) == content_digest(content_library)
    assert hash_ruleset(without.ruleset) == hash_ruleset(content_library.ruleset)
