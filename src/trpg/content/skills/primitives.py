"""效果原語的 schema：``PrimitiveDef``、``PrimitiveTable`` 與預設對象。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.constants import (
    SKELETON_IDS,
    Affects,
    KnobLadder,
    KnobWeight,
    SkillRarity,
    _unique,
)
from trpg.content.skills.shapes import RequiredWhen


class PrimitiveKnob(ContentModel):
    """原語參數的強度旋鈕（Phase 3T-1，原本是 ``composer_parts.effect_knobs`` 的 ``fixed`` 表）：
    隨機組合器與 LLM 提議的預算器（:mod:`trpg.skillgen.proposal_budget`）依這個階梯由弱到強調整
    參數值，讓技能的預算落在區間內。

    - ``ladder``：階梯來源（``dice`` 骰子階梯、``multipliers`` 武器倍率、``push_pull_distances``／
      ``blow_distances`` 位移格數、``status_duration``／``surface_duration`` 依引用的狀態／表面、
      ``stack_amount``／``per_stack`` 層數、``param_range`` 參數自己的 ``min``～``max``）。
    - ``start``／``max``／``step``（只給 ``param_range``）：從 ``start``（省略＝參數的 ``min``）到
      ``max``（省略＝參數的 ``max``），每 ``step`` 一階。
    - ``categories``／``exclude_categories``：只在這些技能類別／不在這些類別時有旋鈕。
    - ``when``：同一個效果的其他參數值（鍵＝參數名，值＝允許的值）符合時才有旋鈕。
    """

    ladder: KnobLadder
    weight: KnobWeight
    start: int | None = None
    max: int | None = None
    step: int = Field(default=1, ge=1)
    categories: tuple[str, ...] | None = None
    exclude_categories: tuple[str, ...] = ()
    when: dict[str, tuple[str, ...]] | None = None

    @model_validator(mode="after")
    def _check(self) -> PrimitiveKnob:
        if self.ladder != "param_range" and (
            self.start is not None or self.max is not None or self.step != 1
        ):
            raise ValueError("knob 的 start、max、step 只給 ladder: param_range 用")
        return self

    def applies(self, category: str, effect: Mapping[str, Any]) -> bool:
        """這個旋鈕在技能類別 ``category``、效果 ``effect``（``SkillDef`` 形狀）時是否成立。"""
        if self.categories is not None and category not in self.categories:
            return False
        if category in self.exclude_categories:
            return False
        if self.when is None:
            return True
        return all(str(effect.get(name)) in values for name, values in self.when.items())


class PrimitiveParam(ContentModel):
    """原語的一個參數。

    ``type``：``dice``（``NdM``）、``int``（``min``～``max``）、``status``／``surface``／
    ``object``／``stack``（引用其他資料檔的 ID）、``element``、``summon``（召喚物範本 ID，
    ``content/units/summons/``，Phase 3D-4a）。
    """

    type: Literal[
        "dice",
        "int",
        "status",
        "surface",
        "object",
        "element",
        "stack",
        "scale",
        "effects",
        "which",
        "tag",
        "bool",
        "resource",
        "skill",
        "on_hit",
        "summon",
        "summon_trait",
        "infusion",
        "anchor",
        "zone_when",
        "rule_change",
        "scaling",
        "count",
        "landing",
        "scope",
        "weapon",
        "form",
        "form_category",
    ]
    required: bool = False
    show_when: dict[str, str] | None = None
    """工坊的條件顯示（3-48c）：同一個原語的另一個參數（鍵）填了指定的值（值）才顯示這個參數
    （例：持續區域的 ``speed`` 只在 ``anchor: moving`` 時有意義）。只影響畫面，不影響驗證。"""
    required_when: RequiredWhen | None = None
    """``required: true`` 時，只在條件成立才必填（``None`` ＝ 一律必填）。"""
    min: int | None = None
    max: int | None = None
    allowed_skeletons: tuple[str, ...] | None = None
    """只能用在這些骨架（``None`` ＝ 不限；``split_heal``，Phase 3E-2f）。"""
    true_only: bool = False
    """``type: bool`` 的參數只能填 ``true``（不啟用就省略；``explode``、``split_heal``，4-L5c）。
    驗證器與 LLM 提議模型讀同一份資料。"""
    description_zh: str = ""
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）：中性描述，不含世界觀名詞、階段編號與欄位名；
    ``description_zh`` 是給開發者的。出貨的資料一律要寫（``tests/content/test_llm_hint.py``）。"""
    knob: Literal["none"] | PrimitiveKnob | tuple[PrimitiveKnob, ...] | None = None
    """強度旋鈕（Phase 3T-1，:class:`PrimitiveKnob`；多個時取第一個成立的）。``none`` ＝ 明寫沒有
    旋鈕；省略只允許在 ``budget_basis: fixed`` 的原語（:mod:`trpg.primitive_coverage` 檢查）。"""

    @model_validator(mode="after")
    def _check_required_when(self) -> PrimitiveParam:
        if self.required_when is not None and not self.required:
            raise ValueError("required_when 必須搭配 required: true")
        for knob in self.knobs():
            if knob.ladder != "param_range":
                continue
            low = self.min if knob.start is None else knob.start
            high = self.max if knob.max is None else knob.max
            if self.type != "int" or low is None or high is None or low > high:
                raise ValueError("knob 的 ladder: param_range 需要 int 參數的 min 與 max")
        return self

    def knobs(self) -> tuple[PrimitiveKnob, ...]:
        """宣告的旋鈕（``none`` 或省略時為空）。"""
        if self.knob is None or self.knob == "none":
            return ()
        if isinstance(self.knob, PrimitiveKnob):
            return (self.knob,)
        return self.knob


