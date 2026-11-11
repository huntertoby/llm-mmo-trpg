"""#150 開局結束：升到 4 級（Phase OB-3；21 21.5 第 5、6、9 點）。

- 正式選定過的角色到 4 級，``opening`` 清成 ``None``：重選過期，溶掉與傳承解鎖，之後就是一般角色。
- 4 級前溶掉、傳承一律擋（入門期與正式選定後都擋）。
- 一律看等級：其他經驗先到 4 級也算；還在入門期（沒正式選定）的不清，選定、三選一選完才結束。
- 世界日誌重播：正式選定 → 選三選一 → 重選 → 選三選一 → 打一場升到 4 級。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_world, with_rules
from tests.world.test_opening_choice import (
    MAX_FIGHT_SEEDS,
    _confirm,
    _fast_played,
    _step,
    _win,
)
from tests.world.test_opening_reselect import _again, _chosen
from trpg.api.world_newcomer_view import lesson_view
from trpg.content.library import ContentLibrary
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import (
    BattleEndedEvent,
    DissolveAction,
    FightAction,
    FlashAction,
    InheritAction,
    LeveledUpEvent,
    OfferPickAction,
    OpeningReselectedEvent,
    QuestStepDoneEvent,
    RestAction,
    TravelAction,
    WorldAction,
)
from trpg.world.battle import auto_steps
from trpg.world.common import rules_of
from trpg.world.errors import WorldActionError
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.opening_reselect import reselect_problem
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, dumps_world, loads_log
from trpg.world.state import CharacterState
from trpg.world.step import LESSON_ALLOCATE, world_step

type MakeChar = Callable[..., CharacterState]

BEFORE_4 = "4 級前不能溶掉技能或傳承"


def _dissolve_and_inherit(char: CharacterState) -> list[WorldAction]:
    skill, other = char.hero.skills[0], char.hero.skills[1]
    return [DissolveAction(skill=skill), InheritAction(skill=skill, source=other, records=(0,))]


def test_dissolve_and_inherit_blocked_before_level_4(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """入門期與正式選定後、4 級前：溶掉、傳承一律擋（OB-1 的閘門，這裡鎖住兩個階段）。"""
    world = make_world()
    for char in (_fast_played(library, make_char), _chosen(library, make_char)):
        assert char.opening is not None and char.level < OPENING_END_LEVEL
        for action in _dissolve_and_inherit(char):
            with pytest.raises(WorldActionError, match=BEFORE_4):
                _step(library, char, action, world)


def test_third_step_ends_the_opening(library: ContentLibrary, make_char: MakeChar) -> None:
    """真的打贏新手第 3 步（雨中梯田）：升到 4 級，開局結束；重選過期、溶掉與閃現解鎖。"""
    world = make_world()
    chosen = _chosen(library, make_char, mercenaries=PARTY)
    assert reselect_problem(library, chosen) is None
    result, _start = _win(library, world, chosen, "rain_terraces")
    char = result.char
    assert [e.index for e in result.events if isinstance(e, QuestStepDoneEvent)] == [3]
    assert [e.level for e in result.events if isinstance(e, LeveledUpEvent)] == [4]
    assert char.level == OPENING_END_LEVEL and char.opening is None
    town = char.model_copy(update={"location": "mist_ferry", "pending_offers": ()})
    # 重選過期
    assert "開局已經結束" in (reselect_problem(library, town) or "")
    with pytest.raises(WorldActionError, match="開局已經結束"):
        _step(library, town, _again("melee"), world)
    # 溶掉解鎖（真的溶掉一招）；傳承不再被「4 級前」擋（之後照它自己的規則）
    dissolved = _step(library, town, DissolveAction(skill=town.hero.skills[-1]), world).char
    assert len(dissolved.hero.skills) == len(town.hero.skills) - 1
    try:
        _step(library, town, _dissolve_and_inherit(town)[1], world)
    except WorldActionError as exc:
        assert BEFORE_4 not in str(exc)
    # 閃現解鎖：第 3 步打完回霧渡鎮才引導第一次閃現（配點教學上過之後）
    used = {s: acquire(s).model_copy(update={"used": True}) for s in town.hero.skills}
    ready = town.model_copy(
        update={
            "flash": dict(sorted(used.items())),
            "hints_seen": (LESSON_ALLOCATE,),
            "attribute_points": 0,
        }
    )
    assert ready.insight >= 1  # 靈感一路照常累積
    lesson = lesson_view(library, ready)
    assert lesson is not None and lesson.kind == "flash"
    flashed = _step(library, ready, FlashAction(skill=ready.hero.skills[0]), world).char
    assert flashed.pending_flash is not None


def test_other_xp_reaching_level_4_also_ends_it(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """一律看等級：不是靠第 3 步升到 4 級也一樣（下一個動作結算時清掉）。"""
    world = make_world()
    grown = _chosen(library, make_char).model_copy(update={"level": OPENING_END_LEVEL})
    assert "4 級之後不能重選" in (reselect_problem(library, grown) or "")
    after = _step(library, grown, RestAction(), world).char
    assert after.opening is None
    still = _step(library, _chosen(library, make_char), RestAction(), world).char
    assert still.opening is not None  # 3 級：還開著


def test_starter_stage_at_level_4_waits_for_the_choice(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """還在入門期（沒正式選定）先到 4 級：不清（還要選定）；選定、兩組三選一選完才結束，重選已經
    過期。"""
    world = make_world()
    played = _fast_played(library, make_char).model_copy(update={"level": OPENING_END_LEVEL})
    rested = _step(library, played, RestAction(), world).char
    assert rested.opening is not None and rested.opening.stage == "starter"
    char = _step(library, rested, _confirm("melee"), world).char
    assert char.opening is not None and len(char.pending_offers) == 1
    char = _step(library, char, OfferPickAction(pick=0), world).char
    assert char.opening is not None and len(char.pending_offers) == 1  # 第 2 組還要靠它出題
    char = _step(library, char, OfferPickAction(pick=0), world).char
    assert char.opening is None and char.pending_offers == ()
    assert len(char.hero.skills) + len(char.bench) == 4


# ---------------------------------------------------------------------------
# 世界日誌重播：正式選定 → 三選一 → 重選 → 三選一 → 升到 4 級
# ---------------------------------------------------------------------------


def _log_library(ambush: ContentLibrary) -> ContentLibrary:
    """每一步都遇敵；3 級到 4 級只差 1 點經驗（打贏任何一場就升級——「其他經驗先到 4 級」）。"""
    thresholds = list(rules_of(ambush).hero_growth.level_thresholds)
    thresholds[2] = thresholds[1] + 1
    return with_rules(ambush, hero_growth={"level_thresholds": thresholds})


def test_choice_reselect_level_4_log_replays_identically(
    ambush: ContentLibrary, make_char: MakeChar
) -> None:
    library = _log_library(ambush)
    start = _fast_played(library, make_char, mercenaries=PARTY)
    assert start.level == 3 and start.opening is not None
    actions: list[WorldAction] = [
        _confirm("melee"),
        OfferPickAction(pick=0),
        OfferPickAction(pick=1),
        _again("melee"),
        OfferPickAction(pick=2),
        OfferPickAction(),  # 第 2 組跳過
        RestAction(),
    ]
    world = make_world()
    char = start
    entries: list[WorldLogEntry] = []

    def record(action: WorldAction, now: int) -> tuple[object, ...]:
        nonlocal world, char
        result = world_step(library, world, char, action, now)
        world, char = result.world, result.char
        entries.append(
            WorldLogEntry(seq=len(entries) + 1, now=now, character_id="alice", action=action)
        )
        return result.events

    reselected = False
    for index, action in enumerate(actions):
        events = record(action, NOON + 60 * (index + 1))
        reselected = reselected or any(isinstance(e, OpeningReselectedEvent) for e in events)
    assert reselected and char.opening is not None and char.opening.reselect_used
    assert char.level == 3 and len(char.opening.granted_skills) == 3
    # 出鎮遇敵、打贏（換時間找會贏的一場）：升到 4 級，開局結束
    base, saved = NOON + 60 * (len(actions) + 1), (world, char, list(entries))
    for attempt in range(MAX_FIGHT_SEEDS):
        world, char = saved[0], saved[1]
        entries[:] = saved[2]
        record(TravelAction(to="ferry_steps"), base + 600 * attempt)
        assert char.pending_encounter is not None
        fight = FightAction(steps=auto_steps(library, char))
        events = record(fight, base + 600 * attempt + 60)
        if any(isinstance(e, BattleEndedEvent) and e.won for e in events):
            break
    else:
        pytest.fail("找不到會贏的一場")
    assert char.level == OPENING_END_LEVEL and char.opening is None
    first = replay(library, make_world(), {"alice": start}, entries)
    second = replay(library, make_world(), {"alice": start}, loads_log(dumps_log(entries)))
    assert dumps_char(first.characters["alice"]) == dumps_char(char)
    assert dumps_char(second.characters["alice"]) == dumps_char(char)
    assert dumps_world(first.world) == dumps_world(world) == dumps_world(second.world)
    assert first.events == second.events
