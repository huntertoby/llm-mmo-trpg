"""技能預算與驗證用的規則資料（``docs/phases/Phase2B計畫.md`` 第 4 節）。

對應資料檔：

- ``content/skill_budget.yaml``：:class:`BudgetRules`（AP 係數、條件倍率、代價折抵、合格區間、
  稀有度上限）。階級預算 ``tier_budget`` 與武器基準傷害在 ``rules/core.yaml``。
- ``content/skill_synergies.yaml``：:class:`SynergyTable`（機制標籤 → 協同係數）。
- ``content/skill_exclusions.yaml``：:class:`ExclusionTable`（互斥規則，以資料表達）。
- ``content/skeletons/<id>.yaml``：:class:`SkeletonDef`（12 種骨架的結構）。

這裡只定義 **資料 schema**；預算計算與驗證邏輯在 ``trpg.skillgen``（``trpg.content`` 不得匯入它）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills import (
    AFFECTS_VALUES,
    RARITY_ORDER,
    SKELETON_IDS,
    Affects,
    SkillKind,
    SkillRarity,
)

__all__ = [
    "BudgetRules",
    "CostAllowance",
    "EffectPattern",
    "ExclusionRule",
    "ExclusionTable",
    "RarityLimit",
    "SecondaryRules",
    "ShapePattern",
    "SkeletonCore",
    "SkeletonDef",
    "SkillMatch",
    "SynergyRule",
    "SynergyTable",
]

_PERMILLE_MAX = 10_000


# ---------------------------------------------------------------------------
# skill_budget.yaml
# ---------------------------------------------------------------------------


class CostAllowance(ContentModel):
    """代價折抵（‰，各項加總後乘上去：可用預算 ×（1000 ＋ 折抵）÷ 1000）。"""

    cooldown_per_turn: int = Field(ge=0)
    cooldown_cap: int = Field(ge=0)
    uses_per_battle: dict[int, int]
    """每場次數 → 折抵；次數超過表中最大值時用 ``uses_default``。"""
    uses_default: int = Field(ge=0)
    mana_per_point: int = Field(ge=0)
    mana_cap: int = Field(ge=0)
    hp_per_permille: int = Field(ge=0)
    """``hp_percent`` 每 1‰ 的折抵。"""
    hp_cap: int = Field(ge=0)
    total_cap: int = Field(ge=0)
    """各項先套用自己的上限，加總後再以此截斷（‰）。"""


class RarityLimit(ContentModel):
    """各稀有度的結構上限。"""

    max_effects: int = Field(ge=1, le=4)


class BudgetRules(ContentModel):
    """``content/skill_budget.yaml``。"""

    min_ratio_permille: int = Field(ge=1, le=_PERMILLE_MAX)
    max_ratio_permille: int = Field(ge=1, le=_PERMILLE_MAX)
    ap_coefficient_permille: dict[int, int]
    reaction_coefficient_permille: int = Field(ge=1)
    passive_extra_trigger_permille: int = Field(default=800, ge=1, le=1000)
    """被動技能的 ``trigger.max_per_round`` 每多 1 次，可用預算 × 這個值（‰）。"""
    condition_permille: dict[Literal["none", "common", "harsh"], int]
    all_target_permille: int = Field(ge=1, le=1000)
    """``affects: all``（敵我不分）的對象係數。"""
    allowance: CostAllowance
    rarity: dict[Literal["common", "rare", "epic", "legendary"], RarityLimit]
    max_rule_rewrite: int = Field(ge=0)
    """每個技能的改寫規則型原語上限。"""
    rule_rewrite_min_cooldown: int = Field(ge=1)
    """有改寫規則型原語的技能：``uses_per_battle: 1`` 或冷卻至少這麼多回合。"""

    @model_validator(mode="after")
    def _check(self) -> BudgetRules:
        if self.min_ratio_permille >= self.max_ratio_permille:
            raise ValueError("min_ratio_permille 必須小於 max_ratio_permille")
        if sorted(self.ap_coefficient_permille) != [1, 2, 3]:
            raise ValueError("ap_coefficient_permille 必須剛好有 AP 1、2、3")
        if sorted(self.condition_permille) != ["common", "harsh", "none"]:
            raise ValueError("condition_permille 必須剛好有 none、common、harsh")
        if set(self.rarity) != set(RARITY_ORDER):
            raise ValueError(f"rarity 必須剛好有 {', '.join(RARITY_ORDER)}")
        return self

    def summary(self) -> str:
        return f"合格區間 {self.min_ratio_permille / 10:g}%–{self.max_ratio_permille / 10:g}%"


# ---------------------------------------------------------------------------
# skill_synergies.yaml
# ---------------------------------------------------------------------------

MECHANIC_TAGS: tuple[str, ...] = (
    "damage",
    "heal",
    "area",
    "displace",
    "control",
    "debuff",
    "dot",
    "surface",
    "terrain",
)
"""驗證器從技能內容推導的機制標籤（推導規則見 ``trpg.skillgen.mechanics``）。"""


class SynergyRule(ContentModel):
    """技能同時帶有 ``tags`` 的全部機制標籤時，total 乘上 ``coefficient_permille``。"""

    tags: tuple[str, ...] = Field(min_length=2)
    coefficient_permille: int = Field(ge=1, le=_PERMILLE_MAX)

    @model_validator(mode="after")
    def _check(self) -> SynergyRule:
        unknown = [t for t in self.tags if t not in MECHANIC_TAGS]
        if unknown:
            raise ValueError(
                f"未知的機制標籤：{', '.join(unknown)}（可用：{', '.join(MECHANIC_TAGS)}）"
            )
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("協同規則的標籤不可重複")
        return self


class SynergyTable(ContentModel):
    """``content/skill_synergies.yaml``。符合多條規則時全部相乘。"""

    synergies: tuple[SynergyRule, ...] = ()

    def summary(self) -> str:
        return f"{len(self.synergies)} 條協同規則"


# ---------------------------------------------------------------------------
# skill_exclusions.yaml
# ---------------------------------------------------------------------------


class ShapePattern(ContentModel):
    """形狀的比對：``type`` 相同，且有填的參數都相同。"""

    type: str = Field(pattern=ID_PATTERN)
    size: int | None = None
    range: int | None = None
    radius: int | None = None
    jumps: int | None = None
    jump_range: int | None = None


class EffectPattern(ContentModel):
    """效果的比對：``type`` 相同，且（有填 ``affects`` 時）實際對象與 ``affects`` 有交集。
    ``affects: all`` 的效果同時算敵方與友方。"""

    type: str | None = Field(default=None, pattern=ID_PATTERN)
    affects: tuple[Affects, ...] | None = None

    @model_validator(mode="after")
    def _check(self) -> EffectPattern:
        if self.type is None and self.affects is None:
            raise ValueError("效果比對至少要指定 type 或 affects")
        bad = [a for a in self.affects or () if a not in AFFECTS_VALUES]
        if bad:
            raise ValueError(f"未知的 affects：{', '.join(bad)}")
        return self


class SkillMatch(ContentModel):
    """技能的比對條件；有填的欄位全部成立才算符合（空的比對永遠符合）。

    - ``shapes``：形狀符合其中任一個。
    - ``has_cooldown``：``True`` 要有冷卻、``False`` 要沒有冷卻。``min_cooldown``：冷卻至少幾回合。
    - ``statuses``：施加了其中任一個狀態。
    - ``primitives_any``：有其中任一個原語；``primitives_all``：每個原語都有。
    - ``effects_any``：有效果符合其中任一個；``effects_all``：每個比對都有效果符合。
    - ``repeated_control_group``：``True`` 表示施加了兩個以上相同 ``control_group`` 的狀態。
    - ``kinds``：技能的 ``kind`` 是其中之一（2E-1：被動的 ``self`` 形狀是「作用在觸發對象」，
      不受 ``self`` 形狀不打敵人的限制）。
    """

    kinds: tuple[SkillKind, ...] | None = None
    shapes: tuple[ShapePattern, ...] | None = None
    has_cooldown: bool | None = None
    min_cooldown: int | None = Field(default=None, ge=1)
    statuses: tuple[str, ...] | None = None
    primitives_any: tuple[str, ...] | None = None
    primitives_all: tuple[str, ...] | None = None
    effects_any: tuple[EffectPattern, ...] | None = None
    effects_all: tuple[EffectPattern, ...] | None = None
    repeated_control_group: bool | None = None


class ExclusionRule(ContentModel):
    """一條互斥規則：技能符合 ``when``（省略＝永遠）時，

    - ``forbid``：不得符合這個比對；或
    - ``require``：必須符合這個比對。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    message_zh: str = Field(min_length=1)
    when: SkillMatch | None = None
    forbid: SkillMatch | None = None
    require: SkillMatch | None = None

    @model_validator(mode="after")
    def _check(self) -> ExclusionRule:
        if (self.forbid is None) == (self.require is None):
            raise ValueError(f"互斥規則 {self.id}：forbid 與 require 必須剛好填一個")
        return self


