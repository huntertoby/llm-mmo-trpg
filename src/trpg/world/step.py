"""套用世界動作（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.5）。

``world_step(library, world, char, action, now) → StepResult(world, char, events)`` 是純函式：
不讀時間、不呼叫 LLM、亂數只由 :mod:`trpg.world.rng` 依賽季種子衍生。不合法的動作拋
:class:`~trpg.world.errors.WorldActionError`，傳入的狀態不變（模型是不可變的）。

- **移動**（09 9.6.2、9.6.7 #9、#10）：走到相鄰地點；每一步擲遇敵（目的地建議等級越高越容易），
  可花補給趕路降低機率；遇敵只產生 :class:`EncounterResult`（開戰在 5A-4）。抵達後對目的地旁的
  隱藏地點自動感知判定（#112）。
- **紮營**（#114）：非戰鬥狀態的地點花補給，HP、法力、耐力回滿＝營火。
- **5A-4**：撤退、戰鬥（:mod:`trpg.world.battle`）、城鎮休息、換技能、傳送
  （:mod:`trpg.world.town`）；移動到「已清空」的地點不遇敵（擲骰照擲）。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.shared.types import Attribute
from trpg.world.actions import (
    CampAction,
    CampedEvent,
    EncounterCheckEvent,
    EncounterEvent,
    FightAction,
    LoadoutAction,
    LocationRevealedEvent,
    PerceptionCheckEvent,
    RestAction,
    RetreatAction,
    TeleportAction,
    TravelAction,
    TraveledEvent,
    WorldAction,
    WorldEvent,
)
from trpg.world.battle import fight
from trpg.world.clock import day_phase, refresh_day
from trpg.world.common import max_hp, max_mana
from trpg.world.common import rules_of as _rules
from trpg.world.common import world_map_of as _world_map
from trpg.world.errors import WorldActionError
from trpg.world.events import roll_event
from trpg.world.rng import STREAM_BATTLE, STREAM_REVEAL, STREAM_TRAVEL, draw
from trpg.world.state import (
    CharacterState,
    EncounterResult,
    LocationRef,
    PerceptionMark,
    WorldState,
)
from trpg.world.town import loadout, rest, retreat, teleport, with_visited_town
from trpg.world.weather import weather_at

__all__ = [
    "NO_CAMP_KINDS",
    "StepResult",
    "camp_problem",
    "max_hp",
    "max_mana",
    "new_character",
    "perception_modifier",
    "reveal_location",
    "world_step",
]

NO_CAMP_KINDS = frozenset({"town", "elite_lair", "boss"})
"""不能紮營的地點種類（#114：Boss 地點、精英巢穴不行；城鎮直接休息，5A-4）。
``camp`` 另看是否已清空。"""

_PERCEPTION_REVEAL = "perception_nearby"


@dataclass(frozen=True)
class StepResult:
    world: WorldState
    char: CharacterState
    events: tuple[WorldEvent, ...]


# ---------------------------------------------------------------------------
# 內容與角色數值
# ---------------------------------------------------------------------------


def perception_modifier(library: ContentLibrary, char: CharacterState) -> int:
    """感知修正：``(感知 − ability_mod_base) // ability_mod_divisor``（同引擎的檢定修正）。"""
    core = library.ruleset.core
    wis = char.hero.attributes[Attribute.WIS]
    return (wis - core.ability_mod_base) // core.ability_mod_divisor


