"""一次載入並交叉驗證全部戰鬥內容：:class:`Ruleset`（規則包）與 :class:`ContentLibrary`。

:class:`Ruleset` 是引擎結算需要的全部規則資料（核心數值、命中表、地形、狀態），會整份嵌入
戰鬥狀態，讓「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import PrivateAttr, model_validator

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
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.maps import MapDef, SpawnUnitsEvent, check_map
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_rules import (
    BudgetRules,
    ExclusionTable,
    SkeletonDef,
    SkillMatch,
    SynergyTable,
)
from trpg.content.skill_triggers import SkillTriggerDef, SkillTriggerTable
from trpg.content.skills import (
    SKELETON_IDS,
    ConditionDef,
    ConditionTable,
    PrimitiveDef,
    PrimitiveTable,
    ShapeDef,
    ShapeTable,
    SkillDef,
    SkillTable,
    skill_problems,
    skill_slot_problems,
    weapon_problem,
)
from trpg.content.stacks import StackDef, StackTable
from trpg.content.summons import SummonDef, SummonTable
from trpg.shared.errors import ContentError
from trpg.shared.types import Surface

__all__ = [
    "REQUIRED_STATUSES",
    "ContentLibrary",
    "Ruleset",
    "load_library",
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
        return self

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
    exclusions: ExclusionTable
    skeletons: dict[str, SkeletonDef]
    files: list[tuple[Path, ContentModel]] = field(default_factory=list)

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
    exclusions = load("skill_exclusions.yaml", ExclusionTable)
    skeletons = _load_dir(root / "skeletons", SkeletonDef, files)
    skills = _load_dir(root / "skills", SkillDef, files)
    summons = _load_summons(root, weapons.by_id(), files)
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
        )
    except ValueError as exc:
        raise ContentError(root / "rules", str(exc)) from exc

    _check_skills(root, skills, ruleset)
    _check_skill_rules(root, ruleset, exclusions, skeletons)
    unknown_values = sorted(set(ai_profiles.status_values) - {s.id for s in statuses.statuses})
    if unknown_values:
        raise ContentError(
            root / "ai_profiles.yaml",
            f"status_values 引用了未知的狀態：{', '.join(unknown_values)}",
        )
    units = _load_dir(root / "units", UnitTemplate, files)
    weapon_map = weapons.by_id()
    stray = sorted(t for t, u in units.items() if u.summon)
    if stray:
        raise ContentError(root / "units", f"召喚物範本要放在 units/summons/：{', '.join(stray)}")
    _check_units(
        root, units, weapons=weapon_map, skills=skills, ruleset=ruleset, ai_profiles=ai_profiles
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
    )

    maps = _load_dir(root / "maps", MapDef, files)
    terrain_map = terrain.by_id()
    weather_map = weather.by_id()
    for map_id, map_def in maps.items():
        problems = check_map(map_def, terrain_map, core, objects.by_id())
        problems += _map_reference_problems(map_def, units, weather_map)
        if problems:
            raise ContentError(root / "maps" / f"{map_id}.yaml", "；".join(problems))

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
        exclusions=exclusions,
        skeletons=skeletons,
        files=files,
    )


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


def _check_skills(root: Path, skills: dict[str, SkillDef], ruleset: Ruleset) -> None:
    """技能引用的形狀、原語、狀態、物件都存在，參數在範圍內。"""
    shape_map = ruleset.shapes.by_id()
    primitive_map = ruleset.primitives.by_id()
    condition_map = ruleset.conditions.by_id()
    trigger_map = ruleset.skill_triggers.by_id()
    stack_map = ruleset.stacks.by_id()
    status_ids = {s.id for s in ruleset.statuses.statuses}
    object_ids = {o.id for o in ruleset.objects.objects}
    summon_ids = set(ruleset.summons.by_id())
    for skill_id, skill in skills.items():
        problems = skill_problems(
            skill,
            shape_map,
            primitive_map,
            status_ids=status_ids,
            object_ids=object_ids,
            conditions=condition_map,
            triggers=trigger_map,
            stacks=stack_map,
            dual_min_rarity=ruleset.core.dual_scaling_min_rarity,
            summon_ids=summon_ids,
        )
        if problems:
            raise ContentError(root / "skills" / f"{skill_id}.yaml", "；".join(problems))


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
) -> None:
    """單位範本引用的武器、行為模式、反應與技能都存在且合法（``source``：錯誤訊息指向的檔案）。"""
    reaction_index = ruleset.reactions.by_id()
    for template_id, template in units.items():
        path = source or root / "units" / f"{template_id}.yaml"
        if template.weapon not in weapons:
            raise ContentError(path, f"未知的武器：{template.weapon}")
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
) -> None:
    """build 的英雄範本合法（武器、技能、行為模式），隊友存在，build ID 不與單位範本衝突。"""
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
    )


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