class ExclusionTable(ContentModel):
    """``content/skill_exclusions.yaml``。"""

    rules: tuple[ExclusionRule, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ExclusionTable:
        ids = [r.id for r in self.rules]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"重複的互斥規則 ID：{', '.join(dup)}")
        return self

    def summary(self) -> str:
        return f"{len(self.rules)} 條互斥規則"


# ---------------------------------------------------------------------------
# skeletons/<id>.yaml
# ---------------------------------------------------------------------------


class SkeletonCore(ContentModel):
    """骨架的核心效果：``primitives`` 之一，且（有填時）對象在 ``affects`` 內。

    ``min_share_permille``：核心效果的點數占全部效果點數的最低比例（‰）。
    ``beneficial_only``（2B-3）：核心的狀態與表面必須是 ``beneficial: true``（光環）。
    """

    primitives: tuple[str, ...]
    affects: tuple[Affects, ...] | None = None
    min_share_permille: int = Field(default=0, ge=0, le=1000)
    beneficial_only: bool = False


class SecondaryRules(ContentModel):
    """骨架的附帶效果（不是核心的效果）。

    - ``primitives``：允許的原語；``None`` 表示不限。``harmful_only``：只能是有害原語。
    - ``max_count``：數量上限。
    - ``max_share_permille``：個別原語占全部效果點數的上限（‰），例如 ``{damage: 400}``。
    """

    primitives: tuple[str, ...] | None = None
    harmful_only: bool = False
    max_count: int = Field(default=0, ge=0, le=4)
    max_share_permille: dict[str, int] = Field(default_factory=dict)


