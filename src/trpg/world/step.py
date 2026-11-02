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
- **5A-6**：成長的動作（配點、重配、閃現、溶掉、傳承、立誓；:mod:`trpg.world.growth`）。有已付點、
  還沒選的閃現選項時，只能送 ``flash_pick``。
- **5B-4**：接任務、選任務給的技能、和 NPC 說話、酒館（:mod:`trpg.world.quests`、
  :mod:`trpg.world.social`）；**每個動作之後** 依事件結果調好感度、推進進行中的任務
  （:func:`~trpg.world.quests.advance_quests`）。有任務給的三選一還沒選時，只能送 ``offer_pick``。
- **5B-4b**：放棄、交涉、戰鬥解法（``event_solve``，:mod:`trpg.world.solutions`；戰鬥解法的遭遇
  結束時在動作後段結算事件）；**每個動作之前** 結算到期、有結局的線頭（:mod:`trpg.world.endings`）。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.shared.types import Attribute
from trpg.world.actions import (
    AcceptQuestAction,
    CampAction,
    CampedEvent,
    EncounterCheckEvent,
    EncounterEvent,
    EventSolveAction,
    FightAction,
    FlashPickAction,
    HireAction,
    LoadoutAction,
    LocationRevealedEvent,
    NarrateAction,
    OfferPickAction,
    PerceptionCheckEvent,
    RestAction,
    RetreatAction,
    ShadowAiAction,
    SituationAction,
    TalkAction,
    TavernAction,
    TeleportAction,
    TravelAction,
    TraveledEvent,
    WorldAction,
    WorldEvent,
)
from trpg.world.battle import fight
from trpg.world.clock import refresh_day
from trpg.world.common import max_hp, max_mana
from trpg.world.common import rules_of as _rules
from trpg.world.common import world_map_of as _world_map
from trpg.world.companions import sync_companions
from trpg.world.economy import ECONOMY_ACTIONS, after_step, apply_economy
from trpg.world.economy_actions import EquipAction
from trpg.world.endings import expire_threads
from trpg.world.errors import WorldActionError
from trpg.world.events import mark_finished, mark_met_opportunities, roll_event
from trpg.world.gear import apply_equip
from trpg.world.growth import GROWTH_ACTIONS, apply_growth, hero_tier
from trpg.world.narration import apply_narration
from trpg.world.party import default_party, hire, set_shadow_ai
from trpg.world.quests import accept_quest, advance_quests, take_offer
from trpg.world.rng import STREAM_REVEAL, STREAM_TRAVEL, draw
from trpg.world.shadows import save_after_prep
from trpg.world.situations import resolve_situation
from trpg.world.social import talk, tavern
from trpg.world.solutions import make_encounter, settle_event_combat, solve_event
from trpg.world.state import (
    CharacterState,
    LocationRef,
    PerceptionMark,
    WorldState,
)
from trpg.world.town import loadout, rest, retreat, teleport, with_visited_town

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
            "skill_tier": hero_tier(library, 1),  # 開局不重配（6.34.9），第一次升階才重配
            "mercenaries": default_party(library),  # 預設鐵壁＋回春（9.6.11，5C-3）
            "gold": 0 if (economy := library.world_economy.rules) is None else economy.start_gold,
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
    """套用一個世界動作；不合法拋 :class:`WorldActionError`。動作之後推進任務（5B-4）。"""
    if char.pending_flash is not None and not isinstance(action, FlashPickAction):
        raise WorldActionError("還有閃現的選項沒有選（flash_pick）")
    if (
        char.pending_flash is None
        and char.pending_offers
        and not isinstance(action, OfferPickAction | NarrateAction)
    ):  # 敘述不改數值（只有事件敘述換骨架），三選一待選時也能寫進日誌（5B-5）
        raise WorldActionError("還有任務給的技能三選一沒有選（offer_pick）")
    world, char, ended = expire_threads(library, world, char, now)  # 線頭到期結局（5B-4b）
    before = char
    result = _dispatch(library, world, char, action, now)
    world, char, settled = settle_event_combat(
        library, result.world, before, result.char, result.events, now=now
    )
    events = (*ended, *result.events, *settled)
    char = mark_finished(library, char, events, now=now)  # 只出一次的骨架（5B-4c、5B-4d）
    char = mark_met_opportunities(library, char, events)  # 機遇保底（5B-4d）
    char, extra = advance_quests(library, world, char, events, now)
    char, joined = sync_companions(library, char)  # 劇情夥伴加入／離隊（5C-3）
    extra = [*extra, *joined]
    world, saved = save_after_prep(library, world, char, action, now)  # 城鎮整備存影子（5C-2）
    world, char, paid = after_step(library, world, char, (*events, *extra))  # 任務幣（5D-1）
    if not ended and not settled and not extra and not saved and not paid and char is result.char:
        return result
    return StepResult(world=world, char=char, events=(*events, *extra, *saved, *paid))


