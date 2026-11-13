"""大世界內容（``world/``，Phase 5A 起）的載入與跨檔案檢查。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

from trpg.content.battle import UnitTemplate, WeaponDef
from trpg.content.environment import AiProfileTable, WeatherDef
from trpg.content.equipment import AffixDef
from trpg.content.fields import CAPITAL_REGION, FieldMapDef, FieldMapReport, field_map_report
from trpg.content.library.base import _BaseTables, _load_optional
from trpg.content.library.ruleset import Ruleset
from trpg.content.library.skill_checks import _story_skill_problems
from trpg.content.library.tables import _check_unit_races
from trpg.content.library.unit_checks import _check_units
from trpg.content.loader import load_content_file
from trpg.content.maps import MapDef
from trpg.content.races import RaceTable
from trpg.content.regions import RegionTable
from trpg.content.schemas import ContentModel
from trpg.content.sim_builds import BuildTable
from trpg.content.skills import SkillDef, weapon_problem
from trpg.content.world_address import ADDRESS_FILE, AddressRules, load_world_address
from trpg.content.world_crafting import CraftingRules, load_world_crafting, load_world_resonance
from trpg.content.world_economy import WorldEconomy, load_world_economy
from trpg.content.world_encounters import EncounterTable, encounter_table_problems
from trpg.content.world_enemies import EnemyCatalog, WorldEnemies, world_enemies_problems
from trpg.content.world_events import WorldEventContent, load_world_event_content
from trpg.content.world_loot import LootRules, load_world_loot
from trpg.content.world_map import LocationKind, LocationMapDef, world_map_problems
from trpg.content.world_mercenaries import MercenaryTable
from trpg.content.world_newcomer import NewcomerContent, RangeContent, load_newcomer
from trpg.content.world_oaths import OathTable, OathTemplateDef
from trpg.content.world_quests import WorldQuestContent, load_world_quest_content
from trpg.content.world_rules import WorldRules, world_rules_problems
from trpg.content.world_season import (
    SEASON_FILE,
    SeasonContent,
    season_problems,
    shop_price_problems,
)
from trpg.content.world_trade import TradeRules, load_world_trade
from trpg.shared.errors import ContentError


def _hint_texts(events: WorldEventContent, quests: WorldQuestContent) -> dict[str, tuple[str, ...]]:
    """區域 → 玩家看得到的傳聞文字（酒館傳聞、聊天、線頭；5F-5a 隱藏配方提示的檢查用）。只列聊天
    內容與事件骨架都有的區域（精簡的內容資料夾不檢查）。"""
    found: dict[str, tuple[str, ...]] = {}
    for region in sorted(set(quests.social) & set(events.events)):
        social = quests.social[region]
        skeletons = events.events[region].skeletons
        found[region] = (
            *(r.text_zh for r in social.rumors),
            *(t.text_zh for t in social.talk),
            *(th.text_zh for s in skeletons for th in s.threads),
        )
    return found


@dataclass(frozen=True)
class _WorldBattle:
    """大世界的地點圖、規則、誓約、傭兵、敵人、遭遇與季節（:func:`_load_world_battle` 的結果）。"""

    world_maps: dict[str, LocationMapDef]
    hub_maps: dict[str, LocationMapDef]
    world_rules: WorldRules | None
    world_oaths: OathTable | None
    world_mercenaries: MercenaryTable | None
    world_enemies: WorldEnemies | None
    world_encounters: dict[str, EncounterTable]
    world_season: SeasonContent | None


@dataclass(frozen=True)
class _WorldMarket:
    """大世界的經濟、掉落、製作與交易（:func:`_load_world_market` 的結果）。"""

    world_economy: WorldEconomy
    world_loot: LootRules | None
    world_crafting: CraftingRules | None
    world_trade: TradeRules | None


def _region_npcs(events: WorldEventContent) -> dict[str, dict[str, str]]:
    """區域 → NPC → 所在地點（人設卡）。"""
    return {r: {n.id: n.location for n in e.npcs} for r, e in events.npcs.items()}


def _load_world(
    root: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    *,
    ruleset: Ruleset,
    units: dict[str, UnitTemplate],
    maps: dict[str, MapDef],
    races: RaceTable | None,
    affixes: dict[str, AffixDef],
) -> dict[str, Any]:
    """大世界的內容（Phase 5A 起，``world/``）：回傳 :class:`ContentLibrary` 的 ``world_*``
    欄位。依序載入戰鬥面、事件與任務、經濟面、野外地圖（R1b 拆段；順序即檢查與 ``files`` 的
    登記順序，不可對調）。"""
    battle = _load_world_battle(root, t, files, ruleset=ruleset, units=units, maps=maps)
    keyword_ids = {k.id for k in t.keywords.keywords}
    events, quests = _load_world_story(
        root, t, files, battle, ruleset=ruleset, races=races, keyword_ids=keyword_ids
    )
    _check_unit_races(root, {**units, **{b.id: b.hero for b in t.builds.builds}}, races)
    _check_companions(root, battle.world_mercenaries, t.builds, events, quests)
    market = _load_world_market(
        root,
        t,
        files,
        battle,
        events=events,
        quests=quests,
        ruleset=ruleset,
        units=units,
        affixes=affixes,
        keyword_ids=keyword_ids,
    )
    fields, field_report = _load_world_field_maps(
        root, t, files, battle, events=events, quests=quests
    )
    _check_post_facilities(root, fields, market.world_trade)  # 6T-1b
    return {
        "field_maps": fields,
        "field_warnings": field_report.warnings,
        "field_pending": field_report.pending,
        "world_maps": battle.world_maps,
        "hub_maps": battle.hub_maps,
        "world_rules": battle.world_rules,
        "world_enemies": battle.world_enemies,
        "world_encounters": battle.world_encounters,
        "world_event_content": events,
        "world_quests": quests,
        "world_oaths": battle.world_oaths,
        "world_mercenaries": battle.world_mercenaries,
        "world_economy": market.world_economy,
        "world_loot": market.world_loot,
        "world_trade": market.world_trade,
        "world_address": _load_address(root, files),  # 6R-2（#137）
        "world_crafting": market.world_crafting,
        "world_resonance": load_world_resonance(root, files, affixes=affixes, keywords=keyword_ids),
        "world_season": battle.world_season,
        "world_newcomer": _load_newcomer(
            root,
            battle.world_maps,
            quests,
            files,
            npcs=_region_npcs(events),
            arena=_RangeRefs(t.skills, t.weapons.by_id(), units, maps),
        ),
    }


def _load_world_battle(
    root: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    *,
    ruleset: Ruleset,
    units: dict[str, UnitTemplate],
    maps: dict[str, MapDef],
) -> _WorldBattle:
    """大世界的戰鬥面：地點圖、規則、誓約、傭兵、敵人、遭遇表與季節（5F-1）。"""
    regions, statuses = t.regions, t.statuses
    skills, weapon_map = t.skills, t.weapons.by_id()
    weather_map = t.weather.by_id()
    world_maps, hub_maps = _load_world_maps(root / WORLD_MAPS_DIR, regions, maps, files)
    world_rules = _load_world_rules(root / WORLD_RULES_FILE, regions, weather_map, files)
    world_oaths = _load_world_oaths(
        root / WORLD_OATHS_FILE,
        files,
        status_ids=set(statuses.by_id()),
        tag_ids={tag.id for tag in t.skill_tags.tags},
        element_ids={str(e.id) for e in t.elements.elements},
    )
    world_mercenaries = _load_world_mercenaries(
        root / WORLD_MERCENARIES_FILE, t.builds, t.ai_profiles, files, t.regions
    )
    unit_check = _UnitCheck(root, weapon_map, skills, ruleset, t.ai_profiles)
    world_enemies = _load_world_enemies(root / WORLD_ENEMIES_FILE, units, unit_check, files)
    catalog = _enemy_catalog(units, world_enemies, weapon_map, skills, ruleset)
    world_encounters = _load_world_encounters(
        root / WORLD_ENCOUNTERS_DIR, world_maps, catalog, unit_check, files
    )
    world_season = _load_world_season(  # 5F-1
        root / SEASON_FILE,
        files,
        world_maps=world_maps,
        encounters=world_encounters,
        catalog=catalog,
        weather_ids=set(weather_map),
        region_ids=set() if regions is None else {r.id for r in regions.regions},
        units=set(units),
        maps=maps,
        battle_maps={k: v.archetype for k, v in maps.items()},
        status_ids={s.id for s in statuses.statuses if not s.enemy_only},  # 5F-R1：影子是玩家這邊
    )
    return _WorldBattle(
        world_maps=world_maps,
        hub_maps=hub_maps,
        world_rules=world_rules,
        world_oaths=world_oaths,
        world_mercenaries=world_mercenaries,
        world_enemies=world_enemies,
        world_encounters=world_encounters,
        world_season=world_season,
    )


def _load_world_story(
    root: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    battle: _WorldBattle,
    *,
    ruleset: Ruleset,
    races: RaceTable | None,
    keyword_ids: set[str],
) -> tuple[WorldEventContent, WorldQuestContent]:
    """大世界的事件內容與任務（含聊天、傳聞）。"""
    regions, statuses = t.regions, t.statuses
    world_event_content = load_world_event_content(
        root,
        battle.world_maps,
        t.weather.by_id(),
        files,
        status_ids=statuses.by_id(),
        enemy_only_ids={s.id for s in statuses.statuses if s.enemy_only},  # 06 6.35（5F-R2）
        keyword_ids=keyword_ids,
        race_ids=None if races is None else races.by_id(),
        tone_regions={
            *battle.hub_maps,
            *(() if regions is None else (r.id for r in regions.regions)),
        },
    )
    world_quests = load_world_quest_content(
        root,
        battle.world_maps,
        world_event_content,
        files,
        check_skill=lambda skill: _story_skill_problems(skill, ruleset, t.skills, t.budget),
        keyword_ids=keyword_ids,
    )
    return world_event_content, world_quests


def _load_world_market(
    root: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    battle: _WorldBattle,
    *,
    events: WorldEventContent,
    quests: WorldQuestContent,
    ruleset: Ruleset,
    units: dict[str, UnitTemplate],
    affixes: dict[str, AffixDef],
    keyword_ids: set[str],
) -> _WorldMarket:
    """大世界的經濟面：經濟（5D-1）、商店價格檢查（5F-5b）、掉落（5D-2）、製作（5D-3）、
    交易（6T-1a）。"""
    world_maps, hub_maps, world_enemies = battle.world_maps, battle.hub_maps, battle.world_enemies
    world_economy = load_world_economy(  # 5D-1
        root,
        files,
        regions=set(world_maps),
        npcs_by_region={r: {n.id for n in e.npcs} for r, e in events.npcs.items()},
        check_skill=lambda skill: _story_skill_problems(skill, ruleset, t.skills, t.budget),
    )
    _check_shop_prices(root, battle.world_season, world_economy)  # 5F-5b
    world_loot = load_world_loot(  # 5D-2
        root,
        files,
        regions=set(world_maps),
        units=None if world_enemies is None else {*units, *(v.id for v in world_enemies.variants)},
        affixes=None if world_enemies is None else {a.id for a in world_enemies.affixes},
        items=world_economy.items,
        keywords=keyword_ids,
        gear_affixes=affixes,
    )
    world_crafting = load_world_crafting(  # 5D-3
        root,
        files,
        locations={  # 6D-5：主城的鐵匠鋪也是設施（6D-R2：主城的地點圖在 hub_maps）
            r: {loc.id: loc.kind for loc in m.locations}
            for r, m in sorted({**world_maps, **hub_maps}.items())
        },
        npcs=_region_npcs(events),
        items=world_economy.items,
        affixes=affixes,
        keywords=keyword_ids,
        hint_texts=_hint_texts(events, quests),
    )
    world_trade = load_world_trade(  # 6T-1a：郵差要站在城鎮（含主城）
        root,
        files,
        locations={
            r: {loc.id: loc.kind for loc in m.locations}
            for r, m in sorted({**world_maps, **hub_maps}.items())
        },
    )
    return _WorldMarket(
        world_economy=world_economy,
        world_loot=world_loot,
        world_crafting=world_crafting,
        world_trade=world_trade,
    )


def _load_world_field_maps(
    root: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    battle: _WorldBattle,
    *,
    events: WorldEventContent,
    quests: WorldQuestContent,
) -> tuple[dict[str, FieldMapDef], FieldMapReport]:
    """野外地圖（``world/fields``）：NPC 與任務步驟的引用一併檢查。"""
    return _load_world_fields(
        root / WORLD_FIELDS_DIR,
        t,
        files,
        world_maps=battle.world_maps,
        npcs=_region_npcs(events),
        # 沒有任何任務檔（測試用的精簡內容）＝不檢查出口 gate，和 npcs 缺區不檢查一致
        quest_steps={
            r: {q.id: tuple(s.id for s in q.steps) for q in table.quests}
            for r, table in quests.quests.items()
        }
        or None,
    )


def _load_newcomer(
    root: Path,
    world_maps: Mapping[str, LocationMapDef],
    quests: WorldQuestContent,
    files: list[tuple[Path, ContentModel]],
    *,
    npcs: Mapping[str, Mapping[str, str]] = {},
    arena: _RangeRefs | None = None,
) -> NewcomerContent | None:
    """``world/newcomer.yaml``（6F-2）：新手區要有地點圖；戰鬥短提示的 ID 和任務各步的 ``teach``
    不能撞（畫面用 ID 記「出過了」）；6F-4：``mentor_npc`` 要是新手區的人設卡（``npcs``＝區域 →
    NPC → 地點）。"""
    loaded = load_newcomer(root)
    if loaded is None:
        return None
    path, newcomer = loaded
    problems: list[str] = []
    if newcomer.start_region not in world_maps:
        problems.append(f"start_region {newcomer.start_region} 沒有地點圖")
    region_npcs = npcs.get(newcomer.start_region)
    if (  # 新手區沒有人設卡檔（只裝了部分內容）時不檢查
        newcomer.mentor_npc is not None
        and region_npcs is not None
        and newcomer.mentor_npc not in region_npcs
    ):
        problems.append(f"mentor_npc {newcomer.mentor_npc} 不在 {newcomer.start_region} 的人設卡裡")
    seen = {h.id: "battle_hints" for h in newcomer.battle_hints}
    for region, table in sorted(quests.quests.items()):
        for quest in table.quests:
            for step in quest.steps:
                where = f"{region}/{quest.id}/{step.id}"
                for hint in step.teach:
                    if hint.id in seen:
                        problems.append(f"提示 {hint.id} 重複（{seen[hint.id]}、{where}）")
                    seen[hint.id] = where
    if newcomer.range is not None and arena is not None:
        problems += _range_problems(newcomer.range, arena)
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, newcomer))
    return newcomer


@dataclass(frozen=True)
class _RangeRefs:
    """靶場（TR-1）交叉檢查要看的表。"""

    skills: Mapping[str, SkillDef]
    weapons: Mapping[str, WeaponDef]
    units: Mapping[str, UnitTemplate]
    maps: Mapping[str, MapDef]


def _range_problems(arena: RangeContent, refs: _RangeRefs) -> list[str]:
    """``newcomer.yaml`` 的 ``range``（TR-1，#134）：地圖、木樁、佔位武器要存在；位置在地圖內、
    不重疊；示範招是 1 階主動技、該大類每一把武器都能用（不限定武器）；入門武器（OB-1，#150）存在
    且屬於該大類。"""
    problems: list[str] = []
    for cls, weapon_id in sorted(arena.starters.items()):
        starter = refs.weapons.get(weapon_id)
        if starter is None:
            problems.append(f"range.starters.{cls} 的 {weapon_id} 不存在")
        elif starter.weapon_class != cls or starter.summon_only:
            problems.append(f"range.starters.{cls} 的 {weapon_id} 不是可用的{cls}武器")
    if arena.placeholder_weapon not in refs.weapons:
        problems.append(f"range.placeholder_weapon {arena.placeholder_weapon} 不存在")
    battle_map = refs.maps.get(arena.map)
    if battle_map is None:
        problems.append(f"range.map {arena.map} 不存在")
    problems += [
        f"range.dummies 的 {d.unit} 不存在" for d in arena.dummies if d.unit not in refs.units
    ]
    if battle_map is not None:
        width, height = battle_map.size
        for x, y in (arena.hero_at, *(d.at for d in arena.dummies)):
            if not (0 <= x < width and 0 <= y < height):
                problems.append(f"range 的位置 ({x}, {y}) 在地圖 {arena.map} 外")
    for cls, ids in sorted(arena.demos.items()):
        class_weapons = [w for w in refs.weapons.values() if w.weapon_class == cls]
        for skill_id in ids:
            skill = refs.skills.get(skill_id)
            if skill is None:
                problems.append(f"range.demos.{cls} 的 {skill_id} 不存在")
                continue
            if skill.kind != "active" or skill.tier != 1:
                problems.append(f"range.demos.{cls} 的 {skill_id} 要是 1 階主動技")
            problems += [
                f"range.demos.{cls} 的 {skill_id}：{problem}"
                for w in class_weapons
                if not w.summon_only
                and (problem := weapon_problem(skill, cls, {w.id: w.name_zh})) is not None
            ]
    return problems


WORLD_MAPS_DIR = "world/maps"
"""大世界地點圖的資料夾（相對於內容資料夾；Phase 5A-1）。"""


WORLD_RULES_FILE = "world/rules.yaml"
"""大世界規則的數值（相對於內容資料夾；Phase 5A-2）。"""
WORLD_OATHS_FILE = "world/oaths.yaml"
"""誓約模板（相對於內容資料夾；Phase 5A-6 接點，內容在 5C-3）。"""


WORLD_MERCENARIES_FILE = "world/mercenaries.yaml"
"""系統傭兵名單（相對於內容資料夾；Phase 5C-1）。"""


def _load_world_mercenaries(
    path: Path,
    builds: BuildTable,
    ai_profiles: AiProfileTable,
    files: list[tuple[Path, ContentModel]],
    regions: RegionTable | None = None,
) -> MercenaryTable | None:
    """系統傭兵名單：底稿必須是 ``builds.yaml`` 裡的一般 build（不是白板或對照組）；AI 打法選單
    （5C-2）必須在 ``ai_profiles.yaml``；出身（#131）必須在 ``regions.yaml``（沒有區域表時
    不檢查）。"""
    table = _load_optional(path, MercenaryTable, files)
    if table is None:
        return None
    known = builds.by_id()
    problems = [
        f"傭兵 {m.id} 的底稿 {m.build} 不在 sim/builds.yaml"
        if m.build not in known
        else f"傭兵 {m.id} 的底稿 {m.build} 是白板或對照組"
        for m in table.mercenaries
        if m.build not in known or known[m.build].blank or known[m.build].reference
    ]
    profiles = ai_profiles.by_id()
    problems += [f"AI 打法 {p} 不在 ai_profiles" for p in table.ai_choices if p not in profiles]
    problems += [
        f"夥伴 {c.id} 的 AI 打法 {c.ai_profile} 不在 ai_profiles"
        for c in table.companions
        if c.ai_profile is not None and c.ai_profile not in profiles
    ]
    if regions is not None:
        region_ids = {r.id for r in regions.regions}
        problems += [
            f"傭兵 {m.id} 的出身 {m.origin} 不在 regions.yaml"
            for m in table.mercenaries
            if m.origin is not None and m.origin not in region_ids
        ]
    if problems:
        raise ContentError(path, "；".join(problems))
    return table


def _check_companions(
    root: Path,
    table: MercenaryTable | None,
    builds: BuildTable,
    events: WorldEventContent,
    quests: WorldQuestContent,
) -> None:
    """劇情夥伴（5C-3）：底稿是一般 build、NPC 在人設卡（有人設卡時）；任務的 ``companion`` 在名單裡
    （沒有傭兵名單時不檢查：舊內容資料夾照常載入，夥伴不會加入）。"""
    if table is None:
        return
    known = table.companion_by_id()
    npcs = {n.id for t in events.npcs.values() for n in t.npcs}
    build_map = builds.by_id()
    problems: list[str] = []
    for c in known.values():
        build = build_map.get(c.build)
        if build is None or build.blank or build.reference:
            problems.append(f"劇情夥伴 {c.id} 的底稿 {c.build} 不是 sim/builds.yaml 的一般 build")
        if npcs and c.npc not in npcs:
            problems.append(f"劇情夥伴 {c.id} 的 NPC {c.npc} 不在人設卡")
    if problems:
        raise ContentError(root / WORLD_MERCENARIES_FILE, "；".join(problems))
    for region in sorted(quests.quests):
        bad = [
            f"任務 {q.id} 的劇情夥伴 {q.companion} 不在 world/mercenaries.yaml"
            for q in quests.quests[region].quests
            if q.companion is not None and q.companion not in known
        ]
        if bad:
            raise ContentError(root / "world" / "quests" / f"{region}.yaml", "；".join(bad))


def _load_world_oaths(
    path: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    status_ids: set[str],
    tag_ids: set[str],
    element_ids: set[str],
) -> OathTable | None:
    """誓約模板（5C-3）：每個模板要有判定、參數要有中文名（``choice`` 的每個值也要）；加成與破誓
    狀態、判定引用的標籤、元素與狀態參數的值都要存在。"""
    table = _load_optional(path, OathTable, files)
    if table is None:
        return None
    problems = [
        f"缺少難度 {d} 的加成" for d in ("easy", "medium", "hard") if d not in table.bonuses
    ]
    statuses = [*table.bonuses.values(), *([table.penalty_status] if table.penalty_status else [])]
    problems += [f"未知的狀態 {s}" for s in statuses if s not in status_ids]
    for template in table.templates:
        problems += [f"{template.id}：{p}" for p in _oath_template_problems(template, tag_ids)]
        for param in template.params:
            field = template.bind.get(param.id)
            known = {"element": element_ids, "status": status_ids}.get(field or "")
            if known is not None:
                problems += [
                    f"{template.id}：參數 {param.id} 的值 {v} 不存在"
                    for v in param.choices
                    if v not in known
                ]
    if problems:
        raise ContentError(path, "；".join(problems))
    return table


def _oath_template_problems(template: OathTemplateDef, tag_ids: set[str]) -> list[str]:
    problems: list[str] = []
    if template.check is None:
        problems.append("沒有判定（check）")
    else:
        problems += [f"未知的技能標籤 {t}" for t in template.check.tags if t not in tag_ids]
    for param in template.params:
        if not param.name_zh:
            problems.append(f"參數 {param.id} 沒有中文名")
        missing = [c for c in param.choices if c not in param.choice_names_zh]
        if missing:
            problems.append(f"參數 {param.id} 的值沒有中文名：{', '.join(missing)}")
    return problems


def _season_variants(season: SeasonContent) -> list[tuple[str, SeasonContent]]:
    """預設（標籤空字串）＋每一季套上覆寫後的內容（標籤「seasons.<季 ID>：」；依季 ID 排序）。"""
    return [("", season)] + [
        (f"seasons.{sid}：", season.for_season(sid)) for sid in sorted(season.seasons)
    ]


def _check_post_facilities(
    root: Path, fields: Mapping[str, FieldMapDef], trade: TradeRules | None
) -> None:
    """郵寄設施（6T-1b）：``post`` 只放在有郵差的城鎮的室外圖；每位郵差恰好一格 ``postman``。"""
    problems: list[str] = []
    towns: dict[tuple[str, str | None], str] = (
        {}
        if trade is None
        else {(p.region, p.card.location): p.card.id for p in trade.mail.postmen}
    )
    found: dict[str, int] = {}
    for field_id, fmap in sorted(fields.items()):
        postman = None if fmap.is_interior else towns.get((fmap.region, fmap.location))
        if postman is not None:
            found[postman] = found.get(postman, 0)
        posts = [f for f in fmap.facilities if f.id == "post"]
        if posts and postman is None:
            problems.append(f"實地地圖 {field_id}：post 只能放在有郵差的城鎮室外圖")
        elif postman is not None:
            found[postman] += sum(1 for f in posts if f.postman)
    # 有室外圖的郵差城鎮：郵差要恰好站一格（測試用的精簡內容沒有那張圖就不查）
    problems += [
        f"郵差 {p} 在地圖上有 {n} 個站位（要恰好 1 個）" for p, n in sorted(found.items()) if n != 1
    ]
    if problems:
        raise ContentError(root / WORLD_FIELDS_DIR, "；".join(problems))


def _check_shop_prices(root: Path, season: SeasonContent | None, economy: WorldEconomy) -> None:
    """世界事件的商店價格加成（Phase 5F-5b）指到的商店都要存在；經濟比賽季晚載入，所以另外檢查。"""
    if season is None:
        return
    shop_ids = {shop.id for t in economy.shops.values() for shop in t.shops}
    problems: list[str] = []
    for label, content in _season_variants(season):
        problems += [label + p for p in shop_price_problems(content, shop_ids)]
    if problems:
        raise ContentError(root / SEASON_FILE, "；".join(problems))


def _load_address(root: Path, files: list[tuple[Path, ContentModel]]) -> AddressRules | None:
    """載入 ``world/address.yaml``（6R-2，#137；檔案不存在＝``None``）。"""
    path = root / ADDRESS_FILE
    rules = load_world_address(path)
    if rules is not None:
        files.append((path, rules))
    return rules


