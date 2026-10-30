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
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal, localcontext
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import SUMMON_ROLES, Dice, UnitTemplate
from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute, Element, Surface

__all__ = [
    "HIT_TABLE_SCALE",
    "AttributePerk",
    "AttributePerks",
    "CoreRules",
    "HitTable",
    "HitThreshold",
    "PerkKind",
    "PerkLine",
    "ResourceKind",
    "ResourcePool",
    "ResourceRules",
    "SkillSlots",
    "SummonGrowth",
    "SummonInfusion",
    "SummonTrait",
    "WindRules",
    "compute_hit_thresholds",
]

HIT_TABLE_SCALE = 1_000_000
"""門檻比例的放大倍數（10⁶）。"""

_DECIMAL_PRECISION = 60
_PERMILLE = 1000


PerkKind = Literal[
    "collision_dealt",
    "collision_taken",
    "surface_duration",
    "reaction_hit",
    "reveal_range",
    "control_resist",
]
"""常駐數值的種類（Phase 3H-1）；每一種由引擎的一個結算點讀取（見 :class:`AttributePerks`）。"""


class AttributePerk(ContentModel):
    """一條屬性常駐數值：``attr`` 每升一階，``kind`` 的效果加 ``per_tier``。

    ``text_zh`` 是面板說明，``{n}`` 換成「每階數值」（面板另外寫出目前階數與總和）。"""

    attr: Attribute
    kind: PerkKind
    per_tier: int = Field(ge=1)
    text_zh: str = Field(min_length=1)


@dataclass(frozen=True)
class PerkLine:
    """面板上的一行常駐數值：``now_zh`` 是目前階數的總效果（0 階為 ``None``）；``next_at`` 是
    下一階需要的屬性值。"""

    attr: Attribute
    kind: PerkKind
    tier: int
    per_tier_zh: str
    now_zh: str | None
    next_at: int


ResourceKind = Literal["mana", "stamina"]
"""可依屬性決定上限的資源（Phase 3H-2）：法力（法術技）與耐力（武器技、格擋）。"""


class ResourcePool(ContentModel):
    """一種資源的上限加成：``attrs`` 裡最高的屬性每高於基準 1 點，上限 + ``per_point``。"""

    attrs: tuple[Attribute, ...] = Field(min_length=1)
    per_point: int = Field(ge=0)


