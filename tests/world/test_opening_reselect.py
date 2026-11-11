"""#150 開局先玩再定的第 3 段：4 級前的免費重選（Phase OB-3；21 21.5 第 5、9 點、
:mod:`trpg.world.opening_reselect`）。

一律跑真的世界動作：正式選定 → 選完兩組三選一 → 重選到另一個大類（武器、招、點數、HP、法力；舊的
起始招與三選一招連同紀錄全部收回；重新出題）→ 只能一次、4 級後被擋。邊界：起始武器已賣、已強化、
背包滿、雙手武器與副手。入門招、起始招一律從資料與開局種子推，不寫死技能 ID。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import make_encounter, make_world
from tests.world.test_gear import _item
from tests.world.test_opening_choice import (
    CHOICES,
    QUEST,
    _confirm,
    _fast_played,
    _played,
    _step,
)
from tests.world.test_opening_stages import _pending, _starter
from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary
from trpg.roguelite.start import apply_allocation, new_keyword_run, pick_starters, start_hero
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.usage import SkillUsage
from trpg.world.actions import (
    OfferPickAction,
    OpeningConfirmAction,
    OpeningReselectAction,
    OpeningReselectedEvent,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    WorldAction,
)
from trpg.world.common import max_hp, max_mana
from trpg.world.economy_actions import EquipAction
from trpg.world.errors import WorldActionError
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.opening_choice import full_allocation
from trpg.world.opening_reselect import (
    reselect_losses,
    reselect_problem,
    reselect_returns,
    starter_item_id,
    starter_weapon_held,
)
from trpg.world.quests import quest_home
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState, GearMod

type MakeChar = Callable[..., CharacterState]

RESELECT = {
    # 入門大類 → 重選的武器與關鍵字（和入門大類、正式選定的大類都不同：基礎值要再重建一次）
    "melee": ("bow", ("ignite", "frozen")),
    "ranged": ("fire_staff", ("ignite", "charged")),
    "focus": ("greatsword", ("prone", "ignite")),
}


def _again(cls: str) -> OpeningReselectAction:
    weapon, keywords = RESELECT[cls]
    return OpeningReselectAction(weapon=weapon, keywords=keywords)


def _chosen(
    library: ContentLibrary,
    make_char: MakeChar,
    cls: str = "melee",
    *,
    real: bool = False,
    confirm: WorldAction | None = None,
    **updates: object,
) -> CharacterState:
    """正式選定、兩組三選一都選完、人在霧渡鎮（``real``：第 1、2 步真的打；``confirm``：不照
    ``CHOICES`` 選時的正式選定）。"""
    world = make_world()
    play = _played if real else _fast_played
    action = _confirm(cls) if confirm is None else confirm
    char = _step(library, play(library, make_char, cls, **updates), action, world).char
    for _ in range(2):
        char = _step(library, char, OfferPickAction(pick=0), world).char
    assert char.opening is not None and len(char.opening.granted_skills) == 4
    assert char.pending_offers == ()
    return char


def _with_records(char: CharacterState) -> CharacterState:
    """替重選要收回的招補上用法與閃現的紀錄（正式選定後真的用過、學完整技能時會有）。"""
    assert char.opening is not None
    granted = char.opening.granted_skills
    usage = {**char.skill_usage, **{s: SkillUsage(uses=2) for s in granted}}
    flash = {**char.flash, granted[0]: acquire(granted[0], complete=True)}
    return char.model_copy(
        update={
            "skill_usage": dict(sorted(usage.items())),
            "flash": dict(sorted(flash.items())),
        }
    )


# ---------------------------------------------------------------------------
# 表格：三大類 × 正式選定 → 重選到另一個大類
# ---------------------------------------------------------------------------


def _check_returned(before: CharacterState, char: CharacterState, given: tuple[str, ...]) -> None:
    """舊的起始 2 招與三選一招全部收回，紀錄都不在了；其他來源的招留著。"""
    assert before.opening is not None
    old = before.opening.granted_skills
    gone = set(old) - set(given)
    assert len(old) == 4 and gone
    for skill in gone:
        assert skill not in char.hero.skills and skill not in char.bench
        assert skill not in {s.id for s in char.generated_skills}
    for skill in old:  # 新的起始技能剛好和舊招同一招時，那一招是新給的、紀錄是空的
        assert skill not in char.flash and skill not in char.skill_usage
        assert skill not in char.skill_regions
        assert skill not in {s.id for s in char.flash_bases}
    others = [s for s in before.hero.skills if s not in old]
    assert [s for s in char.hero.skills if s not in given] == others


def _check_numbers(
    library: ContentLibrary, before: CharacterState, char: CharacterState, cls: str
) -> None:
    """基礎值照新大類重建、8 點全部重配並記在 ``attribute_spent``、HP 與法力回滿。"""
    assert before.opening is not None
    weapon, keywords = RESELECT[cls]
    rules = library.roguelite
    picked = pick_starters(library, weapon, keywords, before.opening.seed)
    points = rules.start_free_points + 2 * rules.attribute_points_per_level
    assert sum(before.attribute_spent.values()) == points == 8
    allocation = full_allocation(library, picked, library.weapons[weapon], points)
    expected = apply_allocation(start_hero(library, weapon, char.hero.skills), allocation)
    expected = expected.model_copy(
        update={
            "name_zh": before.hero.name_zh,
            "race": before.hero.race,
            "doll": before.hero.doll,
        }
    )
    assert char.hero == expected
    assert char.attribute_points == 0 and dict(char.attribute_spent) == allocation
    assert (char.level, char.xp, char.insight) == (before.level, before.xp, before.insight)
    assert char.hp == max_hp(library, char) and char.mana == max_mana(library, char)
    assert char.gold == before.gold


@pytest.mark.parametrize("cls", sorted(RESELECT))
def test_reselect_to_another_class(library: ContentLibrary, make_char: MakeChar, cls: str) -> None:
    world = make_world()
    before = _with_records(_chosen(library, make_char, cls, real=cls == "melee"))
    assert before.opening is not None and before.level == 3
    assert reselect_problem(library, before) is None
    old = before.opening.granted_skills
    assert reselect_returns(before) and set(reselect_returns(before)) == set(old)
    assert set(old) & set(before.skill_regions) and set(old) & set(before.flash)
    weapon, keywords = RESELECT[cls]
    assert library.weapons[weapon].weapon_class not in (
        cls,
        library.weapons[CHOICES[cls][0]].weapon_class,
    )
    result = _step(library, before, _again(cls), world)
    char = result.char
    # 武器與招：和靶場預覽同一個種子
    run = new_keyword_run(library, weapon, keywords, before.opening.seed, "recommended")
    given = run.hero.skills
    assert char.hero.weapon == weapon and char.hero.skills[:2] == given and len(given) == 2
    assert "main_hand" not in char.equipment
    _check_returned(before, char, given)
    _check_numbers(library, before, char, cls)
    opening = char.opening
    assert opening is not None and opening.stage == "chosen" and opening.reselect_used
    assert (opening.weapon, opening.keywords) == (weapon, keywords)
    assert opening.weapon_class == library.weapons[weapon].weapon_class
    assert opening.granted_skills == given
    assert opening.deferred_offers == before.opening.deferred_offers
    event = next(e for e in result.events if isinstance(e, OpeningReselectedEvent))
    assert (event.weapon, event.keywords, event.skills) == (weapon, keywords, given)
    assert event.old_weapon == CHOICES[cls][0]
    assert set(event.returned) == set(old) and len(event.returned_names) == 4
    assert all(event.returned_names) and event.lost_zh == ()
    # 重新出題：第 1 組馬上出，選完才出第 2 組；選到的招記進 granted_skills
    home = quest_home(library, QUEST)
    assert home is not None
    steps = [s.id for s in home[1].steps[:2]]
    events: tuple[object, ...] = result.events
    taken: list[str] = []
    for index in range(2):
        assert [e.step for e in events if isinstance(e, SkillOfferedEvent)] == [steps[index]]
        assert [p.step for p in char.pending_offers] == [steps[index]]
        assert char.offers_made == before.offers_made + index + 1
        picked = _step(library, char, OfferPickAction(pick=0), world)
        char, events = picked.char, picked.events
        took = next(e for e in picked.events if isinstance(e, SkillOfferTakenEvent))
        assert took.skill is not None
        taken.append(took.skill)
    assert char.pending_offers == () and len(set(taken)) == 2
    assert char.opening is not None and char.opening.granted_skills == (*given, *taken)
    # 只能一次
    assert reselect_problem(library, char) == "免費重選只有一次，已經用過了"
    with pytest.raises(WorldActionError, match="只有一次"):
        _step(library, char, _again(cls), world)


def test_reselect_is_deterministic(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    first = _step(library, _chosen(library, make_char), _again("melee"), world)
    second = _step(library, _chosen(library, make_char), _again("melee"), world)
    assert dumps_char(first.char) == dumps_char(second.char)
    assert first.events == second.events


def test_reselect_same_kit_gives_the_same_starting_skills(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """重選成原本那一套：起始 2 招相同（同一個開局種子），紀錄歸零、三選一重新出題。"""
    world = make_world()
    before = _with_records(_chosen(library, make_char))
    assert before.opening is not None
    weapon, keywords = CHOICES["melee"]
    action = OpeningReselectAction(weapon=weapon, keywords=keywords)
    char = _step(library, before, action, world).char
    assert char.hero.skills[:2] == before.hero.skills[:2]
    assert char.hero.attributes == before.hero.attributes
    for skill in before.opening.granted_skills:
        assert skill not in char.skill_usage and skill not in char.flash
    assert len(char.pending_offers) == 1 and char.offers_made == before.offers_made + 1


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


def test_reselect_conditions(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    chosen = _chosen(library, make_char)
    cases: list[tuple[CharacterState, str]] = [
        (make_char(), "開局已經結束"),  # 舊角色：沒有重選
        (_starter(library, make_char), "還沒正式選定"),
        (_fast_played(library, make_char), "還沒正式選定"),
        (chosen.model_copy(update={"level": OPENING_END_LEVEL}), "4 級之後不能重選"),
        (chosen.model_copy(update={"location": "bamboo_path"}), "霧渡鎮找葛蘭"),
        (
            chosen.model_copy(update={"pending_encounter": make_encounter("mist_ferry")}),
            "遭遇",
        ),
    ]
    for char, reason in cases:
        before = dumps_char(char)
        assert reason in (reselect_problem(library, char) or "")
        with pytest.raises(WorldActionError, match=reason):
            _step(library, char, _again("melee"), world)
        assert dumps_char(char) == before
    with pytest.raises(WorldActionError):  # 還在選大類：開局閘門擋
        _step(library, _pending(library, make_char), _again("melee"), world)
    capital = chosen.model_copy(update={"region": "capital", "location": "capital"})
    assert _step(library, capital, _again("melee"), world).char.hero.weapon == "bow"


def test_reselect_rejects_bad_weapon_or_keywords(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    chosen = _chosen(library, make_char)
    bad: list[WorldAction] = [
        OpeningReselectAction(weapon="no_such_weapon", keywords=("ignite", "charged")),
        OpeningReselectAction(weapon="fire_staff", keywords=("ignite",)),
        OpeningReselectAction(weapon="fire_staff", keywords=("ignite", "ignite")),
        OpeningReselectAction(weapon="fire_staff", keywords=("ignite", "no_such_keyword")),
    ]
    for action in bad:
        before = dumps_char(chosen)
        with pytest.raises(WorldActionError):
            _step(library, chosen, action, world)
        assert dumps_char(chosen) == before
    assert reselect_problem(library, chosen) is None  # 沒有用掉那一次


# ---------------------------------------------------------------------------
# 邊界（21.5 第 9 點「重選的邊界」）
# ---------------------------------------------------------------------------


def _swapped(library: ContentLibrary, make_char: MakeChar) -> tuple[CharacterState, ItemDef, str]:
    """正式選定（火焰法杖）之後自己換上一把掉落的主手：起始武器本體變成背包裡的一件基礎武器。
    回傳角色、玩家自己的那把、起始武器本體的物品 ID。"""
    own = _item(library, "weapon")
    chosen = _chosen(library, make_char, gear=(own,))
    assert starter_weapon_held(library, chosen) and reselect_losses(library, chosen) == ()
    char = _step(library, chosen, EquipAction(item=own.id), make_world()).char
    base_id = starter_item_id(library, char)
    assert base_id is not None and [g.id for g in char.gear] == [base_id]
    assert char.equipment["main_hand"] == own
    return char, own, base_id


def test_reselect_takes_back_the_starting_weapon_item(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """玩家換過主手：背包裡的起始武器本體收回；玩家自己換上的那把留在背包。"""
    char, own, base_id = _swapped(library, make_char)
    assert starter_weapon_held(library, char)
    done = _step(library, char, _again("melee"), make_world()).char
    assert done.hero.weapon == "bow" and "main_hand" not in done.equipment
    assert done.gear == (own,) and base_id not in done.gear_mods
    assert done.gold == char.gold


def test_reselect_takes_back_the_starting_weapon_when_worn_again(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """換下又換回：主手欄裡的起始武器本體收回，玩家自己的那把照舊在背包。"""
    world = make_world()
    char, own, base_id = _swapped(library, make_char)
    char = _step(library, char, EquipAction(item=base_id), world).char
    assert char.equipment["main_hand"].id == base_id and char.gear == (own,)
    done = _step(library, char, _again("melee"), world).char
    assert "main_hand" not in done.equipment and done.gear == (own,)
    assert done.hero.weapon == "bow"


def test_reselect_when_the_starting_weapon_was_sold(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """起始武器已經不在（賣掉、寄走、分解）：不收回也不扣錢，照樣能重選。"""
    char, own, _base_id = _swapped(library, make_char)
    sold = char.model_copy(update={"gear": (), "gold": 77})
    assert not starter_weapon_held(library, sold)
    done = _step(library, sold, _again("melee"), make_world()).char
    assert done.gold == 77 and done.gear == (own,)
    assert done.hero.weapon == "bow" and "main_hand" not in done.equipment


def test_reselect_lists_and_drops_enhancement(library: ContentLibrary, make_char: MakeChar) -> None:
    """花在起始武器上的強化不退：確認用的清單列得出來，重選後紀錄跟著武器一起消失。"""
    char, own, base_id = _swapped(library, make_char)
    mod = GearMod(fingerprint="0" * 64, enhance=2, rerolls=(0,), imbues=1)
    bag = {"item_coarse_material": 5}
    enhanced = char.model_copy(update={"gear_mods": {base_id: mod}, "bag": bag})
    name = library.weapons[CHOICES["melee"][0]].name_zh
    lost = reselect_losses(library, enhanced)
    assert lost == (
        f"{name}的強化 +2（材料不退）",
        f"{name}的重骰 1 次（材料不退）",
        f"{name}的指定詞條 1 次（材料不退）",
    )
    result = _step(library, enhanced, _again("melee"), make_world())
    event = next(e for e in result.events if isinstance(e, OpeningReselectedEvent))
    assert event.lost_zh == lost
    done = result.char
    assert done.gear_mods == {} and done.gear == (own,)
    assert done.bag == bag and done.gold == enhanced.gold  # 材料與金幣都不退


def test_reselect_refused_when_bag_is_full(library: ContentLibrary, make_char: MakeChar) -> None:
    """背包放不下就不能重選，並說明原因；角色不變。起始武器收回會空出一格，所以還在背包時放得下。"""
    world = make_world()
    rules = library.world_economy.rules
    assert rules is not None
    slots = rules.bag_slots
    char, own, _base_id = _swapped(library, make_char)
    # 起始武器已賣、背包全滿：玩家自己的主手沒有地方放
    full = char.model_copy(update={"gear": (), "bag": {"item_coarse_material": 20 * slots}})
    before = dumps_char(full)
    with pytest.raises(WorldActionError) as refused:
        _step(library, full, _again("melee"), world)
    assert str(refused.value) == (
        f"不能重選：換下來的主手要收進背包，但背包放不下（需要 {slots + 1} 格，只有 {slots} 格）"
    )
    assert dumps_char(full) == before and reselect_problem(library, full) is None
    # 起始武器還在背包（占 1 格）：收回它剛好空出玩家主手要的那一格
    tight = char.model_copy(update={"bag": {"item_coarse_material": 20 * (slots - 1)}})
    assert _step(library, tight, _again("melee"), world).char.gear == (own,)


def test_reselect_two_handed_stows_off_hand(library: ContentLibrary, make_char: MakeChar) -> None:
    """重選雙手武器：穿著的副手收進背包（防具照穿）；背包放不下就不能重選並說明原因。"""
    world = make_world()
    rules = library.world_economy.rules
    assert rules is not None
    shield, body = _item(library, "offhand"), _item(library, "body")
    sword = OpeningConfirmAction(weapon="one_handed_sword", keywords=("prone", "ignite"))
    chosen = _chosen(library, make_char, confirm=sword, gear=(shield, body))
    for piece in (shield, body):
        chosen = _step(library, chosen, EquipAction(item=piece.id), world).char
    assert set(chosen.equipment) == {"off_hand", "body"} and chosen.gear == ()
    assert library.weapons["greatsword"].two_handed
    action = OpeningReselectAction(weapon="greatsword", keywords=("prone", "ignite"))
    done = _step(library, chosen, action, world).char
    assert set(done.equipment) == {"body"} and done.gear == (shield,)
    one_handed = OpeningReselectAction(weapon="dagger", keywords=("prone", "ignite"))
    kept = _step(library, chosen, one_handed, world).char
    assert set(kept.equipment) == {"off_hand", "body"} and kept.gear == ()
    full = chosen.model_copy(update={"bag": {"item_coarse_material": 20 * rules.bag_slots}})
    before = dumps_char(full)
    with pytest.raises(WorldActionError, match=r"不能重選：不能選雙手劍：它占用副手.*背包放不下"):
        _step(library, full, action, world)
    assert dumps_char(full) == before