class SkeletonDef(ContentModel):
    """一種技能骨架（``content/skeletons/<id>.yaml``）。

    - ``enabled``：``False`` 的骨架不能使用（驗證器拒絕）；停用的骨架可以引用尚未實作的原語。
    - ``kinds``：骨架適用的技能 ``kind``。
    - ``forbid_affects``：技能不得有對這些對象的效果（光環不得傷害敵方）。
    - ``requires_condition``：技能或效果必須有條件。
    - ``min_rarity``：使用此骨架的最低稀有度（省略為 common）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    kinds: tuple[SkillKind, ...] = Field(min_length=1)
    enabled: bool
    shapes: tuple[str, ...] = Field(min_length=1)
    core: SkeletonCore
    secondary: SecondaryRules = Field(default_factory=SecondaryRules)
    forbid_affects: tuple[Affects, ...] = ()
    requires_condition: bool = False
    min_rarity: SkillRarity = "common"
    """使用此骨架的最低稀有度（2E：被動 epic；之後的反應技、姿態、蓄力／終結、陷阱 rare）。"""

    @model_validator(mode="after")
    def _check(self) -> SkeletonDef:
        if self.id not in SKELETON_IDS:
            raise ValueError(f"未知的骨架 {self.id!r}（可用：{', '.join(SKELETON_IDS)}）")
        if self.enabled and not self.core.primitives:
            raise ValueError(f"骨架 {self.id}：啟用的骨架必須有核心原語")
        return self

    def summary(self) -> str:
        state = "啟用" if self.enabled else "停用"
        return f"{self.name_zh}（{state}）"
