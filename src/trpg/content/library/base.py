"""各載入段共用的小工具：資料夾載入、選用檔載入、基礎表 :class:`_BaseTables`。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trpg.content.appearance import AppearanceTable
from trpg.content.battle import (
    OffhandTable,
    StatusTable,
    TerrainTable,
    WeaponTable,
)
from trpg.content.composer_rules import ComposerRules
from trpg.content.environment import (
    AiProfileTable,
    InteractionTable,
    ObjectTable,
    ReactionTable,
    SurfaceTable,
    WeatherTable,
)
from trpg.content.equipment import (
    AffixTable,
    EquipmentRules,
    ItemTable,
)
from trpg.content.forms import FormTable
from trpg.content.item_budget import ItemGenRules
from trpg.content.loader import load_content_file
from trpg.content.modifier_changes import (
    ModifierChangeTable,
)
from trpg.content.regions import RegionTable
from trpg.content.roguelite import RunRules
from trpg.content.rule_changes import RuleChangeTable
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skill_rules import (
    BudgetRules,
    ExclusionTable,
    SkeletonDef,
    SynergyTable,
)
from trpg.content.skill_tags import SkillTagTable
from trpg.content.skill_triggers import SkillTriggerTable
from trpg.content.skills import (
    ConditionTable,
    PrimitiveTable,
    ShapeTable,
    SkillDef,
)
from trpg.content.stacks import StackTable
from trpg.content.summons import SummonTable
from trpg.content.workshop import WorkshopRules, WorkshopTextTable
from trpg.shared.errors import ContentError


def _load_dir[M: ContentModel](
    directory: Path, model: type[M], files: list[tuple[Path, ContentModel]]
) -> dict[str, M]:
    if not directory.is_dir():
        raise ContentError(directory, "找不到資料夾")
    result: dict[str, M] = {}
    for path in sorted(directory.glob("*.yaml")):
        item = load_content_file(path, model)
        item_id = getattr(item, "id", None)
        if item_id != path.stem:
            raise ContentError(path, f"檔名必須與 id 相同（id 為 {item_id!r}）")
        files.append((path, item))
        result[path.stem] = item
    return result


type _Loader = Callable[[str, type[Any]], Any]
"""``load_library`` 裡讀一個檔並記進 ``files`` 的函式。"""


@dataclass(frozen=True)
class _BaseTables:
    """``load_library`` 第一步讀的表（戰鬥規則、技能、單位以外的單檔內容；5F-R2 從 ``load_library``
    拆出）。"""

    elements: ElementTable
    core: CoreRules
    hit_table: HitTable
    terrain: TerrainTable
    weapons: WeaponTable
    offhands: OffhandTable
    statuses: StatusTable
    objects: ObjectTable
    surfaces: SurfaceTable
    interactions: InteractionTable
    reactions: ReactionTable
    weather: WeatherTable
    ai_profiles: AiProfileTable
    shapes: ShapeTable
    primitives: PrimitiveTable
    conditions: ConditionTable
    skill_triggers: SkillTriggerTable
    stacks: StackTable
    budget: BudgetRules
    modifier_changes: ModifierChangeTable
    composer: ComposerRules
    builds: BuildTable
    synergies: SynergyTable
    keywords: KeywordTable
    exclusions: ExclusionTable
    skill_tags: SkillTagTable
    skeletons: dict[str, SkeletonDef]
    skills: dict[str, SkillDef]
    summons: SummonTable
    rule_changes: RuleChangeTable
    forms: FormTable
    roguelite: RunRules
    workshop: WorkshopRules
    workshop_text: WorkshopTextTable
    equipment_rules: EquipmentRules
    affix_table: AffixTable
    item_table: ItemTable
    appearance: AppearanceTable
    item_gen: ItemGenRules
    regions: RegionTable | None


def _load_optional[M: ContentModel](
    path: Path, model: type[M], files: list[tuple[Path, ContentModel]]
) -> M | None:
    """載入沒有跨檔案檢查的選用資料檔（檔案不存在＝``None``）。"""
    if not path.is_file():
        return None
    loaded = load_content_file(path, model)
    files.append((path, loaded))
    return loaded
