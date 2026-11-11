"""4 級前的免費重選與開局結束（Phase OB-3，#150 第 5 點與第 9 點「重選的邊界」；21 21.5）。

世界動作 ``opening_reselect {weapon, keywords}``（:func:`apply_reselect`）。條件
（:func:`reselect_problem`）：已經正式選定（``opening.stage == "chosen"``）、``char.level`` 低於
:data:`~trpg.world.growth.OPENING_END_LEVEL`、沒用過、人在葛蘭所在的城鎮或主城、沒有待處理的遭遇。

重選的順序（每一步的理由見 ``docs/phases/PhaseOB-3報告.md``）：

1. 檢查全部做完才動狀態（不合法拋 :class:`WorldActionError`，狀態不變）。
2. 依開局種子取新的起始 2 招（和靶場預覽、正式選定同一套）。
3. 收回 ``opening.granted_skills``（舊的起始 2 招＋新手第 1、2 步三選一拿到的）：裝備中與備用，
   連同 ``generated_skills``、``flash``、``flash_bases``、``skill_usage``、``skill_regions``；還沒選
   的那組延後三選一也收回。其他來源學到的招留著。
4. 收回起始武器本體（:func:`_take_back_weapon`）：還拿在手上就直接換掉；玩家換過主手時，起始武器
   是背包或主手欄裡的那件基礎武器（:func:`starter_item_id`），拿掉它與它的改動紀錄；已經賣掉、
   寄走就不收回也不扣錢。玩家自己換上的主手留在背包。
5. 新武器是雙手或成對的：穿著的副手收進背包。背包放不下（第 4、5 步多出來的）就不能重選。
6. 依新武器的大類重建基礎值、全部屬性點照推薦配法重配（全數在 ``attribute_spent``）。
7. 新的起始 2 招排在最前面；最大 HP、法力的變化走 ``with_hp_change``，再把 HP、法力回滿。
8. ``opening``：新的武器、關鍵字、大類，``granted_skills``＝新的起始 2 招，``reselect_used``。
9. 重新出延後的三選一的第 1 組（選完一組才出下一組，同正式選定）。

**開局結束**（:func:`close_opening`，第 9 點「4 級前：一律看等級」）：正式選定過的角色升到
:data:`~trpg.world.growth.OPENING_END_LEVEL` 級，``opening`` 清成 ``None``——重選過期，溶掉與傳承
解鎖。延後的三選一還沒選完時等選完才清（後面那組要靠 ``opening`` 出題）。

純函式、確定性：不讀時間、不用全域亂數。
"""

from __future__ import annotations

from typing import Final

from trpg.content.battle import WeaponDef
from trpg.content.equipment import ItemDef, loadout_problems
from trpg.content.library import ContentLibrary
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.gear import current_item
from trpg.roguelite.progress import with_hp_change
from trpg.roguelite.start import new_keyword_run, start_weapons
from trpg.world.actions import OpeningReselectAction, OpeningReselectedEvent, WorldEvent
from trpg.world.common import max_hp, max_mana
from trpg.world.errors import WorldActionError
from trpg.world.gear import gear_run, item_loadout
from trpg.world.growth import OPENING_END_LEVEL, as_run, from_run
from trpg.world.inventory import room_problem
from trpg.world.opening_choice import (
    chosen_hero,
    place_ok,
    place_problem,
    stow_off_hand,
    with_starting_skills,
    without_skills,
)
from trpg.world.quests import deferred_index, deferred_pending, issue_deferred_offers
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "apply_reselect",
    "close_opening",
    "reselect_losses",
    "reselect_problem",
    "reselect_returns",
    "starter_item_id",
    "starter_weapon_held",
]

_MAIN_HAND: Final = "main_hand"
_NOT_CHOSEN_ZH: Final = "還沒正式選定武器與關鍵字，不能重選"
_OVER_ZH: Final = "開局已經結束，不能重選起始武器與關鍵字（換武器靠掉落與打造）"
_USED_ZH: Final = "免費重選只有一次，已經用過了"


