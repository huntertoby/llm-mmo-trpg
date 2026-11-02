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
from trpg.world.solutions import make_encounter as open_encounter
from trpg.world.state import CharacterState, EncounterResult, TimedFlag
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


# ---------------------------------------------------------------------------
# 世界級線頭的到期結局（Phase 5B-4c；Phase5計畫 21.7）
# ---------------------------------------------------------------------------

TWO_DAYS = 172_800


def test_world_thread_ending_gives_timed_flag(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world(threads=(thread("wraiths_from_rift", "possessed_hunter", OLD),))
    result = world_step(library, world, make_char(), TavernAction(), NOON)
    expired = [e for e in result.events if isinstance(e, ThreadExpiredEvent)]
    until = OLD + 259_200 + TWO_DAYS  # 從線頭到期起算 2 天
    assert [(e.thread, e.scope, e.flag, e.until) for e in expired] == [
        ("wraiths_from_rift", "world", "wraiths_surge", until)
    ]
    assert result.world.threads == ()
    assert result.world.flags == ()  # 限時旗標不進永久旗標
    assert result.world.timed_flags == (TimedFlag(flag="wraiths_surge", until=until),)
    assert result.world.active_flags(NOON) == ("wraiths_surge",)
    assert result.world.active_flags(until) == ()


def test_shards_ending_is_permanent_world_flag(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world(threads=(thread("shards_to_ashen", "shard_convoy", OLD),))
    result = world_step(library, world, make_char(), TavernAction(), NOON)
    expired = next(e for e in result.events if isinstance(e, ThreadExpiredEvent))
    assert (expired.flag, expired.until) == ("ashen_heart_hardened", None)
    assert result.world.flags == ("ashen_heart_hardened",)
    assert result.world.timed_flags == ()


def test_timed_flag_takes_later_until(library: ContentLibrary, make_char: MakeChar) -> None:
    late = NOON + 10 * TWO_DAYS
    world = make_world(
        threads=(thread("wraiths_from_rift", "possessed_hunter", OLD),),
        timed_flags=(TimedFlag(flag="wraiths_surge", until=late),),
    )
    result = world_step(library, world, make_char(), TavernAction(), NOON)
    assert result.world.timed_flags == (TimedFlag(flag="wraiths_surge", until=late),)


def _night(location: str, flags: tuple[str, ...], seed: int = 3) -> EncounterResult:
    return make_encounter(location, seed=seed).model_copy(
        update={"day_phase": "night", "world_flags": flags}
    )


def test_wraith_surge_adds_one_at_night_camps(library: ContentLibrary) -> None:
    for seed in range(6):
        plain = roll_lineup(library, _night("ferry_steps", (), seed))
        surged = roll_lineup(library, _night("ferry_steps", ("wraiths_surge",), seed))
        assert surged.members[: len(plain.members)] == plain.members  # 亂數不變
        assert [m.unit for m in surged.members[len(plain.members) :]] == ["mist_wraith"]
        assert surged.members[-1].affix is None
    day = make_encounter("ferry_steps", seed=3).model_copy(
        update={"world_flags": ("wraiths_surge",)}
    )
    assert roll_lineup(library, day) == roll_lineup(library, make_encounter("ferry_steps", seed=3))
    rift = roll_lineup(library, _night("crystal_rift", ("wraiths_surge",)))
    assert rift == roll_lineup(library, _night("crystal_rift", ()))  # 不是營地


def test_wraith_surge_skips_full_and_variant(library: ContentLibrary) -> None:
    for seed in range(8):
        plain = roll_lineup(library, _night("cliff_gang_fort", (), seed))
        surged = roll_lineup(library, _night("cliff_gang_fort", ("wraiths_surge",), seed))
        if len(plain.members) >= 4:
            assert surged == plain  # 滿 4 名不加
    risen = roll_lineup(
        library,
        _night("cliff_gang_fort", ("wraiths_surge",)),
        ("scarface_rises",),
    )
    assert "mist_wraith" not in [m.unit for m in risen.members]  # 遭遇變化不加


def test_encounter_records_active_world_flags(library: ContentLibrary, make_char: MakeChar) -> None:
    until = NOON + TWO_DAYS
    world = make_world(timed_flags=(TimedFlag(flag="wraiths_surge", until=until),))
    place = library.world_maps["cloud_ridge"].location_by_id()["ferry_steps"]
    during, _ = open_encounter(library, world, make_char(), place, NOON)
    assert during.world_flags == ("wraiths_surge",)
    after, _ = open_encounter(library, world, make_char(), place, until)
    assert after.world_flags == ()
