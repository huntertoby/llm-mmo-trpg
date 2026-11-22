"""白板技能的閃現（靈光一閃）設定與模板（``content/flash_templates.yaml``；Phase 3W-1，
``docs/design/06-技能.md`` 6.34；玩法決定 #69、#70）。

這份資料只描述「規則數值」與「有哪些變化模板」；怎麼套用（純函式）在
:mod:`trpg.skillgen.flash_derive`，
閃現狀態（每招次數、變化歷程、先上場用過）在 :mod:`trpg.skillgen.flash_state`。

- ``rules``：次數上限、第幾次是大變化、每次的預算上限加成（‰）、完整技能、靈感點。
- ``pricing``：不指定類別（花 1 點出 4 個混合、至少涵蓋 2 類）與指定類別（花 2 點出 3 個）；
  重閃同價。
- ``categories``：變化的類別（範圍、連段、元素與關鍵字、費用、延長與收割、輔助、觸發；大變化的
  加深、橋接），各自限定可用的技能種類。
- ``minor``：小變化模板（第 1、2、4、5 次）；``op`` 的實作在
  :data:`trpg.skillgen.flash_ops.FLASH_OPS`
  （3W-1 只實作 ``area``、``range``，其餘由 3W-2 補上）。
- ``major``：大變化（第 3 次）沿用 ``skill_evolution.yaml`` 的進化模板（以 ID 引用）。
- ``transforms``：主動 → 被動／反應的轉型模板（3W-3 實作；有合法轉型時一定是選項之一，#70）。

跨檔案檢查（``major`` 引用的進化模板存在且分支相符、轉型的觸發時機存在）在
:mod:`trpg.content.library` 載入時。
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.quantity import quantity_cap
from trpg.content.schemas import ContentModel, field_bounds
from trpg.content.skills import EffectSpec, ReactionSpec, ShapeSpec, TrapSpec, TriggerSpec
from trpg.content.skills.modifiers import ModifierChange

__all__ = [
    "DRAFT_COST_FIELDS",
    "FLASH_KINDS",
    "INHERIT_RECORDS_FORMAT_MAX",
    "USAGE_SCORE_OPS",
    "BattleVariantText",
    "CompleteSkillRules",
    "ExtraMajorTemplate",
    "FlashCategory",
    "FlashHeadline",
    "FlashKind",
    "FlashPricing",
    "FlashRules",
    "FlashSearch",
    "FlashTable",
    "FlashTemplate",
    "FlashTerm",
    "MajorFlashTemplate",
    "PriceRule",
    "TransformTarget",
    "TransformTemplate",
    "UsageScoreOp",
    "VariantPlace",
]

type FlashKind = Literal["active", "passive", "reaction", "stance", "modifier"]
FLASH_KINDS: tuple[FlashKind, ...] = ("active", "passive", "reaction", "stance", "modifier")


type CostCutField = Literal["stance_upkeep", "cooldown", "mana", "stamina", "ap_cost"]
type EntryCostField = Literal["ap_cost", "cooldown", "mana", "stamina"]
"""姿態的「進入代價」（施放費用）可以動的欄位（BAL-10b）；維持費不在內（#67）。"""


class CostCut(ContentModel):
    """完整技能沒有可加的數值時，依序減的一項代價（3W-5b）：``field`` 減 ``step``。
    HC-4c 起 ``step`` 必填（法力、耐力是量類，內容檔寫 10）。"""

    field: CostCutField
    step: int = Field(ge=1, le=10)


def _ladder(values: tuple[int, ...], name: str) -> tuple[int, ...]:
    if not values or values[0] != _NEUTRAL or list(values) != sorted(set(values)):
        raise ValueError(f"{name} 必須從 1000 開始、嚴格遞增")
    return values


_NEUTRAL = 1000
_FIXED_MODIFIER_CHANGES = frozenset({"form_upkeep_permille"})
"""不能當閃現旋鈕的修正改變：形態維持費照 #67 固定（化形專精減半）。"""


class CompleteSkillRules(ContentModel):
    """完整技能（6.34.6）：視為「已閃 ``flashes`` 次」、預算上限 +``budget_permille``‰、不能再閃，
    可以重閃換掉一個附帶效果或形狀。

    強度怎麼加上去（3W-5b，06 6.34.6「沒有一般數值可調的結構」）：預算器的強度旋鈕（傷害、治療、
    護盾的骰子或倍率、推拉距離）之外，召喚再加 ``summon_power_steps``（召喚物 HP 與傷害的倍率，
    乘在原本的 ``power_permille`` 上）、姿態再加 ``stance_magnitude_steps``（姿態幅度）一起重調；
    仍然調不上去時，依 ``cost_cuts`` 的順序一次減一格代價，直到預算分數達到 +``budget_permille``‰
    或沒有能減的。

    HC-4b3 起數字都必填（``content/flash_templates.yaml`` 的 ``rules.complete`` 每格都有寫）。"""

    flashes: int = Field(ge=0, le=9)
    budget_permille: int = Field(ge=0, le=1000)
    cap_permille: int = Field(ge=0, le=1000)
    """實際加上去的上限（06 6.34.6，玩法 PM ec73486f）：
    一步會超過時先用較細的旋鈕補，都不行才接受超過。"""
    stop_over_permille: int | None = Field(default=None, ge=0, le=1000)
    """BAL-12b 定（06 6.34.6）：都不行、要超過上限時，若會超過這個值，改成停在
    +``budget_permille``‰ 以下最接近的那一階（只走上限內的步子停下的版本）；省略＝接受超過。"""
    modifier_step: int | None = Field(default=None, ge=1, le=25)
    """BAL-12b 定：完整技能的修正幅度（傷害、治療）改用每 ``modifier_step``‰ 一格的細階梯；
    省略＝同升階重配的修正階梯。只用在完整技能。"""
    can_flash: bool = False
    can_reflash: bool = True
    summon_power_steps: tuple[int, ...]
    stance_magnitude_steps: tuple[int, ...]
    status_magnitude_steps: tuple[int, ...]
    """數值型狀態與表面的強度（BAL-12e，#76；``magnitude_permille``，乘在原本的強度上）。在效果參數
    那一組（持續回合等）一起加，比持續 +1 回合細。"""
    cost_cuts: tuple[CostCut, ...]
    """減代價的順序與步距（HC-4c 起必填，寫在 ``flash_templates.yaml`` 的 ``rules.complete``）。"""

    @model_validator(mode="after")
    def _check_ladders(self) -> CompleteSkillRules:
        _ladder(self.summon_power_steps, "summon_power_steps")
        _ladder(self.stance_magnitude_steps, "stance_magnitude_steps")
        _ladder(self.status_magnitude_steps, "status_magnitude_steps")
        return self


