"""OB-5（#150 前端）後端補的畫面資料：選大類與正式選定的台詞、頭像、地名；教學「選定」、任務指引、
升級畫面；入門期不開放的系統在面板資料上先標成不可用，原因和送出動作被拒的是同一句。

只驗畫面資料（``trpg.api`` 的 view）；規則本身在 ``tests/world/test_opening_*.py``。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.world.helpers import NOON, hero, make_world
from tests.world.test_gear import _item
from tests.world.test_opening_choice import QUEST, _confirm, _fast_played
from tests.world.test_opening_stages import _pending, _starter
from tests.world.test_quests import _with_quest
from trpg.api.league_view import league_view
from trpg.api.season_boss_view import season_boss_block
from trpg.api.world_newcomer_view import battle_hints, guide_view, lesson_view, level_up_view
from trpg.api.world_presenter import world_view
from trpg.api.world_range import range_view
from trpg.content.library import ContentLibrary
from trpg.world import opening_choice
from trpg.world import opening_limits as limits_module
from trpg.world.actions import ChangeRaceAction, FlashAction, HireAction, LoadoutAction
from trpg.world.economy_actions import EquipAction
from trpg.world.errors import WorldActionError
from trpg.world.opening import opening_limits, range_content
from trpg.world.state import CharacterState
from trpg.world.step import new_character, world_step

type MakeChar = Callable[..., CharacterState]

LIMIT_KEYS = {
    "race",
    "flash",
    "loadout",
    "hire",
    "league",
    "season_boss",
    "oath",
    "main_hand",
    "smith",
    "dissolve",
}


@pytest.fixture
def library(content_library: ContentLibrary) -> ContentLibrary:
    return content_library


@pytest.fixture
def make_char(library: ContentLibrary) -> MakeChar:
    def factory(character_id: str = "alice", **updates: object) -> CharacterState:
        char = new_character(library, character_id, hero(library), region="cloud_ridge")
        return char.model_copy(update=updates) if updates else char

    return factory


def _refused(library: ContentLibrary, char: CharacterState, action: object) -> str:
    with pytest.raises(WorldActionError) as excinfo:
        world_step(library, make_world(), char, action, NOON)  # type: ignore[arg-type]
    return str(excinfo.value)


# ---------------------------------------------------------------------------
# 收尾：STARTER_STEPS 只有一份
# ---------------------------------------------------------------------------


def test_starter_steps_has_a_single_definition() -> None:
    """``opening_choice`` 從 ``opening_limits`` 匯入（不各寫一份）。"""
    source = Path(opening_choice.__file__).read_text(encoding="utf-8")
    assert "from trpg.world.opening_limits import STARTER_STEPS" in source
    assert "STARTER_STEPS: Final" not in source
    assert opening_choice.STARTER_STEPS == limits_module.STARTER_STEPS


# ---------------------------------------------------------------------------
# 選大類
# ---------------------------------------------------------------------------


def test_pick_class_view_has_keeper_lines_and_blurbs(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    arena = range_content(library)
    view = range_view(library, _pending(library, make_char))
    assert view is not None and view.stage == "pick_class" and view.choice is None
    # 守印人的頭像：主城實地地圖的情境物件；地名讀內容檔（不寫死「主城」）
    assert view.keeper is not None and view.keeper.name_zh == "守印人"
    assert view.keeper.portrait is not None and view.keeper.region == "capital"
    capital = library.outdoor_map("capital", "capital")
    assert capital is not None and view.capital_zh == capital.name_zh != ""
    assert [x.text_zh for x in view.intro] == [x.text_zh for x in arena.intro]
    assert [x.text_zh for x in view.loan] == [x.text_zh for x in arena.loan] != []
    # 每招入門招各一句白話（玩法 PM 定稿「六招各一句」），鍵就是那一類的示範招
    for rack in view.racks:
        assert (
            set(rack.blurbs_zh)
            == {s.id for s in rack.skills}
            == set(arena.demos[rack.weapon_class])
        )
        assert all(rack.blurbs_zh.values())


def test_range_lines_follow_the_final_script(library: ContentLibrary) -> None:
    """定稿（台詞-150與147）：先挑一條路；確定出發後「先走這條路試試」。"""
    arena = range_content(library)
    assert arena.intro[1].text_zh.endswith("先挑一條路。")
    assert arena.done[0].text_zh.startswith("好，先走這條路試試。")
    assert [x.speaker_zh for x in arena.choose] == ["葛蘭", "葛蘭"]
    assert [x.speaker_zh for x in arena.choose_capital] == ["守印人"]
    capital = library.outdoor_map("capital", "capital")
    assert capital is not None
    spots = {s.id for s in capital.situation_objects}
    assert arena.keeper_object in spots and set(arena.choose_objects) <= spots


# ---------------------------------------------------------------------------
# 正式選定的入口：可否選定與原因、教學「選定」、任務指引、升級畫面
# ---------------------------------------------------------------------------


def test_choice_view_before_and_after_two_steps(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    fresh = _starter(library, make_char).model_copy(update={"location": "mist_ferry"})
    before = range_view(library, fresh)
    assert before is not None and before.choice is not None
    assert not before.choice.available and before.choice.blocked_zh
    assert lesson_view(library, fresh) is None
    guide = guide_view(library, fresh)
    assert guide is None or guide.text_zh != "回霧渡鎮導師堂找葛蘭"

    played = _fast_played(library, make_char)
    view = range_view(library, played)
    assert view is not None and view.choice is not None
    choice = view.choice
    assert choice.available and choice.blocked_zh is None and not choice.in_capital
    assert choice.place_zh == "霧渡鎮導師堂" and choice.npc == "gran"
    assert choice.speaker is not None and choice.speaker.name_zh == "葛蘭"
    assert choice.speaker.portrait is not None and choice.speaker.region == "cloud_ridge"
    assert [x.speaker_zh for x in choice.lines] == ["葛蘭", "葛蘭"] and len(choice.done) == 1
    lesson = lesson_view(library, played)
    assert lesson is not None and lesson.kind == "choose"
    assert [x.text_zh for x in lesson.lines] == [x.text_zh for x in choice.lines]
    guide = guide_view(library, played)
    assert guide is not None and guide.text_zh == "回霧渡鎮導師堂找葛蘭"


def test_choice_view_in_the_capital_uses_the_keeper_and_the_capital_name(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    played = _fast_played(library, make_char).model_copy(
        update={"region": "capital", "location": "capital"}
    )
    view = range_view(library, played)
    assert view is not None and view.choice is not None
    choice = view.choice
    assert choice.available and choice.in_capital
    assert choice.place_zh == f"{view.capital_zh}工坊靶場" and "主城" not in choice.place_zh
    assert choice.speaker is not None and choice.speaker.name_zh == "守印人"
    assert [x.speaker_zh for x in choice.lines] == ["守印人"]
    # OB-5b（玩法 PM 定稿）：在主城選定完成由守印人說一句
    assert [(x.speaker_zh, x.text_zh) for x in choice.done] == [
        ("守印人", "挑好了。借你的那套我收走，渡口和竹林欠你的，現在一起補上。")
    ]
    assert set(choice.objects) == {"training_range", "workshop_master"}
    lesson = lesson_view(library, played)
    assert lesson is not None and lesson.kind == "choose"


def test_choose_lesson_stops_after_the_formal_choice(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    played = _fast_played(library, make_char, "ranged")
    chosen = world_step(library, make_world(), played, _confirm("ranged"), NOON).char
    assert chosen.opening is not None and chosen.opening.stage == "chosen"
    view = range_view(library, chosen)
    assert view is not None and view.choice is None
    lesson = lesson_view(library, chosen)
    assert lesson is None or lesson.kind != "choose"
    guide = guide_view(library, chosen)
    assert guide is None or guide.text_zh != "回霧渡鎮導師堂找葛蘭"


def test_starter_level_up_texts(library: ContentLibrary, make_char: MakeChar) -> None:
    """入門期的升級畫面（定稿）：2 級＝屬性點已自動配好；打完前兩步＝回葛蘭那裡選定。"""
    starter = _starter(library, make_char).model_copy(update={"level": 2})
    up = level_up_view(library, starter)
    assert up is not None and up.text_zh.startswith("升到 2 級：屬性點已照入門招配好，靈感 +")
    played = _fast_played(library, make_char).model_copy(update={"level_seen": 2})
    assert played.level == 3
    up = level_up_view(library, played)
    assert up is not None
    assert up.text_zh.startswith("升到 3 級：靈感 +")
    assert up.text_zh.endswith("回霧渡鎮導師堂找葛蘭，選你自己的武器與關鍵字。")
    # 舊角色（已完成開局）照舊
    old = make_char().model_copy(update={"level": 2})
    up = level_up_view(library, old)
    assert up is not None and "屬性點 +" in up.text_zh


def test_bamboo_hints_get_a_note_in_the_starter_period(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """竹林那兩句提示（水＋雷、冰凍）入門期放不出來：句尾加一句（定稿「沿用與小改」）。"""
    newcomer = library.world_newcomer
    assert newcomer is not None
    noted, note = set(newcomer.starter_teach_hints), newcomer.starter_teach_note_zh
    assert noted and note == "（選關鍵字時可以自己試試）"

    def at_bamboo(char: CharacterState) -> dict[str, str]:
        there = _with_quest(char, QUEST, steps_done=1).model_copy(
            update={"location": "bamboo_path"}
        )
        return {h.id: h.text_zh for h in battle_hints(library, there)}

    starter = at_bamboo(_starter(library, make_char))
    assert noted <= set(starter)
    for hint_id, text in starter.items():
        assert text.endswith(note) == (hint_id in noted)
    old = at_bamboo(make_char())
    assert noted <= set(old) and not any(text.endswith(note) for text in old.values())


# ---------------------------------------------------------------------------
# 入門期的限制：面板資料先標成不可用，原因同動作被拒的那一句
# ---------------------------------------------------------------------------


def test_limits_by_stage(library: ContentLibrary, make_char: MakeChar) -> None:
    assert opening_limits(make_char()) == {}  # 舊角色
    assert opening_limits(_pending(library, make_char)) == {}  # 選大類中：整頁是靶場
    starter = _starter(library, make_char)
    assert set(opening_limits(starter)) == LIMIT_KEYS
    chosen = world_step(
        library, make_world(), _fast_played(library, make_char, "ranged"), _confirm("ranged"), NOON
    ).char
    assert set(opening_limits(chosen)) == {"flash", "dissolve"}
    assert opening_limits(chosen.model_copy(update={"level": 4})).keys() == {"dissolve"}


def test_limit_reasons_match_the_gate(library: ContentLibrary, make_char: MakeChar) -> None:
    """畫面標的原因＝送出動作被拒的原因（同一張表）；定稿的三句逐字相同。"""
    sword = _item(library, "weapon")
    starter = _starter(library, make_char, gear=(sword,))
    limits = opening_limits(starter)
    assert limits["main_hand"] == "入門期不能換主手，找葛蘭選定武器後就能換"
    assert limits["flash"] == "到 4 級才能閃現"
    assert limits["race"] == "正式選定武器與關鍵字之前不能換種族"
    assert _refused(library, starter, ChangeRaceAction(race="elf")) == limits["race"]
    assert _refused(library, starter, FlashAction(skill=starter.hero.skills[0])) == limits["flash"]
    assert _refused(library, starter, LoadoutAction(skills=())) == limits["loadout"]
    assert _refused(library, starter, HireAction(mercenaries=())) == limits["hire"]
    assert _refused(library, starter, EquipAction(item=sword.id)) == limits["main_hand"]


def test_panels_are_marked_unavailable_in_the_starter_period(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    sword, helm = _item(library, "weapon"), _item(library, "head")
    starter = _starter(library, make_char, gear=(sword, helm)).model_copy(
        update={"location": "mist_ferry"}
    )
    world = make_world()
    limits = opening_limits(starter)
    view = world_view(library, world, starter, NOON)
    assert view.limits == limits
    # 背包：武器不能換上（原因＝換主手那一句）；防具照常
    assert view.inventory is not None
    rows = {row.item: row for row in view.inventory.bag if row.gear}
    assert not rows[sword.id].can_equip and rows[sword.id].equip_problem_zh == limits["main_hand"]
    assert rows[helm.id].equip_problem_zh != limits["main_hand"]
    # 換技能、雇傭兵、誓約、每一招的閃現
    assert not view.here.can_loadout
    assert view.party is not None and not view.party.can_hire
    assert view.party.hire_problem_zh == "入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵"
    assert view.oath is not None and not view.oath.can_swear
    assert view.oath.swear_problem_zh == limits["oath"]
    assert view.hero.flash and all(
        not f.can_flash and f.flash_problem_zh == limits["flash"] for f in view.hero.flash
    )
    assert not view.growth.can_flash and view.growth.flash_blocked_zh == limits["flash"]
    # 聯賽、賽季 Boss（各自的端點）
    league = league_view(library, world, starter, None, NOON, account="alice")
    assert not league.can_enter
    boss = season_boss_block(library, world, starter, NOON, actor="alice")
    assert boss is None or (not boss.can_challenge and boss.problem_zh == limits["season_boss"])


def test_old_characters_panels_are_untouched(library: ContentLibrary, make_char: MakeChar) -> None:
    sword = _item(library, "weapon")
    old = make_char(gear=(sword,)).model_copy(update={"location": "mist_ferry"})
    view = world_view(library, make_world(), old, NOON)
    assert view.limits == {} and view.opening is None
    assert view.inventory is not None
    row = next(r for r in view.inventory.bag if r.item == sword.id)
    assert row.equip_problem_zh is None or "入門期" not in row.equip_problem_zh
    assert view.here.can_loadout
