"""一次載入並交叉驗證全部戰鬥內容：:class:`Ruleset`（規則包）與 :class:`ContentLibrary`。

:class:`Ruleset` 是引擎結算需要的全部規則資料（核心數值、命中表、地形、狀態），會整份嵌入
戰鬥狀態，讓「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import Field, PrivateAttr, model_validator

from trpg.content.affix_names import resolve_affix_names
from trpg.content.appearance import AppearanceTable, item_appearance_problems
from trpg.content.battle import (
    OffhandDef,
    OffhandTable,
    StatusDef,
    StatusTable,
    SummonLook,
    TerrainDef,
    TerrainTable,
    UnitTemplate,
    WeaponDef,
    WeaponTable,
)
from trpg.content.composer_rules import ComposerRules
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
from trpg.content.workshop import WorkshopRules, WorkshopTextTable, workshop_problems
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute, Surface

_LOG = logging.getLogger(__name__)

__all__ = [
    "REQUIRED_STATUSES",
    "ContentLibrary",
    "Ruleset",
    "apply_ally_mana_cost",
    "enemy_template_ids",
    "gear_class_problem",
    "gear_reference_problems",
    "load_library",
    "scale_mana_cost",
    "skill_reference_problems",
    "unit_skill_problems",
]

_PERMILLE = 1000

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


def scale_mana_cost(skill: SkillDef, permille: int) -> SkillDef:
    """法力費用乘 ``permille``‰（四捨五入；原本有費用的技能至少 1）；1000 或沒有費用時回傳原物件。

    BAL-4 難度旋鈕用（``trpg.sim.difficulty``）：整數運算、確定性；不驗證預算（只在模擬用）。"""
    mana = skill.cost.mana
    if permille == _PERMILLE or mana == 0:
        return skill
    scaled = max(1, (mana * permille + _PERMILLE // 2) // _PERMILLE)
    return skill.model_copy(update={"cost": skill.cost.model_copy(update={"mana": scaled})})


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


def apply_ally_mana_cost(
    ruleset: Ruleset,
    units: Mapping[str, UnitTemplate],
    enemy_ids: Iterable[str],
    permille: int,
) -> Ruleset:
    """規則包內我方技能的法力費用乘 ``permille``‰（敵方陣容裝備的技能不縮放），回傳新的規則包。

    ``permille`` ＝ 1000 時原樣回傳。只動 ``Ruleset.skills``（戰鬥實際結算的版本）；
    ``ContentLibrary.skills`` 保持內容檔的原始值，預算、閃現、組合器都以原始費用計算（生成技能
    同理：先照原始費用過預算，進規則包時才由 ``Ruleset.with_skills`` 乘倍率）。``load_library``
    以 ``core.ally_mana_cost_permille`` 呼叫一次；模擬的難度覆寫（``trpg.sim.difficulty``）再在
    已縮放的值上乘它自己的倍率。"""
    if permille == _PERMILLE:
        return ruleset
    enemy_skills = {s for i in enemy_ids for s in units[i].skills}
    table = ruleset.skills.model_copy(
        update={
            "skills": tuple(
                s if s.id in enemy_skills else scale_mana_cost(s, permille)
                for s in ruleset.skills.skills
            )
        }
    )
    new_ruleset = ruleset.model_copy(update={"skills": table})
    new_ruleset.model_post_init(None)
    return new_ruleset


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
        permille = self.core.ally_mana_cost_permille
        combined = {**known, **added}
        problems = [
            f"{skill.id}：{p}"
            for skill in added.values()
            for p in skill_reference_problems(skill, self, combined)
        ]
        if problems:
            raise ValueError("；".join(problems))
        new_skills = tuple(scale_mana_cost(s, permille) for s in added.values())  # BAL-4 旋鈕
        merged = SkillTable(skills=(*self.skills.skills, *new_skills))
        rules = self.model_copy(update={"skills": merged})
        rules.model_post_init(None)
        return rules

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
    files: list[tuple[Path, ContentModel]] = field(default_factory=list)
    retier_cache: dict[str, SkillDef] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    """技能照角色階級重配的快取（:func:`trpg.skillgen.skill_tier.retier`，3W-R1）：掛在內容庫上、隨它
    回收；鍵是「技能內容的 SHA-256 ＋ 階級」。不是建構參數，``dataclasses.replace`` 換內容後是新的空
    快取；不參與相等比較。"""

    def loadout_of(self, template: UnitTemplate) -> Loadout:
        """單位範本的裝備快照（``equipment`` 解析成內嵌定義的 :class:`Loadout`；沒有裝備時
        為空）。"""
        if not template.equipment:
            return Loadout()
        return resolve_loadout(template.equipment, self.items, self.affixes)

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


def load_library(  # noqa: PLR0915
    content_dir: Path | None = None,
) -> ContentLibrary:
    """載入並交叉驗證 ``content/`` 下全部戰鬥內容；任何問題都拋出 :class:`ContentError`。"""
    root = default_content_dir() if content_dir is None else content_dir
    files: list[tuple[Path, ContentModel]] = []

    def load[M: ContentModel](rel: str, model: type[M]) -> M:
        path = root / rel
        item = load_content_file(path, model)
        files.append((path, item))
        return item

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
    rule_changes = load("rule_changes.yaml", RuleChangeTable)
    forms = load("forms.yaml", FormTable)
    roguelite = load("roguelite.yaml", RunRules)
    workshop = load("workshop.yaml", WorkshopRules)
    workshop_text = load("workshop_text.yaml", WorkshopTextTable)
    equipment_rules = load("rules/equipment.yaml", EquipmentRules)
    affix_table = load("affixes.yaml", AffixTable)
    item_table = load("items.yaml", ItemTable)
    appearance = load("equipment/appearance.yaml", AppearanceTable)
    item_gen = load("item_gen.yaml", ItemGenRules)
    regions = load("regions.yaml", RegionTable) if (root / "regions.yaml").exists() else None
    races, origins = _load_races(
        root,
        load,
        regions,
        shapes=shapes.by_id(),
        weather=weather.by_id(),
        terrain=terrain.by_id(),
        summons=frozenset(s.id for s in summons.summons),
    )
    try:
        ruleset = Ruleset(
            core=core,
            hit_table=hit_table,
            terrain=terrain,
            statuses=statuses,
            objects=objects,
            surfaces=surfaces,
            interactions=interactions,
            reactions=reactions,
            shapes=shapes,
            primitives=primitives,
            conditions=conditions,
            skill_triggers=skill_triggers,
            stacks=stacks,
            skills=SkillTable(skills=tuple(skills[k] for k in sorted(skills))),
            summons=summons,
            forms=forms,
            rule_changes=rule_changes,
            races=races,
            equipment=equipment_rules,
            keywords=keywords,
            skill_tags=skill_tags,
            gear_names={
                **{w.id: w.name_zh for w in weapons.weapons},
                **{o.id: o.name_zh for o in offhands.offhands},
            },
        )
    except ValueError as exc:
        raise ContentError(root / "rules", str(exc)) from exc
    affixes = affix_table.by_id()
    offhand_map = offhands.by_id()
    items = {
        i.id: i
        if i.offhand is None
        else i.model_copy(update={"offhand_def": offhand_map.get(i.offhand)})
        for i in item_table.items
    }
    weapon_map = weapons.by_id()
    _check_affixes(root, affixes, ruleset, weapon_map)
    try:  # 詞條文字的欄位代入（Phase 3-41a）：數字與名稱從資料填，不寫死在 name_zh
        affixes = resolve_affix_names(affixes, ruleset)
    except (ValueError, KeyError) as exc:
        raise ContentError(root / "affixes.yaml", str(exc)) from exc
    for item in item_table.items:
        problems = item_problems(item, affixes, weapon_map, equipment_rules, offhand_map)
        if problems:
            raise ContentError(root / "items.yaml", "；".join(problems))
    _check_appearance(root, appearance, item_table, keywords)
    _check_item_gen(root, item_gen, affixes)
    gear = _GearCatalog(items=items, affixes=affixes, rules=equipment_rules)

    _check_skills(root, skills, ruleset, budget, weapons=weapon_map, offhands=offhand_map)
    _check_skill_rules(root, ruleset, exclusions, skeletons)
    _check_keywords(root, keywords, ruleset, skills)
    unknown_values = sorted(set(ai_profiles.status_values) - {s.id for s in statuses.statuses})
    if unknown_values:
        raise ContentError(
            root / "ai_profiles.yaml",
            f"status_values 引用了未知的狀態：{', '.join(unknown_values)}",
        )
    units = _load_dir(root / "units", UnitTemplate, files)
    stray = sorted(t for t, u in units.items() if u.summon)
    if stray:
        raise ContentError(root / "units", f"召喚物範本要放在 units/summons/：{', '.join(stray)}")
    _check_units(
        root,
        units,
        weapons=weapon_map,
        skills=skills,
        ruleset=ruleset,
        ai_profiles=ai_profiles,
        gear=gear,
    )
    _check_units(
        root,
        {s.id: s.template for s in summons.summons},
        weapons=weapon_map,
        skills=skills,
        ruleset=ruleset,
        ai_profiles=ai_profiles,
        source=root / "units" / "summons",
    )

    _check_builds(
        root,
        builds,
        units,
        weapons=weapon_map,
        skills=skills,
        ruleset=ruleset,
        ai_profiles=ai_profiles,
        gear=gear,
    )

    maps = _load_dir(root / "maps", MapDef, files)
    terrain_map = terrain.by_id()
    weather_map = weather.by_id()
    for map_id, map_def in maps.items():
        problems = check_map(map_def, terrain_map, core, objects.by_id())
        problems += _map_reference_problems(map_def, units, weather_map)
        if problems:
            raise ContentError(root / "maps" / f"{map_id}.yaml", "；".join(problems))

    map_warnings = _apply_map_themes(maps, regions)
    _check_unit_races(root, {**units, **{b.id: b.hero for b in builds.builds}}, races)

    problems = roguelite_problems(roguelite, maps, units, core.tier_budget)
    if problems:
        raise ContentError(root / "roguelite.yaml", "；".join(problems))
    problems = workshop_problems(workshop, maps, units)
    if problems:
        raise ContentError(root / "workshop.yaml", "；".join(problems))
    dev_starters = DevStarterTable()
    if (root / "dev_starters.yaml").exists():
        dev_starters = load("dev_starters.yaml", DevStarterTable)
        problems = _dev_starter_problems(dev_starters, weapon_map, keywords, skills)
        if problems:
            raise ContentError(root / "dev_starters.yaml", "；".join(problems))
    has_evolution = (root / "skill_evolution.yaml").exists()
    evolution = load("skill_evolution.yaml", EvolutionTable) if has_evolution else EvolutionTable()
    _check_evolution(root, evolution, keywords, skeletons)
    flash = _load_flash(root, load, evolution, skill_triggers)
    skill_scaling = load("skill_scaling.yaml", SkillScalingRules)
    _check_scaling(root, skill_scaling, skills, weapon_map)

    # 我方技能法力費用倍率（BAL-4b，原型專用）：驗證都用內容檔的原始費用，驗證完才縮放
    ruleset = apply_ally_mana_cost(
        ruleset,
        units,
        enemy_template_ids(units, maps, roguelite),
        core.ally_mana_cost_permille,
    )

    return ContentLibrary(
        root=root,
        elements=elements,
        ruleset=ruleset,
        weapons=weapon_map,
        skills=skills,
        units=units,
        maps=maps,
        weather=weather_map,
        ai_profiles=ai_profiles,
        budget=budget,
        composer=composer,
        builds=builds,
        synergies=synergies,
        keywords=keywords,
        exclusions=exclusions,
        skeletons=skeletons,
        roguelite=roguelite,
        workshop=workshop,
        workshop_text=workshop_text,
        affixes=affixes,
        offhands=offhand_map,
        items=items,
        appearance=appearance,
        item_gen=item_gen,
        dev_starters=dev_starters,
        evolution=evolution,
        flash=flash,
        skill_scaling=skill_scaling,
        regions=regions,
        races=races,
        origins=origins,
        modifier_changes=modifier_changes,
        map_warnings=tuple(map_warnings),
        files=files,
    )


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
        look = SummonLook.model_validate(entry.model_dump(exclude={"zh"}))
        template = template.model_copy(update={"look": look})
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
    problems = skill_problems(
        skill,
        ruleset.shapes.by_id(),
        ruleset.primitives.by_id(),
        status_ids={s.id for s in ruleset.statuses.statuses},
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
