"""任務狀態機（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16.6、16.8）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from tests.world.test_situations import act, at_event, sure, thread
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.validate import validate_skill
from trpg.world.actions import (
    AcceptQuestAction,
    BattleEndedEvent,
    BattleStartedEvent,
    FightAction,
    InsightGainedEvent,
    OfferPickAction,
    QuestCompletedEvent,
    QuestStartedEvent,
    QuestStepDoneEvent,
    RestAction,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    StorySkillGrantedEvent,
    TalkAction,
    TalkedEvent,
    TravelAction,
    WorldEvent,
)
from trpg.world.battle import auto_steps
from trpg.world.common import rules_of
from trpg.world.encounters import EncounterLineup, LineupMember
from trpg.world.errors import WorldActionError
from trpg.world.quests import advance_quests
from trpg.world.state import CharacterState, FieldContact, FieldPos, QuestState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


STARTER_FIXED = {
    "ferry_steps": "bandit_raiders",
    "bamboo_path": "mist_wolf_pack",
    "rain_terraces": "terrace_clash",
}
"""新手三步的固定戰（6F-4b：只算打贏固定戰）；:func:`_won` 沒指定陣容時在這三個地點用它。"""


def _won(location: str, *, won: bool = True, group: str | None = None) -> tuple[WorldEvent, ...]:
    lineup = EncounterLineup(
        region="cloud_ridge",
        location=location,
        group=group if group is not None else STARTER_FIXED.get(location, "g"),
        members=(LineupMember(unit="mist_wolf"),),
    )
    started = BattleStartedEvent(
        location=location,
        battle_map="cliff_outpost",
        region="cloud_ridge",
        lineup=lineup,
        enemy_level=1,
        weather="clear",
        hero_hp=10,
        fatigued=False,
    )
    ended = BattleEndedEvent(
        won=won, end_reason=None, rounds=3, hp=10, mana=10, xp_gained=0, level=1
    )
    return (started, ended)


def _with_quest(char: CharacterState, quest: str, steps_done: int = 0) -> CharacterState:
    states = sorted(
        [*char.quests, QuestState(quest=quest, steps_done=steps_done, started_at=NOON)],
        key=lambda q: q.quest,
    )
    return char.model_copy(update={"quests": tuple(states)})


def _talked(events: tuple[WorldEvent, ...]) -> TalkedEvent:
    return next(e for e in events if isinstance(e, TalkedEvent))


def _share(library: ContentLibrary, source: str, level: int) -> int:
    return rules_of(library).xp.xp_for(source, level)


# ---------------------------------------------------------------------------
# 接任務
# ---------------------------------------------------------------------------


def test_accept_starter_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert char.location == "mist_ferry"
    result = world_step(library, make_world(), char, AcceptQuestAction(quest="starter_ferry"), NOON)
    assert result.events == (
        QuestStartedEvent(quest="starter_ferry", quest_kind="starter"),
        # 劇情夥伴阿岳等第 1 步打完才加入（OB-7，#154；tests/world/test_companions.py）
    )
    assert result.char.companions == ()
    state = result.char.quest_state("starter_ferry")
    assert state == QuestState(quest="starter_ferry", started_at=NOON)


def test_accept_rejections(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    away = make_char(location="ferry_steps")
    with pytest.raises(WorldActionError, match="給任務的人"):
        world_step(library, world, away, AcceptQuestAction(quest="starter_ferry"), NOON)
    with pytest.raises(WorldActionError, match="沒有任務"):
        world_step(library, world, make_char(), AcceptQuestAction(quest="nope"), NOON)
    hostile = make_char(affinity={"granny_du": -60})
    with pytest.raises(WorldActionError, match="敵視"):
        world_step(library, world, hostile, AcceptQuestAction(quest="starter_ferry"), NOON)
    taken = _with_quest(make_char(), "starter_ferry")
    with pytest.raises(WorldActionError, match="已經接過"):
        world_step(library, world, taken, AcceptQuestAction(quest="starter_ferry"), NOON)


def test_chain_needs_main_step_two(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(location="mist_temple_gate")
    with pytest.raises(WorldActionError, match="開始條件"):
        world_step(library, world, char, AcceptQuestAction(quest="chain_temple_split"), NOON)
    ready = _with_quest(char, "main_mist_rift", steps_done=2)
    result = world_step(library, world, ready, AcceptQuestAction(quest="chain_temple_split"), NOON)
    assert result.char.quest_state("chain_temple_split") is not None


# ---------------------------------------------------------------------------
# 新手任務鏈
# ---------------------------------------------------------------------------


def test_starter_steps_give_xp_insight_and_offer(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    char = _with_quest(make_char(location="ferry_steps"), "starter_ferry")
    char, events = advance_quests(library, world, char, _won("ferry_steps"), NOON)
    done = [e for e in events if isinstance(e, QuestStepDoneEvent)]
    assert [(e.step, e.index) for e in done] == [("ferry_bandits", 1)]
    # 6F-4 C2：第 1 步完成補到剛好 2 級（level_to: 2；比任務鏈一步 3 份＝300 多）
    to_two = rules_of(library).hero_growth.level_thresholds[0]
    assert done[0].xp == to_two > _share(library, "quest_chain_step", 1) == 300
    assert char.xp == to_two and char.level == 2
    assert char.insight >= 1
    assert any(
        isinstance(e, InsightGainedEvent) and e.source == "quest:starter_ferry" for e in events
    )
    offered = [e for e in events if isinstance(e, SkillOfferedEvent)]
    assert len(offered) == 1 and offered[0].reason == "level_up"
    assert len(offered[0].candidates) == 3
    assert len(char.pending_offers) == 1
    assert char.offers_made == 1
    state = char.quest_state("starter_ferry")
    assert state is not None and state.steps_done == 1 and not state.done


def test_lost_battle_or_wrong_place_does_nothing(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(make_char(location="ferry_steps"), "starter_ferry")
    for events in (_won("ferry_steps", won=False), _won("bamboo_path"), ()):
        after, out = advance_quests(library, make_world(), char, events, NOON)
        assert out == [] and after == char


def test_event_condition_counts_once_per_action(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """同一場勝利只完成一步（第 2 步也是 win_battle，雖然地點不同也不會被同一動作推進）。"""
    char = _with_quest(make_char(), "starter_ferry")
    events = (*_won("ferry_steps"), *_won("bamboo_path"))
    char, out = advance_quests(library, make_world(), char, events, NOON)
    assert [e.step for e in out if isinstance(e, QuestStepDoneEvent)] == ["ferry_bandits"]


def test_starter_completes_after_three_steps(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_quest(make_char(), "starter_ferry")
    world = make_world()
    for location in ("ferry_steps", "bamboo_path", "rain_terraces"):
        char, out = advance_quests(library, world, char, _won(location), NOON)
        char = char.model_copy(update={"pending_offers": ()})
    assert any(isinstance(e, QuestCompletedEvent) for e in out)
    state = char.quest_state("starter_ferry")
    assert state is not None and state.done and state.completed_at == NOON
    after, more = advance_quests(library, world, char, _won("rain_terraces"), NOON)
    assert more == [] and after == char


def test_real_fight_advances_starter(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_quest(make_char(location="ferry_steps", mercenaries=PARTY), "starter_ferry")
    for seed in range(16):
        encounter = make_encounter("ferry_steps", seed=seed, battle_map="cliff_outpost")
        contact = FieldContact(  # 6F-4b：新手步驟只算打贏固定戰（渡口的 bandit_raiders）
            map="ferry_steps",
            spawn=0,
            group=STARTER_FIXED["ferry_steps"],
            lineup_seed=seed,
            x=0,
            y=0,
            retreat_to=FieldPos(map="ferry_steps", x=0, y=0),
        )
        start = char.model_copy(
            update={"pending_encounter": encounter.model_copy(update={"contact": contact})}
        )
        result = world_step(
            library, make_world(), start, FightAction(steps=auto_steps(library, start)), NOON
        )
        if any(isinstance(e, BattleEndedEvent) and e.won for e in result.events):
            break
    else:
        pytest.fail("找不到會贏的種子")
    assert any(isinstance(e, QuestStepDoneEvent) for e in result.events)
    assert result.char.pending_offers


# ---------------------------------------------------------------------------
# 三選一
# ---------------------------------------------------------------------------


def _offered(library: ContentLibrary, make_char: MakeChar, location: str) -> CharacterState:
    char = _with_quest(make_char(location=location), "starter_ferry")
    char, _ = advance_quests(library, make_world(), char, _won("ferry_steps"), NOON)
    return char


def test_pending_offer_blocks_other_actions(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _offered(library, make_char, "ferry_steps")
    with pytest.raises(WorldActionError, match="三選一沒有選"):
        world_step(library, make_world(), char, TravelAction(to="mist_ferry"), NOON)


def test_offer_in_the_wild_goes_to_bench(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _offered(library, make_char, "ferry_steps")
    candidate = char.pending_offers[0].offer.candidates[0]
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        world_step(
            library, make_world(), char, OfferPickAction(pick=0, replace=char.hero.skills[0]), NOON
        )
    result = world_step(library, make_world(), char, OfferPickAction(pick=0), NOON)
    taken = next(e for e in result.events if isinstance(e, SkillOfferTakenEvent))
    assert taken.placed == "bench"
    assert taken.skill is not None and taken.skill in result.char.bench
    assert result.char.hero.skills == char.hero.skills
    assert result.char.pending_offers == ()
    assert candidate.name_zh  # 候選照存，不重抽


def test_offer_in_town_equips(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _offered(library, make_char, "mist_ferry")
    result = world_step(library, make_world(), char, OfferPickAction(pick=1), NOON)
    taken = next(e for e in result.events if isinstance(e, SkillOfferTakenEvent))
    assert taken.skill is not None
    if taken.placed == "equipped":
        assert taken.skill in result.char.hero.skills
    else:  # 裝不下又沒指定替換：放進備用
        assert taken.skill in result.char.bench


def test_offer_skip(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _offered(library, make_char, "ferry_steps")
    result = world_step(library, make_world(), char, OfferPickAction(), NOON)
    taken = next(e for e in result.events if isinstance(e, SkillOfferTakenEvent))
    assert taken.placed == "skipped" and taken.skill is None
    assert result.char.bench == char.bench
    with pytest.raises(WorldActionError, match="沒有待選"):
        world_step(library, make_world(), result.char, OfferPickAction(), NOON)
    with pytest.raises(WorldActionError, match="索引"):
        world_step(library, make_world(), char, OfferPickAction(pick=7), NOON)


def test_offer_is_deterministic(library: ContentLibrary, make_char: MakeChar) -> None:
    a = _offered(library, make_char, "ferry_steps")
    b = _offered(library, make_char, "ferry_steps")
    assert a.pending_offers == b.pending_offers


# ---------------------------------------------------------------------------
# 主線第 1 章
# ---------------------------------------------------------------------------


def test_main_step_one_by_thread(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _with_quest(make_char(), "main_mist_rift")
    char = char.model_copy(update={"threads": (thread("missing_went_to_rift", "lantern_patrol"),)})
    char, events = advance_quests(library, make_world(), char, (), NOON)
    done = [e for e in events if isinstance(e, QuestStepDoneEvent)]
    assert [e.step for e in done] == ["missing_townsfolk"]
    assert done[0].xp == _share(library, "main_step", 1) == 500  # 主線一步 5 份


def test_main_enter_temple_needs_trust_or_pass(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(make_char(location="mist_temple_gate"), "main_mist_rift", steps_done=1)
    world = make_world()
    _, events = advance_quests(library, world, char, (), NOON)
    assert events == []  # 拒絕外人
    friendly = char.model_copy(update={"affinity": {"acolyte_xiaolian": 20}})
    _, events = advance_quests(library, world, friendly, (), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["enter_temple"]
    with_pass = char.model_copy(update={"threads": (thread("temple_pass", "crane_envoy"),)})
    _, events = advance_quests(library, world, with_pass, (), NOON)
    assert any(isinstance(e, StorySkillGrantedEvent) for e in events)


def test_story_skill_is_complete_tiered_and_benched(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(make_char(location="mist_temple_gate"), "main_mist_rift", steps_done=1)
    char = char.model_copy(update={"affinity": {"daoist_qingya": 30}})
    after, events = advance_quests(library, make_world(), char, (), NOON)
    granted = next(e for e in events if isinstance(e, StorySkillGrantedEvent))
    assert granted.skill == "skill_mist_breaker"
    assert granted.skill in after.bench
    assert granted.skill not in after.hero.skills
    skill = next(s for s in after.generated_skills if s.id == granted.skill)
    assert skill.name_zh == "破霧"
    assert after.flash[granted.skill].complete  # 完整技能：不能再閃（06 6.34.6）
    # 已擁有就不再給
    again = _with_quest(after.model_copy(update={"quests": ()}), "main_mist_rift", steps_done=1)
    _, more = advance_quests(library, make_world(), again, (), NOON)
    assert not any(isinstance(e, StorySkillGrantedEvent) for e in more)


def test_main_temple_split_by_situation(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = sure(library, "monks_see_lie", "success")
    char = _with_quest(make_char(), "main_mist_rift", steps_done=2)
    char = at_event(char, "monks_dispute", "mist_temple_gate", strong=True)
    action = act("monks_see_lie", attribute=Attribute.WIS, method="notice")
    result = world_step(lib, make_world(), char, action, NOON)
    done = [e.step for e in result.events if isinstance(e, QuestStepDoneEvent)]
    assert done == ["temple_split"]
    assert result.char.affinity["acolyte_xiaolian"] == 10 + 10  # 5B-4c 步驟 +10、5B-4e 骨架 6 +10
    assert result.char.affinity["daoist_qingya"] == 20  # 事件好感度（骨架 6 成功）＋10


def test_main_rift_battle_substitutes_three_way(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(make_char(), "main_mist_rift", steps_done=3)
    char, events = advance_quests(library, make_world(), char, _won("crystal_rift"), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["rift_battle"]


# ---------------------------------------------------------------------------
# 區域任務鏈與隱藏任務
# ---------------------------------------------------------------------------


def test_chain_flow(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = _with_quest(make_char(location="herb_valley"), "chain_temple_split")
    char, events = advance_quests(library, world, char, (), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["deliver_letter"]
    assert not char.pending_offers
    char = char.model_copy(update={"threads": (thread("temple_traitor", "monks_dispute"),)})
    char, events = advance_quests(library, world, char, (), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["find_traitor"]
    assert len(char.pending_offers) == 1  # 中段三選一
    char = char.model_copy(update={"pending_offers": ()})
    char, events = advance_quests(library, world, char, _won("cliff_gang_fort"), NOON)
    assert any(isinstance(e, QuestCompletedEvent) for e in events)
    assert len(char.pending_offers) == 1  # 結尾三選一
    assert char.story_flags == ("mentor_qingya",)
    assert char.affinity["daoist_qingya"] == 30  # 5B-4c：每步 +10
    assert char.insight >= 3


def test_hidden_quest_from_talk(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char()
    with pytest.raises(WorldActionError, match="開始條件"):
        world_step(library, world, char, AcceptQuestAction(quest="hidden_elixir_cave"), NOON)
    friendly = char.model_copy(update={"affinity": {"shopkeeper_liu": 25}})
    talked = world_step(library, world, friendly, TalkAction(npc="shopkeeper_liu"), NOON)
    assert _talked(talked.events).quests_available == ("hidden_elixir_cave",)
    accepted = world_step(
        library, world, friendly, AcceptQuestAction(quest="hidden_elixir_cave"), NOON
    )
    char = accepted.char.model_copy(update={"location": "elixir_cave"})
    char, events = advance_quests(library, world, char, (), NOON)
    done = [e for e in events if isinstance(e, QuestStepDoneEvent)]
    assert done[0].xp == _share(library, "hidden_location", 5)  # 隱藏地點 2 份
    talked = world_step(
        library,
        world,
        friendly.model_copy(update={"quests": char.quests}),
        TalkAction(npc="shopkeeper_liu"),
        NOON,
    )
    assert _talked(talked.events).quests_available == ()


def test_frost_riddle_starts_from_clue(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    char = make_char(location="crane_cliff")
    with pytest.raises(WorldActionError, match="開始條件"):
        world_step(library, world, char, AcceptQuestAction(quest="hidden_frost_riddle"), NOON)
    clued = char.model_copy(update={"threads": (thread("foxfire_guide", "fox_traveler"),)})
    result = world_step(library, world, clued, AcceptQuestAction(quest="hidden_frost_riddle"), NOON)
    assert result.char.quest_state("hidden_frost_riddle") is not None


def test_no_quests_no_extra_events(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    result = world_step(library, make_world(), char, RestAction(), NOON)
    assert all(not isinstance(e, QuestStepDoneEvent) for e in result.events)
    after, events = advance_quests(library, make_world(), char, _won("ferry_steps"), NOON)
    assert events == [] and after == char


# ---------------------------------------------------------------------------
# 5B-4b：新手鏈保底、區域任務鏈偏向（Phase5計畫 19.4、19.5）
# ---------------------------------------------------------------------------

REGION_KEYWORDS = ("wet", "charged", "concealed")


def test_starter_first_offer_is_deepen_bridge_new_with_passive(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """#130（6F-4）：新手第 1 步的三選一＝加深 1、橋接 1、新方向 1；橋接能湊到時帶兩個起始關鍵字，
    每張候選都是組合器實際做出、通過驗證的技能（可行解，6E-W 的做法）。"""
    pairs = 0
    for name in ("alice", "bob", "carol", "dave"):
        char = _with_quest(make_char(name, location="ferry_steps"), "starter_ferry")
        char, _ = advance_quests(library, make_world(), char, _won("ferry_steps"), NOON)
        offer = char.pending_offers[0].offer
        assert [t.kind for t in offer.tags] == ["deepen", "bridge", "new"], name
        assert any(s.kind == "passive" for s in offer.candidates), name
        for skill in offer.candidates:
            assert validate_skill(skill, library) == [], (name, skill.id)
        bridge = offer.tags[1]
        if len(bridge.keywords) == 2:
            pairs += 1
            made = derive_keywords(offer.candidates[1], library.keywords, exclusive_only=True)
            assert set(bridge.keywords) <= set(made.all()), name
    assert pairs >= 1


def test_starter_later_steps_keep_one_deepen_two_new(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(make_char("alice", location="bamboo_path"), "starter_ferry", steps_done=1)
    char, _ = advance_quests(library, make_world(), char, _won("bamboo_path"), NOON)
    assert [t.kind for t in char.pending_offers[0].offer.tags] == ["deepen", "new", "new"]


def test_chain_offer_new_direction_prefers_region_keywords(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    hits = 0
    for name in ("alice", "bob", "carol", "dave", "erin", "frank"):
        char = _with_quest(make_char(name), "chain_temple_split", steps_done=1)
        char = char.model_copy(update={"threads": (thread("temple_traitor", "monks_dispute"),)})
        char, _ = advance_quests(library, make_world(), char, (), NOON)
        offer = char.pending_offers[0].offer
        assert [t.kind for t in offer.tags] == ["deepen", "bridge", "new"]
        new = offer.tags[2]
        if new.keywords:  # 通用池白板（#55）照舊
            assert new.keywords[0] in REGION_KEYWORDS, name
            hits += 1
    assert hits >= 3
