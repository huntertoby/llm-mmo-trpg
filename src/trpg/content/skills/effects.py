"""效果與形狀規格：``ShapeSpec``、``ScaleSpec``、``EffectSpec``、組合規則與 YAML 參數表。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, Dice
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.skills.conditions import ConditionSpec
from trpg.content.skills.constants import (
    _MAX_MULTIPLIER_PERMILLE,
    _PERMILLE,
    EFFECT_NON_PARAM_FIELDS,
    SELF_MOVES,
    SKILL_ID_PATTERN,
    YAML_RANGED_FIELDS,
    Affects,
    ScaleBy,
)
from trpg.content.skills.primitives import PrimitiveDef, PrimitiveParam, PrimitiveTable
from trpg.shared.types import Element, Surface

# ---------------------------------------------------------------------------
# 技能
# ---------------------------------------------------------------------------


class ShapeSpec(ContentModel):
    """技能的目標形狀：``type`` 加上該形狀的參數（範圍見 ``skill_shapes.yaml``）。"""

    type: str = Field(pattern=ID_PATTERN)
    size: int | None = None
    range: int | Literal["weapon"] | None = None
    radius: int | None = None
    jumps: int | None = None
    jump_range: int | None = None

    def param_values(self) -> dict[str, int | str]:
        """已填寫的參數（依名稱排序）。"""
        values: dict[str, int | str] = {}
        for name in ("jump_range", "jumps", "radius", "range", "size"):
            value = getattr(self, name)
            if value is not None:
                values[name] = value
        return dict(sorted(values.items()))


class ScaleSpec(ContentModel):
    """傷害效果的 ``scaling``（Phase 3D-7b）：每一步傷害 ``+per_step_permille`` ‰（無條件捨去），
    總加成不超過 ``cap_permille``（必填；上限見 ``core.yaml`` 的 ``scale_cap_max_permille``）。
    （欄位名不叫 ``scale``：那是 ``consume_status`` 的欄位。）"""

    by: ScaleBy
    per_step_permille: int = Field(ge=1, le=_PERMILLE)
    cap_permille: int = Field(ge=1, le=_MAX_MULTIPLIER_PERMILLE)


class EffectSpec(ContentModel):
    """技能的一個效果原語（flat 結構；哪些參數合法由原語定義決定）。

    ``condition`` 為效果層級的條件：對每個對象（單位或格子）分別判斷，不成立的對象不受此效果影響。
    """

    type: str = Field(pattern=ID_PATTERN)
    affects: Affects | None = None
    dice: Dice | None = None
    multiplier_permille: int | None = None
    element: Element | None = None
    distance: int | None = None
    collision_dice: Dice | None = None
    """``push``/``pull`` 可省略：撞擊傷害骰，取代核心規則的預設（Phase 3C-3a）。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    duration: int | None = Field(default=None, ge=1)
    surface: Surface | None = None
    object: str | None = Field(default=None, pattern=ID_PATTERN)
    amount: int | None = None
    permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``redirect_damage`` 專用（Phase 3C-4b）：轉移給施放者的傷害千分比。"""
    stack: str | None = Field(default=None, pattern=ID_PATTERN)
    per_stack_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    then: tuple[EffectSpec, ...] | None = None
    """``consume_status`` 專用：移除狀態之後結算的效果（1–2 個；Phase 3C-3b）。"""
    scale: Literal["remaining_rounds", "stacks"] | None = None
    """``consume_status`` 專用：``then`` 的骰數倍率（Phase 3C-3b）。``remaining_rounds``＝被消耗
    狀態的剩餘回合（永久狀態為 1）；``stacks``＝同時消耗目標身上 ``stack`` 的層數
    （``stack`` 必填）。"""
    splash: int | None = None
    """``consume_status`` 專用：``then`` 也作用在被消耗者周圍這麼遠（曼哈頓距離）的敵方單位。"""
    which: Literal["all", "tag"] | None = None
    """``reset_cooldown`` 專用（Phase 3C-4a）：``all`` 全部技能、``tag`` 只有帶 ``tag`` 標籤的
    技能。"""
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """``reset_cooldown`` 的 ``which: tag`` 必填：要重置的技能標籤。"""
    range: int | None = Field(default=None, ge=1)
    """``hurl_object`` 專用（Phase 3C-5a）：可以舉起的物件與施放者的最遠距離（曼哈頓）。"""
    knock_prone: bool | None = None
    """``hurl_object`` 專用（Phase 3C-5a）：命中落點的單位時另外擊倒（對抗判定同
    ``knock_prone`` 原語）。"""
    resource: Literal["mana", "cooldown"] | None = None
    """``restore_resource`` 專用（Phase 3D-1）：``mana`` 回復法力 ``amount``；``cooldown`` 讓目標
    所有技能（不含花源力的技能與施放中的這個技能）冷卻 −``amount``。"""
    on_hit: Literal["knock_prone", "push_aside"] | None = None
    """``charge_through`` 專用（Phase 3D-2c）：被撞到的敵人除了傷害之外的效果——``knock_prone``
    擊倒（對抗判定）或 ``push_aside`` 推到路徑旁一格。"""
    landing: Literal["choose", "behind"] | None = None
    """``shadowstep`` 專用（Phase 3D-8d）：``choose`` 一般瞬步（形狀 ``unit_then_tile``，玩家自選
    目標相鄰的空格）；``behind`` 瞬步背刺類（形狀 ``single``，固定落在目標的背後格）。"""
    unit: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3D-4a）：召喚物範本 ID（``content/units/summons/``）。"""
    form: str | None = Field(default=None, pattern=ID_PATTERN)
    """``enter_form`` 專用（Phase 3J-1a）：形態 ID（``content/forms.yaml``）。"""
    count: int | Literal["all"] | None = Field(default=None)
    """``summon`` 專用（Phase 3D-4a）：一次召喚的數量（1；數量型分歧進化 3-33f2 可為 2，此時必須
    填 ``power_permille``）。``dispel`` 專用（Phase 3D-8a）：驅散的增益個數（1）或
    ``all``（全部）。"""
    power_permille: int | None = None
    """``summon`` 專用（Phase 3-33f2，數量型分歧進化）：每隻召喚物的最大 HP 與傷害只有一般的這麼多
    ‰（例如 600 ＝ 60%）；一次召喚 2 隻（``count: 2``）時必填，必須小於 1000。只有一隻時不能小於
    1000（Phase 3W-5b，完整技能把 +120‰ 加在召喚物的 HP 與傷害上；1000 ＝ 不變，存檔前會省略）。"""
    magnitude_permille: int | None = None
    """``apply_status`` 專用（Phase 3W-5b，完整姿態技能）：姿態的幅度（‰，不小於 1000；1000 ＝
    不變）——狀態倍率欄位對持有者有利的一邊離中性值的距離乘上它（:func:`trpg.engine.rules.statuses.scaled_permille`）。
    只能用在姿態技能（``kind: stance``）。"""
    max_hp_permille: int | None = None
    """``summon`` 專用（Phase 3-33f2，加深分歧進化）：召喚物的最大 HP 多 ‰（召喚時結算，在成長與
    修正規則之後相乘）。"""
    trait: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3-33f2，加深分歧進化）：召喚物的小特性（``core.yaml`` 的
    ``summon_traits``）。"""
    infusion: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3-33f2，橋接分歧進化）：召喚物固有的第二個灌注關鍵字
    （``core.yaml`` 的 ``summon_infusions``）；與施放時選的灌注、範本固有的灌注並存。"""
    anchor: Literal["tile", "caster", "moving"] | None = None
    """``zone`` 專用（Phase 3D-5）：``tile`` 固定在施放時的格子、``caster`` 跟隨施放者、``moving``
    每次環境回合沿施放方向前進 ``speed`` 格。"""
    when: Literal["enter", "turn_start", "both"] | None = None
    """``zone`` 專用（Phase 3D-5）：區域效果結算的時機——單位 **進入** 區域時、**回合開始時** 站在
    區域內時，或兩者。（設計文件寫作 ``on``；YAML 1.1 會把 ``on`` 讀成布林值，所以欄位名用
    ``when``。）"""
    speed: int | None = Field(default=None, ge=1)
    """``zone`` 的 ``anchor: moving`` 專用（Phase 3D-5）：每次環境回合前進的格數。"""
    rule: str | None = Field(default=None, pattern=ID_PATTERN)
    """``rule_change`` 專用（Phase 3D-6）：``content/rule_changes.yaml`` 的規則改變 ID。"""
    chance_permille: int | None = Field(default=None, ge=1, le=_PERMILLE - 1)
    """``gamble`` 專用（Phase 3D-7a）：成功（結算 ``win``）的機率（‰）；d1000 不超過它就成功。"""
    win: tuple[EffectSpec, ...] | None = None
    lose: tuple[EffectSpec, ...] | None = None
    """``gamble`` 專用：成功／失敗時結算的效果（各 0–2 個，至少一邊有效果；類型見
    :data:`GAMBLE_BRANCH_TYPES`）；對象 ``self`` 即對施放者（失敗的反噬）。"""
    damage_multiplier_permille: int | None = Field(
        default=None, ge=100, le=_MAX_MULTIPLIER_PERMILLE
    )
    """``damage_multiplier`` 專用：本次施放的傷害效果 × 這個倍率（‰；2000 ＝ 加倍）。"""
    self_damage_permille_of_hit: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``self_damage_of_hit`` 專用：施放者受到「本次施放對敵人造成的傷害」的 n‰（反噬，不致命）。"""
    explode: bool | None = None
    """``damage`` 專用（Phase 3D-7b，6.17 B）：爆骰——擲到最大值再加擲一次，每顆骰最多再擲
    ``core.explode_max`` 次。只有主技能效果（不含賭注分支與 ``then``）可以用。"""
    scaling: ScaleSpec | None = None
    """``damage`` 專用（Phase 3D-7b，6.17 E、6.18 G）：依情況縮放傷害。"""
    lifesteal_permille: int | None = None
    """``damage`` 專用（Phase 3D-8a，6.18 A）：吸血——施放者回復「這個效果實際造成的傷害（扣掉護盾
    吸收）」的 n‰（無條件捨去，不超過最大 HP）。只有技能自己的傷害效果可以用。"""
    attr_permille: int | None = Field(default=None, ge=0, le=_PERMILLE)
    """``damage`` 專用的法術屬性倍率覆蓋（Phase 3J-2；‰）：省略＝法術的屬性倍率（核心規則）。
    只給引擎由資料組出的技能用（形態的蓄力吐息要和普攻一樣屬性 × 0.3，見
    :mod:`trpg.content.form_breath`）；原語定義沒有列它，玩家與 LLM 的技能不能使用。"""
    form_bonus_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``damage``、``heal`` 專用（Phase 3J-4b，06 6.30）：施放者在形態中時，這個效果的傷害或治療
    ×（1000 ＋ n）‰（整體乘上去：骰值、屬性加成和其他倍率一起，屬性加成只算一次；不在形態中
    不變）。只有技能自己的效果可以用。"""
    spread: int | None = Field(default=None, ge=1, le=2)
    """``damage`` 專用（Phase 3-54b，06 6.33）：風元素傷害的元素擴散格數（1 或 2；省略＝
    ``core.wind.spread_distance``，預設 1）。只有 ``element: wind`` 的技能自己的傷害效果可以填；
    2 格的預算較貴（``wind_spread_permille``）。"""
    split_heal: bool | None = None
    """``damage`` 專用（Phase 3D-8a，6.18 B）：聖光雙效——必須搭配 ``affects: all``；敵方依一般命中
    判定受到傷害、友方（含施放者）不擲命中而改為治療同樣的骰值（骰一次）。只能用在 ``aura``、
    ``area`` 骨架的法術技。"""
    skill: str | None = Field(default=None, pattern=SKILL_ID_PATTERN)
    """``grant_skill`` 專用（Phase 3D-8c，6.20）：暫時給目標的技能 ID（``content/skills/``）；必須是
    一般的主動技能（不是傳說、不含改寫規則型原語、不是 ``grant_skill`` 技能；跨檔案檢查）。"""
    hp_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``revive`` 專用（Phase 3D-8b，6.18 C）：被復活的單位站起來時的 HP（最大 HP 的 n‰，至少
    1）。"""
    rounds: int | None = None
    """``delayed_damage`` 專用（Phase 3D-8b，6.18 H）：定時炸彈的倒數輪數（每次環境回合 −1，歸零時
    爆炸）。"""
    radius: int | None = None
    """``delayed_damage`` 專用：爆炸半徑（曼哈頓距離；0 只波及目標自己）。"""
    scope: Literal["target_cell"] | None = None
    """``detonate_runes`` 專用（Phase 3-31，修正規則 ``on_hit_effects`` 與普攻詞條）：
    ``target_cell`` 只引爆被命中目標所在的那 1 格上自己的符文。"""
    on_kill: tuple[EffectSpec, ...] | None = None
    """``damage`` 專用（Phase 3D-8b，6.18 F）：這個傷害效果讓敵人倒下時才結算的效果（1–2 個，類型見
    :data:`ON_KILL_TYPES`，對象一律是施放者）；同一個效果讓一個以上的敵人倒下只結算一次。只有技能
    自己的傷害效果可以用（不能放進賭注分支、失手反噬、``then``）。"""
    effects: tuple[EffectSpec, ...] | None = None
    """``zone`` 專用（Phase 3D-5）：區域結算的效果（1–2 個，只能用 :data:`ZONE_EFFECT_TYPES`，
    不可自帶 ``affects``／``condition``；對象由區域的 ``affects`` 決定）。"""
    condition: ConditionSpec | None = None

    @model_validator(mode="after")
    def _check_yaml_ranges(self) -> EffectSpec:
        """:data:`YAML_RANGED_FIELDS` 的範圍取自 ``skill_primitives.yaml`` 的 ``min``／``max``
        （Phase 3E-2f，唯一來源）；其他整數欄位的細緻範圍由跨檔案驗證（:func:`skill_problems`）
        檢查。不在該檔的效果類型（``refund_ap`` 等）沒有範圍。"""
        for name, spec in _yaml_ranged_params().get(self.type, {}).items():
            value = getattr(self, name, None)
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if (spec.min is not None and value < spec.min) or (
                spec.max is not None and value > spec.max
            ):
                raise ValueError(
                    f"效果 {self.type} 的 {name} 必須在 {spec.min}–{spec.max}，收到 {value}"
                )
        return self

    def param_values(self) -> dict[str, Any]:
        """已填寫的原語參數（不含 ``type``、``affects``、``condition``；欄位清單由
        :data:`EFFECT_PARAM_FIELDS` 從 model 推導，依名稱排序）。"""
        return {n: getattr(self, n) for n in EFFECT_PARAM_FIELDS if getattr(self, n) is not None}


@cache
def _ranged_params_of(path: Path) -> dict[str, dict[str, PrimitiveParam]]:
    if not path.is_file():  # 沒有這個檔的內容資料夾由載入器自己報錯
        return {}
    table = load_content_file(path, PrimitiveTable)
    return {
        p.id: {
            n: s
            for n, s in p.params.items()
            if n in YAML_RANGED_FIELDS
            and s.type == "int"
            and (s.min is not None or s.max is not None)
        }
        for p in table.primitives
    }


def _yaml_ranged_params() -> dict[str, dict[str, PrimitiveParam]]:
    """各原語「範圍只在 YAML」的整數參數（內容資料夾見
    :func:`~trpg.content.loader.default_content_dir`，每個路徑只讀一次）。"""
    return _ranged_params_of(default_content_dir() / "skill_primitives.yaml")


@dataclass(frozen=True, slots=True)
class CompositionRule:
    """一個原語對整招技能的組合規則（Phase 4-L5b；欄位意義見 :class:`PrimitiveDef`）。"""

    primitive: str
    allowed_shapes: tuple[str, ...] | None = None
    position: Literal["first", "last"] | None = None
    sole_effect: bool = False
    others_affect: Literal["self"] | None = None
    max_per_skill: int | None = None
    active_only: bool = False

    @classmethod
    def of(cls, primitive: PrimitiveDef) -> CompositionRule:
        return cls(
            primitive=primitive.id,
            allowed_shapes=primitive.allowed_shapes,
            position=primitive.position,
            sole_effect=primitive.sole_effect,
            others_affect=primitive.others_affect,
            max_per_skill=primitive.max_per_skill,
            active_only=primitive.active_only,
        )

    @property
    def cross_effect(self) -> bool:
        """有牽涉其他效果的規則（位置、唯一效果、其他效果的對象）。"""
        return self.position is not None or self.sole_effect or self.others_affect is not None


@cache
def _composition_of(path: Path) -> dict[str, CompositionRule]:
    if not path.is_file():  # 沒有這個檔的內容資料夾由載入器自己報錯
        return {}
    table = load_content_file(path, PrimitiveTable)
    return {p.id: CompositionRule.of(p) for p in table.primitives}


def composition_rules() -> dict[str, CompositionRule]:
    """各原語的組合規則（``skill_primitives.yaml``，唯一來源；每個路徑只讀一次）。"""
    return _composition_of(default_content_dir() / "skill_primitives.yaml")


@cache
def _true_only_of(path: Path) -> dict[str, frozenset[str]]:
    if not path.is_file():
        return {}
    table = load_content_file(path, PrimitiveTable)
    out = {p.id: frozenset(n for n, s in p.params.items() if s.true_only) for p in table.primitives}
    return {k: v for k, v in out.items() if v}


def true_only_params() -> dict[str, frozenset[str]]:
    """原語 ID → 只能填 ``true`` 的參數名稱（``skill_primitives.yaml`` 的 ``true_only``）。"""
    return _true_only_of(default_content_dir() / "skill_primitives.yaml")


def composition_shapes(primitive: str) -> tuple[str, ...]:
    """原語 YAML 的 ``allowed_shapes``（``SkillDef`` 結構檢查用；沒有限制時為空 tuple）。"""
    rule = composition_rules().get(primitive)
    return () if rule is None or rule.allowed_shapes is None else rule.allowed_shapes


class SkillRuleError(ValueError):
    """``SkillDef`` 結構檢查的錯誤，帶出錯的 JSON 路徑（Phase 4-L5b：給 LLM 的回饋可定位）。

    pydantic 會把它包進 ``value_error``，原本的例外留在錯誤的 ``ctx["error"]``。"""

    def __init__(self, message: str, *, path: str = "", code: str = "") -> None:
        super().__init__(message)
        self.path = path
        self.code = (
            code  # 穩定的錯誤代碼（Phase 4-L5c，例 combo.position）；空字串＝沿用 value_error
        )


def _check_composition(kind: str, effects: tuple[EffectSpec, ...]) -> None:
    """技能頂層效果的組合規則（Phase 4-L5b；資料見 :func:`composition_rules`）：只能用在主動技能、
    每技能數量上限、唯一的效果、第一個／最後一個、其他效果的對象。形狀限制（``allowed_shapes``）
    由各原語自己的檢查與跨檔案驗證處理（:func:`skill_problems`）。"""
    rules = composition_rules()
    types = [e.type for e in effects]
    used = [rules[t] for t in dict.fromkeys(types) if t in rules]
    for rule in used:
        if rule.active_only and kind != "active":
            raise SkillRuleError(
                f"{rule.primitive} 只能用在主動技能，收到 kind: {kind}",
                path="kind",
                code="combo.active_only",
            )
    moves = [t for t in types if t in SELF_MOVES]
    if len(moves) > 1 and any(t != "teleport" for t in moves):  # 跨原語的群組規則（留在程式）
        raise SkillRuleError(
            f"一個技能最多一個改變自身位置的原語，收到 {'、'.join(moves)}",
            path="effects",
            code="combo.max_per_skill",
        )
    for rule in used:
        _check_rule(rule, effects, types)


def _check_rule(rule: CompositionRule, effects: tuple[EffectSpec, ...], types: list[str]) -> None:
    name = rule.primitive
    where = [i for i, t in enumerate(types) if t == name]
    if rule.max_per_skill is not None and len(where) > rule.max_per_skill:
        count = "一個" if rule.max_per_skill == 1 else f" {rule.max_per_skill} 個"
        raise SkillRuleError(
            f"一個技能最多{count} {name} 效果",
            path=f"effects[{where[rule.max_per_skill]}]",
            code="combo.max_per_skill",
        )
    if rule.sole_effect and len(types) != 1:
        raise SkillRuleError(
            f"{name} 必須是技能唯一的效果", path="effects", code="combo.sole_effect"
        )
    if rule.position == "first" and types[0] != name:
        raise SkillRuleError(
            f"{name} 必須是技能的第一個效果（一律最先結算）",
            path=f"effects[{where[0]}]",
            code="combo.position",
        )
    if rule.position == "last" and types[-1] != name:
        raise SkillRuleError(
            f"{name} 必須是技能的最後一個效果（一律最後結算）",
            path=f"effects[{where[-1]}]",
            code="combo.position",
        )
    if rule.others_affect is not None:
        for index, effect in enumerate(effects):
            if effect.type != name and effect.affects != rule.others_affect:
                raise SkillRuleError(
                    f"{name} 以外的效果必須明寫 affects: {rule.others_affect}（只作用在施放者）",
                    path=f"effects[{index}].affects",
                    code="combo.others_affect",
                )


EFFECT_PARAM_FIELDS = tuple(sorted(set(EffectSpec.model_fields) - EFFECT_NON_PARAM_FIELDS))
"""``EffectSpec`` 的原語參數欄位名稱（從 ``model_fields`` 推導）。"""
