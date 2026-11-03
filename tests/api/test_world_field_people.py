"""實地地圖上的人（6B-4）：NPC 的好感表情與「！」、站在城裡的朋友（影子）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_field_people import FRIENDS_MAX, friend_cells, npc_marks
from trpg.api.world_field_view import field_view
from trpg.content.library import ContentLibrary
from trpg.world.calendar import day_of
from trpg.world.field import field_grid
from trpg.world.shadows import shadow_snapshot
from trpg.world.state import CharacterState, FieldPos, QuestState, ShadowRecord, WorldState
from trpg.world.step import new_character

ALL_QUESTS = ("starter_ferry", "main_mist_rift", "hidden_elixir_cave")


def _char(library: ContentLibrary, cid: str = "alice", **updates: Any) -> CharacterState:
    char = new_character(library, cid, hero(library), region="cloud_ridge")
    return char.model_copy(update=updates)


def _started(*quests: str) -> tuple[QuestState, ...]:
    return tuple(QuestState(quest=q, started_at=NOON) for q in quests)


type Case = tuple[str, int, bool, tuple[str, ...], str, str | None]
"""（NPC、好感度、今天聊過、已接的任務、預期級別、預期「！」）。"""


@pytest.mark.parametrize(
    "case",
    [
        # 新角色：渡婆給新手任務（還沒接）→ 任務的「！」
        ("granny_du", 0, False, (), "neutral", "quest"),
        # 任務都接了、今天還沒聊：中立聊得出傳聞 → 傳聞的「！」
        ("granny_du", 0, False, ALL_QUESTS, "neutral", "rumor"),
        # 今天聊過了、任務都接了：沒有「！」
        ("granny_du", 0, True, ALL_QUESTS, "neutral", None),
        # 敵視：不給任務、也聊不出傳聞
        ("granny_du", -100, False, (), "hostile", None),
        ("granny_du", -30, False, ALL_QUESTS, "cold", None),
        # 柳掌櫃：中立只有傳聞；友善聊得出隱藏任務的入口
        ("shopkeeper_liu", 0, False, (), "neutral", "rumor"),
        ("shopkeeper_liu", 0, True, (), "neutral", None),
        ("shopkeeper_liu", 20, True, (), "friendly", "quest"),
        ("shopkeeper_liu", 20, True, ("hidden_elixir_cave",), "friendly", None),
        ("shopkeeper_liu", 60, False, ("hidden_elixir_cave",), "trusted", "rumor"),
    ],
)
def test_npc_marks_table(field_library: ContentLibrary, case: Case) -> None:
    npc, affinity, talked, quests, rank, alert = case
    today = day_of(field_library, NOON)
    char = _char(
        field_library,
        affinity={npc: affinity},
        talk_days={npc: today} if talked else {},
        quests=_started(*quests),
    )
    mark = npc_marks(field_library, make_world(), char, [npc], NOON)[npc]
    assert (mark.rank, mark.alert) == (rank, alert)
    assert mark.rank_zh != ""


def test_field_npcs_carry_marks_without_look(field_library: ContentLibrary) -> None:
    """畫面的 NPC 帶好感級別與「！」；人設卡沒有外觀，``look`` 為空（前端用預設、不畫血條）。"""
    view = field_view(field_library, _char(field_library), world=make_world(), now=NOON)
    assert view is not None
    npcs = {n.id: n for n in view.npcs}
    assert npcs["granny_du"].alert == "quest"
    assert npcs["granny_du"].alert_zh == "有任務可以接"
    assert npcs["shopkeeper_liu"].alert == "rumor"
    assert all(
        n.look is None and n.rank == "neutral" and n.rank_zh == "中立" for n in npcs.values()
    )


# ---------------------------------------------------------------------------
# 朋友
# ---------------------------------------------------------------------------


def _world_with(library: ContentLibrary, owners: list[str], **pos: Any) -> WorldState:
    records = []
    for owner in sorted(owners):
        char = _char(library, owner, **pos)
        records.append(ShadowRecord(snapshot=shadow_snapshot(char, NOON)))
    return make_world(shadows=tuple(records))


def test_friend_cells_deterministic(field_library: ContentLibrary) -> None:
    found = field_library.field_maps["mist_ferry"]
    grid = field_grid(field_library, _char(field_library), found)
    owners = [f"friend{i}" for i in range(6)]
    first = friend_cells(found, grid, owners, 1)
    shuffled = [*owners[3:], *reversed(owners[:3])]
    assert friend_cells(found, grid, shuffled, 1) == first  # 和名單順序無關
    assert friend_cells(found, grid, owners, 1) == first  # 同樣的輸入同樣的結果
    assert len(set(first.values())) == len(owners)  # 不重疊
    reserved = {found.entry, *(d.at for d in found.doors), *(f.at for f in found.facilities)}
    reserved |= {c for e in found.exits for c in e.at}
    reserved |= {s.at for s in found.teleport_stones}
    for cell in first.values():
        assert grid.standable(cell)
        assert cell not in reserved
    # 單一朋友的位置只看自己的 ID（沒有撞到別人時）
    alone = friend_cells(found, grid, ["friend0"], 1)
    assert alone["friend0"] == first["friend0"]


def test_friends_in_town_only(field_library: ContentLibrary) -> None:
    owners = ["bob", "carol", "alice"]
    world = _world_with(field_library, owners)
    me = _char(field_library)
    view = field_view(field_library, me, world=world, now=NOON)
    assert view is not None and view.map_id == "mist_ferry"
    assert [f.owner for f in view.friends] == ["bob", "carol"]  # 不含自己、依 ID
    assert all(f.look.template_id for f in view.friends)
    again = field_view(field_library, me, world=world, now=NOON + 3600)
    assert again is not None
    assert [(f.x, f.y) for f in again.friends] == [(f.x, f.y) for f in view.friends]
    # 室內不放朋友
    inside = me.model_copy(update={"field": FieldPos(map="mist_ferry_tavern", x=4, y=6)})
    view_in = field_view(field_library, inside, world=world, now=NOON)
    assert view_in is not None and view_in.interior and view_in.friends == ()
    # 沒有世界狀態（舊呼叫）不放
    plain = field_view(field_library, me)
    assert plain is not None and plain.friends == ()


def test_friends_capped(field_library: ContentLibrary) -> None:
    owners = [f"f{i:02d}" for i in range(FRIENDS_MAX + 3)]
    world = _world_with(field_library, owners)
    view = field_view(field_library, _char(field_library), world=world, now=NOON)
    assert view is not None
    assert [f.owner for f in view.friends] == sorted(owners)[:FRIENDS_MAX]


def test_field_npcs_carry_portrait(field_library: ContentLibrary) -> None:
    """6C-7：人設卡的 ``portrait`` 原樣給前端（地圖紙娃娃與頭像同一份）；``look`` 仍為空。"""
    view = field_view(field_library, _char(field_library), world=make_world(), now=NOON)
    assert view is not None
    npcs = {n.id: n for n in view.npcs}
    granny = npcs["granny_du"].portrait
    assert granny is not None and granny.look is not None
    assert granny.look.hair == "bun" and granny.look.bun_band == "#b8432f"
    assert granny.gear["body"].kind == "robe"
    assert granny.extras == ("wrinkles",)


def test_all_cards_have_portraits(field_library: ContentLibrary) -> None:
    """兩區 15 張人設卡都有頭像；霜音是白狐（``fox``，沒有紙娃娃外觀）。"""
    tables = field_library.world_event_content.npcs
    cards = {c.id: c for t in tables.values() for c in t.npcs}
    assert all(c.portrait is not None for c in cards.values())
    fox = cards["frost_chime"].portrait
    assert fox is not None and fox.extras == ("fox",) and fox.look is None