def _load_world_season(
    path: Path,
    files: list[tuple[Path, ContentModel]],
    *,
    world_maps: Mapping[str, LocationMapDef],
    encounters: Mapping[str, EncounterTable],
    catalog: EnemyCatalog,
    weather_ids: set[str],
    region_ids: set[str],
    units: set[str],
    maps: Mapping[str, MapDef],
    battle_maps: Mapping[str, str] | None = None,
    status_ids: set[str] | None = None,
) -> SeasonContent | None:
    """載入 ``world/season.yaml``（檔案不存在＝``None``）並做跨檔案檢查（Phase 5F-1）。"""
    if not path.is_file():
        return None
    season = load_content_file(path, SeasonContent)
    problems: list[str] = []
    for label, content in _season_variants(season):  # 預設與每一季的覆寫（5F-R2）都檢查
        found = season_problems(
            content,
            world_maps=world_maps,
            encounters=encounters,
            catalog=catalog,
            weather_ids=weather_ids,
            region_ids=region_ids,
            location_kinds=get_args(LocationKind.__value__),
            units=units,
            maps=maps,
            battle_maps=battle_maps,
            status_ids=status_ids,
        )
        problems += [label + p for p in found]
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, season))
    return season


def _load_world_rules(
    path: Path,
    regions: RegionTable | None,
    weather: Mapping[str, WeatherDef],
    files: list[tuple[Path, ContentModel]],
) -> WorldRules | None:
    """載入 ``world/rules.yaml``（檔案不存在＝``None``）並做跨檔案檢查。"""
    if not path.is_file():
        return None
    rules = load_content_file(path, WorldRules)
    problems = world_rules_problems(rules, regions=regions, weather_ids=weather)
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, rules))
    return rules