type UsageScoreOp = Literal[
    "area",
    "range",
    "reshape",
    "multi_hit",
    "followup",
    "followup_potency",
    "kill_refund",
    "extend",
    "charge",
    "light",
    "keyword_exploit",
    "keyword_imbue",
    "mod_keyword",
]
"""有用法分數的小變化 ``op``（:func:`trpg.skillgen.flash_offer._usage_score`；收束另看
``converge_usage_score``）。"""
USAGE_SCORE_OPS: tuple[UsageScoreOp, ...] = (
    "area",
    "range",
    "reshape",
    "multi_hit",
    "followup",
    "followup_potency",
    "kill_refund",
    "extend",
    "charge",
    "light",
    "keyword_exploit",
    "keyword_imbue",
    "mod_keyword",
)

DRAFT_COST_FIELDS: tuple[str, ...] = ("mana", "stamina", "cooldown")
"""轉型草稿依序試的代價可以寫的欄位（法力、耐力是換算前的單位，程式經 ``CoreRules.scaled_cost``
乘 ``quantity_scale``）。"""


class FlashSearch(ContentModel):
    """閃現生成器的搜尋參數（HC-5a 從 ``skillgen/flash_derive.py``、``flash_major.py``、
    ``flash_trade.py`` 搬來，值不變）。不是玩法數值，但會改變做得出來的招，所以寫在資料裡；不開進
    工坊。"""

    tune_attempts: int = Field(ge=1, le=10)
    """同一份草稿最多試幾次不同的調整亂數（強度下限讓一次調整失敗的機會變大）。"""
    strict_margin_millipoints: int = Field(ge=0, le=1000)
    """結構不變、只靠重調變強的變化（``STRICT_OPS``、護盾量提高）：預算分數至少要比變化前多
    這麼多「千分之一點」（10 ＝ 0.01 點）。"""
    cap_shrink_steps: int = Field(ge=1, le=20)
    """壓回單發上限時，目標比例最多往下退幾次。"""
    cap_shrink_permille: int = Field(ge=0, le=1000)
    """壓回單發上限時，目標比例每次再往下退多少‰（離散的骰子階梯可能一次跳過上限）。"""
    max_cost_cuts: int = Field(ge=0, le=50)
    """超過單發上限、改成減費用時，最多累計減幾格代價。"""

    @property
    def strict_margin(self) -> Fraction:
        return Fraction(self.strict_margin_millipoints, 1000)


def _steps_up(values: tuple[int, ...], name: str) -> tuple[int, ...]:
    if not values or values[0] < 1 or list(values) != sorted(set(values)):
        raise ValueError(f"{name} 必須非空、從正數開始嚴格遞增")
    return values


