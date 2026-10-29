"""隨機技能組合器的調參資料（``content/skill_composer.yaml``；Phase 2C-1 3.1）。

這些數值是「抽選機率與範圍」，不是演算法：稀有度與 AP 的權重、法術比例、骰子與倍率的階梯、
條件與代價的機率與範圍、強度調整的目標區間……改動它們會改變隨機技能的分佈（種子對應的技能也會
不同），但不需要改程式。組合的流程與亂數呼叫順序仍在 ``trpg.skillgen``。

只定義 schema；``trpg.content`` 不得匯入 ``trpg.skillgen``。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel
from trpg.content.skills import RARITY_ORDER, EffectSpec, ShapeSpec, VariantWhen
from trpg.shared.types import Element

__all__ = [
    "AttrWeights",
    "ComposerRules",
    "ConditionRules",
    "CostRules",
    "CostStep",
    "DiceRules",
    "DurationRules",
    "IntRange",
    "LadderRange",
    "LlmCostRules",
    "LlmTopicRules",
    "PassiveRules",
    "ReactionRules",
    "ScalingRules",
    "SpecialRules",
    "StanceRules",
    "StructureRules",
    "TuningRules",
]

_PERMILLE_MAX = 1000
_MIN_SIDES = 2
_PERMILLE = Field(ge=0, le=_PERMILLE_MAX)


class IntRange(ContentModel):
    """閉區間 ``[min, max]``（含兩端）。"""

    min: int
    max: int

    @model_validator(mode="after")
    def _check(self) -> IntRange:
        if self.min > self.max:
            raise ValueError("min 不可大於 max")
        return self


class LadderRange(ContentModel):
    """``range(start, stop, step)`` 的一段；倍率階梯由數段接起來。"""

    start: int = Field(ge=1)
    stop: int = Field(ge=1)
    step: int = Field(ge=1)


class DiceRules(ContentModel):
    """骰子旋鈕的階梯：顆數 1–``max_count``、面數 ``sides``，依平均值由弱到強排序。"""

    sides: tuple[int, ...] = Field(min_length=1)
    max_count: int = Field(ge=1)

    @model_validator(mode="after")
    def _check(self) -> DiceRules:
        if len(set(self.sides)) != len(self.sides) or any(s < _MIN_SIDES for s in self.sides):
            raise ValueError("sides 必須是不重複且 ≥ 2 的整數")
        return self


class AttrWeights(ContentModel):
    int_: int = Field(alias="int", ge=0)
    wis: int = Field(ge=0)
    wil: int = Field(ge=0)


class DurationRules(ContentModel):
    """狀態與表面持續的旋鈕上限。"""

    cap: int = Field(ge=1)
    """持續的絕對上限（回合）。"""
    movement_extra: int = Field(ge=0)
    """移動類狀態可比預設持續多幾回合（硬控不可延長）。"""
    other_extra: int = Field(ge=0)
    """其他狀態可比預設持續多幾回合。"""
    surface_extra: int = Field(ge=0)
    """表面可比預設持續多幾回合。"""
    status_weight: int = Field(ge=1)
    surface_weight: int = Field(ge=1)


class StructureRules(ContentModel):
    """核心、形狀、效果的抽選。"""

    knob_weight_core: int = Field(ge=1)
    """核心效果的旋鈕權重。"""
    knob_weight_other: int = Field(ge=1)
    push_pull_distances: tuple[int, ...] = Field(min_length=1)
    """推拉距離旋鈕的階梯。"""
    blow_distances: tuple[int, ...] = (2, 3)
    """吹送距離旋鈕的階梯（Phase 3-54a）。"""
    blow_surface_permille: int = Field(default=0, ge=0, le=1000)
    """範圍骨架加上吹送附帶效果的機率（Phase 3-54a；獨立的亂數串流，沒抽中的種子結果不變）。"""
    shockwave_permille: int = Field(default=0, ge=0, le=1000)
    """大地主題、直線形狀的範圍骨架加上震波附帶效果的機率（Phase 3-54b；獨立的亂數串流）。"""
    displace_second_core_permille: int = _PERMILLE
    combo_double_damage_permille: int = _PERMILLE
    control_buff_permille: int = _PERMILLE
    """控場骨架的核心狀態是自我增益的機率。"""
    stun_min_cooldown: int = Field(ge=0)
    big_ring_radius: int = Field(ge=1)
    big_cone_size: int = Field(ge=1)
    """環形半徑、錐形大小達到這個值就算大範圍（強制冷卻）。"""
    cross_zero_range_permille: int = _PERMILLE
    """十字與 3×3 的施放距離為 0（以自身為中心）的機率。"""
    cross_min_range: int = Field(ge=0)
    other_min_range: int = Field(ge=0)
    fallback_secondary: tuple[str, ...]
    """骨架沒有指定附帶原語清單時的後備清單。"""


class ConditionRules(ContentModel):
    skill_permille: int = _PERMILLE
    """稀有（含）以上的技能有條件的機率。"""
    effect_level_permille: int = _PERMILLE
    """有條件時，條件掛在單一效果（而非整個技能）的機率。"""
    target_conditions: tuple[str, ...]
    """目標型條件（需要影響範圍內有敵人）。"""
    extra_conditions: tuple[str, ...] = ()
    """低權重的額外目標型條件（Phase 3-24c）：已經抽到目標型條件時，以 ``extra_permille`` 的機率改成
    從這裡抽（用 ``rng.fork`` 的獨立串流，沒有抽到的種子得到與加入之前完全相同的技能）。"""
    extra_permille: int = 0
    affinity_permille: int = 0
    """武器親和（Phase 3I-5）：給了主角手上的裝備時，附帶效果上的常見條件換成「手持某種武器時」的
    機率（‰；:func:`trpg.skillgen.affinity.grant_affinity`，用技能 ID 決定的確定性抽籤）。"""
    self_conditions: tuple[str, ...] = ("self_hp_below",)
    """施放者條件（只看施放者，Phase 3C-6b 加入連段條件）；技能層級的條件不需要影響範圍內有對象。"""
    target_hp_below: IntRange
    self_hp_below: IntRange


class CostRules(ContentModel):
    spell_mana_per_ap: IntRange
    """法術的法力 ＝ 這個範圍的亂數 × AP ＋ （階級 − 1）× ``spell_mana_per_tier``。"""
    spell_mana_per_tier: int = Field(ge=0)
    weapon_free_permille: int = _PERMILLE
    """武器技不花法力的機率。"""
    weapon_mana_per_ap: IntRange
    no_cooldown_permille: int = _PERMILLE
    """AP 不超過 ``no_cooldown_max_ap`` 時沒有冷卻的機率。"""
    no_cooldown_max_ap: int = Field(ge=1)
    cooldown_base_max: int = Field(ge=1)
    """冷卻 ＝ 1 到（``cooldown_base_max`` ＋ AP）的亂數。"""
    cooldown_cap: int = Field(ge=1)
    uses_per_battle_permille: int = _PERMILLE
    uses_per_battle: IntRange
    self_status_permille: int = _PERMILLE
    """主動技能加入自身狀態代價（``cost.self_status``）的機率（Phase 2H-1）。"""
    self_status_duration: IntRange
    """自身狀態代價的持續回合範圍（必須在 2–3 之內；持續時間固定的狀態，如暈眩，以
    ``allowance.self_status.fixed_duration`` 為準）。"""
    overdraft_permille: int = 0
    """主動技能加入透支（``cost.overdraft``）的機率（Phase 3-50；3-50b 起可和自身狀態並用）。"""

    @model_validator(mode="after")
    def _check_self_status_duration(self) -> CostRules:
        if self.self_status_duration.min < 2 or self.self_status_duration.max > 3:  # noqa: PLR2004
            raise ValueError("self_status_duration 必須在 2–3 之內")
        return self


class TuningRules(ContentModel):
    """強度調整的目標比例與步長（組合器收在合格區間內）。"""

    low_permille: int = Field(ge=1, le=1000)
    high_permille: int = Field(ge=1, le=1000)
    target_margin_permille: int = Field(ge=0, le=1000)
    """目標比例均勻分佈在 ``[low, high − margin]``。"""
    target_steps: int = Field(ge=1)
    jump_share_permille: int = Field(ge=1, le=1000)
    """依缺口一次跳多格時，實際跳的比例。"""

    @model_validator(mode="after")
    def _check(self) -> TuningRules:
        if self.low_permille + self.target_margin_permille > self.high_permille:
            raise ValueError("low_permille ＋ target_margin_permille 不可超過 high_permille")
        return self


class PassiveRules(ContentModel):
    """被動技能的抽選（Phase 2E-1 3.7）。

    ``skeleton_permille``：稀有度 epic 以上、未指定骨架時，改組被動的機率（用獨立的亂數串流抽，
    所以沒有抽到被動的種子與 2D 的技能完全相同）。
    """

    skeleton_permille: int = _PERMILLE
    other_permille: int = _PERMILLE
    """觸發時機有另一方時，效果作用在另一方（``target: other``）的機率（其餘作用在持有者）。"""
    second_effect_permille: int = _PERMILLE
    """被動多帶一個附帶效果的機率。"""
    mana: IntRange
    """法力（階級 −1 後另加 ``mana_per_tier`` × 階級）。"""
    mana_per_tier: int = Field(ge=0)
    cooldown_permille: int = _PERMILLE
    """有冷卻的機率。"""
    cooldown: IntRange


class ReactionRules(ContentModel):
    """反應技的抽選（Phase 2E-2 4.1）。

    ``skeleton_permille``：稀有度 rare 以上、未指定骨架時，改組反應技的機率（獨立的亂數串流，
    沒抽到的種子與 2E-1 的技能完全相同；抽到但做不出合格技能時退回一般主動技能）。
    """

    skeleton_permille: int = _PERMILLE
    intercept_permille: int = _PERMILLE
    """事件為 ``ally_hit_adjacent``（擋攻擊，形狀 self）的機率；其餘事件三選一。"""
    self_permille: int = _PERMILLE
    """非擋攻擊的反應技是自身增益（形狀 self）的機率；其餘對觸發者（形狀 single）。"""
    second_effect_permille: int = _PERMILLE
    """多帶一個附帶效果的機率。"""
    mana: IntRange
    mana_per_tier: int = Field(ge=0)
    cooldown_permille: int = _PERMILLE
    cooldown: IntRange


class StanceRules(ContentModel):
    """姿態的抽選（Phase 2E-2 4.3）。"""

    skeleton_permille: int = _PERMILLE
    """稀有度 rare 以上、未指定骨架時，改組姿態的機率（獨立的亂數串流）。"""
    shield_permille: int = _PERMILLE
    """姿態之外多帶一個自身護盾（有強度旋鈕，讓高階也湊得到預算）的機率；階級 2 以上一定帶。"""
    mana: IntRange


class BuilderRules(ContentModel):
    """蓄力與終結的抽選（Phase 2E-3 5.1）。"""

    skeleton_permille: int = _PERMILLE
    """稀有度 rare 以上、未指定骨架時，改組蓄力／終結技的機率（獨立的亂數串流）。"""
    builder_permille: int = _PERMILLE
    """技能是累積層數（``add_stack``）的機率（其餘為消耗層數）。"""
    max_amount: int = Field(default=1, ge=1)
    """``add_stack`` 一次累積層數的旋鈕上限（再受該層數的 ``max`` 限制）。"""
    per_stack: LadderRange
    """``consume_stack`` 的 ``per_stack_permille`` 階梯（‰；``range(start, stop, step)``）。"""
    max_required_stacks: int = Field(default=1, ge=1)
    """消耗施放者層數的技能，``cost.stacks`` 抽 1 到這個值（再受該層數的 ``max`` 限制）。"""
    required_permille: int = _PERMILLE
    """消耗施放者層數的技能帶 ``cost.stacks`` 的機率。"""


class TrapRules(ContentModel):
    """陷阱的抽選（Phase 2E-3 5.2）。"""

    skeleton_permille: int = _PERMILLE
    """稀有度 rare 以上、未指定骨架時，改組陷阱的機率（獨立的亂數串流）。"""
    delay_permille: int = _PERMILLE
    """觸發方式為 ``delay`` 的機率（其餘為 ``enter``）。"""
    enter_rounds: IntRange
    """``enter`` 陷阱的存續輪數。"""
    delay_rounds: IntRange
    """``delay`` 陷阱的延遲輪數。"""
    shape_weights: dict[Literal["single", "cross", "square3"], int]
    """觸發範圍 ``trap.shape`` 的抽選權重。"""


class RuneRules(ContentModel):
    """刻印技能的抽選（Phase 3-23；``rune`` 骨架）。"""

    skeleton_permille: int = _PERMILLE
    """稀有度 rare 以上、未指定骨架時，改組刻印技能的機率（獨立的亂數串流；低權重）。"""


class SacrificeRules(ContentModel):
    """獻祭召喚物技能的抽選（Phase 3-24c；``sacrifice`` 骨架）。"""

    skeleton_permille: int = _PERMILLE
    """稀有度 rare 以上、未指定骨架時，改組獻祭技能的機率（獨立的亂數串流；低權重）。"""
    heal_permille: int = _PERMILLE
    """獻祭技能是治療（沒有 element）而非爆炸的機率。"""


class ScalingRules(ContentModel):
    """雙屬性縮放與專精加成的抽選（Phase 2H-2；主動技能，強度調整成功之後才抽）。

    ``dual_permille``：稀有度夠（``core.yaml`` 的 ``dual_scaling_min_rarity``）時加第二縮放屬性的
    機率；第二屬性從技能的縮放允許範圍（``skill_scaling.yaml``，主屬性以外）抽一個（3H-7；範圍
    裡沒有別的屬性時不給）。``mastery_permille``：沒有第二屬性、且有合法專精時給 ``mastery`` 的
    機率（``range`` 需要施放距離、``duration`` 需要施加狀態）。
    """

    dual_permille: int = _PERMILLE
    mastery_permille: int = _PERMILLE


class SpecialRules(ContentModel):
    """修正技能與傳說（Phase 3C-6b；:mod:`trpg.skillgen.composer_special`）。"""

    modifier_permille: int = _PERMILLE
    """稀有度史詩以上、未指定骨架時改組修正技能（``kind: modifier``）的機率（獨立的亂數串流）。"""


class VariantCondition(ContentModel):
    """組合器與進化的變奏候選：一個條件（名稱用來組成型態名）。"""

    id: str
    name_zh: str
    when: VariantWhen


class VariantChange(ContentModel):
    """組合器與進化的變奏候選：一項替換內容（恰好一欄）。"""

    id: str
    name_zh: str
    shape: ShapeSpec | None = None
    range_delta: int | None = None
    element: Element | None = None
    add_effect: EffectSpec | None = None

    @model_validator(mode="after")
    def _check(self) -> VariantChange:
        given = [
            n
            for n in ("shape", "range_delta", "element", "add_effect")
            if getattr(self, n) is not None
        ]
        if len(given) != 1:
            raise ValueError(f"變奏候選 {self.id} 的替換內容必須恰好填一欄，收到 {len(given)} 欄")
        return self


class VariantRules(ContentModel):
    """戰場變奏的組合器設定（Phase 3-25b，6.24）。"""

    permille: int = _PERMILLE
    """稀有度 rare 以上的主動技能，組好之後再加一個變奏的機率（獨立的亂數串流；低權重）。"""
    conditions: tuple[VariantCondition, ...] = Field(min_length=1)
    changes: tuple[VariantChange, ...] = Field(min_length=1)
    """候選＝條件 × 替換內容的所有組合；依亂數順序逐一試，第一個通過驗證的採用。"""


class LlmTopicRules(ContentModel):
    """LLM 提議題目的多樣性參數（Phase 4-L6，``docs/phases/Phase4計畫.md`` 3C 節）。

    結構的多樣性由引擎決定，不交給模型的偏好：核心原語由種子加權抽出（含 run 內配額）、附帶原語與
    條件只開放一部分（輪替選單）。權重與數量都在這裡，不寫死在程式。
    """

    secondary_count: int = Field(default=6, ge=0)
    """輪替選單：附帶原語最多開放幾個（題目關鍵字要的必收，不計入）。"""
    condition_count: int = Field(default=4, ge=0)
    """輪替選單：條件最多開放幾個（題目關鍵字要的與骨架必要的必收，不計入）。"""
    core_exclude: tuple[str, ...] = ("enter_form", "leave_form")
    """不能被抽成題目核心原語的原語（形態只由手寫內容提供）。"""
    core_weights: dict[str, int] = Field(default_factory=dict)
    """核心原語的基礎權重（沒列出的用 ``base_weight``）。"""
    base_weight: int = Field(default=100, ge=1)
    quota_percent_per_use: int = Field(default=100, ge=0)
    """run 內配額：原語已出現在這一輪的候選 ``n`` 次時，權重 ＝ 基礎權重 × 100 ÷
    （100 ＋ ``n`` × 這個值）（整數除法，至少 1）。0 ＝ 不看配額。"""

    def weight_of(self, primitive: str, uses: int) -> int:
        base = self.core_weights.get(primitive, self.base_weight)
        return max(1, base * 100 // (100 + uses * self.quota_percent_per_use))


class CostStep(ContentModel):
    """費用旋鈕的一階（Phase 4-L8b）：每一階各自獨立（不累加），省略的欄位不動；套用時各欄位取
    「技能原本的值」與「這一階的值」中較大者，不會把已有的較高費用往下調。"""

    ap: int | None = Field(default=None, ge=1, le=3)
    """主動技能的 AP。"""
    cooldown: int | None = Field(default=None, ge=1)
    """冷卻回合。"""
    mana: int | None = Field(default=None, ge=1)
    """法力（法術技）；武器技依 ``allowance.stamina_per_mana`` 換成等價的耐力。"""


class LlmCostRules(ContentModel):
    """LLM 提議的費用旋鈕（Phase 4-L8b，4-L3 待決 #2、4-L8 待決 #6）：結構在最低費用下仍超出預算時，
    補值器依序往上試 ``steps``（由輕到重），取第一個讓預算比例回到上限以內的；之後才照一般旋鈕調到
    區間內。只在補值器作用（手寫技能與隨機組合器的費用、預算不受影響）；只用在主動技能。
    """

    steps: tuple[CostStep, ...] = ()
    """費用階梯（空 ＝ 不開放），由輕到重（預算折抵與 AP 係數單調上升；
    ``tests/skillgen/test_proposal_l8b_cost.py`` 檢查）。"""
    max_cooldown: int = Field(default=5, ge=1)
    """冷卻上限（06 6.5；比引擎的硬上限更保守）。"""

    @model_validator(mode="after")
    def _check(self) -> LlmCostRules:
        for i, step in enumerate(self.steps):
            if step.cooldown is not None and step.cooldown > self.max_cooldown:
                raise ValueError(f"steps[{i}]：冷卻 {step.cooldown} 超過 max_cooldown")
        return self


class ComposerRules(ContentModel):
    """``content/skill_composer.yaml``。"""

    rarity_weights: dict[Literal["common", "rare", "epic", "legendary"], int]
    ap_weights: dict[int, int]
    """AP 嘗試順序的權重。"""
    spell_share_permille: dict[str, int]
    """骨架 → 法術占比（‰）；``default`` 是沒列出的骨架。"""
    spell_any_weapon_permille: int = _PERMILLE
    """法術技的武器需求為「任何」（其餘為法器）的機率。"""
    spell_attr_weights: AttrWeights
    melee_permille: int = _PERMILLE
    """武器技是近戰（其餘為遠程）的機率。"""
    melee_dex_permille: int = _PERMILLE
    infuse_permille: int = _PERMILLE
    """武器技帶元素（其餘為物理）的機率。"""
    dice: DiceRules
    multipliers: tuple[LadderRange, ...] = Field(min_length=1)
    """武器倍率階梯（‰），依序接起來。"""
    duration: DurationRules
    structure: StructureRules
    condition: ConditionRules
    cost: CostRules
    tuning: TuningRules
    passive: PassiveRules
    reaction: ReactionRules
    stance: StanceRules
    builder: BuilderRules
    trap: TrapRules
    rune: RuneRules
    sacrifice: SacrificeRules
    scaling: ScalingRules
    special: SpecialRules
    variant: VariantRules
    llm_topic: LlmTopicRules = Field(default_factory=LlmTopicRules)
    """LLM 提議題目的多樣性參數（Phase 4-L6）。"""
    llm_cost: LlmCostRules = Field(default_factory=LlmCostRules)
    """LLM 提議的費用旋鈕（Phase 4-L8b）。"""

    @model_validator(mode="after")
    def _check(self) -> ComposerRules:
        if set(self.rarity_weights) != set(RARITY_ORDER):
            raise ValueError(f"rarity_weights 必須剛好有 {', '.join(RARITY_ORDER)}")
        if sorted(self.ap_weights) != [1, 2, 3]:
            raise ValueError("ap_weights 必須剛好有 AP 1、2、3")
        if any(w < 0 for w in (*self.rarity_weights.values(), *self.ap_weights.values())):
            raise ValueError("權重不可為負")
        if sum(self.rarity_weights.values()) <= 0 or sum(self.ap_weights.values()) <= 0:
            raise ValueError("權重總和必須大於 0")
        if "default" not in self.spell_share_permille:
            raise ValueError("spell_share_permille 必須有 default")
        if any(not 0 <= v <= _PERMILLE_MAX for v in self.spell_share_permille.values()):
            raise ValueError("spell_share_permille 必須在 0–1000")
        return self

    def multiplier_ladder(self) -> tuple[int, ...]:
        return tuple(v for r in self.multipliers for v in range(r.start, r.stop, r.step))

    def summary(self) -> str:
        weights = "／".join(str(w) for w in self.rarity_weights.values())
        return f"稀有度權重 {weights}"
