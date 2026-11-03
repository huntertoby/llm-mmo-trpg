"""大世界敵人的元素變體與精英詞綴（``content/world/enemies.yaml``，Phase 5A-3）。

``docs/design/09-世界與敘事.md`` 9.6.6（#82）：同一種敵人可換元素、換武器（**變體**）；精英帶
**精英詞綴**（例：狂暴的、再生的）。變體規則與詞綴都是 content 資料；本模組只把它們套到既有的
:class:`~trpg.content.battle.UnitTemplate` 上，產生可以直接放進戰鬥的範本，不新增引擎機制。
雲嶺的變體與詞綴見 ``docs/design/18-雲嶺內容.md`` 18.2.1；對照與代決見
``docs/phases/Phase5計畫.md`` 第 7 節。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, field_validator, model_validator

from trpg.content.battle import (
    ID_PATTERN,
    DollLook,
    OpeningStatus,
    ReactionRule,
    UnitTemplate,
    WeaponDef,
)
from trpg.content.rules import SkillSlots
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillDef, held_gear, skill_slot_problems, weapon_problem

__all__ = [
    "ELITE_TAG",
    "RANGED_TAG",
    "EliteAffixDef",
    "EnemyCatalog",
    "EnemyVariantDef",
    "VariantTheme",
    "WorldEnemies",
    "apply_affix",
    "apply_variant",
    "world_enemies_problems",
]

ELITE_TAG = "elite"
"""精英標籤（同 ``trpg.engine.ids.ELITE_TAG``；content 不匯入引擎，所以另寫一份）。"""
RANGED_TAG = "ranged"
"""用法器但算遠程的範本標籤（符籙師，18.2.1「雲鶴使、符籙師都算遠程」；代決 5A3-7）。"""

type VariantTheme = Literal[
    "physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow", "water"
]
"""變體的外觀元素標記（5A-ART 用；純顯示）。9 種元素＋水（水不是元素，只是表面）。"""

type WeaponClass = Literal["melee", "ranged", "focus"]

_SKILL_ID = r"^skill_[a-z0-9_]+$"


class EnemyVariantDef(ContentModel):
    """元素變體（9.6.6）：以 ``base`` 範本為底，換名字、武器與部分技能。"""

    id: str = Field(pattern=ID_PATTERN)
    base: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    theme: VariantTheme
    weapon: str | None = Field(default=None, pattern=ID_PATTERN)
    """換的武器；``None``＝沿用 base 的武器。"""
    skill_swaps: dict[str, str] = Field(default_factory=dict)
    """舊技能 → 新技能（鍵必須在 base 的 ``skills`` 裡）。"""
    doll: DollLook | None = None
    """變體自己的外觀（Phase 5A-ART4；雷符師換墨灰袍、雷殼甲蟲換元素）；``None``＝沿用 base。
    純顯示資料。"""

    @field_validator("skill_swaps")
    @classmethod
    def _swaps(cls, value: dict[str, str]) -> dict[str, str]:
        bad = [s for pair in value.items() for s in pair if re.match(_SKILL_ID, s) is None]
        if bad:
            raise ValueError(f"技能 ID 格式應為 skill_xxx：{', '.join(sorted(bad))}")
        same = sorted(k for k, v in value.items() if k == v)
        if same:
            raise ValueError(f"換技能的新舊相同：{', '.join(same)}")
        if len(set(value.values())) != len(value):
            raise ValueError("換上的技能不可重複")
        return dict(sorted(value.items()))

    @model_validator(mode="after")
    def _changes_something(self) -> EnemyVariantDef:
        if self.weapon is None and not self.skill_swaps:
            raise ValueError(f"變體 {self.id} 沒有換武器也沒有換技能")
        if self.id == self.base:
            raise ValueError(f"變體 {self.id} 的 ID 不可等於 base")
        return self


class EliteAffixDef(ContentModel):
    """精英詞綴（9.6.6）：加技能與反應規則、HP 倍率，套上的單位成為精英。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    """形容詞（「再生的」），套用後的名字＝詞綴名＋範本名。"""
    add_skills: tuple[str, ...] = ()
    add_reactions: tuple[ReactionRule, ...] = ()
    """加上的反應規則；範本沒寫 ``reactions`` 時先展開成 ``reactions.yaml`` 的預設規則再加。"""
    add_opening_statuses: tuple[OpeningStatus, ...] = ()
    """開場就帶著的狀態（Phase 5A-M1：霧隱的＝開場隱蔽 1 回合），接在範本自己的後面。"""
    hp_permille: int = Field(default=1000, ge=1000, le=5000)
    weapon_classes: tuple[WeaponClass, ...] = ()
    """限定的武器大類；空＝不限。"""
    description_zh: str = ""
    look: str | None = Field(default=None, pattern=ID_PATTERN)
    """精英詞綴的外觀 id（Phase 5A-ART2，``docs/art/敵人外觀.md`` 1.2 的特效：``regen``、
    ``mist_hidden``…）；``None``＝用詞綴 ID。前端不認得時只畫精英金環。"""

    @field_validator("add_skills")
    @classmethod
    def _skills(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        bad = [s for s in value if re.match(_SKILL_ID, s) is None]
        if bad:
            raise ValueError(f"技能 ID 格式應為 skill_xxx：{', '.join(bad)}")
        if len(set(value)) != len(value):
            raise ValueError("加上的技能不可重複")
        return value

    @model_validator(mode="after")
    def _reactions_use_added_skills(self) -> EliteAffixDef:
        stray = sorted(
            r.reaction
            for r in self.add_reactions
            if r.reaction.startswith("skill_") and r.reaction not in self.add_skills
        )
        if stray:
            raise ValueError(f"詞綴 {self.id} 的反應規則引用了沒有加上的反應技：{', '.join(stray)}")
        return self


class WorldEnemies(ContentModel):
    """``content/world/enemies.yaml``：變體與精英詞綴。"""

    variants: tuple[EnemyVariantDef, ...] = ()
    affixes: tuple[EliteAffixDef, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> WorldEnemies:
        for label, ids in (
            ("變體", [v.id for v in self.variants]),
            ("詞綴", [a.id for a in self.affixes]),
        ):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            if dupes:
                raise ValueError(f"{label} ID 重複：{', '.join(dupes)}")
        return self

    def variant_by_id(self) -> dict[str, EnemyVariantDef]:
        return {v.id: v for v in self.variants}

    def affix_by_id(self) -> dict[str, EliteAffixDef]:
        return {a.id: a for a in self.affixes}

    def summary(self) -> str:
        return f"{len(self.variants)} 種元素變體、{len(self.affixes)} 種精英詞綴"


def apply_variant(base: UnitTemplate, variant: EnemyVariantDef) -> UnitTemplate:
    """把變體套到 ``base``：換 ID、名字、武器與技能（順序不變），其餘照 base。"""
    missing = sorted(k for k in variant.skill_swaps if k not in base.skills)
    if missing:
        raise ValueError(f"變體 {variant.id}：base {base.id} 沒有裝備 {', '.join(missing)}")
    skills = tuple(variant.skill_swaps.get(s, s) for s in base.skills)
    swapped = {**variant.skill_swaps}
    reactions = (
        None
        if base.reactions is None
        else tuple(
            r.model_copy(update={"reaction": swapped.get(r.reaction, r.reaction)})
            for r in base.reactions
        )
    )
    return base.model_copy(
        update={
            "id": variant.id,
            "name_zh": variant.name_zh,
            "weapon": variant.weapon or base.weapon,
            "skills": skills,
            "reactions": reactions,
            "doll": variant.doll if variant.doll is not None else base.doll,
        }
    )


def apply_affix(
    template: UnitTemplate, affix: EliteAffixDef, default_rules: tuple[ReactionRule, ...]
) -> UnitTemplate:
    """把精英詞綴套到範本：ID＝``<範本>_<詞綴>``、名字＝詞綴名＋範本名、加 ``elite`` 標籤、
    HP × ``hp_permille``（捨去，至少 1）、加技能、反應規則與開場狀態。不檢查能不能套（見
    :meth:`EnemyCatalog.affix_problem`）。

    本身已是精英的範本（Phase 5B-4c：資料指定的懸賞詞綴）HP 不再乘（代決 5B4c-3）。

    Phase 5A-ART2：範本有外觀（``doll``）時，把詞綴的外觀 id 加進 ``doll.affixes``（純顯示；
    沒有外觀的範本不加，前端依 ``elite`` 標籤只畫金環）。"""
    reactions = template.reactions
    doll = template.doll
    if doll is not None:
        look = affix.look or affix.id
        if look not in doll.affixes:
            doll = doll.model_copy(update={"affixes": (*doll.affixes, look)})
    already_elite = ELITE_TAG in template.tags
    if affix.add_reactions:
        base_rules = default_rules if reactions is None else reactions
        reactions = (*base_rules, *affix.add_reactions)
    return template.model_copy(
        update={
            "id": f"{template.id}_{affix.id}",
            "name_zh": f"{affix.name_zh}{template.name_zh}",
            "max_hp": (
                template.max_hp
                if already_elite
                else max(1, template.max_hp * affix.hp_permille // 1000)
            ),
            "skills": (*template.skills, *affix.add_skills),
            "reactions": reactions,
            "opening_statuses": (*template.opening_statuses, *affix.add_opening_statuses),
            "tags": tuple(sorted({*template.tags, ELITE_TAG})),
            "doll": doll,
        }
    )


@dataclass(frozen=True)
class EnemyCatalog:
    """解析敵人名字（單位範本 ID 或變體 ID）與套用詞綴；遭遇表檢查與 ``trpg.world`` 共用。"""

    units: Mapping[str, UnitTemplate]
    enemies: WorldEnemies | None
    weapons: Mapping[str, WeaponDef]
    skills: Mapping[str, SkillDef]
    slots: SkillSlots
    default_rules: tuple[ReactionRule, ...]

    def has(self, name: str) -> bool:
        """``name`` 是非召喚物的單位範本，或已知的變體。"""
        unit = self.units.get(name)
        if unit is not None:
            return not unit.summon
        return self.enemies is not None and name in self.enemies.variant_by_id()

    def template(self, name: str) -> UnitTemplate:
        """解析名字成範本（變體會套用）；未知時拋 :class:`KeyError`。"""
        if name in self.units:
            return self.units[name]
        variant = None if self.enemies is None else self.enemies.variant_by_id().get(name)
        if variant is None:
            raise KeyError(name)
        return apply_variant(self.units[variant.base], variant)

    def is_ranged(self, template: UnitTemplate) -> bool:
        """遠程（每場上限用）：武器大類 ``ranged``，或帶 ``ranged`` 標籤（代決 5A3-7）。"""
        weapon = self.weapons.get(template.weapon)
        return RANGED_TAG in template.tags or (
            weapon is not None and weapon.weapon_class == "ranged"
        )

    def is_elite(self, template: UnitTemplate) -> bool:
        return ELITE_TAG in template.tags

    def affix(self, affix_id: str) -> EliteAffixDef:
        affix = None if self.enemies is None else self.enemies.affix_by_id().get(affix_id)
        if affix is None:
            raise KeyError(affix_id)
        return affix

    def affix_problem(
        self, template: UnitTemplate, affix_id: str, *, allow_elite: bool = False
    ) -> str | None:
        """詞綴不能套到這個範本的原因（繁體中文）；``None``＝可以。``allow_elite``：資料指定的
        精英（遭遇表的固定精英；Phase 5B-4c 懸賞的指定詞綴）可以套在本身已是精英的範本上；營地
        隨機混精英不行。"""
        affix = self.affix(affix_id)
        weapon = self.weapons[template.weapon]
        if self.is_elite(template) and not allow_elite:
            return f"{template.name_zh}已經是精英"
        if template.speed == 0 or "immovable" in template.tags:
            return f"{template.name_zh}是物件型單位"
        if affix.weapon_classes and weapon.weapon_class not in affix.weapon_classes:
            return f"詞綴「{affix.name_zh}」限定{'、'.join(affix.weapon_classes)}武器"
        return self._skill_problem(template, weapon, affix)

    def _skill_problem(
        self, template: UnitTemplate, weapon: WeaponDef, affix: EliteAffixDef
    ) -> str | None:
        added: list[SkillDef] = []
        for skill_id in affix.add_skills:
            skill = self.skills.get(skill_id)
            if skill_id in template.skills or skill is None:
                return f"{template.name_zh}已經裝備或不認得 {skill_id}"
            problem = weapon_problem(skill, weapon.weapon_class, held_gear(weapon))
            if problem is not None:
                return problem
            added.append(skill)
        equipped = [self.skills[s] for s in template.skills if s in self.skills]
        slot = skill_slot_problems([*equipped, *added], self.slots)
        return slot[0] if slot else None

    def applicable_affixes(self, template: UnitTemplate, affix_ids: tuple[str, ...]) -> list[str]:
        """``affix_ids`` 中可以套到 ``template`` 的詞綴（保持順序）。"""
        return [a for a in affix_ids if self.affix_problem(template, a) is None]

    def with_affix(self, template: UnitTemplate, affix_id: str) -> UnitTemplate:
        return apply_affix(template, self.affix(affix_id), self.default_rules)


def world_enemies_problems(
    enemies: WorldEnemies,
    *,
    units: Mapping[str, UnitTemplate],
    weapons: Mapping[str, WeaponDef],
    skills: Mapping[str, SkillDef],
) -> list[str]:
    """跨檔案檢查（繁體中文、排序；空＝通過）：變體的 base、武器、技能存在，ID 不和範本撞；
    詞綴的技能存在。套用後的範本合不合法由載入端用單位檢查驗證。"""
    problems: list[str] = []
    for variant in enemies.variants:
        where = f"變體 {variant.id}"
        if variant.id in units:
            problems.append(f"{where}：ID 和單位範本重複")
        base = units.get(variant.base)
        if base is None or base.summon:
            problems.append(f"{where}：未知的 base {variant.base}")
        elif missing := sorted(k for k in variant.skill_swaps if k not in base.skills):
            problems.append(f"{where}：base 沒有裝備 {', '.join(missing)}")
        if variant.weapon is not None and variant.weapon not in weapons:
            problems.append(f"{where}：未知的武器 {variant.weapon}")
        unknown = sorted(s for s in variant.skill_swaps.values() if s not in skills)
        if unknown:
            problems.append(f"{where}：未知的技能 {', '.join(unknown)}")
    for affix in enemies.affixes:
        unknown = sorted(s for s in affix.add_skills if s not in skills)
        if unknown:
            problems.append(f"詞綴 {affix.id}：未知的技能 {', '.join(unknown)}")
    return sorted(problems)