def reselect_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """現在不能免費重選的原因（中文）；可以時 ``None``。"""
    opening = char.opening
    if opening is None:
        return _OVER_ZH
    if opening.stage != "chosen" or opening.weapon is None:
        return _NOT_CHOSEN_ZH
    checks = (
        (char.level >= OPENING_END_LEVEL, f"已到 {OPENING_END_LEVEL} 級，免費重選已結束"),
        (opening.reselect_used, _USED_ZH),
        (not place_ok(library, char), place_problem(library, "重選")),
        (char.pending_encounter is not None, "還有沒處理的遭遇，不能重選"),
        (char.pending_flash is not None, "還有閃現的選項沒有選，不能重選"),
    )
    return next((reason for failed, reason in checks if failed), None)


def starter_item_id(library: ContentLibrary, char: CharacterState) -> str | None:
    """起始武器本體變成物品時的 ID（玩家換過主手之後，原本拿在手上的起始武器會變成一件沒有詞條
    的基礎武器放進背包，:func:`trpg.roguelite.gear.current_item`）；沒有正式選定＝``None``。"""
    opening = char.opening
    if opening is None or opening.weapon is None or opening.weapon not in library.weapons:
        return None
    bare = gear_run(char).model_copy(
        update={
            "hero": char.hero.model_copy(update={"weapon": opening.weapon}),
            "equipment": {},
        }
    )
    item = current_item(library, bare, _MAIN_HAND)
    return None if item is None else item.id


def _starter_item(library: ContentLibrary, char: CharacterState) -> ItemDef | None:
    """起始武器本體那件物品（主手欄或背包）；還拿在手上（不是物品）或已經不在＝``None``。"""
    item_id = starter_item_id(library, char)
    if item_id is None:
        return None
    worn = char.equipment.get(_MAIN_HAND)
    if worn is not None and worn.id == item_id:
        return worn
    return next((g for g in char.gear if g.id == item_id), None)


def starter_weapon_held(library: ContentLibrary, char: CharacterState) -> bool:
    """起始武器本體還在（拿在手上、主手欄或背包），重選時會被收回；賣掉、寄走、分解了＝假。"""
    opening = char.opening
    if opening is None or opening.weapon is None:
        return False
    if _MAIN_HAND not in char.equipment and char.hero.weapon == opening.weapon:
        return True
    return _starter_item(library, char) is not None


