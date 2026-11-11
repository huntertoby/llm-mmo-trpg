"""大世界的顯示資料（Phase 5A-5；``docs/phases/Phase5計畫.md`` 11.3）：角色、地點圖、目前地點的
服務、遭遇陣容、時刻與天氣、事件句子。規則一律呼叫 ``trpg.world``，這裡只組裝文字。

Phase 5A-7（13.2）：成長、誓約、下一場修正、開場說明、最近一次戰鬥
（:mod:`trpg.api.world_growth_view`）。

Phase 5B-5（18.4、18.5）：事件卡、情境判定結果、NPC、對話、任務、三選一、線頭、酒館
（:mod:`trpg.api.world_story_view`）；地點說明在隱藏地點揭露前用提示語。"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any, Final

from trpg.api.account_schemas import TitlesOf, no_titles
from trpg.api.league_view import league_event_line
from trpg.api.run_presenter import origin_realm
from trpg.api.season_boss_view import season_boss_event_line
from trpg.api.season_view import season_event_line
from trpg.api.skill_cards import SkillCard, skill_card
from trpg.api.world_atlas_view import atlas_view
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
    pending_loot_view,
    shop_view,
    wallet_view,
)
from trpg.api.world_field_people import look_of
from trpg.api.world_field_things import FieldSocial, things_line
from trpg.api.world_field_view import field_line, field_view
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
from trpg.api.world_mail_view import mail_badge, mail_event_line
from trpg.api.world_newcomer_view import (
    battle_hints,
    guide_view,
    hints_view,
    lesson_view,
    level_up_view,
    with_advice,
    with_routes,
)
from trpg.api.world_party_view import (
    allies_line,
    my_shadow_view,
    party_event_line,
    party_view,
)
from trpg.api.world_range import range_view
from trpg.api.world_region_view import region_marks
from trpg.api.world_schemas import (
    BattlefieldRectView,
    EncounterEnemyView,
    EncounterView,
    EnemyRank,
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
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_enemies import EnemyCatalog
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.content.world_narration import mask_text
from trpg.engine.ids import BOSS_TAG
from trpg.engine.setup import UnitSpawn
from trpg.shared.types import Team
from trpg.world.actions import (
    BattleEndedEvent,
    BattlefieldCut,
    CampedEvent,
    DefeatedEvent,
    EncounterEvent,
    LoadoutChangedEvent,
    LocationClearedEvent,
    LocationRevealedEvent,
    LookChangedEvent,
    NarrateAction,
    OpeningClassChosenEvent,
    OpeningConfirmedEvent,
    OpeningReselectedEvent,
    PerceptionCheckEvent,
    RaceChangedEvent,
    RestedEvent,
    RetreatedEvent,
    TeleportedEvent,
    TraveledEvent,
    WorldEvent,
)
from trpg.world.atlas import can_teleport_to, cross_gate, region_name
from trpg.world.battle import PreparedBattle, prepare_battle
from trpg.world.battlefield import FALLBACK_ZH
from trpg.world.clock import day_phase, game_clock
from trpg.world.common import max_hp, max_mana, rules_of, world_map_of
from trpg.world.field_enemies import cleared_for, personal_left
from trpg.world.gear import hero_loadout
from trpg.world.growth import hero_tier
from trpg.world.looks import look_change_problem
from trpg.world.narration import story_masks
from trpg.world.opening import opening_limits
from trpg.world.race_change import free_race_change_open, race_change_problem
from trpg.world.state import CharacterState, LocationRef, WorldState
from trpg.world.step import camp_problem
from trpg.world.weapon_mix import WEAPON_CLASS_ZH, hero_skills, weapon_class_of
from trpg.world.weather import weather_at


def _reselected_line(library: ContentLibrary, event: OpeningReselectedEvent) -> str:
    weapon = library.weapons.get(event.weapon)
    name = event.weapon if weapon is None else weapon.name_zh
    line = f"重選完成，改拿{name}：起始技能 {'、'.join(event.skill_names)}。"
    if event.returned_names:
        line += f"收回：{'、'.join(event.returned_names)}。"
    if event.lost_zh:
        line += f"一起消失：{'、'.join(event.lost_zh)}。"
    return line


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
    "boss": "頭目據點",
    "gate": "傳送點",
}

PHASE_ZH: Final[dict[str, str]] = {"day": "白天", "night": "夜晚"}

_END_REASON_ZH: Final[dict[str, str]] = {"max_rounds": "輪數用完"}


def _region_name(library: ContentLibrary, region: str) -> str:
    regions = library.regions.region_by_id() if library.regions is not None else {}
    found = regions.get(region)
    if found is None:
        return region_name(library, region)  # 主城（6D-5）
    return found.name_zh


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


def _hero_face(library: ContentLibrary, char: CharacterState) -> dict[str, Any]:
    """主角的 Q 版頭像要用的外觀與出身區（QK-2b；角色清單、HUD 主角卡）。"""
    return {
        "hero_look": look_of(library, char.hero, hero_loadout(library, char)),
        "origin_realm": origin_realm(library, char.origin),
    }


def _slots_zh(library: ContentLibrary) -> str:
    slots = library.ruleset.core.skill_slots
    return f"主動 {slots.active}、被動 {slots.passive}、反應 {slots.reaction}、姿態 {slots.stance}"


def _character_view(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> WorldCharacterView:
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
        race=char.hero.race,
        look=None if char.hero.doll is None else char.hero.doll.custom,
        look_change_zh=look_change_problem(world, char),
        **_weapon_blocked(library, char),
        **_race_change(library, world, char),
        **_hero_face(library, char),
    )


def _race_change(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> dict[str, Any]:
    """這一季的免費換種族（6R-1，#138）：開放、還沒用過時給 ``free_race_change``；不在主城等
    原因放 ``free_race_change_zh``（按鈕灰掉時的說明）。"""
    if not free_race_change_open(library, world) or char.free_race_change_used:
        return {}
    return {
        "free_race_change": True,
        # OB-5（#150 第 7 點）：正式選定前不能換種族——先標原因（同動作被拒的那一句）
        "free_race_change_zh": opening_limits(char).get("race")
        or race_change_problem(library, world, char, None),
    }


def _weapon_blocked(library: ContentLibrary, char: CharacterState) -> dict[str, Any]:
    """主手別大類時暫時不能用的技能（6T-1b）。"""
    usable = set(hero_skills(library, char))
    blocked = tuple(s for s in char.hero.skills if s not in usable)
    if not blocked:
        return {}
    defs = _skill_defs(library, char)
    names = "、".join(f"〈{defs[s].name_zh}〉" if s in defs else s for s in blocked)
    class_zh = WEAPON_CLASS_ZH[weapon_class_of(library, char)]
    text = f"主手是{class_zh}武器：{names}暫時不能用"
    return {"weapon_blocked": blocked, "weapon_blocked_zh": text}


def character_summary(library: ContentLibrary, char: CharacterState) -> WorldCharacterSummary:
    return WorldCharacterSummary(
        character_id=char.character_id,
        name=char.hero.name_zh,
        level=char.level,
        region_name_zh=_region_name(library, char.region),
        location_name_zh=_location_name(library, char.region, char.location),
        **_hero_face(library, char),
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
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    in_battle: bool,
    social: FieldSocial | None = None,
    region: str | None = None,
) -> WorldMapView:
    """所在區的地點圖；``region`` 是別區時（6D-5 大世界圖點進去看）：沒有目前位置與相鄰。"""
    region = char.region if region is None else region
    world_map = world_map_of(library, region)
    here = region == char.region
    neighbors = set(world_map.neighbors(char.location)) if here else set()
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
            current=here and loc.id == char.location,
            adjacent=loc.id in neighbors,
            blocked_zh=_blocked(world, char, loc, in_battle) if loc.id in neighbors else None,
            cleared=cleared_for(library, world, char, (region, loc.id), now),  # 6F-3
            hidden=loc.hidden,
        )
        for loc in shown
    )
    edges = tuple((a, b) for a, b in world_map.edges if a in ids and b in ids)
    view = WorldMapView(
        region=world_map.region,
        name_zh=world_map.name_zh,
        level_zh=_level_zh(world_map.level_min, world_map.level_max) or "",
        hub=world_map.hub,
        locations=locations,
        edges=edges,
    )
    return region_marks(  # 6C-6；足跡 6C-5
        library, char, view, town=world_map.town, in_battle=in_battle, social=social
    )


def _teleports(library: ContentLibrary, char: CharacterState, loc: LocationDef) -> list[str]:
    if char.pending_encounter is not None or char.pending_flash is not None or char.pending_offers:
        return []
    if loc.kind == "town":  # 6D-5：主城一開始就能去；其他區要在大世界圖上亮起
        lit = [r for r in sorted(library.world_maps) if can_teleport_to(library, char, r)]
        targets = [r for r in (CAPITAL_REGION, *lit) if r != char.region]
    elif loc.kind == "gate" and loc.gate_to is not None:
        if cross_gate(library, char.region, char.location):  # 6D-5：要走到渡口盡頭的出口過去
            return []
        targets = [loc.gate_to]
    else:
        return []
    return [r for r in targets if library.location_map(r) is not None or r == CAPITAL_REGION]


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
        can_loadout=free
        and (loc.kind == "town" or camped)
        and "loadout" not in opening_limits(char),  # OB-5：入門期不能換技能
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


type PrepareBattle = Callable[[CharacterState], PreparedBattle]
"""畫面用的 ``prepare_battle``（6C-R3：伺服器傳快取過的版本，
:meth:`~trpg.api.world.WorldStore.prepared_battle`）。"""


def _encounter_enemy(
    library: ContentLibrary, catalog: EnemyCatalog, spawn: UnitSpawn, affix: str | None
) -> EncounterEnemyView:
    """遇敵卡的一名敵人；``rank``、``look``（UI-E3b）只給畫面畫頭像與金環，不影響規則。外觀照
    開戰時的範本（已套精英詞綴）與裝備，和戰鬥的 ``UnitView`` 一致。"""
    elite = affix is not None or catalog.is_elite(spawn.template)
    rank: EnemyRank = "boss" if BOSS_TAG in spawn.template.tags else "elite" if elite else "normal"
    return EncounterEnemyView(
        name_zh=spawn.template.name_zh,
        elite=elite,
        affix_zh=catalog.affix(affix).name_zh if affix is not None else None,
        third=spawn.team is Team.THIRD,
        rank=rank,
        look=look_of(library, spawn.template, spawn.equipment),
    )


def _encounter_view(
    library: ContentLibrary,
    char: CharacterState,
    in_battle: bool,
    prepare: PrepareBattle | None = None,
) -> EncounterView | None:
    encounter = char.pending_encounter
    if encounter is None:
        return None
    prepared = prepare_battle(library, char) if prepare is None else prepare(char)
    catalog = library.enemy_catalog()
    # 敵方在前、第三方（5B-M3）在後；第三方沒有詞綴
    foes = [u for u in prepared.setup.units if u.team is not Team.ALLY]
    affixes = [m.affix for m in prepared.lineup.members] + [None] * len(prepared.lineup.third)
    views = tuple(
        _encounter_enemy(library, catalog, spawn, affix)
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
        battlefield=_battlefield_view(prepared.field_cut),
        battlefield_fallback_zh=(
            None if prepared.cut_fallback is None else FALLBACK_ZH[prepared.cut_fallback]
        ),
    )


def _battlefield_view(cut: BattlefieldCut | None) -> BattlefieldRectView | None:
    """切出來的戰場（6C-2）在實地地圖上的範圍。"""
    if cut is None:
        return None
    return BattlefieldRectView(
        field_map=cut.field_map, x=cut.x, y=cut.y, width=cut.width, height=cut.height
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
        return f"被抬回{town}，HP、法力回滿；下一場戰鬥帶「疲憊」。"
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
    return _looks_line(library, event)


def _looks_line(library: ContentLibrary, event: WorldEvent) -> str | None:
    """換種族（6R-1，#138）、改外觀（6R-2，#137）的句子。"""
    if isinstance(event, RaceChangedEvent):
        old = _race_name(library, event.from_race) or "沒有種族"
        new = _race_name(library, event.to_race) or event.to_race
        free = "（這一季的免費換種族）" if event.free else ""
        return f"種族從{old}換成{new}{free}。"
    if isinstance(event, LookChangedEvent):
        return "外觀換好了。" if event.look is not None else "外觀回到種族預設。"
    if isinstance(event, OpeningConfirmedEvent):  # TR-1（#134）
        weapon = library.weapons.get(event.weapon)
        name = event.weapon if weapon is None else weapon.name_zh
        return f"帶著{name}出發：起始技能 {'、'.join(event.skill_names)}。"
    if isinstance(event, OpeningClassChosenEvent):  # OB-1（#150）
        weapon = library.weapons.get(event.weapon)
        name = event.weapon if weapon is None else weapon.name_zh
        return f"先帶著入門的{name}上路：入門招 {'、'.join(event.skill_names)}。"
    if isinstance(event, OpeningReselectedEvent):  # OB-3（#150 第 5 點）
        return _reselected_line(library, event)
    return None


