"""隨機技能組合器的調參資料（``content/skill_composer.yaml``；Phase 2C-1 3.1）。

這些數值是「抽選機率與範圍」，不是演算法：稀有度與 AP 的權重、法術比例、骰子與倍率的階梯、
條件與代價的機率與範圍、強度調整的目標區間……改動它們會改變隨機技能的分佈（種子對應的技能也會
不同），但不需要改程式。組合的流程與亂數呼叫順序仍在 ``trpg.skillgen``。

只定義 schema；``trpg.content`` 不得匯入 ``trpg.skillgen``。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel
from trpg.content.skills import RARITY_ORDER, EffectSpec, ShapeSpec, VariantWhen
from trpg.shared.types import Element

__all__ = [
    "WEAPON_ACTION_SUFFIXES",
    "AttrWeights",
    "ComposerRules",
    "ConditionRules",
    "CostRules",
    "CostStep",
    "DiceRules",
    "DurationRules",
    "ExploitCarrier",
    "ExploitRules",
    "ExploitTarget",
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
    "WhiteboardRecipe",
    "WhiteboardRules",
    "recipe_display_names",
    "whiteboard_name_problems",
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
    obstacle_exclude: tuple[str, ...] = ()
    """不當造牆候選的物件 ID（NW-3c，玩法 PM 交接 4.1.15）：``create_obstacle`` 只從
    ``blocks_move`` 且非 ``explosive`` 的物件抽，再拿掉這裡列的（例：冷卻井，打破就造水）。
    ID 必須是 ``objects.yaml`` 的物件（載入時檢查）。"""


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
    「技能原本的值」與「這一階的值」中較大者，不會把已有的較高費用往下調（過弱階梯 ``weak_steps``
    的 ``ap`` 例外：取較小者，見 :class:`LlmCostRules`）。"""

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
    weak_steps: tuple[CostStep, ...] = ()
    """過弱階梯（Phase 4-L10b，4-L9 建議 B1）：旋鈕（含巢狀效果）全部調完仍低於預算下限時依序試，
    取第一個讓比例落進驗證器窗的。``ap`` 往下取（原本與這一階的較小者），``cooldown``／``mana``
    往上取（較大者）。空 ＝ 不開放。"""

    @model_validator(mode="after")
    def _check(self) -> LlmCostRules:
        for name, steps in (("steps", self.steps), ("weak_steps", self.weak_steps)):
            for i, step in enumerate(steps):
                if step.cooldown is not None and step.cooldown > self.max_cooldown:
                    raise ValueError(f"{name}[{i}]：冷卻 {step.cooldown} 超過 max_cooldown")
        return self


class WhiteboardRecipe(ContentModel):
    """白板「單一效果」模式的一個配方（Phase 3W-4，06 6.34.1）：一個關鍵字、一個核心效果。

    ``effect`` 是 ``SkillDef.effects[0]`` 的字典（旋鈕欄位由組合器的強度調整填值）；``skeleton``
    決定驗證用的骨架。主動配方的 ``shapes`` 是可選的形狀（簡單：單體或小範圍）；被動配方用
    ``trigger_event``（``trigger.event``）；反應配方用 ``reaction_event``。
    """

    id: str = Field(min_length=1)
    keyword: str = Field(min_length=1)
    skeleton: str = Field(min_length=1)
    effect: dict[str, Any] = Field(default_factory=dict)
    name_zh: str = Field(min_length=1)
    weapon_name_zh: str | None = Field(default=None, min_length=1)
    """武器技版本的名稱（6F-1：和法術版同名時用來區分，例「冰錐刺」）；省略＝同 ``name_zh``。"""
    concept_zh: str = Field(min_length=1)
    flavor_zh: str = Field(min_length=1)
    theme: Element | None = None
    """技能的主題元素（名稱與標籤）；省略 ＝ 取 ``effect.element``，仍無則為物理。"""
    shapes: tuple[str, ...] = ("single",)
    categories: tuple[Literal["spell", "weapon"], ...] = ("spell", "weapon")
    trigger_event: str | None = None
    reaction_event: str | None = None
    species: Literal["basic", "summon", "trap", "stance", "displace", "modifier", "dual"] = "basic"
    """種類：``basic`` 是 3W-4 的單一效果；其餘是 6.34.9 依角色階級開放的新種類（3W-4b）。"""
    min_tier: int = Field(default=1, ge=1)
    """最低角色階級（6.34.9：召喚、陷阱、姿態、位移 2 階；修正型被動、雙屬性縮放 3 階）。"""
    max_tier: int | None = Field(default=None, ge=1)
    """最高角色階級（數值固定的配方，例如不同點數的姿態狀態，只在對得上預算的階級出）。"""
    creation_tier: int | None = Field(default=None, ge=1)
    """創角例外（6.34.9，Phase 3W-9）：創角的起始技能可以在這一階就用這個配方（例如 1 階的召喚
    白板），不受 ``min_tier`` 限制；三選一照 ``min_tier``。"""
    condition: dict[str, Any] | None = None
    """核心效果的條件（潮濕、倒地、撞擊的「利用者」白板：條件傷害本身算一個核心效果）。"""
    rider: dict[str, Any] | None = None
    """第二個效果：製造者例外的「弱傷害＋製造關鍵字」（核心是傷害）、位移白板的小補強。"""
    min_cooldown: int | None = Field(default=None, ge=1)
    """主動白板的最低冷卻（6F-4g：掀地這種範圍硬控至少冷卻 2）。照舊擲冷卻，再取兩者較大的；
    省略＝照 ``whiteboard.cooldown``。"""
    skill: dict[str, Any] = Field(default_factory=dict)
    """``SkillDef`` 欄位的覆寫（種類、AP、形狀、陷阱、修正規則、第二縮放屬性、武器需求……）。"""
    vary: tuple[dict[str, Any], ...] = ()
    """強度調整前可選的數值變化（深度合併進技能字典；``effect0``／``effect1`` 合併進效果）。"""
    starter: bool = True
    """創角的起始技能可以用這個配方（BAL-19f 追加：號令型武器技只出在三選一，創角選「召喚物」
    照 6.34.1 給召喚白板）。"""
    uses: str | None = None
    """自動生成的利用者白板（6F-4b，#129）：條件利用的關鍵字。手寫配方不填；有值的配方只在呼叫端
    指定「要利用哪個關鍵字」時出（:func:`trpg.content.whiteboard_exploit.exploit_recipes`）。"""


