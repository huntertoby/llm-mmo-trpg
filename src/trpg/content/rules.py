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

from trpg.content.battle import Dice, UnitTemplate
from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute, Element, Surface

__all__ = [
    "HIT_TABLE_SCALE",
    "CoreRules",
    "HitTable",
    "HitThreshold",
    "SkillSlots",
    "SummonGrowth",
    "SummonInfusion",
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


class SummonGrowth(ContentModel):
    """召喚物數值成長（Phase 3-33b，``docs/design/06-技能.md`` 6.29.1；初值，未經模擬）。

    召喚當下依施放者的等級 ``L`` 與縮放屬性修正 ``M``（``(屬性 − ability_mod_base) ÷
    ability_mod_divisor``，下限 0）快照：最大 HP ＋ ``hp_per_level × (L−1) + hp_per_attr_mod × M``；
    普攻固定傷害 ＋ ``(flat_per_level_permille × (L−1) + flat_per_attr_mod_permille × M) ÷ 1000``
    （無條件捨去）；傷害加成（‰）＝ ``bonus_per_level_permille × (L−1) +
    bonus_per_attr_mod_permille × M``，與施放者自己的傷害加成合計套全身上限。"""

    hp_per_level: int = Field(default=2, ge=0, le=20)
    hp_per_attr_mod: int = Field(default=1, ge=0, le=20)
    flat_per_level_permille: int = Field(default=250, ge=0, le=5000)
    flat_per_attr_mod_permille: int = Field(default=250, ge=0, le=5000)
    bonus_per_level_permille: int = Field(default=10, ge=0, le=200)
    bonus_per_attr_mod_permille: int = Field(default=10, ge=0, le=200)


class SummonInfusion(ContentModel):
    """灌注關鍵字的效果（Phase 3-33b，3-33e1 補齊到 10 個）。``roles`` 是 AI 偏好的召喚物定位
    （``melee`` 近戰、``ranged`` 遠程）。

    普攻命中後附加：``status``（持續 ``duration`` 回合）、``knockback``（震退）、
    ``surface``（在目標格造表面）、``extra_damage``（另加一擊 ``extra_element`` 元素的傷害）、
    ``trip``（對抗判定絆倒，每隻
    召喚物每輪 1 次）。傷害：``height_permille``（站得比目標高時普攻傷害 ＋‰）。召喚時：
    ``conceal_rounds``（獲得隱蔽幾回合）、``hp_permille``（最大 HP ＋‰）。"""

    status: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    duration: int = Field(default=2, ge=1, le=6)
    knockback: int = Field(default=0, ge=0, le=2)
    surface: Surface | None = None
    extra_damage: Dice | None = None
    extra_element: Element = Element.PHYSICAL
    trip: bool = False
    height_permille: int = Field(default=0, ge=0, le=1000)
    conceal_rounds: int = Field(default=0, ge=0, le=4)
    hp_permille: int = Field(default=0, ge=0, le=1000)
    roles: tuple[Literal["melee", "ranged"], ...] = ()

    @model_validator(mode="after")
    def _has_effect(self) -> SummonInfusion:
        if not (
            self.status is not None
            or self.knockback
            or self.surface is not None
            or self.extra_damage is not None
            or self.trip
            or self.height_permille
            or self.conceal_rounds
            or self.hp_permille
        ):
            raise ValueError("灌注關鍵字至少要有一項效果")
        return self


class CoreRules(ContentModel):
    """``content/rules/core.yaml``：所有可調整的戰鬥規則數值。

    百分比一律以整數千分比（‰）表示，欄位名稱以 ``_permille`` 結尾。
    """

    # 行動經濟
    ap_per_turn: int = Field(ge=0)
    ap_carry_max: int = Field(ge=0)
    basic_attack_ap_cost: int = Field(ge=0)
    defend_ap_cost: int = Field(ge=0)
    run_ap_cost: int = Field(ge=0)
    """跑步（Phase 3-20，玩法 #22）消耗的 AP。"""
    run_move_bonus: int = Field(ge=0)
    """跑步：本回合移動點數增加的固定格數（不受加速、緩速倍率影響；平衡階段初值）。"""
    swap_ap_cost: int = Field(ge=0)
    """換位（Phase 3-21a，玩法 #24）消耗的 AP。"""
    aim_ap_cost: int = Field(ge=0)
    """瞄準（Phase 3-21a）消耗的 AP。"""
    aim_hit_bonus: int = Field(ge=0)
    """瞄準：下一次需要擲命中的攻擊的命中加值（不疊加；平衡階段初值）。"""
    vault_ap_cost: int = Field(ge=0)
    """攀跳（Phase 3-21b，玩法 #24）消耗的 AP。"""
    vault_move_cost: int = Field(ge=0)
    """攀跳另外消耗的移動點數（平衡階段初值）。"""
    vault_climb_height: int = Field(ge=1, le=4)
    """攀爬：可爬上的相鄰格高度差上限（要大於 ``max_climb_height`` 才有意義；平衡階段初值）。"""
    vault_jump_width: int = Field(ge=1, le=3)
    """跳躍：最多越過幾格連續的不可站立格（深淵、岩漿；初值 1 格寬）。"""
    guard_transfers_per_round: int = Field(ge=0)
    """守護隊友：守護者每輪最多替隊友承受單體攻擊的次數（平衡階段初值）。"""

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

    # 衍生數值：最大 HP ＝ 範本基礎 HP ＋（體質 − hp_con_base）× hp_per_con_point（至少 1）；
    # roguelite 每升一級再加 基礎 HP × level_hp_permille ‰（Phase 3-7，初值）
    hp_con_base: int = Field(ge=0)
    hp_per_con_point: int = Field(ge=0)
    level_hp_permille: int = Field(ge=0)

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
    teleport_enemy_resist_bonus: int = Field(default=2, ge=0, le=10)
    """傳送他人（Phase 3D-2b ``teleport_target``）：敵方目標的抵抗加成（從對抗判定的 d20 總和扣除；
    同級時成功率 60% → 50%）。"""
    teleport_lethal_resist_bonus: int = Field(default=8, ge=0, le=20)
    """傳送到致命地形時，目標再加的抵抗加成（與 ``teleport_enemy_resist_bonus`` 相加；同級時
    總 +10，d20 自然 19 與 20 才成功，成功率 10%）。"""
    pierce_behind_permille: int = Field(default=700, ge=1, le=1000)
    """穿透（Phase 3C-5b）：穿過 ``penetrable`` 物件之後，後方目標受到的傷害（‰；物件本身受全額
    傷害）。舊紀錄沒有此欄位。"""
    explode_max: int = Field(default=2, ge=1, le=5)
    """爆骰（``explode: true``，Phase 3D-7b）：每顆骰最多再擲的次數。舊紀錄沒有此欄位。"""
    scale_cap_max_permille: int = Field(default=800, ge=1, le=5000)
    """依情況縮放（``scaling``，Phase 3D-7b）：``cap_permille`` 的上限（‰）。舊紀錄沒有此欄位。"""
    backstab_hit_bonus: int = Field(default=2, ge=0, le=10)
    """背刺（Phase 3D-8d）：近戰攻擊者站在目標的背後格時的命中加值。舊紀錄沒有此欄位。"""
    backstab_crit_range_bonus: int = Field(default=1, ge=0, le=5)
    """背刺（Phase 3D-8d）：暴擊範圍擴大的格數（1 ＝ 武器 20 → 19–20）。"""
    ambush_hit_bonus: int = Field(default=2, ge=0, le=10)
    """潛行偷襲（Phase 3D-8d）：攻擊者帶 ``concealed`` 狀態時的命中加值（攻擊結算完後移除隱蔽）。"""
    revive_landing_radius: int = Field(default=2, ge=0, le=6)
    """復活（``revive``，Phase 3D-8b）：原格被占用或不能站立時，站到這個距離（曼哈頓）內最近的空格；
    範圍內沒有空格就不能施放。舊紀錄沒有此欄位。"""
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
    variant_max_by_rarity: dict[str, int] = Field(
        default_factory=lambda: {"common": 0, "rare": 1, "epic": 2, "legendary": 2}
    )
    """各稀有度最多可帶的戰場變奏數（Phase 3-25a，6.24；PM 決定 #7）。沒列的稀有度為 0。"""
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

    # 召喚（3D-4a）
    summon_limit_per_owner: int = Field(default=2, ge=1, le=6)
    """同一召喚者同時存在的召喚物上限（Phase 3D-4a）；超過時最舊的消失。"""
    summon_hard_cap: int = Field(default=3, ge=1, le=6)
    """召喚物同時存在的硬上限（Phase 3-33b）：之後專精可提高上限，但不得超過這個值。"""
    summon_max_duration: int = Field(default=4, ge=1, le=10)
    """召喚物持續輪數的上限（Phase 3-33b）：召喚技能的 ``duration`` 超過時以此為準。"""
    boss_summon_damage_permille: int = Field(default=2000, ge=1000, le=5000)
    """Boss（``boss`` 標籤）對召喚物造成的傷害倍率（‰；Phase 3-33b，預設 ×2）。"""
    summon_command_ap_cost: int = Field(default=1, ge=0, le=3)
    """指揮召喚物（Phase 3-33c）的 AP 花費（切換模式免費）。"""
    summon_growth: SummonGrowth = Field(default_factory=SummonGrowth)
    """召喚物 HP 與傷害的成長（Phase 3-33b）。"""
    summon_infusions: dict[str, SummonInfusion] = Field(default_factory=dict)
    """灌注關鍵字對照（Phase 3-33b）：關鍵字 ID → 召喚物普攻附加效果；不在表中的關鍵字不可灌注。"""

    # 持續區域（3D-5）
    zone_limit_per_owner: int = Field(default=2, ge=1, le=6)
    """同一施放者同時存在的區域上限（Phase 3D-5）；超過時最舊的消失。"""

    # 刻印（3-23）
    rune_limit_per_owner: int = Field(default=6, ge=1, le=12)
    """同一施放者同時存在的符文格上限（Phase 3-23）；超過時最舊的消失。"""
    rune_default_rounds: int = Field(default=3, ge=1, le=6)
    """``inscribe`` 省略 ``duration`` 時符文的持續環境回合數（Phase 3-23）。"""
    rune_max_rounds: int = Field(default=5, ge=1, le=10)
    """``inscribe`` 的 ``duration`` 上限（Phase 3-23）。"""

    # 常駐類傳說的啟動（3D-6）
    legendary_activation_ap: int = Field(default=1, ge=1, le=3)
    """啟動常駐類傳說（修正型與規則改變型，``activation``）花的 AP（Phase 3D-6）。"""
    legendary_timed_rounds: int = Field(default=3, ge=1, le=10)
    """``activation: timed`` 的持續輪數（Phase 3D-6；初值，以模擬調整）：啟動後在持有者第
    ``N`` 次之後的回合開始時結束（也就是持有者連同啟動的那一回合共有 ``N`` 個回合）。"""

    @model_validator(mode="after")
    def _check_summon_cap(self) -> CoreRules:
        if self.summon_limit_per_owner > self.summon_hard_cap:
            raise ValueError("summon_limit_per_owner 不可大於 summon_hard_cap")
        return self

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

    def max_hp_for(self, base_hp: int, con: int) -> int:
        """最大 HP ＝ 基礎 HP ＋（體質 − ``hp_con_base``）× ``hp_per_con_point``（至少 1）。"""
        return max(1, base_hp + (con - self.hp_con_base) * self.hp_per_con_point)

    def template_max_hp(self, template: UnitTemplate) -> int:
        """範本建立出的單位的最大 HP（引擎對敵我所有單位用同一公式）。"""
        return self.max_hp_for(template.max_hp, template.attributes[Attribute.CON])

    def run_max_hp(self, base_hp: int, con: int, level: int) -> int:
        """roguelite 主角的最大 HP：``max_hp_for(基礎 HP ＋ 等級加成, 體質)``。戰鬥中的主角單位
        用同一個式子（等級加成併入範本的基礎 HP，再由引擎加體質），所以兩邊永遠一致。"""
        return self.max_hp_for(base_hp + self.level_hp_bonus(base_hp, level), con)

    def level_hp_bonus(self, base_hp: int, level: int) -> int:
        """roguelite 升級的最大 HP 加成：基礎 HP × ``level_hp_permille``‰ ×（等級−1），向下取整。"""
        return base_hp * self.level_hp_permille * max(0, level - 1) // 1000

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
