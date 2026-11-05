"""一次載入並交叉驗證全部戰鬥內容：:class:`Ruleset`（規則包）與 :class:`ContentLibrary`。

:class:`Ruleset` 是引擎結算需要的全部規則資料（核心數值、命中表、地形、狀態），會整份嵌入
戰鬥狀態，讓「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, get_args

from pydantic import Field, PrivateAttr, model_validator

from trpg.content.affix_names import resolve_affix_names
from trpg.content.appearance import AppearanceTable, item_appearance_problems
from trpg.content.battle import (
    BossPhase,
    DollLook,
    OffhandDef,
    OffhandTable,
    StatusDef,
    StatusTable,
    SummonLook,
    TagDownTrigger,
    TerrainDef,
    TerrainTable,
    UnitTemplate,
    WeaponDef,
    WeaponTable,
)
from trpg.content.composer_rules import ComposerRules, WhiteboardRules
from trpg.content.dev_starters import DevStarterTable
from trpg.content.environment import (
    AiProfileTable,
    InteractionTable,
    ObjectDef,
    ObjectTable,
    ReactionDef,
    ReactionTable,
    SurfaceDef,
    SurfaceTable,
    WeatherDef,
    WeatherTable,
    check_rule,
)
from trpg.content.equipment import (
    ActionAffix,
    AffixDef,
    AffixTable,
    ChargeAffix,
    ConditionalAffix,
    EquipmentRules,
    ItemDef,
    ItemTable,
    KeywordAffix,
    Loadout,
    ReactionAffix,
    RuleAffix,
    TriggerAffix,
    WeaponTraitAffix,
    item_problems,
    loadout_problems,
    resolve_loadout,
)
from trpg.content.fields import (
    CAPITAL_REGION,
    FieldMapDef,
    FieldMapReport,
    field_map_report,
)
from trpg.content.flash_templates import FlashTable
from trpg.content.forms import FormDef, FormTable, scaled_form_def
from trpg.content.item_budget import ItemGenRules, item_gen_problems
from trpg.content.keyword_derive import (
    Facts,
    SkillKeywords,
    derive_from_facts,
    derive_keywords,
    skill_condition_specs,
)
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.maps import MapDef, SpawnUnitsEvent, check_map
from trpg.content.modifier_changes import (
    MODIFIER_CHANGES_FILE,
    ModifierChangeTable,
    bundled_modifier_changes,
    modifier_change_problems,
)
from trpg.content.races import OriginTable, RaceDef, RaceTable, race_reference_problems
from trpg.content.regions import RegionTable, sanitize_map_theme
from trpg.content.roguelite import RunRules, roguelite_problems
from trpg.content.rule_changes import RuleChangeDef, RuleChangeTable
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_keywords import KeywordRule, KeywordTable
from trpg.content.skill_rules import (
    BudgetRules,
    ExclusionTable,
    SkeletonDef,
    SkillMatch,
    SynergyTable,
)
from trpg.content.skill_scaling import (
    ScalingBasis,
    ScalingFacts,
    SkillScalingRules,
    scaling_problems,
)
from trpg.content.skill_tags import SkillTagTable
from trpg.content.skill_triggers import SkillTriggerDef, SkillTriggerTable
from trpg.content.skills import (
    MODIFIER_CHANGES,
    SKELETON_IDS,
    ConditionDef,
    ConditionTable,
    ModifierChange,
    PrimitiveDef,
    PrimitiveTable,
    ShapeDef,
    ShapeTable,
    SkillDef,
    SkillTable,
    granted_skill_problems,
    held_gear,
    skill_problems,
    skill_slot_problems,
    weapon_problem,
)
from trpg.content.stacks import StackDef, StackTable
from trpg.content.summons import SummonDef, SummonTable, load_summon_looks
from trpg.content.weapon_params import set_weapon_param
from trpg.content.whiteboard_exploit import exploit_problems
from trpg.content.workshop import WorkshopRules, WorkshopTextTable, workshop_problems
from trpg.content.world_crafting import (
    CraftingRules,
    ResonanceRules,
    load_world_crafting,
    load_world_resonance,
)
from trpg.content.world_economy import WorldEconomy, load_world_economy
from trpg.content.world_encounters import EncounterTable, encounter_table_problems
from trpg.content.world_enemies import EnemyCatalog, WorldEnemies, world_enemies_problems
from trpg.content.world_events import WorldEventContent, load_world_event_content
from trpg.content.world_loot import LootRules, load_world_loot
from trpg.content.world_map import LocationKind, LocationMapDef, world_map_problems
from trpg.content.world_mercenaries import MercenaryTable
from trpg.content.world_newcomer import NewcomerContent, load_newcomer
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
from trpg.shared.types import Attribute, Surface

_LOG = logging.getLogger(__name__)

__all__ = [
    "REQUIRED_STATUSES",
    "ContentLibrary",
    "Ruleset",
    "enemy_template_ids",
    "gear_class_problem",
    "gear_reference_problems",
    "load_library",
    "player_template_enemy_only_problems",
    "skill_name_problems",
    "skill_reference_problems",
    "unit_skill_problems",
]

REQUIRED_STATUSES = (
    "armor_broken",
    "burning",
    "concealed",
    "defending",
    "prone",
    "revealed",
    "shielded",
    "slow",
    "root",
    "stun",
    "weaken",
    "vulnerable",
    "bleed",
    "poison",
)
"""引擎規則直接引用的狀態 ID，必須存在於 ``statuses.yaml``。"""


class _CacheDict(dict[object, SkillKeywords]):
    """快取字典：永遠與另一個快取「相等」。pydantic 的 ``__eq__`` 會比較私有屬性，而快取內容只是
    推導結果（依需要才填），不是規則資料——同一份規則包因為快取填過與否而不相等，會讓
    「狀態 JSON 來回後仍相等」這類比較時好時壞（3G-G2 起的不穩定測試）。"""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _CacheDict)

    __hash__ = None


def enemy_template_ids(
    units: Mapping[str, UnitTemplate], maps: Mapping[str, MapDef], rules: RunRules
) -> tuple[str, ...]:
    """敵方範本 ID（排序）：一輪的遭遇與 Boss 陣容、地圖預設陣容與援軍事件；不含召喚物。"""
    ids: set[str] = set()
    for step in rules.encounters:
        for option in step.options:
            ids.update(option)
    ids.update(rules.boss.enemies)
    for map_def in maps.values():
        if map_def.encounter is not None:
            ids.update(map_def.encounter.enemies)
        for event in map_def.events:
            if isinstance(event, SpawnUnitsEvent):
                ids.update(p.template for p in event.units)
    return tuple(sorted(i for i in ids if i in units and not units[i].summon))


class Ruleset(ContentModel):
    """引擎需要的規則資料。"""

    core: CoreRules
    hit_table: HitTable
    terrain: TerrainTable
    statuses: StatusTable
    objects: ObjectTable
    surfaces: SurfaceTable
    interactions: InteractionTable
    reactions: ReactionTable
    shapes: ShapeTable
    primitives: PrimitiveTable
    conditions: ConditionTable
    skill_triggers: SkillTriggerTable = SkillTriggerTable.model_construct(triggers=())
    stacks: StackTable = StackTable()
    skills: SkillTable = SkillTable()
    summons: SummonTable = SummonTable()
    """召喚物範本（Phase 3D-4a，``content/units/summons/``）：嵌入規則包，重播不依賴資料檔。"""
    forms: FormTable = FormTable()
    """形態（Phase 3J-1a，``content/forms.yaml``）：嵌入規則包，重播不依賴資料檔。"""
    rule_changes: RuleChangeTable = RuleChangeTable()
    """規則改變（Phase 3D-6，``content/rule_changes.yaml``）：嵌入規則包，重播不依賴資料檔。"""
    races: RaceTable | None = None
    """可玩種族（Phase 3R-2，``content/races.yaml``）：種族技與環境被動，嵌入規則包，重播不依賴資料
    檔；沒有這個檔案時為 ``None``（單位帶 ``race`` 會在載入時報錯）。"""
    equipment: EquipmentRules = EquipmentRules()
    """裝備的遞減權重與硬上限（Phase 3G-G1，``content/rules/equipment.yaml``）。"""
    keywords: KeywordTable = KeywordTable.model_construct(keywords=())
    """關鍵字推導表（Phase 3G-G2，``content/skill_keywords.yaml``）：裝備的技能強化詞條依關鍵字
    選取技能。嵌入規則包，重播不依賴資料檔。"""
    skill_tags: SkillTagTable = SkillTagTable()
    """技能標籤的中文名（Phase 3-41a，``content/skill_tags.yaml``）：說明文字與刻印符文名用。"""
    gear_names: dict[str, str] = Field(default_factory=dict)
    """武器與副手的中文名（ID → 名稱；Phase 3I-5）：引擎的限定武器與「手持某種武器」條件訊息用。
    嵌入規則包，重播不依賴資料檔。"""

    _keyword_cache: dict[object, SkillKeywords] = PrivateAttr(default_factory=_CacheDict)
    _rule_change_index: dict[str, RuleChangeDef] = PrivateAttr(default_factory=dict)
    _summon_index: dict[str, SummonDef] = PrivateAttr(default_factory=dict)
    _form_index: dict[str, FormDef] = PrivateAttr(default_factory=dict)
    _race_index: dict[str, RaceDef] = PrivateAttr(default_factory=dict)
    _skill_index: dict[str, SkillDef] = PrivateAttr(default_factory=dict)
    _shape_index: dict[str, ShapeDef] = PrivateAttr(default_factory=dict)
    _primitive_index: dict[str, PrimitiveDef] = PrivateAttr(default_factory=dict)
    _condition_index: dict[str, ConditionDef] = PrivateAttr(default_factory=dict)
    _trigger_index: dict[str, SkillTriggerDef] = PrivateAttr(default_factory=dict)
    _stack_index: dict[str, StackDef] = PrivateAttr(default_factory=dict)
    _terrain_index: dict[str, TerrainDef] = PrivateAttr(default_factory=dict)
    _status_index: dict[str, StatusDef] = PrivateAttr(default_factory=dict)
    _reaction_index: dict[str, ReactionDef] = PrivateAttr(default_factory=dict)
    _modifier_ids: frozenset[str] = PrivateAttr(default_factory=frozenset)

    def model_post_init(self, context: object, /) -> None:
        # 查表索引（不屬於資料本身，不參與序列化與相等比較）
        self._terrain_index = self.terrain.by_id()
        self._status_index = self.statuses.by_id()
        self._reaction_index = self.reactions.by_id()
        self._skill_index = self.skills.by_id()
        self._shape_index = self.shapes.by_id()
        self._primitive_index = self.primitives.by_id()
        self._condition_index = self.conditions.by_id()
        self._trigger_index = self.skill_triggers.by_id()
        self._stack_index = self.stacks.by_id()
        self._summon_index = self.summons.by_id()
        self._form_index = self.forms.by_id()
        self._race_index = {} if self.races is None else self.races.by_id()
        self._rule_change_index = self.rule_changes.by_id()
        self._modifier_ids = frozenset(s.id for s in self.skills.skills if s.is_modifier)

    @model_validator(mode="after")
    def _check(self) -> Ruleset:
        if (self.hit_table.slope, self.hit_table.cap) != (
            self.core.hit_slope,
            self.core.hit_mod_cap,
        ):
            raise ValueError(
                "hit_table.yaml 的 slope／cap 與 core.yaml 的 hit_slope／hit_mod_cap 不一致，"
                "請執行 `uv run python scripts/gen_hit_table.py` 重新產生"
            )
        ids = {s.id for s in self.statuses.statuses}
        missing = [s for s in REQUIRED_STATUSES if s not in ids]
        if missing:
            raise ValueError(f"statuses.yaml 缺少引擎需要的狀態：{', '.join(missing)}")
        unknown_refs = sorted(self.primitives.status_refs() - ids)
        if unknown_refs:
            raise ValueError(f"skill_primitives.yaml 引用了未知的狀態：{', '.join(unknown_refs)}")
        by_status = self.statuses.by_id()
        for source, target in sorted(self.core.boss_control_conversion.items()):
            if source not in by_status or by_status[source].control_group != "hard":
                raise ValueError(
                    f"core.yaml 的 boss_control_conversion：{source} 必須是 hard 類別的控制狀態"
                )
            if target not in by_status:
                raise ValueError(f"core.yaml 的 boss_control_conversion 引用了未知的狀態：{target}")
        unknown = sorted({ref for ref in self.surfaces.status_refs() if ref not in ids})
        if unknown:
            raise ValueError(f"surfaces.yaml 引用了未知的狀態：{', '.join(unknown)}")
        terrain_ids = {t.id for t in self.terrain.terrain}
        bad_terrain = sorted(
            {
                o.terrain
                for rule in self.interactions.rules
                for o in rule.then
                if o.terrain is not None and o.terrain not in terrain_ids
            }
        )
        if bad_terrain:
            raise ValueError(f"interactions.yaml 引用了未知的地形：{', '.join(bad_terrain)}")
        bad_status = sorted(
            {
                o.status
                for rule in self.interactions.rules
                for o in rule.then
                if o.status is not None and o.status not in ids
            }
        )
        if bad_status:
            raise ValueError(f"interactions.yaml 引用了未知的狀態：{', '.join(bad_status)}")
        rubble = self.core.topple_rubble_object
        if rubble not in {o.id for o in self.objects.objects}:
            raise ValueError(f"core.yaml 的 topple_rubble_object 引用了未知的物件：{rubble}")
        self._check_rule_changes(ids)
        self._check_overloads(ids)
        reduction = 1000 - self.core.element_mod_floor_permille
        if self.equipment.caps.damage_reduction_permille != reduction:
            raise ValueError(
                "rules/equipment.yaml 的 caps.damage_reduction_permille 必須等於 1000 − "
                f"core.yaml 的 element_mod_floor_permille（{reduction}）"
            )
        return self

    def _check_overloads(self, status_ids: set[str]) -> None:
        """超載（3D-7b）的反噬：狀態存在、不能是硬控、跳過回合或持續傷害（不讓持有者跳過回合）。"""
        unsafe = self.unsafe_backlash_statuses()
        for stack in self.stacks.stacks:
            if stack.overload is None:
                continue
            for sub in stack.overload.backlash:
                if sub.type != "apply_status":
                    continue
                if sub.status not in status_ids:
                    raise ValueError(
                        f"stacks.yaml 的 {stack.id} 反噬引用了未知的狀態：{sub.status}"
                    )
                if sub.status in unsafe:
                    raise ValueError(
                        f"stacks.yaml 的 {stack.id} 反噬不能使用硬控、跳過回合或持續傷害的狀態"
                        f"（{sub.status}）"
                    )

    def _check_rule_changes(self, status_ids: set[str]) -> None:
        """規則改變（3D-6）引用的狀態與召喚物範本存在。"""
        summon_ids = set(self.summons.by_id())
        for rule in self.rule_changes.rule_changes:
            if rule.status is not None and rule.status not in status_ids:
                raise ValueError(f"rule_changes.yaml 的 {rule.id} 引用了未知的狀態：{rule.status}")
            if rule.unit is not None and rule.unit not in summon_ids:
                raise ValueError(
                    f"rule_changes.yaml 的 {rule.id} 引用了未知的召喚物範本：{rule.unit}"
                )

    def with_skills(self, skills: Iterable[SkillDef]) -> Ruleset:
        """加入 ``skills``（例如 LLM 或組合器生成的技能）的新規則包：每個技能都走
        :func:`skill_reference_problems`（與內容庫載入、技能驗證器同一份檢查），通過才加入並重建
        查表索引；原規則包不變。

        技能 ID 與既有技能重複時拋出 :class:`ValueError`（內容完全相同的重複視為已加入而略過）；
        有任何引用問題也拋出 :class:`ValueError`（訊息列出全部技能的問題）。
        """
        known = self.skills.by_id()
        added: dict[str, SkillDef] = {}
        for skill in skills:
            existing = known.get(skill.id) or added.get(skill.id)
            if existing is None:
                added[skill.id] = skill
            elif existing != skill:
                raise ValueError(f"技能 ID {skill.id} 已存在，且內容不同")
        if not added:
            return self
        combined = {**known, **added}
        problems = [
            f"{skill.id}：{p}"
            for skill in added.values()
            for p in skill_reference_problems(skill, self, combined)
        ]
        if problems:
            raise ValueError("；".join(problems))
        merged = SkillTable(skills=(*self.skills.skills, *added.values()))
        rules = self.model_copy(update={"skills": merged})
        rules.model_post_init(None)
        return rules

    def enemy_only_statuses(self) -> frozenset[str]:
        """只給敵人的狀態 ID（``enemy_only``，Phase 5F-5c）：技能引用它們一律當引用錯誤。"""
        return frozenset(s.id for s in self.statuses.statuses if s.enemy_only)

    def unsafe_backlash_statuses(self) -> frozenset[str]:
        """不能當反噬的狀態 ID（Phase 3D-7a）：硬控類、會讓持有者跳過回合、回合開始時持續傷害
        （反噬不會讓施放者跳過回合，也不會讓他的 HP 低於 1）。"""
        return frozenset(
            s.id
            for s in self.statuses.statuses
            if s.skip_turn or s.control_group == "hard" or s.on_turn_start_damage is not None
        )

    def object_def(self, kind: str) -> ObjectDef:
        return self.objects.get(kind)

    def surface_def(self, surface: Surface) -> SurfaceDef:
        return self.surfaces.get(surface)

    def surface_scales_with_magnitude(self, surface: Surface) -> bool:
        """表面的強度（BAL-12e，#76）有沒有作用：回合開始的傷害或治療，或進入、回合開始時施加的
        狀態是數值型（:attr:`StatusDef.scales_with_magnitude`，例如火焰表面的燃燒）。"""
        if surface is Surface.NONE:
            return False
        definition = self.surface_def(surface)
        start, enter = definition.on_turn_start, definition.on_enter
        if start is not None and (start.damage is not None or start.heal is not None):
            return True
        applied = [
            s
            for s in (
                None if start is None else start.apply_status,
                None if enter is None else enter.apply_status,
            )
            if s is not None
        ]
        return any(self.status_def(s).scales_with_magnitude for s in applied)

    # 查表是引擎最常呼叫的函式之一：直接讀 ``__pydantic_private__``，略過 BaseModel.__getattr__
    # 的私有屬性慢速路徑（結果與 ``self._terrain_index`` 相同）。
    def reaction_def(self, reaction_id: str) -> ReactionDef:
        index: dict[str, ReactionDef] = self.__pydantic_private__["_reaction_index"]  # type: ignore[index]
        return index[reaction_id]

    def terrain_def(self, terrain_id: str) -> TerrainDef:
        index: dict[str, TerrainDef] = self.__pydantic_private__["_terrain_index"]  # type: ignore[index]
        return index[terrain_id]

    def status_def(self, status_id: str) -> StatusDef:
        index: dict[str, StatusDef] = self.__pydantic_private__["_status_index"]  # type: ignore[index]
        return index[status_id]

    def shape_def(self, shape_id: str) -> ShapeDef:
        index: dict[str, ShapeDef] = self.__pydantic_private__["_shape_index"]  # type: ignore[index]
        return index[shape_id]

    def primitive_def(self, primitive_id: str) -> PrimitiveDef:
        index: dict[str, PrimitiveDef] = self.__pydantic_private__["_primitive_index"]  # type: ignore[index]
        return index[primitive_id]

    def find_primitive(self, primitive_id: str) -> PrimitiveDef | None:
        """同 :meth:`primitive_def`，但查不到時回傳 ``None``：巢狀位置有不是原語的效果類型
        （``on_kill`` 的 ``refund_ap``、``refund_cooldown``，賭注的 ``damage_multiplier`` 等）。"""
        index: dict[str, PrimitiveDef] = self.__pydantic_private__["_primitive_index"]  # type: ignore[index]
        return index.get(primitive_id)

    def condition_def(self, condition_id: str) -> ConditionDef:
        index: dict[str, ConditionDef] = self.__pydantic_private__["_condition_index"]  # type: ignore[index]
        return index[condition_id]

    def trigger_def(self, trigger_id: str) -> SkillTriggerDef:
        """觸發時機定義；找不到時拋出 ``KeyError``。"""
        index: dict[str, SkillTriggerDef] = self.__pydantic_private__["_trigger_index"]  # type: ignore[index]
        return index[trigger_id]

    def stack_def(self, stack_id: str) -> StackDef:
        """層數定義；找不到時拋出 ``KeyError``。"""
        index: dict[str, StackDef] = self.__pydantic_private__["_stack_index"]  # type: ignore[index]
        return index[stack_id]

    def skill_def(self, skill_id: str) -> SkillDef:
        """技能定義；找不到時拋出 ``KeyError``。"""
        index: dict[str, SkillDef] = self.__pydantic_private__["_skill_index"]  # type: ignore[index]
        return index[skill_id]

    def race_def(self, race_id: str) -> RaceDef:
        """種族定義（Phase 3R-2）；沒有種族資料或找不到時拋出 ``KeyError``。"""
        index: dict[str, RaceDef] = self.__pydantic_private__["_race_index"]  # type: ignore[index]
        return index[race_id]

    def summon_def(self, summon_id: str) -> SummonDef:
        """召喚物範本；找不到時拋出 ``KeyError``。"""
        index: dict[str, SummonDef] = self.__pydantic_private__["_summon_index"]  # type: ignore[index]
        return index[summon_id]

    def form_def(self, form_id: str) -> FormDef:
        """形態定義（Phase 3J-1a）；不存在時拋出 ``KeyError``。"""
        index: dict[str, FormDef] = self.__pydantic_private__["_form_index"]  # type: ignore[index]
        return index[form_id]

    def scaled_form(self, form_id: str, magnitude: int) -> FormDef:
        """套上幅度 ``magnitude``（‰，BAL-2c）的形態定義
        （:func:`~trpg.content.forms.scaled_form_def`；幅度 1000 時就是 :meth:`form_def`）；形態
        不存在時拋出 ``KeyError``。不快取在規則包上：pydantic 的相等比較包含私有屬性，快取會讓
        同樣的規則包比較起來不相等。"""
        return scaled_form_def(self.form_def(form_id), magnitude)

    def rule_change_def(self, rule_id: str) -> RuleChangeDef:
        """規則改變（Phase 3D-6）；找不到時拋出 ``KeyError``。"""
        index: dict[str, RuleChangeDef] = self.__pydantic_private__["_rule_change_index"]  # type: ignore[index]
        return index[rule_id]

    def skill_keywords(self, skill: SkillDef) -> SkillKeywords:
        """``skill`` 製造與利用的關鍵字（推導結果依技能 ID 快取；變形後的技能 ID 不變、效果不變，
        所以共用同一筆）。"""
        cache: dict[object, SkillKeywords] = self.__pydantic_private__["_keyword_cache"]  # type: ignore[index]
        found = cache.get(skill.id)
        if found is None:
            found = cache[skill.id] = derive_keywords(skill, self.keywords)
        return found

    def facts_keywords(self, key: object, facts: Facts) -> SkillKeywords:
        """由事實（例如普攻的元素與命中附帶狀態）推導的關鍵字，依 ``key`` 快取。"""
        cache: dict[object, SkillKeywords] = self.__pydantic_private__["_keyword_cache"]  # type: ignore[index]
        found = cache.get(key)
        if found is None:
            found = cache[key] = derive_from_facts(facts, self.keywords)
        return found

    def has_modifier(self, skill_ids: Iterable[str]) -> bool:
        """``skill_ids`` 之中是否有修正技能（``kind: modifier``，3C-2；引擎的快速路徑）。"""
        ids: frozenset[str] = self.__pydantic_private__["_modifier_ids"]  # type: ignore[index]
        return any(skill_id in ids for skill_id in skill_ids)


@dataclass(frozen=True)
class ContentLibrary:
    """``content/`` 下全部已驗證的戰鬥內容。"""

    root: Path
    elements: ElementTable
    ruleset: Ruleset
    weapons: dict[str, WeaponDef]
    skills: dict[str, SkillDef]
    units: dict[str, UnitTemplate]
    maps: dict[str, MapDef]
    weather: dict[str, WeatherDef]
    ai_profiles: AiProfileTable
    budget: BudgetRules
    composer: ComposerRules
    builds: BuildTable
    synergies: SynergyTable
    keywords: KeywordTable
    """關鍵字推導表（``skill_keywords.yaml``，Phase 3-24b1）。"""
    exclusions: ExclusionTable
    skeletons: dict[str, SkeletonDef]
    roguelite: RunRules
    """roguelite 一輪的參數（``roguelite.yaml``，Phase 3-5a）。"""
    workshop: WorkshopRules
    """技能工坊「裝上試玩」的設定（``workshop.yaml``，Phase 3F-1）。"""
    skill_scaling: SkillScalingRules
    """技能縮放屬性的允許範圍（``skill_scaling.yaml``，Phase 3H-1；武器技看武器、法術技依主題）。
    必填（Phase 3T-2）：沒有縮放規則的內容庫無法驗證技能。"""
    affixes: dict[str, AffixDef] = field(default_factory=dict)
    """詞條白名單（``affixes.yaml``，Phase 3G-G1）。"""
    offhands: dict[str, OffhandDef] = field(default_factory=dict)
    """副手定義（``offhands.yaml``，Phase 3I-2）；物品的 ``offhand_def`` 由這裡嵌入。"""
    items: dict[str, ItemDef] = field(default_factory=dict)
    """物品（``items.yaml``，Phase 3G-G1；目前只有測試用物品）。"""
    appearance: AppearanceTable | None = None
    """裝備外觀清單（``equipment/appearance.yaml``，Phase 3G-G5a）。"""
    item_gen: ItemGenRules | None = None
    """物品產生器與物品預算的係數（``item_gen.yaml``，Phase 3K-1）。"""
    dev_starters: DevStarterTable = field(default_factory=DevStarterTable)
    """開發者起始包（``dev_starters.yaml``，Phase 3-24b2；不是設計規則，玩家介面不顯示）。"""
    evolution: EvolutionTable = field(default_factory=EvolutionTable)
    """3 級分歧進化的模板（``skill_evolution.yaml``，Phase 3-26b）。"""
    flash: FlashTable = field(default_factory=FlashTable)
    """閃現（靈光一閃）的規則與模板（``flash_templates.yaml``，Phase 3W-1）；不嵌入規則包。"""
    workshop_text: WorkshopTextTable = field(default_factory=WorkshopTextTable)
    """工坊說明的玩家語氣對照表（``workshop_text.yaml``，Phase 3-48f）；不屬於規則。"""
    regions: RegionTable | None = None
    """區域主題表（``regions.yaml``，Phase 3-37a；純顯示資料）。"""
    races: RaceTable | None = None
    """可玩種族（``races.yaml``，Phase 3R-1；已通過防最佳解驗證）。"""
    origins: OriginTable | None = None
    """出身（``origins.yaml``，Phase 3R-1；不影響戰鬥）。"""
    modifier_changes: ModifierChangeTable = field(default_factory=bundled_modifier_changes)
    """修正規則的改變種類（``modifier_changes.yaml``，Phase 3T-1）；不嵌入規則包（引擎只用
    :mod:`trpg.content.skills` 由內建資料推導的常數）。"""
    map_warnings: tuple[str, ...] = ()
    """地圖 ``region``／``look`` 的未知值警告（已丟棄、退回預設畫法；不是錯誤）。"""
    world_maps: dict[str, LocationMapDef] = field(default_factory=dict)
    """大世界地點圖（``world/maps/*.yaml``，Phase 5A-1）；鍵＝區域 ID。沒有資料夾時為空。不含主城
    （在 ``hub_maps``）；查某區的地點圖一律用 :meth:`location_map`。"""
    hub_maps: dict[str, LocationMapDef] = field(default_factory=dict)
    """不屬於任何區的樞紐地點圖（``hub: true``，目前只有主城；6D-R2）；鍵＝``region``。"""
    world_rules: WorldRules | None = None
    """大世界規則的數值（``world/rules.yaml``，Phase 5A-2）；沒有檔案時為 ``None``。"""
    world_enemies: WorldEnemies | None = None
    """大世界敵人的元素變體與精英詞綴（``world/enemies.yaml``，Phase 5A-3）；沒有檔案時為
    ``None``。"""
    world_encounters: dict[str, EncounterTable] = field(default_factory=dict)
    """大世界遭遇表（``world/encounters/*.yaml``，Phase 5A-3）；鍵＝區域 ID。沒有資料夾時為空。"""
    world_event_content: WorldEventContent = field(default_factory=WorldEventContent)
    """事件骨架、NPC 人設卡、事件規則（``world/events/``、``world/npcs/``、
    ``world/event_rules.yaml``，Phase 5B-1）；沒有資料時為空。"""
    world_quests: WorldQuestContent = field(default_factory=WorldQuestContent)
    """任務、聊天內容、事件好感度、酒館傳聞與好感度規則（``world/quests/``、``world/social/``、
    ``world/affinity.yaml``，Phase 5B-4）；沒有資料時為空。"""
    world_oaths: OathTable | None = None
    """誓約模板（``world/oaths.yaml``，Phase 5A-6 接點；內容在 5C-3）；沒有檔案時為 ``None``。"""
    world_mercenaries: MercenaryTable | None = None
    """系統傭兵名單（``world/mercenaries.yaml``，Phase 5C-1）；沒有檔案時為 ``None``（開戰用標準
    隊友）。"""
    world_economy: WorldEconomy = field(default_factory=WorldEconomy)
    """貨幣規則、物品與商店（Phase 5D-1；沒有 ``world/economy.yaml`` 時經濟功能關閉）。"""
    world_loot: LootRules | None = None
    """掉落規則（``world/loot.yaml``，Phase 5D-2）；沒有檔案時為 ``None``（掉落關閉）。"""
    world_trade: TradeRules | None = None
    """交易共同前置與郵寄（``world/trade.yaml``，Phase 6T-1a）；沒有檔案時為 ``None``
    （交易關閉）。"""
    world_crafting: CraftingRules | None = None
    """鐵匠與附魔台（``world/crafting.yaml``，Phase 5D-3）；沒有檔案時為 ``None``（關閉）。"""
    world_newcomer: NewcomerContent | None = None
    """新手引導（``world/newcomer.yaml``，Phase 6F-2：開局在主城、戰鬥短提示）；沒有檔案時為
    ``None``（新角色照舊站在起始區的小鎮、沒有第一次免費傳送）。"""
    world_season: SeasonContent | None = None
    """賽季日程、今日目標、懸賞、世界事件（``world/season.yaml``，Phase 5F-1）；沒有檔案時為
    ``None``（這些功能關閉）。"""
    world_resonance: ResonanceRules | None = None
    """裝備共鳴（``world/resonance.yaml``，Phase 5D-3）；沒有檔案時為 ``None``（沒有共鳴）。"""
    field_maps: dict[str, FieldMapDef] = field(default_factory=dict)
    """實地地圖與室內圖（``world/fields/<region>/``，Phase 6B-1）；鍵＝地圖 ID；沒有資料夾＝空。"""
    field_warnings: tuple[str, ...] = ()
    """實地地圖的數值類警告（尺寸、傳送石數；不影響通過）。"""
    field_pending: tuple[str, ...] = ()
    """對面還沒畫的出口與門（配對待補；不是錯誤）。"""
    files: list[tuple[Path, ContentModel]] = field(default_factory=list)
    retier_cache: dict[str, SkillDef] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """技能照角色階級重配的快取（:func:`trpg.skillgen.skill_tier.retier`，3W-R1）：掛在內容庫上、隨它
    回收；鍵是「技能內容的 SHA-256 ＋ 階級」。不是建構參數，``dataclasses.replace`` 換內容後是新的空
    快取；不參與相等比較。"""
    mercenary_gear_cache: dict[tuple[str, int], dict[str, ItemDef]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """傭兵系統裝備的快取（:func:`trpg.world.gear.mercenary_equipment`，5D-R1）：掛在內容庫上、隨它
    回收；鍵是「傭兵 ID ＋ 物品等級」，滿了就清空（上限在 ``trpg.world.gear``）。同 ``retier_cache``
    不是建構參數、不參與相等比較。"""
    outdoor_index: dict[str, dict[tuple[str, str], FieldMapDef]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """:meth:`outdoor_map` 的索引（Phase 6C-R2：``"maps"`` → (區域, 地點) → 室外圖；第一次查時建）。
    同 ``retier_cache`` 不是建構參數，``dataclasses.replace`` 換了 ``field_maps`` 後是新的空
    索引。"""
    season_views: dict[str, ContentLibrary] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """:meth:`for_season` 的快取（季 ID → 套上覆寫的內容庫；Phase 5F-R2）。"""
    season_base: ContentLibrary | None = field(default=None, init=False, repr=False, compare=False)
    """:meth:`for_season` 產生的內容庫指回原本的內容庫（原本的＝``None``）。"""

    def for_season(self, season_id: str) -> ContentLibrary:
        """``season_id`` 這一季的內容庫（Phase 5F-R2）：``world_season`` 換成套上
        ``seasons.<季 ID>`` 覆寫的內容，其他不變。那一季沒有覆寫時回傳原本的內容庫（第一季的行為
        完全不變）。結果有快取，同一季拿到同一個物件。"""
        base = self.season_base or self
        season = base.world_season
        if season is None or season_id not in season.seasons:
            return base
        view = base.season_views.get(season_id)
        if view is None:
            view = replace(base, world_season=season.for_season(season_id))
            object.__setattr__(view, "season_base", base)
            base.season_views[season_id] = view
        return view

    def outdoor_map(self, region: str, location: str) -> FieldMapDef | None:
        """地點的實地地圖（室外圖；還沒畫＝``None``）。同一個地點有好幾張時取地圖 ID 最小的
        （和原本依 ID 排序掃描的結果一樣）。"""
        index = self.outdoor_index.get("maps")
        if index is None:
            index = {}
            for map_id in sorted(self.field_maps):
                found = self.field_maps[map_id]
                if found.location is not None:
                    index.setdefault((found.region, found.location), found)
            self.outdoor_index["maps"] = index
        return index.get((region, location))

    def loadout_of(self, template: UnitTemplate) -> Loadout:
        """單位範本的裝備快照（``equipment`` 解析成內嵌定義的 :class:`Loadout`；沒有裝備時
        為空）。"""
        if not template.equipment:
            return Loadout()
        return resolve_loadout(template.equipment, self.items, self.affixes)

    def location_map(self, region: str) -> LocationMapDef | None:
        """``region`` 的地點圖：區域的，或主城這類樞紐的（6D-R2）；沒有＝``None``。"""
        found = self.world_maps.get(region)
        return found if found is not None else self.hub_maps.get(region)

    def enemy_catalog(self) -> EnemyCatalog:
        """解析大世界敵人名字（範本或變體）與套用精英詞綴（Phase 5A-3）。"""
        return _enemy_catalog(
            self.units, self.world_enemies, self.weapons, self.skills, self.ruleset
        )

    def unit(self, template_id: str) -> UnitTemplate:
        try:
            return self.units[template_id]
        except KeyError:
            known = ", ".join(sorted(self.units))
            raise KeyError(f"未知的單位範本：{template_id}（可用：{known}）") from None

    def map(self, map_id: str) -> MapDef:
        try:
            return self.maps[map_id]
        except KeyError:
            known = ", ".join(sorted(self.maps))
            raise KeyError(f"未知的地圖：{map_id}（可用：{known}）") from None

    def weapon_of(self, template: UnitTemplate) -> WeaponDef:
        return self.weapons[template.weapon]

    def scaling_basis(self, skill: SkillDef | ScalingFacts) -> ScalingBasis:
        """技能（或工坊草稿）的縮放屬性允許範圍與由來（``skill_scaling.yaml``，Phase 3H-7）。"""
        return self.skill_scaling.basis(skill, self.weapons)

    def scaling_range(self, skill: SkillDef | ScalingFacts) -> tuple[Attribute, ...]:
        """允許的縮放屬性（有順序；沒有主角屬性時取第一個）。"""
        return self.scaling_basis(skill).attrs

    def secondary_range(self, skill: SkillDef | ScalingFacts) -> tuple[Attribute, ...]:
        """允許的第二縮放屬性（3I-3，#46；武器技只能是心智屬性、身體類法術沒有；不含主屬性要
        呼叫者自己排除）。"""
        return self.skill_scaling.secondary_range(skill, self.weapons)

    def weather_def(self, weather_id: str) -> WeatherDef:
        try:
            return self.weather[weather_id]
        except KeyError:
            known = ", ".join(sorted(self.weather))
            raise KeyError(f"未知的天氣：{weather_id}（可用：{known}）") from None


def skill_name_problems(skills: Mapping[str, SkillDef], whiteboard: WhiteboardRules) -> list[str]:
    """顯示名相同、技能內容不同（6L-1，玩法 PM）：手寫技能（``skills/``）不可同名；白板配方的武器版
    名稱（``weapon_name_zh``）不可和手寫技能同名。配方之間的同名由
    :func:`~trpg.content.composer_rules.whiteboard_name_problems` 檢查。"""
    by_name: dict[str, list[SkillDef]] = {}
    for skill_id in sorted(skills):
        by_name.setdefault(skills[skill_id].name_zh, []).append(skills[skill_id])
    problems: list[str] = []
    for name, group in sorted(by_name.items()):
        bodies = {
            json.dumps(s.model_dump(mode="json", exclude={"id"}), sort_keys=True) for s in group
        }
        if len(group) > 1 and len(bodies) > 1:
            problems.append(f"技能同名但內容不同：{name}（{'、'.join(s.id for s in group)}）")
    for recipe in (*whiteboard.active, *whiteboard.passive, *whiteboard.reaction):
        if recipe.weapon_name_zh is not None and recipe.weapon_name_zh in by_name:
            problems.append(
                f"白板配方 {recipe.id} 的 weapon_name_zh 和手寫技能同名：{recipe.weapon_name_zh}"
            )
    return problems


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
    欄位。"""
    regions, statuses, keywords = t.regions, t.statuses, t.keywords
    skills, budget, weapon_map = t.skills, t.budget, t.weapons.by_id()
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
    keyword_ids = {k.id for k in keywords.keywords}
    world_event_content = load_world_event_content(
        root,
        world_maps,
        weather_map,
        files,
        status_ids=statuses.by_id(),
        enemy_only_ids={s.id for s in statuses.statuses if s.enemy_only},  # 06 6.35（5F-R2）
        keyword_ids=keyword_ids,
        race_ids=None if races is None else races.by_id(),
        tone_regions={*hub_maps, *(() if regions is None else (r.id for r in regions.regions))},
    )
    world_quests = load_world_quest_content(
        root,
        world_maps,
        world_event_content,
        files,
        check_skill=lambda skill: _story_skill_problems(skill, ruleset, skills, budget),
        keyword_ids=keyword_ids,
    )
    _check_unit_races(root, {**units, **{b.id: b.hero for b in t.builds.builds}}, races)
    _check_companions(root, world_mercenaries, t.builds, world_event_content, world_quests)
    world_economy = load_world_economy(  # 5D-1
        root,
        files,
        regions=set(world_maps),
        npcs_by_region={r: {n.id for n in e.npcs} for r, e in world_event_content.npcs.items()},
        check_skill=lambda skill: _story_skill_problems(skill, ruleset, skills, budget),
    )
    _check_shop_prices(root, world_season, world_economy)  # 5F-5b
    world_loot = load_world_loot(  # 5D-2
        root,
        files,
        regions=set(world_maps),
        units=None if world_enemies is None else {*units, *(v.id for v in world_enemies.variants)},
        affixes=None if world_enemies is None else {a.id for a in world_enemies.affixes},
        items=world_economy.items,
        keywords=keyword_ids,
    )
    world_crafting = load_world_crafting(  # 5D-3
        root,
        files,
        locations={  # 6D-5：主城的鐵匠鋪也是設施（6D-R2：主城的地點圖在 hub_maps）
            r: {loc.id: loc.kind for loc in m.locations}
            for r, m in sorted({**world_maps, **hub_maps}.items())
        },
        npcs={r: {n.id: n.location for n in e.npcs} for r, e in world_event_content.npcs.items()},
        items=world_economy.items,
        affixes=affixes,
        keywords=keyword_ids,
        hint_texts=_hint_texts(world_event_content, world_quests),
    )
    world_trade = load_world_trade(  # 6T-1a：郵差要站在城鎮（含主城）
        root,
        files,
        locations={
            r: {loc.id: loc.kind for loc in m.locations}
            for r, m in sorted({**world_maps, **hub_maps}.items())
        },
    )
    fields, field_report = _load_world_fields(
        root / WORLD_FIELDS_DIR,
        t,
        files,
        world_maps=world_maps,
        npcs={r: {n.id: n.location for n in e.npcs} for r, e in world_event_content.npcs.items()},
        # 沒有任何任務檔（測試用的精簡內容）＝不檢查出口 gate，和 npcs 缺區不檢查一致
        quest_steps={
            r: {q.id: tuple(s.id for s in q.steps) for q in table.quests}
            for r, table in world_quests.quests.items()
        }
        or None,
    )
    return {
        "field_maps": fields,
        "field_warnings": field_report.warnings,
        "field_pending": field_report.pending,
        "world_maps": world_maps,
        "hub_maps": hub_maps,
        "world_rules": world_rules,
        "world_enemies": world_enemies,
        "world_encounters": world_encounters,
        "world_event_content": world_event_content,
        "world_quests": world_quests,
        "world_oaths": world_oaths,
        "world_mercenaries": world_mercenaries,
        "world_economy": world_economy,
        "world_loot": world_loot,
        "world_trade": world_trade,
        "world_crafting": world_crafting,
        "world_resonance": load_world_resonance(root, files, affixes=affixes, keywords=keyword_ids),
        "world_season": world_season,
        "world_newcomer": _load_newcomer(
            root,
            world_maps,
            world_quests,
            files,
            npcs={
                r: {n.id: n.location for n in e.npcs} for r, e in world_event_content.npcs.items()
            },
        ),
    }


def _load_newcomer(
    root: Path,
    world_maps: Mapping[str, LocationMapDef],
    quests: WorldQuestContent,
    files: list[tuple[Path, ContentModel]],
    *,
    npcs: Mapping[str, Mapping[str, str]] = {},
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
    if problems:
        raise ContentError(path, "；".join(problems))
    files.append((path, newcomer))
    return newcomer


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


def _load_optional[M: ContentModel](
    path: Path, model: type[M], files: list[tuple[Path, ContentModel]]
) -> M | None:
    """載入沒有跨檔案檢查的選用資料檔（檔案不存在＝``None``）。"""
    if not path.is_file():
        return None
    loaded = load_content_file(path, model)
    files.append((path, loaded))
    return loaded


def _season_variants(season: SeasonContent) -> list[tuple[str, SeasonContent]]:
    """預設（標籤空字串）＋每一季套上覆寫後的內容（標籤「seasons.<季 ID>：」；依季 ID 排序）。"""
    return [("", season)] + [
        (f"seasons.{sid}：", season.for_season(sid)) for sid in sorted(season.seasons)
    ]


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


def skill_reference_problems(
    skill: SkillDef, ruleset: Ruleset, skills: Mapping[str, SkillDef]
) -> list[str]:
    """技能的全部跨檔案引用檢查（內容庫與技能驗證器共用）：形狀、原語、條件、狀態、物件、層數、召喚物、
    規則改變、``grant_skill`` 指向的技能，以及規則改變型傳說的 ``ap_cost``（空串列為通過）。

    ``skills`` 是 ``grant_skill`` 查找的技能表；所有引用表一律帶齊（不省略任何一項）。
    """
    enemy_only = ruleset.enemy_only_statuses()  # 5F-5c：只給敵人的狀態，技能不能引用
    problems = skill_problems(
        skill,
        ruleset.shapes.by_id(),
        ruleset.primitives.by_id(),
        status_ids={s.id for s in ruleset.statuses.statuses if s.id not in enemy_only},
        object_ids={o.id for o in ruleset.objects.objects},
        conditions=ruleset.conditions.by_id(),
        triggers=ruleset.skill_triggers.by_id(),
        stacks=ruleset.stacks.by_id(),
        dual_min_rarity=ruleset.core.dual_scaling_min_rarity,
        summon_ids=set(ruleset.summons.by_id()),
        rule_change_ids=set(ruleset.rule_changes.by_id()),
        unsafe_statuses=ruleset.unsafe_backlash_statuses(),
        scale_cap_max=ruleset.core.scale_cap_max_permille,
        summon_trait_ids=set(ruleset.core.summon_traits),
        infusion_ids=set(ruleset.core.summon_infusions),
        form_ids=set(ruleset.forms.by_id()),
    )
    problems += [
        f"狀態 {sid} 只給敵人（enemy_only），技能不能用"
        for sid in sorted(enemy_only)
        if any(sid in p for p in problems)
    ]
    problems += granted_skill_problems(skill, skills, ruleset.primitives.by_id())
    follow = skill.followup_skill()  # 複合技能的動作段（Phase 3F-3a）：同一套引用檢查
    if follow is not None:
        problems += [f"followup.{p}" for p in skill_reference_problems(follow, ruleset, skills)]
    problems += _variant_reference_problems(skill, ruleset, skills)
    activation_ap = ruleset.core.legendary_activation_ap
    if skill.rule_change_id is not None and skill.ap_cost != activation_ap:
        problems.append(
            f"ap_cost：規則改變型傳說以 core.yaml 的 legendary_activation_ap（{activation_ap}）"
            f"啟動，收到 {skill.ap_cost}"
        )
    return problems


def _variant_lookup_problems(variant_id: str | None, form: SkillDef, ruleset: Ruleset) -> list[str]:
    """帶變奏的技能（基礎型態與每個變奏型態）不能含「事後以技能 ID 查表」的原語（Phase 3E-2a；
    ``skill_primitives.yaml`` 的 ``lookup_by_skill_id``）：查到的是基礎型態，變奏的替換不會生效，
    引擎還可能找不到效果而崩潰。"""
    flagged = {p.id for p in ruleset.primitives.primitives if p.lookup_by_skill_id}
    where = "variants" if variant_id is None else f"variants.{variant_id}"
    found = sorted({e.type for e in form.iter_effects(include_followup=True)} & flagged)
    return [
        f"{where}：帶變奏的技能不能含「{name}」效果（區域、延遲傷害、複製技能等事後以技能 ID 查表，"
        "拿到的是基礎型態，變奏不會生效）"
        for name in found
    ]


def _variant_reference_problems(
    skill: SkillDef, ruleset: Ruleset, skills: Mapping[str, SkillDef]
) -> list[str]:
    """戰場變奏（Phase 3-25a）：數量不超過稀有度上限（``core.variant_max_by_rarity``）、條件引用的
    表面存在，每個型態本身也通過同一套引用檢查。"""
    if not skill.variants:
        return []
    problems: list[str] = []
    limit = ruleset.core.variant_max_by_rarity.get(skill.rarity, 0)
    if len(skill.variants) > limit:
        problems.append(
            f"variants：稀有度 {skill.rarity} 最多帶 {limit} 個變奏，收到 {len(skill.variants)} 個"
        )
    problems += _variant_lookup_problems(None, skill, ruleset)
    known = {s.id.value for s in ruleset.surfaces.surfaces}
    for variant in skill.variants:
        unknown = [s for s in variant.when.surfaces if s not in known]
        if unknown:
            problems.append(
                f"variants.{variant.id}.when：未知的表面 {', '.join(unknown)}"
                f"（可用：{', '.join(sorted(known))}）"
            )
        form = skill.variant_form(variant.id)
        problems += _variant_lookup_problems(variant.id, form, ruleset)
        problems += [
            f"variants.{variant.id}.{p}" for p in skill_reference_problems(form, ruleset, skills)
        ]
    return problems


def gear_reference_problems(
    skill: SkillDef, weapons: Mapping[str, WeaponDef], offhands: Mapping[str, OffhandDef]
) -> list[str]:
    """技能的限定武器（``weapon_only``）與「手持某種武器」條件引用的武器或副手存在，而且武器的
    大類符合技能的 ``weapon_req``（否則技能永遠不能裝，或加成永遠不會成立；Phase 3I-5）。"""
    refs = [("weapon_only", w) for w in skill.weapon_only]
    refs += [
        ("wielding_weapon", c.weapon)
        for c in skill_condition_specs(skill)
        if c.type == "wielding_weapon" and c.weapon is not None
    ]
    found = (
        (where, gear_class_problem(skill.weapon_req, g, weapons, offhands)) for where, g in refs
    )
    return [f"{where}：{p}" for where, p in found if p is not None]


_CLASS_ZH = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}


def gear_class_problem(
    weapon_req: str,
    gear_id: str,
    weapons: Mapping[str, WeaponDef],
    offhands: Mapping[str, OffhandDef],
) -> str | None:
    """``gear_id``（武器或副手）不存在、或武器大類與技能的 ``weapon_req`` 不符時的原因。驗證器與
    工坊的事前停用共用（Phase 3I-5）。副手不分大類，永遠相符。"""
    weapon = weapons.get(gear_id)
    if weapon is None:
        return None if gear_id in offhands else f"未知的武器或副手 {gear_id!r}"
    if weapon_req in ("any", weapon.weapon_class):
        return None
    return (
        f"{weapon.name_zh}是{_CLASS_ZH[weapon.weapon_class]}武器，"
        f"與技能的武器需求（{_CLASS_ZH.get(weapon_req, weapon_req)}）不符"
    )


def _check_skills(
    root: Path,
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    budget: BudgetRules,
    *,
    weapons: Mapping[str, WeaponDef] | None = None,
    offhands: Mapping[str, OffhandDef] | None = None,
) -> None:
    """技能引用的形狀、原語、狀態、物件都存在，參數在範圍內；費用花的資源與類別相符（3H-2）；
    限定武器與手持條件引用的裝備存在且大類相符（3I-5）。"""
    for skill_id, skill in skills.items():
        problems = skill_reference_problems(skill, ruleset, skills)
        if weapons is not None and offhands is not None:
            problems += gear_reference_problems(skill, weapons, offhands)
        cost = budget.cost_problem(skill.category, skill.cost)
        if cost is not None:
            problems.append(cost)
        if problems:
            raise ContentError(root / "skills" / f"{skill_id}.yaml", "；".join(problems))


def _story_skill_problems(
    skill: SkillDef, ruleset: Ruleset, skills: Mapping[str, SkillDef], budget: BudgetRules
) -> list[str]:
    """劇情技能（``world/quests/`` 的 ``story_skills``，Phase 5B-4）的引用與費用檢查（同
    ``content/skills/``；不進技能池）。劇情技能是給玩家的，不能標 ``enemy_only``（5F-R1）。"""
    problems = skill_reference_problems(skill, ruleset, skills)
    if skill.enemy_only:
        problems.append("劇情技能是給玩家的，不能標 enemy_only")
    cost = budget.cost_problem(skill.category, skill.cost)
    return problems if cost is None else [*problems, cost]


def _keyword_rule_problems(
    rule: KeywordRule, ruleset: Ruleset, skills: Mapping[str, SkillDef]
) -> list[str]:
    """關鍵字推導規則引用的原語、條件、觸發、形狀、狀態、物件、層數、規則改變、技能都存在。"""
    known: dict[str, set[str]] = {
        "effect": set(ruleset.primitives.by_id()),
        "condition": set(ruleset.conditions.by_id()),
        "trigger": set(ruleset.skill_triggers.by_id()),
        "shape": set(ruleset.shapes.by_id()),
        "change": set(MODIFIER_CHANGES),
    }
    problems: list[str] = []
    if rule.source_id not in known[rule.source]:
        problems.append(f"未知的{rule.source} {rule.source_id!r}")
    params = rule.params()
    refs: dict[str, set[str]] = {
        "status": {s.id for s in ruleset.statuses.statuses},
        "object": {o.id for o in ruleset.objects.objects},
        "stack": set(ruleset.stacks.by_id()),
        "rule": set(ruleset.rule_changes.by_id()),
        "skill": set(skills),
        "infusion": set(ruleset.core.summon_infusions),
    }
    problems += [
        f"未知的 {name} {params[name]!r}"
        for name, ids in refs.items()
        if name in params and params[name] not in ids
    ]
    return problems


def _check_keywords(
    root: Path, keywords: KeywordTable, ruleset: Ruleset, skills: Mapping[str, SkillDef]
) -> None:
    """關鍵字推導表引用的內容都存在。"""
    path = root / "skill_keywords.yaml"
    for keyword in keywords.keywords:
        for label, rules in (("makes", keyword.makes), ("uses", keyword.uses)):
            for index, rule in enumerate(rules):
                found = _keyword_rule_problems(rule, ruleset, skills)
                if found:
                    raise ContentError(path, f"{keyword.id}.{label}[{index}]：" + "；".join(found))


def _match_problems(match: SkillMatch | None, ruleset: Ruleset) -> list[str]:
    """互斥規則的比對引用的形狀、狀態、原語是否存在。"""
    if match is None:
        return []
    shape_ids, primitive_ids = set(ruleset.shapes.by_id()), set(ruleset.primitives.by_id())
    status_ids = {s.id for s in ruleset.statuses.statuses}
    problems = [f"未知的形狀 {p.type!r}" for p in match.shapes or () if p.type not in shape_ids]
    problems += [f"未知的狀態 {s!r}" for s in match.statuses or () if s not in status_ids]
    refs = [*(match.primitives_any or ()), *(match.primitives_all or ())]
    refs += [e.type for e in [*(match.effects_any or ()), *(match.effects_all or ())] if e.type]
    problems += [f"未知的原語 {r!r}" for r in refs if r not in primitive_ids]
    for sub in match.any_of or ():
        problems += _match_problems(sub, ruleset)
    return problems


def _check_skill_rules(
    root: Path,
    ruleset: Ruleset,
    exclusions: ExclusionTable,
    skeletons: dict[str, SkeletonDef],
) -> None:
    """互斥規則與骨架引用的形狀、狀態、原語都存在；12 種骨架各一個資料檔。"""
    path = root / "skill_exclusions.yaml"
    for rule in exclusions.rules:
        found = [
            *_match_problems(rule.when, ruleset),
            *_match_problems(rule.forbid, ruleset),
            *_match_problems(rule.require, ruleset),
        ]
        if found:
            raise ContentError(path, f"互斥規則 {rule.id}：" + "；".join(found))
    missing = [i for i in SKELETON_IDS if i not in skeletons]
    if missing:
        raise ContentError(root / "skeletons", f"缺少骨架資料檔：{', '.join(missing)}")
    shape_ids, primitive_ids = set(ruleset.shapes.by_id()), set(ruleset.primitives.by_id())
    for skeleton_id, skeleton in skeletons.items():
        where = root / "skeletons" / f"{skeleton_id}.yaml"
        unknown = [s for s in skeleton.shapes if s not in shape_ids]
        if unknown:
            raise ContentError(where, f"未知的形狀：{', '.join(unknown)}")
        if not skeleton.enabled:
            continue  # 停用的骨架可以引用尚未實作的原語
        used = [*skeleton.core.primitives, *(skeleton.secondary.primitives or ())]
        unknown = [p for p in used if p not in primitive_ids]
        if unknown:
            raise ContentError(where, f"未知的原語：{', '.join(unknown)}")


def _check_units(
    root: Path,
    units: dict[str, UnitTemplate],
    *,
    weapons: dict[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    source: Path | None = None,
    gear: _GearCatalog | None = None,
) -> None:
    """單位範本引用的武器、行為模式、反應與技能都存在且合法（``source``：錯誤訊息指向的檔案）。
    ``gear``：有給時檢查範本的裝備（物品存在、穿戴合法；Phase 3G-G1）；召喚物不能有裝備。"""
    reaction_index = ruleset.reactions.by_id()
    for template_id, template in units.items():
        path = source or root / "units" / f"{template_id}.yaml"
        if template.weapon not in weapons:
            raise ContentError(path, f"未知的武器：{template.weapon}")
        if template.equipment:
            problems = (
                ["召喚物不能有裝備"]
                if gear is None
                else gear.problems(template, weapons[template.weapon])
            )
            if problems:
                raise ContentError(path, "；".join(problems))
        if template.ai_profile is not None and template.ai_profile not in ai_profiles.by_id():
            raise ContentError(path, f"未知的行為模式：{template.ai_profile}")
        if template.totem is not None:
            status = next(
                (d for d in ruleset.statuses.statuses if d.id == template.totem.status), None
            )
            if status is None or not status.beneficial:
                raise ContentError(path, f"圖騰的狀態必須是有益的既有狀態：{template.totem.status}")
        _check_summon_traits(path, template, ruleset)
        for rule in template.reactions or ():
            try:
                check_rule(rule, reaction_index, skills)
            except ValueError as exc:
                raise ContentError(path, str(exc)) from exc
            if rule.reaction in skills and rule.reaction not in template.skills:
                raise ContentError(path, f"反應規則引用了沒有裝備的反應技：{rule.reaction}")
        offhand = None if gear is None else gear.offhand_of(template)
        problems = unit_skill_problems(
            template, weapons[template.weapon], skills, ruleset.core, offhand
        )
        if problems:
            raise ContentError(path, "；".join(problems))


def _check_summon_traits(path: Path, template: UnitTemplate, ruleset: Ruleset) -> None:
    """召喚物的固有灌注關鍵字在對照表中、命中特性的狀態存在（Phase 3-33e1）。"""
    if template.innate is not None and template.innate not in ruleset.core.summon_infusions:
        raise ContentError(path, f"固有灌注關鍵字不在 summon_infusions 對照表中：{template.innate}")
    status_ids = {d.id for d in ruleset.statuses.statuses}
    for rule in template.hit_rules:
        if rule.status is not None and rule.status not in status_ids:
            raise ContentError(path, f"命中特性引用了未知的狀態：{rule.status}")
    for opening in template.opening_statuses:  # Phase 5A-M1
        if opening.status not in status_ids:
            raise ContentError(path, f"開場狀態引用了未知的狀態：{opening.status}")


def _check_builds(
    root: Path,
    builds: BuildTable,
    units: dict[str, UnitTemplate],
    *,
    weapons: dict[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    gear: _GearCatalog,
) -> None:
    """build 的英雄範本合法（武器、技能、行為模式、裝備），隊友存在，build ID 不與單位範本衝突。"""
    path = root / "sim" / "builds.yaml"
    unknown = sorted(c for c in builds.companions if c not in units)
    if unknown:
        raise ContentError(path, f"companions 引用了未知的單位範本：{', '.join(unknown)}")
    clash = sorted(b.id for b in builds.builds if b.id in units)
    if clash:
        raise ContentError(path, f"build ID 與單位範本重複：{', '.join(clash)}")
    heroes = {b.id: b.hero for b in builds.builds}
    player_side = {**heroes, **{c: units[c] for c in sorted(builds.companions)}}
    problems = [
        p
        for uid, template in sorted(player_side.items())
        for p in player_template_enemy_only_problems(uid, template, skills, ruleset)
    ]
    if problems:
        raise ContentError(path, "；".join(problems))
    _check_units(
        root,
        heroes,
        weapons=weapons,
        skills=skills,
        ruleset=ruleset,
        ai_profiles=ai_profiles,
        source=path,
        gear=gear,
    )


def pool_region_problems(skills: Mapping[str, SkillDef], regions: RegionTable | None) -> list[str]:
    """技能的 ``pool_regions``（6F-4c 區域技能池）只能填 ``regions.yaml`` 的區域 ID，
    且不可是空串列。"""
    known = set() if regions is None else set(regions.region_by_id())
    problems: list[str] = []
    for skill_id in sorted(skills):
        found = skills[skill_id].pool_regions
        if found is None:
            continue
        if not found:
            problems.append(f"技能 {skill_id} 的 pool_regions 不可是空串列（不限區域請省略）")
        unknown = sorted(r for r in found if r not in known)
        if unknown:
            problems.append(f"技能 {skill_id} 的 pool_regions 有未知的區域：{'、'.join(unknown)}")
    return problems


def player_template_enemy_only_problems(
    unit_id: str, template: UnitTemplate, skills: Mapping[str, SkillDef], ruleset: Ruleset
) -> list[str]:
    """玩家這一邊的範本（Phase 5F-R1；build 英雄＝主角、影子、傭兵、劇情夥伴的底稿，
    與 build 的隊友）
    不能裝 ``enemy_only`` 技能（技能欄與反應）、不能開場帶 ``enemy_only`` 狀態。"""
    problems: list[str] = []
    reactions = tuple(r.reaction for r in template.reactions or ())
    for sid in (*template.skills, *reactions):
        skill = skills.get(sid)
        if skill is not None and skill.enemy_only:
            problems.append(f"{unit_id}：技能 {sid} 只給敵人（enemy_only），玩家這一邊不能用")
    enemy_statuses = ruleset.enemy_only_statuses()
    for opening in template.opening_statuses:
        if opening.status in enemy_statuses:
            problems.append(
                f"{unit_id}：開場狀態 {opening.status} 只給敵人（enemy_only），玩家這一邊不能帶"
            )
    return problems


@dataclass(frozen=True)
class _GearCatalog:
    """載入時檢查單位裝備用的物品、詞條與裝備規則（Phase 3G-G1）。"""

    items: dict[str, ItemDef]
    affixes: dict[str, AffixDef]
    rules: EquipmentRules

    def offhand_of(self, template: UnitTemplate) -> OffhandDef | None:
        """範本裝備的副手定義（沒有或解析失敗為 ``None``；解析失敗由 :meth:`problems` 回報）。"""
        try:
            return resolve_loadout(template.equipment, self.items, self.affixes).offhand_def()
        except ValueError:
            return None

    def problems(self, template: UnitTemplate, weapon: WeaponDef) -> list[str]:
        try:
            loadout = resolve_loadout(template.equipment, self.items, self.affixes)
        except ValueError as exc:
            return [f"equipment：{exc}"]
        return [f"equipment：{p}" for p in loadout_problems(loadout, weapon, self.rules)]


def _trait_problems(affix: WeaponTraitAffix, weapons: Mapping[str, WeaponDef]) -> list[str]:
    """武器特性強化：限定的武器存在、參數路徑在這些武器上存在，而且套用一次之後武器資料仍然合法。"""
    problems: list[str] = []
    for weapon_id in affix.weapons:
        weapon = weapons.get(weapon_id)
        if weapon is None:
            problems.append(f"詞條 {affix.id} 引用了未知的武器：{weapon_id}")
            continue
        data = weapon.model_dump()
        factor = affix.scale_permille
        if not set_weapon_param(data, affix.param, affix.delta, factor):
            problems.append(f"詞條 {affix.id}：武器 {weapon_id} 沒有可改的參數 {affix.param}")
            continue
        try:
            WeaponDef.model_validate(data)
        except ValueError as exc:
            problems.append(f"詞條 {affix.id}：改 {weapon_id}.{affix.param} 後武器不合法：{exc}")
    return problems


def _affix_reference_problems(
    affix: AffixDef,
    ruleset: Ruleset,
    weapons: Mapping[str, WeaponDef],
    keyword_ids: frozenset[str],
) -> list[str]:
    """詞條引用的條件、狀態、觸發時機、反應與規則改變存在（Phase 3G-G1）。

    Phase 3G-G2 起也檢查：技能強化的關鍵字 id（對照推導表）、武器特性強化限定的武器與參數。
    Phase 3G-G3a 起也檢查：觸發與充能的時機（對象要有「另一方」）、效果原語、充能的層數。
    Phase 3G-G3b 起也檢查：授予動作的技能（存在、主動技）、授予反應的反應與事件。
    """
    statuses = {s.id for s in ruleset.statuses.statuses}
    refs: list[tuple[str, str, set[str]]] = []
    if isinstance(affix, ConditionalAffix):
        refs.append(("條件", affix.condition.type, {c.id for c in ruleset.conditions.conditions}))
    if isinstance(affix, TriggerAffix):
        refs.append(("觸發時機", affix.trigger, {t.id for t in ruleset.skill_triggers.triggers}))
    if isinstance(affix, ChargeAffix):
        refs.append(
            ("觸發時機", affix.gain_trigger, {t.id for t in ruleset.skill_triggers.triggers})
        )
    if isinstance(affix, RuleAffix):
        refs.append(("規則改變", affix.rule, {r.id for r in ruleset.rule_changes.rule_changes}))
    if isinstance(affix, ReactionAffix):
        refs.append(("反應", affix.reaction, {r.id for r in ruleset.reactions.reactions}))
    if isinstance(affix, ActionAffix):
        refs.append(("技能", affix.skill, set(ruleset.skills.by_id())))
    for status in _affix_statuses(affix):
        refs.append(("狀態", status, statuses))
    if isinstance(affix, KeywordAffix):
        refs.append(("關鍵字", affix.keyword, set(keyword_ids)))
    extra = _trait_problems(affix, weapons) if isinstance(affix, WeaponTraitAffix) else []
    if isinstance(affix, ActionAffix):
        extra += _action_problems(affix, ruleset)
    if isinstance(affix, ReactionAffix):
        extra += _reaction_affix_problems(affix, ruleset)
    if isinstance(affix, TriggerAffix | ChargeAffix):
        extra += _trigger_charge_problems(affix, ruleset)
    return extra + [
        f"詞條 {affix.id} 引用了未知的{what}：{ref}"
        for what, ref, known in refs
        if ref not in known
    ]


def _action_problems(affix: ActionAffix, ruleset: Ruleset) -> list[str]:
    """授予動作（G3b）：授予的必須是主動技（被動技與反應技不是「動作」）。"""
    skill = ruleset.skills.by_id().get(affix.skill)
    if skill is not None and skill.kind != "active":
        return [f"詞條 {affix.id} 授予的技能 {skill.id} 必須是主動技（目前 {skill.kind}）"]
    return []


def _reaction_affix_problems(affix: ReactionAffix, ruleset: Ruleset) -> list[str]:
    """授予反應（G3b）：``extend_trigger`` 的事件必須是該反應支援的事件；``grant`` 的反應必須有
    ``range``（目前只有 ``redirect_damage``），也不能需要狀態。"""
    definition = ruleset.reactions.by_id().get(affix.reaction)
    if definition is None:
        return []
    if affix.mode == "extend_trigger" and affix.event not in definition.events:
        return [f"詞條 {affix.id}：反應 {affix.reaction} 不支援事件 {affix.event}"]
    if affix.mode == "grant" and (definition.effect != "redirect_damage" or affix.range is None):
        return [f"詞條 {affix.id}：授予的反應必須是 redirect_damage 並填寫 range"]
    return []


def _trigger_charge_problems(affix: TriggerAffix | ChargeAffix, ruleset: Ruleset) -> list[str]:
    """觸發與充能詞條（G3a）：效果原語存在；觸發對象（目標、攻擊者）需要該時機有「另一方」；
    充能的層數存在、屬於持有者自己（``owner: self``）且裝備版上限不超過層數本身的上限。"""
    problems = [
        f"詞條 {affix.id} 引用了未知的效果原語：{e.type}"
        for e in affix.effects
        if e.type not in ruleset.primitives.by_id()
    ]
    if isinstance(affix, ChargeAffix):
        stacks = ruleset.stacks.by_id()
        stack = stacks.get(affix.stack)
        if stack is None:
            problems.append(f"詞條 {affix.id} 引用了未知的層數：{affix.stack}")
        elif stack.owner != "self" or affix.max_stacks > stack.max:
            problems.append(
                f"詞條 {affix.id} 的層數 {stack.id} 必須是 owner: self 且上限不小於 max_stacks"
            )
        return problems
    triggers = ruleset.skill_triggers.by_id()
    trigger = triggers.get(affix.trigger)
    if trigger is not None and affix.effect_target != "self" and not trigger.has_other:
        problems.append(
            f"詞條 {affix.id}：時機 {affix.trigger} 沒有另一方，effect_target 只能是 self"
        )
    if affix.effect_target == "attacker" and affix.trigger != "on_damaged":
        problems.append(f"詞條 {affix.id}：effect_target: attacker 只能搭配 on_damaged")
    return problems


def _affix_statuses(affix: AffixDef) -> list[str]:
    found: list[str] = []
    for name in ("status", "on_hit_status"):
        value = getattr(affix, name, None)
        if isinstance(value, str):
            found.append(value)
    for effect in getattr(affix, "effects", ()):
        if effect.status is not None:
            found.append(effect.status)
    return found


def _check_appearance(
    root: Path, appearance: AppearanceTable, items: ItemTable, keywords: KeywordTable
) -> None:
    """外觀清單的關鍵字都是 3-24b1 的關鍵字；items.yaml 寫了的外觀欄位都認得且相容。"""
    unknown = sorted(set(appearance.keywords) - set(keywords.ids()))
    if unknown:
        raise ContentError(
            root / "equipment" / "appearance.yaml", f"未知的關鍵字：{', '.join(unknown)}"
        )
    problems = [p for item in items.items for p in item_appearance_problems(item, appearance)]
    if problems:
        raise ContentError(root / "items.yaml", "；".join(problems))


def _check_item_gen(root: Path, rules: ItemGenRules, affixes: Mapping[str, AffixDef]) -> None:
    """物品產生器的係數和詞條白名單一致（Phase 3K-1）。"""
    problems = item_gen_problems(rules, affixes)
    if problems:
        raise ContentError(root / "item_gen.yaml", "；".join(problems))


def _check_affixes(
    root: Path,
    affixes: Mapping[str, AffixDef],
    ruleset: Ruleset,
    weapons: Mapping[str, WeaponDef],
) -> None:
    keyword_ids = frozenset(ruleset.keywords.ids())
    problems = [
        p
        for affix in affixes.values()
        for p in _affix_reference_problems(affix, ruleset, weapons, keyword_ids)
    ]
    if problems:
        raise ContentError(root / "affixes.yaml", "；".join(problems))


def unit_skill_problems(
    template: UnitTemplate,
    weapon: WeaponDef,
    skills: dict[str, SkillDef],
    core: CoreRules,
    offhand: OffhandDef | None = None,
) -> list[str]:
    """單位範本裝備的技能是否存在、與武器（含限定武器，3I-5）相容、沒有超過欄位上限（繁體中文，
    空串列為通過）。``offhand``：範本裝備的副手。"""
    held = held_gear(weapon, offhand)
    problems: list[str] = []
    equipped: list[SkillDef] = []
    for skill_id in template.skills:
        skill = skills.get(skill_id)
        if skill is None:
            problems.append(f"skills：未知的技能 {skill_id!r}")
            continue
        equipped.append(skill)
        problem = weapon_problem(skill, weapon.weapon_class, held)
        if problem is not None:
            problems.append(f"skills：{problem}")
    problems += [f"skills：{p}" for p in skill_slot_problems(equipped, core.skill_slots)]
    return problems


def unit_phase_problems(
    template: UnitTemplate,
    *,
    units: Mapping[str, UnitTemplate],
    weapons: Mapping[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    weather: Mapping[str, WeatherDef],
    offhand: OffhandDef | None = None,
) -> list[str]:
    """範本 ``phases``（Phase 5F-2）引用的技能（存在、符合武器、欄位上限）、行為模式、狀態、天氣、
    召喚範本與地形都存在（繁體中文，空串列為通過）。"""
    problems: list[str] = []
    status_ids = set(ruleset.statuses.by_id())
    profiles = ai_profiles.by_id()
    terrain_ids = set(ruleset.terrain.by_id())
    weapon = weapons.get(template.weapon)
    for phase in template.phases:
        where = f"階段 {phase.id}"
        if phase.skills is not None and weapon is not None:
            staged = template.model_copy(update={"skills": phase.skills})
            problems += [
                f"{where}：{p}"
                for p in unit_skill_problems(staged, weapon, skills, ruleset.core, offhand)
            ]
        if phase.ai_profile is not None and phase.ai_profile not in profiles:
            problems.append(f"{where}：未知的行為模式 {phase.ai_profile}")
        wanted = [*phase.remove_statuses, *(o.status for o in phase.add_statuses)]
        problems += [f"{where}：未知的狀態 {s}" for s in wanted if s not in status_ids]
        if phase.weather is not None and phase.weather not in weather:
            problems.append(f"{where}：未知的天氣 {phase.weather}")
        for spawn in phase.spawns:
            found = units.get(spawn.template)
            if found is None or found.summon:
                problems.append(f"{where}：召喚的單位範本不存在或是召喚物 {spawn.template}")
            elif found.phases:
                problems.append(f"{where}：召喚的單位範本不能也有 phases（{spawn.template}）")
        problems += [
            f"{where}：未知的地形 {t.terrain}"
            for t in phase.tiles
            if t.terrain is not None and t.terrain not in terrain_ids
        ]
    return problems


def _check_unit_phases(
    root: Path,
    units: dict[str, UnitTemplate],
    *,
    weapons: dict[str, WeaponDef],
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    ai_profiles: AiProfileTable,
    weather: dict[str, WeatherDef],
    gear: _GearCatalog,
) -> None:
    """每個範本的 ``phases`` 都通過 :func:`unit_phase_problems`。"""
    for template_id, template in units.items():
        problems = unit_phase_problems(
            template,
            units=units,
            weapons=weapons,
            skills=skills,
            ruleset=ruleset,
            ai_profiles=ai_profiles,
            weather=weather,
            offhand=gear.offhand_of(template),
        )
        if problems:
            raise ContentError(root / "units" / f"{template_id}.yaml", "；".join(problems))


def _map_phase_tile_problems(map_def: MapDef, units: Mapping[str, UnitTemplate]) -> list[str]:
    """地圖預設陣容裡 Boss 階段的 ``tiles``／``spawns.at`` 在地圖內（Phase 5F-2）。"""
    if map_def.encounter is None:
        return []
    problems: list[str] = []
    for template_id in sorted(set(map_def.encounter.enemies)):
        template = units.get(template_id)
        for phase in () if template is None else template.phases:
            cells = [t.at for t in phase.tiles] + [s.at for s in phase.spawns if s.at is not None]
            problems += [
                f"{template_id} 階段 {phase.id} 的 {list(xy)} 在地圖外"
                for xy in cells
                if not (0 <= xy[0] < map_def.width and 0 <= xy[1] < map_def.height)
            ]
            problems += _tag_down_problems(template_id, phase, map_def.encounter.enemies, units)
    return problems


def _tag_down_problems(
    template_id: str, phase: BossPhase, enemies: Sequence[str], units: Mapping[str, UnitTemplate]
) -> list[str]:
    """``tag_down`` 觸發（Phase 5F-3）：預設陣容裡帶該標籤的單位要夠 ``count`` 名（否則永遠不會
    觸發）。"""
    trigger = phase.trigger
    if not isinstance(trigger, TagDownTrigger):
        return []
    have = sum(1 for e in enemies if (u := units.get(e)) is not None and trigger.tag in u.tags)
    if have >= trigger.count:
        return []
    return [
        f"{template_id} 階段 {phase.id} 要「{trigger.tag}」倒下 {trigger.count} 名，"
        f"地圖的預設陣容只有 {have} 名"
    ]


def _map_reference_problems(
    map_def: MapDef, units: dict[str, UnitTemplate], weather: dict[str, WeatherDef]
) -> list[str]:
    """地圖引用的天氣、遭遇與地圖事件中的單位範本是否存在。"""
    problems: list[str] = []
    if map_def.weather not in weather:
        problems.append(f"未知的天氣：{map_def.weather}")
    templates: list[str] = []
    if map_def.encounter is not None:
        templates += [*map_def.encounter.allies, *map_def.encounter.enemies]
    for event in map_def.events:
        if isinstance(event, SpawnUnitsEvent):
            templates += [u.template for u in event.units]
    unknown = sorted({t for t in templates if t not in units})
    if unknown:
        problems.append(f"未知的單位範本：{', '.join(unknown)}")
    return problems
