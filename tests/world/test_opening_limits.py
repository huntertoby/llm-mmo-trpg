"""#150 入門期的戰鬥閘與活動限制（Phase OB-4；21 21.5 第 7、9 點，
:mod:`trpg.world.opening_limits`）。

一律跑真的世界動作。三種角色走同一條路線對照：

- **入門期**：選了大類、還沒正式選定（``stage=starter``）。
- **已選定**：同一個角色只把 ``stage`` 換成 ``chosen``（路線、亂數計數都一樣，才比得出差別）；
  另有一筆走完整流程（打完兩步 → 真的正式選定）的。
- **舊角色**：``opening is None``。

實地地圖用正式內容（``content_library``）；節點移動、事件用沒有實地地圖的內容庫（同 5A～5F 的
測試）。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_encounter, make_world, without_fields
from tests.world.test_events import NIGHT
from tests.world.test_field_things import _path
from tests.world.test_opening_choice import CHOICES, QUEST, _fast_played
from tests.world.test_opening_stages import _starter
from tests.world.test_opportunity import ALTAR, CHARGED, DAY6, OPPORTUNITY
from tests.world.test_quests import _with_quest, _won
from tests.world.test_situations import at_event, peddler, sure, thread
from trpg.api.world_field_view import field_view
from trpg.api.world_story_view import event_view
from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathProposal
from trpg.content.world_quests import AnyOf
from trpg.world import opening_choice, opening_limits
from trpg.world.actions import (
    AcceptQuestAction,
    BattleEndedEvent,
    CampAction,
    CampedEvent,
    EncounterCheckEvent,
    EncounterEvent,
    EventSolveAction,
    EventTriggeredEvent,
    FightAction,
    HintSeenAction,
    HireAction,
    LoadoutAction,
    OfferPickAction,
    OpeningClassAction,
    OpeningConfirmAction,
    QuestStartedEvent,
    QuestStepDoneEvent,
    ReleaseOathAction,
    ShadowAiAction,
    SkillOfferedEvent,
    StorySkillGrantedEvent,
    SwearOathAction,
    TravelAction,
    WorldAction,
)
from trpg.world.battle import auto_steps
from trpg.world.errors import WorldActionError
from trpg.world.events import guaranteed_opportunity, mark_met_opportunities
from trpg.world.field import field_grid
from trpg.world.field_actions import UseFieldObjectAction, WalkAction
from trpg.world.field_enemies import field_enemies, with_visit
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.opening import new_opening, pending_hero
from trpg.world.opening_limits import FIGHT_ZH, OBJECT_ZH, SOLUTION_ZH, in_starter_period
from trpg.world.quests import advance_quests
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, loads_log
from trpg.world.season_events import SeasonBossAction
from trpg.world.state import CharacterState, FieldContact, FieldPos, WorldState
from trpg.world.step import StepResult, camp_problem, new_character, world_step

type MakeChar = Callable[..., CharacterState]
type XY = tuple[int, int]

REGION = "cloud_ridge"
SIDES: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))
STARTER_SHOWN = {"ferry_steps": {0}, "bamboo_path": {0}}
"""入門期看得到的隊伍（地圖 → ``spawns`` 索引）：只有新手第 1、2 步的固定戰；沒列的地圖＝一隊都沒有
（雨中梯田的第 3 步固定戰、各圖的巡邏與駐守）。"""
HIDDEN_NAMED = (
    ("ferry_steps", "bandit_shield_line", NIGHT),  # 石階夜間巡邏
    ("bamboo_path", "bandit_wolf_handler", NOON),  # 竹林巡邏
    ("rain_terraces", "terrace_clash", NOON),  # 第 3 步固定戰
    ("rain_terraces", "terrace_patrol", NOON),  # 田埂巡邏
)


def _chosen(char: CharacterState) -> CharacterState:
    """同一個角色、只把階段換成已正式選定（對照用：其他狀態與亂數計數都一樣）。"""
    assert char.opening is not None
    opening = char.opening.model_copy(update={"stage": "chosen"})
    return char.model_copy(update={"opening": opening})


def _old(char: CharacterState) -> CharacterState:
    return char.model_copy(update={"opening": None})


def _step(
    library: ContentLibrary,
    char: CharacterState,
    action: WorldAction,
    now: int = NOON,
    world: WorldState | None = None,
) -> StepResult:
    return world_step(library, world or make_world(), char, action, now)


def _maps(library: ContentLibrary) -> list[str]:
    """雲嶺有敵人的室外圖。"""
    return sorted(
        m.id
        for m in library.field_maps.values()
        if m.region == REGION and not m.is_interior and m.spawns
    )


def _enter(library: ContentLibrary, char: CharacterState, map_id: str) -> CharacterState:
    """站到 ``map_id`` 的入口、開始這一趟。"""
    found = library.field_maps[map_id]
    pos = FieldPos(map=map_id, x=found.entry[0], y=found.entry[1])
    char = char.model_copy(
        update={
            "region": REGION,
            "location": found.place,
            "field": pos,
            "field_visit": None,
            "pending_encounter": None,
        }
    )
    return with_visit(library, make_world(), char)


def _beside(
    library: ContentLibrary, char: CharacterState, target: XY
) -> tuple[CharacterState, WalkAction]:
    """把角色放到離 ``target`` 兩步的格子，回傳（角色, 走一步到 ``target`` 相鄰格的動作）。"""
    assert char.field is not None
    found = library.field_maps[char.field.map]
    grid = field_grid(library, char, found)
    climb = library.ruleset.core.max_climb_height
    portals = {c for e in found.exits for c in e.at} | {d.at for d in found.doors}
    portals |= {s.at for s in found.teleport_stones}
    for dx, dy in SIDES:
        near = (target[0] + dx, target[1] + dy)
        if not grid.standable(near) or near in portals:
            continue
        for ex, ey in SIDES:
            start = (near[0] + ex, near[1] + ey)
            if start == target or start in portals or not grid.standable(start):
                continue
            if grid.can_step(start, near, climb):
                pos = char.field.model_copy(update={"x": start[0], "y": start[1]})
                return char.model_copy(update={"field": pos}), WalkAction(path=(near,))
    pytest.fail(f"{found.id} 的 {target} 旁邊沒有走得到的格子")


def _touch(
    library: ContentLibrary, char: CharacterState, index: int, now: int
) -> tuple[CharacterState, StepResult]:
    """走到第 ``index`` 隊旁邊（位置照舊角色看到的；入門期看不到也照樣走過去）。"""
    world = make_world()
    enemy = next(e for e in field_enemies(library, world, _old(char), now) if e.index == index)
    start, walk = _beside(library, char, enemy.xy)
    return start, _step(library, start, walk, now, world)


def _shown(library: ContentLibrary, char: CharacterState, now: int) -> set[int]:
    """畫面清單（``FieldView.enemies``）裡的隊伍索引；順便檢查和 :func:`field_enemies` 一致。"""
    world = make_world()
    view = field_view(library, char, world=world, now=now)
    assert view is not None
    listed = {int(e.id.removeprefix("e")) for e in view.enemies}
    assert listed == {e.index for e in field_enemies(library, world, char, now)}
    return listed


def _contact(result: StepResult) -> int | None:
    encounter = result.char.pending_encounter
    if encounter is None:
        assert not any(isinstance(e, EncounterEvent) for e in result.events)
        return None
    assert encounter.contact is not None
    return encounter.contact.spawn


# ---------------------------------------------------------------------------
# 常數、入門期的定義
# ---------------------------------------------------------------------------


def test_starter_steps_match_formal_choice() -> None:
    assert opening_limits.STARTER_STEPS == opening_choice.STARTER_STEPS == 2


def test_starter_period_definition(library: ContentLibrary, make_char: MakeChar) -> None:
    starter = _starter(library, make_char)
    pending = make_char(opening=new_opening(7))
    assert in_starter_period(starter) and in_starter_period(pending)
    assert not in_starter_period(_chosen(starter))
    assert not in_starter_period(make_char())


# ---------------------------------------------------------------------------
# 實地地圖的敵人：畫面清單與實際接觸一致（表格：雲嶺每張有敵人的圖 × 白天、夜晚 × 每一隊）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("now", [NOON, NIGHT], ids=["day", "night"])
def test_field_enemies_table(
    content_library: ContentLibrary, library: ContentLibrary, make_char: MakeChar, now: int
) -> None:
    lib = content_library
    starter = _with_quest(_starter(library, make_char), QUEST)
    assert {"ferry_steps", "bamboo_path", "rain_terraces"} <= set(_maps(lib))
    for map_id in _maps(lib):
        new = _enter(lib, starter, map_id)
        chosen, old = _chosen(new), _old(new)
        everyone = _shown(lib, old, now)
        shown = _shown(lib, new, now)
        # 入門期只留新手第 1、2 步的固定戰；選定後與舊角色看到的一樣
        assert shown == STARTER_SHOWN.get(map_id, set()) & everyone, map_id
        assert _shown(lib, chosen, now) == everyone, map_id
        for index in sorted(everyone):
            label = f"{map_id}#{index}"
            _, walked = _touch(lib, new, index, now)
            hit = _contact(walked)
            if index in shown:  # 畫面清單裡的碰得到
                assert hit == index, label
            else:  # 不在清單裡的碰不到（走過去最多碰到清單裡的那一隊）
                assert hit is None or hit in shown, label
                assert hit != index, label
            # 選定後同一步恢復開戰；舊角色的事件和已選定的一模一樣
            _, walked_chosen = _touch(lib, chosen, index, now)
            _, walked_old = _touch(lib, old, index, now)
            assert _contact(walked_chosen) is not None, label
            assert walked_old.events == walked_chosen.events, label


@pytest.mark.parametrize(("map_id", "group", "now"), HIDDEN_NAMED)
def test_named_enemies_hidden_then_restored(  # noqa: PLR0917 - 表格的欄位
    content_library: ContentLibrary,
    library: ContentLibrary,
    make_char: MakeChar,
    map_id: str,
    group: str,
    now: int,
) -> None:
    lib = content_library
    index = next(i for i, s in enumerate(lib.field_maps[map_id].spawns) if s.group == group)
    new = _enter(lib, _with_quest(_starter(library, make_char), QUEST), map_id)
    assert index not in _shown(lib, new, now)
    _, walked = _touch(lib, new, index, now)
    assert _contact(walked) != index
    _, walked = _touch(lib, _chosen(new), index, now)
    assert _contact(walked) is not None
    assert index in _shown(lib, _chosen(new), now)


@pytest.mark.parametrize(
    ("map_id", "group"), [("ferry_steps", "bandit_raiders"), ("bamboo_path", "mist_wolf_pack")]
)
def test_starter_fixed_fights_open_in_starter_period(
    content_library: ContentLibrary,
    library: ContentLibrary,
    make_char: MakeChar,
    map_id: str,
    group: str,
) -> None:
    lib = content_library
    char = _with_quest(_starter(library, make_char, mercenaries=PARTY), QUEST)
    _, walked = _touch(lib, _enter(lib, char, map_id), 0, NOON)
    encounter = walked.char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.group == group
    fought = _step(lib, walked.char, FightAction(steps=auto_steps(lib, walked.char)))
    assert any(isinstance(e, BattleEndedEvent) for e in fought.events)  # 真的開戰、打完


def test_done_starter_step_is_gone_for_everyone(
    content_library: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    """第 1 步打完：渡口石階白天一隊都沒有（固定戰退場，其他的入門期看不到）。"""
    lib = content_library
    char = _with_quest(_starter(library, make_char), QUEST, steps_done=1)
    assert _shown(lib, _enter(lib, char, "ferry_steps"), NIGHT) == set()
    assert _shown(lib, _enter(lib, char, "bamboo_path"), NOON) == {0}


# ---------------------------------------------------------------------------
# 第 3 步固定戰與戰鬥閘
# ---------------------------------------------------------------------------


def _terrace_encounter(char: CharacterState) -> CharacterState:
    """硬塞一場雨中梯田固定戰的遭遇（正常流程入門期碰不到；驗戰鬥閘的最後一道）。"""
    contact = FieldContact(
        map="rain_terraces",
        spawn=0,
        group="terrace_clash",
        lineup_seed=1,
        x=0,
        y=0,
        retreat_to=FieldPos(map="rain_terraces", x=0, y=0),
    )
    pending = make_encounter("rain_terraces", seed=1, battle_map="cliff_outpost")
    pending = pending.model_copy(update={"contact": contact})
    return char.model_copy(update={"location": "rain_terraces", "pending_encounter": pending})


def test_fight_gate_blocks_everything_but_starter_fights(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    starter = _starter(library, make_char, mercenaries=PARTY)
    third = _terrace_encounter(starter)
    node = starter.model_copy(
        update={"location": "north_slope", "pending_encounter": make_encounter("north_slope")}
    )
    for blocked in (third, node):
        with pytest.raises(WorldActionError) as excinfo:
            _step(library, blocked, FightAction(steps=()))
        assert str(excinfo.value) == FIGHT_ZH
    # 選定後、舊角色：同一場照打
    for char in (_chosen(third), _old(third)):
        fought = _step(library, char, FightAction(steps=auto_steps(library, char)))
        assert any(isinstance(e, BattleEndedEvent) for e in fought.events)


def test_step_three_waits_for_formal_choice(
    content_library: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    """走完整流程：打完兩步 → 梯田的固定戰看不到、碰不到 → 真的正式選定 → 同一步開戰、能打。"""
    lib = content_library
    played = _fast_played(library, make_char, "melee", mercenaries=PARTY)
    before = _enter(lib, played, "rain_terraces")
    assert _shown(lib, before, NOON) == set()
    _, walked = _touch(lib, before, 0, NOON)
    assert _contact(walked) is None
    # 就算第 3 步的條件成立，入門期也不結算（給招的獎勵等正式選定）
    held, events = advance_quests(library, make_world(), played, _won("rain_terraces"), NOON)
    assert events == [] and held == played

    weapon, keywords = CHOICES["melee"]
    char = _step(library, played, OpeningConfirmAction(weapon=weapon, keywords=keywords)).char
    while char.pending_offers:
        char = _step(library, char, OfferPickAction(pick=None)).char
    assert char.opening is not None and char.opening.stage == "chosen"
    after = _enter(lib, char, "rain_terraces")
    assert 0 in _shown(lib, after, NOON)
    _, walked = _touch(lib, after, 0, NOON)
    encounter = walked.char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.group == "terrace_clash"
    fought = _step(lib, walked.char, FightAction(steps=auto_steps(lib, walked.char)))
    assert any(isinstance(e, BattleEndedEvent) for e in fought.events)
    done, events = advance_quests(library, make_world(), char, _won("rain_terraces"), NOON)
    assert [e.step for e in events if isinstance(e, QuestStepDoneEvent)] == ["terrace_clash"]
    assert any(isinstance(e, SkillOfferedEvent) for e in events) and done.level == 4


# ---------------------------------------------------------------------------
# 節點移動的遭遇
# ---------------------------------------------------------------------------


def test_node_travel_never_encounters_in_starter_period(
    ambush: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    starter = _starter(library, make_char)
    route = ("ferry_steps", "bamboo_path", "rain_terraces")
    char = starter
    for to in route:
        result = _step(ambush, char, TravelAction(to=to))
        check = next(e for e in result.events if isinstance(e, EncounterCheckEvent))
        assert (check.chance_permille, check.encountered) == (0, False)
        assert result.char.pending_encounter is None
        char = result.char
    assert char.location == route[-1]
    # 選定後、舊角色：同一步照常遇敵；擲的骰和入門期同一顆（亂數消耗不變）
    first = next(
        e
        for e in _step(ambush, starter, TravelAction(to=route[0])).events
        if isinstance(e, EncounterCheckEvent)
    )
    for other in (_chosen(starter), _old(starter)):
        result = _step(ambush, other, TravelAction(to=route[0]))
        check = next(e for e in result.events if isinstance(e, EncounterCheckEvent))
        assert check.encountered and check.roll == first.roll
        assert result.char.pending_encounter is not None
    assert (
        _step(ambush, _old(starter), TravelAction(to=route[0])).events
        == _step(ambush, _chosen(starter), TravelAction(to=route[0])).events
    )


# ---------------------------------------------------------------------------
# 事件解法、機遇、情境物件
# ---------------------------------------------------------------------------


def _charged(char: CharacterState) -> CharacterState:
    skills = (CHARGED, *char.hero.skills[1:])
    return char.model_copy(update={"hero": char.hero.model_copy(update={"skills": skills})})


def test_combat_solution_blocked_then_restored(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = at_event(_starter(library, make_char), "wounded_peddler")
    with pytest.raises(WorldActionError) as excinfo:
        _step(library, char, EventSolveAction(solution=0))
    assert str(excinfo.value) == SOLUTION_ZH["combat"]
    view = event_view(library, make_world(), char, NOON, ())
    assert view is not None
    assert not view.solutions[0].available
    assert view.solutions[0].unavailable_zh == SOLUTION_ZH["combat"]
    assert view.solutions[2].kind == "abandon" and view.solutions[2].available
    restored = _step(library, _chosen(char), EventSolveAction(solution=0))
    assert restored.char.pending_encounter is not None
    view = event_view(library, make_world(), _chosen(char), NOON, ())
    assert view is not None and view.solutions[0].available


def test_opportunity_blocked_then_restored(library: ContentLibrary, make_char: MakeChar) -> None:
    char = at_event(_charged(_starter(library, make_char)), ALTAR, "old_pine_altar")
    with pytest.raises(WorldActionError) as excinfo:
        _step(library, char, EventSolveAction(solution=OPPORTUNITY))
    assert str(excinfo.value) == SOLUTION_ZH["opportunity"]
    view = event_view(library, make_world(), char, NOON, ())
    assert view is not None
    assert view.solutions[OPPORTUNITY].unavailable_zh == SOLUTION_ZH["opportunity"]
    restored = _step(library, _chosen(char), EventSolveAction(solution=OPPORTUNITY))
    assert any(isinstance(e, SkillOfferedEvent) for e in restored.events)


def test_opportunity_guarantee_is_kept_for_later(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """入門期不出機遇保底、碰到機遇骨架也不算遇過：保底留到正式選定之後。"""
    world = make_world()
    char = _starter(library, make_char).model_copy(update={"location": "old_pine_altar"})
    assert guaranteed_opportunity(library, world, char, DAY6) is None
    assert guaranteed_opportunity(library, world, _chosen(char), DAY6) is not None
    met = at_event(char, ALTAR, "old_pine_altar")
    assert met.pending_event is not None
    events = (EventTriggeredEvent(trigger=met.pending_event),)
    assert mark_met_opportunities(library, met, events).met_opportunities == ()
    assert mark_met_opportunities(library, _chosen(met), events).met_opportunities == (ALTAR,)


def test_peaceful_solutions_still_work(library: ContentLibrary, make_char: MakeChar) -> None:
    """不開戰也不給招的照常：放棄、情境判定。"""
    char = at_event(_starter(library, make_char), "wounded_peddler")
    left = _step(library, char, EventSolveAction(solution=2))
    assert left.char.pending_event is None
    lib = sure(library, "peddler_safe_path", "success")
    strong = at_event(_starter(library, make_char), "wounded_peddler", strong=True)
    judged = _step(lib, strong, peddler())
    assert judged.char.pending_event is None and judged.char.pending_encounter is None
    assert not judged.char.pending_offers


def test_boss_gate_object_blocked_then_restored(
    content_library: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    lib = content_library
    gate = next(
        s for s in lib.field_maps["cloud_summit"].situation_objects if s.id == "summit_gate"
    )
    entered = _enter(lib, _starter(library, make_char), "cloud_summit")
    grid = field_grid(lib, entered, lib.field_maps["cloud_summit"])
    cell = next(
        (gate.at[0] + dx, gate.at[1] + dy)
        for dx, dy in SIDES
        if grid.standable((gate.at[0] + dx, gate.at[1] + dy))
    )
    assert entered.field is not None
    char = entered.model_copy(
        update={"field": entered.field.model_copy(update={"x": cell[0], "y": cell[1]})}
    )
    with pytest.raises(WorldActionError) as excinfo:
        _step(lib, char, UseFieldObjectAction(object="summit_gate"))
    assert str(excinfo.value) == OBJECT_ZH
    view = field_view(lib, char, world=make_world(), now=NOON)
    assert view is not None
    shown = next(o for o in view.situation_objects if o.id == "summit_gate")
    assert not shown.usable and shown.problem_zh == OBJECT_ZH
    restored = _step(lib, _chosen(char), UseFieldObjectAction(object="summit_gate"))
    assert restored.char.pending_encounter is not None
    view = field_view(lib, _chosen(char), world=make_world(), now=NOON)
    assert view is not None
    assert next(o for o in view.situation_objects if o.id == "summit_gate").usable


# ---------------------------------------------------------------------------
# 任務：可以接；給招的步驟等正式選定
# ---------------------------------------------------------------------------


def test_quests_can_be_accepted(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _starter(library, make_char)
    for quest in (QUEST, "main_mist_rift"):
        result = _step(library, char, AcceptQuestAction(quest=quest))
        assert [e.quest for e in result.events if isinstance(e, QuestStartedEvent)] == [quest]
        char = result.char


def test_skill_reward_step_waits_for_formal_choice(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """主線第 2 步（給劇情技能，條件不用打）：入門期先不結算，選定後下一個動作就結算。"""
    char = _starter(library, make_char, location="mist_temple_gate")
    char = _with_quest(char, "main_mist_rift", steps_done=1)
    char = char.model_copy(update={"threads": (thread("temple_pass", "crane_envoy"),)})
    note = HintSeenAction(ids=("ob4",))
    held = _step(library, char, note)
    assert not any(isinstance(e, QuestStepDoneEvent) for e in held.events)
    state = held.char.quest_state("main_mist_rift")
    assert state is not None and state.steps_done == 1
    done = _step(library, _chosen(held.char), HintSeenAction(ids=("ob4b",)))
    assert [e.step for e in done.events if isinstance(e, QuestStepDoneEvent)] == ["enter_temple"]
    assert any(isinstance(e, StorySkillGrantedEvent) for e in done.events)


def test_steps_without_skill_rewards_still_complete(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _with_quest(_starter(library, make_char), "main_mist_rift")
    char = char.model_copy(update={"threads": (thread("missing_went_to_rift", "lantern_patrol"),)})
    done = _step(library, char, HintSeenAction(ids=("ob4",)))
    steps = [e.step for e in done.events if isinstance(e, QuestStepDoneEvent)]
    assert steps == ["missing_townsfolk"]


# ---------------------------------------------------------------------------
# 不開放的系統：入門期被擋且有原因，選定後不再被入門期擋
# ---------------------------------------------------------------------------

CLOSED: dict[str, tuple[WorldAction, str]] = {
    "hire": (HireAction(mercenaries=()), "入門期不能雇用傭兵，找葛蘭正式選定後開放"),
    "shadow_ai": (ShadowAiAction(profile=None), "入門期不能雇用傭兵，找葛蘭正式選定後開放"),
    "league_enter": (LeagueEnterAction(), "入門期不能參加聯賽，找葛蘭正式選定後開放"),
    "league_withdraw": (LeagueWithdrawAction(), "入門期不能參加聯賽，找葛蘭正式選定後開放"),
    "season_boss": (SeasonBossAction(), "入門期不能挑戰賽季 Boss，找葛蘭正式選定後開放"),
    "swear": (
        SwearOathAction(proposal=OathProposal(template="oath_no_retreat")),
        "入門期不能立誓，找葛蘭正式選定後開放",
    ),
    "release": (ReleaseOathAction(), "入門期不能立誓，找葛蘭正式選定後開放"),
    "loadout": (LoadoutAction(skills=()), "入門期不能換技能，找葛蘭正式選定後開放"),
}
USABLE_AT_ONCE = ("hire", "shadow_ai", "swear")
"""選定後在霧渡鎮直接做得成的（其餘的會被動作自己的條件擋：沒報名、賽季 Boss 沒開、沒有誓約…）。"""


@pytest.fixture(scope="module")
def chosen_char(content_library: ContentLibrary) -> CharacterState:
    """走完整流程正式選定的角色（打完兩步 → 在霧渡鎮選定 → 三選一都跳過）。"""
    library = without_fields(content_library)

    def make_char(**updates: object) -> CharacterState:
        char = new_character(library, "alice", hero(library), region=REGION)
        return char.model_copy(update=updates) if updates else char

    played = _fast_played(library, make_char, "melee")
    weapon, keywords = CHOICES["melee"]
    char = _step(library, played, OpeningConfirmAction(weapon=weapon, keywords=keywords)).char
    while char.pending_offers:
        char = _step(library, char, OfferPickAction(pick=None)).char
    return char


@pytest.mark.parametrize("name", sorted(CLOSED))
def test_closed_systems(
    library: ContentLibrary, make_char: MakeChar, chosen_char: CharacterState, name: str
) -> None:
    action, reason = CLOSED[name]
    with pytest.raises(WorldActionError) as excinfo:
        _step(library, _starter(library, make_char), action)
    assert str(excinfo.value) == reason
    assert chosen_char.opening is not None and chosen_char.opening.stage == "chosen"
    if name == "loadout":
        action = LoadoutAction(skills=chosen_char.hero.skills)
    try:
        _step(library, chosen_char, action)
    except WorldActionError as exc:
        assert "入門期" not in str(exc), str(exc)
        assert name not in (*USABLE_AT_ONCE, "loadout"), str(exc)


# ---------------------------------------------------------------------------
# 世界日誌重播：一條入門期流程
# ---------------------------------------------------------------------------


def test_starter_period_log_replays_identically(
    content_library: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    """選大類 → 夜裡走到石階巡邏旁邊（看不到、不開戰）→ 走到第 1 步固定戰旁邊（開戰）→ 打。"""
    lib = content_library
    base = make_char(mercenaries=PARTY)
    blank = pending_hero(library, base.hero.model_copy(update={"name_zh": "小靶"}))
    start = _with_quest(
        base.model_copy(update={"hero": blank, "generated_skills": (), "opening": new_opening(7)}),
        QUEST,
    )
    start = _enter(lib, start, "ferry_steps")
    world = make_world()
    patrol = next(e for e in field_enemies(lib, world, _old(start), NIGHT) if e.index == 1)
    start, walk = _beside(lib, start, patrol.xy)  # 起點＝夜間巡邏旁邊兩步
    char = start
    entries: list[WorldLogEntry] = []
    events: list[object] = []

    def run(action: WorldAction, now: int) -> StepResult:
        nonlocal char, world
        result = world_step(lib, world, char, action, now)
        char, world = result.char, result.world
        seq = len(entries) + 1
        entries.append(WorldLogEntry(seq=seq, now=now, character_id="alice", action=action))
        events.extend(result.events)
        return result

    run(OpeningClassAction(weapon_class="melee"), NIGHT)
    quiet = run(walk, NIGHT + 60)
    assert _contact(quiet) in (None, 0)  # 巡邏看不到、碰不到；最多被旁邊的第 1 步固定戰看到
    if quiet.char.pending_encounter is None:
        fixed = next(e for e in field_enemies(lib, world, char, NIGHT + 120) if e.index == 0)
        route = _path(lib, char, fixed.xy)[:-1]
        touched = run(WalkAction(path=route), NIGHT + 120)
        assert _contact(touched) == 0
    run(FightAction(steps=auto_steps(lib, char)), NIGHT + 180)
    assert any(isinstance(e, BattleEndedEvent) for e in events)
    assert char.opening is not None and char.opening.stage == "starter"

    first = replay(lib, make_world(), {"alice": start}, entries)
    second = replay(lib, make_world(), {"alice": start}, loads_log(dumps_log(entries)))
    assert dumps_char(first.characters["alice"]) == dumps_char(char)
    assert dumps_char(second.characters["alice"]) == dumps_char(char)
    assert first.events == second.events


# ---------------------------------------------------------------------------
# OB-4b：給招步驟的完成條件、入門期紮營
# ---------------------------------------------------------------------------


def test_skill_reward_steps_stay_reachable_after_choice(content_library: ContentLibrary) -> None:
    """全部任務：會給招的步驟，完成條件不能只靠當下發生一次的事件（入門期整步延後，選定後要還能
    達成）。「查出私通盜賊的人」另有線頭條件，算過。"""
    stuck: list[str] = []
    giving = 0
    for region, table in sorted(content_library.world_quests.quests.items()):
        for quest in table.quests:
            for step in quest.steps:
                giving += step.reward.offer is not None or step.reward.story_skill is not None
                stuck += [
                    f"{region}/{quest.id}/{step.id} when[{i}]"
                    for i in opening_limits.stuck_conditions(step)
                ]
    assert giving >= 9  # 現有內容：新手 3 步、雲嶺任務鏈 2 步、主線劇情技能 2 步、荒原任務鏈 2 步
    assert stuck == []
    traitor = content_library.world_quests.quest(REGION, "chain_temple_split")
    assert traitor is not None
    step = next(s for s in traitor.steps if s.id == "find_traitor")
    assert step.reward.offer is not None and step.has_event_condition()


def test_stuck_conditions_flags_event_only_steps(content_library: ContentLibrary) -> None:
    traitor = content_library.world_quests.quest(REGION, "chain_temple_split")
    assert traitor is not None
    step = next(s for s in traitor.steps if s.id == "find_traitor")
    any_of = step.when[0]
    assert isinstance(any_of, AnyOf)
    only_event = step.model_copy(update={"when": (any_of.conditions[0],)})
    assert opening_limits.stuck_conditions(only_event) == (0,)
    plain = step.model_copy(update={"reward": step.reward.model_copy(update={"offer": None})})
    assert opening_limits.stuck_conditions(plain.model_copy(update={"when": only_event.when})) == ()


def test_hidden_enemies_do_not_block_camping(
    content_library: ContentLibrary, library: ContentLibrary, make_char: MakeChar
) -> None:
    """雨中梯田（營地：要先清空才能紮營）：入門期那裡的敵人全都看不到，不擋紮營；選定後、舊角色
    照舊要先清空。渡口石階的第 1 步固定戰看得到，入門期照擋，打完那一步就不擋。"""
    lib = content_library
    world = make_world()
    starter = _with_quest(_starter(library, make_char), QUEST)
    terraces = _enter(lib, starter, "rain_terraces")
    assert camp_problem(lib, world, terraces, NOON) is None
    camped = _step(lib, terraces, CampAction())
    assert any(isinstance(e, CampedEvent) for e in camped.events)
    for other in (_chosen(terraces), _old(terraces)):
        problem = camp_problem(lib, world, other, NOON)
        assert problem is not None and "敵人還在" in problem
    ferry = _enter(lib, starter, "ferry_steps")
    problem = camp_problem(lib, world, ferry, NOON)
    assert problem is not None and "敵人還在" in problem
    with pytest.raises(WorldActionError, match="敵人還在"):
        _step(lib, ferry, CampAction())
    after = _enter(
        lib, _with_quest(_starter(library, make_char), QUEST, steps_done=1), "ferry_steps"
    )
    assert camp_problem(lib, world, after, NIGHT) is None
    # 沒有實地地圖的地點入門期不遇敵，也不擋
    assert (
        camp_problem(library, world, starter.model_copy(update={"location": "rain_terraces"}), NOON)
        is None
    )
