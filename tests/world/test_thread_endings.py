"""線頭到期的結局與導師任務鏈（Phase 5B-4b；``docs/phases/Phase5計畫.md`` 19.7、19.8）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from tests.world.test_quests import _with_quest, _won
from tests.world.test_situations import thread
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    AcceptQuestAction,
    AffinityChangedEvent,
    FightAction,
    FlashPickedEvent,
    QuestStepDoneEvent,
    SkillDissolvedEvent,
    StoryFlagClearedEvent,
    TavernAction,
    ThreadExpiredEvent,
    WorldEvent,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.encounters import roll_lineup
from trpg.world.errors import WorldActionError
from trpg.world.quests import advance_quests
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

OLD = NOON - 400_000  # 已經過了 3 天到期


# ---------------------------------------------------------------------------
# 到期結局
# ---------------------------------------------------------------------------


def test_expired_thread_with_ending_gives_flag(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    threads = (thread("peddler_owes_you", at=OLD), thread("scarface_grudge", "gang_toll", OLD))
    char = make_char(threads=threads)
    result = world_step(library, make_world(), char, TavernAction(), NOON)
    expired = [e for e in result.events if isinstance(e, ThreadExpiredEvent)]
    assert [(e.thread, e.scope, e.flag) for e in expired] == [
        ("scarface_grudge", "personal", "scarface_rises")
    ]
    assert result.events[0] == expired[0]  # 動作之前結算
    assert result.char.story_flags == ("scarface_rises",)
    assert [t.thread for t in result.char.threads] == ["peddler_owes_you"]  # 沒結局的照舊


def test_live_thread_does_not_end(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(threads=(thread("temple_traitor", "monks_dispute"),))
    result = world_step(library, make_world(), char, TavernAction(), NOON)
    assert not any(isinstance(e, ThreadExpiredEvent) for e in result.events)
    assert result.char.story_flags == ()


def test_variant_lineups(library: ContentLibrary) -> None:
    fort = make_encounter("cliff_gang_fort", seed=3)
    normal = roll_lineup(library, fort)
    assert normal.variant is None
    risen = roll_lineup(library, fort, ("scarface_rises",))
    assert (risen.group, risen.variant) == ("scarface_risen", "scarface_rises")
    assert risen.members[0].unit == "bandit_captain"
    gate = make_encounter("mist_temple_gate", seed=3)
    traitor = roll_lineup(library, gate, ("temple_traitor_strikes",))
    assert traitor.group == "temple_traitor"
    assert roll_lineup(library, gate, ("scarface_rises",)).variant is None  # 別的地點不受影響


def test_prepare_battle_uses_story_flags(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(
        location="mist_temple_gate",
        pending_encounter=make_encounter("mist_temple_gate", seed=5, level=3),
        story_flags=("temple_traitor_strikes",),
    )
    assert prepare_battle(library, char).lineup.group == "temple_traitor"


def test_winning_variant_clears_flag(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(
        location="mist_temple_gate",
        pending_encounter=make_encounter("mist_temple_gate", seed=5, level=3),
        story_flags=("temple_traitor_strikes",),
    )
    result = world_step(
        library, make_world(), char, FightAction(steps=auto_steps(library, char)), NOON
    )
    won = result.char.last_battle is not None and result.char.last_battle.won
    cleared = [e for e in result.events if isinstance(e, StoryFlagClearedEvent)]
    if won:
        assert [e.flag for e in cleared] == ["temple_traitor_strikes"]
        assert result.char.story_flags == ()
    else:
        assert cleared == [] and result.char.story_flags == ("temple_traitor_strikes",)


def test_traitor_battle_completes_main_step_three(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(make_char(location="mist_temple_gate"), "main_mist_rift", steps_done=2)
    plain = _won("mist_temple_gate")
    _, none = advance_quests(library, make_world(), char, plain, NOON)
    assert not any(isinstance(e, QuestStepDoneEvent) for e in none)
    started = plain[0].model_copy(
        update={"lineup": plain[0].lineup.model_copy(update={"group": "temple_traitor"})}  # type: ignore[union-attr]
    )
    _, done = advance_quests(library, make_world(), char, (started, plain[1]), NOON)
    assert [e.step for e in done if isinstance(e, QuestStepDoneEvent)] == ["temple_split"]


# ---------------------------------------------------------------------------
# 導師任務鏈
# ---------------------------------------------------------------------------


def _battle(weather: str, skills: tuple[str, ...]) -> tuple[WorldEvent, ...]:
    started, ended = _won("bamboo_path")
    started = started.model_copy(update={"weather": weather})
    ended = ended.model_copy(update={"skills_used": skills})
    return (started, ended)


def test_mentor_needs_flag(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="mist_temple_gate")
    with pytest.raises(WorldActionError, match="開始條件"):
        world_step(
            library, make_world(), char, AcceptQuestAction(quest="mentor_qingya_trial"), NOON
        )
    flagged = char.model_copy(update={"story_flags": ("mentor_qingya",)})
    result = world_step(
        library, make_world(), flagged, AcceptQuestAction(quest="mentor_qingya_trial"), NOON
    )
    assert result.char.quest_state("mentor_qingya_trial") is not None


def test_mentor_chain_steps(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = _with_quest(make_char(), "mentor_qingya_trial")
    reflash = FlashPickedEvent(skill="a", new_skill="b", pick=0, slot=0)
    char, events = advance_quests(library, world, char, (reflash,), NOON)
    assert events == []  # 重閃不算「閃現」
    flash = reflash.model_copy(update={"slot": None})
    char, events = advance_quests(library, world, char, (flash,), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["observe_flash"]
    assert char.insight == 1
    assert [(e.npc, e.delta) for e in events if isinstance(e, AffinityChangedEvent)] == [
        ("daoist_qingya", 10)
    ]
    for weather, skills in (("clear", ("skill_bear_trap",)), ("fog", ())):
        _, none = advance_quests(library, world, char, _battle(weather, skills), NOON)
        assert none == []
    char, events = advance_quests(library, world, char, _battle("fog", ("skill_bear_trap",)), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["learn_from_mist"]
    dissolved = SkillDissolvedEvent(skill="a", refund=1, insight=1)
    char, events = advance_quests(library, world, char, (dissolved,), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["choose_path"]
    state = char.quest_state("mentor_qingya_trial")
    assert state is not None and state.done
    assert "title_qingya_disciple" in char.story_flags
    assert char.insight == 3
    assert char.affinity["daoist_qingya"] == 30
    assert char.xp == 0 and char.pending_offers == ()  # 不給經驗、不給技能