class FlashRules(ContentModel):
    """閃現的規則數值（6.34.2、6.34.3）。HC-4b3 起數字都必填（``content/flash_templates.yaml``
    的 ``rules`` 每格都有寫）；形態幅度的上限對照 ``enter_form`` 原語在載入內容庫時檢查。
    HC-5a 起小變化、轉型、出題的步階與上限也寫在這裡（原本是 ``skillgen/flash_*.py`` 的
    模組常數）。"""

    max_flashes: int = Field(ge=1, le=9)
    major_flash: int = Field(ge=1, le=9)
    """第幾次閃現是大變化（加深、橋接、轉型）。"""
    budget_step_permille: int = Field(ge=0, le=200)
    """每次閃現讓這招的預算上限多幾 ‰（佔同階預算；5 次共 +200‰）。"""
    needs_use: bool = True
    """閃現前這招要自上次閃現（或取得）後在戰鬥中用過（主動技放出 1 次；被動、反應、姿態裝備著
    打完一場）。"""
    reflash_needs_use: bool = False
    """重閃不需要先上場用過。"""
    dissolve_refund_permille: int = Field(ge=0, le=1000)
    """溶掉一招時退回「花在它身上的靈感點」的比例（‰，無條件捨去；#71：一半）。"""
    insight_per_win: int = Field(ge=0)
    """roguelite 原型每打贏一場給的靈感點（3W-5 接；HC-4c 起必填）。"""
    insight_start: int = Field(default=0, ge=0)
    """開局給的靈感點（BAL-1 經濟旋鈕；預設 0＝現行行為）。"""
    insight_preboss: int = Field(default=0, ge=0)
    """打贏最後一場一般戰鬥（下一場是 Boss）時額外加給的靈感點（BAL-1；預設 0）。"""
    usage_min_uses: int = Field(ge=0)
    """用法統計要有這麼多次放出才算數（3W-2）；不夠時先出通用變化（``generic``）。"""
    complete: CompleteSkillRules
    stance_magnitudes: tuple[int, ...]
    """沒有階梯的單一狀態姿態（狂怒、堅壁…，BAL-2b）費用、修正類小變化可換到的姿態幅度（‰，
    ``apply_status.magnitude_permille``）。比完整技能的級距寬：這些姿態是固定點數，角色階級高時
    要靠幅度把預算分數拉進預算窗。"""
    modifier_knobs: dict[str, tuple[int, ...]] = Field(default_factory=dict)
    """修正型被動除了傷害、治療幅度以外可以重調的幅度（BAL-10b；``ModifierChange`` 的欄位 → 由弱到
    強的值）。只給 ``mod_potency`` 在沒有正的傷害／治療幅度時與 BAL-10b 新增的修正模板用；形態維持費
    （``form_upkeep_permille``）照 #67 不列；冷卻、持續回合有自己的模板（``mod_cooldown``、
    ``mod_duration``），也不列。"""
    modifier_on_hit_dice: bool = True
    """同上，命中後效果（``on_hit_effects``）的骰子也當旋鈕（組合器的骰子階梯；BAL-10b）。"""
    modifier_fine_step: int = Field(ge=1, le=50)
    """BAL-10b 新增的修正模板重調正的傷害、治療幅度用的階梯間距（‰；從這個數到 1000）。"""
    modifier_potency_step: int | None = Field(default=None, ge=1, le=50)
    """閃現「強效」（``mod_potency``）重調正的傷害、治療幅度的階梯間距（‰；從這個數到 1000；
    BAL-11b）。省略時用舊階梯（50～1000 每 25）。只在閃現；升階重配、完整技能照舊。"""
    followup_multiplier_step: int | None = Field(default=None, ge=1, le=100)
    """接續段強化類（BAL-10b 的 ``followup_*``）重調接續段武器倍率的細階梯間距（‰；3000‰ 以下，
    與原階梯合併；BAL-11b）。省略時用原階梯。"""
    trigger_flat_bonus: int = Field(default=0, ge=0, le=quantity_cap(10))
    """被動、反應「效果 +」的細旋鈕（BAL-12b 定）：骰子重調不進預算窗時，法術傷害再試固定值
    +1～+n（``damage.flat_bonus``）。0 ＝ 不用。"""
    area_trap_shapes: tuple[str, ...] = ()
    """「範圍 +1」用在陷阱時（BAL-12b 定）：陷阱觸發範圍（``trap.shape``）依序換到下一個；空 ＝ 陷阱
    不改範圍（舊行為）。"""
    area_tile_shapes: tuple[str, ...] = ()
    """「範圍 +1」用在地面格（BAL-12b 定）：形狀依序換到下一個（例：指定格 → 十字）；空 ＝ 不改。"""
    extend_effects: tuple[str, ...] = ()
    """「延長」放寬的對象（BAL-12b 定）：原本的狀態、表面、區域延長不了時，這些效果的 ``duration``
    ＋1（召喚物存活、障礙、刻印）；陷阱另看 ``extend_trap``。"""
    extend_trap: bool = False
    """「延長」也加陷阱持續回合（``trap.rounds`` ＋1，BAL-12b 定）。"""
    modifier_drawback_step: int = Field(ge=1, le=500)
    """``mod_cost``（代價減輕）：負的傷害、治療幅度（‰）往 0 減輕多少（BAL-10b）。"""
    form_magnitudes: tuple[int, ...]
    """變身姿態（BAL-2c）修正類小變化與升階重配可換到的形態幅度（‰，``enter_form.magnitude_permille``；
    最後一格不能超過該參數的上限，載入內容庫時對照 ``skill_primitives.yaml``）。比
    ``stance_magnitudes`` 細：升階重配把形態拉到接近原本的比例（例如 99%）之後，一次閃現的 +40‰
    預算仍要放得下下一格。"""
    single_hit_cap_permille: int = Field(ge=1000, le=10000)
    """收回家族（收束起，BAL-10d，06 6.34.4）的單發上限：收回後一次施放對單一目標的期望傷害（治療、
    護盾同理）最多是「同階、同 AP 的單體技能預算」（``tier_budget`` × AP 係數）的這麼多‰；超過的預算
    改成減費用（減不動就不出這個選項）。"""
    converge_targets_permille: int = Field(ge=1000, le=10000)
    converge_usage_score: int = Field(ge=0, le=5)
    """收束的用法分數（BAL-10d2，原型 AI 權重）：這招放過、平均命中目標數（‰）低於
    ``converge_targets_permille`` 時，兩種收束各加這麼多分（換形狀在同樣條件下是 2 分，3 分讓
    常打單體的範圍技優先看到收束）。"""
    tighten_permille: int = Field(ge=0, le=1000)
    """專注的條件收緊一級（BAL-10e2，06 6.34.4「BAL-10e 定」）：預算器不幫條件計價，收緊一級固定
    視為拿掉這麼多‰（佔同階可用預算），和這次閃現的 ``budget_step_permille`` 一起換觸發效果或
    修正幅度。"""
    max_side_per_offer: int = Field(default=1, ge=0, le=4)
    """每次閃現（或重閃）最多出幾張側變（SK-1，06 6.38 第 3 點：最多 1 張）。"""
    # --- HC-5a：小變化（skillgen/flash_ops.py、flash_cost.py、flash_reclaim.py） ---
    charge_cooldown_step: int = Field(ge=1, le=6)
    """蓄力（主動技）每次把冷卻加幾回合（6.34.4）。"""
    max_charge_cooldown: int = Field(ge=0, le=6)
    """蓄力把冷卻加到最多幾回合（6.34.4）；姿態的「費用」小變化加冷卻也不超過這個數。"""
    charge_duration_cap: int = Field(ge=0, le=6)
    """蓄力累計最多比原招多幾回合（06 6.34 費用方向第 1 點）。"""
    max_triggers_per_round: int = Field(ge=1, le=9)
    """「每回合觸發次數上限 +1」最多加到幾次（再由驗證器的 6.6 硬上限擋）。"""
    hp_relax_step_permille: int = Field(ge=0, le=1000)
    """條件放寬一級：血量門檻（‰）放寬多少。"""
    hp_relax_max_permille: int = Field(ge=0, le=1000)
    """條件放寬後的血量門檻最多到這個值（‰）。"""
    hp_tighten_step_permille: int = Field(ge=0, le=1000)
    """專注的條件收緊一級：血量門檻（‰）收緊多少（同條件放寬的一級）。"""
    hp_tighten_min_permille: int = Field(ge=0, le=1000)
    """收緊後的血量門檻不低於這個值（‰）。"""
    added_hp_condition_permille: int = Field(ge=0, le=1000)
    """條件放寬多加的「或」分支、專注在沒有條件時加的條件：目標（或自身）血量低於這個值（‰）。"""
    max_empty_slots_cap: int = Field(ge=1, le=6)
    """「計數上限 +1」最多加到幾格（也不超過主動技能欄數；不能超過 ``empty_slots_cap`` 的
    schema 上限 6）。"""
    blood_bonus_permille: int = Field(ge=0, le=1000)
    """側變「以血支付」：生命代價的折抵比省下的法力／耐力折抵多這麼多 ‰（「威力略升」）。"""
    summon_hp_steps: tuple[int, ...]
    """召喚物最大 HP 加成（‰）的階梯：強壯（``summon_toughen``）與合體依序試，第一個過預算窗與
    下限的是結果。"""
    new_damage_multiplier_permille: int = Field(ge=1, le=10000)
    """小變化新增傷害效果時，武器技的起始倍率（‰；之後由旋鈕重調；法術技用骰子）。"""
    followup_potency_tries: int = Field(ge=0, le=50)
    """接續段強化依序試「第一段接續傷害往上 1～n 格」的草稿數。"""
    followup_ease_steps: int = Field(ge=0, le=20)
    """接續段範圍、距離、第二元素：原本的接續段傷害最多往下讓幾格。"""
    followup_fine_top_permille: int = Field(ge=0, le=10000)
    """接續段細階梯（``followup_multiplier_step``）只細到這裡（‰；以上照原階梯）。"""
    # --- HC-5a：出題（skillgen/flash_offer.py） ---
    usage_scores: dict[UsageScoreOp, int]
    """用法分數（原型 AI 權重；越高越優先）：小變化 ``op`` → 用法條件成立時加幾分（每個 op 的條件
    寫在程式）。"""
    usage_multi_targets_permille: int = Field(ge=0, le=10000)
    """平均目標數達到這個數（‰）視為「常打到多個目標」。"""
    usage_frequent_uses: int = Field(ge=0, le=100)
    """放出次數達到這個數視為常用（輕巧優先）。"""
    second_keyword_cap: int = Field(ge=1, le=20)
    """每個「第二個關鍵字」模板最多列幾個關鍵字。"""
    # --- HC-5a：大變化與轉型（skillgen/flash_major.py） ---
    transform_carry_max: int = Field(ge=1, le=4)
    """轉型帶得走的核心效果（敵對的傷害、狀態，或輔助技的友方效果）最多幾個。"""
    beside_power_step_permille: int = Field(ge=1, le=1000)
    """伴生、護主的縮小版召喚物：強度不在預算窗內時，每這麼多‰ 一格往上下試（最低是
    ``core.skill_limits.min_beside_power_permille``，最高 1000）。"""
    search: FlashSearch
    """生成器的搜尋參數（不是玩法數值）。"""

    @model_validator(mode="after")
    def _check(self) -> FlashRules:
        for name, values in self.modifier_knobs.items():
            if name not in ModifierChange.model_fields or name in _FIXED_MODIFIER_CHANGES:
                raise ValueError(f"modifier_knobs.{name} 不是可以重調的修正改變")
            if not values or list(values) != sorted(set(values), key=abs):
                raise ValueError(f"modifier_knobs.{name} 必須非空、由弱到強（絕對值嚴格遞增）")
        if self.major_flash > self.max_flashes:
            raise ValueError("major_flash 不可大於 max_flashes")
        _ladder(self.stance_magnitudes, "stance_magnitudes")
        _ladder(self.form_magnitudes, "form_magnitudes")
        _steps_up(self.summon_hp_steps, "summon_hp_steps")
        missing = [op for op in USAGE_SCORE_OPS if op not in self.usage_scores]
        if missing:
            raise ValueError(f"usage_scores 缺少：{', '.join(missing)}")
        return self

    def budget_bonus_permille(self, flashes: int) -> int:
        """閃了 ``flashes`` 次後的預算上限加成（‰）。"""
        return self.budget_step_permille * max(0, min(flashes, self.max_flashes))

    def is_major(self, nth: int) -> bool:
        return nth == self.major_flash


