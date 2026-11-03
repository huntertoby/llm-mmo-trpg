"""``content/world/rules.yaml``（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.4）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_rules import WorldRules, world_rules_problems
from trpg.shared.errors import ContentError


def _rules_dict(library: ContentLibrary) -> dict[str, object]:
    assert library.world_rules is not None
    return library.world_rules.model_dump()


def test_loaded(library: ContentLibrary) -> None:
    rules = library.world_rules
    assert rules is not None
    assert rules.camp_cost == 1  # #114「花 1 補給」
    assert rules.perception.dc_for(5) == 12  # #112 例：丹爐洞 5 級＝12
    assert rules.perception.dc_for(6) == 13  # 鶴歸崖 6 級＝13
    assert rules.encounter.permille_for(None) == 0
    assert rules.encounter.permille_for(1) <= rules.encounter.permille_for(6)
    assert {w.region for w in rules.weather} == {
        "crystal_crown",
        "cloud_ridge",
        "arcane_hub",
        "ashen_waste",
        "frost_tide",
    }
    cloud = rules.weather_for("cloud_ridge")
    heavy = {k for k, v in cloud.day.items() if v == max(cloud.day.values())}
    assert heavy == {"fog", "rain"}  # 05 5.1：雲嶺偏霧、雨
    assert world_rules_problems(rules, regions=library.regions, weather_ids=library.weather) == []
    assert any(path.as_posix().endswith("world/rules.yaml") for path, _ in library.files)


def test_encounter_cap(library: ContentLibrary) -> None:
    rules = library.world_rules
    assert rules is not None
    assert rules.encounter.permille_for(99) == rules.encounter.max_permille


def test_unknown_weather_and_region(library: ContentLibrary) -> None:
    data = _rules_dict(library)
    data["weather"] = [{"region": "nowhere", "day": {"hail": 1}, "night": {"night": 1}}]
    rules = WorldRules.model_validate(data)
    problems = world_rules_problems(rules, regions=library.regions, weather_ids=library.weather)
    assert any("未知的天氣 hail" in p for p in problems)
    assert any("未知的區域 nowhere" in p for p in problems)


@pytest.mark.parametrize(
    "patch",
    [
        {"supplies": {"max": 3, "start": 5}},
        {"default_weather": {"day": {"clear": 0}, "night": {"night": 1}}},
        {"default_weather": {"day": {"clear": -1, "rain": 2}, "night": {"night": 1}}},
        {"hasten": {"cost": 1, "encounter_permille": 1200}},
        {"perception": {"dc_base": 10, "level_divisor": 0}},
    ],
)
def test_invalid_values(library: ContentLibrary, patch: dict[str, object]) -> None:
    data = {**_rules_dict(library), **patch}
    with pytest.raises(ValidationError):
        WorldRules.model_validate(data)


def test_duplicate_region(library: ContentLibrary) -> None:
    data = _rules_dict(library)
    entry = {"region": "cloud_ridge", "day": {"clear": 1}, "night": {"night": 1}}
    data["weather"] = [entry, entry]
    with pytest.raises(ValidationError, match="重複"):
        WorldRules.model_validate(data)


def _copy(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def test_missing_rules_file_is_none(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy(tmp_path, library)
    (content / "world" / "rules.yaml").unlink()
    assert load_library(content).world_rules is None


def test_bad_rules_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy(tmp_path, library)
    path = content / "world" / "rules.yaml"
    text = path.read_text(encoding="utf-8").replace("{clear: 3, rain: 1", "{hail: 3, rain: 1", 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    with pytest.raises(ContentError, match="hail"):
        load_library(content)


def test_field_rules_loaded_with_old_defaults(library: ContentLibrary) -> None:
    """6C-R2：實地地圖的規則數值搬進 ``field:`` 區塊，數值和原本程式裡的常數相同。"""
    assert library.world_rules is not None
    field = library.world_rules.field
    assert (field.sight_range, field.sneak_sight()) == (4, 2)  # 21.10 第 3、6 條
    assert field.perceive_range == 3  # 21.10 第 17 條
    assert (field.cut_size, field.min_enemy_cells, field.min_ally_cells) == (12, 4, 3)
    assert field.walk_max_steps == 30


def test_field_rules_default_when_block_missing(library: ContentLibrary) -> None:
    """沒寫 ``field:`` 的舊 content 照常載入，用同樣的預設值；不合法的數值擋下。"""
    assert library.world_rules is not None
    data = _rules_dict(library)
    data.pop("field")
    assert WorldRules.model_validate(data).field == library.world_rules.field
    with pytest.raises(ValidationError):
        WorldRules.model_validate({**data, "field": {"sneak_sight_divisor": 0}})
