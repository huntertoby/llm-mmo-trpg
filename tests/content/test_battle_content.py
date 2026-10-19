"""戰鬥內容（地形、武器、狀態、單位、地圖、規則包）的 schema 與跨檔案驗證測試。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.battle import Dice, StatusDef, UnitTemplate, WeaponDef
from trpg.content.library import ContentLibrary, Ruleset, load_library
from trpg.content.maps import MapDef, check_map
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute, Element, ResistGroup, Team

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENT = PROJECT_ROOT / "content"


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library(CONTENT)


def _copy_content(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(CONTENT, target)
    return target


# ---------------------------------------------------------------------------
# 實際資料
# ---------------------------------------------------------------------------


def test_library_loads(library: ContentLibrary) -> None:
    assert {"stone", "grass", "dirt", "chasm", "lava"} <= set(library.ruleset.terrain.by_id())
    assert set(library.weapons) >= {"one_handed_sword", "greatsword", "dagger", "bow", "fire_staff"}
    assert set(library.units) >= {
        "hero_fighter",
        "hero_archer",
        "hero_mage",
        "bandit",
        "bandit_archer",
        "bandit_boss",
    }
    assert set(library.maps) >= {"test_flat_6x6", "test_heights_8x8"}


def test_weapons_match_spec(library: ContentLibrary) -> None:
    w = library.weapons
    expect = {
        "one_handed_sword": (1, "1d8", Attribute.STR, Element.PHYSICAL, 20),
        "greatsword": (1, "2d6", Attribute.STR, Element.PHYSICAL, 20),
        "dagger": (1, "1d4", Attribute.DEX, Element.PHYSICAL, 19),
        "bow": (8, "1d8", Attribute.DEX, Element.PHYSICAL, 20),
        "fire_staff": (5, "1d6", Attribute.INT, Element.FIRE, 20),
    }
    for wid, (rng, dice, attr, elem, crit) in expect.items():
        weapon = w[wid]
        assert (weapon.range, str(weapon.dice), weapon.scaling_attr, weapon.element) == (
            rng,
            dice,
            attr,
            elem,
        )
        assert weapon.crit_range == crit
    assert w["greatsword"].two_handed
    assert w["dagger"].is_melee and not w["bow"].is_melee


def test_terrain_flags(library: ContentLibrary) -> None:
    terrain = library.ruleset.terrain.by_id()
    assert terrain["chasm"].deadly and not terrain["chasm"].walkable
    assert terrain["lava"].deadly
    assert terrain["stone"].walkable and not terrain["stone"].deadly


def test_boss_tags(library: ContentLibrary) -> None:
    boss = library.unit("bandit_boss")
    assert "steadfast" in boss.tags and "elite" in boss.tags
    assert boss.resist[ResistGroup.PHYSICAL] == 150
    assert boss.resist[ResistGroup.SPIRIT] == 0


def test_statuses(library: ContentLibrary) -> None:
    statuses = library.ruleset.statuses.by_id()
    burning = statuses["burning"]
    assert burning.duration == 2
    assert burning.on_turn_start_damage is not None
    assert str(burning.on_turn_start_damage.dice) == "1d6"
    assert statuses["defending"].expires == "own_turn_start"


def test_unknown_lookups(library: ContentLibrary) -> None:
    with pytest.raises(KeyError, match="未知的單位範本"):
        library.unit("dragon")
    with pytest.raises(KeyError, match="未知的地圖"):
        library.map("nowhere")


# ---------------------------------------------------------------------------
# 骰子、武器、單位、狀態
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "count", "sides"), [("1d8", 1, 8), ("2d6", 2, 6), (" 3 d 4 ", 3, 4)]
)
def test_dice_parse(text: str, count: int, sides: int) -> None:
    dice = Dice.model_validate(text)
    assert (dice.count, dice.sides) == (count, sides)
    assert Dice.model_validate(dice.model_dump()) == dice
    assert dice.model_dump_json() == f'"{count}d{sides}"'


@pytest.mark.parametrize("text", ["d6", "1d", "0d6", "1d0", "abc", "1x6"])
def test_dice_rejects(text: str) -> None:
    with pytest.raises(ValidationError):
        Dice.model_validate(text)


def _unit_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "test_unit",
        "name_zh": "測試",
        "attributes": {a.value: 10 for a in Attribute},
        "max_hp": 10,
        "weapon": "dagger",
    }
    data.update(overrides)
    return data


def test_unit_defaults() -> None:
    unit = UnitTemplate.model_validate(_unit_data())
    assert unit.speed == 5
    assert unit.resist == dict.fromkeys(ResistGroup, 0)
    assert unit.element_mods == {}


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"attributes": {"str": 10}}, "缺少屬性"),
        ({"attributes": {a.value: 0 for a in Attribute}}, "屬性值"),
        ({"resist": {"physical": 2000}}, "分組抗性"),
        ({"resist": {"fire": 100}}, "resist"),
        ({"element_mods": {"fire": -2000}}, "個別元素"),
        ({"tags": ["Elite"]}, "snake_case"),
        ({"tags": ["elite", "elite"]}, "重複"),
        ({"max_hp": 0}, "max_hp"),
        ({"hp": 3}, "hp"),
    ],
)
def test_unit_validation(overrides: dict[str, object], fragment: str) -> None:
    with pytest.raises(ValidationError, match=fragment):
        UnitTemplate.model_validate(_unit_data(**overrides))


def test_weapon_validation() -> None:
    base = {
        "id": "w",
        "name_zh": "武",
        "weapon_class": "melee",
        "range": 1,
        "dice": "1d4",
        "scaling_attr": "str",
    }
    assert WeaponDef.model_validate(base).crit_range == 20
    with pytest.raises(ValidationError, match="weapon_class"):
        WeaponDef.model_validate({**base, "weapon_class": "staff"})
    with pytest.raises(ValidationError):
        WeaponDef.model_validate({**base, "range": 0})
    with pytest.raises(ValidationError):
        WeaponDef.model_validate({**base, "crit_range": 21})


def test_status_turn_end_requires_duration() -> None:
    with pytest.raises(ValidationError, match="duration"):
        StatusDef.model_validate(
            {
                "id": "x",
                "name_zh": "x",
                "description_zh": "x",
                "expires": "turn_end",
                "polarity": "neutral",
            }
        )


def test_ruleset_detects_stale_hit_table(library: ContentLibrary) -> None:
    rs = library.ruleset
    with pytest.raises(ValidationError, match="gen_hit_table"):
        Ruleset.model_validate({**dict(rs), "core": rs.core.model_copy(update={"hit_slope": 3})})


# ---------------------------------------------------------------------------
# 地圖
# ---------------------------------------------------------------------------


def _map_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "m",
        "name_zh": "地圖",
        "archetype": "test",
        "size": [4, 3],
        "heights": "0000\n0000\n0000\n",
        "terrain": "....\n....\n....\n",
        "legend": {".": "stone", "x": "chasm"},
        "start_zones": {"ally": [[0, 2]], "enemy": [[3, 0]]},
    }
    data.update(overrides)
    return data


def test_map_accessors() -> None:
    m = MapDef.model_validate(_map_data(heights="0123\n0000\n0000"))
    assert (m.width, m.height) == (4, 3)
    assert m.tile_height(3, 0) == 3
    assert m.tile_terrain(0, 0) == "stone"
    assert m.grid()[0][2] == (2, "stone")


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"heights": "0000\n0000\n"}, "heights 應有 3 行"),
        ({"terrain": "....\n...\n....\n"}, "terrain 第 1 行應有 4 個字元"),
        ({"heights": "0004\n0000\n0000\n"}, "高度必須是 0–3"),
        ({"heights": "000a\n0000\n0000\n"}, "高度必須是 0–3"),
        ({"terrain": "...?\n....\n....\n"}, "legend 缺少字元"),
        ({"legend": {"..": "stone"}}, "單一字元"),
        ({"start_zones": {"ally": [[0, 2]]}}, "缺少 enemy"),
        ({"start_zones": {"ally": [[9, 2]], "enemy": [[3, 0]]}}, "超出地圖範圍"),
        ({"start_zones": {"ally": [[0, 2]], "enemy": [[0, 2]]}}, "重複出現"),
        ({"size": [0, 3]}, "size"),
        ({"objects": [{"at": [9, 9], "kind": "crate"}]}, "objects"),
    ],
)
def test_map_shape_validation(overrides: dict[str, object], fragment: str) -> None:
    with pytest.raises(ValidationError, match=fragment):
        MapDef.model_validate(_map_data(**overrides))


def test_check_map_cross_file(library: ContentLibrary) -> None:
    terrain = library.ruleset.terrain.by_id()
    core = library.ruleset.core
    ok = MapDef.model_validate(_map_data())
    assert check_map(ok, terrain, core) == []

    on_chasm = MapDef.model_validate(_map_data(terrain="....\n....\nx...\n"))
    assert "不可站立" in check_map(on_chasm, terrain, core)[0]

    unknown = MapDef.model_validate(_map_data(legend={".": "marble"}))
    assert "未知的地形" in check_map(unknown, terrain, core)[0]

    # 一整排深淵把雙方隔開
    split = MapDef.model_validate(_map_data(terrain="....\nxxxx\n....\n"))
    problems = check_map(split, terrain, core)
    assert problems and all("連通性" in p for p in problems)

    # 往上兩層的牆：敵方可以往下走過來，我方爬不上去 → 我方起始格無法抵達
    wall = MapDef.model_validate(_map_data(heights="2222\n2222\n0000\n"))
    problems = check_map(wall, terrain, core)
    assert len(problems) == 1 and "start_zones.ally" in problems[0]

    # 一層一層的階梯可通行
    stairs = MapDef.model_validate(_map_data(heights="2222\n1111\n0000\n"))
    assert check_map(stairs, terrain, core) == []

    # 物件：未知種類報錯；blocks_move 的物件擋住起始區
    objects = library.ruleset.objects.by_id()
    with_objects = MapDef.model_validate(_map_data(objects=[{"at": [1, 1], "kind": "crate"}]))
    assert check_map(with_objects, terrain, core, objects) == []
    assert "未知的物件" in check_map(with_objects, terrain, core)[0]
    on_crate = MapDef.model_validate(_map_data(objects=[{"at": [0, 2], "kind": "crate"}]))
    assert "不可站立" in check_map(on_crate, terrain, core, objects)[0]
    # 木橋讓深淵可以通過
    bridged = MapDef.model_validate(
        _map_data(
            terrain="....\nxxxx\n....\n",
            objects=[{"at": [2, 1], "kind": "wooden_bridge"}],
        )
    )
    assert check_map(bridged, terrain, core, objects) == []
    walled = MapDef.model_validate(
        _map_data(
            terrain="....\nx...\n....\n",
            objects=[{"at": [x, 1], "kind": "stone_pillar"} for x in (1, 2, 3)],
        )
    )
    assert all("連通性" in p for p in check_map(walled, terrain, core, objects))


def test_real_maps_start_zones(library: ContentLibrary) -> None:
    m = library.map("test_heights_8x8")
    assert m.start_zones[Team.ALLY][0] == (0, 6)
    assert m.tile_terrain(3, 2) == "chasm"
    assert m.tile_height(3, 2) == 2


# ---------------------------------------------------------------------------
# load_library 的錯誤情境
# ---------------------------------------------------------------------------


def test_library_unknown_weapon(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    path = root / "units" / "bandit.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("dagger", "laser"), encoding="utf-8")
    with pytest.raises(ContentError, match="未知的武器") as info:
        load_library(root)
    assert info.value.path == path


def test_library_filename_must_match_id(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    (root / "units" / "bandit.yaml").rename(root / "units" / "thief.yaml")
    with pytest.raises(ContentError, match="檔名必須與 id 相同"):
        load_library(root)


def test_library_broken_map(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    path = root / "maps" / "test_flat_6x6.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["start_zones"]["ally"] = [[0, 0], [7, 7]]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="超出地圖範圍") as info:
        load_library(root)
    assert info.value.path == path


def test_library_disconnected_map(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    path = root / "maps" / "test_flat_6x6.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["terrain"] = "......\n......\nxxxxxx\n......\n......\n......\n"
    data["legend"]["x"] = "chasm"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="連通性"):
        load_library(root)


def test_library_missing_units_dir(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    shutil.rmtree(root / "units")
    with pytest.raises(ContentError, match="找不到資料夾"):
        load_library(root)


def test_library_stale_hit_table(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    core = root / "rules" / "core.yaml"
    core.write_text(
        core.read_text(encoding="utf-8").replace("hit_mod_cap: 8", "hit_mod_cap: 6"),
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="gen_hit_table"):
        load_library(root)