def new_character(
    library: ContentLibrary,
    character_id: str,
    hero: UnitTemplate,
    *,
    region: str,
    origin: str | None = None,
) -> CharacterState:
    """新角色：等級 1、HP 與法力滿、補給 ``supplies.start``、站在 ``region`` 的小鎮。"""
    world_map = _world_map(library, region)
    char = CharacterState.model_validate(
        {
            "character_id": character_id,
            "hero": hero,
            "origin": origin,
            "level": 1,
            "xp": 0,
            "hp": 0,
            "mana": 0,
            "region": region,
            "location": world_map.town,
            "supplies": _rules(library).supplies.start,
            "visited_towns": (region,),
        }
    )
    return char.model_copy(update={"hp": max_hp(library, char), "mana": max_mana(library, char)})


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def world_step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WorldAction,
    now: int,
) -> StepResult:
    """套用一個世界動作；不合法拋 :class:`WorldActionError`。"""
    if isinstance(action, TravelAction):
        return _travel(library, world, char, action, now)
    if isinstance(action, CampAction):
        return _camp(library, world, char, now)
    if isinstance(action, FightAction):
        if char.pending_encounter is None:
            raise WorldActionError("目前沒有遭遇")
        world, char, events = fight(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)
    return _service(library, world, char, action)


def _service(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: WorldAction
) -> StepResult:
    """撤退與城鎮服務（5A-4，:mod:`trpg.world.town`）：不動世界快照。"""
    if isinstance(action, RetreatAction):
        char, events = retreat(library, char)
    elif isinstance(action, RestAction):
        char, events = rest(library, char)
    elif isinstance(action, LoadoutAction):
        char, events = loadout(library, char, action)
    elif isinstance(action, TeleportAction):
        char, events = teleport(library, char, action)
    else:
        raise WorldActionError(f"未知的世界動作：{action!r}")  # pragma: no cover
    return StepResult(world=world, char=char, events=events)


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------


def _check_travel(
    world: WorldState, char: CharacterState, world_map: LocationMapDef, action: TravelAction
) -> LocationDef:
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能移動")
    locations = world_map.location_by_id()
    target = locations.get(action.to)
    if target is None:
        raise WorldActionError(f"{world_map.name_zh}沒有地點 {action.to}")
    if action.to not in world_map.neighbors(char.location):
        raise WorldActionError(f"{action.to} 不和目前所在的 {char.location} 相鄰")
    if target.hidden and not char.has_revealed(world_map.region, target.id):
        raise WorldActionError(f"還沒發現 {action.to}")
    if target.unlock_flag is not None and not world.has_flag(target.unlock_flag):
        raise WorldActionError(f"{target.name_zh}還沒開放")
    return target


def _travel(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: TravelAction,
    now: int,
) -> StepResult:
    rules = _rules(library)
    world_map = _world_map(library, char.region)
    target = _check_travel(world, char, world_map, action)
    spent = 0
    if action.hasten:
        spent = rules.hasten.cost
        if char.supplies < spent:
            raise WorldActionError(f"補給不足，趕路要 {spent} 補給")
    chance = rules.encounter.permille_for(target.level_max)
    if world.is_cleared(char.region, target.id, now):
        chance = 0  # 已清空：沒有敵人（代決 5A4-9）；擲骰照擲，亂數消耗不變
    if action.hasten:
        chance = chance * rules.hasten.encounter_permille // 1000

    events: list[WorldEvent] = [
        TraveledEvent(
            from_location=char.location, to=target.id, hasten=action.hasten, supplies_spent=spent
        )
    ]
    from_location = char.location
    char = char.model_copy(
        update={"location": target.id, "supplies": char.supplies - spent, "camped_at": None}
    )
    if target.kind == "town":
        char = with_visited_town(char, char.region)
    rng, char = draw(world.season_seed, char, STREAM_TRAVEL)
    roll = rng.randint(0, 999)
    encountered = roll < chance
    events.append(
        EncounterCheckEvent(
            location=target.id, chance_permille=chance, roll=roll, encountered=encountered
        )
    )
    if encountered and target.level_max is not None:
        result, char = _encounter(library, world, char, target, now)
        result = result.model_copy(update={"from_location": from_location})
        char = char.model_copy(update={"pending_encounter": result})
        events.append(EncounterEvent(result=result))
    rolled = roll_event(library, world, char, encountered=encountered, now=now)
    char = rolled.char
    events += rolled.events
    char, found = _perceive(library, world, char, world_map, now)
    events += found
    return StepResult(world=world, char=char, events=tuple(events))


