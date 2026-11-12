"""預設傭兵與劇情夥伴阿岳（Phase 5C-3；``docs/phases/Phase5計畫.md`` 24.2、24.3）。

OB-7（#154）：開局只帶賽倫；阿岳在新手第 1 步（渡口石階）打完才入隊（任務的 ``companion_after``）。
替換與還原的機制照舊，用 2 名傭兵的隊伍（:data:`TWO`）測。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.shared.types import Team
from trpg.world.actions import (
    AcceptQuestAction,
    AffinityChangedEvent,
    BattleEndedEvent,
    BattleStartedEvent,
    CompanionJoinedEvent,
    CompanionLeftEvent,
    FightAction,
    HireAction,
    TravelAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.clock import refresh_day
from trpg.world.companions import companion_win_affinity, sync_companions
from trpg.world.errors import WorldActionError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState, QuestState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
AYUE = "companion_ayue"
DAY = 86_400
TWO = ("merc_tiebi", "merc_huichun")
"""自己雇滿 2 名的隊伍（OB-7 前的預設）。"""


def _accept(
    library: ContentLibrary, char: CharacterState, quest: str = "starter_ferry"
) -> CharacterState:
    return world_step(library, make_world(), char, AcceptQuestAction(quest=quest), NOON).char


def _first_step(char: CharacterState) -> CharacterState:
    """新手任務第 1 步完成（渡口石階打完）。"""
    states = tuple(
        q.model_copy(update={"steps_done": 1}) if q.quest == "starter_ferry" else q
        for q in char.quests
    )
    return char.model_copy(update={"quests": states})


def _with_ayue(library: ContentLibrary, char: CharacterState) -> CharacterState:
    """接新手任務、打完第 1 步、同步夥伴：阿岳入隊。"""
    joined, _ = sync_companions(library, _first_step(_accept(library, char)))
    return joined


def _done(char: CharacterState, *quests: str) -> CharacterState:
    states = tuple(
        q.model_copy(update={"done": True, "completed_at": NOON}) if q.quest in quests else q
        for q in char.quests
    )
    return char.model_copy(update={"quests": states})


def test_new_character_has_default_party(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert char.mercenaries == ("merc_tiebi",)  # #154：開局只帶賽倫
    assert char.companions == ()
    solo = world_step(library, make_world(), char, HireAction(mercenaries=()), NOON).char
    assert solo.mercenaries == ()  # 可以自己改成獨行


def test_ayue_joins_after_first_step_into_second_slot(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """#154：接任務時不加入；第 1 步完成才入隊、坐第 2 個隊友位；任務結束離隊後第 2 位留空。"""
    accepted = _accept(library, make_char())
    assert accepted.companions == ()
    joined, events = sync_companions(library, _first_step(accepted))
    assert events == [CompanionJoinedEvent(companion=AYUE, quest="starter_ferry")]
    assert joined.mercenaries == ("merc_tiebi",) and joined.companions == (AYUE,)
    left, events = sync_companions(library, _done(joined, "starter_ferry"))
    assert events == [CompanionLeftEvent(companion=AYUE)]
    assert left.mercenaries == ("merc_tiebi",) and left.companions == ()