def _load_world_maps(
    directory: Path,
    regions: RegionTable | None,
    maps: Mapping[str, MapDef],
    files: list[tuple[Path, ContentModel]],
) -> tuple[dict[str, LocationMapDef], dict[str, LocationMapDef]]:
    """載入 ``world/maps/*.yaml``（鍵＝``region``；資料夾不存在＝空）並做跨檔案檢查。

    地點圖以 ``region`` 而不是 ``id`` 為鍵，所以不用 :func:`_load_dir`；檔名必須等於 ``region``。
    回傳（區域地點圖, 樞紐地點圖）：``hub: true`` 的（主城，6D-R2）另外放，不進區域清單；樞紐目前
    只認主城（``region: capital``），不查 ``regions.yaml``。
    """
    if not directory.is_dir():
        return {}, {}
    result: dict[str, LocationMapDef] = {}
    hubs: dict[str, LocationMapDef] = {}
    for path in sorted(directory.glob("*.yaml")):
        world_map = load_content_file(path, LocationMapDef)
        if world_map.region in result or world_map.region in hubs:
            raise ContentError(path, f"區域 {world_map.region} 已有另一份地點圖")
        if world_map.region != path.stem:
            raise ContentError(path, f"檔名必須與 region 相同（region 為 {world_map.region!r}）")
        if world_map.hub != (world_map.region == CAPITAL_REGION):
            raise ContentError(path, f"只有主城 {CAPITAL_REGION} 的地點圖標 hub: true，而且必須標")
        if not world_map.hub:
            problems = world_map_problems(world_map, regions=regions, maps=maps)
            if problems:
                raise ContentError(path, "；".join(problems))
        files.append((path, world_map))
        (hubs if world_map.hub else result)[world_map.region] = world_map
    return result, hubs


