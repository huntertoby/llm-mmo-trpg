"""看得見的敵人：規則收尾（Phase 6C-1b；21.10 第 8、9、11 條）。

- 進圖寬限：走出口或門抵達的那一格不檢查，從走的第一步才檢查。
- 每隊清空：共享的地點（營地、精英巢穴、遺跡、祭壇）打贏一隊只消失那一隊（世界狀態），全打完才寫
  「已清空」；重生時間每隊對齊地點的。
- ``personal``：只對自己消失（角色這一趟）、不算進共享清空、下一趟回來再出現。
- ``day_phase``：只在那個時段出現；沒寫全天。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_world, with_rules
from tests.world.test_field_enemies import (
    _char,
    _ended,
    _library,
    _of,
    _play,
    _steps_map,
    _visit,
    _walk,
)
from trpg.content.fields import FieldSpawn
from trpg.content.library import ContentLibrary
from trpg.world.actions import BattleEndedEvent, FightAction, LocationClearedEvent, WorldEvent
from trpg.world.battle import auto_steps
from trpg.world.clock import day_phase
from trpg.world.common import rules_of
from trpg.world.field_actions import WalkedEvent
from trpg.world.field_enemies import (
    after_fight,
    appears,
    field_enemies,
    shared_clear,
)
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, read_log
from trpg.world.state import CharacterState, FieldPos, WorldState
from trpg.world.step import new_character, world_step

type XY = tuple[int, int]

NIGHT = next(t for t in range(NOON, NOON + 3600, 60) if day_phase(t) == "night")
"""``NOON`` 之後第一個夜晚的時刻。"""


def _lib(base: ContentLibrary, spawns: list[dict[str, Any]], location: str = "ferry_steps") -> Any:
    """渡口石階的測試小地圖（13×13，西邊 (0, 6) 出口），可以換到別的地點（種類不同）。"""
    found = _steps_map(spawns)
    if location != "ferry_steps":
        found = found.model_copy(update={"id": location, "location": location, "exits": ()})
    return _library(base, found)


def _at(library: ContentLibrary, at: XY, location: str = "ferry_steps", **updates: Any) -> Any:
    visit = _visit(1).model_copy(update={"location": location})
    return _char(library, at, location=location, field_visit=visit, **updates)


def _touch(
    library: ContentLibrary, char: CharacterState, cell: XY, world: WorldState | None = None
) -> CharacterState:
    """走一格碰到敵人（相鄰一定碰到，跟朝向無關）。"""
    result = world_step(library, world or make_world(), char, _walk(cell), NOON)
    assert result.char.pending_encounter is not None
    return result.char


def _win(
    library: ContentLibrary, world: WorldState, touched: CharacterState, now: int = NOON
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """直接套用打贏（不跑戰鬥）：``after_fight`` 收到勝利的 ``BattleEndedEvent``。"""
    after = touched.model_copy(update={"pending_encounter": None})
    return after_fight(
        library,
        world,
        touched,
        after,
        action=FightAction(steps=()),
        events=(_ended(won=True),),
        now=now,
    )


def _shown(library: ContentLibrary, world: WorldState, char: CharacterState, now: int) -> list[int]:
    return [e.index for e in field_enemies(library, world, char, now)]


# ---------------------------------------------------------------------------
# 1. 進圖寬限（21.10 第 8 條）
# ---------------------------------------------------------------------------


def test_arrival_cell_is_not_checked(field_library: ContentLibrary) -> None:
    """抵達格 (1, 6) 和駐守 (2, 6) 相鄰：一到不開打；走開再走回來才開打。"""
    library = _lib(field_library, [{"at": [2, 6], "group": "bandit_raiders"}])
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    start = char.model_copy(update={"field": FieldPos(map="mist_ferry", x=22, y=8)})
    arrived = world_step(library, make_world(), start, _walk((23, 8)), NOON).char
    assert arrived.location == "ferry_steps"
    assert arrived.field is not None and (arrived.field.x, arrived.field.y) == (1, 6)
    assert arrived.pending_encounter is None
    assert len(field_enemies(library, make_world(), arrived, NOON)) == 1
    # 走開再走回來（(1, 7) 看朝向可能已經在視野裡；回到 (1, 6) 一定相鄰）
    moved = world_step(library, make_world(), arrived, _walk((1, 7), (1, 6)), NOON)
    assert moved.char.pending_encounter is not None
    assert _of(WalkedEvent, list(moved.events))[0].stopped == "enemy"


# ---------------------------------------------------------------------------
# 2. 每隊清空（21.10 第 9 條）
# ---------------------------------------------------------------------------

TWO: list[dict[str, Any]] = [
    {"at": [6, 6], "group": "bandit_raiders"},
    {"at": [10, 10], "group": "bandit_raiders"},
]


@pytest.mark.parametrize(
    ("location", "shared"),
    [
        ("ferry_steps", True),  # 營地
        ("north_slope", True),  # 精英巢穴
        ("herb_valley", True),  # 遺跡
        ("old_pine_altar", True),  # 祭壇
        ("hunter_hut", False),  # 村落：照 6C-1，只在這一趟消失
        ("elixir_cave", False),  # 秘境
        ("crystal_rift", False),  # 異象
    ],
)
def test_which_kinds_share_the_clear(
    field_library: ContentLibrary, location: str, shared: bool
) -> None:
    library = _lib(field_library, TWO, location)
    assert shared_clear(library, "cloud_ridge", location) is shared
    char = _touch(library, _at(library, (6, 4), location), (6, 5))
    world, won, events = _win(library, make_world(), char)
    assert events == ()  # 還有一隊：不寫已清空
    assert not world.is_cleared("cloud_ridge", location, NOON)
    assert won.field_visit is not None
    if shared:
        assert [s.key() for s in world.defeated_spawns] == [("cloud_ridge", location, 0)]
        assert won.field_visit.defeated == ()
    else:  # 6C-R2：世界只記重生世代（陣容換一批），不讓它對任何人消失
        assert [(s.key(), s.wins) for s in world.defeated_spawns] == [
            (("cloud_ridge", location, 0), 1)
        ]
        assert not world.spawn_defeated("cloud_ridge", location, 0, NOON)
        assert won.field_visit.defeated == (0,)
    assert _shown(library, world, won, NOON) == [1]  # 只消失打贏的那一隊


def test_shared_kinds_from_rules(field_library: ContentLibrary) -> None:
    """6C-2：共享清空的種類改讀規則檔的 ``battle.clear_kinds``（拿掉程式常數，行為不變）。"""
    kinds = rules_of(field_library).battle.clear_kinds
    assert sorted(kinds) == ["altar", "camp", "elite_lair", "ruin"]
    library = _lib(with_rules(field_library, battle={"clear_kinds": ["camp"]}), TWO, "herb_valley")
    assert not shared_clear(library, "cloud_ridge", "herb_valley")  # 規則拿掉遺跡就不共享


def test_all_groups_beaten_clears_location_and_aligns_respawn(
    field_library: ContentLibrary,
) -> None:
    library = _lib(field_library, TWO)
    respawn = rules_of(library).battle.respawn_seconds
    world = make_world()
    first = _touch(library, _at(library, (6, 4)), (6, 5), world)
    world, char, _ = _win(library, world, first, NOON)
    char = char.model_copy(update={"field": FieldPos(map="ferry_steps", x=10, y=8)})
    second = _touch(library, char, (10, 9), world)
    world, char, events = _win(library, world, second, NOON + 60)
    assert events == (LocationClearedEvent(location="ferry_steps", respawn_at=NOON + 60 + respawn),)
    assert world.is_cleared("cloud_ridge", "ferry_steps", NOON + 60)
    assert {s.respawn_at for s in world.defeated_spawns} == {NOON + 60 + respawn}  # 對齊地點
    # 所有人看得到：另一個角色進來也沒有敵人
    bob = _at(library, (1, 6)).model_copy(update={"character_id": "bob"})
    assert _shown(library, world, bob, NOON + 60) == []
    assert _shown(library, world, bob, NOON + 60 + respawn) == [0, 1]  # 一起重生


def test_beaten_group_respawns_for_everyone(field_library: ContentLibrary) -> None:
    library = _lib(field_library, TWO)
    respawn = rules_of(library).battle.respawn_seconds
    world, _, _ = _win(library, make_world(), _touch(library, _at(library, (6, 4)), (6, 5)))
    bob = _at(library, (1, 6)).model_copy(update={"character_id": "bob"})
    assert _shown(library, world, bob, NOON) == [1]
    assert _shown(library, world, bob, NOON + respawn) == [0, 1]


def test_lost_fight_changes_nothing(field_library: ContentLibrary) -> None:
    library = _lib(field_library, TWO)
    touched = _touch(library, _at(library, (6, 4)), (6, 5))
    world = make_world()
    after, char, events = after_fight(
        library,
        world,
        touched,
        touched,
        action=FightAction(steps=()),
        events=(_ended(won=False),),
        now=NOON,
    )
    assert (after, char, events) == (world, touched, ())


# ---------------------------------------------------------------------------
# 3. personal（21.10 第 9 條）
# ---------------------------------------------------------------------------

MIXED: list[dict[str, Any]] = [
    {"at": [6, 6], "group": "bandit_raiders", "personal": True},
    {"at": [10, 10], "group": "bandit_raiders"},
]


@pytest.mark.parametrize(
    ("spawns", "beat", "cleared", "world_rows", "visit_defeated", "shown"),
    [
        (MIXED, 0, False, 1, (0,), [1]),  # 打贏個人的：只記在自己（世界只記重生世代，6C-R2）
        (MIXED, 1, True, 1, (), [0]),  # 打贏唯一的共享隊伍：已清空，個人的照樣在
    ],
)
def test_personal_groups(
    field_library: ContentLibrary,
    *,
    spawns: list[dict[str, Any]],
    beat: int,
    cleared: bool,
    world_rows: int,
    visit_defeated: tuple[int, ...],
    shown: list[int],
) -> None:
    library = _lib(field_library, spawns)
    target = spawns[beat]["at"]
    char = _at(library, (target[0], target[1] - 2))
    touched = _touch(library, char, (target[0], target[1] - 1))
    world, won, _ = _win(library, make_world(), touched)
    assert world.is_cleared("cloud_ridge", "ferry_steps", NOON) is cleared
    assert len(world.defeated_spawns) == world_rows
    assert won.field_visit is not None and won.field_visit.defeated == visit_defeated
    assert _shown(library, world, won, NOON) == shown
    bob = _at(library, (1, 6)).model_copy(update={"character_id": "bob"})
    assert 0 in _shown(library, world, bob, NOON)  # 別人照樣看得到個人的駐守


def test_personal_group_returns_next_visit(field_library: ContentLibrary) -> None:
    """打贏個人的駐守，離開這張圖再進來（下一趟）又出現。"""
    library = _lib(field_library, MIXED)
    world, won, _ = _win(library, make_world(), _touch(library, _at(library, (6, 4)), (6, 5)))
    assert _shown(library, world, won, NOON) == [1]
    won = won.model_copy(update={"field": FieldPos(map="ferry_steps", x=1, y=6)})
    out = world_step(library, world, won, _walk((0, 6)), NOON)
    assert out.char.location == "mist_ferry" and out.char.field_visit is None
    assert out.char.field is not None
    cell = (out.char.field.x + 1, out.char.field.y)
    back = world_step(library, out.world, out.char, _walk(cell), NOON)
    assert back.char.location == "ferry_steps"
    assert back.char.field_visit is not None and back.char.field_visit.defeated == ()
    assert _shown(library, back.world, back.char, NOON) == [0, 1]


# ---------------------------------------------------------------------------
# 4. day_phase（21.10 第 11 條）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phase", "now", "seen"),
    [
        (None, NOON, True),
        (None, NIGHT, True),
        ("night", NOON, False),
        ("night", NIGHT, True),
        ("day", NOON, True),
        ("day", NIGHT, False),
    ],
)
def test_day_phase_spawns(
    field_library: ContentLibrary, phase: str | None, now: int, seen: bool
) -> None:
    spawn: dict[str, Any] = {"at": [6, 6], "group": "bandit_raiders"}
    if phase is not None:
        spawn["day_phase"] = phase
    assert appears(FieldSpawn.model_validate(spawn), now) is seen
    library = _lib(field_library, [spawn])
    assert (_shown(library, make_world(), _at(library, (1, 6)), now) == [0]) is seen


def test_day_clear_ignores_night_patrol(field_library: ContentLibrary) -> None:
    """白天打完白天在的隊伍就算清空（晚上才出現的那隊不算）；清空期間晚上也不出現。"""
    spawns = [
        {"at": [6, 6], "group": "bandit_raiders"},
        {"at": [10, 2], "group": "bandit_shield_line", "day_phase": "night"},
    ]
    library = _lib(field_library, spawns)
    world, _, events = _win(library, make_world(), _touch(library, _at(library, (6, 4)), (6, 5)))
    assert _of(LocationClearedEvent, list(events))
    assert _shown(library, world, _at(library, (1, 6)), NIGHT) == []


def test_day_phase_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="day_phase"):
        FieldSpawn.model_validate({"at": [1, 1], "group": "x", "day_phase": "dusk"})
    spawn = FieldSpawn.model_validate({"at": [1, 1], "group": "x"})
    assert (spawn.personal, spawn.day_phase) == (False, None)


# ---------------------------------------------------------------------------
# 重播：進圖寬限＋每隊清空
# ---------------------------------------------------------------------------


def test_replay_arrival_and_per_group_clear(field_library: ContentLibrary) -> None:
    library = _lib(field_library, [{"at": [6, 6], "group": "bandit_raiders"}, *TWO[1:]])
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    start = char.model_copy(
        # 6C-2 起就地切 12×12、貼著敵人開打：主角 3 級才穩定打贏（這裡測的是每隊清空與重播）
        update={"field": FieldPos(map="mist_ferry", x=22, y=8), "mercenaries": PARTY, "level": 3}
    )
    world, live, entries = _play(
        library, start, [_walk((23, 8)), _walk((2, 6), (3, 6), (4, 6), (5, 6))], make_world()
    )
    assert live.location == "ferry_steps"
    assert live.pending_encounter is not None  # 最晚在 (5, 6) 和 (6, 6) 相鄰
    fight = FightAction(steps=auto_steps(library, live))
    result = world_step(library, world, live, fight, NOON + 3)
    assert any(isinstance(e, BattleEndedEvent) and e.won for e in result.events)
    entries.append(WorldLogEntry(seq=3, now=NOON + 3, character_id="alice", action=fight))
    assert [s.spawn for s in result.world.defeated_spawns] == [0]
    assert not result.world.is_cleared("cloud_ridge", "ferry_steps", NOON + 3)
    log = read_log(dumps_log(entries))
    runs = [replay(library, make_world(), {"alice": start}, log.entries) for _ in range(2)]
    assert all(dumps_char(r.characters["alice"]) == dumps_char(result.char) for r in runs)
    assert all(r.world == result.world for r in runs)