WEAPON_ACTION_SUFFIXES: tuple[str, ...] = ("擊", "斬", "刺", "射", "撞", "刀")
"""名稱已經是武器打法的結尾（6L-1：武器版不另取名也不會和法術版混淆）。"""


def recipe_display_names(recipe: WhiteboardRecipe) -> dict[str, str]:
    """配方產生的技能顯示名：``{"spell": 法術版, "weapon": 武器版}``（只列配方開放的種類）。"""
    names: dict[str, str] = {}
    if "spell" in recipe.categories:
        names["spell"] = recipe.name_zh
    if "weapon" in recipe.categories:
        names["weapon"] = recipe.weapon_name_zh or recipe.name_zh
    return names


def whiteboard_name_problems(
    active: Sequence[WhiteboardRecipe], every: Sequence[WhiteboardRecipe]
) -> list[str]:
    """同名檢查（6L-1，玩法 PM：顯示名相同、技能內容不同要報錯）：

    - 不同配方產生的技能不可同名（含武器版名稱）。
    - 主動的基本配方同時開放法術與武器時，武器版要有 ``weapon_name_zh``（照武器打法加動作字，
      例「火球擊」），除非名稱本來就以動作字結尾（:data:`WEAPON_ACTION_SUFFIXES`）。
    - ``weapon_name_zh`` 不可和 ``name_zh`` 相同。"""
    problems: list[str] = []
    owner: dict[str, str] = {}
    for recipe in every:
        for name in sorted(set(recipe_display_names(recipe).values())):
            other = owner.setdefault(name, recipe.id)
            if other != recipe.id:
                problems.append(f"白板配方 {other} 與 {recipe.id} 的技能同名：{name}")
        if recipe.weapon_name_zh is not None and recipe.weapon_name_zh == recipe.name_zh:
            problems.append(f"白板配方 {recipe.id} 的 weapon_name_zh 和 name_zh 相同")
    for recipe in active:
        dual = {"spell", "weapon"} <= set(recipe.categories)
        if (
            dual
            and recipe.species == "basic"
            and recipe.weapon_name_zh is None
            and not recipe.name_zh.endswith(WEAPON_ACTION_SUFFIXES)
        ):
            problems.append(
                f"白板配方 {recipe.id} 的武器版和法術版同名（{recipe.name_zh}）："
                "請加 weapon_name_zh"
            )
    return problems


class ExploitTarget(ContentModel):
    """利用者白板的條件對象（一個狀態或表面）的用字（6F-4b）。"""

    prefix_zh: str = Field(min_length=1)
    """名稱前綴（例「趁燃」）；名稱＝前綴＋元素的名詞。"""
    target_zh: str = Field(min_length=1)
    """說明用的對象（例「燃燒中的目標」）。"""
    flavor_zh: str = Field(min_length=1)


