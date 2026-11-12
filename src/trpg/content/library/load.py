"""載入入口 :func:`load_library`：依序載入基礎表、規則包、裝備、單位、地圖、大世界
與一輪附屬內容。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from trpg.content.affix_names import resolve_affix_names
from trpg.content.appearance import AppearanceTable
from trpg.content.battle import OffhandTable, StatusTable, TerrainTable, UnitTemplate, WeaponTable
from trpg.content.composer_rules import ComposerRules
from trpg.content.dev_starters import DevStarterTable
from trpg.content.environment import (
    AiProfileTable,
    InteractionTable,
    ObjectTable,
    ReactionTable,
    SurfaceTable,
    WeatherTable,
)
from trpg.content.equipment import (
    AffixDef,
    AffixTable,
    EquipmentRules,
    ItemDef,
    ItemTable,
    item_problems,
)
from trpg.content.forms import FormTable
from trpg.content.item_budget import ItemGenRules
from trpg.content.library.base import _BaseTables, _load_dir, _Loader
from trpg.content.library.container import ContentLibrary, skill_name_problems
from trpg.content.library.gear_checks import (
    _check_affixes,
    _check_appearance,
    _check_item_gen,
    _GearCatalog,
)
from trpg.content.library.ruleset import Ruleset
from trpg.content.library.skill_checks import (
    _check_keywords,
    _check_skill_rules,
    _check_skills,
    icon_prop_problems,
    pool_region_problems,
)
from trpg.content.library.tables import (
    _check_evolution,
    _check_modifier_changes,
    _check_scaling,
    _dev_starter_problems,
    _load_flash,
    _load_races,
    _load_summons,
)
from trpg.content.library.unit_checks import (
    _check_builds,
    _check_unit_phases,
    _check_units,
    _map_phase_tile_problems,
    _map_reference_problems,
)
from trpg.content.library.world import _load_world
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.maps import MapDef, check_map
from trpg.content.modifier_changes import MODIFIER_CHANGES_FILE, ModifierChangeTable
from trpg.content.races import RaceTable
from trpg.content.regions import RegionTable, sanitize_map_theme
from trpg.content.roguelite import RunRules, roguelite_problems
from trpg.content.rule_changes import RuleChangeTable
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_icon_props import IconPropTable
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skill_rules import BudgetRules, ExclusionTable, SkeletonDef, SynergyTable
from trpg.content.skill_scaling import SkillScalingRules
from trpg.content.skill_tags import SkillTagTable
from trpg.content.skill_triggers import SkillTriggerTable
from trpg.content.skills import ConditionTable, PrimitiveTable, ShapeTable, SkillDef, SkillTable
from trpg.content.stacks import StackTable
from trpg.content.whiteboard_exploit import exploit_problems
from trpg.content.workshop import WorkshopRules, WorkshopTextTable, workshop_problems
from trpg.shared.errors import ContentError

_LOG = logging.getLogger("trpg.content.library")


def _apply_map_themes(maps: dict[str, MapDef], regions: RegionTable | None) -> list[str]:
    """把區域表套到每張地圖（丟掉未知的 ``region``／``look``，併入區域預設）；回傳警告。"""
    warnings: list[str] = []
    if regions is not None:
        for map_id in sorted(maps):
            maps[map_id], found = sanitize_map_theme(maps[map_id], regions)
            warnings += found
    for warning in warnings:
        _LOG.warning(warning)
    return warnings


def _load_base_tables(
    root: Path, load: _Loader, files: list[tuple[Path, ContentModel]]
) -> _BaseTables:
    """依固定順序讀第一批表（順序＝``files`` 的順序與第一個報錯的檔）。"""
    elements = load("elements.yaml", ElementTable)
    core = load("rules/core.yaml", CoreRules)
    hit_table = load("rules/hit_table.yaml", HitTable)
    terrain = load("terrain.yaml", TerrainTable)
    weapons = load("weapons.yaml", WeaponTable)
    offhands = load("offhands.yaml", OffhandTable)
    statuses = load("statuses.yaml", StatusTable)
    objects = load("objects.yaml", ObjectTable)
    surfaces = load("surfaces.yaml", SurfaceTable)
    interactions = load("interactions.yaml", InteractionTable)
    reactions = load("reactions.yaml", ReactionTable)
    weather = load("weather.yaml", WeatherTable)
    ai_profiles = load("ai_profiles.yaml", AiProfileTable)
    shapes = load("skill_shapes.yaml", ShapeTable)
    primitives = load("skill_primitives.yaml", PrimitiveTable)
    conditions = load("skill_conditions.yaml", ConditionTable)
    skill_triggers = load("skill_triggers.yaml", SkillTriggerTable)
    stacks = load("stacks.yaml", StackTable)
    budget = load("skill_budget.yaml", BudgetRules)
    modifier_changes = load(MODIFIER_CHANGES_FILE, ModifierChangeTable)
    _check_modifier_changes(root, modifier_changes, budget)
    composer = load("skill_composer.yaml", ComposerRules)
    builds = load("sim/builds.yaml", BuildTable)
    synergies = load("skill_synergies.yaml", SynergyTable)
    keywords = load("skill_keywords.yaml", KeywordTable)
    exclusions = load("skill_exclusions.yaml", ExclusionTable)
    skill_tags = load("skill_tags.yaml", SkillTagTable)
    skeletons = _load_dir(root / "skeletons", SkeletonDef, files)
    skills = _load_dir(root / "skills", SkillDef, files)
    summons = _load_summons(root, weapons.by_id(), files)
    return _BaseTables(
        elements=elements,
        core=core,
        hit_table=hit_table,
        terrain=terrain,
        weapons=weapons,
        offhands=offhands,
        statuses=statuses,
        objects=objects,
        surfaces=surfaces,
        interactions=interactions,
        reactions=reactions,
        weather=weather,
        ai_profiles=ai_profiles,
        shapes=shapes,
        primitives=primitives,
        conditions=conditions,
        skill_triggers=skill_triggers,
        stacks=stacks,
        budget=budget,
        modifier_changes=modifier_changes,
        composer=composer,
        builds=builds,
        synergies=synergies,
        keywords=keywords,
        exclusions=exclusions,
        skill_tags=skill_tags,
        skeletons=skeletons,
        skills=skills,
        summons=summons,
        rule_changes=load("rule_changes.yaml", RuleChangeTable),
        forms=load("forms.yaml", FormTable),
        roguelite=load("roguelite.yaml", RunRules),
        workshop=load("workshop.yaml", WorkshopRules),
        workshop_text=load("workshop_text.yaml", WorkshopTextTable),
        equipment_rules=load("rules/equipment.yaml", EquipmentRules),
        affix_table=load("affixes.yaml", AffixTable),
        item_table=load("items.yaml", ItemTable),
        appearance=load("equipment/appearance.yaml", AppearanceTable),
        item_gen=load("item_gen.yaml", ItemGenRules),
        regions=load("regions.yaml", RegionTable) if (root / "regions.yaml").exists() else None,
    )


def _build_ruleset(root: Path, t: _BaseTables, races: RaceTable | None) -> Ruleset:
    """組出戰鬥規則包（引擎用的整包規則；錯誤指向 ``rules/``）。"""
    try:
        return Ruleset(
            core=t.core,
            hit_table=t.hit_table,
            terrain=t.terrain,
            statuses=t.statuses,
            objects=t.objects,
            surfaces=t.surfaces,
            interactions=t.interactions,
            reactions=t.reactions,
            shapes=t.shapes,
            primitives=t.primitives,
            conditions=t.conditions,
            skill_triggers=t.skill_triggers,
            stacks=t.stacks,
            skills=SkillTable(skills=tuple(t.skills[k] for k in sorted(t.skills))),
            summons=t.summons,
            forms=t.forms,
            rule_changes=t.rule_changes,
            races=races,
            equipment=t.equipment_rules,
            keywords=t.keywords,
            skill_tags=t.skill_tags,
            gear_names={
                **{w.id: w.name_zh for w in t.weapons.weapons},
                **{o.id: o.name_zh for o in t.offhands.offhands},
            },
        )
    except ValueError as exc:
        raise ContentError(root / "rules", str(exc)) from exc


def _load_gear(
    root: Path, t: _BaseTables, ruleset: Ruleset
) -> tuple[dict[str, AffixDef], dict[str, ItemDef], _GearCatalog]:
    """詞條（文字代入後）、物品（副手解析後）與裝備目錄；並檢查物品、外觀、物品生成。"""
    affixes = t.affix_table.by_id()
    offhand_map = t.offhands.by_id()
    items = {
        i.id: i
        if i.offhand is None
        else i.model_copy(update={"offhand_def": offhand_map.get(i.offhand)})
        for i in t.item_table.items
    }
    weapon_map = t.weapons.by_id()
    _check_affixes(root, affixes, ruleset, weapon_map)
    try:  # 詞條文字的欄位代入（Phase 3-41a）：數字與名稱從資料填，不寫死在 name_zh
        affixes = resolve_affix_names(affixes, ruleset)
    except (ValueError, KeyError) as exc:
        raise ContentError(root / "affixes.yaml", str(exc)) from exc
    for item in t.item_table.items:
        problems = item_problems(item, affixes, weapon_map, t.equipment_rules, offhand_map)
        if problems:
            raise ContentError(root / "items.yaml", "；".join(problems))
    _check_appearance(root, t.appearance, t.item_table, t.keywords)
    _check_item_gen(root, t.item_gen, affixes)
    return affixes, items, _GearCatalog(items=items, affixes=affixes, rules=t.equipment_rules)


def _load_units(
    root: Path,
    t: _BaseTables,
    ruleset: Ruleset,
    gear: _GearCatalog,
    files: list[tuple[Path, ContentModel]],
) -> dict[str, UnitTemplate]:
    """技能與 AI 設定的檢查，再讀 ``units/`` 並檢查單位、召喚物與模擬用 build。"""
    weapon_map = t.weapons.by_id()
    skills = t.skills
    _check_skills(root, skills, ruleset, t.budget, weapons=weapon_map, offhands=t.offhands.by_id())
    _check_skill_rules(root, ruleset, t.exclusions, t.skeletons)
    _check_keywords(root, t.keywords, ruleset, skills)
    unknown_values = sorted(set(t.ai_profiles.status_values) - {s.id for s in t.statuses.statuses})
    if unknown_values:
        raise ContentError(
            root / "ai_profiles.yaml",
            f"status_values 引用了未知的狀態：{', '.join(unknown_values)}",
        )
    units = _load_dir(root / "units", UnitTemplate, files)
    stray = sorted(k for k, u in units.items() if u.summon)
    if stray:
        raise ContentError(root / "units", f"召喚物範本要放在 units/summons/：{', '.join(stray)}")
    checks: dict[str, Any] = {
        "weapons": weapon_map,
        "skills": skills,
        "ruleset": ruleset,
        "ai_profiles": t.ai_profiles,
    }
    _check_units(root, units, gear=gear, **checks)
    summons = {s.id: s.template for s in t.summons.summons}
    _check_units(root, summons, source=root / "units" / "summons", **checks)
    _check_builds(root, t.builds, units, gear=gear, **checks)
    return units


def _load_maps(
    root: Path,
    t: _BaseTables,
    files: list[tuple[Path, ContentModel]],
    *,
    units: dict[str, UnitTemplate],
    ruleset: Ruleset,
    gear: _GearCatalog,
) -> dict[str, MapDef]:
    """讀 ``maps/``；先檢查 Boss 階段（Phase 5F-2），再逐張檢查地圖。"""
    maps = _load_dir(root / "maps", MapDef, files)
    terrain_map = t.terrain.by_id()
    weather_map = t.weather.by_id()
    _check_unit_phases(  # Boss 階段（Phase 5F-2）
        root,
        units,
        weapons=t.weapons.by_id(),
        skills=t.skills,
        ruleset=ruleset,
        ai_profiles=t.ai_profiles,
        weather=weather_map,
        gear=gear,
    )
    for map_id, map_def in maps.items():
        problems = check_map(map_def, terrain_map, t.core, t.objects.by_id())
        problems += _map_reference_problems(map_def, units, weather_map)
        problems += _map_phase_tile_problems(map_def, units)
        if problems:
            raise ContentError(root / "maps" / f"{map_id}.yaml", "；".join(problems))
    return maps


def _load_run_extras(
    root: Path,
    t: _BaseTables,
    load: _Loader,
    *,
    maps: dict[str, MapDef],
    units: dict[str, UnitTemplate],
) -> dict[str, Any]:
    """一輪（roguelite）與工作坊的檢查、開發用起始包、技能演化、閃現與技能成長（回傳
    :class:`ContentLibrary` 的對應欄位）。"""
    problems = roguelite_problems(t.roguelite, maps, units, t.core.tier_budget)
    if problems:
        raise ContentError(root / "roguelite.yaml", "；".join(problems))
    problems = workshop_problems(t.workshop, maps, units)
    if problems:
        raise ContentError(root / "workshop.yaml", "；".join(problems))
    weapon_map = t.weapons.by_id()
    dev_starters = DevStarterTable()
    if (root / "dev_starters.yaml").exists():
        dev_starters = load("dev_starters.yaml", DevStarterTable)
        problems = _dev_starter_problems(dev_starters, weapon_map, t.keywords, t.skills)
        if problems:
            raise ContentError(root / "dev_starters.yaml", "；".join(problems))
    has_evolution = (root / "skill_evolution.yaml").exists()
    evolution = load("skill_evolution.yaml", EvolutionTable) if has_evolution else EvolutionTable()
    _check_evolution(root, evolution, t.keywords, t.skeletons)
    flash = _load_flash(root, load, evolution, t.skill_triggers)
    skill_scaling = load("skill_scaling.yaml", SkillScalingRules)
    _check_scaling(root, skill_scaling, t.skills, weapon_map)
    return {
        "dev_starters": dev_starters,
        "evolution": evolution,
        "flash": flash,
        "skill_scaling": skill_scaling,
    }


def load_library(
    content_dir: Path | None = None,
) -> ContentLibrary:
    """載入並交叉驗證 ``content/`` 下全部戰鬥內容；任何問題都拋出 :class:`ContentError`。

    步驟（5F-R2 拆成小函式，順序不變）：第一批表 → 種族與出身 → 規則包 → 詞條與物品 → 技能與單位
    → 地圖 → 大世界 → 一輪與其他。"""
    root = default_content_dir() if content_dir is None else content_dir
    files: list[tuple[Path, ContentModel]] = []

    def load[M: ContentModel](rel: str, model: type[M]) -> M:
        path = root / rel
        item = load_content_file(path, model)
        files.append((path, item))
        return item

    t = _load_base_tables(root, load, files)
    races, origins = _load_races(
        root,
        load,
        t.regions,
        shapes=t.shapes.by_id(),
        weather=t.weather.by_id(),
        terrain=t.terrain.by_id(),
        summons=frozenset(s.id for s in t.summons.summons),
    )
    ruleset = _build_ruleset(root, t, races)
    affixes, items, gear = _load_gear(root, t, ruleset)
    units = _load_units(root, t, ruleset, gear, files)
    maps = _load_maps(root, t, files, units=units, ruleset=ruleset, gear=gear)
    map_warnings = _apply_map_themes(maps, t.regions)
    world = _load_world(
        root, t, files, ruleset=ruleset, units=units, maps=maps, races=races, affixes=affixes
    )
    extras = _load_run_extras(root, t, load, maps=maps, units=units)
    name_problems = skill_name_problems(t.skills, t.composer.whiteboard)  # 6L-1：其他檢查之後
    name_problems += exploit_problems(t.composer.whiteboard, t.keywords)  # 6F-4b：利用者白板
    name_problems += pool_region_problems(t.skills, t.regions)  # 6F-4c：區域技能池
    icon_props = load("skill_icon_props.yaml", IconPropTable)
    name_problems += icon_prop_problems(t.skills, icon_props)  # IP-1：技能圖示道具
    if name_problems:
        raise ContentError(root / "skills", "；".join(name_problems))
    return ContentLibrary(
        root=root,
        elements=t.elements,
        ruleset=ruleset,
        weapons=t.weapons.by_id(),
        skills=t.skills,
        units=units,
        maps=maps,
        weather=t.weather.by_id(),
        ai_profiles=t.ai_profiles,
        budget=t.budget,
        composer=t.composer,
        builds=t.builds,
        synergies=t.synergies,
        keywords=t.keywords,
        exclusions=t.exclusions,
        skeletons=t.skeletons,
        roguelite=t.roguelite,
        workshop=t.workshop,
        workshop_text=t.workshop_text,
        affixes=affixes,
        offhands=t.offhands.by_id(),
        items=items,
        appearance=t.appearance,
        item_gen=t.item_gen,
        regions=t.regions,
        races=races,
        origins=origins,
        modifier_changes=t.modifier_changes,
        map_warnings=tuple(map_warnings),
        files=files,
        **extras,
        **world,
    )