class ResourceRules(ContentModel):
    """法力與耐力上限（Phase 3H-2，``docs/design/07-角色成長.md`` 7.2；初值，平衡待辦）::

        上限 ＝ 基礎 ＋（attrs 最高者 − base）× per_point（至少 0）

    基礎是範本的 ``max_mana``／``stamina``（主角依武器大類，``roguelite.yaml`` 的
    ``start.heroes``）。只套用在 ``scaled_resources`` 的範本（主角）；敵人、隊友與召喚物照範本的
    固定值。"""

    base: int = Field(default=10, ge=0)
    mana: ResourcePool = ResourcePool(
        attrs=(Attribute.INT, Attribute.WIS, Attribute.WIL), per_point=2
    )
    stamina: ResourcePool = ResourcePool(
        attrs=(Attribute.STR, Attribute.DEX, Attribute.CON), per_point=2
    )
    stamina_regen: int = Field(default=5, ge=0)
    """耐力每回合開始回復的點數（Phase 3H-5，07 7.2；初值，平衡待辦 B15）。只套用在
    ``scaled_resources`` 的範本（主角）；不超過上限。戰後回滿見 ``roguelite.yaml`` 的
    ``refill_after_battle``。"""

    def pool(self, kind: ResourceKind) -> ResourcePool:
        return self.mana if kind == "mana" else self.stamina

    def bonus(self, kind: ResourceKind, attributes: Mapping[Attribute, int]) -> int:
        """屬性帶來的上限加成（可為負：最高者低於基準時）。"""
        pool = self.pool(kind)
        best = max(attributes.get(a, self.base) for a in pool.attrs)
        return (best - self.base) * pool.per_point

    mana_cap_permille: int = Field(default=1000, ge=100, le=5000)
    """法力上限倍率（‰；BAL-4b，**原型專用**難度數值）：
    套用在依屬性算上限的角色（主角與 build 英雄）。
    欄位預設 1000；``content/rules/core.yaml`` 寫 1400。進序列化與規則包雜湊。"""

    def max_for(self, kind: ResourceKind, base: int, attributes: Mapping[Attribute, int]) -> int:
        """上限 ＝ max(0, ``base`` ＋ :meth:`bonus`)；法力再乘 ``mana_cap_permille``。"""
        value = max(0, base + self.bonus(kind, attributes))
        if kind == "mana" and self.mana_cap_permille != _PERMILLE:
            return (value * self.mana_cap_permille + _PERMILLE // 2) // _PERMILLE
        return value


class AttributePerks(ContentModel):
    """屬性的常駐數值（Phase 3H-1，``docs/design/07-角色成長.md`` 7.2；初值，平衡待辦 B13）。

    屬性高於 ``base`` 每 ``step`` 點升一階（``base``＋``step``＝1 階，＋2×``step``＝2 階）。結算點：

    - ``collision_dealt``／``collision_taken``：撞擊傷害（``cause == "collision"``）每次 +／−；
    - ``surface_duration``：自己的技能產生的表面、持續區域的持續回合 +；
    - ``reaction_hit``：反應攻擊（藉機攻擊、監視射擊）的命中 +；
    - ``reveal_range``：能鎖定隱蔽單位的距離 +，也是自動看見敵方陷阱的距離；
    - ``control_resist``：有 ``control_group`` 的狀態（控制）的抵抗屬性值 +。
    """

    base: int = Field(default=10, ge=0)
    step: int = Field(default=4, ge=1)
    perks: tuple[AttributePerk, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> AttributePerks:
        keys = [(p.attr, p.kind) for p in self.perks]
        if len(set(keys)) != len(keys):
            raise ValueError("attribute_perks：同一屬性的同一種常駐數值重複")
        return self

    def tier(self, value: int) -> int:
        """屬性值 ``value`` 的階數（不高於 ``base`` 為 0）。"""
        return max(0, (value - self.base) // self.step)

    def of_attr(self, attr: Attribute) -> tuple[AttributePerk, ...]:
        return tuple(p for p in self.perks if p.attr is attr)

    def lines(self, attributes: Mapping[Attribute, int]) -> tuple[PerkLine, ...]:
        """角色面板的常駐數值說明（依資料產生，不寫死）：每條常駐數值一行，含目前階數。"""
        out: list[PerkLine] = []
        for perk in self.perks:
            value = attributes.get(perk.attr, self.base)
            tier = self.tier(value)
            total = perk.per_tier * tier
            out.append(
                PerkLine(
                    attr=perk.attr,
                    kind=perk.kind,
                    tier=tier,
                    per_tier_zh=perk.text_zh.replace("{n}", str(perk.per_tier)) + "／階",
                    now_zh=perk.text_zh.replace("{n}", str(total)) if tier else None,
                    next_at=self.base + self.step * (tier + 1),
                )
            )
        return tuple(out)

    def total(self, kind: PerkKind, attributes: Callable[[Attribute], int]) -> int:
        """``kind`` 的總加成：每條符合的常駐數值 ``per_tier × 階數``；``attributes`` 回傳屬性值。"""
        return sum(p.per_tier * self.tier(attributes(p.attr)) for p in self.perks if p.kind == kind)


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


_ROLE_HP_RANGE = (500, 3000)
"""召喚物依定位的 HP 係數允許的範圍（‰）。"""


class SummonTrait(ContentModel):
    """召喚物的小特性（Phase 3-33f2，分歧進化「加深」多給的一個小特性；``content/rules/core.yaml``
    的 ``summon_traits``）：召喚時直接加在召喚物身上的小幅數值。``budget_points`` 是這個特性在召喚技
    預算中的一次性點數。"""

    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    armor_bonus: int = Field(default=0, ge=0, le=3)
    speed_bonus: int = Field(default=0, ge=0, le=3)
    crit_range_delta: int = Field(default=0, ge=0, le=2)
    """暴擊範圍擴大幾點（最低自然骰值 −N；不低於 2）。"""
    budget_points: int = Field(default=1, ge=0, le=10)

    @model_validator(mode="after")
    def _has_effect(self) -> SummonTrait:
        if not (self.armor_bonus or self.speed_bonus or self.crit_range_delta):
            raise ValueError("召喚物小特性至少要有一項效果")
        return self


class WindRules(ContentModel):
    """風元素的專屬機制（Phase 3-54a，``docs/design/06-技能.md`` 6.33，#56）。

    - ``blow_surfaces``：吹送（``blow_surface`` 原語）能整片平移的表面。
    - ``spread_surfaces``／``spread_zone_elements``：風元素的技能傷害吹到這些表面、或帶這些元素的
      區域時，往風向擴大 ``spread_distance`` 格（元素擴散）。
    - ``collision_permille``：風元素的技能推擊造成的撞擊傷害倍率（風壓撞擊；1500 ＝ +50%）。

    預設值與 ``core.yaml`` 相同（舊紀錄沒有此欄位）。
    """

    blow_surfaces: tuple[Surface, ...] = (
        Surface.FIRE,
        Surface.POISON,
        Surface.ICE,
        Surface.WATER,
        Surface.OIL,
        Surface.SMOKE,
    )
    spread_surfaces: tuple[Surface, ...] = (Surface.FIRE, Surface.ICE, Surface.POISON)
    spread_zone_elements: tuple[Element, ...] = (
        Element.FIRE,
        Element.ICE,
        Element.POISON,
        Element.LIGHTNING,
    )
    spread_distance: int = Field(default=1, ge=1, le=2)
    collision_permille: int = Field(default=1500, ge=1000)


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

    # 屬性的常駐數值（Phase 3H-1，07 7.2）：每高於基準 4 點升一階
    attribute_perks: AttributePerks = AttributePerks()

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
    wind: WindRules = Field(default_factory=WindRules)
    clear_surfaces: tuple[Surface, ...] = (Surface.SMOKE, Surface.POISON)
    """清除表面（``clear_surface`` 原語，3-54c）省略表面種類時清除的表面。"""
    """風元素的專屬機制（Phase 3-54a；吹送、元素擴散、風壓撞擊）。"""
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

    # 資源上限（3H-2，07 7.2）：主角的法力與耐力上限依屬性
    resources: ResourceRules = ResourceRules()

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
    summon_role_hp_permille: dict[str, int] = Field(default_factory=dict)
    """依定位的召喚物 HP 係數（‰；Phase 3-33f1）：召喚當下 ``(範本 HP ＋ 成長) ×`` 這個值；
    定位見 ``battle.SUMMON_ROLES``，沒列出的定位視為 1000。近戰擋路與不動型調高、遠程維持。"""
    summon_max_duration: int = Field(default=4, ge=1, le=10)
    """召喚物持續輪數的上限（Phase 3-33b）：召喚技能的 ``duration`` 超過時以此為準。"""
    boss_summon_damage_permille: int = Field(default=2000, ge=1000, le=5000)
    """Boss（``boss`` 標籤）對召喚物造成的傷害倍率（‰；Phase 3-33b，預設 ×2）。"""
    enemy_damage_permille: int = Field(default=1000, ge=100, le=5000)
    """一般敵方（非 ``boss``、非 ``boss_escort`` 標籤）對我方造成的傷害倍率（‰；BAL-4b，**原型專用**
    難度數值）。欄位預設 1000；``content/rules/core.yaml`` 寫 1200。進序列化與規則包雜湊。"""
    boss_damage_permille: int = Field(default=1000, ge=100, le=5000)
    """Boss（``boss`` 標籤）造成的傷害倍率（‰；BAL-4b，原型專用）。"""
    boss_escort_damage_permille: int = Field(default=1000, ge=100, le=5000)
    """Boss 戰護衛與援軍（``boss_escort`` 標籤）造成的傷害倍率（‰；BAL-4b，原型專用）：
    與一般敵人分開調，
    ``content/rules/core.yaml`` 預設與 ``enemy_damage_permille`` 相同（行為與一般敵人一致）。"""
    ally_mana_cost_permille: int = Field(default=1000, ge=100, le=5000)
    """我方技能法力費用倍率（‰；BAL-4b，原型專用）。BAL-4c 起依**施放者陣營**套用：我方單位
    （含我方召喚物）施放、灌注、觸發技能時付 :meth:`ally_mana` 的費用，敵方照原價；技能資料
    （內容檔、規則包、生成技能）一律保持原始費用，預算、閃現、組合器都以原始費用計算。"""
    summon_command_ap_cost: int = Field(default=1, ge=0, le=3)
    """指揮召喚物（Phase 3-33c）的 AP 花費（切換模式免費）。"""
    summon_infuse_ap_cost: int = Field(default=1, ge=0, le=3)
    """灌注技能（Phase 3-33d，6.29.3）：施放者花的 AP（取代技能本身的 AP；法力與冷卻照技能）。"""
    summon_infused_cast_ap_cost: int = Field(default=1, ge=0, le=3)
    """召喚物在自己回合開始時施放灌注的技能，佔用牠自己的 AP（Phase 3-33d；取代一次普攻，
    不足時扣到 0）。"""
    summon_growth: SummonGrowth = Field(default_factory=SummonGrowth)
    """召喚物 HP 與傷害的成長（Phase 3-33b）。"""
    summon_infusions: dict[str, SummonInfusion] = Field(default_factory=dict)
    """灌注關鍵字對照（Phase 3-33b）：關鍵字 ID → 召喚物普攻附加效果；不在表中的關鍵字不可灌注。"""
    summon_traits: dict[str, SummonTrait] = Field(default_factory=dict)
    """召喚物小特性對照（Phase 3-33f2）：特性 ID → 效果；召喚技能的 ``trait`` 引用這裡。"""

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
        bad = sorted(set(self.summon_role_hp_permille) - set(SUMMON_ROLES))
        if bad:
            raise ValueError("summon_role_hp_permille 有未知的定位：" + "、".join(bad))
        low, high = _ROLE_HP_RANGE
        if any(not low <= v <= high for v in self.summon_role_hp_permille.values()):
            raise ValueError(f"summon_role_hp_permille 的係數必須在 {low}～{high}‰")
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

    def ally_mana(self, mana: int) -> int:
        """我方施放者實際付的法力（BAL-4c）：``mana × ally_mana_cost_permille‰``，四捨五入（半數
        進位）、原本有費用者至少 1；沒有費用或倍率 1000 時原值。整數運算、確定性。"""
        permille = self.ally_mana_cost_permille
        if mana == 0 or permille == _PERMILLE:
            return mana
        return max(1, (mana * permille + _PERMILLE // 2) // _PERMILLE)

    def max_hp_for(self, base_hp: int, con: int) -> int:
        """最大 HP ＝ 基礎 HP ＋（體質 − ``hp_con_base``）× ``hp_per_con_point``（至少 1）。"""
        return max(1, base_hp + (con - self.hp_con_base) * self.hp_per_con_point)

    def template_max_hp(self, template: UnitTemplate) -> int:
        """範本建立出的單位的最大 HP（引擎對敵我所有單位用同一公式）。"""
        return self.max_hp_for(template.max_hp, template.attributes[Attribute.CON])

    def template_stamina(self, template: UnitTemplate) -> int:
        """範本的基礎耐力：``stamina``，省略時 ``default_stamina``。"""
        return self.default_stamina if template.stamina is None else template.stamina

    def template_max_resource(self, kind: ResourceKind, template: UnitTemplate) -> int:
        """範本建立出的單位的法力／耐力上限：``scaled_resources`` 的範本（主角）依屬性加成
        （:class:`ResourceRules`），其他照範本的固定值。"""
        base = template.max_mana if kind == "mana" else self.template_stamina(template)
        if not template.scaled_resources:
            return base
        return self.resources.max_for(kind, base, template.attributes)

    def template_stamina_regen(self, template: UnitTemplate) -> int:
        """範本建立出的單位每回合開始回復的耐力：主角（``scaled_resources``）才有（3H-5）。"""
        return self.resources.stamina_regen if template.scaled_resources else 0

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