_LINES = (
    _move_line,
    _battle_line,
    _service_line,
    party_event_line,
    economy_event_line,
    crafting_event_line,
    season_event_line,  # 5F-1
    season_boss_event_line,  # 5F-3
    league_event_line,  # 5F-4
    field_line,  # 6B-2
    things_line,  # 6C-5
    lambda library, _region, event: mail_event_line(library, event),  # 6T-1a
)


def _cleared_but_left(
    library: ContentLibrary,
    region: str,
    event: WorldEvent,
    char: CharacterState | None,
    now: int | None,
) -> str | None:
    """「已清空」事件、但這個角色在那裡還有個人隊伍（:func:`personal_left`，6F-3 巡檢 bug 2）：
    回傳那個地點；其他＝``None``。"""
    if not isinstance(event, LocationClearedEvent) or char is None or now is None:
        return None
    return event.location if personal_left(library, char, region, event.location, now) else None


def event_lines(
    library: ContentLibrary,
    region: str,
    events: Iterable[WorldEvent],
    char: CharacterState | None = None,
    now: int | None = None,
) -> tuple[str, ...]:
    """世界事件 → 中文句子（``region`` 是事件發生前的區域；傳送後的地點名照事件本身）。``char``
    是事件之後的角色（技能名用；省略時只用內容庫的技能名）。``now`` 有給時，共享隊伍打完、但
    角色還有個人隊伍的地點不說「已清空」（6F-3）。"""
    names = skill_names(library, char) if char is not None else {}
    if char is None:
        names = {k: s.name_zh for k, s in library.skills.items()}
    lines: list[str] = []
    for event in events:
        if isinstance(event, TeleportedEvent):
            region = event.region
        left = _cleared_but_left(library, region, event, char, now)
        if left is not None:
            lines.append(f"這一隊打散了，但{_location_name(library, region, left)}還有別的敵群。")
            continue
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
    titles: TitlesOf = no_titles,
    social: FieldSocial | None = None,
    prepare: PrepareBattle | None = None,
    inline_tiles: bool = True,
) -> WorldView:
    """``raw_events`` 是這次請求的世界事件（判定結果、對話、傳聞用）；``narrations`` 是目前事件
    觸發之後
    的說書人敘述（事件卡用，5B-5）；``titles`` 是影子主人的帳號稱號（名片，5F-3c）；``social`` 是
    其他角色的足跡與地點留言數（6C-5；省略＝不畫）。``prepare`` 是遭遇面板用的 ``prepare_battle``
    （6C-R3 伺服器傳快取版）；``inline_tiles`` 為假時實地地圖不帶地形（6C-R3，前端依雜湊另外
    取）。"""
    in_battle = battle_id is not None
    hero, pending = hero_panel(library, world, char)
    limits = opening_limits(char)  # OB-5（#150 第 7、9 點）
    if "flash" in limits:
        # 開局還沒結束、4 級前不能閃現：每一招的閃現鈕都先標成不可用（原因同動作被拒的那一句）
        blocked = {"can_flash": False, "flash_problem_zh": limits["flash"]}
        hero = hero.model_copy(
            update={"flash": tuple(f.model_copy(update=blocked) for f in hero.flash)}
        )
    return WorldView(
        character=_character_view(library, world, char),
        map=_map_view(library, world, char, now, in_battle=in_battle, social=social),
        here=_here_view(library, world, char, now, in_battle),
        encounter=_encounter_view(library, char, in_battle, prepare),
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
        pending_loot=pending_loot_view(library, char),
        event=event_view(library, world, char, now, narrations, in_battle=in_battle),
        situation_result=situation_result_view(library, char, raw_events),
        npcs_here=npcs_here(library, char),
        dialog=dialog_lines(library, char, raw_events),
        quests=with_routes(library, char, quest_log(library, char)),  # 6F-2：方向、建議
        quests_here=with_advice(library, char, quests_here(library, world, char, now)),
        pending_offer=pending_offer_view(library, world, char),
        threads=thread_views(library, world, char, now),
        rumors=rumor_lines(library, char, raw_events),
        party=party_view(library, world, char, in_battle=in_battle, titles=titles),
        my_shadow=my_shadow_view(library, world, char, in_battle=in_battle),
        wallet=wallet_view(library, char),
        inventory=_inventory(library, char, in_battle=in_battle),
        shop=shop_view(library, world, char, now, in_battle=in_battle),
        crafting=crafting_view(library, world, char, in_battle=in_battle),
        field=field_view(
            library, char, world=world, now=now, social=social, inline_tiles=inline_tiles
        ),
        atlas=atlas_view(
            library,
            world,
            char,
            in_battle=in_battle,
            region_map=lambda r: _map_view(
                library, world, char, now, in_battle=in_battle, social=social, region=r
            ),
        ),
        guide=guide_view(library, char),  # 6F-2（#125、U2）
        battle_hints=battle_hints(library, char) if in_battle else (),  # 6F-2（#99、U1）
        lesson=None if in_battle else lesson_view(library, char),  # 6F-2（#132）、6F-4（#133）
        level_up=None if in_battle else level_up_view(library, char),  # 6F-4（C2）
        hints=hints_view(char),  # 6F-4（6F-2b）
        mail=mail_badge(library, world, char, now),  # 6T-1a：郵差頭上的「✉」
        opening=range_view(library, char),  # TR-1（#134）：未完成開局＝停在工坊靶場
        limits=limits,
    )


def _inventory(
    library: ContentLibrary, char: CharacterState, *, in_battle: bool
) -> InventoryView | None:
    """背包與腰包，加上目前的共鳴（5D-3）。"""
    view = inventory_view(library, char, in_battle=in_battle)
    lines = resonance_lines(library, char)
    return view if view is None or not lines else view.model_copy(update={"resonance_zh": lines})