INHERIT_RECORDS_FORMAT_MAX: Final = field_bounds(FlashRules, "major_flash")[1] - 1
"""傳承請求 ``records`` 的格式上限（HC-7 a 裁定 4）：大變化最晚是 ``major_flash`` 的上限那一次，所以
小變化最多比它少 1 個。真正的上限是規則的 ``major_flash − 1``（``max_carry``），由傳承檢查並
說明。"""


class PriceRule(ContentModel):
    """一種出題方式的價格與選項數。"""

    cost: int = Field(ge=0)
    """花幾點靈感。"""
    options: int = Field(ge=1, le=6)
    """出幾個選項（不含指定類別時另列的轉型）。"""
    min_categories: int = Field(ge=1)
    """選項至少涵蓋幾類（做得到時；HC-4c 起必填）。"""


class FlashPricing(ContentModel):
    """出題方式（#70）：不指定類別（``open``）與指定類別（``focused``）。重閃和閃現同價。
    HC-4b3 起兩組都必填（``content/flash_templates.yaml`` 的 ``pricing``）。"""

    open: PriceRule
    focused: PriceRule
    reflash_same_price: bool = True
    """重閃的價格與選項數和閃現相同（#70）；之後若要不同價，改成另一組 ``PriceRule``。"""
    allow_focus: bool = True
    """是否允許指定類別（先選方向）。"""
    transform_guaranteed: bool = True
    """大變化時有合法轉型就一定是選項之一（不指定時佔其中一個；指定加深或橋接時另列一個）。"""

    def rule(self, focused: bool) -> PriceRule:
        return self.focused if focused else self.open


