"""GB-1a 不動巨型頭目的內容 schema 與檢查（05 5.12.4、``PhaseGB計畫.md`` T13）：合成巨人只在測試裡，
``content/`` 不改。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import giant_template, library, make_map, template
from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.library.giant_checks import giant_problems
from trpg.content.maps import Encounter, MapDef
from trpg.content.roguelite import EncounterStep

GIANT = "test_giant"
FLAT = "\n".join("00000000" for _ in range(9))


def check(lib: ContentLibrary, **changes: Any) -> list[str]:
    units: dict[str, UnitTemplate] = {**lib.units, GIANT: giant_template(id=GIANT)}
    units.update(changes.pop("units", {}))
    maps = {**lib.maps, **changes.pop("maps", {})}
    return giant_problems(
        units,
        maps,
        terrain=lib.ruleset.terrain.by_id(),
        objects=lib.ruleset.objects.by_id(),
        roguelite=changes.pop("roguelite", lib.roguelite),
        world_maps=lib.world_maps,
        world_encounters=changes.pop("world_encounters", lib.world_encounters),
    )


def boss_map(**kw: Any) -> MapDef:
    m = make_map(FLAT, ally=[(4, 8)], enemy=[(4, 3), (1, 1)], **kw)
    return m.model_copy(
        update={
            "id": "giant_pit",
            "archetype": "boss",
            "encounter": Encounter(allies=("hero_fighter",), enemies=(GIANT, "bandit")),
        }
    )


# ---------------------------------------------------------------------------
# 範本與地圖的欄位
# ---------------------------------------------------------------------------


def test_footprint_defaults_to_one_and_is_not_written() -> None:
    plain = template("bandit")
    assert plain.footprint == 1 and "footprint" not in plain.model_dump()
    assert giant_template().model_dump()["footprint"] == 3


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"footprint": 2}, "只能是 1 或 3"),
        ({"footprint": 3, "tags": ()}, "boss"),
    ],
)
def test_footprint_rules(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        template("bandit", **overrides)


def test_giant_facing_is_optional_and_round_trips() -> None:
    m = make_map(FLAT, ally=[(4, 8)], enemy=[(4, 3)])
    assert "giant_facing" not in m.model_dump()
    faced = MapDef.model_validate({**m.model_dump(), "giant_facing": {GIANT: "south"}})
    assert faced.giant_facing == {GIANT: "south"}
    with pytest.raises(ValidationError):
        MapDef.model_validate({**m.model_dump(), "giant_facing": {GIANT: "up"}})


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


def test_current_content_has_no_giant_problems() -> None:
    lib = library()
    assert not any(u.footprint > 1 for u in lib.units.values())
    assert check(lib) == []


def test_a_clean_boss_map_lineup_passes() -> None:
    assert check(library(), maps={"giant_pit": boss_map()}) == []


def test_giants_only_on_boss_maps() -> None:
    lib = library()
    plain = boss_map().model_copy(update={"archetype": "open_plain"})
    problems = check(lib, maps={"giant_pit": plain})
    assert any("giant_pit 不是頭目地圖" in p and GIANT in p for p in problems)


@pytest.mark.parametrize(
    ("kw", "word"),
    [
        ({"surfaces": [(3, 3, "fire")]}, "有表面"),
        ({"objects": [(5, 4, "crate")]}, "有物件"),
        ({"terrain": "\n".join(["........"] * 4 + ["...~...."] + ["........"] * 4)}, "站不上去"),
    ],
)
def test_the_nine_tiles_must_be_clean(kw: dict[str, Any], word: str) -> None:
    problems = check(library(), maps={"giant_pit": boss_map(**kw)})
    assert any("giant_pit" in p and word in p for p in problems), problems


def test_heights_must_match() -> None:
    rows = ["00000000"] * 9
    rows[2] = "00001000"  # (4, 2) 在佔格內
    m = make_map("\n".join(rows), ally=[(4, 8)], enemy=[(4, 3), (1, 1)])
    m = boss_map().model_copy(update={"heights": m.heights})
    assert any("高度不一致" in p for p in check(library(), maps={"giant_pit": m}))


def test_random_encounters_and_companions_cannot_have_giants() -> None:
    lib = library()
    run = lib.roguelite
    steps = (EncounterStep(options=((GIANT,),)), *run.encounters[1:])
    problems = check(lib, roguelite=run.model_copy(update={"encounters": steps}))
    assert any("一般遭遇" in p and GIANT in p for p in problems)
    companions = run.model_copy(update={"companions": (GIANT,)})
    assert any("同伴" in p for p in check(lib, roguelite=companions))


def _with_group(lib: ContentLibrary, units: tuple[str, ...], location: str) -> dict[str, Any]:
    table = lib.world_encounters["ashen_waste"]
    groups = [
        g.model_copy(update={"units": units}) if g.id == "ashen_heart_court" else g
        for g in table.groups
    ]
    locations = []
    for loc in table.locations:
        names = [w.group for w in loc.groups]
        if loc.location != location and "ashen_heart_court" in names:
            continue  # 原本的頭目地點拿掉，只留指定的地點用這個陣容
        if loc.location == location and "ashen_heart_court" not in names:
            first = loc.groups[0].model_copy(update={"group": "ashen_heart_court"})
            locations.append(loc.model_copy(update={"groups": (*loc.groups, first)}))
        else:
            locations.append(loc)
    patched = table.model_copy(update={"groups": tuple(groups), "locations": tuple(locations)})
    return {**lib.world_encounters, "ashen_waste": patched}


def test_world_boss_locations_may_have_giants_and_others_may_not() -> None:
    lib = library()
    lineup = (GIANT, "heart_ember_lizard", "heart_ember_lizard")
    ok = _with_group(lib, lineup, "molten_heart_pit")
    assert check(lib, world_encounters=ok) == []
    bad = _with_group(lib, lineup, "scorched_outskirts")
    assert any("必須全是頭目地圖" in p for p in check(lib, world_encounters=bad))


def test_giant_facing_must_name_a_known_template() -> None:
    lib = library()
    m = lib.maps["open_plain"].model_copy(update={"giant_facing": {"nobody": "south"}})
    problems = giant_problems(
        lib.units,
        {"open_plain": m},
        terrain=lib.ruleset.terrain.by_id(),
        objects=lib.ruleset.objects.by_id(),
        roguelite=lib.roguelite,
        world_maps=lib.world_maps,
        world_encounters=lib.world_encounters,
    )
    assert problems == ["地圖 open_plain 的 giant_facing 寫了不存在的範本：nobody"]