def _dispatch(  # noqa: PLR0911 — 動作分派（每類動作一個出口）
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WorldAction,
    now: int,
) -> StepResult:
    if isinstance(action, GROWTH_ACTIONS):
        char, events = apply_growth(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)
    if isinstance(action, TravelAction):
        return _travel(library, world, char, action, now)
    if isinstance(action, CampAction):
        return _camp(library, world, char, now)
    if isinstance(action, FightAction):
        if char.pending_encounter is None:
            raise WorldActionError("目前沒有遭遇")
        world, char, events = fight(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)
    if isinstance(action, SituationAction | NarrateAction):
        return _story(library, world, char, action, now)
    if isinstance(action, AcceptQuestAction | OfferPickAction | TalkAction | TavernAction):
        return _social(library, world, char, action, now)
    if isinstance(action, EventSolveAction):
        world, char, events = solve_event(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)
    if isinstance(action, ECONOMY_ACTIONS):  # 5D-1 買、賣、腰包、用道具
        char, events = apply_economy(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)
    if isinstance(action, EquipAction):  # 5D-2 換裝備
        char, equipped = apply_equip(library, char, action)
        return StepResult(world=world, char=char, events=equipped)
    return _service(library, world, char, action)


def _social(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: AcceptQuestAction | OfferPickAction | TalkAction | TavernAction,
    now: int,
) -> StepResult:
    """任務與聊天（5B-4，:mod:`trpg.world.quests`、:mod:`trpg.world.social`）：不動世界快照。"""
    events: tuple[WorldEvent, ...]
    if isinstance(action, AcceptQuestAction):
        char, events = accept_quest(library, world, char, action, now)
    elif isinstance(action, OfferPickAction):
        char, events = take_offer(library, char, action)
    elif isinstance(action, TalkAction):
        char, events = talk(library, world, char, action, now)
    else:
        events = tavern(library, world, char, now)
    return StepResult(world=world, char=char, events=events)


def _story(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: SituationAction | NarrateAction,
    now: int,
) -> StepResult:
    """事件的情境判定（5B-2）與說書人敘述（5B-3，:mod:`trpg.world.narration`）。"""
    if isinstance(action, SituationAction):
        world, char, events = resolve_situation(library, world, char, action, now)
    else:
        char, events = apply_narration(library, world, char, action, now)
    return StepResult(world=world, char=char, events=events)


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
    elif isinstance(action, HireAction):
        char, events = hire(library, world, char, action)  # 5C-1、5C-2（影子）
    elif isinstance(action, ShadowAiAction):
        char, events = set_shadow_ai(library, char, action)  # 5C-2
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
        result, char = make_encounter(library, world, char, target, now)
        result = result.model_copy(update={"from_location": from_location})
        char = char.model_copy(update={"pending_encounter": result})
        events.append(EncounterEvent(result=result))
    rolled = roll_event(library, world, char, encountered=encountered, now=now)
    char = rolled.char
    events += rolled.events
    char, found = _perceive(library, world, char, world_map, now)
    events += found
    return StepResult(world=world, char=char, events=tuple(events))


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