class FlashCategory(ContentModel):
    """一個變化類別。``stage``：``minor`` 用在第 1、2、4、5 次，``major`` 用在第 3 次。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    stage: Literal["minor", "major"] = "minor"
    kinds: tuple[FlashKind, ...] = ("active",)
    """可以出這類變化的技能種類。"""
    support_only: bool = False
    """只給輔助技（治療、護盾、增益，沒有傷害；
    見 :func:`trpg.skillgen.flash_category.is_support_skill`）。"""


_RIDER_OPS = frozenset({"self_rider", "active_rider"})
"""帶 ``rider`` 的改法（BAL-19e 附帶護身；SK-1 蓄勢、附淨化、附加速）。"""


class FlashTemplate(ContentModel):
    """一個小變化模板。數值欄位依 ``op`` 使用；強度不寫在這裡（套用後由預算器重調）。"""

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    op: str = Field(pattern=ID_PATTERN)
    """改法；實作登錄在 :data:`trpg.skillgen.flash_ops.FLASH_OPS`（沒有實作的模板不會出現）。"""
    kinds: tuple[FlashKind, ...] | None = None
    """限定的技能種類；省略時沿用類別的 ``kinds``。"""
    prefix_zh: str = Field(min_length=1)
    summary_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用 ``summary_zh``。"""
    headline_zh: str | None = None
    """選變體畫面的白話大標（FL-1b，移植需求 8.2；玩法 PM 寫）；可帶 ``{n}``（模板的
    ``delta``）。省略時畫面退回 ``summary_zh``。依關鍵字而不同的見 :attr:`FlashTable.headlines`。"""
    say_zh: str | None = None
    """選中時下固定區的一句話（FL-1b 9.3）；可帶 ``{shape}``、``{cells}``、``{range}``、
    ``{n}`` 與術語標記 ``[[術語|字]]``。省略時由差異清單照句型組。"""
    delta: int | None = Field(default=None, ge=-3, le=3)
    """``area``／``range`` 的增量（格）。"""
    shapes: tuple[ShapeSpec, ...] = ()
    """``reshape`` 的候選形狀（3W-2）。"""
    keywords: tuple[str, ...] = ()
    """限定可用的關鍵字（3W-2；``keyword_*`` 模板，例：輔助技只能加不會傷到友方的關鍵字，像「潮濕」
    「暗影」）；空 ＝ 不限（嫁接表有的都可以）。"""
    min_tier: int = Field(default=1, ge=1, le=3)
    """最低角色階級（#72，6.34.9）：角色階級不到就不出這個模板（1 階基本版、2 階 3×3／接續段／第二
    元素／範圍 +2、3 階整排直線／連鎖跳躍／雙屬性縮放）。第 3 次大變化不受階級限制。"""
    generic: bool = False
    """通用變化（3W-2）：用法統計不夠時（放出次數少於 ``rules.usage_min_uses``）先出這些。"""
    elements: tuple[str, ...] = ()
    """``element`` 模板的候選元素（3W-2）；空 ＝ 不限。"""
    min_cells: int | None = Field(default=None, ge=1)
    max_cells: int | None = Field(default=None, ge=1)
    """``terrain_area`` 的影響格數範圍（3W-2b，#58）：新形狀的格數（``cell_count``）要落在其中
    （2 階 4～6 格、3 階 7 格以上）。"""
    usage_base: int = Field(default=0, ge=0, le=5)
    """基本用法分（BAL-2b）：加在用法分數上。觸發、修正類沒有對應的用法統計（用法統計只記主動技的
    命中與目標），沒有基本分就永遠 0 分、被「全指定」策略排在最後；其他模板省略（0）。"""
    cost_fields: tuple[EntryCostField, ...] = ()
    """姿態的進入代價（施放費用）可以動的欄位，依序試（BAL-10b）：``stance_enter_light`` 減 1；
    姿態費用類（``stance_light``／``stance_heavy``）填了就也適用變身姿態（形態的維持費照 #67 不動，
    改用進入代價當費用旋鈕）。空 ＝ 不動進入代價（變身姿態不出費用類，同 BAL-2c）。"""
    skeletons: tuple[str, ...] = ()
    """收束（BAL-10d）：新形狀不在原骨架允許的形狀內時，依序改試的骨架（例：範圍骨架收成單體 →
    打擊、連擊）；只取允許新形狀的。空 ＝ 只用原骨架。"""
    rider: EffectSpec | None = None
    """附帶護身（``self_rider``，BAL-19e）：姿態進入時、反應觸發時多一個作用於自己的效果（護盾、
    治療、回復資源、淨化）。數值只是起點，套用後由預算器重調。SK-1 的 ``active_rider``（蓄勢、
    附淨化、附加速）也用這個欄位。"""
    side: bool = False
    """側變（SK-1，06 6.38 第 3 點）：換方向、不換強度的變化（換骨架、換元素、推 ↔ 拉、換觸發、
    以血支付）。每次閃現最多出 ``rules.max_side_per_offer`` 張。"""
    surfaces: tuple[str, ...] = ()
    """``surface_exploit``（利用地面，SK-1）的候選表面 ID。"""
    trigger_swaps: tuple[tuple[str, str], ...] = ()
    """``trigger_swap``（換觸發時機，SK-1）可以換的（原本, 換成）觸發時機或反應事件。"""

    @model_validator(mode="after")
    def _check(self) -> FlashTemplate:
        if (self.op in _RIDER_OPS) != (self.rider is not None):
            raise ValueError(
                f"模板 {self.id}：rider 只給 self_rider／active_rider 用，而且它們必須填"
            )
        if self.op == "self_rider" and self.rider is not None and self.rider.affects != "self":
            raise ValueError(f"模板 {self.id}：附帶護身的效果只能作用於自己（affects: self）")
        if self.op in ("area", "range") and not self.delta:
            raise ValueError(f"模板 {self.id}：{self.op} 必須填非 0 的 delta")
        if self.op == "terrain_area" and (not self.shapes or self.min_cells is None):
            raise ValueError(f"模板 {self.id}：terrain_area 必須填 shapes 與 min_cells")
        return self