WORLD_FIELDS_DIR = "world/fields"
"""實地地圖的資料夾（相對於內容資料夾；Phase 6B-1）：``<region>/<location>.yaml``，室內圖在
``<region>/interiors/<id>.yaml``。"""


def _load_world_fields(
    directory: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    *,
    world_maps: Mapping[str, LocationMapDef],
    npcs: Mapping[str, Mapping[str, str]],
    quest_steps: Mapping[str, Mapping[str, Sequence[str]]] | None,
) -> tuple[dict[str, FieldMapDef], FieldMapReport]:
    """載入 ``world/fields/``（資料夾不存在＝空）並做跨檔案檢查；錯誤丟 :class:`ContentError`。

    檔名：室外圖＝``location``、室內圖＝``id``；上一層資料夾＝``region``。地圖 ID 全部不重複。
    """
    if not directory.is_dir():
        return {}, FieldMapReport()
    result: dict[str, FieldMapDef] = {}
    paths = sorted(directory.glob("*/*.yaml")) + sorted(directory.glob("*/interiors/*.yaml"))
    for path in paths:
        field_map = load_content_file(path, FieldMapDef)
        interior = path.parent.name == "interiors"
        region_dir = path.parent.parent.name if interior else path.parent.name
        stem = field_map.id if interior else field_map.location
        if field_map.region != region_dir:
            raise ContentError(path, f"資料夾必須與 region 相同（region 為 {field_map.region!r}）")
        if interior != field_map.is_interior or stem != path.stem:
            what = "室內圖放在 interiors/、檔名＝id" if interior else "室外圖的檔名＝location"
            raise ContentError(path, f"檔案位置不對：{what}")
        if field_map.id in result:
            raise ContentError(path, f"實地地圖 ID {field_map.id} 重複")
        files.append((path, field_map))
        result[field_map.id] = field_map
    report = field_map_report(
        result,
        world_maps=world_maps,
        terrain=t.terrain.by_id(),
        objects=t.objects.by_id(),
        core=t.core,
        npcs=npcs,
        quest_steps=quest_steps,
    )
    if report.errors:
        raise ContentError(directory, "；".join(report.errors))
    _check_stele_regions(directory, result, t.regions)
    return result, report


