"""隱藏地點的顯示規則（Phase 5C-3f）：顯示給還沒發現該地點的人看時一律用提示語；朋友戰報、朋友影子
存的地點套用，自己影子的存檔位置照常顯示。"""

from __future__ import annotations

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_party_view import my_shadow_view, report_line
from trpg.content.library import ContentLibrary
from trpg.world.narration import location_name_for
from trpg.world.shadows import shadow_snapshot
from trpg.world.state import CharacterState, LocationRef, ShadowRecord, ShadowReport
from trpg.world.step import new_character

REGION, HIDDEN = "cloud_ridge", "elixir_cave"
NAME, HINT = "丹爐洞", "谷底一處隱密的洞窟"


def _char(library: ContentLibrary, cid: str, *, found: bool = False) -> CharacterState:
    char = new_character(library, cid, hero(library), region=REGION)
    if found:
        char = char.model_copy(update={"revealed": (LocationRef(region=REGION, location=HIDDEN),)})
    return char


def test_location_name_for_viewer(library: ContentLibrary) -> None:
    assert location_name_for(library, _char(library, "alice"), REGION, HIDDEN) == HINT
    assert location_name_for(library, _char(library, "alice", found=True), REGION, HIDDEN) == NAME
    assert location_name_for(library, _char(library, "alice"), REGION, "mist_ferry") == "霧渡鎮"
    assert location_name_for(library, _char(library, "alice"), "gone", "somewhere") == "somewhere"


def _report() -> ShadowReport:
    return ShadowReport(
        day=0,
        at=NOON,
        borrower="bob",
        borrower_name="小美",
        region=REGION,
        location=HIDDEN,
        won=False,
    )


def test_friend_report_uses_hint_until_found(library: ContentLibrary) -> None:
    line = report_line(library, _report(), 0, _char(library, "alice"))
    assert HINT in line and NAME not in line
    assert NAME in report_line(library, _report(), 0, _char(library, "alice", found=True))


def test_own_shadow_save_location_shows_name(library: ContentLibrary) -> None:
    """自己的存檔位置照常顯示（就算是自己已不在、或資料裡沒標發現的地點）。"""
    alice = _char(library, "alice").model_copy(update={"location": HIDDEN})
    record = ShadowRecord(snapshot=shadow_snapshot(alice, NOON))
    world = make_world().model_copy(update={"shadows": (record,)})
    view = my_shadow_view(library, world, alice, in_battle=False)
    assert view.saved_zh is not None and view.saved_zh.startswith(NAME)