class MajorFlashTemplate(ContentModel):
    """大變化模板：引用 ``skill_evolution.yaml`` 的進化模板（``evolution``），類別是加深或橋接。"""

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    evolution: str = Field(pattern=ID_PATTERN)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用進化模板的說明。"""
    headline_zh: str | None = None
    """選變體畫面的白話大標（FL-1b，移植需求 8.2；玩法 PM 寫）；可帶 ``{n}``（模板的
    ``delta``）。省略時畫面退回 ``summary_zh``。依關鍵字而不同的見 :attr:`FlashTable.headlines`。"""
    say_zh: str | None = None
    """選中時下固定區的一句話（FL-1b 9.3）；可帶 ``{shape}``、``{cells}``、``{range}``、
    ``{n}`` 與術語標記 ``[[術語|字]]``。省略時由差異清單照句型組。"""


type TransformTarget = Literal["passive", "reaction", "summon", "trap", "stance", "modifier"]


class TransformTemplate(ContentModel):
    """主動技轉型（6.34.5、#73）：把這招轉成別種技能。

    - ``to``：新種類。``passive``／``reaction`` 把效果縮小後掛到觸發（``trigger``）或反應
      （``reaction``）上；``summon`` 召喚一隻幫你打的召喚物（``units``）；``trap`` 放置陷阱
      （``trap``）；``stance`` 進入姿態（``stances``）；``modifier`` 修正型被動（持續改變你的
      同元素技能）。
    - ``min_tier``：最低角色階級（#73：1 階被動、反應；2 階起召喚、陷阱、姿態；3 階起修正型被動）。
    - 強度不寫在這裡：轉型後照新種類的預算由預算器重調。
    - ``source``（TF-1，#159）：適用的原招。``hostile``（預設）＝帶得走敵對效果的招；``summon``
      ＝召喚技（伴生、護主：效果是召喚到身邊，縮小幅度在 ``skill_budget.yaml`` 的
      ``flash_transform``）；``support`` ＝輔助技（沒有傷害的治療、護盾、增益：庇佑、援手）。
    - ``heal_reaction``（TF-1 援手）：原招只有治療（沒有護盾、增益）時改用的反應（受擊後補血）；
      其他輔助技用 ``reaction``（被瞄準時、命中判定之前）。
    - HC-4b3：``summon_duration`` 只有轉召喚時用到；用到時必填，其他可省略。HC-4c 刪掉沒有程式讀的
      ``scale_permille``（縮小起點的提示）。
    """

    id: str = Field(pattern=ID_PATTERN)
    to: TransformTarget
    source: Literal["hostile", "summon", "support"] = Field(
        default="hostile", exclude_if=lambda v: v == "hostile"
    )
    min_tier: int = Field(default=1, ge=1, le=3)
    prefix_zh: str = Field(min_length=1)
    summary_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用 ``summary_zh``。"""
    headline_zh: str | None = None
    """選變體畫面的白話大標（FL-1b，移植需求 8.2；玩法 PM 寫）；可帶 ``{n}``（模板的
    ``delta``）。省略時畫面退回 ``summary_zh``。依關鍵字而不同的見 :attr:`FlashTable.headlines`。"""
    say_zh: str | None = None
    """選中時下固定區的一句話（FL-1b 9.3）；可帶 ``{shape}``、``{cells}``、``{range}``、
    ``{n}`` 與術語標記 ``[[術語|字]]``。省略時由差異清單照句型組。"""
    trigger: TriggerSpec | None = None
    reaction: ReactionSpec | None = None
    heal_reaction: ReactionSpec | None = Field(default=None, exclude_if=lambda v: v is None)
    units: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """``summon``：技能元素（``any`` ＝ 沒有元素或沒列到時）→ 候選召喚物（依序試）。"""
    summon_duration: int | None = Field(default=None, ge=1, le=6)
    """``summon``：召喚物存在幾輪。"""
    summon_boosts: tuple[dict[str, int], ...] = ()
    """``summon``：角色階級高、預算變大時，依序加試的強化（``summon`` 效果的 ``duration``、
    ``max_hp_permille``、``count``、``power_permille``）；先試不強化的版本。"""
    trap: TrapSpec | None = None
    stances: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """``stance``：``offense``（原招有傷害）、``defense``（沒有傷害）→ 候選姿態狀態 ID（依序試，第一
    個落在預算窗內的）。原招有傷害時先試 :attr:`FlashTable.stance_ladders` 的同元素元素姿態。"""
    damage_permille_steps: tuple[int, ...] = ()
    """``modifier``：「傷害 +n‰」候選（由大到小，第一個落在預算窗內的）。"""
    draft_costs: tuple[dict[str, int], ...] = ()
    """新種類依序試的代價（HC-5a 從 ``skillgen/flash_major.py`` 搬來）：被動、反應、召喚、陷阱與
    TF-1 的四種轉型必填；姿態、修正型被動不填。法力、耐力是換算前的單位（程式乘
    ``quantity_scale``）。``{}`` ＝ 不花代價。"""
    draft_range: int | None = Field(default=None, ge=1, le=8)
    """新種類的射程（反應的單體目標、召喚與陷阱的指定格）；轉成反應、召喚、陷阱時必填，其他不填。"""
    draft_ap_cost: int | None = Field(default=None, ge=1, le=3)
    """新種類（主動技）的 AP；轉成召喚、陷阱時必填，其他不填。"""
    max_trap_effects: int | None = Field(default=None, ge=1, le=4)
    """轉成陷阱時，陷阱觸發的效果最多帶幾個（不含放置陷阱本身）；轉成陷阱時必填。"""
    stance_upkeeps: tuple[int, ...] = ()
    """轉成元素姿態時依序試的維持費（點數；先 1 點：隨階級變強的階梯在維持費 1 時對上預算窗）；
    轉成姿態時必填。"""

    @model_validator(mode="after")
    def _check(self) -> TransformTemplate:
        needs = {
            "passive": ("trigger", self.trigger is not None),
            "reaction": ("reaction", self.reaction is not None),
            "summon": ("units", bool(self.units)),
            "trap": ("trap", self.trap is not None),
            "stance": ("stances", bool(self.stances)),
            "modifier": ("damage_permille_steps", bool(self.damage_permille_steps)),
        }
        for kind, (field, present) in needs.items():
            if (self.to == kind) != present:
                raise ValueError(f"轉型 {self.id}：轉成 {kind} 時必須（且只有 {kind}）填 {field}")
        if self.source != "hostile" and self.to not in ("passive", "reaction"):
            raise ValueError(f"轉型 {self.id}：source: {self.source} 只能轉成被動或反應")
        if self.heal_reaction is not None and (self.source != "support" or self.to != "reaction"):
            raise ValueError(f"轉型 {self.id}：heal_reaction 只給輔助技轉反應（援手）用")
        if self.to == "summon" and self.summon_duration is None:
            raise ValueError(f"轉型 {self.id}：轉成 summon 時必須填 summon_duration")
        self._check_drafts()
        return self

    def _check_drafts(self) -> None:
        """HC-5a 的草稿欄位：用到時必填、用不到時不填。"""
        uses = {
            "draft_costs": (self.to not in ("stance", "modifier"), bool(self.draft_costs)),
            "draft_range": (
                self.to in ("reaction", "summon", "trap"),
                self.draft_range is not None,
            ),
            "draft_ap_cost": (self.to in ("summon", "trap"), self.draft_ap_cost is not None),
            "max_trap_effects": (self.to == "trap", self.max_trap_effects is not None),
            "stance_upkeeps": (self.to == "stance", bool(self.stance_upkeeps)),
        }
        bad = sorted({k for cost in self.draft_costs for k in cost} - set(DRAFT_COST_FIELDS))
        if bad:
            raise ValueError(f"轉型 {self.id}：draft_costs 只能寫 {'、'.join(DRAFT_COST_FIELDS)}")
        for field, (needed, present) in uses.items():
            if needed and not present:
                raise ValueError(f"轉型 {self.id}：轉成 {self.to} 時必須填 {field}")
            if present and not needed:
                raise ValueError(f"轉型 {self.id}：轉成 {self.to} 時不用填 {field}")


