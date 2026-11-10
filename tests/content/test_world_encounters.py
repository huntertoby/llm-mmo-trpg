"""大世界遭遇表（Phase 5A-3；``docs/phases/Phase5計畫.md`` 7.2 第 3 項、7.4）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_encounters import (
    MAX_GROUP_SIZE,
    MIN_GROUP_SIZE,
    NO_ENCOUNTER_KINDS,
    EncounterTable,
    encounter_table_problems,
)
from trpg.shared.errors import ContentError


@pytest.fixture(scope="module")
def table(library: ContentLibrary) -> EncounterTable:
    return library.world_encounters["cloud_ridge"]


def test_cloud_ridge_table_loaded(library: ContentLibrary, table: EncounterTable) -> None:
    assert table.ranged_cap == 2  # 18.2.1
    assert table.affixes == ("regenerating", "mist_veiled", "heart_linked", "berserk")
    assert 0 < table.camp_elite_permille <= 1000
    assert "遠程上限 2" in table.summary()
    rel = [p.relative_to(library.root).as_posix() for p, _ in library.files]
    assert "world/encounters/cloud_ridge.yaml" in rel


def test_ally_first_threads_exist(library: ContentLibrary, table: EncounterTable) -> None:
    """5A-6：遭遇表的 ``ally_first_threads``（18.4 補充：暗門）都是事件骨架的線頭。"""
    threads = {
        t for table_ in library.world_event_content.events.values() for t in table_.thread_ids()
    }
    wanted = {t for loc in table.locations for t in loc.ally_first_threads}
    assert wanted == {"gang_fort_secret_door"}
    assert wanted <= threads
    fort = table.location_by_id()["cliff_gang_fort"]
    assert fort.ally_first_threads == ("gang_fort_secret_door",)


def test_every_encounter_location_has_a_table(
    library: ContentLibrary, table: EncounterTable
) -> None:
    world_map = library.world_maps["cloud_ridge"]
    expected = {loc.id for loc in world_map.locations if loc.kind not in NO_ENCOUNTER_KINDS}
    assert set(table.location_by_id()) == expected
    assert len(expected) == 16


def test_lineups_respect_caps(library: ContentLibrary, table: EncounterTable) -> None:
    catalog = library.enemy_catalog()
    groups = table.group_by_id()
    for loc in table.locations:
        for weighted in loc.groups:
            group = groups[weighted.group]
            templates = [catalog.template(u) for u in group.units]
            if loc.elite is not None:
                templates.append(catalog.with_affix(catalog.template(loc.elite.unit), "berserk"))
            assert len(templates) + len(group.third) >= MIN_GROUP_SIZE  # 下限算第三方（CB-2d）
            assert len(templates) <= MAX_GROUP_SIZE
            assert sum(catalog.is_ranged(t) for t in templates) <= table.ranged_cap
            assert sum(catalog.is_elite(t) for t in templates) <= 1


def test_north_slope_fixed_elite(table: EncounterTable) -> None:
    elite = table.location_by_id()["north_slope"].elite
    assert elite is not None
    assert (elite.unit, elite.affix) == ("mist_wolf", "berserk")  # 懸賞「北坡狼王」


def test_every_new_enemy_appears(library: ContentLibrary, table: EncounterTable) -> None:
    # 5F-5a：荒原的敵人在荒原的遭遇表（所有區域一起算；含第三方）
    used = {u for t in library.world_encounters.values() for g in t.groups for u in g.all_units}
    season = library.world_season
    if season is not None:  # 懸賞的精英本體（5F-1b 霧中劍客）只出現在懸賞陣容
        used |= {b.elite.unit for b in season.bounties}
    new = {u for u, t in library.units.items() if {"sect", "beast", "construct"} & set(t.tags)}
    assert library.world_enemies is not None
    variants = {v.id for v in library.world_enemies.variants}
    assert new | variants <= used


def _data(table: EncounterTable) -> dict[str, Any]:
    return table.model_dump(mode="json")


def _problems(library: ContentLibrary, data: dict[str, Any]) -> list[str]:
    return encounter_table_problems(
        EncounterTable.model_validate(data),
        world_map=library.world_maps["cloud_ridge"],
        catalog=library.enemy_catalog(),
    )


def test_real_table_has_no_problems(library: ContentLibrary, table: EncounterTable) -> None:
    assert _problems(library, _data(table)) == []


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"ranged_cap": -1}, "ranged_cap"),
        ({"camp_elite_permille": 1001}, "camp_elite_permille"),
        ({"affixes": ["berserk", "berserk"]}, "詞綴重複"),
    ],
)
def test_schema_fields(table: EncounterTable, change: dict[str, Any], fragment: str) -> None:
    data = {**_data(table), **change}
    with pytest.raises(ValidationError, match=fragment):
        EncounterTable.model_validate(data)


def test_schema_groups_and_locations(table: EncounterTable) -> None:
    data = _data(table)
    data["groups"][0]["units"] = ["bandit"]
    with pytest.raises(ValidationError, match="至少 2 名"):
        EncounterTable.model_validate(data)
    data = _data(table)
    data["groups"][0]["units"] = ["bandit"] * 5
    with pytest.raises(ValidationError, match="units"):
        EncounterTable.model_validate(data)
    data = _data(table)
    data["groups"].append(dict(data["groups"][0]))
    with pytest.raises(ValidationError, match="陣容重複"):
        EncounterTable.model_validate(data)
    data = _data(table)
    data["locations"].append(dict(data["locations"][0]))
    with pytest.raises(ValidationError, match="地點重複"):
        EncounterTable.model_validate(data)
    data = _data(table)
    data["locations"][0]["groups"] = [{"group": "nobody", "weight": 1}]
    with pytest.raises(ValidationError, match="未知的陣容"):
        EncounterTable.model_validate(data)
    data = _data(table)
    data["locations"][0]["groups"][0]["weight"] = 0
    with pytest.raises(ValidationError, match="weight"):
        EncounterTable.model_validate(data)


def test_fixed_elite_must_fit(table: EncounterTable) -> None:
    data = _data(table)
    north = next(loc for loc in data["locations"] if loc["location"] == "north_slope")
    group = north["groups"][0]["group"]
    # 6E-3c：北坡狼群剩兩隻，補兩隻才超過（固定精英＋4 隻）
    next(g for g in data["groups"] if g["id"] == group)["units"].extend(["mist_wolf", "mist_wolf"])
    with pytest.raises(ValidationError, match="超過 4 名"):
        EncounterTable.model_validate(data)


def _location(data: dict[str, Any], loc_id: str) -> dict[str, Any]:
    found: dict[str, Any] = next(loc for loc in data["locations"] if loc["location"] == loc_id)
    return found


def _group(data: dict[str, Any], group_id: str) -> dict[str, Any]:
    found: dict[str, Any] = next(g for g in data["groups"] if g["id"] == group_id)
    return found


def test_unknown_unit_and_affix(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _group(data, "bandit_raiders")["units"][0] = "nobody"
    data["affixes"] = [*data["affixes"], "glowing"]
    problems = _problems(library, data)
    assert "陣容 bandit_raiders：未知的單位 nobody" in problems
    assert "未知的詞綴：glowing" in problems


def test_summon_is_not_an_enemy(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _group(data, "bandit_raiders")["units"][0] = "summon_golem"
    assert any("未知的單位 summon_golem" in p for p in _problems(library, data))


def test_ranged_cap(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _group(data, "bandit_raiders")["units"] = ["bandit_archer", "sect_crane_archer", "bandit"]
    _group(data, "bandit_raiders")["units"][2] = "sect_talisman_caster"  # 法器但算遠程
    problems = _problems(library, data)
    assert "陣容 bandit_raiders：遠程 3 名，超過上限 2" in problems


def test_two_elites(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _group(data, "bandit_raiders")["units"] = ["sect_steward", "bandit_captain", "bandit"]
    assert "陣容 bandit_raiders：精英 2 名（一場最多 1 名）" in _problems(library, data)


def test_elite_field_rules(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _location(data, "ferry_steps")["elite"] = {"unit": "bandit", "affix": "berserk"}
    _location(data, "north_slope")["elite"] = None
    problems = _problems(library, data)
    assert "地點 ferry_steps：只有精英巢穴可以填固定精英" in problems
    assert "地點 north_slope：精英巢穴必須有固定精英" in problems


def test_fixed_elite_affix_must_apply(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _location(data, "north_slope")["elite"] = {"unit": "sect_crane_archer", "affix": "berserk"}
    assert any("固定精英不能套用詞綴" in p for p in _problems(library, data))
    data = _data(table)
    _location(data, "north_slope")["elite"] = {"unit": "mist_wolf", "affix": "glowing"}
    assert "地點 north_slope：未知的詞綴 glowing" in _problems(library, data)


def test_lair_group_with_elite(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    _group(data, "north_slope_pack")["units"] = ["sect_steward", "mist_wolf", "mist_wolf"]
    assert any(
        "north_slope 的陣容 north_slope_pack：精英 2 名" in p for p in _problems(library, data)
    )


def test_missing_and_unknown_locations(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    data["locations"] = [loc for loc in data["locations"] if loc["location"] != "hunter_hut"]
    data["locations"].append({"location": "mist_ferry", "groups": [{"group": "bandit_raiders"}]})
    data["locations"].append({"location": "atlantis", "groups": [{"group": "bandit_raiders"}]})
    problems = _problems(library, data)
    assert "地點 hunter_hut 會遇敵，但沒有遭遇表" in problems
    assert "地點 mist_ferry（town）不會遇敵，不該有遭遇表" in problems
    assert "未知的地點：atlantis" in problems


def test_camp_group_needs_an_affix_target(library: ContentLibrary, table: EncounterTable) -> None:
    data = _data(table)
    data["affixes"] = ["berserk"]
    _group(data, "bandit_raiders")["units"] = ["bandit_archer", "sect_crane_archer"]
    problems = _problems(library, data)
    assert "地點 ferry_steps：陣容 bandit_raiders 沒有成員可以套用本區的詞綴" in problems


def test_region_without_world_map(library: ContentLibrary, table: EncounterTable) -> None:
    problems = encounter_table_problems(table, world_map=None, catalog=library.enemy_catalog())
    assert problems == ["區域 cloud_ridge 沒有地點圖"]


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def test_bad_file_raises_content_error(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "encounters" / "cloud_ridge.yaml"
    text = path.read_text(encoding="utf-8").replace("ranged_cap: 2", "ranged_cap: 0")
    path.write_text(text, encoding="utf-8", newline="\n")
    with pytest.raises(ContentError, match="遠程"):
        load_library(content)


def test_file_name_must_match_region(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    directory = content / "world" / "encounters"
    shutil.copy(directory / "cloud_ridge.yaml", directory / "zz_copy.yaml")
    with pytest.raises(ContentError, match="cloud_ridge"):
        load_library(content)


def test_without_encounter_folder(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    shutil.rmtree(content / "world" / "encounters")
    lib = load_library(content)
    assert lib.world_encounters == {}
    assert lib.world_enemies is not None