class ExploitCarrier(ContentModel):
    """利用者白板的傷害元素的用字（6F-4b）。"""

    noun_zh: str = Field(min_length=1)
    """名稱的名詞（例「雷擊」）；以動作字結尾，武器版不另取名。"""
    name_zh: str = Field(min_length=1)
    """元素名（說明用，例「雷電」）。"""


class ExploitRules(ContentModel):
    """自動生成的利用者白板（6F-4b，#129；06 6.34.1「利用者白板＝一段條件傷害」）：關鍵字推導表裡
    每一條 ``conditions`` 種類的利用規則（對某狀態或表面的目標）配上每一種 ``carriers`` 的傷害元素。
    ``statuses``／``surfaces`` 要涵蓋推導表裡所有這類規則（內容檢查）。"""

    skeleton: str = "strike"
    shapes: tuple[str, ...] = ("single",)
    conditions: tuple[str, ...] = ("target_has_status", "target_on_surface")
    statuses: dict[str, ExploitTarget] = Field(default_factory=dict)
    surfaces: dict[str, ExploitTarget] = Field(default_factory=dict)
    carriers: dict[Element, ExploitCarrier] = Field(default_factory=dict)
    effect_statuses: dict[str, str] = Field(default_factory=dict)
    """6F-4c（06 6.27.3 #129「第 2 招優先挑第 1 招真的造得出來的狀態或表面」）：效果本身沒寫
    ``status``、但結算時會施加某狀態的原語（例：``knock_prone`` → 倒地）。效果寫了 ``status``／
    ``surface`` 的直接算，不用列在這裡（:func:`trpg.skillgen.exploit_match.made_targets`）。
    6F-4d：只列引擎實際施加的（結算事實）；傷害元素不對應任何狀態（6F-4c 的 ``element_statuses``
    已刪）。"""
    offer_permille: int | None = Field(default=None, ge=0, le=1000)
    """6F-4d：一般三選一混進利用者白板的權重（‰）。該關鍵字的一般配方與混進的利用者白板都有時，
    先以這個機率決定從哪一組挑；``None`` ＝ 兩組合在一起平均抽（6F-4c 的做法）。"""
    bridge_permille: int | None = Field(default=None, ge=0, le=1000)
    """6F-4d：#130 雙關鍵字橋接先試利用者白板的機率（‰；獨立的 ``fork("pair/exploit")``）。沒中時
    跳過利用者白板，只試一般的雙關鍵字白板與手寫池（都沒有就照舊放寬）；``None`` ＝ 一律先試。"""

    @model_validator(mode="after")
    def _known_targets(self) -> ExploitRules:
        unknown = sorted(s for s in set(self.effect_statuses.values()) if s not in self.statuses)
        if unknown:
            raise ValueError(f"effect_statuses 的狀態沒有用字：{'、'.join(unknown)}")
        return self