def reselect_losses(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """重選會跟著起始武器一起消失、不退材料的改動（每項一句；給確認畫面與事件用）。"""
    item = _starter_item(library, char)
    mod = None if item is None else char.gear_mods.get(item.id)
    if item is None or mod is None:
        return ()
    lost: list[str] = []
    if mod.enhance:
        lost.append(f"{item.name_zh}的強化 +{mod.enhance}（材料不退）")
    if mod.rerolls:
        lost.append(f"{item.name_zh}的重骰 {len(mod.rerolls)} 次（材料不退）")
    if mod.imbues:
        lost.append(f"{item.name_zh}的指定詞條 {mod.imbues} 次（材料不退）")
    return tuple(lost)


def reselect_returns(char: CharacterState) -> tuple[str, ...]:
    """重選會收回的招（還在身上的；裝備中的在前、備用的在後）。"""
    opening = char.opening
    if opening is None:
        return ()
    gone = set(opening.granted_skills)
    return tuple(s for s in (*char.hero.skills, *char.bench) if s in gone)


def _take_back_weapon(
    library: ContentLibrary, char: CharacterState, new: WeaponDef
) -> CharacterState:
    """第 4、5 步：收回起始武器本體、玩家自己的主手與被占用的副手收進背包；背包放不下就拒絕。"""
    item_id = starter_item_id(library, char)
    equipment = dict(char.equipment)
    gear = list(char.gear)
    worn = equipment.pop(_MAIN_HAND, None)
    if worn is not None and worn.id != item_id:
        gear.append(worn)  # 玩家自己換上的主手：留在背包
    mods = dict(char.gear_mods)
    kept = next((g for g in gear if g.id == item_id), None)
    if kept is not None:
        gear.remove(kept)
    if kept is not None or (worn is not None and worn.id == item_id):
        mods.pop(item_id or "", None)
    moved = char.model_copy(update={"equipment": equipment, "gear": tuple(gear), "gear_mods": mods})
    try:
        moved = stow_off_hand(library, moved, new)
    except WorldActionError as exc:
        raise WorldActionError(f"不能重選：{exc}") from exc
    if len(moved.gear) > len(char.gear):
        room = room_problem(library, moved.bag, len(moved.gear))
        if room is not None:
            raise WorldActionError(f"不能重選：換下來的主手要收進背包，但{room}")
    return moved


def apply_reselect(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: OpeningReselectAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """世界動作 ``opening_reselect``（順序見模組說明）；不合法拋 :class:`WorldActionError`，狀態
    不變。"""
    del now
    problem = reselect_problem(library, char)
    if problem is not None:
        raise WorldActionError(problem)
    opening = char.opening
    assert opening is not None
    if action.weapon not in start_weapons(library):
        raise WorldActionError(f"靶場沒有這把武器：{action.weapon}")
    try:
        run = new_keyword_run(library, action.weapon, action.keywords, opening.seed, "recommended")
    except ChoiceError as exc:
        raise WorldActionError(str(exc)) from exc
    generated = {s.id: s for s in run.generated_skills}
    picked = [generated.get(s) or library.skills[s] for s in run.hero.skills]
    weapon = library.weapons[action.weapon]
    old_names = {s.id: s.name_zh for s in char.generated_skills}
    returned = reselect_returns(char)
    lost = reselect_losses(library, char)
    before = as_run(char)
    done = without_skills(char, opening.granted_skills)
    done = done.model_copy(
        update={
            "pending_offers": tuple(
                p for p in done.pending_offers if deferred_index(library, done, p) is None
            )
        }
    )
    done = _take_back_weapon(library, done, weapon)
    total = done.attribute_points + sum(done.attribute_spent.values())
    hero, allocation = chosen_hero(library, done, action.weapon, picked, total)
    hero = hero.model_copy(update={"skills": done.hero.skills})  # 起始 2 招在下一步併進來
    done = done.model_copy(
        update={"hero": hero, "attribute_points": 0, "attribute_spent": allocation}
    )
    _check_loadout(library, done, weapon)
    done, given = with_starting_skills(library, world, done, run)
    done = from_run(done, with_hp_change(library, before, as_run(done)))
    done = done.model_copy(update={"hp": max_hp(library, done), "mana": max_mana(library, done)})
    again = opening.model_copy(
        update={
            "weapon_class": weapon.weapon_class,
            "weapon": action.weapon,
            "keywords": tuple(action.keywords),
            "granted_skills": given,
            "reselect_used": True,
        }
    )
    done = done.model_copy(update={"opening": again})
    names = {s.id: s.name_zh for s in (*done.generated_skills, *picked)}
    event = OpeningReselectedEvent(
        weapon=action.weapon,
        keywords=tuple(action.keywords),
        skills=given,
        skill_names=tuple(names.get(s) or library.skills[s].name_zh for s in given),
        old_weapon=opening.weapon,
        returned=returned,
        returned_names=tuple(_name(library, old_names, s) for s in returned),
        lost_zh=lost,
    )
    done, offered = issue_deferred_offers(library, world, done)
    return done, (event, *offered)


def _name(library: ContentLibrary, generated: dict[str, str], skill_id: str) -> str:
    found = library.skills.get(skill_id)
    return generated.get(skill_id) or (skill_id if found is None else found.name_zh)


def _check_loadout(library: ContentLibrary, char: CharacterState, weapon: WeaponDef) -> None:
    """重選後身上的裝備要和新武器相容（主手欄已清空、副手已收起；其他限制照 8.23 再查一次）。"""
    if not char.equipment:
        return
    problems = loadout_problems(
        item_loadout(library, char.equipment), weapon, library.ruleset.equipment
    )
    if problems:
        raise WorldActionError(f"不能重選：{'；'.join(problems)}")


def close_opening(library: ContentLibrary, char: CharacterState) -> CharacterState:
    """開局結束（21.5 第 9 點）：正式選定過的角色到 :data:`OPENING_END_LEVEL` 級，``opening`` 清成
    ``None``。延後的三選一還沒選完時先不清；還在入門期（沒正式選定）的不清（還要選定）。"""
    opening = char.opening
    if opening is None or opening.stage != "chosen" or char.level < OPENING_END_LEVEL:
        return char
    if deferred_pending(library, char):
        return char
    return char.model_copy(update={"opening": None})
