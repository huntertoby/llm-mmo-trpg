"""新手第一次閃現（Phase 6F-2，#132；18 18.7.1、18.7.5）。

- 導師任務鏈第 1 步「觀摩」多了狀態型條件 ``flashed``：閃現過就算，新手時（接任務以前）閃的也算。
- 閃現教學的畫面資料（:func:`trpg.api.world_newcomer_view.lesson_view`）：第 1 步完成、在城鎮、
  沒閃過、有靈感、有用過的招＝閃現引導；3 級＋閃過＝改教重閃。
- 重播一致。
"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, make_world
from trpg.api.world_newcomer_view import lesson_view
from trpg.content.library import ContentLibrary
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import AcceptQuestAction, FlashAction, FlashPickAction, WorldAction
from trpg.world.quests import has_flashed
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_log, read_log
from trpg.world.state import CharacterState, QuestState, WorldState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
SKILL = "skill_frost_shackle"  # FL-1a：戰歌只有「只多冷卻」的蓄力，改成沒有閃現選項
MENTOR = "mentor_qingya_trial"


def _used(char: CharacterState, *skills: str, insight: int = 1) -> CharacterState:
    flash = {s: acquire(s).model_copy(update={"used": True}) for s in skills}
    return char.model_copy(update={"flash": flash, "insight": insight})


def _step1_done(char: CharacterState) -> CharacterState:
    quest = QuestState(quest="starter_ferry", steps_done=1, started_at=NOON)
    return char.model_copy(update={"quests": (quest,)})


def _flash(library: ContentLibrary, char: CharacterState) -> CharacterState:
    char = world_step(library, make_world(), char, FlashAction(skill=SKILL), NOON).char
    return world_step(library, make_world(), char, FlashPickAction(pick=0), NOON).char


def _at_mentor(char: CharacterState) -> CharacterState:
    return char.model_copy(
        update={"location": "mist_temple_gate", "story_flags": ("mentor_qingya",)}
    )


def test_first_flash_counts_for_observe_step(library: ContentLibrary, make_char: MakeChar) -> None:
    flashed = _flash(library, _used(make_char(), SKILL))
    assert has_flashed(flashed)
    accepted = world_step(
        library, make_world(), _at_mentor(flashed), AcceptQuestAction(quest=MENTOR), NOON
    ).char
    state = accepted.quest_state(MENTOR)
    assert state is not None and state.steps_done == 1  # 新手的閃現也算「觀摩」


def test_observe_step_waits_without_flash(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _at_mentor(make_char())
    accepted = world_step(library, make_world(), char, AcceptQuestAction(quest=MENTOR), NOON).char
    state = accepted.quest_state(MENTOR)
    assert state is not None and state.steps_done == 0
    back = accepted.model_copy(update={"location": "mist_ferry"})
    done = _flash(library, _used(back, SKILL))
    state = done.quest_state(MENTOR)
    assert state is not None and state.steps_done == 1


def test_lesson_flash_then_reflash(library: ContentLibrary, make_char: MakeChar) -> None:
    fresh = make_char()
    assert lesson_view(library, fresh) is None  # 還沒完成第 1 步
    ready = _step1_done(_used(fresh, SKILL))
    lesson = lesson_view(library, ready)
    assert lesson is not None and lesson.kind == "flash"
    assert [line.text_zh for line in lesson.lines] == [
        "剛才那一招還在你手裡發燙。",
        "讓剛用過的招靈光一閃。",
    ]
    assert len(lesson.skills_zh) == 1
    assert lesson_view(library, ready.model_copy(update={"insight": 0})) is None  # 不另給點
    outside = ready.model_copy(update={"location": "ferry_steps"})
    assert lesson_view(library, outside) is None  # 只在城鎮
    flashed = _flash(library, ready)
    assert lesson_view(library, flashed) is None  # 1 級閃過：不再教
    at3 = flashed.model_copy(update={"level": 3})
    re = lesson_view(library, at3)
    assert re is not None and re.kind == "reflash"
    assert re.lines and re.lines[0].speaker_zh == "葛蘭"  # 6F-4：駐堂導師葛蘭兼任重閃（#133）


def _play(
    library: ContentLibrary, world: WorldState, char: CharacterState, actions: list[WorldAction]
) -> tuple[WorldState, CharacterState, list[WorldLogEntry]]:
    entries: list[WorldLogEntry] = []
    for seq, action in enumerate(actions, start=1):
        now = NOON + seq * 60
        result = world_step(library, world, char, action, now)
        world, char = result.world, result.char
        entries.append(WorldLogEntry(seq=seq, now=now, character_id="alice", action=action))
    return world, char, entries


def test_first_flash_and_observe_replay(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    start = _step1_done(_used(make_char(), SKILL))
    flash: list[WorldAction] = [FlashAction(skill=SKILL), FlashPickAction(pick=0)]
    mid_world, mid, entries = _play(library, world, start, flash)
    mentor_start = _at_mentor(mid)
    end_world, live, more = _play(
        library, mid_world, mentor_start, [AcceptQuestAction(quest=MENTOR)]
    )
    for first, chars, log in ((world, start, entries), (mid_world, mentor_start, more)):
        parsed = read_log(dumps_log(log))
        one = replay(library, first, {"alice": chars}, parsed.entries)
        two = replay(library, first, {"alice": chars}, parsed.entries)
        assert one.characters["alice"] == two.characters["alice"]
    final = replay(library, mid_world, {"alice": mentor_start}, read_log(dumps_log(more)).entries)
    assert final.characters["alice"] == live and final.world == end_world
    state = live.quest_state(MENTOR)
    assert state is not None and state.steps_done == 1
