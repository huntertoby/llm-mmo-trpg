"""大世界的顯示資料（Phase 5A-5；``docs/phases/Phase5計畫.md`` 10.3）：角色、地點圖、目前地點的
服務、遭遇陣容、時刻與天氣、事件句子。規則一律呼叫 ``trpg.world``，這裡只組裝文字。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

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
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.narrative.skills import SkillCard, skill_card
from trpg.shared.types import Team
from trpg.world.actions import (
    BattleEndedEvent,
    CampedEvent,
    DefeatedEvent,
    EncounterEvent,
    LeveledUpEvent,
    LoadoutChangedEvent,
    LocationClearedEvent,
    LocationRevealedEvent,
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
    thresholds = library.roguelite.level_thresholds
    rules = rules_of(library)
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
    locations = tuple(
        WorldLocationView(
            id=loc.id,
            name_zh=loc.name_zh,
            kind=loc.kind,
            kind_zh=KIND_ZH.get(loc.kind, loc.kind),
            level_zh=_level_zh(loc.level_min, loc.level_max),
            description_zh=loc.description_zh,
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
    if char.pending_encounter is not None:
        return []
    if loc.kind == "town":
        targets = [r for r in char.visited_towns if r != char.region]
    elif loc.kind == "gate" and loc.gate_to is not None:
        targets = [loc.gate_to]
    else:
        return []
    return [r for r in targets if r in library.world_maps]


def _here_view(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int, in_battle: bool
) -> HereView:
    loc = world_map_of(library, char.region).location_by_id()[char.location]
    rules = rules_of(library)
    free = char.pending_encounter is None and not in_battle
    camped = char.camped_at == LocationRef(region=char.region, location=char.location)
    problem = camp_problem(library, world, char, now)
    return HereView(
        location=loc.id,
        name_zh=loc.name_zh,
        kind_zh=KIND_ZH.get(loc.kind, loc.kind),
        description_zh=loc.description_zh,
        can_rest=free and loc.kind == "town",
        can_loadout=free and (loc.kind == "town" or camped),
        camp_problem_zh="戰鬥進行中" if in_battle else problem,
        camped=camped,
        teleports=tuple(
            TeleportOption(region=r, name_zh=_region_name(library, r))
            for r in _teleports(library, char, loc)
        ),
        hasten_cost=rules.hasten.cost,
        camp_cost=rules.camp_cost,
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
    enemies = [u.template for u in prepared.setup.units if u.team is Team.ENEMY]
    affixes = [m.affix for m in prepared.lineup.members]
    views = tuple(
        EncounterEnemyView(
            name_zh=template.name_zh,
            elite=affix is not None or catalog.is_elite(template),
            affix_zh=catalog.affix(affix).name_zh if affix is not None else None,
        )
        for template, affix in zip(enemies, affixes, strict=True)
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
    if isinstance(event, LeveledUpEvent):
        return f"升到 {event.level} 級！（未分配屬性點 {event.attribute_points}）"
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


_LINES = (_move_line, _battle_line, _service_line)


def event_lines(
    library: ContentLibrary, region: str, events: Iterable[WorldEvent]
) -> tuple[str, ...]:
    """世界事件 → 中文句子（``region`` 是事件發生前的區域；傳送後的地點名照事件本身）。"""
    lines: list[str] = []
    for event in events:
        if isinstance(event, TeleportedEvent):
            region = event.region
        for make in _LINES:
            line = make(library, region, event)
            if line is not None:
                lines.append(line)
                break
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
) -> WorldView:
    in_battle = battle_id is not None
    return WorldView(
        character=_character_view(library, char),
        map=_map_view(library, world, char, now, in_battle),
        here=_here_view(library, world, char, now, in_battle),
        encounter=_encounter_view(library, char, in_battle),
        clock=_clock_view(library, world, char.region, now),
        events=events,
        battle_id=battle_id,
    )
