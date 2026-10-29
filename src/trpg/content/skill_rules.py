"""技能預算與驗證用的規則資料（``docs/phases/Phase2B計畫.md`` 第 4 節）。

對應資料檔：

- ``content/skill_budget.yaml``：:class:`BudgetRules`（AP 係數、條件倍率、代價折抵、合格區間、
  稀有度上限）。階級預算 ``tier_budget`` 與武器基準傷害在 ``rules/core.yaml``。
- ``content/skill_synergies.yaml``：:class:`SynergyTable`（機制標籤 → 協同係數）。
- ``content/skill_exclusions.yaml``：:class:`ExclusionTable`（互斥規則，以資料表達）。
- ``content/skeletons/<id>.yaml``：:class:`SkeletonDef`（12 種骨架的結構，加上 3C-2 的
  ``modifier``）。

這裡只定義 **資料 schema**；預算計算與驗證邏輯在 ``trpg.skillgen``（``trpg.content`` 不得匯入它）。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.rules import ResourceKind
from trpg.content.schemas import ContentModel
from trpg.content.skills import (
    AFFECTS_VALUES,
    RARITY_ORDER,
    SKELETON_IDS,
    Affects,
    SkillCategory,
    SkillCost,
    SkillKind,
    SkillRarity,
    WeaponReq,
)
from trpg.shared.types import Element

__all__ = [
    "MODIFIER_USE_KEYS",
    "BudgetRules",
    "CostAllowance",
    "EffectPattern",
    "ExclusionRule",
    "ExclusionTable",
    "ModifierBudget",
    "ModifierPoints",
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


class SelfStatusAllowance(ContentModel):
    """自身狀態代價的折抵（Phase 2H-1；初值，未經模擬）。

    折抵（‰）＝ 狀態的 ``budget_points`` × 有效回合（``duration − 1``）× ``per_point_permille``，
    先以 ``cap`` 截斷，再和其他折抵一起截斷在 ``total_cap``。
    """

    allowed: tuple[str, ...] = Field(min_length=1)
    per_point_permille: int = Field(ge=0)
    cap: int = Field(ge=0)
    status_caps: dict[str, int] = Field(default_factory=dict)
    """個別狀態的專屬上限（‰；Phase 3-50，06 6.5：暈眩 400）；沒列出的用 ``cap``。"""
    fixed_duration: dict[str, int] = Field(default_factory=dict)
    """持續時間固定的狀態（Phase 3-50：暈眩固定 2，＝跳過自己下一個回合）；其他可在 2–3 選。"""
    spell_only: tuple[str, ...] = ()
    """只能放在法術技（``category: spell``）的狀態（Phase 3-50：沉默；沒有法術不能白拿折扣）。"""

    def cap_of(self, status_id: str) -> int:
        """這個狀態的折抵上限（‰）。"""
        return self.status_caps.get(status_id, self.cap)


class CostAllowance(ContentModel):
    """代價折抵（‰，各項加總後乘上去：可用預算 ×（1000 ＋ 折抵）÷ 1000）。"""

    cooldown_per_turn: int = Field(ge=0)
    cooldown_cap: int = Field(ge=0)
    uses_per_battle: dict[int, int]
    """每場次數 → 折抵；次數超過表中最大值時用 ``uses_default``。"""
    uses_default: int = Field(ge=0)
    mana_per_point: int = Field(ge=0)
    mana_cap: int = Field(ge=0)
    stamina_per_mana: int = Field(default=2, ge=1)
    """耐力與法力的預算換算（Phase 3H-2，06 6.10；初值）：耐力 ``stamina_per_mana`` 點 ＝ 法力
    1 點，預算點數等價——耐力代價的折抵 ＝ 耐力 × ``mana_per_point`` ÷ ``stamina_per_mana``
    （向下取整），上限同 ``mana_cap``。武器技由法力改花耐力時，耐力 ＝ 法力 × 這個值，折抵與
    強度不變。"""
    hp_per_permille: int = Field(ge=0)
    """``hp_percent`` 每 1‰ 的折抵。"""
    hp_cap: int = Field(ge=0)
    self_status: SelfStatusAllowance
    overdraft_permille: int = Field(default=200, ge=0)
    """透支（``cost.overdraft``，Phase 3-50，06 6.5）的固定折抵（‰）：下一個回合少 1 AP。"""
    leave_form_permille: int = Field(default=200, ge=0)
    """解除形態（``leave_form`` 原語，Phase 3J-4c，06 6.30 解形爆發）的固定折抵（‰；初值，未經
    模擬）：施放時先解除自己的形態（照常冷卻），算代價。"""
    source_per_point: int = Field(default=250, ge=0)
    """源力代價（``cost.source``，Phase 3C-4a）每點的折抵（‰；初值，未經模擬）。"""
    source_cap: int = Field(default=500, ge=0)
    total_cap: int = Field(ge=0)
    """各項先套用自己的上限，加總後再以此截斷（‰）。"""


MODIFIER_USE_KEYS: tuple[str, ...] = (
    "attack",
    "shove",
    "trip",
    "interact",
    "all_attacks",
    "all_skills",
    "weapon_skills",
    "skill_tag",
)
"""``modifier.uses`` 的鍵：基本動作、所有攻擊、所有技能、武器技（3J-3）與每個符合的技能標籤。"""


class ModifierPoints(ContentModel):
    """修正規則每次使用增加的價值（千分之一點；初值，未經模擬）。

    ``damage_permille`` 與 ``push_distance_delta`` 沒有列在這裡：前者以基準武器傷害
    （``core.yaml`` 的 ``budget_reference_weapon_damage``）× ‰ 計算，後者沿用 ``push`` 原語的
    ``base_points``（每格）；``on_hit_effects`` 以效果本身的預算點數計算。
    """

    hit_bonus: int = Field(ge=0)
    """命中每 ±1。"""
    cooldown_delta: int = Field(ge=0)
    """剩餘冷卻每 −1。"""
    ap_decrease: int = Field(ge=0)
    """AP 成本 −1。"""
    ap_increase: int = Field(le=0)
    """AP 成本 +1（代價，負值）。"""
    range_delta: int = Field(ge=0)
    """射程每 ±1。"""
    add_element: int = Field(ge=0)
    add_tag: int = Field(ge=0)
    """每個加上的標籤。"""
    grant_pierce: int = Field(default=0, ge=0)
    """技能獲得穿透（Phase 3C-5b；每次使用的價值）。"""
    area_delta: int = Field(default=0, ge=0)
    """範圍型形狀大小 +1（Phase 3D-3；每次使用的價值，約為基準傷害 × 直線每格的形狀倍率加成）。"""
    summon_hp_per_100: int = Field(default=0, ge=0)
    """召喚物最大 HP 每 +100‰（Phase 3-24b1；每次使用的價值）。"""
    summon_attack_die: int = Field(default=0, ge=0)
    """召喚物攻擊每多 1 顆傷害骰（Phase 3-24b1；每次使用的價值）。``heal_permille`` 沒有列在這裡：
    與 ``damage_permille`` 一樣以基準武器傷害 × ‰ 計算。"""
    summon_limit: int = Field(default=0, ge=0)
    """召喚物同時上限每 ±1 的價值（Phase 3-33f1，召喚專精；每次使用的價值，負的上限改變為代價）。"""
    summon_duration: int = Field(default=0, ge=0)
    """召喚物持續每 +1 輪的價值（Phase 3-33f1）。"""
    summon_damage_per_100: int = Field(default=0, ge=0)
    """召喚物傷害加成每 +100‰ 的價值（Phase 3-33f1）。"""
    form_upkeep_per_100: int = Field(default=0, ge=0)
    """形態維持費每減少 100‰ 的價值（Phase 3J-3，化形專精；每次使用的價值）。"""
    form_entry_per_100: int = Field(default=0, ge=0)
    """形態進入獎勵的數值每增加 100‰ 的價值（Phase 3J-3，化形專精）。"""
    allow_self_target: int = Field(default=0, ge=0)
    """治療、護盾、增益類技能也包含自己（Phase 3D-3；每次使用的價值）。``shape_to`` 沒有列在這裡：
    依 ``skill_shapes.yaml`` 的形狀倍率差 × 基準武器傷害計算。"""


class ModifierBudget(ContentModel):
    """修正技能（``kind: modifier``，Phase 3C-2，6.14.1）的預算：

    ``規則點數 ＝ 每場預估使用次數 ×（命中後才生效的再 × 命中率）× 每次的價值 × 條件倍率``，
    ``可用預算 ＝ tier_budget × coefficient_permille ÷ 1000``。
    使用次數 ＝ ``applies_to`` 各項的 ``uses`` 加總（``all_attacks`` 涵蓋 ``attack``、``all_skills``
    涵蓋 ``skill_tags``；標籤每個各算一次），上限 ``uses_cap``。全部為初值、未經模擬。
    """

    coefficient_permille: int = Field(ge=1)
    hit_rate_permille: int = Field(ge=1, le=1000)
    shape_benefit_permille: int = Field(default=1000, ge=1, le=1000)
    """技能變形（``area_delta``、``shape_to``、``allow_self_target``，Phase 3D-3）的使用次數再乘上
    的比例：變形只有在目標的站位剛好受益時才有價值（類似命中率之於命中後效果）。"""
    uses: dict[str, int]
    uses_cap: int = Field(ge=1)
    per_turn_limit_uses: int = Field(default=8, ge=1)
    """帶 ``per_turn_limit`` 的規則（Phase 3-31）每場的預估使用次數：每個自己的回合最多 1 次，
    不看 ``uses`` 表（初值，未經模擬）。"""
    on_hit_rune_permille: int = Field(default=1000, ge=1, le=1000)
    """命中後效果裡的 ``inscribe``、``detonate_runes``（Phase 3-31）的點數再乘上的比例：符文單獨
    沒有效果、要先搭配另一個讀取者，且每回合只有 1 次（初值，未經模擬）。"""
    empty_slots_permille: int = Field(default=1000, ge=1, le=1000)
    """依空欄位數加傷的規則（``empty_slots_cap``，Phase 3-32a 普攻精通）以「滿格」估算的點數再乘上
    的比例：技能欄空著本身就是代價（少帶技能），所以打折（初值，未經模擬）。"""
    points_milli: ModifierPoints

    @model_validator(mode="after")
    def _check(self) -> ModifierBudget:
        if sorted(self.uses) != sorted(MODIFIER_USE_KEYS):
            raise ValueError(f"modifier.uses 必須剛好有 {', '.join(MODIFIER_USE_KEYS)}")
        if any(v < 0 for v in self.uses.values()):
            raise ValueError("modifier.uses 的次數不可為負")
        return self


class RarityLimit(ContentModel):
    """各稀有度的結構上限。"""

    max_effects: int = Field(ge=1, le=4)


def _default_cost_resource() -> dict[SkillCategory, ResourceKind]:
    return {"weapon": "stamina", "spell": "mana"}


class TerrainAreaRarity(ContentModel):
    """影響格數 ``min_cells`` 以上的升降地形，技能的稀有度至少要 ``rarity``。"""

    min_cells: int = Field(ge=1)
    rarity: SkillRarity


class BudgetRules(ContentModel):
    """``content/skill_budget.yaml``。"""

    min_ratio_permille: int = Field(ge=1, le=_PERMILLE_MAX)
    max_ratio_permille: int = Field(ge=1, le=_PERMILLE_MAX)
    ap_coefficient_permille: dict[int, int]
    reaction_coefficient_permille: int = Field(ge=1)
    stance_coefficient_permille: int = Field(default=1000, ge=1)
    """姿態技能的預算係數（‰；2E-2）：可用預算 ＝ tier_budget × 係數 ×（1000 ＋ 折抵）÷ 1000。"""
    form_coefficient_permille: int = Field(default=1000, ge=1)
    """形態技能（``enter_form``，Phase 3J-1a，6.30「照姿態計」）的預算係數（‰）：取代姿態係數。"""
    passive_extra_trigger_permille: int = Field(default=800, ge=1, le=1000)
    """被動技能的 ``trigger.max_per_round`` 每多 1 次，可用預算 × 這個值（‰）。"""
    known_budget_exceptions: tuple[str, ...] = ()
    """已知超出預算範圍（70～100%）的內建技能 ID（Phase 3-49：射程係數上線後，依規格不改技能數值，
    先標記，交玩法 PM 決定）。``trpg content check`` 不把它們的 ``budget.over``／``budget.weak``
    算成錯誤（``trpg skills budget`` 仍標出）；調整技能後從 ``content/skill_budget.yaml`` 移除。"""
    range_baseline: int = Field(default=4, ge=1)
    """射程係數（Phase 3-49，玩法決定 #53）：固定射程 N 的技能，形狀倍率再乘
    ``1000 ＋ (N − range_baseline) × range_step_permille``（‰）；射程 4＝×1.00。"""
    range_step_permille: int = Field(default=50, ge=0, le=200)
    """射程每多 1 格的係數增減（‰）：射程 1＝850、10＝1300。武器射程與沒有射程的形狀為 1000。"""
    trap_coefficient_permille: int = Field(default=800, ge=1, le=1000)
    """陷阱技能（Phase 2E-3）：觸發不確定，可用預算再 × 這個值（‰；初值，未經模擬）。"""
    consume_stack_expected_permille: int = Field(default=500, ge=1, le=1000)
    """``consume_stack`` 的預算以「期望消耗層數 ＝ 該層數上限 × 這個值」估算加成點數（‰；初值）。"""
    consume_status_scale_expected: int = Field(default=2, ge=1)
    """``consume_status`` 的預算以 ``then`` 的點數 × 這個期望倍率估算（Phase 3C-3b；初值）。"""
    consume_status_splash_permille: int = Field(default=500, ge=0, le=2000)
    """``splash`` 讓 ``then`` 的點數再加這個比例（‰；預期多波及的敵人；初值）。"""
    consume_status_discount_permille: int = Field(default=700, ge=1, le=1000)
    """「需要先有狀態」的條件折扣（‰；沿用條件折扣的做法；初值）。"""
    collision_die_points: int = Field(default=1, ge=0)
    """``push``／``pull`` 填了 ``collision_dice`` 時，每顆骰加的預算點數（Phase 3C-3a；初值）。"""
    hurl_object_discount_permille: int = Field(default=800, ge=1, le=1000)
    """``hurl_object`` 的「需要附近有可投擲的物件」折扣（Phase 3C-5a；初值，未經模擬）。"""
    charge_through_expected_targets_permille: int = Field(default=1500, ge=100, le=5000)
    """``charge_through`` 預期被撞到的敵人數（‰；Phase 3D-2c；初值，未經模擬）。"""
    summon_round_value_permille: int = Field(default=800, ge=1, le=5000)
    """``summon`` 的點數 ＝ 召喚物每輪預估傷害 × 持續輪數 × 這個值（‰；Phase 3D-4a；命中率與
    吸引火力的折合，初值，未經模擬）。"""
    summon_trait_extra_damage_permille: int = Field(default=1000, ge=0, le=5000)
    """召喚物特性計入預算（Phase 3-33e2a；以下 ``summon_trait_*`` 與 ``summon_detonate_*``、
    ``summon_topple_*`` 都是初值，未經模擬）：每輪的特性點數 ＝ 各項價值 × 對應係數，與武器骰平均
    加總後乘持續輪數與 ``summon_round_value_permille``。這個係數：灌注的額外傷害（雷靈的雷電）
    骰子平均 × 此值。"""
    summon_trait_status_permille: int = Field(default=100, ge=0, le=5000)
    """普攻命中附帶狀態（點燃、冰凍、標記、揭露…）：狀態的 ``budget_points`` × 此值。"""
    summon_trait_surface_permille: int = Field(default=100, ge=0, le=5000)
    """造表面（命中造水、脈動造水）：表面的 ``budget_points`` × 此值。"""
    summon_trait_chain_permille: int = Field(default=400, ge=0, le=5000)
    """水面連鎖（雷靈）：連鎖傷害（武器骰平均 × 連鎖人數 × 連鎖倍率）× 此值（要站在水裡才生效）。"""
    summon_trait_heal_permille: int = Field(default=600, ge=0, le=5000)
    """脈動治療（水精）：治療骰平均 × 此值（預期約 1 名受傷的友方在範圍內）。"""
    summon_trait_backstab_permille: int = Field(default=250, ge=0, le=5000)
    """背刺多出的傷害骰（影魅）：多出的骰子平均 × 此值（要繞到背後才生效）。"""
    summon_trait_trip_permille: int = Field(default=300, ge=0, le=5000)
    """絆倒（倒地關鍵字、骷髏、戰狼）：擊倒原語的 ``base_points`` × 此值（對抗判定、每輪 1 次）。"""
    summon_trait_knockback_permille: int = Field(default=200, ge=0, le=5000)
    """震退（撞擊關鍵字、石像）：推擊原語的 ``base_points`` × 震退格數 × 此值。"""
    summon_trait_height_permille: int = Field(default=300, ge=0, le=5000)
    """高處加傷（鷹隼的利爪）：武器每輪傷害 × 加傷比例 × 此值（要站得比目標高才生效）。"""
    summon_trait_conceal_points: int = Field(default=1, ge=0, le=10)
    """召喚時隱蔽：一次性的點數（不乘持續輪數）。"""
    summon_detonate_targets_permille: int = Field(default=1500, ge=0, le=5000)
    """自爆（爆裂傀儡）：爆炸傷害骰平均 × 預期被炸到的敵人數（‰），一次性（不乘持續輪數）；
    留下的表面另加 ``summon_trait_surface_permille`` × 表面點數 × 格數。"""
    summon_trait_conditional_permille: int = Field(default=400, ge=0, le=1000)
    """有條件才生效的命中特性（``hit_rules`` 的 ``when`` 不是 ``always``，如冰靈只凍水裡的目標）：
    狀態點數再 × 此值。"""
    summon_trait_immovable_permille: int = Field(default=500, ge=0, le=5000)
    """不會被推動（石像）：每輪折合的點數（‰，擋路的價值）。"""
    summon_detonate_rounds: int = Field(default=1, ge=1, le=6)
    """會自爆的召喚物（爆裂傀儡）：一般攻擊與特性只算這麼多輪（自爆後就消失了），自爆另計。"""
    summon_trait_pull_permille: int = Field(default=1000, ge=0, le=5000)
    """拉扯（吸引圖騰，Phase 3-33e2b）：拉扯原語點數 × 此比例（‰），每輪。"""
    summon_trait_platform_permille: int = Field(default=1000, ge=0, le=5000)
    """高台（高台圖騰，Phase 3-33e2b）：升起地形原語點數 × 高度 × 此比例（‰），每輪。"""
    summon_topple_targets_permille: int = Field(default=1000, ge=0, le=5000)
    """被推倒壓人（土牆）：推倒傷害骰平均 ＋ 擊倒原語點數，× 預期被壓到的敵人數（‰），一次性。"""
    summon_hp_weight_permille: int = Field(default=300, ge=0, le=2000)
    """召喚技能的 ``max_hp_permille``（加深進化，Phase 3-33f2）：召喚物每輪價值 ×（1 ＋ 多出的
    HP 比例 × 此值）；HP 的價值只佔每輪價值的這個比例（‰，初值，未經模擬）。"""
    totem_expected_allies_permille: int = Field(default=1000, ge=0, le=5000)
    """圖騰（Phase 3D-4b）的點數 ＝ 光環狀態的 ``budget_points`` × 預期受惠的友方數（‰）× 持續輪數
    × ``summon_round_value_permille``（初值，未經模擬）。"""
    legendary_battle_budget_permille: int = Field(default=600, ge=100, le=1000)
    """常駐類傳說 ``activation: battle``（整場）的可用預算倍率（‰；Phase 3D-6，使用者決定
    「整場較弱」；初值，以模擬調整）。``timed``（限時）為基準 1000‰。"""
    zone_cell_round_permille: int = Field(default=120, ge=1, le=5000)
    """``zone``（Phase 3D-5）：每格每輪預估的觸發次數（‰；初值，未經模擬）。"""
    zone_both_permille: int = Field(default=1500, ge=1000, le=5000)
    """``zone`` 的 ``when: both``（進入與回合開始都結算）的倍率（‰）。"""
    zone_moving_permille: int = Field(default=1500, ge=1000, le=5000)
    """``zone`` 的 ``anchor: moving``（掃過更多格子）的倍率（‰）。"""
    zone_surface_permille: int = Field(default=300, ge=0, le=5000)
    """``zone`` 留下的表面：每個新覆蓋格的表面點數折合（‰）。"""
    restore_mana_point_permille: int = Field(default=700, ge=0, le=5000)
    """``restore_resource`` 回復法力：每點法力折合的預算點數（‰；Phase 3D-1；初值）。"""
    restore_cooldown_points: int = Field(default=3, ge=0)
    """``restore_resource`` 縮短冷卻：每回合折合的預算點數（Phase 3D-1；初值）。"""
    dispel_one_points: int = Field(default=3, ge=0)
    """``dispel`` 驅散 1 個增益的預算點數（Phase 3D-8a；初值，未經模擬）。"""
    dispel_all_points: int = Field(default=6, ge=0)
    """``dispel`` 驅散全部增益的預算點數（Phase 3D-8a；初值）。"""
    obstacle_duration_permille: tuple[int, ...] = Field(
        default=(400, 500, 600, 700, 750, 800, 850, 900, 950, 1000), min_length=10, max_length=10
    )
    """``create_obstacle``（Phase 3-11）：``duration`` 為 n 回合時，點數 ＝ 基礎 × 第 n 項（‰）；
    共 10 項（1–10 回合），永久（省略 ``duration``）＝ 基礎 × 1000‰ ＝ 現狀（初值，未經模擬）。"""
    inscribe_duration_permille: tuple[int, ...] = Field(
        default=(600, 800, 1000, 1200, 1400), min_length=5, max_length=5
    )
    """``inscribe``（Phase 3-23）：``duration`` 為 n 輪時，點數 ＝ 基礎 × 第 n 項（‰）；共 5 項
    （1–5 輪），省略 ``duration`` 時取 ``core.rune_default_rounds`` 對應的項（初值，未經模擬）。"""
    shield_duration_permille: tuple[int, ...] = Field(
        default=(1000, 1300), min_length=2, max_length=2
    )
    """``shield``（Phase 3-50b）：``duration`` 為 2 或 3 回合時，點數 ＝ 骰子平均 × 第 n 項（‰；
    省略 ＝ 2 回合 ＝ 1000‰ ＝ 現狀；初值，未經模擬）。"""
    terrain_area_rarity: tuple[TerrainAreaRarity, ...] = ()
    """升降地形（``raise_terrain``、``lower_terrain``）的影響格數對應的最低稀有度（Phase 3-54b，
    06 6.33，#58）：形狀影響格數 ≥ ``min_cells`` 的最高一項生效（依 ``min_cells`` 由小到大）。"""
    wind_spread_permille: tuple[int, ...] = Field(default=(1000, 1150), min_length=2, max_length=2)
    """風元素傷害的元素擴散格數（``spread``，Phase 3-54b）：擴散 n 格時，傷害效果的點數 × 第 n 項
    （‰；1 格或省略 ＝ 1000‰ ＝ 現狀；初值，未經模擬）。"""
    detonate_runes_permille: int = Field(default=700, ge=1, le=3000)
    """``detonate_runes``（Phase 3-23）：點數 ＝ 骰子平均 × 此值 ÷ 1000（需要先刻印、且敵人要站在
    符文上的折扣；形狀倍率另外照一般效果計算；初值，未經模擬）。"""
    sacrifice_summon_permille: int = Field(default=800, ge=1, le=3000)
    """``sacrifice_summon``（Phase 3-24c）：點數 ＝ 骰子平均 × 此值 ÷ 1000（需要先有召喚物、而且
    召喚物會消失的折扣；形狀倍率另外照一般效果計算；初值，未經模擬）。"""
    reveal_base_points: int = Field(default=2, ge=0)
    reveal_round_points: int = Field(default=1, ge=0)
    """``reveal`` 的預算點數 ＝ ``reveal_base_points`` ＋ ``reveal_round_points`` × ``duration``
    （Phase 3D-8a；初值，未經模擬）。"""
    revive_base_points: int = Field(default=6, ge=0)
    revive_hp_point_permille: int = Field(default=10, ge=0, le=100)
    """``revive`` 的預算點數 ＝ ``revive_base_points`` ＋ ``hp_permille`` ×
    ``revive_hp_point_permille`` ÷ 1000（Phase 3D-8b；初值，未經模擬）。"""
    delayed_damage_base_targets_permille: int = Field(default=1000, ge=0, le=5000)
    delayed_damage_radius_targets_permille: int = Field(default=400, ge=0, le=3000)
    """``delayed_damage`` 的預算點數 ＝ 骰子平均 ×（``delayed_damage_base_targets_permille`` ＋
    半徑 × ``delayed_damage_radius_targets_permille``）÷ 1000（預期波及的人數；Phase 3D-8b）。"""
    on_kill_expected_permille: int = Field(default=300, ge=0, le=1000)
    """``on_kill`` 各效果的點數 × 這個預估擊殺率（‰；Phase 3D-8b；初值，未經模擬）。"""
    refund_ap_points: int = Field(default=6, ge=0)
    """``on_kill`` 的 ``refund_ap`` 每返還 1 點 AP 折合的預算點數（Phase 3D-8b；初值）。"""
    grant_skill_expected_uses_per_round_permille: int = Field(default=800, ge=0, le=3000)
    """``grant_skill`` 的預算點數 ＝ 被給技能的總點數 × 這個值 ÷ 1000 × 持續輪數（預期每輪使用
    次數；Phase 3D-8c；初值，未經模擬）。"""
    lifesteal_value_permille: int = Field(default=800, ge=0, le=2000)
    """吸血（``lifesteal_permille``，Phase 3D-8a）：回復的 HP 折合傷害點數的比例（‰）。傷害效果的
    點數 × (1 ＋ 吸血‰ × 這個值 ÷ 10⁶)（初值，未經模擬）。"""
    pierce_bonus_permille: int = Field(default=150, ge=0, le=1000)
    """有 ``pierce`` 的技能，總點數再加這個比例（‰；Phase 3C-5b；初值，未經模擬）。"""
    variant_surcharge_permille: int = Field(default=100, ge=0, le=1000)
    """戰場變奏（Phase 3-25a，6.24）：每個變奏的加價（‰）。基礎型態的總點數 ×（1000 ＋ 這個值 ×
    變奏數）÷ 1000；每個變奏型態另外照一般技能計算，各自落在預算窗內（初值，之後以模擬調整）。"""
    composite_tax_permille: int = Field(default=150, ge=0, le=1000)
    """複合技能（Phase 3F-3a，6.23）的加成：總點數 ＝（位移段點數 ＋ 動作段點數）×（1000 ＋ 這個值）
    ÷ 1000（省下一次行動的代價；初值，之後以模擬調整）。"""
    composite_self_combo_permille: int = Field(default=1000, ge=0, le=5000)
    """複合技能兩段之間形成元素／表面連鎖（第一段造表面或施加狀態、第二段的元素引爆或與之互動；
    Phase 3F-4a，6.23「同一招不能自己造環境又引爆它」）時，總點數再 ×（1000 ＋ 這個值）÷ 1000
    （初值 1000‰，即點數翻倍）。"""
    composite_delayed_discount_permille: int = Field(default=800, ge=0, le=1000)
    """延遲段（Phase 3F-4b，6.23 #5）的折扣：第二段點數 × 這個值 ÷ 1000 再乘複合加成（敵人看得到
    倒數與範圍、能反應；初值，未經模擬）。"""
    gamble_variance_bonus_permille: int = Field(default=1100, ge=1000, le=2000)
    """帶賭博機制的技能（Phase 3D-7a，6.17）：預算以期望值計，可用預算再 × 這個「變異加成」（‰；
    平均強度略高於同級穩定技能，作為冒險的補償；初值，未經模擬）。"""
    gamble_self_harm_permille: int = Field(default=500, ge=0, le=1000)
    """賭注分支與失手反噬中，對施放者自己的有害效果（自傷、反噬狀態）折合的預算：效果點數 × 這個值
    （‰）後從總點數扣除（Phase 3D-7a；初值）。"""
    gamble_on_miss_rate_permille: int = Field(default=300, ge=0, le=1000)
    """失手反噬 ``cost.on_miss`` 的預估觸發率（‰；Phase 3D-7a；約等於未命中的比例，初值）。"""
    variance_dice_share_permille: int = Field(default=700, ge=0, le=1000)
    """高變異（Phase 3D-7b）：武器技的傷害裡「骰子」所占的比例（‰；其餘是固定值與屬性加成）。
    爆骰與擴大暴擊範圍只增加骰子的部分（初值，未經模擬）。"""
    explode_weapon_sides: int = Field(default=8, ge=2, le=20)
    """武器技的 ``explode`` 以幾面骰估計期望值（法術技用自己的骰子面數；Phase 3D-7b；初值）。"""
    scale_expected_steps_milli: dict[str, int] = Field(
        default_factory=lambda: {
            "missing_hp_10pct": 2000,
            "distance": 3000,
            "enemies_adjacent_target": 1500,
            "enemies_adjacent_self": 1500,
        }
    )
    """依情況縮放（Phase 3D-7b）：每種依據預估的平均步數（千分之一步）。"""
    overload_expected_permille: int = Field(default=1000, ge=0, le=3000)
    """超載（Phase 3D-7b）：帶標籤技能的傷害加成以「平均層數 ＝ (門檻 − 1) ÷ 2」×
    這個比例（‰）估計；累積層數的技能另外扣「反噬點數 × 自傷折合 ÷ 門檻 × 累積層數」
    （初值，未經模擬）。"""
    condition_permille: dict[Literal["none", "common", "harsh"], int]
    all_target_permille: int = Field(ge=1, le=1000)
    """``affects: all``（敵我不分）的對象係數。"""
    allowance: CostAllowance
    rarity: dict[Literal["common", "rare", "epic", "legendary"], RarityLimit]
    max_rule_rewrite: int = Field(ge=0)
    """每個技能的改寫規則型原語上限。"""
    rule_rewrite_min_cooldown: int = Field(ge=1)
    """有改寫規則型原語的技能：``uses_per_battle: 1`` 或冷卻至少這麼多回合。"""
    rule_rewrite_min_cooldown_with_source: int = Field(default=2, ge=1)
    """花源力（``cost.source``，傳說技能）的改寫規則型技能：改為 ``uses_per_battle: 1`` 或冷卻至少
    這麼多回合（Phase 3C-4a；初值）。"""
    modifier: ModifierBudget
    """修正技能的預算（Phase 3C-2）。"""
    cost_resource: dict[SkillCategory, ResourceKind] = Field(default_factory=_default_cost_resource)
    """技能的費用花哪種資源（Phase 3H-2，06 6.10）：武器技花耐力、法術技花法力。"""

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
        if sorted(self.cost_resource) != ["spell", "weapon"]:
            raise ValueError("cost_resource 必須剛好有 weapon、spell")
        cells = [t.min_cells for t in self.terrain_area_rarity]
        ranks = [RARITY_ORDER.index(t.rarity) for t in self.terrain_area_rarity]
        if cells != sorted(set(cells)) or ranks != sorted(ranks):
            raise ValueError("terrain_area_rarity 必須依 min_cells 嚴格遞增、稀有度不遞減")
        return self

    def resource_of(self, category: SkillCategory) -> ResourceKind:
        """``category`` 的技能花哪種資源。"""
        return self.cost_resource[category]

    def cost_problem(self, category: SkillCategory, cost: SkillCost) -> str | None:
        """代價花的資源與類別不符（例：武器技花法力）時的說明；相符為 ``None``。"""
        want = self.resource_of(category)
        other: ResourceKind = "stamina" if want == "mana" else "mana"
        if getattr(cost, other) == 0:
            return None
        names = {"mana": "法力", "stamina": "耐力"}
        kind = "武器技" if category == "weapon" else "法術技"
        return f"{kind}花{names[want]}，不能花{names[other]}"

    def min_cost_problem(
        self, kind: str, category: SkillCategory, cost: SkillCost, tags: Iterable[str] = ()
    ) -> str | None:
        """最低花費（06 6.10，2026-10-24）：主動的法術技至少 1 法力、主動的武器技至少 1 耐力；
        被動、反應、姿態、修正照各自的規則。例外（06 6.10 `244974a`）：花源力的技能（源力就是代價）
        與裝備解鎖的動作（標籤 ``gear``，預算由詞條計價）不受限制。"""
        if kind != "active" or cost.source is not None or "gear" in tags:
            return None
        want = self.resource_of(category)
        if getattr(cost, want) >= 1:
            return None
        names = {"mana": "法力", "stamina": "耐力"}
        label = "武器技" if category == "weapon" else "法術技"
        return f"主動的{label}至少要花 1 點{names[want]}"

    def stamina_for_mana(self, mana: int) -> int:
        """法力代價換成等價的耐力代價（預算點數相同）。"""
        return mana * self.allowance.stamina_per_mana

    def resource_cost(self, cost: dict[str, Any], category: SkillCategory) -> dict[str, Any]:
        """把產生器的代價（一律以法力表示）換成 ``category`` 該花的資源：花耐力的類別把 ``mana``
        換成等價的 ``stamina``（:meth:`stamina_for_mana`），其他欄位不變。"""
        if self.resource_of(category) == "mana" or not cost.get("mana"):
            return cost
        out = {k: v for k, v in cost.items() if k != "mana"}
        return {**out, "stamina": self.stamina_for_mana(int(cost["mana"]))}

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
    elements_any: tuple[Element, ...] | None = None
    """技能的元素（:func:`~trpg.content.skills.skill_elements`：技能元素欄，沒填時沿用標籤的元素）是
    其中之一（Phase 3-54b／3-54d：只有大地技能能升降地形、施加石膚、震波）。"""
    any_of: tuple[SkillMatch, ...] | None = None
    """子比對任一個符合就算符合（Phase 3-54d：一條規則涵蓋「原語 A 或狀態 B」）。"""


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
    require_any_primitives: tuple[str, ...] = ()
    """技能的效果至少要有其中一個原語（蓄力與終結：add_stack／consume_stack；陷阱：place_trap）。"""
    required_category: SkillCategory | None = None
    """使用此骨架的技能必須是這個類別（``None`` ＝ 不限；被動：``spell``）。"""
    required_weapon_req: WeaponReq | None = None
    """使用此骨架的技能必須是這個武器需求（``None`` ＝ 不限；被動：``any``）。"""
    min_rarity: SkillRarity = "common"
    """使用此骨架的最低稀有度（2E：被動 epic；之後的反應技、姿態、蓄力／終結、陷阱 rare）。"""

    @model_validator(mode="after")
    def _check(self) -> SkeletonDef:
        if self.id not in SKELETON_IDS:
            raise ValueError(f"未知的骨架 {self.id!r}（可用：{', '.join(SKELETON_IDS)}）")
        if self.enabled and not self.core.primitives and self.kinds != ("modifier",):
            raise ValueError(f"骨架 {self.id}：啟用的骨架必須有核心原語（修正技能的骨架除外）")
        return self

    def summary(self) -> str:
        state = "啟用" if self.enabled else "停用"
        return f"{self.name_zh}（{state}）"
