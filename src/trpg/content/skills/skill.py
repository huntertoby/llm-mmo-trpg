"""技能本體 ``SkillDef`` 與 ``SkillTable``。"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.conditions import ConditionSpec
from trpg.content.skills.constants import (
    _ELEMENT_VALUES,
    _GAMBLE_ONLY_FIELDS,
    _MAX_AP_COST,
    _MAX_BRANCH_EFFECTS,
    _MAX_CONSUME_THEN,
    _MAX_COOLDOWN_RESTORE,
    _MAX_DISPLACE,
    _MAX_MASTERY_MODIFIERS,
    _MAX_MODIFIERS,
    _MAX_ZONE_EFFECTS,
    _PERMILLE,
    _ZONE_ONLY_FIELDS,
    ADD_STACK,
    BACKLASH_TYPES,
    CHARGE_THROUGH,
    CONSUME_STACK,
    CONSUME_STATUS,
    CONSUME_THEN_TYPES,
    COPY_SKILL,
    DAMAGE_MULTIPLIER,
    DELAYED_DAMAGE,
    DETONATE_RUNES,
    ENTER_FORM,
    GAMBLE,
    GAMBLE_BRANCH_TYPES,
    GAMBLE_TAG,
    GRANT_SKILL,
    HURL_OBJECT,
    INSCRIBE,
    INTERCEPT,
    MAX_EFFECTS,
    MAX_GRANT_DURATION,
    MAX_ON_KILL_EFFECTS,
    MAX_REFUND_AP,
    MAX_SUMMON_COUNT,
    MAX_VARIANTS,
    MIN_SKILL_CRIT_RANGE,
    ON_KILL_TYPES,
    PAIR_MOVES,
    PAIR_SHAPES,
    PIERCE_SHAPES,
    PLACE_TRAP,
    REFUND_AP,
    REFUND_COOLDOWN,
    RESET_COOLDOWN,
    RESTORE_RESOURCE,
    REVIVE,
    RULE_CHANGE,
    RUNE_BOTH_MESSAGE,
    SACRIFICE_SUMMON,
    SELF_DAMAGE_OF_HIT,
    SELF_MOVES,
    SHADOWSTEP,
    SHADOWSTEP_SHAPES,
    SKELETON_IDS,
    SKILL_ID_PATTERN,
    SPLIT_SKELETONS,
    SUMMON,
    WIELDING_EFFECT_ONLY,
    WIELDING_WEAPON,
    ZONE,
    ZONE_CASTER_SHAPES,
    ZONE_EFFECT_TYPES,
    ZONE_MOVING_SHAPES,
    Activation,
    Mastery,
    SkillCategory,
    SkillKind,
    SkillRarity,
    WeaponReq,
    _unique,
)
from trpg.content.skills.effects import (
    EffectSpec,
    ShapeSpec,
    SkillRuleError,
    _check_composition,
    composition_shapes,
    error_path_of,
    true_only_params,
)
from trpg.content.skills.followup import _FOLLOWUP_CHECKS
from trpg.content.skills.modifiers import ModifierSpec
from trpg.content.skills.reactions import ReactionSpec, TrapSpec
from trpg.content.skills.shapes import ShapeDef
from trpg.content.skills.specs import FollowupSpec, NarrativeDef, Provenance, SkillCost, TriggerSpec
from trpg.content.skills.variants import VariantSpec, walk_effect
from trpg.shared.bonus_text import bonus_text
from trpg.shared.types import Attribute, Element

if TYPE_CHECKING:
    from trpg.content.battle import WeaponDef
    from trpg.content.rules import CoreRules


_FOLLOWUP_CACHE: dict[int, tuple[Any, Any]] = {}


_FOLLOWUP_CACHE_LIMIT = 4096


_VARIANT_CACHE: dict[tuple[int, str], tuple[Any, Any]] = {}
"""變奏型態（:meth:`SkillDef.variant_form`）的快取：以技能物件的 ``id`` 與變奏 ID 為鍵
（值保留原物件，避免 ``id`` 重用時取錯）。"""


class SkillDef(ContentModel):
    """一個技能（``content/skills/<id>.yaml``）。"""

    id: str = Field(pattern=SKILL_ID_PATTERN)
    schema_version: Literal[1] = 1
    name_zh: str = Field(min_length=1)
    description_zh: str | None = None
    tier: int = Field(ge=1, le=5)
    rank: int = Field(default=1, ge=1, le=5)
    rarity: SkillRarity
    kind: SkillKind = "active"
    skeleton: str
    category: SkillCategory
    weapon_req: WeaponReq
    weapon_only: tuple[str, ...] = ()
    """限定武器（Phase 3I-5，6.10 #50 專屬招牌技）：非空時，只有主手武器或副手的 ID 在這份清單裡
    （``weapons.yaml``、``offhands.yaml``）才能裝備、施放這個技能；空 ＝ 不限（照 ``weapon_req``）。
    與 ``weapon_req`` 並存：兩者都要符合。只有火器、盾、成對武器、鞭的招牌技使用。"""
    ap_cost: int | None = None
    scaling_attr: Attribute
    secondary_scaling_attr: Attribute | None = None
    """第二縮放屬性（Phase 2H-2）：與 ``scaling_attr`` 各占 50%（取平均，無條件捨去）。
    最低稀有度由 ``core.yaml`` 的 ``dual_scaling_min_rarity`` 決定（跨檔案檢查）。"""
    mastery: Mastery | None = None
    """專精加成（Phase 2H-2）：施放者的 ``scaling_attr`` 基礎屬性是自己所有屬性中最高（含並列）
    時生效——``range`` 施放距離 +1、``duration`` 此技能施加的狀態持續 +1。雙屬性技能不可設定。"""
    shape: ShapeSpec
    effects: tuple[EffectSpec, ...]
    condition: ConditionSpec | None = None
    trigger: TriggerSpec | None = None
    reaction: ReactionSpec | None = None
    trap: TrapSpec | None = None
    cost: SkillCost = Field(default_factory=SkillCost)
    crit_range: int | None = Field(default=None, ge=MIN_SKILL_CRIT_RANGE, le=19)
    """擴大暴擊範圍（Phase 3D-7b，6.17 B）：自然骰不小於它就暴擊（17 ＝ 17–20）；取技能與武器
    （法術技為 20）中較寬的。需要有傷害效果。"""
    damage_permille: int | None = Field(default=None, ge=100, le=_PERMILLE - 1)
    """基礎傷害折扣（Phase 3D-7b，6.17 B）：技能的每個傷害效果再 × 它（‰；750 ＝ −25%），
    例如高變異技能用較低的基礎傷害換取暴擊與爆骰。需要有傷害效果。"""
    pierce: bool = False
    """穿透（Phase 3C-5b，6.15）：無視半掩護，並穿過 ``penetrable`` 物件（物件受全額傷害，後方目標
    受 ``core.pierce_behind_permille``）。只能用在遠程的單體或直線形狀。"""
    include_caster: bool = False
    """影響範圍也包含施放者自己（Phase 3D-3）：修正規則 ``allow_self_target`` 套用後的技能才會是
    ``true``（引擎在施放前複製出變形後的技能，見 :func:`trpg.engine.modifiers.shaped_skill`），
    資料檔不必寫。只對有友方效果、形狀不含施放者的技能有意義。"""
    modifiers: tuple[ModifierSpec, ...] = ()
    """修正規則（Phase 3C-2；只有 ``kind: modifier`` 可以有，1～2 條）。"""
    activation: Activation | None = None
    """常駐類傳說的啟動方式（Phase 3D-6）：修正型傳說（``kind: modifier``）與規則改變型傳說
    （``rule_change`` 原語）必填，其他技能不可填。以 ``UseSkill`` 花 ``legendary_activation_ap``
    AP ＋ 源力啟動；啟動前修正規則與規則改變都不生效。"""
    exclusive_group: str | None = Field(default=None, pattern=ID_PATTERN)
    """互斥群組（Phase 3-33f1，6.29.4）：同一群組的技能不能同時裝備（例如普攻精通、群召、精英召喚
    都是 ``mastery``）；只有修正型被動可以填。檢查在 :func:`skill_slot_problems`。"""
    tags: tuple[str, ...] = ()
    element: Element | None = None
    """技能元素（主題元素，Phase 3-54d，06 6.33「大地元素的判定與限制」）：填了就以它為準，不論有沒
    有
    傷害效果（可以做出沒有傷害、只有隆起或下陷的大地技能）；省略時沿用 ``tags`` 裡的元素名稱
    （手寫技能的主題標籤、組合器的主題元素）。見 :func:`skill_elements`。"""
    narrative: NarrativeDef = Field(default_factory=NarrativeDef)
    provenance: Provenance = Field(default_factory=Provenance)
    followup: FollowupSpec | None = None
    """複合技能的第二段（Phase 3F-3a，6.23）：有它的技能本身是第一段，``followup.when`` 決定第二段
    何時、以哪裡為原點結算（見 :class:`FollowupSpec`、:meth:`followup_skill`）。"""
    variants: tuple[VariantSpec, ...] = ()
    """戰場變奏（Phase 3-25a，6.24）：0～2 個，條件成立時施放的是變奏型態（:meth:`variant_form`）；
    多個成立時取排在前面的。只有主動技能可以帶；稀有度上限是跨檔案檢查（``core.yaml``）。"""
    budget_bonus_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """閃現（靈光一閃，Phase 3W-1，6.34.3）提高的預算上限（‰，佔同階預算）：可用預算再 ×（1000 ＋
    它）÷ 1000。每閃一次 +40‰、完整技能 +120‰（``flash_templates.yaml``）；省略＝沒有加成。只影響
    預算驗證與重調，不影響結算（結算只看技能本身的數值）。"""

    stance_upkeep: int = Field(default=0, ge=0, le=2)
    """姿態的維持費（Phase 3W-2b，6.34.4「費用」類）：每個自己的回合開始，一般姿態（不含形態）付
    這麼多點（武器技扣耐力、法術技扣法力，每點數量見 ``forms.yaml``）；付不起就自動解除姿態。
    維持費換到預算折抵（``allowance.stance_upkeep_per_point``）；0＝免費。"""

    @field_validator("skeleton")
    @classmethod
    def _skeleton(cls, value: str) -> str:
        if value not in SKELETON_IDS:
            raise ValueError(f"未知的骨架 {value!r}（可用：{', '.join(SKELETON_IDS)}）")
        return value

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        bad = [t for t in value if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"標籤必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(value)) != len(value):
            raise ValueError("標籤不可重複")
        return value

    @model_validator(mode="after")
    def _check_element(self) -> SkillDef:
        clash = [t for t in self.tags if t in _ELEMENT_VALUES and t != self.element]
        if self.element is not None and any(t != Element.PHYSICAL.value for t in clash):
            raise ValueError(
                f"技能元素 {self.element.value} 與標籤的元素不一致：{', '.join(clash)}"
            )
        return self

    @model_validator(mode="after")
    def _check_exclusive_group(self) -> SkillDef:
        if self.exclusive_group is not None and self.kind != "modifier":
            raise ValueError("只有修正型被動（kind: modifier）可以填 exclusive_group")
        return self

    @model_validator(mode="after")
    def _check(self) -> SkillDef:
        if self.kind == "modifier":
            self._check_modifier()
        else:
            if not 1 <= len(self.effects) <= MAX_EFFECTS:
                raise ValueError(
                    f"效果原語必須有 1 到 {MAX_EFFECTS} 個，收到 {len(self.effects)} 個"
                )
            if self.modifiers:
                raise ValueError(
                    f"只有修正技能（kind: modifier）可以有 modifiers，收到 {self.kind}"
                )
        if self.kind == "active":
            if self.ap_cost is None or not 1 <= self.ap_cost <= _MAX_AP_COST:
                raise ValueError(
                    f"主動技能的 ap_cost 必須是 1 到 {_MAX_AP_COST}，收到 {self.ap_cost}"
                )
        elif self.ap_cost is not None:
            raise ValueError(f"{self.kind} 技能的 ap_cost 必須為 null（不花 AP）")
        self._check_self_costs()
        _check_composition(self.kind, self.effects)
        self._check_legendary()
        self._check_copy_skill()
        self._check_hurl_object()
        self._check_pierce()
        self._check_self_moves()
        self._check_pair_moves()
        self._check_summon()
        self._check_zone()
        self._check_runes()
        self._check_sacrifice()
        self._check_gamble()
        self._check_revive()
        self._check_delayed_damage()
        self._check_grant_skill()
        if self.kind == "passive" and self.trigger is None:
            raise ValueError("被動技能（kind: passive）必須有 trigger")
        if self.kind != "passive" and self.trigger is not None:
            raise ValueError(f"只有被動技能可以有 trigger，收到 kind: {self.kind}")
        self._check_reaction_and_stance()
        self._check_stance_upkeep()
        self._check_trap_and_stacks()
        self._check_scaling_and_mastery()
        self._check_gear_limits()
        allowed = ("melee", "ranged") if self.category == "weapon" else ("focus", "any")
        if self.weapon_req not in allowed:
            name = "武器技" if self.category == "weapon" else "法術技"
            raise ValueError(
                f"{name}（category: {self.category}）的 weapon_req 只能是 "
                f"{'、'.join(allowed)}，收到 {self.weapon_req}"
            )
        for index, effect in enumerate(self.effects):
            self._check_effect(f"effects[{index}]", effect, top=True)
        self._check_variance()
        self._add_gamble_tag()
        self._check_followup()
        self._check_variants()
        return self

    def _check_variants(self) -> None:
        """戰場變奏（Phase 3-25a，PM 決定 #1、#7）：最多 2 個、ID 不重複；只有主動技能（不是陷阱、
        不是複合技能、不是常駐類傳說）可以帶；每個型態本身也要是合法的技能（:meth:`variant_form`
        以同一套 schema 檢查）。"""
        if not self.variants:
            return
        if len(self.variants) > MAX_VARIANTS:
            raise ValueError(f"一招技能最多 {MAX_VARIANTS} 個變奏，收到 {len(self.variants)} 個")
        ids = [v.id for v in self.variants]
        if len(set(ids)) != len(ids):
            raise ValueError(f"變奏的 id 不可重複：{', '.join(ids)}")
        if self.kind != "active" or self.trap is not None:
            raise ValueError("只有主動技能可以帶變奏（被動、反應、姿態、陷阱之後再開放）")
        if self.followup is not None:
            raise ValueError("複合技能（有 followup）不能帶變奏")
        if self.is_activatable:
            raise ValueError("常駐類傳說（有 activation）不能帶變奏")
        for index, variant in enumerate(self.variants):
            self._check_variant(index, variant)
            try:
                self.variant_form(variant.id)
            except ValueError as exc:
                raise SkillRuleError(
                    f"變奏「{variant.name_zh}」：{exc}",
                    path=self.variant_error_path(index, error_path_of(str(exc))),
                ) from None

    def variant_error_path(self, index: int, inner: str = "") -> str:
        """變奏型態裡的錯誤路徑 → 技能（提議）裡的路徑（Phase 4-L10a）：型態的 ``effects[j]`` 是
        變奏換上的效果時指向 ``variants[i].replace_effect.effect``、加上的效果時指向
        ``variants[i].add_effect``，其餘是基礎技能自己的效果（原樣）；形狀錯誤在變奏有換形狀時指向
        ``variants[i].shape``；``when`` 指向 ``variants[i].when``；沒有路徑時指向
        ``variants[i]``。"""
        variant = self.variants[index]
        base = f"variants[{index}]"
        match = re.match(r"effects\[(\d+)\](.*)$", inner)
        if match is not None:
            position, rest = int(match.group(1)), match.group(2)
            swap = variant.replace_effect
            if swap is not None and position == swap.index:
                return f"{base}.replace_effect.effect{rest}"
            if variant.add_effect is not None and position == len(self.effects):
                return f"{base}.add_effect{rest}"
            return inner
        if inner.startswith("shape"):
            return f"{base}.{inner}" if variant.shape is not None else inner
        if not inner or inner.startswith("when"):
            return f"{base}.{inner}" if inner else base
        return inner

    def iter_effects(
        self,
        *,
        include_followup: bool = False,
        include_variants: bool = False,
        include_backlash: bool = False,
        include_modifiers: bool = False,
    ) -> Iterator[EffectSpec]:
        """技能所有層級的效果（Phase 3E-2a 統一走訪）：``effects`` 與其巢狀的 ``then``、賭注
        ``win``／``lose``、擊殺時效果 ``on_kill``、區域子效果 ``effects``（zone）。陷阱技能的觸發
        效果就是 ``effects``，自然包含在內。

        - ``include_followup``：複合技能第二段的效果；
        - ``include_variants``：每個變奏的 ``add_effect``、``replace_effect.effect``（尚未套用到
          基礎效果上的原始內容；要看變奏型態的完整效果請走 :meth:`variant_form`）；
        - ``include_backlash``：失手反噬 ``cost.on_miss``；
        - ``include_modifiers``：修正規則的命中後效果 ``change.on_hit_effects``。
        """
        roots: list[EffectSpec] = list(self.effects)
        if include_followup and self.followup is not None:
            roots += self.followup.effects
        if include_backlash:
            roots += self.cost.on_miss
        if include_modifiers:
            for rule in self.modifiers:
                roots += rule.change.on_hit_effects or ()
        if include_variants:
            for variant in self.variants:
                if variant.add_effect is not None:
                    roots.append(variant.add_effect)
                if variant.replace_effect is not None:
                    roots.append(variant.replace_effect.effect)
        for root in roots:
            yield from walk_effect(root)

    def _check_variant(self, position: int, variant: VariantSpec) -> None:
        main = self.main_damage_index
        swap = variant.replace_effect
        at = f"variants[{position}]"
        if swap is not None:
            where = f"{at}.replace_effect.index"
            if len(self.effects) == 1:
                raise SkillRuleError(
                    f"變奏「{variant.name_zh}」：唯一的效果不能被 replace_effect 換掉", path=where
                )
            if swap.index >= len(self.effects):
                raise SkillRuleError(
                    f"變奏「{variant.name_zh}」：replace_effect.index {swap.index} 超出效果數"
                    f" {len(self.effects)}",
                    path=where,
                )
            if swap.index == main:
                raise SkillRuleError(
                    f"變奏「{variant.name_zh}」：主傷害（第 {main} 個效果）不能被換掉", path=where
                )
        if variant.element is not None and main is None:
            raise SkillRuleError(
                f"變奏「{variant.name_zh}」：沒有傷害效果，不能換元素（element）",
                path=f"{at}.element",
            )
        if variant.range_delta is not None:
            shape = variant.shape or self.shape
            if not isinstance(shape.range, int):
                raise SkillRuleError(
                    f"變奏「{variant.name_zh}」：range_delta 只能用在射程是數字的形狀，"
                    f"收到 {shape.type} 的射程 {shape.range!r}",
                    path=f"{at}.range_delta",
                )

    @property
    def main_damage_index(self) -> int | None:
        """主傷害：第一個 ``damage`` 效果的索引（沒有時為 ``None``）。"""
        return next((i for i, e in enumerate(self.effects) if e.type == "damage"), None)

    def variant(self, variant_id: str) -> VariantSpec:
        """ID 為 ``variant_id`` 的變奏；沒有時拋出 ``KeyError``。"""
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        raise KeyError(f"{self.id} 沒有變奏 {variant_id}")

    def variant_form(self, variant_id: str) -> SkillDef:
        """變奏型態（Phase 3-25a）：本技能套上變奏的替換內容，展開成一個獨立的技能（沒有
        ``variants``；ID、名稱、代價、骨架都不變）。依序套用：換形狀 → 射程 ± → 換掉附帶效果 →
        加附帶效果 → 換所有傷害效果的元素。引擎施放、驗證器與預算都用它。"""
        key = (id(self), variant_id)
        cached = _VARIANT_CACHE.get(key)
        if cached is not None and cached[0] is self:
            found: SkillDef = cached[1]
            return found
        variant = self.variant(variant_id)
        shape = variant.shape or self.shape
        if variant.range_delta is not None and isinstance(shape.range, int):
            shape = shape.model_copy(update={"range": max(1, shape.range + variant.range_delta)})
        effects = list(self.effects)
        if variant.replace_effect is not None and variant.replace_effect.index < len(effects):
            effects[variant.replace_effect.index] = variant.replace_effect.effect
        if variant.add_effect is not None:
            effects.append(variant.add_effect)
        if variant.element is not None:
            effects = [
                e.model_copy(update={"element": variant.element}) if e.type == "damage" else e
                for e in effects
            ]
        data = {name: getattr(self, name) for name in type(self).model_fields}
        data.update(shape=shape, effects=tuple(effects), variants=())
        try:
            form = SkillDef.model_validate(data)
        except ValidationError as exc:
            messages = "；".join(str(e["msg"]).removeprefix("Value error, ") for e in exc.errors())
            raise ValueError(messages) from None
        if len(_VARIANT_CACHE) >= _FOLLOWUP_CACHE_LIMIT:
            _VARIANT_CACHE.clear()
        _VARIANT_CACHE[key] = (self, form)
        return form

    def _check_followup(self) -> None:
        """複合技能（Phase 3F-3a／3F-4a，6.23）：主動技能、不是陷阱、沒有失手反噬；兩段的結構依
        ``followup.when`` 檢查（:data:`_FOLLOWUP_CHECKS`）；兩段合計最多 4 個效果；第二段本身也要
        是合法的技能（:meth:`followup_skill` 以同一套 schema 檢查）。"""
        follow = self.followup
        if follow is None:
            return
        if self.kind != "active":
            raise ValueError(f"只有主動技能可以有 followup（複合技能），收到 kind: {self.kind}")
        if self.trap is not None or self.cost.on_miss:
            raise ValueError("複合技能不能是陷阱，也不能有失手反噬 cost.on_miss")
        if follow.release is not None and follow.when != "delayed":
            raise ValueError(
                f"只有延遲段（when: delayed）可以指定 release，收到 when: {follow.when}"
            )
        _FOLLOWUP_CHECKS[follow.when](self.effects, self.shape, follow)
        total = len(self.effects) + len(follow.effects)
        if total > MAX_EFFECTS:
            raise ValueError(f"複合技能兩段合計最多 {MAX_EFFECTS} 個效果，收到 {total} 個")
        try:
            self.followup_skill()
        except ValueError as exc:
            raise ValueError(f"followup：{exc}") from None

    def followup_skill(self) -> SkillDef | None:
        """複合技能的動作段，展開成一個獨立的技能（Phase 3F-3a）：沿用本技能的 ID、名稱、類別、
        武器需求、縮放屬性、階級、稀有度與代價，骨架、形狀、效果與條件換成 ``followup`` 的。引擎以
        它結算動作段（命中、傷害照常），驗證器與預算以它檢查動作段；沒有 ``followup`` 時為
        ``None``。"""
        if self.followup is None:
            return None
        cached = _FOLLOWUP_CACHE.get(id(self))
        if cached is not None and cached[0] is self:
            derived: SkillDef = cached[1]
            return derived
        follow = self.followup
        data = {name: getattr(self, name) for name in type(self).model_fields if name != "followup"}
        data.update(
            skeleton=follow.skeleton,
            shape=follow.shape,
            effects=follow.effects,
            condition=follow.condition,
        )
        try:
            derived = SkillDef.model_validate(data)
        except ValidationError as exc:
            messages = "；".join(str(e["msg"]).removeprefix("Value error, ") for e in exc.errors())
            raise ValueError(messages) from None
        if len(_FOLLOWUP_CACHE) >= _FOLLOWUP_CACHE_LIMIT:
            _FOLLOWUP_CACHE.clear()
        _FOLLOWUP_CACHE[id(self)] = (self, derived)
        return derived

    def move_segment(self) -> SkillDef:
        """複合技能的第一段（去掉 ``followup`` 的本技能；「位移 → 動作」為位移段）；不是複合技能時
        回傳自己。"""
        if self.followup is None:
            return self
        return self.model_copy(update={"followup": None})

    def _add_gamble_tag(self) -> None:
        """帶賭博機制的技能自動加標籤 ``gamble``（傾向向量與「用法決定進化」用；Phase 3D-7a）。"""
        if self.is_gamble and GAMBLE_TAG not in self.tags:
            object.__setattr__(self, "tags", (*self.tags, GAMBLE_TAG))

    def _check_self_costs(self) -> None:
        """自己付的代價（``cost.self_status``、``cost.overdraft``，2H-1、3-50）只有主動技能可以用。"""
        for name in ("self_status", "overdraft"):
            if getattr(self.cost, name) is not None and self.kind != "active":
                raise ValueError(f"只有主動技能可以有 cost.{name}，收到 kind: {self.kind}")

    def _check_legendary(self) -> None:
        """傳說技能（Phase 3C-4a、3D-6，6.14.4）必須花源力（``cost.source``），非傳說不能花。核心
        三擇一（改寫規則型原語、修正規則、規則改變）是跨檔案檢查（:func:`skill_problems`）。

        常駐類傳說（修正型 ``kind: modifier``、規則改變型 ``rule_change``）必須寫 ``activation``，
        其他技能不可寫；修正型傳說是唯一可以花源力的非主動技能。
        """
        if self.rarity == "legendary" and self.cost.source is None:
            raise ValueError("傳說技能必須有 cost.source（花 1 或 2 點源力）")
        if self.rarity != "legendary" and self.cost.source is not None:
            raise ValueError(f"只有傳說技能可以有 cost.source，收到稀有度 {self.rarity}")
        if self.cost.source is not None and self.kind not in ("active", "modifier"):
            raise ValueError(
                f"只有主動技能與修正型傳說可以花源力（cost.source），收到 kind: {self.kind}"
            )
        lasting = self.rarity == "legendary" and (
            self.kind == "modifier" or any(e.type == RULE_CHANGE for e in self.effects)
        )
        if lasting and self.activation is None:
            raise ValueError("修正型與規則改變型傳說必須寫 activation（timed 限時或 battle 整場）")
        if not lasting and self.activation is not None:
            raise ValueError("只有修正型與規則改變型傳說可以寫 activation")
        self._check_rule_change()

    def _require_shape(self, primitive: str, label: str | None = None) -> None:
        """形狀必須在原語 YAML 的 ``allowed_shapes`` 內（Phase 4-L5b：資料的唯一來源）。"""
        shapes = composition_shapes(primitive)
        if shapes and self.shape.type not in shapes:
            subject = label or f"{primitive} 的"
            allowed = "、".join(shapes)
            raise SkillRuleError(
                f"{subject}形狀必須是 {allowed}，收到 {self.shape.type}", path="shape.type"
            )

    def _check_rule_change(self) -> None:
        """``rule_change``（Phase 3D-6）：主動技能、形狀 ``self``、技能唯一的效果、對象 ``self``，
        而且是傳說（``activation`` 由 :meth:`_check_legendary` 檢查）。主動、唯一效果與形狀的資料在
        ``skill_primitives.yaml``（:func:`_check_composition`）。"""
        changes = [e for e in self.effects if e.type == RULE_CHANGE]
        if not changes:
            return
        if self.rarity != "legendary":
            raise ValueError(f"rule_change 只能用在傳說技能，收到稀有度 {self.rarity}")
        self._require_shape(RULE_CHANGE, "rule_change 技能的")

    def _check_copy_skill(self) -> None:
        """``copy_skill``（Phase 3C-4b）：主動技能、形狀 ``self``，而且是唯一的效果（複製的技能自己
        有目標，由玩家或 AI 在施放時另選）。資料在 ``skill_primitives.yaml``。"""
        if any(e.type == COPY_SKILL for e in self.effects):
            self._require_shape(COPY_SKILL, "copy_skill 技能的")

    def _check_hurl_object(self) -> None:
        """``hurl_object``（Phase 3C-5a）與形狀 ``object_then_tile`` 必須一起出現：主動技能、
        恰好一個投擲效果（物件只有一個）。原語這一側（主動、最多一個、形狀）的資料在
        ``skill_primitives.yaml``；形狀這一側（形狀要求這個原語）留在程式。"""
        hurls = sum(1 for e in self.effects if e.type == HURL_OBJECT)
        if self.shape.type == "object_then_tile" and hurls != 1:
            raise ValueError("形狀 object_then_tile 的技能必須恰好有一個 hurl_object 效果")
        if hurls:
            self._require_shape(HURL_OBJECT)

    def _check_self_moves(self) -> None:
        """自身位移（Phase 3D-2）：``charge_through`` 的形狀、``shadowstep`` 的落點。
        只能用在主動技能、``dash``／``charge_through``／``shadowstep`` 必須是第一個效果的資料在
        ``skill_primitives.yaml``；位移原語最多一個是跨原語的群組規則（都在
        :func:`_check_composition`）。"""
        types = [e.type for e in self.effects]
        if CHARGE_THROUGH in types:
            self._require_shape(CHARGE_THROUGH)
        if SHADOWSTEP in types:
            self._check_shadowstep()

    def _check_shadowstep(self) -> None:
        """``shadowstep``（Phase 3D-8d）：``landing`` 必填，``choose`` 搭配形狀 ``unit_then_tile``、
        ``behind`` 搭配形狀 ``single``（依參數決定形狀，留在程式）。"""
        landing = self.effects[0].landing
        if landing is None:
            raise SkillRuleError(
                "shadowstep 必須填 landing（choose 或 behind）", path="effects[0].landing"
            )
        shape = SHADOWSTEP_SHAPES[landing]
        if self.shape.type != shape:
            raise SkillRuleError(
                f"shadowstep 的 landing: {landing} 必須搭配形狀 {shape}，收到 {self.shape.type}",
                path="shape.type",
            )

    def _check_summon(self) -> None:
        """召喚（Phase 3D-4a）：``count`` 目前只能是 1（或數量型分歧進化的 2）。只能用在主動技能、
        最多一個、形狀 ``ground_tile``、其餘效果必須明寫 ``affects: self``（選的格子是召喚位置，
        必須是空格）的資料在 ``skill_primitives.yaml``。"""
        summons = [e for e in self.effects if e.type == SUMMON]
        if not summons:
            return
        count = summons[0].count or 1
        if count not in (1, MAX_SUMMON_COUNT):
            raise ValueError(f"summon 的 count 只能是 1 或 {MAX_SUMMON_COUNT}，收到 {count}")
        power = summons[0].power_permille
        if count > 1 and (power is None or power >= _PERMILLE):
            raise ValueError(
                "summon 的 count: 2 必須填小於 1000 的 power_permille（數量型分歧進化）"
            )
        if count == 1 and power is not None and power < _PERMILLE:
            raise ValueError(
                "只召喚一隻時 power_permille 不能小於 1000（大於 1000 是完整技能的強化）；"
                "小於 1000 是數量型分歧進化，必須搭配 count: 2"
            )

    def _check_revive(self) -> None:
        """復活（Phase 3D-8b）：必須填 ``hp_permille``。只能用在主動技能、最多一個、形狀
        ``single``（選一個倒下的友方）、其餘效果必須明寫 ``affects: self`` 的資料在
        ``skill_primitives.yaml``。
        「每場限一次或冷卻至少幾回合」是跨檔案檢查（``skillgen.validate``）。"""
        revives = [e for e in self.effects if e.type == REVIVE]
        if not revives:
            return
        self._require_shape(REVIVE)
        if revives[0].hp_permille is None:
            raise ValueError("revive 必須填 hp_permille")

    def _check_grant_skill(self) -> None:
        """暫時獲得技能（Phase 3D-8c）：``skill`` 與 ``duration`` 必填（只能用在主動技能、
        最多一個的資料在 ``skill_primitives.yaml``）。被給技能本身的限制（一般主動技能、不是傳說、
        不含改寫規則型原語、不是 ``grant_skill``）是跨檔案檢查
        （:func:`granted_skill_problems`）。"""
        grants = [e for e in self.effects if e.type == GRANT_SKILL]
        if not grants:
            return
        grant = grants[0]
        if grant.skill is None or grant.duration is None:
            raise ValueError("grant_skill 必須填 skill 與 duration")
        if grant.skill == self.id:
            raise ValueError("grant_skill 不能給出自己")
        if grant.duration > MAX_GRANT_DURATION:
            raise ValueError(
                f"grant_skill 的 duration 最多 {MAX_GRANT_DURATION}，收到 {grant.duration}"
            )

    def _check_delayed_damage(self) -> None:
        """定時炸彈（Phase 3D-8b）：只能用在法術技；``dice``、``element``、``rounds``、
        ``radius`` 都必填（只能用在主動技能、最多一個的資料在 ``skill_primitives.yaml``）。"""
        bombs = [e for e in self.effects if e.type == DELAYED_DAMAGE]
        if not bombs:
            return
        if self.category != "spell":
            raise SkillRuleError("delayed_damage 只能用在主動的法術技", path="category")
        bomb = bombs[0]
        if bomb.dice is None or bomb.element is None or bomb.rounds is None or bomb.radius is None:
            raise ValueError("delayed_damage 必須填 dice、element、rounds、radius")

    def _check_on_kill(self, at: str, effect: EffectSpec, *, top: bool) -> None:
        """``on_kill``（Phase 3D-8b）：只有主動技能自己的 ``damage`` 效果可以有；內容 1–2 個、類型在
        :data:`ON_KILL_TYPES`、對象只能是施放者；``refund_ap`` 與 ``refund_cooldown`` 只能出現在
        ``on_kill`` 裡。"""
        where = f"{at}（{effect.type}）"
        if effect.type in (REFUND_AP, REFUND_COOLDOWN):
            raise ValueError(f"{where}：{effect.type} 只能出現在 on_kill 裡")
        if effect.on_kill is None:
            return
        if effect.type != "damage":
            raise ValueError(f"{where}：只有 damage 使用 on_kill")
        if not top or self.kind != "active":
            raise ValueError(f"{where}：on_kill 只能用在主動技能自己的傷害效果")
        subs = effect.on_kill
        if not 1 <= len(subs) <= MAX_ON_KILL_EFFECTS:
            raise ValueError(f"{where}：on_kill 必須有 1 到 {MAX_ON_KILL_EFFECTS} 個效果")
        for i, sub in enumerate(subs):
            self._check_on_kill_sub(f"{at}.on_kill[{i}]", sub)

    def _check_on_kill_sub(self, path: str, sub: EffectSpec) -> None:
        """``on_kill`` 的一個效果：類型、對象與各類型自己的欄位（``path`` 是完整路徑，4-L10a）。"""
        at = f"{path}（{sub.type}）"
        if sub.type not in ON_KILL_TYPES:
            raise ValueError(f"{at}：只能使用 {'、'.join(ON_KILL_TYPES)}")
        if sub.condition is not None or sub.affects not in (None, "self"):
            raise ValueError(
                f"{at}：對象只能是施放者（省略 affects 或寫 self），不可自帶 condition"
            )
        if sub.type == REFUND_AP:
            if sub.amount is None or not 1 <= sub.amount <= MAX_REFUND_AP:
                raise ValueError(f"{at}：必須填 amount（1–{MAX_REFUND_AP}）")
        elif sub.type == REFUND_COOLDOWN:
            if not self.cost.cooldown:
                raise ValueError(f"{at}：技能沒有冷卻（cost.cooldown），沒有東西可以歸零")
        else:
            self._check_effect(path, sub)

    def _check_runes(self) -> None:
        """刻印（Phase 3-23）：``inscribe`` 恰好填 ``element`` 或 ``tag`` 其中一個（標籤符文不可同時
        帶元素）。兩者只能用在主動技能的資料在 ``skill_primitives.yaml``。"""
        for index, effect in enumerate(self.effects):
            if effect.type not in (INSCRIBE, DETONATE_RUNES):
                continue
            where = f"effects[{index}]（{effect.type}）"
            if effect.type == INSCRIBE and (effect.element is None) == (effect.tag is None):
                raise ValueError(f"{where}：必須恰好填 element 或 tag 其中一個")
            if effect.type == INSCRIBE and effect.dice is not None:
                raise ValueError(f"{where}：符文本身沒有效果，不可填 dice")
            if effect.scope is not None:
                raise ValueError(f"{where}：scope 只能用在修正規則的命中後效果")

    def _check_sacrifice(self) -> None:
        """獻祭召喚物（Phase 3-24c）：形狀是 ``single``（選自己的一個召喚物），必須填 ``dice`` 與
        ``radius``；填了 ``element`` 是爆炸（傷害範圍內的敵人），省略是治療範圍內的友方。只能用在
        主動技能與形狀的資料在 ``skill_primitives.yaml``。"""
        for index, effect in enumerate(self.effects):
            if effect.type != SACRIFICE_SUMMON:
                continue
            where = f"effects[{index}]（{SACRIFICE_SUMMON}）"
            shapes = composition_shapes(SACRIFICE_SUMMON)
            if shapes and self.shape.type not in shapes:
                raise SkillRuleError(
                    f"{where}：形狀必須是 {'、'.join(shapes)}（選自己的召喚物）", path="shape.type"
                )
            if effect.dice is None or effect.radius is None:
                raise ValueError(f"{where}：必須填 dice 與 radius")

    def _check_zone(self) -> None:
        """持續區域（Phase 3D-5）：只能用在主動技能，而且是技能唯一的效果；``anchor``、``when``、
        ``duration``、``effects`` 必填，``affects`` 必須是 ``enemies``／``allies``／``all``；
        ``moving`` 要搭配選方向的形狀並填 ``speed``，``caster`` 要搭配以施放者為中心的形狀。"""
        zones = [e for e in self.effects if e.type == ZONE]
        for index, effect in enumerate(self.effects):
            if effect.type != ZONE and any(
                getattr(effect, f) is not None for f in _ZONE_ONLY_FIELDS
            ):
                raise ValueError(f"effects[{index}]：只有 zone 使用 anchor、when、speed、effects")
        if zones:  # 只能用在主動技能、唯一的效果：skill_primitives.yaml（_check_composition）
            self._check_zone_effect(zones[0])

    def _check_zone_effect(self, zone: EffectSpec) -> None:
        where = "effects[0]（zone）"
        if zone.anchor is None or zone.when is None or zone.duration is None:
            raise ValueError(f"{where}：必須填 anchor、when、duration")
        if zone.affects not in ("enemies", "allies", "all"):
            raise ValueError(f"{where}：affects 必須明寫 enemies、allies 或 all")
        if zone.anchor == "moving":
            if self.shape.type not in ZONE_MOVING_SHAPES:
                allowed = "、".join(ZONE_MOVING_SHAPES)
                raise ValueError(f"{where}：anchor: moving 的形狀必須是 {allowed}")
            if zone.speed is None:
                raise ValueError(f"{where}：anchor: moving 必須填 speed")
        elif zone.speed is not None:
            raise ValueError(f"{where}：只有 anchor: moving 使用 speed")
        if zone.anchor == "caster" and self.shape.type not in ZONE_CASTER_SHAPES:
            allowed = "、".join(ZONE_CASTER_SHAPES)
            raise ValueError(f"{where}：anchor: caster 的形狀必須是 {allowed}")
        subs = zone.effects or ()
        if not 1 <= len(subs) <= _MAX_ZONE_EFFECTS:
            raise ValueError(f"{where}：effects 必須有 1 到 {_MAX_ZONE_EFFECTS} 個效果")
        for sub_index, sub in enumerate(subs):
            if sub.type not in ZONE_EFFECT_TYPES:
                allowed = "、".join(ZONE_EFFECT_TYPES)
                raise ValueError(
                    f"{where}.effects[{sub_index}]：只能使用 {allowed}，收到 {sub.type}"
                )
            if sub.affects is not None or sub.condition is not None:
                raise ValueError(
                    f"{where}.effects[{sub_index}]：區域的效果不可自帶 affects 或 condition"
                )
            self._check_effect(f"effects[0].effects[{sub_index}]", sub)

    def _check_gamble(self) -> None:
        """賭博型（Phase 3D-7a）：``gamble`` 只能用在主動技能、每個技能一個而且是最後一個效果
        （資料在 ``skill_primitives.yaml``）；``cost.on_miss`` 只有主動技能可以有。分支與反噬的
        內容見 :meth:`_check_branch`。"""
        gambles = [e for e in self.effects if e.type == GAMBLE]
        for index, effect in enumerate(self.effects):
            if effect.type != GAMBLE and any(
                getattr(effect, f) is not None for f in _GAMBLE_ONLY_FIELDS
            ):
                raise ValueError(f"effects[{index}]：只有 gamble 使用 chance_permille、win、lose")
            if effect.type in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
                raise ValueError(f"effects[{index}]：{effect.type} 只能出現在 gamble 的分支裡")
        self._check_on_miss()
        if not gambles:
            return
        # 只能用在主動技能、最多一個、最後一個效果：skill_primitives.yaml（_check_composition）
        self._check_gamble_effect(gambles[0], f"effects[{len(self.effects) - 1}]")

    def _check_on_miss(self) -> None:
        """``cost.on_miss``（失手反噬）：只有主動技能可以有。"""
        if not self.cost.on_miss:
            return
        if self.kind != "active":
            raise ValueError(f"只有主動技能可以有 cost.on_miss，收到 kind: {self.kind}")
        self._check_branch("cost.on_miss", self.cost.on_miss, BACKLASH_TYPES, backlash=True)

    def _check_gamble_effect(self, gamble: EffectSpec, path: str) -> None:
        """``gamble`` 效果本身：必填 ``chance_permille``、``win`` 與 ``lose`` 至少一邊有效果。"""
        where = f"{path}（gamble）"
        if gamble.chance_permille is None:
            raise ValueError(f"{where}：必須填 chance_permille")
        if not (gamble.win or gamble.lose):
            raise ValueError(f"{where}：win 與 lose 至少要有一邊有效果")
        for name in ("win", "lose"):
            branch = getattr(gamble, name) or ()
            if branch:
                self._check_branch(
                    f"{where}.{name}",
                    branch,
                    GAMBLE_BRANCH_TYPES,
                    backlash=False,
                    path=f"{path}.{name}",
                )

    def _check_branch(
        self,
        where: str,
        branch: tuple[EffectSpec, ...],
        allowed: tuple[str, ...],
        *,
        backlash: bool,
        path: str | None = None,
    ) -> None:
        """賭注分支或失手反噬的效果列表：1–2 個、類型在 ``allowed`` 內、不自帶 ``condition``；
        反噬的對象只能是施放者自己；倍率與自傷各至多一個，而且技能要有傷害效果可以乘。
        ``path`` 是分支的完整路徑（省略＝``where``；4-L10a 讓巢狀錯誤帶完整路徑）。"""
        if not 1 <= len(branch) <= _MAX_BRANCH_EFFECTS:
            raise ValueError(
                f"{where}：必須有 1 到 {_MAX_BRANCH_EFFECTS} 個效果，收到 {len(branch)}"
            )
        has_damage = any(e.type == "damage" for e in self.effects)
        for i, sub in enumerate(branch):
            at = f"{where}[{i}]（{sub.type}）"
            if sub.type not in allowed:
                raise ValueError(f"{at}：只能使用 {'、'.join(allowed)}")
            if sub.condition is not None:
                raise ValueError(f"{at}：不可自帶 condition")
            if backlash and sub.affects not in (None, "self"):
                raise ValueError(f"{at}：失手反噬的對象只能是施放者（省略 affects 或寫 self）")
            if sub.affects == "tiles":
                raise ValueError(f"{at}：不能用 affects: tiles")
            self._check_branch_fields(at, sub, has_damage=has_damage)
            if sub.type not in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
                self._check_effect(f"{path or where}[{i}]", sub)
        for special in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
            if sum(1 for e in branch if e.type == special) > 1:
                raise ValueError(f"{where}：每個分支最多一個 {special}")

    @staticmethod
    def _check_branch_fields(where: str, sub: EffectSpec, *, has_damage: bool) -> None:
        """分支效果的專用欄位：``damage_multiplier`` 與 ``self_damage_of_hit`` 必填自己的數值、
        不可自帶 ``affects``，而且技能要有傷害效果；其他類型不可填這兩個欄位。"""
        if sub.type == DAMAGE_MULTIPLIER:
            if (
                sub.damage_multiplier_permille is None
                or sub.damage_multiplier_permille == _PERMILLE
            ):
                raise ValueError(f"{where}：必須填 damage_multiplier_permille（不等於 1000）")
        elif sub.damage_multiplier_permille is not None:
            raise ValueError(f"{where}：只有 damage_multiplier 使用 damage_multiplier_permille")
        if sub.type == SELF_DAMAGE_OF_HIT:
            if sub.self_damage_permille_of_hit is None:
                raise ValueError(f"{where}：必須填 self_damage_permille_of_hit")
        elif sub.self_damage_permille_of_hit is not None:
            raise ValueError(f"{where}：只有 self_damage_of_hit 使用 self_damage_permille_of_hit")
        if sub.type in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
            if sub.affects is not None:
                raise ValueError(f"{where}：不可自帶 affects")
            if not has_damage:
                raise ValueError(f"{where}：技能必須有傷害效果")

    def _check_pair_moves(self) -> None:
        """位移他人（Phase 3D-2b）：``teleport_target`` 與形狀 ``unit_then_tile``、``swap_any`` 與
        形狀 ``unit_pair`` 必須一起出現；主動技能、是技能唯一的效果（選取的單位與落點就是它的
        參數，不另外結算命中與其他效果）。"""
        needed = {t for t in PAIR_SHAPES.values()}
        if (
            self.shape.type in needed
            and not any(
                e.type in PAIR_MOVES and PAIR_SHAPES[e.type] == self.shape.type
                for e in self.effects
            )
            and not self._chooses_shadowstep_landing()
        ):
            raise ValueError(f"形狀 {self.shape.type} 的技能必須有對應的位移他人效果")
        # 原語這一側（主動、唯一的效果、形狀）的資料在 skill_primitives.yaml；
        # 形狀這一側（形狀要求對應的原語，上面）留在程式。
        for effect in self.effects:
            if effect.type in PAIR_MOVES:
                self._require_shape(effect.type)

    def _chooses_shadowstep_landing(self) -> bool:
        """一般瞬步（``shadowstep`` 的 ``landing: choose``，Phase 3D-8d）也用形狀
        ``unit_then_tile``：第 1 段選敵人、第 2 段選他相鄰的落點。"""
        return any(e.type == SHADOWSTEP and e.landing == "choose" for e in self.effects)

    def _check_pierce(self) -> None:
        """``pierce``（Phase 3C-5b）：主動技能或反應技、遠程武器或法術、形狀是單體（射程大於 1）或
        直線，而且要有對敵方的傷害效果。射程是否算「遠程」另由引擎依武器判斷。"""
        if not self.pierce:
            return
        if self.kind not in ("active", "reaction"):
            raise ValueError(f"pierce 只能用在主動技能與反應技，收到 kind: {self.kind}")
        if self.shape.type not in PIERCE_SHAPES:
            raise ValueError(
                f"pierce 的形狀必須是 {'、'.join(PIERCE_SHAPES)}，收到 {self.shape.type}"
            )
        if self.weapon_req == "melee":
            raise ValueError("pierce 不能用在近戰武器技")
        if self.shape.type == "single" and self.shape.range == 1:
            raise ValueError("pierce 的單體形狀射程必須大於 1")
        if not any(e.type == "damage" for e in self.effects):
            raise ValueError("pierce 的技能必須有傷害效果")

    def _check_stance_upkeep(self) -> None:
        if self.stance_upkeep and (
            self.kind != "stance" or any(e.type == ENTER_FORM for e in self.effects)
        ):
            raise ValueError("stance_upkeep 只有一般姿態（不含形態）可以填")
        magnitudes = [e for e in self.effects if e.magnitude_permille is not None]
        not_stance = self.kind != "stance" or any(e.type != "apply_status" for e in magnitudes)
        if magnitudes and not_stance:
            raise ValueError("magnitude_permille 只有姿態技能的 apply_status 可以填")
        if any((e.magnitude_permille or 0) < _PERMILLE for e in magnitudes):
            raise ValueError("magnitude_permille 不能小於 1000（姿態幅度的強化）")

    def _check_reaction_and_stance(self) -> None:
        """反應技與姿態的結構（2E-2）：``reaction`` 欄位、形狀、``intercept`` 與 ``teleport``。"""
        if self.kind == "reaction" and self.reaction is None:
            raise ValueError("反應技（kind: reaction）必須有 reaction")
        if self.kind != "reaction" and self.reaction is not None:
            raise ValueError(f"只有反應技可以有 reaction，收到 kind: {self.kind}")
        types = [e.type for e in self.effects]
        if self.kind in ("reaction", "stance") and "teleport" in types:
            raise ValueError("反應技與姿態不能有 teleport（沒有可選的目標格）")
        if self.kind == "stance" and self.shape.type != "self":
            raise ValueError(f"姿態的形狀只能是 self，收到 {self.shape.type}")
        if ENTER_FORM in types and (self.kind != "stance" or len(types) != 1):
            raise ValueError("enter_form（進入形態）只能是姿態（kind: stance）唯一的效果")
        if self.kind == "reaction":
            assert self.reaction is not None
            if self.shape.type not in ("self", "single"):
                raise ValueError(f"反應技的形狀只能是 self 或 single，收到 {self.shape.type}")
            intercepts = INTERCEPT in types
            guarding = self.reaction.event == "ally_hit_adjacent"
            if guarding and not intercepts:
                raise ValueError("ally_hit_adjacent 的反應技必須有 intercept 效果")
            if intercepts and not guarding:
                raise ValueError("intercept 只能用在 event: ally_hit_adjacent 的反應技")
            if guarding and self.shape.type != "self":
                raise ValueError("ally_hit_adjacent 的反應技形狀必須是 self")
            if self.reaction.event == "ally_downed" and self.shape.type != "self":
                raise ValueError("ally_downed 的反應技形狀必須是 self（另一方已經倒下）")
        elif INTERCEPT in types:
            raise ValueError("intercept 只能用在反應技")

    def _check_modifier(self) -> None:
        """修正技能（3C-2）：裝在被動欄位、不花 AP、沒有觸發；效果都寫在 ``modifiers`` 裡。"""
        limit = _MAX_MODIFIERS if self.exclusive_group is None else _MAX_MASTERY_MODIFIERS
        if not 1 <= len(self.modifiers) <= limit:
            count = len(self.modifiers)
            raise ValueError(f"修正技能的 modifiers 必須有 1 到 {limit} 條，收到 {count} 條")
        if self.effects:
            raise ValueError("修正技能（kind: modifier）的 effects 必須為空（效果寫在 modifiers）")
        if self.shape.type != "self":
            raise ValueError(f"修正技能的形狀只能是 self，收到 {self.shape.type}")
        if self.condition is not None:
            raise ValueError("修正技能不能有技能層級的 condition（條件寫在每條修正規則）")
        allowed = (
            SkillCost(source=self.cost.source, cooldown=self.cost.cooldown)
            if self.rarity == "legendary"
            else SkillCost()
        )
        if self.cost != allowed:
            raise ValueError(
                "修正型傳說的代價只能有源力與冷卻（cost.source、cost.cooldown）"
                if self.rarity == "legendary"
                else "修正技能不能有代價（cost 必須為空）"
            )
        if self.mastery is not None:
            raise ValueError("修正技能不能有 mastery")
        rune_types = {
            e.type
            for rule in self.modifiers
            for e in rule.change.on_hit_effects or ()
            if e.type in (INSCRIBE, DETONATE_RUNES)
        }
        if len(rune_types) > 1:
            raise ValueError(f"modifiers：{RUNE_BOTH_MESSAGE}")
        for rule_index, rule in enumerate(self.modifiers):
            for index, effect in enumerate(rule.change.on_hit_effects or ()):
                at = f"modifiers[{rule_index}].change.on_hit_effects[{index}]"
                self._check_effect(at, effect)

    def _check_gear_limits(self) -> None:
        """武器親和與限定武器的結構（3I-5，6.10 #50）：``wielding_weapon`` 只能寫在效果上（沒拿
        那種武器時技能照常可用，只是少一個加成；寫在技能條件上就變成不能施放）；限定武器不重複。"""
        gated = [self.condition]
        if self.followup is not None:
            gated.append(self.followup.condition)
        if any(c is not None and c.type == WIELDING_WEAPON for c in gated):
            raise ValueError(f"condition：{WIELDING_EFFECT_ONLY}")
        if len(set(self.weapon_only)) != len(self.weapon_only):
            raise ValueError("weapon_only 不可重複")

    def _check_scaling_and_mastery(self) -> None:
        """雙屬性縮放與專精加成的結構（2H-2；稀有度門檻是跨檔案檢查）。"""
        if self.secondary_scaling_attr == self.scaling_attr:
            raise ValueError("secondary_scaling_attr 不可和 scaling_attr 相同")
        if self.mastery is None:
            return
        if self.secondary_scaling_attr is not None:
            raise ValueError("雙屬性技能不享專精加成（mastery 與 secondary_scaling_attr 不可並用）")
        if self.mastery == "range" and self.shape.range is None:
            raise ValueError("mastery: range 只能用在有施放距離（shape.range）的技能")
        if self.mastery == "duration" and not any(e.type == "apply_status" for e in self.effects):
            raise ValueError("mastery: duration 只能用在有 apply_status 效果的技能")

    def _check_trap_and_stacks(self) -> None:
        """陷阱與層數的結構（2E-3）：``trap`` 與 ``place_trap`` 成對；陷阱技能是形狀
        ``ground_tile`` 的主動技能，其餘效果在觸發時結算，所以不能有 ``teleport``，也不能累積
        或消耗層數（觸發時的施放者是放置時的快照）。"""
        types = [e.type for e in self.effects]
        if (PLACE_TRAP in types) != (self.trap is not None):
            raise ValueError("place_trap 原語與 trap 欄位必須成對出現")
        if self.cost.stacks is not None and CONSUME_STACK not in types:
            raise ValueError("cost.stacks 需要一個 consume_stack 效果")
        if self.trap is None:
            return
        if types.count(PLACE_TRAP) != 1:
            raise ValueError("陷阱技能只能有一個 place_trap")
        if self.kind != "active" or self.shape.type != "ground_tile":
            raise ValueError("陷阱技能必須是形狀 ground_tile 的主動技能")
        banned = [t for t in types if t in (*SELF_MOVES, *PAIR_MOVES, ADD_STACK, CONSUME_STACK)]
        if banned:
            raise ValueError(f"陷阱技能不能有 {'、'.join(banned)}（陷阱觸發時才結算其餘效果）")

    def _check_consume_status(self, at: str, effect: EffectSpec) -> None:
        """``consume_status`` 的結構（3C-3b）：``then`` 1–2 個、只能用 :data:`CONSUME_THEN_TYPES`、
        不自帶對象；``scale``、``splash``、``then`` 只屬於 ``consume_status``。"""
        where = f"{at}（{effect.type}）"
        if effect.type != CONSUME_STATUS:
            if effect.then is not None or effect.scale is not None or effect.splash is not None:
                raise ValueError(f"{where}：只有 consume_status 使用 then、scale、splash")
            return
        then = effect.then or ()
        if not 1 <= len(then) <= _MAX_CONSUME_THEN:
            raise ValueError(
                f"{where}：then 必須有 1 到 {_MAX_CONSUME_THEN} 個效果，收到 {len(then)}"
            )
        if effect.scale == "stacks" and effect.stack is None:
            raise ValueError(f"{where}：scale: stacks 必須填 stack（目標型層數）")
        if effect.scale != "stacks" and effect.stack is not None:
            raise ValueError(f"{where}：只有 scale: stacks 使用 stack")
        for sub_index, sub in enumerate(then):
            if sub.type not in CONSUME_THEN_TYPES:
                allowed = "、".join(CONSUME_THEN_TYPES)
                raise ValueError(f"{where}.then[{sub_index}]：只能使用 {allowed}，收到 {sub.type}")
            if sub.affects is not None or sub.condition is not None:
                raise ValueError(
                    f"{where}.then[{sub_index}]：then 的效果不可自帶 affects 或 condition"
                )
            self._check_effect(f"{at}.then[{sub_index}]", sub)

    def _check_restore_resource(self, where: str, effect: EffectSpec) -> None:
        """``restore_resource`` 的結構（3D-1）：必須填 ``resource``；冷卻最多 −2。"""
        if effect.resource is None:
            raise ValueError(f"{where}：restore_resource 必須填 resource（mana 或 cooldown）")
        if effect.resource == "cooldown" and (effect.amount or 1) > _MAX_COOLDOWN_RESTORE:
            raise ValueError(f"{where}：冷卻最多縮短 {_MAX_COOLDOWN_RESTORE} 回合")

    def _check_variable_damage(self, where: str, effect: EffectSpec, *, top: bool) -> None:
        """``explode``、``scaling``（Phase 3D-7b）與 ``lifesteal_permille``、``split_heal``
        （Phase 3D-8a）：只有技能自己的 ``damage`` 效果可以用（不能在賭注分支、失手反噬、``then``
        裡）；``scaling.cap_permille`` 的上限是跨檔案檢查。"""
        if (
            effect.explode is None
            and effect.scaling is None
            and effect.lifesteal_permille is None
            and effect.split_heal is None
            and effect.spread is None
        ):
            return
        if effect.type != "damage":
            raise ValueError(
                f"{where}：只有 damage 使用 explode、scaling、lifesteal、split_heal、spread"
            )
        if not top:
            raise ValueError(
                f"{where}：explode、scaling、lifesteal、split_heal、spread "
                "只能用在技能自己的傷害效果"
            )
        if effect.spread is not None and effect.element is not Element.WIND:
            raise ValueError(f"{where}：spread（擴散格數）只有風元素（element: wind）的傷害能填")
        if effect.split_heal is not None:
            self._check_split_heal(where, effect)

    @staticmethod
    def _check_form_bonus(where: str, effect: EffectSpec, *, top: bool) -> None:
        """``form_bonus_permille``（在形態中的倍率）：只有技能自己的傷害、治療可以用。"""
        if effect.form_bonus_permille is None:
            return
        if effect.type not in ("damage", "heal"):
            raise ValueError(f"{where}：只有 damage、heal 使用 form_bonus_permille")
        if not top:
            raise ValueError(f"{where}：form_bonus_permille 只能用在技能自己的傷害或治療效果")

    def _check_split_heal(self, where: str, effect: EffectSpec) -> None:
        """``split_heal``（聖光雙效）：只能填 true、``affects: all``、法術技、``aura``／``area``
        骨架、主動技能，不可與吸血、爆骰、縮放並用（治療與傷害要用同一個骰值）。"""
        if effect.affects != "all":
            raise ValueError(f"{where}：split_heal 必須搭配 affects: all")
        if self.category != "spell" or self.kind != "active":
            raise ValueError(f"{where}：split_heal 只能用在主動的法術技")
        if self.skeleton not in SPLIT_SKELETONS:
            allowed = "、".join(SPLIT_SKELETONS)
            raise ValueError(f"{where}：split_heal 只能用在 {allowed} 骨架，收到 {self.skeleton}")
        if effect.lifesteal_permille is not None or effect.explode or effect.scaling is not None:
            raise ValueError(f"{where}：split_heal 不能與 lifesteal、explode、scaling 並用")

    @staticmethod
    def _check_true_only(at: str, where: str, effect: EffectSpec) -> None:
        """只能填 ``true`` 的開關（資料見 :func:`true_only_params`）：填 ``false`` 一律擋下。"""
        for name in sorted(true_only_params().get(effect.type, ())):
            if getattr(effect, name, None) is False:
                raise SkillRuleError(
                    f"{where}：{name} 只能填 true（不啟用就省略）",
                    path=f"{at}.{name}",
                    code="flag.true_only",
                )

    def _check_variance(self) -> None:
        """``crit_range``、``damage_permille`` 需要有傷害效果、只能用在主動技能。"""
        if self.crit_range is None and self.damage_permille is None:
            return
        if self.kind != "active":
            raise ValueError(f"只有主動技能可以有 crit_range、damage_permille，收到 {self.kind}")
        if not any(e.type == "damage" for e in self.effects):
            raise ValueError("crit_range、damage_permille 需要技能有傷害效果")

    def _check_effect(self, at: str, effect: EffectSpec, *, top: bool = False) -> None:
        """一個效果的結構；``at`` 是它的完整路徑（``effects[0]``、``cost.on_miss[1]``、
        ``effects[0].then[0]``…；4-L10a：巢狀效果的錯誤指向自己，不再一律報 ``effects[0]``）。"""
        where = f"{at}（{effect.type}）"
        self._check_true_only(at, where, effect)
        self._check_variable_damage(where, effect, top=top)
        self._check_on_kill(at, effect, top=top)
        self._check_consume_status(at, effect)
        if effect.type == RESET_COOLDOWN:
            if effect.which is None:
                raise ValueError(f"{where}：reset_cooldown 必須填 which（all 或 tag）")
            if (effect.which == "tag") != (effect.tag is not None):
                raise ValueError(f"{where}：which: tag 必須填 tag，which: all 不可填 tag")
        elif effect.which is not None or (effect.tag is not None and effect.type != INSCRIBE):
            raise ValueError(f"{where}：只有 reset_cooldown 使用 which、tag")
        if effect.type == RESTORE_RESOURCE:
            self._check_restore_resource(where, effect)
        elif effect.resource is not None:
            raise ValueError(f"{where}：只有 restore_resource 使用 resource")
        if effect.type in ("push", "pull") and (
            effect.distance is None or not 1 <= effect.distance <= _MAX_DISPLACE
        ):
            raise ValueError(
                f"{where}：推擊與拉扯的距離必須是 1 到 {_MAX_DISPLACE} 格，收到 {effect.distance}"
            )
        self._check_form_bonus(where, effect, top=top)
        if effect.type != "damage":
            return
        if self.category == "spell":
            if effect.dice is None or effect.element is None:
                raise ValueError(f"{where}：法術技的傷害必須指定 dice 與 element")
            if effect.multiplier_permille not in (None, _PERMILLE):
                raise ValueError(f"{where}：法術技的傷害不使用 multiplier_permille")
        elif effect.dice is not None:
            raise ValueError(
                f"{where}：武器技的傷害骰來自武器，不可指定 dice（用 multiplier_permille）"
            )

    def summary(self) -> str:
        return f"{self.name_zh}（階級 {self.tier}，{self.skeleton}，AP {self.ap_cost}）"

    @property
    def is_gamble(self) -> bool:
        """帶賭博機制（Phase 3D-7a、7b）：有 ``gamble`` 效果、失手反噬 ``cost.on_miss``、高變異
        （``explode``、``crit_range``）或以血換力（``scaling`` 依 ``missing_hp_10pct``）。
        超載是層數的規則（見 ``StackDef``），由帶標籤的技能在預算上反映。"""
        return (
            bool(self.cost.on_miss)
            or self.crit_range is not None
            or any(
                e.type == GAMBLE
                or e.explode
                or (e.scaling is not None and e.scaling.by == "missing_hp_10pct")
                for e in self.effects
            )
        )

    @property
    def is_active(self) -> bool:
        return self.kind == "active"

    @property
    def is_modifier(self) -> bool:
        """修正技能（改造型與修正型被動，3C-2）：不能施放，持續改變持有者自己的動作。"""
        return self.kind == "modifier"

    @property
    def is_activatable(self) -> bool:
        """常駐類傳說（Phase 3D-6）：以 ``UseSkill`` 啟動，啟動前不生效。"""
        return self.activation is not None

    @property
    def rule_change_id(self) -> str | None:
        """規則改變型傳說引用的規則改變 ID（Phase 3D-6）；其他技能為 ``None``。"""
        return next((e.rule for e in self.effects if e.type == RULE_CHANGE), None)

    def scaling_value(
        self, get: Callable[[Attribute], int], weapon: WeaponDef | None = None
    ) -> int:
        """技能縮放屬性的值（Phase 2H-2）：雙屬性為兩個屬性的平均（無條件捨去），否則為主屬性。
        ``get`` 讀屬性值（引擎傳有效屬性，卡片傳面板屬性）；引擎的 ``skill_scaling_value`` 與卡片的
        「目前加成」都經過這裡。

        **武器技看手上武器的屬性**（Phase 3H-6，玩法決定 #45）：``category: weapon`` 且給了
        ``weapon`` 時改用 :meth:`WeaponDef.scaling_value`（雙屬性照取較高／取平均），技能自己的
        ``scaling_attr`` 只當顯示提示。沒有武器時（工坊、三選一的泛稱）退回技能自己的。"""
        if self.category == "weapon" and weapon is not None:
            # 魔劍士方案 A（3I-3，#46）：武器技可帶一個心智第二屬性，和武器的縮放值取平均
            base = weapon.scaling_value(get)
            if self.secondary_scaling_attr is None:
                return base
            return (base + get(self.secondary_scaling_attr)) // 2
        primary = get(self.scaling_attr)
        if self.secondary_scaling_attr is None:
            return primary
        return (primary + get(self.secondary_scaling_attr)) // 2

    def mastery_value(
        self, get: Callable[[Attribute], int], weapon: WeaponDef | None = None
    ) -> int:
        """專精比較用的屬性值（和自己最高的屬性比）：一般技能為 ``scaling_attr`` 本身；武器技為
        手上武器的縮放值（3H-6，雙屬性取較高／取平均）。"""
        if self.category == "weapon" and weapon is not None:
            return weapon.scaling_value(get)
        return get(self.scaling_attr)

    def contest_attr(self, weapon: WeaponDef | None = None) -> Attribute:
        """對抗判定（擊倒、位移、狀態抵抗）守方被比的單一屬性；武器技為手上武器的主屬性。攻方的值是
        :meth:`scaling_value`（雙屬性為平均，3I-3b）。"""
        if self.category == "weapon" and weapon is not None:
            return weapon.scaling_attr
        return self.scaling_attr

    def _formula_names_zh(self, weapon: WeaponDef | None) -> str:
        """算法句裡的屬性名（3-55）。武器技看手上武器（3H-6）：有武器寫實際的屬性名（雙屬性寫取較高
        ／取平均；3I-3 的心智第二屬性再取平均），沒有武器寫「武器屬性」（卡片另列由武器資料產生的
        例子）；其他技能寫自己的縮放屬性。"""
        second = self.secondary_scaling_attr
        if self.category != "weapon":
            names = self.scaling_attr.display_name
            return names if second is None else f"{names}／{second.display_name}（取平均）"
        if weapon is not None:
            return weapon.skill_scaling_names_zh(second)
        return "武器屬性" if second is None else f"武器屬性與{second.display_name}（取平均）"

    def formula_lines_zh(
        self,
        core: CoreRules,
        weapon: WeaponDef | None = None,
        get: Callable[[Attribute], int] | None = None,
        weapon_examples: str = "",
    ) -> tuple[str, ...]:
        """傷害、治療、護盾的算法（3-41c，08 8.11）：「傷害算法：骰值＋智力 × 0.5（目前 +6.5）」。

        法術技的傷害骰值來自效果自己、治療與護盾一律用法術倍率；武器技的傷害用武器的骰與固定傷害，
        屬性乘普攻倍率（效果的倍率、等級與修正規則另算，見效果句）。倍率取自 ``rules/core.yaml``，
        ``weapon`` 與 ``get`` 都省略時不附武器骰與目前加成。"""
        types = {e.type for e in self.effects}
        names = self._formula_names_zh(weapon)
        now = None if get is None else self.scaling_value(get, weapon)

        def line(label: str, base: str, permille: int) -> str:
            text = f"{label}算法：{base}＋{names} × {permille / 1000:g}"
            return text if now is None else f"{text}（{bonus_text(now, permille)}）"

        out: list[str] = []
        if "damage" in types:
            if self.category == "spell":
                out.append(line("傷害", "骰值", core.spell_attr_multiplier_permille))
            else:
                base = "武器骰"
                if weapon is not None:
                    base += f" {weapon.dice}" + (f"＋{weapon.flat}" if weapon.flat else "")
                out.append(line("傷害", base, core.basic_attack_attr_multiplier_permille))
                if weapon is None and weapon_examples:  # 3-55：沒有主角時列例子
                    out.append(f"武器屬性看手上的武器：{weapon_examples}")
        for kind, label in (("heal", "治療"), ("shield", "護盾")):
            if kind in types:
                out.append(line(label, "骰值", core.spell_attr_multiplier_permille))
        return tuple(out)

    @property
    def is_actionable(self) -> bool:
        """玩家可以在自己的回合用 ``UseSkill`` 施放：主動技能與姿態（花 AP），以及修正型傳說的
        啟動（Phase 3D-6，裝在被動欄位、從技能列啟動）。"""
        return self.kind in ("active", "stance") or (self.is_modifier and self.is_activatable)

    @property
    def form_id(self) -> str | None:
        """進入形態的技能（Phase 3J-1a，``enter_form``）的形態 ID；其他技能為 ``None``。"""
        for effect in self.effects:
            if effect.type == ENTER_FORM:
                return effect.form
        return None

    @property
    def slot_kind(self) -> str:
        """佔用的技能欄位：修正型裝在被動欄位（3C-2）；形態技能雖然是姿態，佔主動欄位（6.30）。"""
        if self.is_modifier:
            return "passive"
        if self.form_id is not None:
            return "active"
        return self.kind


class SkillTable(ContentModel):
    """全部技能（``content/skills/`` 載入後嵌入 ``Ruleset``），依 ID 排序。"""

    skills: tuple[SkillDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> SkillTable:
        _unique((s.id for s in self.skills), "技能")
        return self

    def by_id(self) -> dict[str, SkillDef]:
        return {s.id: s for s in self.skills}

    def summary(self) -> str:
        return f"{len(self.skills)} 個技能"


# ---------------------------------------------------------------------------
# 跨檔案驗證
# ---------------------------------------------------------------------------


def _int_param_problems(where: str, values: dict[str, int | str], shape: ShapeDef) -> list[str]:
    problems: list[str] = []
    for name, spec in shape.params.items():
        value = values.get(name)
        if value is None:
            if spec.required:
                problems.append(f"{where}：{shape.name_zh}（{shape.id}）缺少參數 {name}")
            continue
        if value == "weapon":
            if not spec.allow_weapon:
                problems.append(f'{where}.{name}：{shape.id} 的 {name} 不接受 "weapon"')
            continue
        assert isinstance(value, int)
        if not spec.min <= value <= spec.max:
            problems.append(
                f"{where}.{name}：{shape.id} 的 {name} 必須在 {spec.min}–{spec.max}，收到 {value}"
            )
    for name in values:
        if name not in shape.params:
            problems.append(f"{where}.{name}：{shape.id} 不接受參數 {name}")
    return problems
