"""主題合併（R2）。

原 ``test_newcomer_6f2.py``：

開局在主城與第一次免費傳送（Phase 6F-2；09 9.6.9 #125、21 21.5）。

- 新角色在主城出生：主城實地地圖的 ``entry``（中央廣場）。
- 還沒到過新手區（``newcomer.yaml`` 的 ``start_region``）的小鎮：主城可以直接傳到那一區（區域傳送、
  傳送石都可以），不必先解鎖那邊的傳送石；到過之後照一般規則（#120）。
- 舊存檔（建角時就站在雲嶺小鎮）不受影響；重播一致。

原 ``test_newcomer_6f4.py``：

新手前 10 分鐘的數值與教學（Phase 6F-4；#128、#129、#130、#133，玩法 PM 筆記 C1～C3、6F-2b）。

- C2：新手鏈第 1 步完成剛好升到 2 級，第 2、3 步各升 1 級；升級畫面的文字。
- C3／#133：推薦配法（開局同屬性 4 點全給、不同 2／2；升級 2 點給比較低的、一樣高給第 1 招）。
- #133：升到 2 級、在霧渡鎮、有沒分配的點＝葛蘭先教配點，看過或略過之後才接第一次閃現。
- #128：新手任務的固定戰被敵人先看到＝沒有先手；從背後照樣我方先手；其他隊照一般規則。
- 6F-2b：提示紀錄記在角色身上（``hint_seen``、``hints_off``、``hints_reset``；三選一待選、
  戰鬥中也能記）；
  舊角色格式讀進來 ``level_seen`` 補成目前等級。
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world, with_rules
from tests.world.test_field_enemies import (
    GUARD,
    _char,
    _library,
    _seed_facing,
    _step,
    _steps_map,
    _visit,
    _walk,
)
from tests.world.test_quests import _with_quest, _won
from trpg.api.world_newcomer_view import hints_view, lesson_view, level_up_view
from trpg.content.fields import CAPITAL_LOCATION, CAPITAL_REGION, FieldSpawn
from trpg.content.library import ContentLibrary
from trpg.roguelite.start import (
    links_between,
    new_keyword_run,
    recommended_allocation,
    recommended_level_up,
    starting_skill,
)
from trpg.shared.types import Attribute
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import (
    HintSeenAction,
    HintsOffAction,
    HintsResetAction,
    TeleportAction,
    WorldAction,
)
from trpg.world.atlas import (
    can_teleport_to,
    free_first_teleport,
    region_state,
    unlocked_stones,
)
from trpg.world.battle import prepare_battle
from trpg.world.common import rules_of
from trpg.world.errors import WorldActionError
from trpg.world.field import placed
from trpg.world.field_actions import UseTeleportStoneAction
from trpg.world.field_enemies import newcomer_guarded
from trpg.world.growth import xp_to_level
from trpg.world.quests import advance_quests
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import WORLD_RULES_VERSION, dumps_char, dumps_log, loads_char, read_log
from trpg.world.state import CharacterState, FieldPos, PendingOffer, QuestState, WorldState
from trpg.world.step import new_character, world_step

# --- 原 test_newcomer_6f2.py ---

START = "cloud_ridge"


@pytest.fixture(scope="module")
def calm(field_library: ContentLibrary) -> ContentLibrary:
    lib = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    maps = {k: m.model_copy(update={"spawns": ()}) for k, m in lib.field_maps.items()}
    return dataclasses.replace(lib, field_maps=maps)


def _fresh(library: ContentLibrary) -> CharacterState:
    """6F-2 的新角色：在主城出生（API 的 ``spawn_region``）。"""
    return new_character(library, "alice", hero(library), region=CAPITAL_REGION)


def _old(library: ContentLibrary) -> CharacterState:
    """6F-2 以前建的角色：站在雲嶺小鎮出生，之後傳到主城。"""
    char = new_character(library, "alice", hero(library), region=START)
    result = world_step(
        library, make_world(), char, UseTeleportStoneAction(to="stone_capital"), NOON
    )
    assert result.char.region == CAPITAL_REGION
    return result.char


def _town_stone(library: ContentLibrary, region: str) -> str:
    world_map = library.location_map(region)
    assert world_map is not None
    town = library.outdoor_map(region, world_map.town)
    assert town is not None
    return town.teleport_stones[0].id


def test_newcomer_content(calm: ContentLibrary) -> None:
    newcomer = calm.world_newcomer
    assert newcomer is not None
    assert newcomer.start_region == START
    assert [line.speaker_zh for line in newcomer.opening] == ["說書人", "守印人"]
    assert "霧渡鎮" in newcomer.guide_capital_zh and "渡婆婆" in newcomer.guide_capital_zh
    assert WORLD_RULES_VERSION >= 8  # 6F-4 升到 9（新手保護 #128）


def test_new_character_spawns_in_capital_plaza(calm: ContentLibrary) -> None:
    char = placed(calm, _fresh(calm))
    assert (char.region, char.location) == (CAPITAL_REGION, CAPITAL_LOCATION)
    capital = calm.field_maps[CAPITAL_LOCATION]
    assert char.field == FieldPos(map=capital.id, x=capital.entry[0], y=capital.entry[1])
    # 中央廣場（11～20, 9～14；capital.yaml 開頭的說明）
    assert 11 <= capital.entry[0] <= 20 and 9 <= capital.entry[1] <= 14
    assert char.visited_towns == (CAPITAL_REGION,)
    assert START not in char.teleport_stones


def test_free_first_teleport_by_region(calm: ContentLibrary) -> None:
    char = _fresh(calm)
    assert free_first_teleport(calm, char, START)
    assert can_teleport_to(calm, char, START)
    assert region_state(calm, make_world(), char, START).status == "open"
    result = world_step(calm, make_world(), char, TeleportAction(region=START), NOON)
    world_map = calm.location_map(START)
    assert world_map is not None
    assert (result.char.region, result.char.location) == (START, world_map.town)
    assert START in result.char.visited_towns
    assert not free_first_teleport(calm, result.char, START)  # 到過了


def test_free_first_teleport_by_stone(calm: ContentLibrary) -> None:
    char = _fresh(calm)
    stone = _town_stone(calm, START)
    assert stone in unlocked_stones(calm, char)
    assert stone not in char.teleport_stones  # 不寫進存檔，只是第一次免費
    result = world_step(calm, make_world(), char, UseTeleportStoneAction(to=stone), NOON)
    assert result.char.region == START
    assert START in result.char.visited_towns


def test_free_teleport_only_to_start_region(calm: ContentLibrary) -> None:
    char = _fresh(calm)
    assert not free_first_teleport(calm, char, "ashen_waste")
    with pytest.raises(WorldActionError):
        world_step(calm, make_world(), char, TeleportAction(region="ashen_waste"), NOON)


def test_after_visiting_normal_rules(calm: ContentLibrary) -> None:
    """到過霧渡鎮、沒有站上那邊的傳送石：回到主城後，那顆傳送石照一般規則還沒解鎖。"""
    world = make_world()
    char = _fresh(calm)
    there = world_step(calm, world, char, TeleportAction(region=START), NOON).char
    back = world_step(calm, world, there, TeleportAction(region=CAPITAL_REGION), NOON + 60).char
    stone = _town_stone(calm, START)
    assert stone not in back.teleport_stones
    assert stone not in unlocked_stones(calm, back)
    with pytest.raises(WorldActionError, match="還沒走到過傳送石"):
        world_step(calm, world, back, UseTeleportStoneAction(to=stone), NOON + 120)
    # 區域傳送照一般規則：亮起的區可以去
    again = world_step(calm, world, back, TeleportAction(region=START), NOON + 180).char
    assert again.region == START


def test_old_character_unaffected(calm: ContentLibrary) -> None:
    char = _old(calm)
    assert START in char.visited_towns
    assert not free_first_teleport(calm, char, START)
    assert _town_stone(calm, START) not in unlocked_stones(calm, char)
    assert loads_char(dumps_char(char)) == char


def test_without_newcomer_content_no_free_teleport(calm: ContentLibrary) -> None:
    lib = dataclasses.replace(calm, world_newcomer=None)
    char = _fresh(lib)
    assert not free_first_teleport(lib, char, START)
    with pytest.raises(WorldActionError):
        world_step(lib, make_world(), char, TeleportAction(region=START), NOON)


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


@pytest.mark.parametrize("first", ["region", "stone"])
def test_free_teleport_replays(calm: ContentLibrary, first: str) -> None:
    world = make_world()
    start = _fresh(calm)
    go: WorldAction = (
        TeleportAction(region=START)
        if first == "region"
        else UseTeleportStoneAction(to=_town_stone(calm, START))
    )
    actions: list[WorldAction] = [
        go,
        TeleportAction(region=CAPITAL_REGION),
        TeleportAction(region=START),
    ]
    end_world, live, entries = _play(calm, world, start, actions)
    log = read_log(dumps_log(entries))
    one = replay(calm, world, {"alice": start}, log.entries)
    two = replay(calm, world, {"alice": start}, log.entries)
    assert one.characters["alice"] == live == two.characters["alice"]
    assert one.world == end_world == two.world
    assert live.region == START


# --- 原 test_newcomer_6f4.py ---

MakeChar = Callable[..., CharacterState]
INT, STR, DEX = Attribute.INT, Attribute.STR, Attribute.DEX


def _do(library: ContentLibrary, char: CharacterState, action: WorldAction) -> CharacterState:
    return world_step(library, make_world(), char, action, NOON).char


# ---------------------------------------------------------------------------
# C2：等級
# ---------------------------------------------------------------------------


def test_xp_to_level(library: ContentLibrary, make_char: MakeChar) -> None:
    thresholds = rules_of(library).hero_growth.level_thresholds
    char = make_char()
    assert xp_to_level(library, char, 2) == thresholds[0]
    assert xp_to_level(library, char.model_copy(update={"xp": thresholds[0]}), 2) == 0
    assert xp_to_level(library, char, 1) == 0
    assert xp_to_level(library, char, 999) == 0


def test_level_up_text(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert level_up_view(library, char) is None
    up = level_up_view(library, char.model_copy(update={"level": 2}))
    assert up is not None and up.level == 2
    # 靈感照規則（world/rules.yaml insight_per_level＝2；玩法 PM 稿寫「+1」，列在報告的待 PM 決定）
    insight = rules_of(library).hero_growth.insight_per_level
    assert up.text_zh == (
        f"升到 2 級：屬性點 +2、靈感 +{insight}。回霧渡鎮找導師堂的葛蘭，學怎麼配點。"
    )
    taught = char.model_copy(
        update={"level": 3, "level_seen": 2, "hints_seen": ("lesson:allocate",)}
    )
    later = level_up_view(library, taught)
    assert later is not None and later.text_zh == f"升到 3 級：屬性點 +2、靈感 +{insight}。"
    seen = _do(library, char.model_copy(update={"level": 2}), HintSeenAction(level=2))
    assert seen.level_seen == 2 and level_up_view(library, seen) is None
    capped = _do(library, char, HintSeenAction(level=5))
    assert capped.level_seen == 1  # 不超過目前等級


# ---------------------------------------------------------------------------
# C3／#133：推薦配法
# ---------------------------------------------------------------------------


def _skill(library: ContentLibrary, attr: Attribute) -> Any:
    return next(
        s for s in library.skills.values() if s.category != "weapon" and s.scaling_attr == attr
    )


def test_recommended_allocation(library: ContentLibrary) -> None:
    staff = library.weapons["fire_staff"]
    fire, blade = _skill(library, INT), _skill(library, STR)
    assert recommended_allocation([fire, fire], staff, 4) == {INT: 4}
    assert recommended_allocation([fire, blade], staff, 4) == {INT: 2, STR: 2}
    assert recommended_allocation([blade, fire], staff, 3) == {STR: 2, INT: 1}  # 奇數多給第 1 招
    assert recommended_allocation([], staff, 4) == {INT: 4}


def test_recommended_level_up_goes_to_the_lower(library: ContentLibrary) -> None:
    staff = library.weapons["fire_staff"]
    fire, blade = _skill(library, INT), _skill(library, STR)
    # 07 7.2 的範例：智力 12、力量 12 → 升級 2 點給第 1 招的智力 → 智力 14、力量 12
    assert recommended_level_up([fire, blade], staff, {INT: 12, STR: 12}, 2) == {INT: 2}
    assert recommended_level_up([fire, blade], staff, {INT: 14, STR: 12}, 2) == {STR: 2}
    assert recommended_level_up([fire, fire], staff, {INT: 14}, 2) == {INT: 2}


def test_world_start_uses_recommended(library: ContentLibrary) -> None:
    run = new_keyword_run(library, "dagger", ["frozen", "concealed"], 1000, "recommended")
    base = {a: 10 for a in Attribute}
    spent = {a: v - base[a] for a, v in run.hero.attributes.items() if v != base[a]}
    assert sum(spent.values()) == library.roguelite.start_free_points
    assert all(v in (2, 4) for v in spent.values())  # 同屬性 4、不同各 2


# ---------------------------------------------------------------------------
# #129：第 2 招優先利用第 1 個關鍵字
# ---------------------------------------------------------------------------


def test_second_starter_prefers_using_the_first_keyword(library: ContentLibrary) -> None:
    """有「利用第 1 個關鍵字」的招時優先給它（雷法杖：潮濕 → 涉水雷擊利用潮濕）。6F-4b 起火焰法杖
    點燃＋帶電也有：組合器自動生成的利用者白板（例：趁燃雷擊）。6F-4c 起巨劍倒地＋撞擊也有：手寫池的
    「利用倒地的撞擊招」（踢翻、拖地摔）。"""
    linked = 0
    for seed in range(6):
        first = starting_skill(library, "lightning_staff", "wet", seed)
        assert first is not None
        second = starting_skill(
            library, "lightning_staff", "charged", seed, taken=[first.id], prefer_uses="wet"
        )
        assert second is not None
        linked += bool(links_between(library, first, second))
        again = starting_skill(
            library, "lightning_staff", "charged", seed, taken=[first.id], prefer_uses="wet"
        )
        assert again == second  # 確定性
        fire = starting_skill(library, "fire_staff", "ignite", seed)
        assert fire is not None
        prefer = starting_skill(
            library, "fire_staff", "charged", seed, taken=[fire.id], prefer_uses="ignite"
        )
        assert prefer is not None and links_between(library, fire, prefer)  # 6F-4b
        sword = starting_skill(library, "greatsword", "prone", seed)
        assert sword is not None
        uses_prone = starting_skill(
            library, "greatsword", "collision", seed, taken=[sword.id], prefer_uses="prone"
        )
        assert uses_prone is not None  # 6F-4c：手寫池補了利用倒地的撞擊招
        assert uses_prone.id in {"skill_prone_kick", "skill_prone_drag"}
    assert linked >= 1


# ---------------------------------------------------------------------------
# #133：葛蘭先教配點，再教閃現
# ---------------------------------------------------------------------------


def _back_in_town_at_2(char: CharacterState) -> CharacterState:
    quest = QuestState(quest="starter_ferry", steps_done=1, started_at=NOON)
    flash = {"skill_war_hymn": acquire("skill_war_hymn").model_copy(update={"used": True})}
    return char.model_copy(
        update={
            "quests": (quest,),
            "flash": flash,
            "insight": 1,
            "level": 2,
            "attribute_points": 2,
            "location": "mist_ferry",
        }
    )


def test_allocate_lesson_before_flash(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _back_in_town_at_2(make_char())
    lesson = lesson_view(library, char)
    assert lesson is not None and lesson.kind == "allocate"
    assert [line.speaker_zh for line in lesson.lines] == ["葛蘭", "葛蘭"]
    assert lesson.lines[0].text_zh == "升級了？身上多了兩點力氣。來，我示範怎麼分。"
    assert lesson.points == 2
    assert lesson.start_points == library.roguelite.start_free_points  # 6F-4b：從規則讀
    assert sum(lesson.recommended.values()) == 2
    assert lesson.done_zh == "好。接下來看看你剛才用過的那一招。"
    assert lesson.skip_zh == "隨時回來找我。"
    assert {n.attr for n in lesson.notes} == set(Attribute)
    elsewhere = char.model_copy(update={"location": "mist_temple_gate"})
    away = lesson_view(library, elsewhere)  # 葛蘭在霧渡鎮：別的地方不教配點
    assert away is None or away.kind != "allocate"
    # 略過（記下看過）或配完（沒有點了）之後接第一次閃現
    skipped = _do(library, char, HintSeenAction(ids=("lesson:allocate",)))
    after = lesson_view(library, skipped)
    assert after is not None and after.kind == "flash"
    allocated = char.model_copy(update={"attribute_points": 0})
    flash = lesson_view(library, allocated)
    assert flash is not None and flash.kind == "flash"
    done = _do(library, skipped, HintSeenAction(ids=("lesson:flash",)))
    assert lesson_view(library, done) is None


# ---------------------------------------------------------------------------
# 6F-2b：提示紀錄記在角色身上
# ---------------------------------------------------------------------------


def test_hint_records_on_character(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    seen = _do(library, char, HintSeenAction(ids=("move_attack", "opening")))
    assert seen.hints_seen == ("move_attack", "opening")
    twice = _do(library, seen, HintSeenAction(ids=("move_attack",)))
    assert twice == seen  # 沒有變化
    off = _do(library, seen, HintsOffAction())
    assert off.hints_off and hints_view(off).off
    reset = _do(library, off, HintsResetAction())
    assert reset.hints_seen == () and not reset.hints_off
    assert loads_char(dumps_char(off)) == off


def test_hint_actions_allowed_while_offer_pending(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    fresh = _with_quest(make_char("bob", location="ferry_steps"), "starter_ferry")
    won = _won("ferry_steps", group="bandit_raiders")  # 6F-4b：只算打贏固定戰
    pending, _ = advance_quests(library, make_world(), fresh, won, NOON)
    assert pending.pending_offers and isinstance(pending.pending_offers[0], PendingOffer)
    noted = _do(library, pending, HintSeenAction(ids=("move_attack",)))
    assert noted.hints_seen == ("move_attack",)
    assert noted.pending_offers == pending.pending_offers  # 只記紀錄，三選一照樣待選


def test_old_char_format_fills_level_seen(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char().model_copy(update={"level": 3})
    data = json.loads(dumps_char(char))
    data["format"] = "trpg-char/6"
    for key in ("level_seen", "hints_seen", "hints_off"):
        data.pop(key, None)
    old = loads_char(json.dumps(data))
    assert old.format == "trpg-char/15" and old.level_seen == 3
    assert level_up_view(library, old) is None  # 舊角色不跳舊的升級畫面


# ---------------------------------------------------------------------------
# #128：新手保護
# ---------------------------------------------------------------------------

STARTER_GUARD = {
    **GUARD,
    "personal": True,
    "until_quest": "starter_ferry",
    "until_step": "ferry_bandits",
}


@pytest.fixture(scope="module")
def starter_lib(field_library: ContentLibrary) -> ContentLibrary:
    return _library(field_library, _steps_map([STARTER_GUARD]))


def test_newcomer_guarded_only_for_starter_spawns(starter_lib: ContentLibrary) -> None:
    assert newcomer_guarded(starter_lib, "cloud_ridge", FieldSpawn.model_validate(STARTER_GUARD))
    assert not newcomer_guarded(starter_lib, "cloud_ridge", FieldSpawn.model_validate(GUARD))
    chain = {**GUARD, "until_quest": "chain_temple_split"}
    assert not newcomer_guarded(starter_lib, "cloud_ridge", FieldSpawn.model_validate(chain))


def _with_starter(char: CharacterState) -> CharacterState:
    return char.model_copy(update={"quests": (QuestState(quest="starter_ferry", started_at=NOON),)})


def test_starter_fight_seen_first_has_no_first_strike(starter_lib: ContentLibrary) -> None:
    seed = _seed_facing(STARTER_GUARD, "w")
    char = _with_starter(_char(starter_lib, (1, 6), field_visit=_visit(seed)))
    char, _ = _step(starter_lib, char, _walk((2, 6), (3, 6), (4, 6), (5, 6)))
    encounter = char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.group == "bandit_raiders"
    assert encounter.contact.first is None  # 被看到：沒有先手（一般規則是敵方先手）
    assert prepare_battle(starter_lib, char).first_team is None


def test_starter_fight_from_behind_is_still_ours(starter_lib: ContentLibrary) -> None:
    seed = _seed_facing(STARTER_GUARD, "e")
    char = _with_starter(_char(starter_lib, (1, 6), field_visit=_visit(seed)))
    char, _ = _step(starter_lib, char, _walk((2, 6), (3, 6), (4, 6), (5, 6), (5, 7)))
    encounter = char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.first == "ally"


# ---------------------------------------------------------------------------
# 6F-4b：新手三步只算打贏固定戰（#99 每場教一件事）
# ---------------------------------------------------------------------------


def test_starter_steps_count_only_the_fixed_fights(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    quest = next(
        q for q in library.world_quests.quests["cloud_ridge"].quests if q.id == "starter_ferry"
    )
    expected = {
        "ferry_steps": "bandit_raiders",
        "bamboo_path": "mist_wolf_pack",
        "rain_terraces": "terrace_clash",
    }
    for step in quest.steps:
        wins = [c for c in step.when if getattr(c, "kind", None) == "win_battle"]
        assert len(wins) == 1
        location, group = wins[0].location, wins[0].group  # type: ignore[union-attr]
        assert location is not None and group == expected[location]
    fresh = _with_quest(make_char("cat", location="ferry_steps"), "starter_ferry")
    patrol, _ = advance_quests(library, make_world(), fresh, _won("ferry_steps", group="g"), NOON)
    assert patrol.quests == fresh.quests  # 打贏巡邏不算
    fixed = _won("ferry_steps", group="bandit_raiders")
    done, _ = advance_quests(library, make_world(), fresh, fixed, NOON)
    assert done.quests != fresh.quests
