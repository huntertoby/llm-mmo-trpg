"""1B 環境內容（物件、表面、互動表、天氣、反應、地圖擴充欄位）的 schema 與跨檔案驗證。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.battle import ReactionRule
from trpg.content.environment import (
    InteractionRule,
    ObjectDef,
    ReactionTable,
    SurfaceTable,
    WeatherDef,
)
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef, Objective
from trpg.shared.errors import ContentError
from trpg.shared.types import Element, Surface

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENT = PROJECT_ROOT / "content"


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library(CONTENT)


def _copy_content(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(CONTENT, target)
    return target


def test_required_objects_and_tags(library: ContentLibrary) -> None:
    objects = library.ruleset.objects.by_id()
    expect = {
        "wooden_bridge": {"breakable", "flammable", "over_chasm"},
        "oil_barrel": {"breakable", "flammable", "explosive", "pushable"},
        "stone_pillar": {"blocks_sight", "blocks_move", "breakable"},
        "grass": {"flammable", "conceal"},
        "crate": {"breakable", "pushable", "blocks_move"},
    }
    for oid, tags in expect.items():
        assert tags <= set(objects[oid].tags), oid
    assert objects["stone_pillar"].max_hp is not None
    assert objects["stone_pillar"].max_hp >= 4 * (objects["crate"].max_hp or 0)  # 高 HP
    barrel = objects["oil_barrel"]
    assert barrel.explosion is not None and barrel.explosion.radius == 1


def test_surfaces_cover_every_surface(library: ContentLibrary) -> None:
    table = library.ruleset.surfaces
    assert {s.id for s in table.surfaces} == {s for s in Surface if s is not Surface.NONE}
    ice = table.get(Surface.ICE)
    assert ice.on_enter is not None and ice.on_enter.check is not None
    assert (ice.on_enter.check.dc, ice.on_enter.check.fail_status) == (12, "prone")
    poison = table.get(Surface.POISON)
    assert poison.on_turn_start is not None and poison.on_turn_start.damage is not None
    assert str(poison.on_turn_start.damage.dice) == "1d4"
    holy = table.get(Surface.HOLY)
    assert holy.on_turn_start is not None
    assert holy.on_turn_start.heal is not None and holy.on_turn_start.damage is not None
    assert holy.on_turn_start.damage.only_tag == "undead"
    dark = table.get(Surface.DARKNESS)
    assert dark.blocks_sight and dark.conceal
    assert table.get(Surface.OIL).flammable


def test_interaction_table_covers_plan(library: ContentLibrary) -> None:
    """docs/專案計畫.md 5.1 互動表每一列都有對應的資料。"""
    rules = library.ruleset.interactions.rules
    keys = {
        (r.trigger, r.element or r.surface_created, r.target, r.surface or r.object_tag)
        for r in rules
    }
    expected = {
        ("element", Element.FIRE, "surface", Surface.OIL),
        ("element", Element.FIRE, "object", "flammable"),
        ("element", Element.FIRE, "object", "explosive"),
        ("element", Element.LIGHTNING, "surface", Surface.WATER),
        ("element", Element.LIGHTNING, "object", "conductive"),
        ("element", Element.ICE, "surface", Surface.WATER),
        ("element", Element.ICE, "object", "freezable"),
        ("element", Element.FIRE, "surface", Surface.ICE),
        ("surface_created", Surface.WATER, "surface", Surface.FIRE),
        ("element", Element.HOLY, "surface", Surface.POISON),
        ("element", Element.HOLY, "surface", Surface.DARKNESS),
        ("element", Element.WIND, "surface", Surface.FIRE),
        # 「風吹散毒」在 3-54a 移除（06 6.33：風吹到毒改為往風向擴散，由 trpg.engine.wind 結算）
        ("element", Element.WIND, "object", "pushable"),
        ("element", Element.WIND, "unit", None),
        ("element", Element.EARTH, "object", "over_chasm"),
    }
    assert expected <= keys
    caps = {(c.element, c.effect) for c in library.ruleset.interactions.capabilities}
    assert {
        (Element.SHADOW, "create_surface"),
        (Element.EARTH, "raise_terrain"),
        (Element.EARTH, "lower_terrain"),
        (Element.EARTH, "create_obstacle"),
        (Element.WIND, "push"),
    } <= caps


def test_weather_table(library: ContentLibrary) -> None:
    w = library.weather
    assert set(w) >= {"clear", "rain", "fog", "night"}
    assert w["rain"].element_damage_permille == {Element.FIRE: -300, Element.LIGHTNING: 200}
    assert w["rain"].puddles_per_round > 0
    assert w["fog"].sight_range_permille == 500 and w["fog"].ranged_disadvantage_beyond == 4
    assert w["night"].concealed_ranged_max_distance is not None


def test_reactions_defaults(library: ContentLibrary) -> None:
    table = library.ruleset.reactions
    block = table.by_id()["block"]
    assert (block.stamina_cost, block.damage_reduction_permille) == (10, 500)
    rules = {r.reaction: r for r in table.default_rules}
    assert rules["block"].when.event == "targeted_by_melee"
    assert rules["block"].unless is not None and rules["block"].unless.self_stamina_below == 20
    assert rules["opportunity_attack"].when.event == "enemy_leaves_adjacent"
    assert all(r.mode == "auto" for r in table.default_rules)
    assert library.ruleset.core.default_stamina == 30


# ---------------------------------------------------------------------------
# schema 驗證
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ({"id": "x", "name_zh": "x", "glyph": "x", "tags": ["sparkly"]}, "未知的物件標籤"),
        ({"id": "x", "name_zh": "x", "glyph": "x", "tags": ["breakable"]}, "max_hp"),
        (
            {
                "id": "x",
                "name_zh": "x",
                "glyph": "x",
                "max_hp": 3,
                "tags": ["breakable", "explosive"],
            },
            "explosion",
        ),
        ({"id": "x", "name_zh": "x", "glyph": "xx"}, "ASCII"),
    ],
)
def test_object_validation(data: dict[str, object], fragment: str) -> None:
    with pytest.raises(ValidationError, match=fragment):
        ObjectDef.model_validate(data)


def test_surface_table_requires_all() -> None:
    with pytest.raises(ValidationError, match="缺少表面"):
        SurfaceTable.model_validate({"surfaces": [{"id": "oil", "name_zh": "油", "glyph": "o"}]})


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ({"trigger": "element", "target": "surface", "surface": "oil"}, "必須設定 element"),
        ({"trigger": "element", "element": "fire", "target": "object"}, "object_tag"),
        (
            {"trigger": "element", "element": "fire", "target": "object", "object_tag": "shiny"},
            "未知的物件標籤",
        ),
        ({"trigger": "surface_created", "target": "surface", "surface": "oil"}, "surface_created"),
    ],
)
def test_interaction_rule_validation(data: dict[str, object], fragment: str) -> None:
    base = {"id": "r", "description_zh": "r", "then": [{"op": "keep"}]}
    with pytest.raises(ValidationError, match=fragment):
        InteractionRule.model_validate({**base, **data})


def test_outcome_requires_params() -> None:
    base = {"id": "r", "description_zh": "r", "trigger": "element", "element": "fire"}
    with pytest.raises(ValidationError, match="需要 surface"):
        InteractionRule.model_validate(
            {**base, "target": "surface", "surface": "oil", "then": [{"op": "set_surface"}]}
        )


def test_weather_validation() -> None:
    with pytest.raises(ValidationError, match="-1000"):
        WeatherDef.model_validate(
            {
                "id": "w",
                "name_zh": "w",
                "description_zh": "w",
                "element_damage_permille": {"fire": -2000},
            }
        )


def test_reaction_rule_must_match_definition() -> None:
    data = {
        "reactions": [
            {
                "id": "block",
                "name_zh": "格擋",
                "description_zh": "x",
                "effect": "reduce_damage",
                "events": ["targeted_by_melee"],
            }
        ],
        "default_rules": [{"reaction": "block", "when": {"event": "enemy_leaves_adjacent"}}],
    }
    with pytest.raises(ValidationError, match="不支援事件"):
        ReactionTable.model_validate(data)
    data["default_rules"] = [{"reaction": "dodge", "when": {"event": "targeted_by_melee"}}]
    with pytest.raises(ValidationError, match="未知的反應"):
        ReactionTable.model_validate(data)
    rule = ReactionRule.model_validate(
        {"reaction": "block", "when": {"event": "targeted_by_melee"}}
    )
    assert rule.mode == "auto"


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ({"kind": "escape"}, "rounds 與 tiles"),
        ({"kind": "eliminate", "rounds": 3}, "不需要"),
        ({"kind": "defend", "rounds": 3, "tiles": [[1, 1], [1, 1]]}, "重複"),
    ],
)
def test_objective_validation(data: dict[str, object], fragment: str) -> None:
    with pytest.raises(ValidationError, match=fragment):
        Objective.model_validate(data)


def _map(**overrides: object) -> dict[str, object]:
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


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"objects": [{"at": [1, 1], "kind": "crate"}, {"at": [1, 1], "kind": "grass"}]}, "重複"),
        ({"surfaces": [{"at": [5, 1], "surface": "oil"}]}, "超出地圖範圍"),
        ({"objective": {"kind": "escape", "rounds": 3, "tiles": [[9, 0]]}}, "超出地圖範圍"),
        (
            {
                "events": [
                    {
                        "kind": "spawn_units",
                        "round": 2,
                        "units": [{"template": "bandit", "at": [7, 0]}],
                    }
                ]
            },
            "超出地圖範圍",
        ),
        (
            {"events": [{"kind": "terrain_change", "round": 2, "tiles": [{"at": [1, 1]}]}]},
            "至少要改變",
        ),
    ],
)
def test_map_extension_validation(overrides: dict[str, object], fragment: str) -> None:
    with pytest.raises(ValidationError, match=fragment):
        MapDef.model_validate(_map(**overrides))


def _write_map(root: Path, **overrides: object) -> Path:
    path = root / "maps" / "test_flat_6x6.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(overrides)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"weather": "blizzard"}, "未知的天氣"),
        ({"encounter": {"allies": ["hero_fighter"], "enemies": ["dragon"]}}, "未知的單位範本"),
        (
            {
                "events": [
                    {
                        "kind": "spawn_units",
                        "round": 1,
                        "units": [{"template": "ghost", "at": [3, 3]}],
                    }
                ]
            },
            "未知的單位範本",
        ),
        (
            {
                "events": [
                    {
                        "kind": "terrain_change",
                        "round": 1,
                        "tiles": [{"at": [3, 3], "terrain": "goo"}],
                    }
                ]
            },
            "未知的地形",
        ),
        ({"surfaces": [{"at": [3, 3], "surface": "none"}]}, "不可為 none"),
        (
            {
                "objective": {"kind": "defend", "rounds": 3, "tiles": [[3, 3]]},
                "objects": [{"at": [3, 3], "kind": "crate"}],
            },
            "不可站立",
        ),
    ],
)
def test_library_map_references(
    tmp_path: Path, overrides: dict[str, object], fragment: str
) -> None:
    root = _copy_content(tmp_path)
    path = _write_map(root, **overrides)
    with pytest.raises(ContentError, match=fragment) as info:
        load_library(root)
    assert info.value.path == path


def test_library_unit_reaction_rules(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    path = root / "units" / "bandit.yaml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "reactions:\n  - reaction: block\n    when: {event: enemy_leaves_adjacent}\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="不支援事件"):
        load_library(root)


def test_library_surface_status_reference(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    path = root / "surfaces.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("fail_status: prone", "fail_status: petrified"),
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="未知的狀態"):
        load_library(root)


def test_interaction_apply_status_outcome_and_unit_surface_validation(
    library: ContentLibrary, tmp_path: Path
) -> None:
    rule = next(
        r for r in library.ruleset.interactions.rules if r.id == "ice_freezes_unit_in_water"
    )
    assert (rule.target, rule.unit_surface) == ("unit", Surface.WATER)
    assert (rule.then[0].op, rule.then[0].status, rule.then[0].duration) == (
        "apply_status",
        "frozen",
        1,
    )
    base = {
        "id": "bad_rule",
        "description_zh": "x",
        "trigger": "element",
        "element": "ice",
        "target": "unit",
        "then": [{"op": "apply_status", "status": "frozen"}],
    }
    InteractionRule.model_validate(base)
    with pytest.raises(ValidationError, match="apply_status 需要 status"):
        InteractionRule.model_validate({**base, "then": [{"op": "apply_status"}]})
    with pytest.raises(ValidationError, match="只有 apply_status"):
        InteractionRule.model_validate({**base, "then": [{"op": "keep", "status": "frozen"}]})
    with pytest.raises(ValidationError, match=r"unit_surface 只能用於 target: unit"):
        InteractionRule.model_validate(
            {**base, "target": "surface", "surface": "water", "unit_surface": "water"}
        )
    root = _copy_content(tmp_path)
    path = root / "interactions.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("status: frozen", "status: petrified"),
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match=r"interactions.yaml 引用了未知的狀態"):
        load_library(root)
