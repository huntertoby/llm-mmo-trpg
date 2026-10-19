"""規則數值（``content/rules/core.yaml``）與命中修正對照表（``content/rules/hit_table.yaml``）。

命中修正（``docs/phases/Phase1計畫.md`` 4.3）::

    命中修正 = clamp(round(slope × log2(攻擊值 ÷ 防禦值)), −cap, +cap)

執行期不得使用浮點數 ``log2``。改用整數比較：對每個修正值 ``k``（``−cap+1 … cap``），
``修正 ≥ k`` 等價於 ``攻擊值 ÷ 防禦值 ≥ 2^((k − 0.5) / slope)``。門檻
``t_k = 2^((2k − 1) / (2·slope))`` 以 ``scale``（10⁶）放大後 **無條件進位** 存成整數，
執行期以 ``攻擊值 × scale ≥ 防禦值 × T_k`` 判斷。進位讓整數判斷永遠不會給出比真實值更高的修正
（只有比例落在門檻上方不到 10⁻⁶ 相對誤差的極窄區間時會低 1）。

:func:`compute_hit_thresholds` 以 :mod:`decimal` 高精度計算，``scripts/gen_hit_table.py`` 用它
產生資料檔；測試另以 :class:`fractions.Fraction` 做完全精確的驗證。
"""

from __future__ import annotations

import itertools
from decimal import ROUND_CEILING, Decimal, localcontext
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import Dice
from trpg.content.schemas import ContentModel

__all__ = [
    "HIT_TABLE_SCALE",
    "CoreRules",
    "HitTable",
    "HitThreshold",
    "SkillSlots",
    "compute_hit_thresholds",
]

HIT_TABLE_SCALE = 1_000_000
"""門檻比例的放大倍數（10⁶）。"""

_DECIMAL_PRECISION = 60


class SkillSlots(ContentModel):
    """戰鬥時可裝備的技能欄位上限（依技能 ``kind``，``docs/design/06-技能.md`` 6.13）。"""

    active: int = Field(ge=0)
    passive: int = Field(ge=0)
    reaction: int = Field(ge=0)
    stance: int = Field(ge=0)


