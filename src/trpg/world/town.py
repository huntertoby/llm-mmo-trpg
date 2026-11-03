"""撤退與城鎮服務（Phase 5A-4；``docs/phases/Phase5計畫.md`` 9.2）。

- **撤退**（09 9.6.6）：看了陣容不打，退回出發地點；不開戰、不扣任何東西、不擲骰。
- **休息**（9.6.7 #2、#11）：只在城鎮；HP、法力、耐力回滿，補給補到至少初值（代決 5A4-11）。
- **換技能**（07 7.6）：城鎮或營火（``camped_at`` 是目前地點）；只能裝擁有的技能、欄位上限照
  roguelite 的 ``set_loadout``（5A-6 起生成技能——閃現、升階重配後的技能——也能換）。
- **傳送**（9.6.2「城鎮之間用傳送點」）：從城鎮到去過的其他區小鎮，或從傳送點到它通往的區域
  （代決 5A4-12）。
"""

from __future__ import annotations

from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    LoadoutAction,
    LoadoutChangedEvent,
    RestedEvent,
    RetreatedEvent,
    TeleportAction,
    TeleportedEvent,
    WorldEvent,
)
from trpg.world.atlas import cross_gate, region_lit
from trpg.world.common import here, max_hp, max_mana, rules_of, world_map_of
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.growth import at_service, loadout_skills
from trpg.world.state import CharacterState, LocationRef

__all__ = [
    "loadout",
    "rest",
    "retreat",
    "teleport",
    "with_visited_location",
    "with_visited_town",
]


def _no_encounter(char: CharacterState, what: str) -> None:
    if char.pending_encounter is not None:
        raise WorldActionError(f"還有沒處理的遭遇，不能{what}")


def with_visited_town(char: CharacterState, region: str) -> CharacterState:
    """記下到過 ``region`` 的小鎮（主城不記：它不是區域，一開始就解鎖；6D-5）。"""
    if region in char.visited_towns or region == CAPITAL_REGION:
        return char
    return char.model_copy(update={"visited_towns": tuple(sorted({*char.visited_towns, region}))})


def with_visited_location(
    char: CharacterState, region: str | None = None, location: str | None = None
) -> CharacterState:
    """把地點（省略＝所在地點）記進 ``visited_locations``（區域圖的戰爭迷霧，21.1；6C-6）。
    已記過＝同一個物件。"""
    region = char.region if region is None else region
    location = char.location if location is None else location
    if char.has_visited(region, location):
        return char
    refs = [*char.visited_locations, LocationRef(region=region, location=location)]
    refs.sort(key=LocationRef.key)
    return char.model_copy(update={"visited_locations": tuple(refs)})


def retreat(
    library: ContentLibrary, char: CharacterState
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    encounter = char.pending_encounter
    if encounter is None:
        raise WorldActionError("目前沒有遭遇，不用撤退")
    if encounter.contact is not None:  # 6C-1 實地地圖上碰到的敵人：回到進這張地圖時站的格子
        event = RetreatedEvent(from_location=char.location, to=char.location)
        update = {"pending_encounter": None, "field": encounter.contact.retreat_to}
        return char.model_copy(update=update), (event,)
    to = encounter.from_location or world_map_of(library, char.region).town
    event = RetreatedEvent(from_location=char.location, to=to)
    char = char.model_copy(update={"location": to, "pending_encounter": None, "camped_at": None})
    if to == world_map_of(library, char.region).town:
        char = with_visited_town(char, char.region)
    return char, (event,)


def rest(
    library: ContentLibrary, char: CharacterState
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    _no_encounter(char, "休息")
    location = here(library, char)
    if location.kind != "town":
        raise WorldActionError(f"只有城鎮能休息（{location.name_zh}可以紮營）")
    supplies = max(char.supplies, rules_of(library).supplies.start)
    char = char.model_copy(
        update={
            "hp": max_hp(library, char),
            "mana": max_mana(library, char),
            "stamina": None,
            "supplies": supplies,
        }
    )
    event = RestedEvent(location=char.location, hp=char.hp, mana=char.mana, supplies=supplies)
    return char, (event,)


def loadout(
    library: ContentLibrary, char: CharacterState, action: LoadoutAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    _no_encounter(char, "換技能")
    if not at_service(library, char):
        raise WorldActionError("只有城鎮與營火能換技能")
    char = loadout_skills(library, char, tuple(action.skills))
    return char, (LoadoutChangedEvent(skills=char.hero.skills, bench=char.bench),)


def teleport(
    library: ContentLibrary,
    char: CharacterState,
    action: TeleportAction,
    *,
    on_stone: bool = False,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """傳到另一區的城鎮。城鎮裡、或站在傳送石上（``on_stone``，21.1「從圖上傳送」；6D-5）：目的地
    要在自己的大世界圖上亮起（:func:`trpg.world.atlas.region_lit`；主城一開始就亮）。渡口：只能去它
    通往的那一區；畫了跨區出口的渡口要走過去（21.1 第一次要親自走過渡口，6D-5）。"""
    _no_encounter(char, "傳送")
    if action.region == char.region:
        raise WorldActionError("已經在這個區域")
    location = here(library, char)
    if location.kind == "town" or on_stone:
        if not region_lit(char, action.region):
            raise WorldActionError(f"還沒去過 {action.region} 的小鎮，不能傳送")
    elif location.kind == "gate":
        if location.gate_to != action.region:
            raise WorldActionError(f"{location.name_zh}不通往 {action.region}")
        if cross_gate(library, char.region, char.location):
            raise WorldActionError(f"{location.name_zh}要走到盡頭的出口過去")
    else:
        raise WorldActionError("只有城鎮與傳送點能傳送")
    try:
        town = world_map_of(library, action.region).town
    except WorldError as exc:
        raise WorldActionError(str(exc)) from exc
    char = char.model_copy(update={"region": action.region, "location": town, "camped_at": None})
    char = with_visited_town(char, action.region)
    return char, (TeleportedEvent(region=action.region, location=town),)
