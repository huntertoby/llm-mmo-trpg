"""主城設施格上的人（Phase 6V-3；美術 PM 6V-1 檢查待決 4）：殿主、酒館老闆、鐵匠、附魔師、傭兵管事
在原本的設施格多一個 ``figure``（只畫，同 6V-1 情境物件的做法）：格子、設施種類、通行都不變，
也不是 npcs。
另有守印人頭像旁的一句話 ``figure.line_zh``（公告板上緣用）。"""

from __future__ import annotations

import pytest

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_presenter import world_view
from trpg.content.fields import FieldFigure
from trpg.content.library import ContentLibrary
from trpg.content.maps import passable_grid
from trpg.world.field_actions import UseTeleportStoneAction
from trpg.world.step import new_character, world_step

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