def _encounter(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    target: LocationDef,
    now: int,
) -> tuple[EncounterResult, CharacterState]:
    rng, char = draw(world.season_seed, char, STREAM_BATTLE)
    battle_map = rng.choice(target.battle_maps) if target.battle_maps else None
    seed = rng.next_u32()
    assert target.level_max is not None
    result = EncounterResult(
        region=char.region,
        location=target.id,
        level=target.level_max,
        battle_map=battle_map,
        battle_seed=seed,
        weather=weather_at(library, world, char.region, now),
        day_phase=day_phase(now),
        at=now,
    )
    return result, char


def _perceive(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    world_map: LocationMapDef,
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    """抵達後對相鄰的隱藏地點自動感知判定（#112；鄰居依 ID 排序）。"""
    rules = _rules(library)
    locations = world_map.location_by_id()
    today = refresh_day(now)
    region = world_map.region
    events: list[WorldEvent] = []
    for neighbor_id in world_map.neighbors(char.location):
        hidden = locations[neighbor_id]
        if (
            not hidden.hidden
            or _PERCEPTION_REVEAL not in hidden.reveal
            or char.has_revealed(region, neighbor_id)
            or char.perception_day(region, neighbor_id) == today
        ):
            continue
        assert hidden.level_min is not None
        dc = rules.perception.dc_for(hidden.level_min)
        modifier = perception_modifier(library, char)
        rng, char = draw(world.season_seed, char, STREAM_REVEAL)
        roll = rng.d20()
        success = roll + modifier >= dc
        char = _mark_perception(char, region, neighbor_id, today)
        events.append(
            PerceptionCheckEvent(
                location=neighbor_id, roll=roll, modifier=modifier, dc=dc, success=success
            )
        )
        if success:
            char = reveal_location(char, region, neighbor_id)
            events.append(LocationRevealedEvent(location=neighbor_id, method=_PERCEPTION_REVEAL))
    return char, events


def _mark_perception(char: CharacterState, region: str, location: str, day: int) -> CharacterState:
    marks = [m for m in char.perception_marks if (m.region, m.location) != (region, location)]
    marks.append(PerceptionMark(region=region, location=location, day=day))
    marks.sort(key=lambda m: (m.region, m.location))
    return char.model_copy(update={"perception_marks": tuple(marks)})


def reveal_location(char: CharacterState, region: str, location: str) -> CharacterState:
    """把隱藏地點加進角色的 ``revealed``（已發現則不變）。"""
    if char.has_revealed(region, location):
        return char
    refs = [*char.revealed, LocationRef(region=region, location=location)]
    refs.sort(key=LocationRef.key)
    return char.model_copy(update={"revealed": tuple(refs)})


# ---------------------------------------------------------------------------
# 紮營
# ---------------------------------------------------------------------------


def camp_problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> str | None:
    """不能在目前地點紮營的原因；可以時回傳 ``None``。"""
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能紮營"
    world_map = _world_map(library, char.region)
    here = world_map.location_by_id()[char.location]
    if here.kind == "town":
        return "城鎮裡直接休息，不用紮營"
    if here.kind in NO_CAMP_KINDS:
        return f"{here.name_zh}不能紮營"
    if here.kind == "camp" and not world.is_cleared(char.region, here.id, now):
        return f"{here.name_zh}的敵人還在，不能紮營"
    cost = _rules(library).camp_cost
    if char.supplies < cost:
        return f"補給不足，紮營要 {cost} 補給"
    return None


def _camp(library: ContentLibrary, world: WorldState, char: CharacterState, now: int) -> StepResult:
    problem = camp_problem(library, world, char, now)
    if problem is not None:
        raise WorldActionError(problem)
    char = char.model_copy(
        update={
            "supplies": char.supplies - _rules(library).camp_cost,
            "hp": max_hp(library, char),
            "mana": max_mana(library, char),
            "stamina": None,
            "camped_at": LocationRef(region=char.region, location=char.location),
        }
    )
    event = CampedEvent(
        location=char.location, supplies_left=char.supplies, hp=char.hp, mana=char.mana
    )
    return StepResult(world=world, char=char, events=(event,))