def _check_stele_regions(
    directory: Path, fields: Mapping[str, FieldMapDef], regions: RegionTable | None
) -> None:
    """橋頭石碑的 ``stele_region`` 是 ``regions.yaml`` 的區域（6D-R2；含還沒有地點圖的區）。"""
    known = set() if regions is None else {r.id for r in regions.regions}
    problems = [
        f"實地地圖 {map_id} 的情境物件 {s.id}：stele_region 是未知的區域 {s.stele_region}"
        for map_id in sorted(fields)
        for s in fields[map_id].situation_objects
        if s.stele_region is not None and s.stele_region not in known
    ]
    if problems:
        raise ContentError(directory, "；".join(problems))


WORLD_ENEMIES_FILE = "world/enemies.yaml"
"""大世界敵人的元素變體與精英詞綴（相對於內容資料夾；Phase 5A-3）。"""


WORLD_ENCOUNTERS_DIR = "world/encounters"
"""大世界遭遇表的資料夾（相對於內容資料夾；Phase 5A-3）。"""


@dataclass(frozen=True)
class _UnitCheck:
    """對「載入後才產生的範本」（變體、套詞綴）跑和 ``units/`` 相同的單位檢查。"""

    root: Path
    weapons: dict[str, WeaponDef]
    skills: dict[str, SkillDef]
    ruleset: Ruleset
    ai_profiles: AiProfileTable

    def __call__(self, path: Path, template: UnitTemplate) -> None:
        _check_units(
            self.root,
            {template.id: template},
            weapons=self.weapons,
            skills=self.skills,
            ruleset=self.ruleset,
            ai_profiles=self.ai_profiles,
            source=path,
        )


