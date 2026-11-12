"""主題合併（R2）。

原 ``test_capital_figures_6v1.py``：

主城功能型 NPC 的外觀（Phase 6V-1；``docs/archive/art/偷懶自查.md`` G7）：守印人、守池人、
工坊師傅、書記在原本的情境物件格子上多一個 ``figure``（紙娃娃與頭像），只畫：位置、面板、說明、
通行都不變，也不是 npcs。

原 ``test_capital_figures_6v3.py``：

主城設施格上的人（Phase 6V-3；美術 PM 6V-1 檢查待決 4）：殿主、酒館老闆、鐵匠、附魔師、傭兵管事
在原本的設施格多一個 ``figure``（只畫，同 6V-1 情境物件的做法）：格子、設施種類、通行都不變，
也不是 npcs。
另有守印人頭像旁的一句話 ``figure.line_zh``（公告板上緣用）。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_presenter import world_view
from trpg.content.fields import FieldFigure, FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.maps import passable_grid
from trpg.world.field_actions import UseTeleportStoneAction
from trpg.world.step import new_character, world_step

# --- 原 test_capital_figures_6v1.py ---

FIGURES: dict[str, tuple[str, tuple[int, int], str | None]] = {
    # 物件 ID → (地圖, 格子, panel)；格子與 panel 是 6D-4／6D-R2 原本的值（守印人的格子 RT-5b 改）
    "seal_keeper": ("capital", (14, 12), "board"),  # RT-5b：移到中央廣場傳送石旁（玩法 PM）
    "pool_keeper": ("capital", (6, 4), None),
    "workshop_master": ("capital", (24, 18), "workshop"),  # PR-2a：點了開工坊師傅選單
    "scribe": ("capital_mentor_hall", (2, 2), "skills"),
}


def _spot(library: ContentLibrary, map_id: str, spot_id: str) -> Any:
    return next(s for s in library.field_maps[map_id].situation_objects if s.id == spot_id)


@pytest.mark.parametrize("spot_id", sorted(FIGURES))
def test_four_keepers_have_figure_at_original_cell(
    field_library: ContentLibrary, spot_id: str
) -> None:
    map_id, at, panel = FIGURES[spot_id]
    spot = _spot(field_library, map_id, spot_id)
    assert spot.at == at and spot.panel == panel and spot.use == "note"
    fig = spot.figure
    assert fig is not None
    assert fig.portrait.look is not None and fig.portrait.gear.get("body") is not None


def test_only_the_four_keepers_have_figures(field_library: ContentLibrary) -> None:
    with_figure = {
        (m.id, s.id)
        for m in field_library.field_maps.values()
        for s in m.situation_objects
        if s.figure is not None
    }
    assert with_figure == {(m, i) for i, (m, _, _) in FIGURES.items()}


def test_keepers_stay_non_npc_and_walkable(field_library: ContentLibrary) -> None:
    terrain = field_library.ruleset.terrain.by_id()
    objects = field_library.ruleset.objects.by_id()
    for spot_id, (map_id, at, _) in FIGURES.items():
        field = field_library.field_maps[map_id]
        assert not field.npcs
        assert spot_id not in {f.id for f in field.facilities}
        assert passable_grid(field, terrain, objects)[at[1]][at[0]], spot_id  # 只畫，不擋路


def test_workshop_master_hammers_and_keeper_holds_staff(field_library: ContentLibrary) -> None:
    master = _spot(field_library, "capital", "workshop_master").figure
    assert master.work == "smith" and master.held.kind == "hammer"
    keeper = _spot(field_library, "capital", "seal_keeper").figure
    assert keeper.held.kind == "staff" and keeper.portrait.gear["head"].kind == "hood"


def test_figure_only_on_situation_objects(field_library: ContentLibrary) -> None:
    lake = field_library.field_maps["winter_lake"]
    raw = lake.model_dump(mode="json")
    fig = FieldFigure.model_validate({"portrait": {"look": {"skin": "#f1c9a5"}}})
    raw["campfires"][0]["figure"] = fig.model_dump(mode="json")
    with pytest.raises(ValidationError, match="不可填 figure"):
        FieldMapDef.model_validate(raw)
    with pytest.raises(ValidationError):
        FieldFigure.model_validate({"portrait": {}, "work": "dance"})


def test_world_view_carries_figures(field_library: ContentLibrary) -> None:
    char = new_character(field_library, "alice", hero(field_library), region="cloud_ridge")
    moved = world_step(
        field_library, make_world(), char, UseTeleportStoneAction(to="stone_capital"), NOON
    ).char
    view = world_view(field_library, make_world(), moved, NOON)
    assert view.field is not None
    by = {o.id: o for o in view.field.situation_objects}
    for spot_id, (map_id, at, panel) in FIGURES.items():
        if map_id != "capital":
            continue
        o = by[spot_id]
        assert (o.x, o.y) == at and o.panel == panel
        assert o.figure == _spot(field_library, "capital", spot_id).figure
    assert by["wishing_pool"].figure is None and by["seal_altar"].figure is None


# --- 原 test_capital_figures_6v3.py ---

FACILITY_FIGURES: dict[tuple[str, str], tuple[int, int]] = {
    # (地圖, 設施) → 原本的站位
    ("capital_mentor_hall", "mentor"): (6, 2),
    ("capital_tavern", "tavern"): (6, 1),
    ("capital_smithy", "smithy"): (4, 2),
    ("capital_smithy", "enchanter"): (7, 3),
    ("capital", "hire"): (14, 18),
}


def _facility_figure(library: ContentLibrary, map_id: str, kind: str) -> FieldFigure:
    f = next(f for f in library.field_maps[map_id].facilities if f.id == kind)
    assert f.figure is not None, (map_id, kind)
    return f.figure


@pytest.mark.parametrize("key", sorted(FACILITY_FIGURES))
def test_five_facility_keepers_have_figure(
    field_library: ContentLibrary, key: tuple[str, str]
) -> None:
    map_id, kind = key
    field = field_library.field_maps[map_id]
    f = next(f for f in field.facilities if f.id == kind)
    assert f.at == FACILITY_FIGURES[key]
    assert f.figure is not None
    assert f.figure.portrait.look is not None and f.figure.portrait.gear.get("body") is not None


def test_only_these_facilities_have_figures(field_library: ContentLibrary) -> None:
    with_figure = {
        (m.id, f.id)
        for m in field_library.field_maps.values()
        for f in m.facilities
        if f.figure is not None
    }
    assert with_figure == set(FACILITY_FIGURES)


def test_identity_gear_uses_existing_parts(field_library: ContentLibrary) -> None:
    mentor = _facility_figure(field_library, "capital_mentor_hall", "mentor")
    assert (
        mentor.portrait.gear["head"].kind == "crown" and mentor.portrait.gear["body"].kind == "robe"
    )
    assert (
        mentor.held is not None
        and mentor.held.kind == "staff"
        and mentor.held.material == "crystal"
    )
    smith = _facility_figure(field_library, "capital_smithy", "smithy")
    assert smith.held is not None and smith.held.kind == "hammer" and smith.work == "smith"
    assert smith.portrait.gear["body"].kind == "leather"
    assert (
        _facility_figure(field_library, "capital_smithy", "enchanter").portrait.gear["body"].kind
        == "robe"
    )
    assert _facility_figure(field_library, "capital", "hire").portrait.gear["body"].kind == "mail"
    tavern = _facility_figure(field_library, "capital_tavern", "tavern")
    assert tavern.work == "keeper" and tavern.held is None


def test_facility_cells_unchanged_and_not_npcs(field_library: ContentLibrary) -> None:
    terrain = field_library.ruleset.terrain.by_id()
    objects = field_library.ruleset.objects.by_id()
    for (map_id, _kind), at in FACILITY_FIGURES.items():
        field = field_library.field_maps[map_id]
        assert not field.npcs
        # 通行和加欄位之前一樣（只畫）：拿掉 figure 的地圖算出的通行表相同
        bare = field.model_copy(
            update={
                "facilities": tuple(f.model_copy(update={"figure": None}) for f in field.facilities)
            }
        )
        assert passable_grid(field, terrain, objects) == passable_grid(bare, terrain, objects)
        assert at in {f.at for f in field.facilities}


def test_seal_keeper_has_board_line(field_library: ContentLibrary) -> None:
    keeper = next(
        s for s in field_library.field_maps["capital"].situation_objects if s.id == "seal_keeper"
    )
    assert keeper.figure is not None and keeper.figure.line_zh != ""
    assert keeper.note_zh == ""  # 一句話放在 figure（只畫），規則內容不變


def test_world_view_carries_facility_figure(field_library: ContentLibrary) -> None:
    char = new_character(field_library, "alice", hero(field_library), region="cloud_ridge")
    moved = world_step(
        field_library, make_world(), char, UseTeleportStoneAction(to="stone_capital"), NOON
    ).char
    view = world_view(field_library, make_world(), moved, NOON)
    assert view.field is not None
    by = {f.kind: f for f in view.field.facilities}
    assert by["hire"].figure == _facility_figure(field_library, "capital", "hire")
    assert by["notice_board"].figure is None
    keeper = next(o for o in view.field.situation_objects if o.id == "seal_keeper")
    assert keeper.figure is not None and keeper.figure.line_zh != ""