class ExtraMajorTemplate(ContentModel):
    """大變化的補充模板（3W-3）：進化模板做不出來的輔助技、召喚技能用的加深與橋接。

    ``op`` 的實作在 :mod:`trpg.skillgen.flash_major`；``only`` 是適用的對象。
    """

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    op: str = Field(pattern=ID_PATTERN)
    only: Literal["support", "summon", "shield", "borrow"]
    """適用對象：輔助技（治療、護盾、增益）、召喚技能、護盾類（有護盾效果，3W-2b）或預支技能（帶
    ``borrow_ap``，AP-2；預支技能只出這一類）。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    """``only: shield`` 的加深／橋接：護盾改用的狀態（``statuses.yaml`` 的 ``shielded_*``）。"""
    keyword: str | None = Field(default=None, pattern=ID_PATTERN)
    """``only: shield`` 的橋接：這個模板橋接到的關鍵字（持有者持有越多越優先）。"""
    needs_held: bool = False
    """``only: shield`` 的橋接：true ＝ 持有者必須持有 ``keyword`` 才會出現（3W-2c，帶電）。"""
    amount: int | None = Field(default=None, ge=1, le=2)
    """``only: borrow``（AP-2）：預支改成幾 AP。"""
    uses: int | None = Field(default=None, ge=1)
    """``only: borrow``（AP-2）：每場可以用幾次。"""
    prefix_zh: str = Field(min_length=1)
    summary_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用 ``summary_zh``。"""
    headline_zh: str | None = None
    """選變體畫面的白話大標（FL-1b，移植需求 8.2；玩法 PM 寫）；可帶 ``{n}``（模板的
    ``delta``）。省略時畫面退回 ``summary_zh``。依關鍵字而不同的見 :attr:`FlashTable.headlines`。"""
    say_zh: str | None = None
    """選中時下固定區的一句話（FL-1b 9.3）；可帶 ``{shape}``、``{cells}``、``{range}``、
    ``{n}`` 與術語標記 ``[[術語|字]]``。省略時由差異清單照句型組。"""

    @model_validator(mode="after")
    def _check(self) -> ExtraMajorTemplate:
        if self.only == "borrow" and (self.amount is None or self.uses is None):
            raise ValueError(f"大變化補充模板 {self.id}：only: borrow 必須填 amount 與 uses")
        return self


class FlashHeadline(ContentModel):
    """「模板 × 關鍵字」的大標與說明句（FL-1b，移植需求 8.2）：依關鍵字（或第二元素）而不同的模板
    （``keyword_imbue``、``keyword_exploit``、``element_second``…）。表裡沒有的組合退回模板自己的
    ``headline_zh``／``say_zh``，再沒有就退回 ``summary_zh``。不用 LLM。"""

    template: str = Field(pattern=ID_PATTERN)
    keyword: str = Field(pattern=ID_PATTERN)
    """變化帶的關鍵字（``Variation.keyword``）或元素（``Variation.element``）。"""
    headline_zh: str | None = None
    say_zh: str | None = None


class FlashTerm(ContentModel):
    """選變體畫面的說明卡（FL-1b，移植需求 6、9.2；「介面用詞」）。

    ``text_zh`` 可帶資料填的變數（``{ap_per_turn}``、``{ap_carry_max}``、``{water_rounds}``、
    ``{wet_heal_percent}``；武器傷害另有 ``{dice}``、``{attrs}``、``{times}``、``{bonus}``），
    數字不寫死。狀態、關鍵字、形狀照內容原句（``status:<id>``、``kw:<id>``、``shape:<id>``
    讀各自的 ``description_zh``），這裡有同 ID 的優先。"""

    id: str = Field(min_length=1)
    title_zh: str = Field(min_length=1)
    text_zh: str = Field(min_length=1)


class VariantPlace(ContentModel):
    """戰場變奏的一個條件寫成白話（TXT-2）：``condition`` 是 ``skill_composer.yaml`` 的
    ``variant.conditions`` ID；``where_zh`` 是動作片語（「站在水中」，不帶主詞）；``subject`` 是
    條件看誰的地形（``caster``：施放者，``target``：目標點），決定用哪一個句型。"""

    condition: str = Field(pattern=ID_PATTERN)
    where_zh: str = Field(min_length=1)
    subject: Literal["caster", "target"]