def _enemy_catalog(
    units: Mapping[str, UnitTemplate],
    enemies: WorldEnemies | None,
    weapons: Mapping[str, WeaponDef],
    skills: Mapping[str, SkillDef],
    ruleset: Ruleset,
) -> EnemyCatalog:
    return EnemyCatalog(
        units=units,
        enemies=enemies,
        weapons=weapons,
        skills=skills,
        slots=ruleset.core.skill_slots,
        default_rules=ruleset.reactions.default_rules,
    )


def _load_world_enemies(
    path: Path,
    units: dict[str, UnitTemplate],
    unit_check: _UnitCheck,
    files: list[tuple[Path, ContentModel]],
) -> WorldEnemies | None:
    """載入 ``world/enemies.yaml``（檔案不存在＝``None``）；變體套用後要通過單位檢查。"""
    if not path.is_file():
        return None
    enemies = load_content_file(path, WorldEnemies)
    problems = world_enemies_problems(
        enemies, units=units, weapons=unit_check.weapons, skills=unit_check.skills
    )
    if problems:
        raise ContentError(path, "；".join(problems))
    catalog = _enemy_catalog(
        units, enemies, unit_check.weapons, unit_check.skills, unit_check.ruleset
    )
    for variant in enemies.variants:
        unit_check(path, catalog.template(variant.id))
    files.append((path, enemies))
    return enemies


