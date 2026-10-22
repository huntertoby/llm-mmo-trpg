"""一次載入並交叉驗證全部戰鬥內容：:class:`Ruleset`（規則包）與 :class:`ContentLibrary`。

:class:`Ruleset` 是引擎結算需要的全部規則資料（核心數值、命中表、地形、狀態），會整份嵌入
戰鬥狀態，讓「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import PrivateAttr, model_validator

from trpg.content.appearance import AppearanceTable, item_appearance_problems
from trpg.content.battle import (
    StatusDef,
    StatusTable,
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
from trpg.content.keyword_derive import Facts, SkillKeywords, derive_from_facts, derive_keywords
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.maps import MapDef, SpawnUnitsEvent, check_map
from trpg.content.roguelite import RunRules, roguelite_problems
from trpg.content.rule_changes import RuleChangeDef, RuleChangeTable
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_growth import SkillGrowthRules
from trpg.content.skill_keywords import KeywordRule, KeywordTable
from trpg.content.skill_rules import (
    BudgetRules,
    ExclusionTable,
    SkeletonDef,
    SkillMatch,
    SynergyTable,
)
from trpg.content.skill_triggers import SkillTriggerDef, SkillTriggerTable
from trpg.content.skills import (
    MODIFIER_CHANGES,
    SKELETON_IDS,
    ConditionDef,
    ConditionTable,
    PrimitiveDef,
    PrimitiveTable,
    ShapeDef,
    ShapeTable,
    SkillDef,
    SkillTable,
    granted_skill_problems,
    skill_problems,
    skill_slot_problems,
    weapon_problem,
)
from trpg.content.stacks import StackDef, StackTable
from trpg.content.summons import SummonDef, SummonTable
from trpg.content.weapon_params import set_weapon_param
from trpg.content.workshop import WorkshopRules, workshop_problems
from trpg.shared.errors import ContentError
from trpg.shared.types import Surface

__all__ = [
    "REQUIRED_STATUSES",
    "ContentLibrary",
    "Ruleset",
    "load_library",
    "skill_reference_problems",
    "unit_skill_problems",
]

REQUIRED_STATUSES = (
    "burning",
    "concealed",
    "defending",
    "prone",
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
    rule_changes: RuleChangeTable = RuleChangeTable()
    """規則改變（Phase 3D-6，``content/rule_changes.yaml``）：嵌入規則包，重播不依賴資料檔。"""
    equipment: EquipmentRules = EquipmentRules()
    """裝備的遞減權重與硬上限（Phase 3G-G1，``content/rules/equipment.yaml``）。"""
    keywords: KeywordTable = KeywordTable.model_construct(keywords=())
    """關鍵字推導表（Phase 3G-G2，``content/skill_keywords.yaml``）：裝備的技能強化詞條依關鍵字
    選取技能。嵌入規則包，重播不依賴資料檔。"""
    skill_growth: SkillGrowthRules = SkillGrowthRules()
    """技能成長（Phase 3-26a，``content/skill_growth.yaml``）：技能等級的效果倍率與 5 級小特性。
    嵌入規則包，重播不依賴資料檔。"""

    _keyword_cache: dict[object, SkillKeywords] = PrivateAttr(default_factory=_CacheDict)
    _rule_change_index: dict[str, RuleChangeDef] = PrivateAttr(default_factory=dict)
    _summon_index: dict[str, SummonDef] = PrivateAttr(default_factory=dict)
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

    def summon_def(self, summon_id: str) -> SummonDef:
        """召喚物範本；找不到時拋出 ``KeyError``。"""
        index: dict[str, SummonDef] = self.__pydantic_private__["_summon_index"]  # type: ignore[index]
        return index[summon_id]

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
    affixes: dict[str, AffixDef] = field(default_factory=dict)
    """詞條白名單（``affixes.yaml``，Phase 3G-G1）。"""
    items: dict[str, ItemDef] = field(default_factory=dict)
    """物品（``items.yaml``，Phase 3G-G1；目前只有測試用物品）。"""
    appearance: AppearanceTable | None = None
    """裝備外觀清單（``equipment/appearance.yaml``，Phase 3G-G5a）。"""
    dev_starters: DevStarterTable = field(default_factory=DevStarterTable)
    """開發者起始包（``dev_starters.yaml``，Phase 3-24b2；不是設計規則，玩家介面不顯示）。"""
    evolution: EvolutionTable = field(default_factory=EvolutionTable)
    """3 級分歧進化的模板（``skill_evolution.yaml``，Phase 3-26b）。"""
    files: list[tuple[Path, ContentModel]] = field(default_factory=list)

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
    composer = load("skill_composer.yaml", ComposerRules)
    builds = load("sim/builds.yaml", BuildTable)
    synergies = load("skill_synergies.yaml", SynergyTable)
    keywords = load("skill_keywords.yaml", KeywordTable)
    exclusions = load("skill_exclusions.yaml", ExclusionTable)
    skill_growth = load("skill_growth.yaml", SkillGrowthRules)
    skeletons = _load_dir(root / "skeletons", SkeletonDef, files)
    skills = _load_dir(root / "skills", SkillDef, files)
    summons = _load_summons(root, weapons.by_id(), files)
    rule_changes = load("rule_changes.yaml", RuleChangeTable)
    roguelite = load("roguelite.yaml", RunRules)
    workshop = load("workshop.yaml", WorkshopRules)
    equipment_rules = load("rules/equipment.yaml", EquipmentRules)
    affix_table = load("affixes.yaml", AffixTable)
    item_table = load("items.yaml", ItemTable)
    appearance = load("equipment/appearance.yaml", AppearanceTable)
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
            rule_changes=rule_changes,
            equipment=equipment_rules,
            keywords=keywords,
            skill_growth=skill_growth,
        )
    except ValueError as exc:
        raise ContentError(root / "rules", str(exc)) from exc
    affixes = affix_table.by_id()
    items = item_table.by_id()
    weapon_map = weapons.by_id()
    _check_affixes(root, affixes, ruleset, weapon_map)
    for item in item_table.items:
        problems = item_problems(item, affixes, weapon_map, equipment_rules)
        if problems:
            raise ContentError(root / "items.yaml", "；".join(problems))
    _check_appearance(root, appearance, item_table, keywords)
    gear = _GearCatalog(items=items, affixes=affixes, rules=equipment_rules)

    _check_skills(root, skills, ruleset)
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
        affixes=affixes,
        items=items,
        appearance=appearance,
        dev_starters=dev_starters,
        evolution=evolution,
        files=files,
    )


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
    defs: list[SummonDef] = []
    for summon_id in sorted(templates):
        template = templates[summon_id]
        path = directory / f"{summon_id}.yaml"
        if not template.summon:
            raise ContentError(path, "召喚物範本必須寫 summon: true")
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
    known = {s.id.value for s in ruleset.surfaces.surfaces}
    for variant in skill.variants:
        unknown = [s for s in variant.when.surfaces if s not in known]
        if unknown:
            problems.append(
                f"variants.{variant.id}.when：未知的表面 {', '.join(unknown)}"
                f"（可用：{', '.join(sorted(known))}）"
            )
        form = skill.variant_form(variant.id)
        problems += [
            f"variants.{variant.id}.{p}" for p in skill_reference_problems(form, ruleset, skills)
        ]
    return problems


def _check_skills(root: Path, skills: dict[str, SkillDef], ruleset: Ruleset) -> None:
    """技能引用的形狀、原語、狀態、物件都存在，參數在範圍內。"""
    for skill_id, skill in skills.items():
        problems = skill_reference_problems(skill, ruleset, skills)
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
        for rule in template.reactions or ():
            try:
                check_rule(rule, reaction_index, skills)
            except ValueError as exc:
                raise ContentError(path, str(exc)) from exc
            if rule.reaction in skills and rule.reaction not in template.skills:
                raise ContentError(path, f"反應規則引用了沒有裝備的反應技：{rule.reaction}")
        problems = unit_skill_problems(template, weapons[template.weapon], skills, ruleset.core)
        if problems:
            raise ContentError(path, "；".join(problems))


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
    template: UnitTemplate, weapon: WeaponDef, skills: dict[str, SkillDef], core: CoreRules
) -> list[str]:
    """單位範本裝備的技能是否存在、與武器相容、沒有超過欄位上限（繁體中文，空串列為通過）。"""
    problems: list[str] = []
    equipped: list[SkillDef] = []
    for skill_id in template.skills:
        skill = skills.get(skill_id)
        if skill is None:
            problems.append(f"skills：未知的技能 {skill_id!r}")
            continue
        equipped.append(skill)
        problem = weapon_problem(skill, weapon.weapon_class)
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