def test_ayue_replaces_second_member_and_restores(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    joined = _with_ayue(library, make_char(mercenaries=TWO))
    assert joined.companions == (AYUE,)
    assert joined.mercenaries == ("merc_tiebi",)
    assert [b.member_id for b in joined.companion_bench] == ["merc_huichun"]
    # 任務還在進行：同步不變
    same, events = sync_companions(library, joined)
    assert same is joined and events == []
    left, events = sync_companions(library, _done(joined, "starter_ferry"))
    assert events == [
        CompanionLeftEvent(companion=AYUE, restored="merc_huichun", restored_name="回春")
    ]
    assert left.mercenaries == ("merc_tiebi", "merc_huichun") and left.companions == ()
    assert left.companion_bench == ()


def test_ayue_stays_while_main_chapter_runs(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _accept(library, _with_ayue(library, make_char(mercenaries=TWO)), "main_mist_rift")
    assert char.companions == (AYUE,)  # 同一名夥伴只佔一個位置
    still, _ = sync_companions(library, _done(char, "starter_ferry"))
    assert still.companions == (AYUE,)
    gone, _ = sync_companions(library, _done(char, "starter_ferry", "main_mist_rift"))
    assert gone.companions == () and gone.mercenaries == ("merc_tiebi", "merc_huichun")


def test_solo_joins_without_replacing(library: ContentLibrary, make_char: MakeChar) -> None:
    accepted = _accept(library, make_char(mercenaries=()))
    char, events = sync_companions(library, _first_step(accepted))
    joined = next(e for e in events if isinstance(e, CompanionJoinedEvent))
    assert joined.replaced is None and char.companion_bench == ()
    left, events = sync_companions(library, _done(char, "starter_ferry"))
    assert left.mercenaries == () and events[0] == CompanionLeftEvent(companion=AYUE)


def test_hire_while_companion_limits_slots_and_drops_restore(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    joined = _with_ayue(library, make_char(mercenaries=TWO))
    two = HireAction(mercenaries=("merc_qingfeng", "merc_chiyan"))
    try:
        world_step(library, make_world(), joined, two, NOON)
    except WorldActionError as exc:
        assert "劇情夥伴" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("夥伴在隊時不能雇滿 2 名")
    hired = world_step(
        library, make_world(), joined, HireAction(mercenaries=("merc_qingfeng",)), NOON
    ).char
    assert hired.companion_bench == ()
    left, events = sync_companions(library, _done(hired, "starter_ferry"))
    assert left.mercenaries == ("merc_qingfeng",)  # 玩家自己換過：不還原
    assert events == [CompanionLeftEvent(companion=AYUE)]


def test_battle_has_ayue_after_mercenaries(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_ayue(library, make_char())
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    ready = char.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    allies = [u for u in prepare_battle(library, ready).setup.units if u.team is Team.ALLY]
    assert [u.template.id for u in allies[1:]] == ["merc_tiebi", AYUE]
    assert allies[2].template.name_zh == "阿岳"
    assert allies[2].template.weapon == "bow"  # 代決 5C3-2：build_ranged


def test_win_with_ayue_gives_affinity_capped_daily(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_ayue(library, make_char())
    day_start = NOON
    total = 0
    for i in range(4):
        char, events = companion_win_affinity(library, char, day_start + i * 60)
        total += sum(e.delta for e in events if isinstance(e, AffinityChangedEvent))
    assert total == 6  # +2、+2、+2、上限
    assert char.affinity["hunter_ayue"] == 6
    record = char.companion_affinity[AYUE]
    assert record.day == refresh_day(day_start) and record.gained == 6
    char, events = companion_win_affinity(library, char, day_start + DAY)
    assert [e.delta for e in events if isinstance(e, AffinityChangedEvent)] == [2]  # 隔天重新計算


def test_fight_with_ayue_and_replay(calm: ContentLibrary, make_char: MakeChar) -> None:
    start = make_char()
    who = start.character_id
    joined = _with_ayue(calm, start)
    encounter = make_encounter(
        "ferry_steps", seed=5, battle_map="cliff_outpost", from_location="mist_ferry"
    )
    ready = joined.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    steps = auto_steps(calm, ready)
    fought = world_step(calm, make_world(), ready, FightAction(steps=steps), NOON + 60)
    started = next(e for e in fought.events if isinstance(e, BattleStartedEvent))
    assert started.companions == (AYUE,)
    won = next(e for e in fought.events if isinstance(e, BattleEndedEvent)).won
    liked = [
        e
        for e in fought.events
        if isinstance(e, AffinityChangedEvent) and e.source == f"companion_win:{AYUE}"
    ]
    assert len(liked) == (1 if won else 0)
    entries = [
        WorldLogEntry(
            seq=1, now=NOON, character_id=who, action=AcceptQuestAction(quest="starter_ferry")
        ),
        WorldLogEntry(
            seq=2, now=NOON + 30, character_id=who, action=TravelAction(to="ferry_steps")
        ),
        WorldLogEntry(seq=3, now=NOON + 60, character_id=who, action=TravelAction(to="mist_ferry")),
    ]
    first = replay(calm, make_world(), {who: start}, entries)
    second = replay(calm, make_world(), {who: start}, entries)
    assert dumps_char(first.characters[who]) == dumps_char(second.characters[who])
    assert first.characters[who].companions == ()  # #154：第 1 步還沒打完，阿岳還沒入隊
    assert first.characters[who].quest_state("starter_ferry") == QuestState(
        quest="starter_ferry", started_at=NOON
    )


def test_ayue_keeps_distance_with_archer_profile(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_ayue(library, make_char())
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    ready = char.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    allies = [u for u in prepare_battle(library, ready).setup.units if u.team is Team.ALLY]
    ayue = next(u for u in allies if u.template.id == AYUE)
    assert ayue.template.ai_profile == "archer"  # 5C-3b：遠程保持距離的打法（弓手）
    assert library.ai_profiles.by_id()["archer"].weights.keep_distance > 0