class CoreRules(ContentModel):
    """``content/rules/core.yaml``：所有可調整的戰鬥規則數值。

    百分比一律以整數千分比（‰）表示，欄位名稱以 ``_permille`` 結尾。
    """

    # 行動經濟
    ap_per_turn: int = Field(ge=0)
    ap_carry_max: int = Field(ge=0)
    basic_attack_ap_cost: int = Field(ge=0)
    defend_ap_cost: int = Field(ge=0)

    # 判定
    hit_target: int = Field(ge=1)
    hit_slope: int = Field(ge=1)
    hit_mod_cap: int = Field(ge=1)
    proficiency: int
    height_hit_bonus: int = Field(ge=0)
    melee_height_limit: int = Field(ge=0)
    melee_height_limit_max_range: int = Field(ge=1)
    initiative_attr_base: int
    initiative_attr_divisor: int = Field(ge=1)

    # 傷害
    basic_attack_attr_multiplier_permille: int = Field(ge=0)
    element_mod_floor_permille: int = Field(ge=0, le=1000)
    min_damage_on_hit: int = Field(ge=0)
    defend_defense_bonus_permille: int = Field(ge=0)

    # 移動與環境
    move_climb_extra_cost: int = Field(ge=0)
    max_climb_height: int = Field(ge=0, le=3)
    fall_damage_min_drop: int = Field(ge=1)
    fall_damage_permille_per_level: int = Field(ge=0)
    fall_damage_cap_permille: int = Field(ge=0, le=1000)
    deadly_terrain_elite_permille: int = Field(ge=0, le=1000)
    prone_stand_up_move_permille: int = Field(ge=0, le=1000)

    # 技巧動作與互動（1B）
    maneuver_ap_cost: int = Field(ge=0)
    interact_ap_cost: int = Field(ge=0)
    interact_height_limit: int = Field(ge=0)
    shove_distance: int = Field(ge=0)
    max_displace_distance: int = Field(default=2, ge=1)
    """推擊與拉扯的距離上限（6.6）：修正規則加長距離時截斷在這裡（Phase 3C-2；舊紀錄沒有
    此欄位）。"""
    collision_damage_dice: Dice = Field(default_factory=lambda: Dice(count=1, sides=6))
    """撞擊傷害（Phase 3C-3a）：被強制位移的單位因障礙提前停下時，每少走 1 格受一次，物理、不加
    屬性；技能的 ``collision_dice`` 可取代。舊紀錄沒有此欄位。"""
    consume_status_max_scale: int = Field(default=3, ge=1)
    """``consume_status`` 的 ``scale`` 倍率上限（Phase 3C-3b；舊紀錄沒有此欄位）。"""
    topple_length: int = Field(default=2, ge=1, le=4)
    """推倒（Phase 3C-5a）：``topplable`` 物件倒下時，從物件的下一格起壓住的格數。"""
    topple_damage_dice: Dice = Field(default_factory=lambda: Dice(count=2, sides=6))
    """推倒壓到的單位（與 ``breakable`` 物件）受到的物理傷害（Phase 3C-5a）。"""
    topple_rubble_object: str = Field(default="rubble", pattern=r"^[a-z][a-z0-9_]*$")
    """推倒後產生的物件（``objects.yaml`` 的 ID；Phase 3C-5a）。"""
    hurl_scatter_radius: int = Field(default=1, ge=0, le=2)
    """投擲物件（Phase 3C-5a）：落點有單位或物件時，物件放在這個曼哈頓距離內最近的空格；
    沒有空格就摧毀。"""
    pierce_behind_permille: int = Field(default=700, ge=1, le=1000)
    """穿透（Phase 3C-5b）：穿過 ``penetrable`` 物件之後，後方目標受到的傷害（‰；物件本身受全額
    傷害）。舊紀錄沒有此欄位。"""
    steadfast_push_permille: int = Field(ge=0, le=1000)
    ability_mod_base: int
    ability_mod_divisor: int = Field(ge=1)

    # 反應（1B）
    reactions_per_round: int = Field(ge=0)
    default_stamina: int = Field(ge=0)

    # 視線與隱蔽（1B）
    base_sight_range: int = Field(ge=1)
    concealed_ranged_max_distance: int = Field(ge=0)

    # 掩護（1C）
    half_cover_hit_penalty: int = Field(ge=0)

    # 環境回合（1B）
    burning_object_rounds: int = Field(ge=1)

    # 技能（2A）
    spell_attr_multiplier_permille: int = Field(ge=0)
    dual_scaling_min_rarity: Literal["common", "rare", "epic", "legendary"] = "epic"
    """雙屬性縮放（``secondary_scaling_attr``，Phase 2H-2）的最低技能稀有度。"""
    skill_slots: SkillSlots

    # 狀態與控制（2B-1）
    control_dr_rounds: int = Field(ge=0)
    control_dr_resist_permille: int = Field(ge=1000, le=10000)
    boss_control_conversion: dict[str, str]
    """帶 ``boss`` 標籤的單位被施加 ``control_group: hard`` 的狀態時，改為施加對照表中的狀態。"""

    # 技能預算（2B-2）
    tier_budget: dict[int, int]
    """各階級（1–5）的基礎預算點數，必須嚴格遞增。"""
    budget_reference_weapon_damage: int = Field(ge=1)
    """武器技的預算基準：倍率 100% ＝ 這麼多點。"""

    # 效果佇列
    max_chain_depth: int = Field(ge=0)

    # 技能觸發（2E-1）
    max_trigger_depth: int = Field(default=3, ge=0)
    """技能觸發的連鎖深度上限：動作本身為 0，由觸發產生的觸發深度 +1，超過上限不結算。"""

    # 姿態（2E-2）
    stance_ap_cost: int = Field(default=1, ge=0)
    """進入姿態（``kind: stance``）花的 AP；取消姿態（``EndStance``）免費。"""

    # 源力（3C-4a）
    source_max: int = Field(default=3, ge=0)
    """單位持有源力的上限（Phase 3C-4a；舊紀錄沒有此欄位）。"""
    source_min_at_start: int = Field(default=1, ge=0)
    """我方單位每場戰鬥開場至少有這麼多源力（敵人一律 0）。"""

    @model_validator(mode="after")
    def _check_source(self) -> CoreRules:
        if self.source_min_at_start > self.source_max:
            raise ValueError("source_min_at_start 不可大於 source_max")
        return self

    @model_validator(mode="after")
    def _check_tier_budget(self) -> CoreRules:
        if sorted(self.tier_budget) != [1, 2, 3, 4, 5]:
            raise ValueError("tier_budget 必須剛好有階級 1 到 5")
        values = [self.tier_budget[t] for t in range(1, 6)]
        if any(a >= b for a, b in itertools.pairwise(values)) or values[0] < 1:
            raise ValueError(f"tier_budget 必須是隨階級嚴格遞增的正整數，收到 {values}")
        return self

    def summary(self) -> str:
        return f"每回合 {self.ap_per_turn} AP、命中門檻 {self.hit_target}"


