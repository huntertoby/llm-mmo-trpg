"""大世界的顯示資料（Phase 5A-5；``docs/phases/Phase5計畫.md`` 11.3）：角色、地點圖、目前地點的
服務、遭遇陣容、時刻與天氣、事件句子。規則一律呼叫 ``trpg.world``，這裡只組裝文字。

Phase 5A-7（13.2）：成長、誓約、下一場修正、開場說明、最近一次戰鬥
（:mod:`trpg.api.world_growth_view`）。

Phase 5B-5（18.4、18.5）：事件卡、情境判定結果、NPC、對話、任務、三選一、線頭、酒館
（:mod:`trpg.api.world_story_view`）；地點說明在隱藏地點揭露前用提示語。"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Final

from trpg.api.world_crafting_view import (
    crafting_event_line,
    crafting_view,
    resonance_lines,
)
from trpg.api.world_economy_schemas import InventoryView
from trpg.api.world_economy_view import (
    economy_event_line,
    inventory_view,
    last_loot_line,
    shop_view,
    wallet_view,
)
from trpg.api.world_growth_view import (
    growth_event_line,
    growth_view,
    hero_panel,
    hero_status_views,
    last_battle_line,
    next_battle_lines,
    oath_view,
    opening_lines,
    skill_names,
)
from trpg.api.world_party_view import (
    allies_line,
    my_shadow_view,
    party_event_line,
    party_view,
)
from trpg.api.world_schemas import (
    EncounterEnemyView,
    EncounterView,
    HereView,
    TeleportOption,
    WorldCharacterSummary,
    WorldCharacterView,
    WorldClockView,
    WorldLocationView,
    WorldMapView,
    WorldView,
)
from trpg.api.world_story_view import (
    dialog_lines,
    event_view,
    npcs_here,
    pending_offer_view,
    quest_log,
    quests_here,
    rumor_lines,
    situation_result_view,
    story_event_line,
    thread_views,
)
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.content.world_narration import mask_text
from trpg.narrative.skills import SkillCard, skill_card
from trpg.shared.types import Team
from trpg.world.actions import (
    BattleEndedEvent,
    CampedEvent,
    DefeatedEvent,
    EncounterEvent,
    LoadoutChangedEvent,
    LocationClearedEvent,
    LocationRevealedEvent,
    NarrateAction,
    PerceptionCheckEvent,
    RestedEvent,
    RetreatedEvent,
    TeleportedEvent,
    TraveledEvent,
    WorldEvent,
)
from trpg.world.battle import prepare_battle
from trpg.world.clock import day_phase, game_clock
from trpg.world.common import max_hp, max_mana, rules_of, world_map_of
from trpg.world.growth import hero_tier
from trpg.world.narration import story_masks
from trpg.world.state import CharacterState, LocationRef, WorldState
from trpg.world.step import camp_problem
from trpg.world.weather import weather_at

__all__ = [
    "KIND_ZH",
    "character_summary",
    "event_lines",
    "world_view",
]

KIND_ZH: Final[dict[str, str]] = {
    "town": "小鎮",
    "camp": "營地",
    "ruin": "遺跡",
    "altar": "祭壇",
    "anomaly": "異象",
    "caravan": "商隊",
    "village": "村落",
    "secret": "秘境",
    "elite_lair": "精英巢穴",
    "boss": "Boss 據點",
    "gate": "傳送點",
}

PHASE_ZH: Final[dict[str, str]] = {"day": "白天", "night": "夜晚"}

_END_REASON_ZH: Final[dict[str, str]] = {"max_rounds": "輪數用完"}


def _region_name(library: ContentLibrary, region: str) -> str:
    regions = library.regions.region_by_id() if library.regions is not None else {}
    found = regions.get(region)
    return found.name_zh if found is not None else region


def _level_zh(lo: int | None, hi: int | None) -> str | None:
    if lo is None:
        return None
    return f"Lv {lo}" if hi is None or hi == lo else f"Lv {lo}～{hi}"


def _location_name(library: ContentLibrary, region: str, location: str) -> str:
    found = world_map_of(library, region).location_by_id().get(location)
    return found.name_zh if found is not None else location


# ---------------------------------------------------------------------------
# 角色
# ---------------------------------------------------------------------------


def _skill_defs(library: ContentLibrary, char: CharacterState) -> dict[str, SkillDef]:
    return {**library.skills, **{s.id: s for s in char.generated_skills}}


def _cards(
    library: ContentLibrary, char: CharacterState, ids: Iterable[str]
) -> tuple[SkillCard, ...]:
    defs = _skill_defs(library, char)
    return tuple(skill_card(library, defs[s]) for s in ids if s in defs)


def _race_name(library: ContentLibrary, race: str | None) -> str | None:
    table = library.ruleset.races
    if race is None or table is None:
        return None
    return next((r.name_zh for r in table.races if r.id == race), race)


def _slots_zh(library: ContentLibrary) -> str:
    slots = library.ruleset.core.skill_slots
    return f"主動 {slots.active}、被動 {slots.passive}、反應 {slots.reaction}、姿態 {slots.stance}"


def _character_view(library: ContentLibrary, char: CharacterState) -> WorldCharacterView:
    rules = rules_of(library)
    thresholds = rules.hero_growth.level_thresholds
    return WorldCharacterView(
        character_id=char.character_id,
        name=char.hero.name_zh,
        level=char.level,
        xp=char.xp,
        xp_next=thresholds[char.level - 1] if char.level - 1 < len(thresholds) else None,
        hp=char.hp,
        max_hp=max_hp(library, char),
        mana=char.mana,
        max_mana=max_mana(library, char),
        supplies=char.supplies,
        max_supplies=rules.supplies.max,
        fatigued=char.fatigued,
        attribute_points=char.attribute_points,
        weapon_name_zh=library.weapons[char.hero.weapon].name_zh,
        race_name_zh=_race_name(library, char.hero.race),
        skills=_cards(library, char, char.hero.skills),
        bench=_cards(library, char, char.bench),
        slots_zh=_slots_zh(library),
        insight=char.insight,
        skill_tier=char.skill_tier or hero_tier(library, char.level),
    )


def character_summary(library: ContentLibrary, char: CharacterState) -> WorldCharacterSummary:
    return WorldCharacterSummary(
        character_id=char.character_id,
        name=char.hero.name_zh,
        level=char.level,
        region_name_zh=_region_name(library, char.region),
        location_name_zh=_location_name(library, char.region, char.location),
    )


# ---------------------------------------------------------------------------
# 地點圖
# ---------------------------------------------------------------------------


def _visible(char: CharacterState, world_map: LocationMapDef, loc: LocationDef) -> bool:
    return not loc.hidden or char.has_revealed(world_map.region, loc.id)


def _blocked(
    world: WorldState, char: CharacterState, loc: LocationDef, in_battle: bool
) -> str | None:
    if in_battle:
        return "戰鬥進行中"
    if char.pending_encounter is not None:
        return "先處理眼前的遭遇"
    if char.pending_flash is not None:
        return "先選完閃現的變化"
    if char.pending_offers:
        return "先選完任務給的技能"
    if loc.unlock_flag is not None and not world.has_flag(loc.unlock_flag):
        return "還沒開放"
    return None


def _map_view(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int, in_battle: bool
) -> WorldMapView:
    world_map = world_map_of(library, char.region)
    neighbors = set(world_map.neighbors(char.location))
    shown = [loc for loc in world_map.locations if _visible(char, world_map, loc)]
    ids = {loc.id for loc in shown}
    masks = story_masks(library, char)  # 說明文字提到還沒發現的地點時用提示語（5B-5）
    locations = tuple(
        WorldLocationView(
            id=loc.id,
            name_zh=loc.name_zh,
            kind=loc.kind,
            kind_zh=KIND_ZH.get(loc.kind, loc.kind),
            level_zh=_level_zh(loc.level_min, loc.level_max),
            description_zh=mask_text(loc.description_zh, masks),
            x=loc.pos.x,
            y=loc.pos.y,
            current=loc.id == char.location,
            adjacent=loc.id in neighbors,
            blocked_zh=_blocked(world, char, loc, in_battle) if loc.id in neighbors else None,
            cleared=world.is_cleared(char.region, loc.id, now),
            hidden=loc.hidden,
        )
        for loc in shown
    )
    edges = tuple((a, b) for a, b in world_map.edges if a in ids and b in ids)
    return WorldMapView(
        region=world_map.region,
        name_zh=world_map.name_zh,
        level_zh=_level_zh(world_map.level_min, world_map.level_max) or "",
        locations=locations,
        edges=edges,
    )


def _teleports(library: ContentLibrary, char: CharacterState, loc: LocationDef) -> list[str]:
    if char.pending_encounter is not None or char.pending_flash is not None or char.pending_offers:
        return []
    if loc.kind == "town":
        targets = [r for r in char.visited_towns if r != char.region]
    elif loc.kind == "gate" and loc.gate_to is not None:
        targets = [loc.gate_to]
    else:
        return []
    return [r for r in targets if r in library.world_maps]


def _camp_problem(char: CharacterState, problem: str | None, *, in_battle: bool) -> str | None:
    if in_battle:
        return "戰鬥進行中"
    if char.pending_flash is not None:
        return "先選完閃現的變化"
    if char.pending_offers:
        return "先選完任務給的技能"
    return problem


def _here_view(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int, in_battle: bool
) -> HereView:
    loc = world_map_of(library, char.region).location_by_id()[char.location]
    rules = rules_of(library)
    free = (
        char.pending_encounter is None
        and char.pending_flash is None
        and not char.pending_offers
        and not in_battle
    )
    camped = char.camped_at == LocationRef(region=char.region, location=char.location)
    problem = camp_problem(library, world, char, now)
    return HereView(
        location=loc.id,
        name_zh=loc.name_zh,
        kind_zh=KIND_ZH.get(loc.kind, loc.kind),
        description_zh=mask_text(loc.description_zh, story_masks(library, char)),
        can_rest=free and loc.kind == "town",
        can_loadout=free and (loc.kind == "town" or camped),
        camp_problem_zh=_camp_problem(char, problem, in_battle=in_battle),
        camped=camped,
        teleports=tuple(
            TeleportOption(region=r, name_zh=_region_name(library, r))
            for r in _teleports(library, char, loc)
        ),
        hasten_cost=rules.hasten.cost,
        camp_cost=rules.camp_cost,
        can_tavern=free and loc.kind == "town",
    )


# ---------------------------------------------------------------------------
# 遭遇
# ---------------------------------------------------------------------------


def _encounter_view(
    library: ContentLibrary, char: CharacterState, in_battle: bool
) -> EncounterView | None:
    encounter = char.pending_encounter
    if encounter is None:
        return None
    prepared = prepare_battle(library, char)
    catalog = library.enemy_catalog()
    # 敵方在前、第三方（5B-M3）在後；第三方沒有詞綴
    foes = [u for u in prepared.setup.units if u.team is not Team.ALLY]
    affixes = [m.affix for m in prepared.lineup.members] + [None] * len(prepared.lineup.third)
    views = tuple(
        EncounterEnemyView(
            name_zh=spawn.template.name_zh,
            elite=affix is not None or catalog.is_elite(spawn.template),
            affix_zh=catalog.affix(affix).name_zh if affix is not None else None,
            third=spawn.team is Team.THIRD,
        )
        for spawn, affix in zip(foes, affixes, strict=True)
    )
    retreat_to = encounter.from_location or world_map_of(library, encounter.region).town
    return EncounterView(
        location=encounter.location,
        location_name_zh=_location_name(library, encounter.region, encounter.location),
        enemy_level=prepared.enemy_level,
        map_name_zh=prepared.setup.map.name_zh,
        weather_zh=library.weather_def(encounter.weather).name_zh,
        day_phase_zh=PHASE_ZH[encounter.day_phase],
        enemies=views,
        retreat_to_zh=_location_name(library, encounter.region, retreat_to),
        fatigued=char.fatigued,
        hero_hp=prepared.hero_hp,
        in_battle=in_battle,
        reinforcements=prepared.reinforcements,
        first_team=prepared.first_team,
        hero_statuses=hero_status_views(library, prepared.hero_statuses),
        opening_zh=opening_lines(
            library,
            first_team=prepared.first_team,
            hero_statuses=prepared.hero_statuses,
            reinforcements=prepared.reinforcements,
            oath=None if prepared.oath is None else prepared.oath.template,
            oath_bonus=None if prepared.oath is None else prepared.oath.bonus_status,
        ),
        allies_zh=allies_line(library, char, prepared.hero_hp),
    )


def _clock_view(
    library: ContentLibrary, world: WorldState, region: str, now: int
) -> WorldClockView:
    hour, minute = game_clock(now)
    phase = day_phase(now)
    weather = weather_at(library, world, region, now)
    return WorldClockView(
        time_zh=f"{hour:02d}:{minute:02d}",
        day_phase=phase,
        day_phase_zh=PHASE_ZH[phase],
        weather_zh=library.weather_def(weather).name_zh,
    )


# ---------------------------------------------------------------------------
# 事件句子
# ---------------------------------------------------------------------------


def _move_line(library: ContentLibrary, region: str, event: WorldEvent) -> str | None:
    """移動、遇敵、感知判定、發現地點、撤退的句子。"""

    def name(location: str) -> str:
        return _location_name(library, region, location)

    if isinstance(event, TraveledEvent):
        extra = f"（趕路，花 {event.supplies_spent} 補給）" if event.hasten else ""
        return f"走到{name(event.to)}{extra}。"
    if isinstance(event, EncounterEvent):
        return f"在{name(event.result.location)}遇到敵人！"
    if isinstance(event, PerceptionCheckEvent):
        verdict = "成功" if event.success else "失敗"
        total = event.roll + event.modifier
        roll = f"d20={event.roll}＋{event.modifier}＝{total}"
        return f"感知判定（{name(event.location)} 附近）：{roll}，DC {event.dc}，{verdict}。"
    if isinstance(event, LocationRevealedEvent):
        return f"發現了隱藏地點：{name(event.location)}！"
    if isinstance(event, RetreatedEvent):
        return f"撤退回{name(event.to)}。"
    return None


def _battle_line(library: ContentLibrary, region: str, event: WorldEvent) -> str | None:
    """戰鬥結果、升級、全滅、清空的句子。"""
    if isinstance(event, BattleEndedEvent):
        if event.won:
            return f"打贏了（{event.rounds} 輪），獲得 {event.xp_gained} 經驗。"
        reason = _END_REASON_ZH.get(event.end_reason or "", "全滅")
        return f"戰鬥失敗（{reason}）。"
    if isinstance(event, DefeatedEvent):
        town = _location_name(library, region, event.location)
        return f"被抬回{town}，HP 回滿；下一場戰鬥帶「疲憊」。"
    if isinstance(event, LocationClearedEvent):
        return f"{_location_name(library, region, event.location)}已清空，一段時間後敵人才會回來。"
    return None


def _service_line(library: ContentLibrary, region: str, event: WorldEvent) -> str | None:
    """休息、紮營、換技能、傳送的句子。"""
    if isinstance(event, RestedEvent):
        here = _location_name(library, region, event.location)
        return f"在{here}休息：HP、法力回滿，補給 {event.supplies}。"
    if isinstance(event, CampedEvent):
        here = _location_name(library, region, event.location)
        return f"在{here}紮營：HP、法力回滿，剩 {event.supplies_left} 補給。"
    if isinstance(event, LoadoutChangedEvent):
        return f"換好技能：裝備 {len(event.skills)} 招、備用 {len(event.bench)} 招。"
    if isinstance(event, TeleportedEvent):
        return f"傳送到{_region_name(library, event.region)}。"
    return None


_LINES = (
    _move_line,
    _battle_line,
    _service_line,
    party_event_line,
    economy_event_line,
    crafting_event_line,
)


def event_lines(
    library: ContentLibrary,
    region: str,
    events: Iterable[WorldEvent],
    char: CharacterState | None = None,
) -> tuple[str, ...]:
    """世界事件 → 中文句子（``region`` 是事件發生前的區域；傳送後的地點名照事件本身）。``char``
    是事件之後的角色（技能名用；省略時只用內容庫的技能名）。"""
    names = skill_names(library, char) if char is not None else {}
    if char is None:
        names = {k: s.name_zh for k, s in library.skills.items()}
    lines: list[str] = []
    for event in events:
        if isinstance(event, TeleportedEvent):
            region = event.region
        line = next(
            (made for make in _LINES if (made := make(library, region, event)) is not None),
            None,
        )
        if line is None:
            line = growth_event_line(library, event, names)
        if line is None and char is not None:
            line = story_event_line(library, char, event, names)
        if line is not None:
            lines.append(line)
    return tuple(lines)


# ---------------------------------------------------------------------------
# 整份畫面
# ---------------------------------------------------------------------------


def world_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    events: tuple[str, ...] = (),
    battle_id: str | None = None,
    raw_events: Sequence[WorldEvent] = (),
    narrations: Sequence[NarrateAction] = (),
) -> WorldView:
    """``raw_events`` 是這次請求的世界事件（判定結果、對話、傳聞用）；``narrations`` 是目前事件
    觸發之後
    的說書人敘述（事件卡用，5B-5）。"""
    in_battle = battle_id is not None
    hero, pending = hero_panel(library, world, char)
    return WorldView(
        character=_character_view(library, char),
        map=_map_view(library, world, char, now, in_battle),
        here=_here_view(library, world, char, now, in_battle),
        encounter=_encounter_view(library, char, in_battle),
        clock=_clock_view(library, world, char.region, now),
        events=events,
        battle_id=battle_id,
        hero=hero,
        pending_flash=pending,
        growth=growth_view(library, char, in_battle=in_battle),
        oath=oath_view(library, char, now, in_battle=in_battle),
        next_battle_zh=next_battle_lines(library, char.next_battle),
        last_battle_zh=last_battle_line(
            char.last_battle,
            lambda region, loc: _location_name(library, region, loc),
        ),
        last_loot_zh=last_loot_line(library, char.last_battle),
        event=event_view(library, world, char, now, narrations, in_battle=in_battle),
        situation_result=situation_result_view(library, char, raw_events),
        npcs_here=npcs_here(library, char),
        dialog=dialog_lines(library, char, raw_events),
        quests=quest_log(library, char),
        quests_here=quests_here(library, world, char, now),
        pending_offer=pending_offer_view(library, world, char),
        threads=thread_views(library, world, char, now),
        rumors=rumor_lines(library, char, raw_events),
        party=party_view(library, world, char, in_battle=in_battle),
        my_shadow=my_shadow_view(library, world, char, in_battle=in_battle),
        wallet=wallet_view(library, char),
        inventory=_inventory(library, char, in_battle=in_battle),
        shop=shop_view(library, world, char, now, in_battle=in_battle),
        crafting=crafting_view(library, world, char, in_battle=in_battle),
    )


def _inventory(
    library: ContentLibrary, char: CharacterState, *, in_battle: bool
) -> InventoryView | None:
    """背包與腰包，加上目前的共鳴（5D-3）。"""
    view = inventory_view(library, char, in_battle=in_battle)
    lines = resonance_lines(library, char)
    return view if view is None or not lines else view.model_copy(update={"resonance_zh": lines})