class BattleVariantText(ContentModel):
    """戰場變奏（``major_battle_variant``）選項的說明句（TXT-2，玩法 PM 11-13 定稿；原寫死在
    ``api/flash_text.py``）。

    模板的 ``say_zh`` 帶 ``{terrain}`` 時：條件查得到 → 依 ``subject`` 換成 ``caster_say_zh``／
    ``target_say_zh``，``{terrain}`` 填 ``where_zh``；查不到 → 照模板的句子、``{terrain}`` 填
    ``somewhere_zh``。"""

    caster_say_zh: str = Field(min_length=1)
    target_say_zh: str = Field(min_length=1)
    somewhere_zh: str = Field(min_length=1)
    places: tuple[VariantPlace, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> BattleVariantText:
        for name in ("caster_say_zh", "target_say_zh"):
            if "{terrain}" not in getattr(self, name):
                raise ValueError(f"戰場變奏說明句 {name} 必須帶 {{terrain}}")
        dup = sorted(k for k, n in Counter(p.condition for p in self.places).items() if n > 1)
        if dup:
            raise ValueError(f"戰場變奏條件重複：{', '.join(dup)}")
        return self

    def place(self, condition_id: str) -> VariantPlace | None:
        return next((p for p in self.places if p.condition == condition_id), None)

    def say(self, place: VariantPlace) -> str:
        return self.caster_say_zh if place.subject == "caster" else self.target_say_zh


class SupportSkillRule(ContentModel):
    """「輔助技」的判定（「輔助」類 ``support_only`` 用；3W-R2 從程式移到資料）：沒有
    ``harm_effects``，而且有 ``help_effects``，或有作用於友方（``affects: allies``）的
    ``ally_effects``。見 :func:`trpg.skillgen.flash_category.is_support_skill`。"""

    harm_effects: tuple[str, ...] = ("damage", "delayed_damage")
    help_effects: tuple[str, ...] = ("heal", "shield")
    ally_effects: tuple[str, ...] = ("heal", "shield", "apply_status", "cleanse", "grant_ap")


class FlashTable(ContentModel):
    """``content/flash_templates.yaml``。HC-4b3 起 ``rules``、``pricing`` 必填（數字都寫在
    檔裡）。"""

    rules: FlashRules
    pricing: FlashPricing
    categories: tuple[FlashCategory, ...] = ()
    minor: tuple[FlashTemplate, ...] = ()
    major: tuple[MajorFlashTemplate, ...] = ()
    extra_major: tuple[ExtraMajorTemplate, ...] = ()
    transforms: tuple[TransformTemplate, ...] = ()
    support: SupportSkillRule = SupportSkillRule()
    """輔助技的判定（``support_only`` 類別用）。"""
    headlines: tuple[FlashHeadline, ...] = ()
    """「模板 × 關鍵字」的大標（FL-1b）。"""
    terms: tuple[FlashTerm, ...] = ()
    """選變體畫面的說明卡（FL-1b）。"""
    condition_zh: dict[str, str] = Field(default_factory=dict)
    """新加的條件傷害「（……才有）」的白話（FL-1b；條件 ID → 句子，可帶術語標記）；沒有的退回條件的
    一句話。"""
    battle_variant: BattleVariantText | None = None
    """戰場變奏的說明句與條件片語（TXT-2）；``None`` 時 ``{terrain}`` 原樣留著
    （內容漏寫看得出來）。"""
    intensify_new_headline_zh: str | None = None
    """``major_intensify`` 原本不會造成該關鍵字、引擎補上製造效果時的大標（TXT-2 從
    ``api/flash_text.py`` 搬來；可帶 ``{keyword}``）；``None`` 時照模板的 ``headline_zh``。"""
    stance_ladders: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """元素姿態的階梯（3W-2b）：元素 ID（``physical`` 也有）→ 由弱到強的姿態狀態 ID。轉型優先
    轉成同元素的姿態；姿態的「費用」「修正」類小變化在同一階梯上換級（維持費 ±1 搭配效果升降）。"""

    @model_validator(mode="after")
    def _check(self) -> FlashTable:
        ids = [c.id for c in self.categories]
        templates = [t.id for t in self.minor]
        templates += [t.id for t in self.major]
        templates += [t.id for t in self.extra_major]
        templates += [t.id for t in self.transforms]
        for label, values in (("類別", ids), ("模板", templates)):
            dup = sorted(k for k, n in Counter(values).items() if n > 1)
            if dup:
                raise ValueError(f"{label} ID 重複：{', '.join(dup)}")
        stages = {c.id: c.stage for c in self.categories}
        for template in self.minor:
            if stages.get(template.category) != "minor":
                raise ValueError(
                    f"小變化模板 {template.id} 的類別 {template.category} 不是小變化類別"
                )
        for major in self.major:
            if stages.get(major.category) != "major":
                raise ValueError(f"大變化模板 {major.id} 的類別 {major.category} 不是大變化類別")
        for extra in self.extra_major:
            if stages.get(extra.category) != "major":
                raise ValueError(
                    f"大變化補充模板 {extra.id} 的類別 {extra.category} 不是大變化類別"
                )
        known = set(templates)
        for line in self.headlines:
            if line.template not in known:
                raise ValueError(f"大標 {line.template}×{line.keyword}：未知的模板")
        pairs = [(h.template, h.keyword) for h in self.headlines]
        dup = sorted(f"{t}×{k}" for (t, k), n in Counter(pairs).items() if n > 1)
        dup += sorted(k for k, n in Counter(t.id for t in self.terms).items() if n > 1)
        if dup:
            raise ValueError(f"大標或說明卡重複：{', '.join(dup)}")
        return self

    def category(self, category_id: str) -> FlashCategory:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(f"未知的閃現類別：{category_id}")

    def stage_categories(self, stage: Literal["minor", "major"]) -> tuple[FlashCategory, ...]:
        return tuple(c for c in self.categories if c.stage == stage)

    def minor_template(self, template_id: str) -> FlashTemplate | None:
        return next((t for t in self.minor if t.id == template_id), None)

    def major_template(self, template_id: str) -> MajorFlashTemplate | None:
        return next((t for t in self.major if t.id == template_id), None)

    def extra_template(self, template_id: str) -> ExtraMajorTemplate | None:
        return next((t for t in self.extra_major if t.id == template_id), None)

    def stance_rung(self, status_id: str) -> tuple[tuple[str, ...], int] | None:
        """``status_id`` 所在的元素姿態階梯與它的位置；不在任何階梯上時 ``None``。"""
        for ladder in self.stance_ladders.values():
            if status_id in ladder:
                return ladder, ladder.index(status_id)
        return None

    def transform_template(self, template_id: str) -> TransformTemplate | None:
        return next((t for t in self.transforms if t.id == template_id), None)

    def headline(self, template_id: str, keyword: str | None) -> FlashHeadline | None:
        """「模板 × 關鍵字」表的一列（FL-1b）；沒有時 ``None``。"""
        if keyword is None:
            return None
        return next(
            (h for h in self.headlines if h.template == template_id and h.keyword == keyword),
            None,
        )

    def term(self, term_id: str) -> FlashTerm | None:
        return next((t for t in self.terms if t.id == term_id), None)
