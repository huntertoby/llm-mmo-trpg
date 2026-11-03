"""線頭的有效、到期、上限與存檔（Phase 5B-1；``docs/phases/Phase5計畫.md`` 8.6、8.7）。"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from tests.world.helpers import NOON, make_world
from trpg.world.save import dumps_char, dumps_world, loads_char, loads_world
from trpg.world.state import CharacterState, EventTrigger, ThreadState
from trpg.world.threads import active_threads, add_thread, expired_threads

MakeChar = Callable[..., CharacterState]
DAY3 = 3 * 24 * 3600


def _thread(thread: str, created: int, expires: int) -> ThreadState:
    return ThreadState(
        thread=thread,
        skeleton="wounded_peddler",
        region="cloud_ridge",
        created_at=created,
        expires_at=expires,
    )


def _add(
    threads: tuple[ThreadState, ...], thread: str, now: int, limit: int = 5
) -> tuple[tuple[ThreadState, ...], tuple[ThreadState, ...]]:
    return add_thread(
        threads, thread, "wounded_peddler", "cloud_ridge", now, limit=limit, expire_seconds=DAY3
    )


def test_active_and_expired() -> None:
    threads = (_thread("a", 0, 100), _thread("b", 1, 200))
    assert active_threads(threads, 99) == threads
    assert active_threads(threads, 100) == (threads[1],)
    assert expired_threads(threads, 100) == (threads[0],)
    assert expired_threads(threads, 50) == ()


def test_add_thread() -> None:
    threads, pushed = _add((), "peddler_owes_you", NOON)
    assert pushed == ()
    (thread,) = threads
    assert thread.thread == "peddler_owes_you"
    assert thread.created_at == NOON
    assert thread.expires_at == NOON + DAY3


def test_add_same_active_thread_is_noop() -> None:
    threads, _ = _add((), "a", NOON)
    again, pushed = _add(threads, "a", NOON + 10)
    assert again == threads
    assert pushed == ()


def test_expired_same_thread_replaced() -> None:
    old = (_thread("a", 0, NOON),)
    threads, pushed = _add(old, "a", NOON)
    assert pushed == ()
    assert len(threads) == 1
    assert threads[0].created_at == NOON


def test_limit_pushes_out_oldest() -> None:
    threads: tuple[ThreadState, ...] = ()
    for i, name in enumerate(["e", "d", "c", "b", "a"]):
        threads, pushed = _add(threads, name, NOON + i)
        assert pushed == ()
    threads, pushed = _add(threads, "f", NOON + 10)
    assert [t.thread for t in pushed] == ["e"]
    assert [t.thread for t in threads] == ["d", "c", "b", "a", "f"]


def test_limit_ties_broken_by_id() -> None:
    threads = (_thread("b", NOON, NOON + DAY3), _thread("c", NOON, NOON + DAY3))
    out, pushed = _add(threads, "a", NOON + 1, limit=2)
    assert [t.thread for t in pushed] == ["b"]
    assert [t.thread for t in out] == ["c", "a"]


def test_expired_threads_do_not_count() -> None:
    threads = (_thread("old", 0, NOON),)
    out, pushed = _add(threads, "new", NOON, limit=1)
    assert pushed == ()
    assert [t.thread for t in out] == ["old", "new"]


def test_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="上限"):
        _add((), "a", NOON, limit=0)


def test_threads_must_be_sorted_and_unique(make_char: MakeChar) -> None:
    a = _thread("a", 2, 10)
    b = _thread("b", 1, 10)
    with pytest.raises(ValidationError, match="threads"):
        CharacterState.model_validate(make_char().model_dump() | {"threads": (a, b)})
    with pytest.raises(ValidationError, match="threads"):
        make_world(threads=(a, _thread("a", 3, 10)))


def test_save_round_trip_with_threads(make_char: MakeChar) -> None:
    trigger = EventTrigger(
        region="cloud_ridge",
        location="ferry_steps",
        skeleton="wounded_peddler",
        candidates=("broken_ferry", "wounded_peddler"),
        follows_thread="peddler_owes_you",
        weather="rain",
        day_phase="day",
        at=NOON,
    )
    thread = _thread("peddler_owes_you", NOON, NOON + DAY3)
    char = CharacterState.model_validate(
        make_char().model_dump()
        | {"threads": (thread,), "pending_event": trigger, "event_steps": 2}
    )
    assert loads_char(dumps_char(char)) == char
    world = make_world(threads=(thread,))
    assert loads_world(dumps_world(world)) == world


def test_old_saves_without_new_fields(make_char: MakeChar) -> None:
    raw = json.loads(dumps_char(make_char()))
    for key in ("threads", "pending_event", "event_steps"):
        raw.pop(key)
    char = loads_char(json.dumps(raw))
    assert char.threads == ()
    assert char.pending_event is None
    assert char.event_steps == 0
    world_raw = json.loads(dumps_world(make_world()))
    world_raw.pop("threads")
    assert loads_world(json.dumps(world_raw)).threads == ()
