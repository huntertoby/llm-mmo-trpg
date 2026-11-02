"""好感度的新取得方式與信賴後的祕密事件（Phase 5B-4b；Phase5計畫 19.2、19.3）。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_quests import _with_quest, _won
from tests.world.test_situations import act, at_event, sure
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.world.actions import (
    AffinityChangedEvent,
    EventResolvedEvent,
    EventTriggeredEvent,
    SkeletonUnlockedEvent,
    TalkAction,
    TalkedEvent,
    ThreadAddedEvent,
)
from trpg.world.clock import next_refresh_at, refresh_day
from trpg.world.events import event_candidates, mark_finished
from trpg.world.quests import advance_quests
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

DAY = 86_400


def _changes(events: Sequence[object]) -> list[AffinityChangedEvent]:
    return [e for e in events if isinstance(e, AffinityChangedEvent)]


# ---------------------------------------------------------------------------
# 任務步驟 +10（5B-4c 從 +15 下修）
# ---------------------------------------------------------------------------


def test_quest_step_gives_related_npcs_10(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_quest(make_char(location="ferry_steps"), "starter_ferry")
    char, events = advance_quests(library, make_world(), char, _won("ferry_steps"), NOON)
    changes = _changes(events)
    assert [(e.npc, e.delta, e.source) for e in changes] == [
        ("granny_du", 10, "quest:starter_ferry")
    ]
    assert char.affinity["granny_du"] == 10


def test_quest_step_with_two_npcs(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_quest(make_char(), "main_mist_rift", steps_done=2)
    char = char.model_copy(update={"location": "mist_temple_gate"})
    events = _won("mist_temple_gate")
    traitor = events[0].model_copy(
        update={"lineup": events[0].lineup.model_copy(update={"group": "temple_traitor"})}  # type: ignore[union-attr]
    )
    char, out = advance_quests(library, make_world(), char, (traitor, events[1]), NOON)
    assert sorted((e.npc, e.delta) for e in _changes(out)) == [
        ("acolyte_xiaolian", 10),
        ("daoist_qingya", 10),
    ]


# ---------------------------------------------------------------------------
# 每天第一次聊天 +3
# ---------------------------------------------------------------------------


def test_daily_first_talk_gives_3(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char()  # 霧渡鎮
    first = world_step(library, world, char, TalkAction(npc="granny_du"), NOON)
    assert [(e.delta, e.source) for e in _changes(first.events)] == [(3, "talk:daily")]
    assert first.char.affinity["granny_du"] == 3
    again = world_step(library, world, first.char, TalkAction(npc="granny_du"), NOON + 600)
    assert _changes(again.events) == []
    assert again.char.affinity["granny_du"] == 3
    tomorrow = world_step(library, world, again.char, TalkAction(npc="granny_du"), NOON + DAY)
    assert tomorrow.char.affinity["granny_du"] == 6
    other = world_step(library, world, tomorrow.char, TalkAction(npc="shopkeeper_liu"), NOON + DAY)
    assert other.char.affinity["shopkeeper_liu"] == 3  # 每位 NPC 各算


def test_talk_reaching_trusted_tells_secret_now(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = make_char(affinity={"granny_du": 58})
    result = world_step(library, make_world(), char, TalkAction(npc="granny_du"), NOON)
    talked = next(e for e in result.events if isinstance(e, TalkedEvent))
    assert talked.rank == "trusted"
    assert "granny_du_secret" in talked.entries


# ---------------------------------------------------------------------------
# 信賴的祕密解鎖骨架 22
# ---------------------------------------------------------------------------


def test_secret_unlocks_and_triggers_granny_past(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = make_char(affinity={"granny_du": 70})
    result = world_step(library, make_world(), char, TalkAction(npc="granny_du"), NOON)
    kinds = [type(e).__name__ for e in result.events]
    assert kinds.index("TalkedEvent") < kinds.index("SkeletonUnlockedEvent")
    unlocked = next(e for e in result.events if isinstance(e, SkeletonUnlockedEvent))
    assert (unlocked.skeleton, unlocked.npc) == ("granny_past", "granny_du")
    triggered = next(e for e in result.events if isinstance(e, EventTriggeredEvent))
    assert triggered.trigger.candidates == ("granny_past",)
    assert result.char.unlocked_skeletons == ("granny_past",)
    assert result.char.pending_event is not None
    assert result.char.pending_event.skeleton == "granny_past"
    assert not any(isinstance(e, ThreadAddedEvent) for e in result.events)  # 祕密不給線頭
    again = world_step(library, make_world(), result.char, TalkAction(npc="granny_du"), NOON + 60)
    assert not any(isinstance(e, SkeletonUnlockedEvent) for e in again.events)


def test_secret_with_pending_event_only_unlocks(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = at_event(make_char(affinity={"granny_du": 70}), "tavern_storyteller", "mist_ferry")
    result = world_step(library, make_world(), char, TalkAction(npc="granny_du"), NOON)
    assert result.char.unlocked_skeletons == ("granny_past",)
    assert result.char.pending_event is not None
    assert result.char.pending_event.skeleton == "tavern_storyteller"
    assert not any(isinstance(e, EventTriggeredEvent) for e in result.events)


def test_locked_skeleton_is_not_a_candidate(library: ContentLibrary) -> None:
    world = make_world()
    locked = event_candidates(library, world, "cloud_ridge", "mist_ferry", NOON)
    assert [s.id for s in locked] == ["tavern_storyteller"]
    opened = event_candidates(
        library, world, "cloud_ridge", "mist_ferry", NOON, unlocked=("granny_past",)
    )
    assert [s.id for s in opened] == ["granny_past", "tavern_storyteller"]


def test_granny_past_success_gives_secret_door(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    lib = sure(library, "granny_parley", "success")
    char = at_event(make_char(), "granny_past", "mist_ferry", strong=True)
    action = act("granny_parley", attribute=Attribute.WIL, method="parley")
    result = world_step(lib, make_world(), char, action, NOON)
    added = [e.thread for e in result.events if isinstance(e, ThreadAddedEvent)]
    assert added == ["gang_fort_secret_door"]
    partial = world_step(
        sure(library, "granny_notice", "partial"),
        make_world(),
        char,
        act("granny_notice", attribute=Attribute.WIS, method="notice"),
        NOON,
    )
    assert not any(isinstance(e, ThreadAddedEvent) for e in partial.events)


# ---------------------------------------------------------------------------
# 骨架 22 每個角色只出現到解決為止（Phase 5B-4c；Phase5計畫 21.6）
# ---------------------------------------------------------------------------


def _mist_ferry(library: ContentLibrary, char: CharacterState, now: int) -> list[str]:
    candidates = event_candidates(
        library,
        make_world(),
        "cloud_ridge",
        "mist_ferry",
        now,
        unlocked=char.unlocked_skeletons,
        finished=char.finished_skeletons,
        failed=char.failed_skeletons,
    )
    return [s.id for s in candidates]


def _granny_result(library: ContentLibrary, make_char: MakeChar, outcome: str) -> CharacterState:
    lib = sure(library, "granny_parley", outcome)
    char = at_event(make_char(unlocked_skeletons=("granny_past",)), "granny_past", "mist_ferry")
    char = at_event(char, "granny_past", "mist_ferry", strong=True)
    action = act("granny_parley", attribute=Attribute.WIL, method="parley")
    return world_step(lib, make_world(), char, action, NOON).char


@pytest.mark.parametrize("outcome", ["success", "partial"])
def test_granny_past_once_resolved(
    library: ContentLibrary, make_char: MakeChar, outcome: str
) -> None:
    """成功、部分成功才算解決（5B-4d，18.7.6；取代 5B4c-9）。"""
    char = _granny_result(library, make_char, outcome)
    assert char.finished_skeletons == ("granny_past",)
    assert char.failed_skeletons == {}
    assert _mist_ferry(library, char, NOON + DAY) == ["tavern_storyteller"]  # 不再出現
    # 聊天也不再解鎖或觸發
    talked = char.model_copy(update={"affinity": {"granny_du": 70}})
    again = world_step(library, make_world(), talked, TalkAction(npc="granny_du"), NOON + DAY)
    assert not any(isinstance(e, SkeletonUnlockedEvent | EventTriggeredEvent) for e in again.events)


def test_granny_past_failure_retries_next_day(library: ContentLibrary, make_char: MakeChar) -> None:
    """判定失敗不算解決：當天不再出現，隔天（6 點刷新後）回到候選（5B-4d，代決 5B4d-2）。"""
    char = _granny_result(library, make_char, "failure")
    assert char.finished_skeletons == ()
    assert char.failed_skeletons == {"granny_past": refresh_day(NOON)}
    assert _mist_ferry(library, char, NOON) == ["tavern_storyteller"]
    refresh = next_refresh_at(NOON)
    assert _mist_ferry(library, char, refresh - 1) == ["tavern_storyteller"]
    assert _mist_ferry(library, char, refresh) == ["granny_past", "tavern_storyteller"]
    # 隔天再試成功 → 解決、清掉失敗紀錄
    retry = at_event(char, "granny_past", "mist_ferry", strong=True)
    lib = sure(library, "granny_parley", "success")
    action = act("granny_parley", attribute=Attribute.WIL, method="parley")
    done = world_step(lib, make_world(), retry, action, refresh + 600).char
    assert done.finished_skeletons == ("granny_past",)
    assert done.failed_skeletons == {}


def test_abandoning_is_not_resolving(library: ContentLibrary, make_char: MakeChar) -> None:
    """放棄不算解決（代決 5B4c-9）：之後照一般擲骰還會出現；失敗只記失敗那天（5B-4d）。"""
    char = make_char(unlocked_skeletons=("granny_past",))
    abandoned = EventResolvedEvent(
        skeleton="granny_past", location="mist_ferry", solution=0, outcome="abandoned"
    )
    assert mark_finished(library, char, (abandoned,), now=NOON) is char
    failed = abandoned.model_copy(update={"outcome": "failure"})
    marked = mark_finished(library, char, (failed,), now=NOON)
    assert marked.finished_skeletons == ()
    assert marked.failed_skeletons == {"granny_past": refresh_day(NOON)}
    partial = abandoned.model_copy(update={"outcome": "partial"})
    assert mark_finished(library, char, (partial,), now=NOON).finished_skeletons == ("granny_past",)
    other = failed.model_copy(update={"skeleton": "tavern_storyteller"})
    assert mark_finished(library, char, (other,), now=NOON) is char  # 不是 once 的骨架不記


def test_other_skeletons_are_not_once(library: ContentLibrary) -> None:
    table = library.world_event_content.events["cloud_ridge"]
    assert [s.id for s in table.skeletons if s.once] == ["granny_past"]
