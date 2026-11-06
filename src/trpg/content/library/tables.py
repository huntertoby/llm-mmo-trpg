"""其他表的載入與小檢查：種族、修飾變化、技能成長、演化、閃現、開發用起始包、召喚物。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from trpg.content.battle import (
    DollLook,
    SummonLook,
    UnitTemplate,
    WeaponDef,
)
from trpg.content.dev_starters import DevStarterTable
from trpg.content.flash_templates import FlashTable
from trpg.content.library.base import _load_dir
from trpg.content.modifier_changes import (
    MODIFIER_CHANGES_FILE,
    ModifierChangeTable,
    modifier_change_problems,
)
from trpg.content.races import OriginTable, RaceTable, race_reference_problems
from trpg.content.regions import RegionTable
from trpg.content.schemas import ContentModel
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skill_rules import (
    BudgetRules,
    SkeletonDef,
)
from trpg.content.skill_scaling import (
    SkillScalingRules,
    scaling_problems,
)
from trpg.content.skill_triggers import SkillTriggerTable
from trpg.content.skills import (
    ModifierChange,
    SkillDef,
)
from trpg.content.summons import SummonDef, SummonTable, load_summon_looks
from trpg.shared.errors import ContentError


def _check_modifier_changes(root: Path, table: ModifierChangeTable, budget: BudgetRules) -> None:
    """``modifier_changes.yaml`` 與 ``ModifierChange`` 的欄位、``points_milli`` 的鍵一致。"""
    points = type(budget.modifier.points_milli).model_fields
    problems = modifier_change_problems(table, ModifierChange.model_fields, points)
    if problems:
        lines = "\n".join(f"  - {p}" for p in problems)
        raise ContentError(root / MODIFIER_CHANGES_FILE, f"修正規則的改變種類對不上：\n{lines}")


def _check_unit_races(
    root: Path, units: Mapping[str, UnitTemplate], races: RaceTable | None
) -> None:
    """單位範本的 ``race`` 必須是 ``races.yaml`` 裡的種族（Phase 3R-2）。"""
    race_ids = set() if races is None else set(races.by_id())
    for unit_id in sorted(units):
        race = units[unit_id].race
        if race is not None and race not in race_ids:
            raise ContentError(root / "units", f"單位 {unit_id}：未知的種族 {race}")


def _load_races(
    root: Path,
    load: Callable[[str, type[Any]], Any],
    regions: RegionTable | None,
    *,
    shapes: Mapping[str, object],
    weather: Mapping[str, object],
    terrain: Mapping[str, object],
    summons: frozenset[str],
) -> tuple[RaceTable | None, OriginTable | None]:
    """種族與出身（Phase 3R-1；兩個檔案可以都不存在，但要有就一起有）與跨檔案檢查。"""
    has_races = (root / "races.yaml").exists()
    has_origins = (root / "origins.yaml").exists()
    if not has_races and not has_origins:
        return None, None
    if has_races != has_origins:
        missing = "origins.yaml" if has_races else "races.yaml"
        raise ContentError(root / missing, "races.yaml 與 origins.yaml 必須一起存在")
    races: RaceTable = load("races.yaml", RaceTable)
    origins: OriginTable = load("origins.yaml", OriginTable)
    region_ids = frozenset(r.id for r in regions.regions) if regions is not None else frozenset()
    problems = race_reference_problems(
        races,
        origins,
        region_ids=region_ids,
        shape_ids=frozenset(shapes),
        weather_ids=frozenset(weather),
        terrain_ids=frozenset(terrain),
        summon_ids=summons,
    )
    if problems:
        raise ContentError(root / "races.yaml", "；".join(problems))
    return races, origins


def _check_scaling(
    root: Path,
    rules: SkillScalingRules,
    skills: dict[str, SkillDef],
    weapons: dict[str, WeaponDef],
) -> None:
    """內建技能的縮放屬性都在允許範圍內（武器技看武器、法術技依主題，Phase 3H-1）。"""
    problems = scaling_problems(rules, skills, weapons)
    if problems:
        raise ContentError(root / "skill_scaling.yaml", "；".join(problems))


def _check_evolution(
    root: Path,
    table: EvolutionTable,
    keywords: KeywordTable,
    skeletons: Mapping[str, SkeletonDef],
) -> None:
    """進化模板的跨檔案檢查（Phase 3-26b）：嫁接的關鍵字與改試的骨架必須存在。"""
    known = set(keywords.ids())
    problems = [f"未知的關鍵字 {k}" for k in sorted(table.grafts) if k not in known]
    problems += [
        f"模板 {t.id} 的骨架 {s} 不存在"
        for t in table.templates
        for s in t.skeletons
        if s not in skeletons
    ]
    if problems:
        raise ContentError(root / "skill_evolution.yaml", "；".join(problems))


def _load_flash(
    root: Path,
    load: Callable[[str, type[Any]], Any],
    evolution: EvolutionTable,
    triggers: SkillTriggerTable,
) -> FlashTable:
    """閃現設定（Phase 3W-1；檔案可以不存在）與跨檔案檢查：大變化引用的進化模板存在且分支相符、
    轉型的觸發時機存在。"""
    if not (root / "flash_templates.yaml").exists():
        return FlashTable()
    table: FlashTable = load("flash_templates.yaml", FlashTable)
    branches = {t.id: t.branch for t in evolution.templates}
    problems: list[str] = []
    for major in table.major:
        branch = branches.get(major.evolution)
        if branch is None:
            problems.append(f"大變化 {major.id}：未知的進化模板 {major.evolution}")
        elif branch != major.category:
            problems.append(
                f"大變化 {major.id}：進化模板 {major.evolution} 是 {branch}，"
                f"類別卻是 {major.category}"
            )
    known = triggers.by_id()
    problems += [
        f"轉型 {t.id}：未知的觸發時機 {t.trigger.event}"
        for t in table.transforms
        if t.trigger is not None and t.trigger.event not in known
    ]
    if problems:
        raise ContentError(root / "flash_templates.yaml", "；".join(problems))
    return table


def _dev_starter_problems(
    table: DevStarterTable,
    weapons: Mapping[str, WeaponDef],
    keywords: KeywordTable,
    skills: Mapping[str, SkillDef],
) -> list[str]:
    """開發者起始包的引用：武器、關鍵字、技能都要存在（Phase 3-24b2）。"""
    known = set(keywords.ids())
    problems: list[str] = []
    for pack in table.packs:
        if pack.weapon not in weapons:
            problems.append(f"起始包 {pack.id}：未知的武器 {pack.weapon}")
        bad = sorted(set(pack.keywords) - known)
        if bad:
            problems.append(f"起始包 {pack.id}：未知的關鍵字 {', '.join(bad)}")
        enemy = sorted(s for s in pack.skills if s in skills and skills[s].enemy_only)
        if enemy:
            problems.append(f"起始包 {pack.id}：技能 {', '.join(enemy)} 只給敵人（enemy_only）")
        missing = sorted(s for s in pack.skills if s not in skills)
        if missing:
            problems.append(f"起始包 {pack.id}：未知的技能 {', '.join(missing)}")
    return problems


def _load_summons(
    root: Path, weapons: dict[str, WeaponDef], files: list[tuple[Path, ContentModel]]
) -> SummonTable:
    """``content/units/summons/``（Phase 3D-4a；資料夾可以不存在）：召喚物範本與它的武器。"""
    if not (root / "units").is_dir():
        raise ContentError(root / "units", "找不到資料夾")
    directory = root / "units" / "summons"
    if not directory.is_dir():
        return SummonTable()
    templates = _load_dir(directory, UnitTemplate, files)
    looks = load_summon_looks(root).looks
    defs: list[SummonDef] = []
    for summon_id in sorted(templates):
        template = templates[summon_id]
        path = directory / f"{summon_id}.yaml"
        if not template.summon:
            raise ContentError(path, "召喚物範本必須寫 summon: true")
        if template.look is not None:
            raise ContentError(path, "外觀只寫在 summon_looks.yaml，範本不要填 look")
        entry = looks.get(summon_id.removeprefix("summon_"))
        if entry is None:
            raise ContentError(path, f"summon_looks.yaml 沒有 {summon_id} 的外觀")
        look = SummonLook.model_validate(entry.model_dump(exclude={"zh", "creature"}))
        update: dict[str, object] = {"look": look}
        if entry.creature is not None and template.doll is None:
            update["doll"] = DollLook(creature=entry.creature)  # 5A-ART1：召喚物的異形外觀
        template = template.model_copy(update=update)
        weapon = weapons.get(template.weapon)
        if weapon is None:
            raise ContentError(path, f"未知的武器：{template.weapon}")
        defs.append(SummonDef(template=template, weapon=weapon))
    return SummonTable(summons=tuple(defs))
