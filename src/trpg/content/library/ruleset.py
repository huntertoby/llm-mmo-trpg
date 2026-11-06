"""規則包 :class:`Ruleset`（整份嵌入戰鬥狀態）與技能的跨檔案引用檢查
:func:`skill_reference_problems`。"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from pydantic import Field, PrivateAttr, model_validator

from trpg.content.battle import StatusDef, StatusTable, TerrainDef, TerrainTable, UnitTemplate
from trpg.content.environment import (
    InteractionTable,
    ObjectDef,
    ObjectTable,
    ReactionDef,
    ReactionTable,
    SurfaceDef,
    SurfaceTable,
)
from trpg.content.equipment import EquipmentRules
from trpg.content.forms import FormDef, FormTable, scaled_form_def
from trpg.content.keyword_derive import Facts, SkillKeywords, derive_from_facts, derive_keywords
from trpg.content.maps import MapDef, SpawnUnitsEvent
from trpg.content.races import RaceDef, RaceTable
from trpg.content.roguelite import RunRules
from trpg.content.rule_changes import RuleChangeDef, RuleChangeTable
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skill_tags import SkillTagTable
from trpg.content.skill_triggers import SkillTriggerDef, SkillTriggerTable
from trpg.content.skills import (
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
)
from trpg.content.stacks import StackDef, StackTable
from trpg.content.summons import SummonDef, SummonTable
from trpg.shared.types import Surface

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
