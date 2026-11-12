"""世界動作日誌的重播（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.4、6.6）。

「初始快照＋動作日誌」重播出逐字相同的快照（JSON）；同季種子＋同日誌永遠得到同樣結果。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.world.helpers import NOON, make_world, with_rules
from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathProposal, OathTable
from trpg.shared.types import Attribute
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import (
    AllocateAction,
    CampAction,
    DissolveAction,
    FightAction,
    FlashAction,
    FlashPickAction,
    LoadoutAction,
    ReleaseOathAction,
    RestAction,
    RetreatAction,
    SwearOathAction,
    TravelAction,
    WorldAction,
)
from trpg.world.battle import auto_steps
from trpg.world.errors import WorldActionError, WorldReplayError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, dumps_world, loads_log
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _play(
    library: ContentLibrary,
    world: WorldState,
    chars: dict[str, CharacterState],
    picks: list[tuple[int, int, int, bool]],
) -> tuple[list[WorldLogEntry], WorldState]:
    """依 ``picks``（角色、選項、時間增量、趕路）產生合法的日誌（不合法的動作跳過，同 API 層）；
    回傳日誌與最後的世界（5F-1 起每個動作都會記上線紀錄，世界會變）。"""
    entries: list[WorldLogEntry] = []
    now = NOON
    ids = sorted(chars)
    world_map = library.world_maps["cloud_ridge"]
    for who, option, dt, hasten in picks:
        char_id = ids[who % len(ids)]
        char = chars[char_id]
        options: list[WorldAction] = [CampAction()]
        options += [TravelAction(to=n, hasten=hasten) for n in world_map.neighbors(char.location)]
        action = options[option % len(options)]
        now += dt
        try:
            result = world_step(library, world, char, action, now)
        except WorldActionError:
            continue
        chars[char_id] = result.char
        world = result.world
        entries.append(
            WorldLogEntry(seq=len(entries) + 1, now=now, character_id=char_id, action=action)
        )
    return entries, world


def _snapshot(world: WorldState, chars: dict[str, CharacterState]) -> str:
    return dumps_world(world) + "".join(dumps_char(chars[k]) for k in sorted(chars))


def _initial(make_char: MakeChar) -> dict[str, CharacterState]:
    return {"alice": make_char("alice"), "bob": make_char("bob", wis=18)}


def test_replay_matches_live_play(calm: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    start = _initial(make_char)
    live = dict(start)
    picks = [(i % 2, (i * 7) % 5, 37 * (i % 3), i % 4 == 0) for i in range(60)]
    entries, final = _play(calm, world, live, picks)
    assert len(entries) > 20

    first = replay(calm, world, start, entries)
    second = replay(calm, world, start, entries)
    assert _snapshot(first.world, first.characters) == _snapshot(final, live)
    assert _snapshot(first.world, first.characters) == _snapshot(second.world, second.characters)
    assert first.events == second.events


def test_replay_from_serialized_log(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    start = _initial(make_char)
    picks = [(i % 2, i, 120, False) for i in range(30)]
    entries, _ = _play(library, world, dict(start), picks)
    text = dumps_log(entries)
    restored = loads_log(text)
    assert restored == tuple(entries)
    a = replay(library, world, start, entries)
    b = replay(library, world, start, restored)
    assert _snapshot(a.world, a.characters) == _snapshot(b.world, b.characters)


def test_seq_must_increase(calm: ContentLibrary, make_char: MakeChar) -> None:
    entries = [
        WorldLogEntry(seq=2, now=NOON, character_id="alice", action=TravelAction(to="hunter_hut")),
        WorldLogEntry(seq=2, now=NOON, character_id="alice", action=TravelAction(to="mist_ferry")),
    ]
    with pytest.raises(WorldReplayError, match="序號"):
        replay(calm, make_world(), _initial(make_char), entries)


def test_time_must_not_go_back(calm: ContentLibrary, make_char: MakeChar) -> None:
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id="alice", action=TravelAction(to="hunter_hut")),
        WorldLogEntry(
            seq=2, now=NOON - 1, character_id="alice", action=TravelAction(to="mist_ferry")
        ),
    ]
    with pytest.raises(WorldReplayError, match="倒退"):
        replay(calm, make_world(), _initial(make_char), entries)


def test_unknown_character(calm: ContentLibrary, make_char: MakeChar) -> None:
    entries = [WorldLogEntry(seq=1, now=NOON, character_id="carol", action=CampAction())]
    with pytest.raises(WorldReplayError, match="carol"):
        replay(calm, make_world(), _initial(make_char), entries)


def test_different_season_seed_diverges(library: ContentLibrary, make_char: MakeChar) -> None:
    start = _initial(make_char)
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id="alice", action=TravelAction(to="ferry_steps"))
    ]
    outcomes = {
        replay(library, make_world(season_seed=seed), start, entries)
        .characters["alice"]
        .model_dump_json()
        for seed in range(6)
    }
    assert len(outcomes) > 1


@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    picks=st.lists(
        st.tuples(
            st.integers(0, 1),
            st.integers(0, 6),
            st.integers(0, 2000),
            st.booleans(),
        ),
        max_size=40,
    ),
    seed=st.integers(0, 2**64 - 1),
)
def test_replay_is_deterministic(
    library: ContentLibrary,
    make_char: MakeChar,
    picks: list[tuple[int, int, int, bool]],
    seed: int,
) -> None:
    world = make_world(season_seed=seed)
    start = _initial(make_char)
    live = dict(start)
    entries, final = _play(library, world, live, picks)
    result = replay(library, world, start, entries)
    assert _snapshot(result.world, result.characters) == _snapshot(final, live)


def test_replay_with_battle_and_town(library: ContentLibrary, make_char: MakeChar) -> None:
    """5A-4：移動 → 遇敵 → 撤退 → 再遇敵 → 戰鬥（步驟在日誌裡）→ 回小鎮休息、換技能；
    重播逐字相同。"""
    ambush = with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})
    world = make_world()
    start = {"alice": make_char("alice")}
    chars = dict(start)
    entries: list[WorldLogEntry] = []
    now = NOON

    def act(action: WorldAction) -> None:
        nonlocal world, now
        now += 30
        result = world_step(ambush, world, chars["alice"], action, now)
        world = result.world
        chars["alice"] = result.char
        entries.append(
            WorldLogEntry(seq=len(entries) + 1, now=now, character_id="alice", action=action)
        )

    act(TravelAction(to="ferry_steps"))
    act(RetreatAction())
    act(TravelAction(to="ferry_steps"))
    act(FightAction(steps=auto_steps(ambush, chars["alice"])))
    if chars["alice"].location != "mist_ferry":
        act(TravelAction(to="mist_ferry"))
    act(RestAction())
    act(LoadoutAction(skills=chars["alice"].hero.skills[1:]))
    assert any(isinstance(e.action, FightAction) for e in entries)

    restored = loads_log(dumps_log(entries))
    assert restored == tuple(entries)
    first = replay(ambush, make_world(), start, entries)
    second = replay(ambush, make_world(), start, restored)
    assert _snapshot(first.world, first.characters) == _snapshot(world, chars)
    assert _snapshot(first.world, first.characters) == _snapshot(second.world, second.characters)
    assert first.events == second.events
    assert any(e.kind == "battle_ended" for _, e in first.events)


def test_replay_with_growth(library: ContentLibrary, make_char: MakeChar) -> None:
    """5A-6：配點 → 閃現 → 選 → 立誓 → 戰鬥（升級）→ 溶掉 → 解除誓約；重播逐字相同。"""
    lib = dataclasses.replace(
        with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000}),
        world_oaths=OathTable.model_validate(
            {"templates": [{"id": "no_items", "name_zh": "不使用道具", "difficulty": "easy"}]}
        ),
    )
    skill = "skill_frost_shackle"  # FL-1a：戰歌已沒有閃現選項
    base = make_char("alice")
    start = {
        "alice": base.model_copy(
            update={
                "xp": 90,
                "insight": 3,
                "attribute_points": 2,
                "flash": {skill: acquire(skill).model_copy(update={"used": True})},
            }
        )
    }
    world = make_world()
    chars = dict(start)
    entries: list[WorldLogEntry] = []
    now = NOON

    def act(action: WorldAction) -> None:
        nonlocal world, now
        now += 30
        result = world_step(lib, world, chars["alice"], action, now)
        world = result.world
        chars["alice"] = result.char
        entries.append(
            WorldLogEntry(seq=len(entries) + 1, now=now, character_id="alice", action=action)
        )

    act(AllocateAction(attributes={Attribute.CON: 2}))
    act(FlashAction(skill=skill))
    act(FlashPickAction(pick=0))
    act(SwearOathAction(proposal=OathProposal(template="no_items")))
    act(TravelAction(to="ferry_steps"))
    act(FightAction(steps=auto_steps(lib, chars["alice"])))
    if chars["alice"].location != "mist_ferry":
        act(TravelAction(to="mist_ferry"))
    flashed = next(s for s in chars["alice"].hero.skills if s.startswith(skill))
    act(DissolveAction(skill=flashed))
    act(ReleaseOathAction())

    restored = loads_log(dumps_log(entries))
    assert restored == tuple(entries)
    first = replay(lib, make_world(), start, entries)
    second = replay(lib, make_world(), start, restored)
    assert _snapshot(first.world, first.characters) == _snapshot(world, chars)
    assert _snapshot(first.world, first.characters) == _snapshot(second.world, second.characters)
    assert first.events == second.events
    kinds = {e.kind for _, e in first.events}
    assert {"flash_offered", "flash_picked", "oath_sworn", "skill_dissolved"} <= kinds