def _load_world_encounters(
    directory: Path,
    world_maps: Mapping[str, LocationMapDef],
    catalog: EnemyCatalog,
    unit_check: _UnitCheck,
    files: list[tuple[Path, ContentModel]],
) -> dict[str, EncounterTable]:
    """載入 ``world/encounters/*.yaml``（鍵＝``region``，檔名必須相同；資料夾不存在＝空）。

    除了 :func:`encounter_table_problems`，表裡每個單位套上每個可以套的本區詞綴後，也要通過單位
    檢查（反應規則、欄位上限）。"""
    if not directory.is_dir():
        return {}
    result: dict[str, EncounterTable] = {}
    for path in sorted(directory.glob("*.yaml")):
        table = load_content_file(path, EncounterTable)
        if table.region != path.stem:
            raise ContentError(path, f"檔名必須與 region 相同（region 為 {table.region!r}）")
        problems = encounter_table_problems(
            table, world_map=world_maps.get(table.region), catalog=catalog
        )
        if problems:
            raise ContentError(path, "；".join(problems))
        names = sorted({u for g in table.groups for u in g.units})
        for name in names:
            template = catalog.template(name)
            for affix in catalog.applicable_affixes(template, table.affixes):
                unit_check(path, catalog.with_affix(template, affix))
        files.append((path, table))
        result[table.region] = table
    return result