class PrimitiveDef(ContentModel):
    """一種效果原語。

    - ``category``：``numeric`` 數值型、``structural`` 結構型、``rule_rewrite`` 改寫規則型。
    - ``min_rarity``：使用此原語的最低稀有度（2A 只存不用，限制在 2B 實作）。
    - ``harmful``：有害（決定 ``affects`` 的預設值：有害 ``enemies``、有益 ``allies``）。
    - ``acts_on``：``unit``（對單位）、``tile``（對格子；預設 ``affects: tiles``）、
      ``caster``（只對施放者；``affects`` 一律為 ``self``）。
    - ``allowed_shapes``：只能搭配這些形狀（``None`` 為不限）。
    - ``forbid_affects``：不可搭配的 ``affects``（淨化不能對敵方使用）。
    - ``budget_basis``／``base_points``：預算點數的算法（``docs/phases/Phase2B計畫.md`` 4.2）：
      ``fixed`` 固定 ``base_points``、``per_distance`` ``base_points × distance``、
      ``per_amount`` ``base_points × amount``（2E-3 的 ``add_stack``）、
      ``obstacle`` ``base_points`` × ``obstacle_duration_permille``（依 ``duration``；省略＝永久，
      Phase 3-11）、
      ``consume_status`` ``then`` 的點數 × 期望倍率 × 濺射 × 「需要先有狀態」折扣（3C-3b）、
      ``consume_stack`` 同技能傷害點數 × 期望消耗層數 × ``per_stack_permille``（2E-3）、
      ``hurl_object`` 骰子平均 × 「需要附近有物件」折扣（＋擊倒點數，3C-5a）、
      ``charge_through`` （骰子平均 ＋ on_hit 點數）× 預期被撞到的敵人數（3D-2c）、
      ``summon`` 召喚物每輪預估傷害 × 持續輪數 × ``summon_round_value_permille``（3D-4a）、
      ``zone`` 區域效果點數 × 預估觸發次數（格數 × 輪數 × 係數，3D-5）、
      ``gamble`` 成功率 × win 的點數 ＋ 失敗率 × lose 的點數（期望值，3D-7a）、
      ``revive`` 基礎點數 ＋ 回復比例 × 係數（3D-8b）、
      ``delayed_damage`` 骰子平均 × 預期波及人數（3D-8b）、
      ``grant_skill`` 被給技能的總點數 × 預期使用次數（3D-8c）、
      ``inscribe`` ``base_points`` × ``inscribe_duration_permille``（依 ``duration``，3-23）、
      ``detonate_runes`` 骰子平均 × ``detonate_runes_permille``（需要先刻印的折扣，3-23）、
      ``dice_average`` 骰子平均值、``damage`` 法術為骰子平均值而武器為倍率 × 基準武器傷害、
      ``status``／``surface`` 為該狀態或表面的 ``budget_points`` × 持續 ÷ 預設持續。
      ``None`` 表示無法計算預算（驗證器會拒絕）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3；與 ``description_zh``、``player_description`` 分開）。"""
    player_description: str | None = Field(default=None, min_length=1)
    """給玩家看的一句話說明（Phase 3E-2e）：不含階段編號與程式識別字；glossary API 與部件說明框
    用它，省略時退回 ``description_zh``。出貨的原語一律要寫
    （``tests/content/test_player_description.py``）。"""
    category: Literal["numeric", "structural", "rule_rewrite", "rule_change"]
    min_rarity: SkillRarity = "common"
    harmful: bool
    acts_on: Literal["unit", "tile", "caster"] = "unit"
    allowed_shapes: tuple[str, ...] | None = None
    forbid_affects: tuple[Affects, ...] = ()
    position: Literal["first", "last"] | None = None
    """組合規則（Phase 4-L5b）：必須是技能的第一個（``first``）或最後一個（``last``）效果。"""
    sole_effect: bool = False
    """組合規則：必須是技能唯一的效果。"""
    others_affect: Literal["self"] | None = None
    """組合規則：同一技能的其他效果必須明寫這個 ``affects``（``self``：只作用在施放者）。"""
    nested_core: bool = False
    """這個原語的內容就是一組巢狀效果（消耗狀態後的效果、賭注的贏／輸分支、持續區域的效果）：
    工坊在 3-48d 起開放（子效果的選項見 ``trpg.skillgen.option_nested``）。"""
    max_per_skill: int | None = Field(default=None, ge=1)
    """組合規則：一個技能最多幾個這個效果。"""
    active_only: bool = False
    """組合規則：只能用在主動技能（``kind: active``）。

    以上五個欄位與 ``allowed_shapes`` 是「原語對整招技能的組合規則」的唯一來源：
    ``SkillDef`` 的驗證器（:func:`composition_rules`）與 LLM 提議模型（``trpg.skillgen.proposal``）
    都讀它們。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    """這個原語固定施加的狀態 ID（``statuses.yaml``；Phase 3E-2f）。引擎常數
    :data:`CHEAT_DEATH_STATUS`、:data:`REDIRECT_STATUS`、:data:`TIME_BOMB` 從這裡讀取。"""
    lookup_by_skill_id: bool = False
    """事後以技能 ID 查表（``skill_def(id)``）取回本原語的設定（Phase 3E-2a）：查到的是基礎型態，
    所以帶變奏的技能（基礎或任一變奏型態）不能含它——變奏的替換不會生效，甚至找不到效果而崩潰。"""
    params: dict[str, PrimitiveParam] = Field(default_factory=dict)
    budget_basis: (
        Literal[
            "fixed",
            "per_distance",
            "per_amount",
            "dice_average",
            "damage",
            "status",
            "surface",
            "obstacle",
            "consume_stack",
            "consume_status",
            "hurl_object",
            "restore_resource",
            "charge_through",
            "summon",
            "zone",
            "rule_change",
            "gamble",
            "dispel",
            "reveal",
            "revive",
            "delayed_damage",
            "grant_skill",
            "inscribe",
            "detonate_runes",
            "sacrifice_summon",
        ]
        | None
    ) = None
    base_points: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_budget(self) -> PrimitiveDef:
        needs_points = ("fixed", "per_distance", "per_amount", "obstacle", "inscribe")
        if self.budget_basis in needs_points and self.base_points is None:
            raise ValueError(f"原語 {self.id}：budget_basis {self.budget_basis} 必須填 base_points")
        for name, spec in self.params.items():
            unknown = sorted(set(spec.allowed_skeletons or ()) - set(SKELETON_IDS))
            if unknown:
                raise ValueError(
                    f"原語 {self.id}.{name}：allowed_skeletons 有未知的骨架：{', '.join(unknown)}"
                )
        return self

    def summary(self) -> str:
        return self.name_zh


class PrimitiveTable(ContentModel):
    """``content/skill_primitives.yaml``。"""

    primitives: tuple[PrimitiveDef, ...] = Field(min_length=1)
    mechanic_statuses: dict[str, str] = Field(default_factory=dict)
    """不是由原語施加、由技能機制使用的狀態 ID（``charging``；Phase 3E-2f）。"""

    @model_validator(mode="after")
    def _check(self) -> PrimitiveTable:
        _unique((p.id for p in self.primitives), "原語")
        return self

    def status_refs(self) -> set[str]:
        """原語與技能機制固定使用的狀態 ID（必須存在於 ``statuses.yaml``）。"""
        return {p.status for p in self.primitives if p.status is not None} | set(
            self.mechanic_statuses.values()
        )

    def by_id(self) -> dict[str, PrimitiveDef]:
        return {p.id: p for p in self.primitives}

    def summary(self) -> str:
        return f"{len(self.primitives)} 種效果原語"


def default_affects(primitive: PrimitiveDef) -> Affects:
    """省略 ``affects`` 時的預設值：地形類 ``tiles``、施放者專屬 ``self``、有害 ``enemies``、
    有益 ``allies``。"""
    if primitive.acts_on == "tile":
        return "tiles"
    if primitive.acts_on == "caster":
        return "self"
    return "enemies" if primitive.harmful else "allies"


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


class ConditionDef(ContentModel):
    """一種條件（``content/skill_conditions.yaml``）。

    ``harshness``：``common`` 常見／``harsh`` 嚴苛，決定預算的條件倍率（2B-2）。
    ``min_rarity``：使用此條件的最低稀有度。
    ``params`` 沿用原語參數的格式（``int``／``status``／``surface``）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）。"""
    harshness: Literal["common", "harsh"]
    min_rarity: SkillRarity = "common"
    params: dict[str, PrimitiveParam] = Field(default_factory=dict)

    def summary(self) -> str:
        return self.name_zh
