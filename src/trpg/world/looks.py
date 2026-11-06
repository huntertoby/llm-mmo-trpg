"""外觀選項（Phase 6R-2，#137；``docs/design/07-角色成長.md`` 7.7）。

- 建角時選、之後 **在主城隨時免費改**（世界動作 ``change_look``）；只在畫面，不影響數值、技能與
  技能生成，引擎不讀（存在主角紙娃娃的 ``DollLook.custom``）。
- 選項要在該族的 ``look_options`` 內（:func:`trpg.content.races.look_choice_problems`）。
- 換種族（``change_race``、季末沿用上季角色）時，新種族也有的選項保留，沒有的改回預設
  （09 9.7 5F-5c＋#137，:func:`trpg.content.races.look_for_race`）。

純函式：不讀時間、不耗亂數。
"""

from __future__ import annotations

from trpg.content.battle import DollLook, LookChoice, UnitTemplate
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.races import look_choice_problems, look_for_race
from trpg.world.actions import ChangeLookAction, LookChangedEvent, WorldEvent
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "apply_look_change",
    "hero_with_look",
    "look_after_race_change",
    "look_change_problem",
    "look_problem",
]


def look_problem(library: ContentLibrary, race: str | None, look: LookChoice | None) -> str | None:
    """外觀選擇不合法的原因（繁體中文）；合法或沒選時 ``None``。"""
    if look is None or look.is_empty():
        return None
    table = library.ruleset.races
    if table is None or race is None:
        return "沒有種族的角色不能選外觀"
    race_def = table.by_id().get(race)
    if race_def is None:
        return f"未知的種族：{race}"
    problems = look_choice_problems(table, race_def, look)
    return "；".join(problems) if problems else None


def _with_custom(doll: DollLook | None, look: LookChoice | None) -> DollLook | None:
    custom = None if look is None or look.is_empty() else look
    if doll is None:
        return None if custom is None else DollLook(custom=custom)
    return doll.model_copy(update={"custom": custom})


def hero_with_look(hero: UnitTemplate, look: LookChoice | None) -> UnitTemplate:
    """主角換上外觀選擇（``None`` 或全空＝種族預設）；不檢查合法性。"""
    return hero.model_copy(update={"doll": _with_custom(hero.doll, look)})


def look_after_race_change(
    library: ContentLibrary, hero: UnitTemplate, race: str | None
) -> UnitTemplate:
    """主角換成 ``race`` 之後的外觀：新種族也有的選項保留，沒有的改回預設。"""
    doll = hero.doll
    table = library.ruleset.races
    if doll is None or doll.custom is None:
        return hero
    if table is None or race is None or race not in table.by_id():
        return hero_with_look(hero, None)
    kept = look_for_race(table, table.by_id()[race], doll.custom)
    return hero_with_look(hero, kept)


def look_change_problem(world: WorldState, char: CharacterState) -> str | None:
    """現在不能改外觀的原因；可以時 ``None``（#137：在主城隨時免費改）。"""
    del world
    if char.region != CAPITAL_REGION:
        return "只有在主城能改外觀"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能改外觀"
    return None


def apply_look_change(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: ChangeLookAction,
    _now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """世界動作 ``change_look``（不合法拋 :class:`WorldActionError`，狀態不變）。"""
    problem = look_change_problem(world, char) or look_problem(library, char.hero.race, action.look)
    if problem is not None:
        raise WorldActionError(problem)
    hero = hero_with_look(char.hero, action.look)
    char = char.model_copy(update={"hero": hero})
    custom = None if hero.doll is None else hero.doll.custom
    return char, (LookChangedEvent(look=custom),)