class HitThreshold(ContentModel):
    """修正值 ``mod`` 的門檻。

    ``攻擊值 × scale ≥ 防禦值 × min_ratio_scaled`` 時修正至少為 ``mod``。
    """

    mod: int
    min_ratio_scaled: int = Field(ge=1)


class HitTable(ContentModel):
    """``content/rules/hit_table.yaml``（由 ``scripts/gen_hit_table.py`` 產生，請勿手改）。"""

    slope: int = Field(ge=1)
    cap: int = Field(ge=1)
    scale: int = Field(ge=1)
    thresholds: tuple[HitThreshold, ...]

    @model_validator(mode="after")
    def _check_shape(self) -> HitTable:
        mods = [t.mod for t in self.thresholds]
        expected = list(range(-self.cap + 1, self.cap + 1))
        if mods != expected:
            raise ValueError(f"thresholds 的 mod 必須依序為 {expected[0]}…{expected[-1]}")
        ratios = [t.min_ratio_scaled for t in self.thresholds]
        if any(a >= b for a, b in itertools.pairwise(ratios)):
            raise ValueError("thresholds 的 min_ratio_scaled 必須嚴格遞增")
        return self

    def modifier(self, attack_num: int, defense_num: int) -> int:
        """以整數比較求命中修正。

        ``attack_num ÷ defense_num`` 即攻擊值 ÷ 防禦值（呼叫端可把兩者同乘一個分母以表示分數，
        例如防禦姿態的 +25%）。``attack_num <= 0`` 時回傳 ``−cap``。
        """
        if defense_num <= 0:
            raise ValueError(f"防禦值必須 > 0，收到 {defense_num}")
        if attack_num <= 0:
            return -self.cap
        lhs = attack_num * self.scale
        for threshold in reversed(self.thresholds):
            if lhs >= defense_num * threshold.min_ratio_scaled:
                return threshold.mod
        return -self.cap

    def summary(self) -> str:
        return f"斜率 {self.slope}、上下限 ±{self.cap}，{len(self.thresholds)} 個門檻"


def compute_hit_thresholds(
    slope: int, cap: int, scale: int = HIT_TABLE_SCALE
) -> tuple[HitThreshold, ...]:
    """以高精度十進位計算 ``ceil(2^((2k − 1) / (2·slope)) × scale)``，``k = −cap+1 … cap``。"""
    if slope < 1 or cap < 1 or scale < 1:
        raise ValueError("slope、cap、scale 都必須 >= 1")
    result: list[HitThreshold] = []
    with localcontext() as ctx:
        ctx.prec = _DECIMAL_PRECISION
        ln2 = Decimal(2).ln()
        for k in range(-cap + 1, cap + 1):
            exponent = Decimal(2 * k - 1) / Decimal(2 * slope)
            value = (exponent * ln2).exp() * scale
            scaled = int(value.to_integral_value(rounding=ROUND_CEILING))
            result.append(HitThreshold(mod=k, min_ratio_scaled=scaled))
    return tuple(result)