class WhiteboardRules(ContentModel):
    """白板技能的產生規則（Phase 3W-4，``docs/design/06-技能.md`` 6.34.1；
    ``content/skill_composer.yaml`` 的 ``whiteboard``）。"""

    kind_permille: dict[Literal["active", "passive", "reaction"], int]
    """升級與任務三選一的種類比例（‰；07 7.6：主動 70％、被動 20％、反應 10％），總和 1000。"""
    tier: int = Field(default=1, ge=1)
    """沒有指定階級時的階級（創角的起始技能一律 1 階，6.34.9 創角例外）。"""
    ap_cost: int = Field(default=2, ge=1, le=3)
    """主動白板的預設 AP。"""
    cooldown: IntRange
    """主動白板的冷卻範圍（含兩端）。"""
    passive_mana: IntRange
    reaction_mana: IntRange
    reaction_cooldown: IntRange
    max_attempts: int = Field(default=60, ge=1)
    """一個種子最多重抽幾次（配方、形狀、費用與強度調整）。"""
    generic_keyword: str = "generic"
    """沒有關鍵字的基礎白板（通用池，#55）配方使用的關鍵字代號。"""
    exception_keywords: tuple[str, ...] = ("wet", "prone", "collision")
    """單一效果追不上預算下限的關鍵字（6.34.1）：利用者用條件傷害、製造者允許「弱傷害＋製造」。"""
    status_rider_keywords: tuple[str, ...] = ()
    """6F-4e（#129「第 1 招就該真的點燃」）：這些關鍵字的製造者白板可以是「傷害＋施加該關鍵字的狀態
    或造它的表面」（例：引火彈＝火焰傷害＋燃燒）。只放寬結構（兩個效果），不放寬預算，也不允許
    條件（和 ``exception_keywords`` 不同）。"""
    summon_ap_cost: int = Field(default=1, ge=1, le=3)
    """召喚白板的 AP（召喚物的點數固定，AP 2 湊不到預算下限）。"""
    summon_cooldown_max: int = Field(default=4, ge=0)
    """召喚白板的冷卻上限（冷卻換來較高的可用預算，讓不同強度的召喚物都落在 70～100%）。"""
    self_ap_cost: int = Field(default=1, ge=1, le=3)
    """自身位移、互換與自身增益白板的 AP（單一效果的點數固定，AP 2 湊不到預算下限）。"""
    simple_shapes: tuple[str, ...] = ("self", "single", "ground_tile", "cross", "square3")
    """白板允許的形狀（3W-R2 從程式移到資料）：自身、單體、單格、十字與 3×3（小範圍）；BAL-19f 起
    另有直線、錐形、環形、連鎖（資料檔）。"""
    self_move_effects: tuple[str, ...] = ("teleport", "swap", "leap")
    """自身位移或互換的原語（6.34.9 的「位移類」，不含推拉別人）：主動白板用 ``self_ap_cost``。"""
    displace_effects: tuple[str, ...] = ("teleport", "swap", "leap", "push", "pull")
    """位移類核心效果的原語：可以帶一個小補強（單一位移的點數追不上預算下限）。"""
    terrain_effects: tuple[str, ...] = ("raise_terrain", "lower_terrain")
    """升降地形的原語：單格的升降地形白板用 ``self_ap_cost``（3W-9）。"""
    exploit: ExploitRules | None = None
    """自動生成的利用者白板（6F-4b，#129）；``None`` ＝ 不生成。"""
    command_statuses: tuple[str, ...] = ()
    """號令型白板（BAL-19f 追加）的狀態：「傷害＋對自己施加這些狀態」算一個核心效果加號令附帶。"""
    active: tuple[WhiteboardRecipe, ...] = ()
    passive: tuple[WhiteboardRecipe, ...] = ()
    reaction: tuple[WhiteboardRecipe, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> WhiteboardRules:
        if sum(self.kind_permille.values()) != _PERMILLE_MAX or set(self.kind_permille) != {
            "active",
            "passive",
            "reaction",
        }:
            raise ValueError("kind_permille 必須剛好有 active、passive、reaction，總和 1000")
        ids = [r.id for r in (*self.active, *self.passive, *self.reaction)]
        if len(set(ids)) != len(ids):
            raise ValueError("白板配方 id 不可重複")
        if any(r.trigger_event is None for r in self.passive if r.species != "modifier"):
            raise ValueError("被動配方必須有 trigger_event（修正型被動除外）")
        every = (*self.active, *self.passive, *self.reaction)
        if any(not r.effect for r in every if r.species != "modifier"):
            raise ValueError("配方必須有核心效果 effect（修正型被動除外）")
        if any(r.reaction_event is None for r in self.reaction):
            raise ValueError("反應配方必須有 reaction_event")
        problems = whiteboard_name_problems(self.active, every)
        if problems:
            raise ValueError("；".join(problems))
        return self

    def recipes(
        self, kind: str, tier: int | None = None, *, creation: bool = False
    ) -> tuple[WhiteboardRecipe, ...]:
        """``kind``（active／passive／reaction）的配方；給了 ``tier`` 就只留角色階級開放的
        （``creation``：創角的起始技能另外開放 ``creation_tier`` 不高於 ``tier`` 的配方）。"""
        found = {"active": self.active, "passive": self.passive, "reaction": self.reaction}[kind]
        if tier is None:
            return found

        def opened(r: WhiteboardRecipe) -> bool:
            low = r.min_tier
            if creation and r.creation_tier is not None:
                low = min(low, r.creation_tier)
            return low <= tier and (r.max_tier or tier) >= tier

        return tuple(r for r in found if opened(r))

    def reserved_statuses(self) -> frozenset[str]:
        """白板配方專用的狀態（姿態）：完整模式的組合器不抽它們，既有種子的輸出不變。"""
        every = (*self.active, *self.passive, *self.reaction)
        return frozenset(
            str(r.effect["status"]) for r in every if r.species == "stance" and "status" in r.effect
        )

    def keywords(self) -> frozenset[str]:
        """有配方的關鍵字（任何種類）。"""
        return frozenset(r.keyword for r in (*self.active, *self.passive, *self.reaction))


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
    whiteboard: WhiteboardRules
    """白板技能的產生規則（Phase 3W-4）。"""

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
