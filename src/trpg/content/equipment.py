"""裝備：物品、詞條白名單、裝備規則與單位的裝備快照（Phase 3G-G1）。

設計：``docs/design/08-裝備.md`` 8.21（詞條全景）、8.21.5.2～8.21.5.3（上限與遞減疊加）、
8.23（欄位）、8.24（詞條白名單 v1）。

對應資料檔：

- ``content/affixes.yaml``：詞條白名單（:class:`AffixTable`）。11 類詞條用 ``category`` 區分的
  聯合型別（:data:`AffixDef`）驗證；LLM 之後只能從這裡選 id 並填 ``value``（守則 3）。
- ``content/items.yaml``：物品（:class:`ItemTable`）。物品的基礎數值沿用既有資料：武器類物品引用
  ``weapons.yaml``；其他欄位目前沒有基礎資料，基礎數值為 0（只有詞條）。
- ``content/rules/equipment.yaml``：遞減權重與硬上限（:class:`EquipmentRules`，嵌入規則包）。

單位的裝備在開戰時解析成 :class:`Loadout`（物品 ＋ 詞條定義 ＋ 擲出的數值，**內嵌完整定義**），
放進 ``BattleSetup``，重播不依賴當下的資料檔。數值結算（遞減、上限、各類詞條）在
:mod:`trpg.engine.gear`。

數值單位：``value_unit: permille`` 的數值是千分比（150 ＝ 15%），``flat`` 是整數點數。
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, Dice, OffhandDef, WeaponDef
from trpg.content.schemas import ContentModel
from trpg.content.skills import (
    ON_CAST_TAG,
    ON_ENTER_SURFACE,
    ON_STATUS_APPLIED,
    ON_SUMMON_DOWNED,
    RUNE_BOTH_MESSAGE,
    SACRIFICE_SUMMON,
    ConditionSpec,
    EffectSpec,
    condition_text,
    held_gear,
)
from trpg.content.slots import (
    SLOT_INDEX,
    SLOT_TYPE_OF,
    SLOT_TYPE_ZH,
    SLOT_ZH,
    SLOTS,
    Slot,
    SlotType,
)
from trpg.shared.types import Attribute, Element

__all__ = [
    "AFFIX_CATEGORIES",
    "AFFIX_CATEGORY_NUMBER",
    "AFFIX_CATEGORY_ZH",
    "CHARGE_GAIN_UNSUPPORTED",
    "NUMERIC_CATEGORIES",
    "SELF_EVALUABLE_CONDITIONS",
    "ActionAffix",
    "AffixCategory",
    "AffixDef",
    "AffixRoll",
    "AffixTable",
    "AttackAffix",
    "ChargeAffix",
    "ConditionalAffix",
    "CostAffix",
    "CostPart",
    "EquipmentCaps",
    "EquipmentRules",
    "EquippedAffix",
    "EquippedItem",
    "ItemDef",
    "ItemTable",
    "KeywordAffix",
    "Loadout",
    "ReactionAffix",
    "RuleAffix",
    "StatAffix",
    "TriggerAffix",
    "ValueRange",
    "WeaponTraitAffix",
    "affix_strength",
    "affix_text",
    "item_problems",
    "loadout_held",
    "loadout_problems",
    "resolve_loadout",
    "rune_pair_problems",
]

AFFIX_ID_PATTERN = r"^affix_[a-z0-9_]+$"
SUMMON_CHANGES: frozenset[str] = frozenset(
    {"cooldown_delta", "duration_delta", "sacrifice_permille"}
)
"""技能強化詞條中召喚專用的 ``change``（Phase 3-33f2，6.29.6）。"""
_PERMILLE = 1000

type AffixCategory = Literal[
    "stat",
    "conditional",
    "keyword",
    "attack",
    "weapon_trait",
    "trigger",
    "charge",
    "cost",
    "action",
    "reaction",
    "rule",
]
"""11 類詞條（8.21.1 的順序）。"""

AFFIX_CATEGORIES: tuple[str, ...] = (
    "stat",
    "conditional",
    "keyword",
    "attack",
    "weapon_trait",
    "trigger",
    "charge",
    "cost",
    "action",
    "reaction",
    "rule",
)

AFFIX_CATEGORY_NUMBER: dict[str, int] = {c: i + 1 for i, c in enumerate(AFFIX_CATEGORIES)}
"""類別 → 8.21.1 的編號（1 數值 … 11 改變規則）。"""

AFFIX_CATEGORY_ZH: dict[str, str] = {
    "stat": "數值",
    "conditional": "條件數值",
    "keyword": "技能強化",
    "attack": "普攻附加",
    "weapon_trait": "武器特性強化",
    "trigger": "觸發",
    "charge": "充能",
    "cost": "代價型",
    "action": "動作",
    "reaction": "反應",
    "rule": "改變規則",
}

NUMERIC_CATEGORIES: frozenset[str] = frozenset(
    {"stat", "conditional", "keyword", "weapon_trait", "cost"}
)
"""有「數值部分」的類別（8.21.5.3）：同 id 依 100／50／25／0% 遞減疊加。其餘類別（普攻附加、觸發、
充能、動作、反應、改變規則）是非數值效果，同 id 只生效 1 條。"""

SELF_EVALUABLE_CONDITIONS: frozenset[str] = frozenset(
    {"moved_this_turn", "self_hp_below", "self_concealed"}
)
"""只看持有者自己、不需要戰場與目標就能判斷的條件。作用在持有者 **防禦** 的條件數值只能用這些
（防禦值在命中判定裡計算，那裡只有單位本身）。"""


def _unique(ids: list[str], what: str) -> None:
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    if dup:
        raise ValueError(f"重複的{what}：{', '.join(dup)}")


# ---------------------------------------------------------------------------
# 詞條
# ---------------------------------------------------------------------------


MIN_COMBO_N = 2
"""普攻連擊 ``strike: combo`` 的 N 最小值（至少每 2 次）。"""


class ValueRange(ContentModel):
    """詞條數值 ``N`` 的初值範圍（含兩端）。"""

    min: int
    max: int

    @model_validator(mode="after")
    def _check(self) -> ValueRange:
        if self.min > self.max:
            raise ValueError(f"value.min（{self.min}）不可大於 value.max（{self.max}）")
        if self.min == 0 or self.max == 0 or (self.min < 0 < self.max):
            raise ValueError("value 範圍不可包含 0（詞條數值不能是 0）")
        return self


class _AffixBase(ContentModel):
    """所有詞條共用的欄位。

    - ``name_zh``：玩家看到的文字，``{n}`` 會換成擲出的數值（``permille`` 顯示為百分比）。
    - ``slots``：可出現的物品種類（8.24「可出現的欄位」）。
    - ``weapons``：武器類物品限定這些武器（``weapons.yaml`` 的 id；空 ＝ 不限；其他種類的物品
      不受影響）。
    - ``weapon_class``：武器類物品限定武器大類（例如「武（遠程）、頭」的遠程；其他種類不受影響）。
    - ``item_tags``：依物品種類限定標籤（例如「副（限盾）、身」寫成 ``{offhand: [shield]}``：副手
      必須帶 ``shield`` 標籤，身體不限）。
    - ``legendary_only``：只能出現在傳說物品上（改變規則類）。
    - ``value``：數值 ``N`` 的範圍；``None`` 表示這條詞條沒有可擲的數值（固定效果）。
    """

    id: str = Field(pattern=AFFIX_ID_PATTERN)
    name_zh: str = Field(min_length=1)
    slots: tuple[SlotType, ...] = Field(min_length=1)
    weapons: tuple[str, ...] = ()
    weapon_class: Literal["melee", "ranged", "focus"] | None = None
    item_tags: dict[SlotType, tuple[str, ...]] = Field(default_factory=dict)
    legendary_only: bool = False
    value: ValueRange | None = None
    value_unit: Literal["flat", "permille"] = "flat"

    @model_validator(mode="after")
    def _check_base(self) -> _AffixBase:
        if len(set(self.slots)) != len(self.slots):
            raise ValueError(f"詞條 {self.id}：slots 不可重複")
        has_n = "{n}" in self.name_zh
        if has_n and self.value is None:
            raise ValueError(f"詞條 {self.id}：name_zh 有 {{n}} 但沒有 value 範圍")
        if self.value is not None and not has_n:
            raise ValueError(f"詞條 {self.id}：有 value 範圍時 name_zh 必須含 {{n}}")
        tags = [t for group in self.item_tags.values() for t in group]
        bad = [w for w in (*self.weapons, *tags) if re.match(ID_PATTERN, w) is None]
        if bad:
            raise ValueError(f"詞條 {self.id}：weapons／item_tags 格式錯誤：{', '.join(bad)}")
        return self

    @property
    def category_number(self) -> int:
        return AFFIX_CATEGORY_NUMBER[self.category]  # type: ignore[attr-defined]

    @property
    def numeric(self) -> bool:
        """有數值部分（遞減疊加）；否則同 id 只生效 1 條。"""
        return self.category in NUMERIC_CATEGORIES  # type: ignore[attr-defined]


type StatKind = Literal["attribute", "max_hp", "element_resist", "defense", "move"]


class StatAffix(_AffixBase):
    """第 1 類 數值：無條件的固定加值，合併進總屬性（8.21.2.1）。

    - ``attribute``：屬性 +N（``attribute`` 必填）。
    - ``max_hp``：最大 HP +N。
    - ``element_resist``：單一元素抗性 +N‰（``element`` 必填；上限見 ``EquipmentCaps``）。
    - ``defense``：防禦值 +N‰。
    - ``move``：移動 +N（裝備合計上限見 ``EquipmentCaps``）。
    """

    category: Literal["stat"]
    stat: StatKind
    attribute: Attribute | None = None
    element: Element | None = None

    @model_validator(mode="after")
    def _check(self) -> StatAffix:
        if self.value is None:
            raise ValueError(f"詞條 {self.id}：數值類必須有 value 範圍")
        if (self.stat == "attribute") != (self.attribute is not None):
            raise ValueError(f"詞條 {self.id}：attribute 只在 stat: attribute 時填寫（且必填）")
        if (self.stat == "element_resist") != (self.element is not None):
            raise ValueError(f"詞條 {self.id}：element 只在 stat: element_resist 時填寫（且必填）")
        if self.stat in ("element_resist", "defense") and self.value_unit != "permille":
            raise ValueError(f"詞條 {self.id}：{self.stat} 的 value_unit 必須是 permille")
        return self


type ConditionalEffect = Literal["hit", "damage", "defense"]


class ConditionalAffix(_AffixBase):
    """第 2 類 條件數值：條件成立時才生效（8.21.2.2）。

    - ``effect``：``hit`` 命中 +N、``damage`` 傷害 +N‰（計入全身傷害加成上限）、``defense`` 持有者
      自己的防禦值 +N‰。
    - ``condition``：沿用技能條件（``skill_conditions.yaml``）；持有者是「施放者」，命中與傷害的
      判斷對象是這次攻擊的目標。``negate: true`` 表示條件 **不** 成立時才生效（例如「本回合沒有
      移動」）。
    - ``defense`` 的條件只能是 :data:`SELF_EVALUABLE_CONDITIONS`。
    """

    category: Literal["conditional"]
    effect: ConditionalEffect
    condition: ConditionSpec
    negate: bool = False

    @model_validator(mode="after")
    def _check(self) -> ConditionalAffix:
        if self.value is None:
            raise ValueError(f"詞條 {self.id}：條件數值必須有 value 範圍")
        if self.effect in ("damage", "defense") and self.value_unit != "permille":
            raise ValueError(f"詞條 {self.id}：{self.effect} 的 value_unit 必須是 permille")
        if self.effect == "defense" and self.condition.type not in SELF_EVALUABLE_CONDITIONS:
            allowed = "、".join(sorted(SELF_EVALUABLE_CONDITIONS))
            raise ValueError(f"詞條 {self.id}：防禦類條件數值的條件只能是 {allowed}")
        return self


class KeywordAffix(_AffixBase):
    """第 3 類 技能強化（關鍵字）（8.21.2.3；結算在 G2）。

    - ``keyword``／``direction``：選取「製造」或「利用」該關鍵字的技能（06 6.27.1）；
      ``include_attack``：普攻也算（例如「你施加的燃燒」）。
    - ``change``：``status_duration`` 該狀態持續 +N 回合（``status`` 必填）、``damage_permille``
      傷害 +N‰、``area_delta`` 範圍 +N。
    - 召喚專用（Phase 3-33f2，``keyword`` 必須是 ``summon``）：``cooldown_delta`` 製造召喚物的技能
      冷卻 −1（``direction: create``，``amount`` 為負；冷卻最低 1）、``duration_delta`` 召喚物持續
      +N 輪（``direction: create``，``amount`` 為正）、``sacrifice_permille`` 獻祭召喚物
      （``sacrifice_summon``）的傷害與治療 +N‰（``direction: exploit``，``value_unit: permille``；
      傷害加成計入全身 +50% 上限）。
    - ``amount``：沒有 ``value`` 範圍時的固定數值。
    """

    category: Literal["keyword"]
    keyword: str = Field(pattern=ID_PATTERN)
    direction: Literal["create", "exploit"]
    include_attack: bool = False
    change: Literal[
        "status_duration",
        "damage_permille",
        "area_delta",
        "cooldown_delta",
        "duration_delta",
        "sacrifice_permille",
    ]
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    amount: int | None = None

    @model_validator(mode="after")
    def _check(self) -> KeywordAffix:
        if (self.value is None) == (self.amount is None):
            raise ValueError(f"詞條 {self.id}：value 與 amount 恰好填一個")
        if (self.change == "status_duration") != (self.status is not None):
            raise ValueError(
                f"詞條 {self.id}：status 只在 change: status_duration 時填寫（且必填）"
            )
        self._check_summon()
        return self

    def _check_summon(self) -> None:
        """召喚專用的 ``change``（3-33f2）：關鍵字必須是 ``summon``，方向、正負與單位固定。"""
        if self.change not in SUMMON_CHANGES:
            return
        direction = "exploit" if self.change == "sacrifice_permille" else "create"
        if self.keyword != "summon" or self.direction != direction:
            raise ValueError(
                f"詞條 {self.id}：{self.change} 只能用在 keyword: summon、direction: {direction}"
            )
        if self.change == "cooldown_delta" and (self.amount is None or self.amount >= 0):
            raise ValueError(f"詞條 {self.id}：cooldown_delta 的 amount 必須是負數（冷卻減少）")
        if self.change == "duration_delta" and (self.amount is None or self.amount <= 0):
            raise ValueError(f"詞條 {self.id}：duration_delta 的 amount 必須是正數")
        if self.change == "sacrifice_permille" and (
            self.value is None or self.value_unit != "permille"
        ):
            raise ValueError(
                f"詞條 {self.id}：sacrifice_permille 必須用 value（value_unit: permille）"
            )


class AttackAffix(_AffixBase):
    """第 4 類 普攻附加（8.21.2.4；結算在 G2）：``add_element`` 普攻帶元素（法杖等已有元素的
    武器不能掛），或 ``on_hit_status`` 普攻命中時施加狀態 ``status_duration`` 回合，或 ``rune``
    （Phase 3-31，6.25 普攻與符文；三者恰好填一個）：

    - ``read``：普攻打到站在自己符文上的敵人時，傷害 +``value``‰（計入全身 +50% 上限）；
    - ``detonate``：普攻命中時引爆目標那 1 格上自己的符文，造成一次 ``dice`` 的傷害；
    - ``inscribe``：普攻命中時在目標格刻下 ``rune_element``（預設雷紋）的符文，持續
      ``rune_rounds`` 輪（預設 2）。

    ``summon_inherit``（Phase 3-33f2，6.29.6；與其他恰好填一個）：你的召喚物繼承你身上 1 條普攻
    附加詞條（元素、命中附帶狀態、連擊、分裂；符文不繼承；依詞條 ID 取第一條），本身沒有其他效果。

    三種都 **每回合最多觸發 1 次**；同一件裝備不能同時有 ``inscribe`` 與 ``detonate``。

    ``strike``（Phase 3-32a，08 8.25 普攻流；與上面三者恰好填一個）：

    - ``combo``：每第 ``value``（N＝2～3）次普攻命中，多攻擊一次（``strike_permille`` 的傷害，
      要重新擲命中；不花 AP、不用子彈），每回合最多 1 次；
    - ``cleave``：普攻命中後，對目標相鄰的另一個敵人造成 ``strike_permille`` 的傷害（自動命中；
      多個時取 HP 最低、再依座標），每回合最多 1 次。
    """

    category: Literal["attack"]
    add_element: Element | None = None
    on_hit_status: str | None = Field(default=None, pattern=ID_PATTERN)
    status_duration: int | None = Field(default=None, ge=1)
    rune: Literal["read", "detonate", "inscribe"] | None = None
    dice: Dice | None = None
    rune_element: Element | None = None
    rune_rounds: int | None = Field(default=None, ge=1, le=5)
    strike: Literal["combo", "cleave"] | None = None
    strike_permille: int | None = Field(default=None, ge=100, le=1000)
    summon_inherit: bool = False

    @model_validator(mode="after")
    def _check(self) -> AttackAffix:
        given = [
            self.add_element is not None,
            self.on_hit_status is not None,
            self.rune is not None,
            self.strike is not None,
            self.summon_inherit,
        ]
        if sum(given) != 1:
            raise ValueError(
                f"詞條 {self.id}：add_element、on_hit_status、rune、strike、"
                "summon_inherit 恰好填一個"
            )
        self._check_strike()
        if self.add_element is Element.PHYSICAL:
            raise ValueError(f"詞條 {self.id}：add_element 不可是物理")
        if (self.on_hit_status is None) != (self.status_duration is None):
            raise ValueError(f"詞條 {self.id}：on_hit_status 與 status_duration 要一起填")
        self._check_rune()
        return self

    def _check_strike(self) -> None:
        if self.strike is None:
            if self.strike_permille is not None:
                raise ValueError(f"詞條 {self.id}：strike_permille 只能搭配 strike")
            return
        if self.strike_permille is None:
            raise ValueError(f"詞條 {self.id}：strike 必須填 strike_permille")
        if (self.strike == "combo") != (self.value is not None):
            raise ValueError(f"詞條 {self.id}：value（N）只在 strike: combo 時填寫（且必填）")
        if self.strike == "combo" and (
            self.value_unit != "flat" or self.value is None or self.value.min < MIN_COMBO_N
        ):
            raise ValueError(f"詞條 {self.id}：combo 的 N 至少 2，value_unit 必須是 flat")

    def _check_rune(self) -> None:
        if self.rune is None:
            if self.dice is not None or self.rune_element is not None or self.rune_rounds:
                raise ValueError(f"詞條 {self.id}：dice、rune_element、rune_rounds 只能搭配 rune")
            return
        if (self.rune == "read") != (self.value is not None):
            raise ValueError(f"詞條 {self.id}：value 只在 rune: read 時填寫（且必填）")
        if self.rune == "read" and self.value_unit != "permille":
            raise ValueError(f"詞條 {self.id}：讀取符文的 value_unit 必須是 permille")
        if (self.rune == "detonate") != (self.dice is not None):
            raise ValueError(f"詞條 {self.id}：dice 只在 rune: detonate 時填寫（且必填）")
        if self.rune != "inscribe" and (self.rune_element is not None or self.rune_rounds):
            raise ValueError(f"詞條 {self.id}：rune_element、rune_rounds 只能搭配 rune: inscribe")
        if self.rune_element is Element.PHYSICAL:
            raise ValueError(f"詞條 {self.id}：rune_element 不可是物理")


class WeaponTraitAffix(_AffixBase):
    """第 5 類 武器特性強化（8.21.2.5；結算在 G2）：改武器資料的參數 ``param``（例如
    ``knockback``、``armor_break.rounds``）——``delta`` 加減，或 ``scale_permille`` 倍率
    （例如貼臉懲罰減半 ＝ 500）。``weapons`` 必填（只出現在對應武器上）。"""

    category: Literal["weapon_trait"]
    param: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?$")
    delta: int | None = None
    scale_permille: int | None = Field(default=None, ge=0, le=2000)

    @model_validator(mode="after")
    def _check(self) -> WeaponTraitAffix:
        if not self.weapons:
            raise ValueError(f"詞條 {self.id}：武器特性強化必須限定 weapons")
        if (self.delta is None) == (self.scale_permille is None):
            raise ValueError(f"詞條 {self.id}：delta 與 scale_permille 恰好填一個")
        return self


class TriggerAffix(_AffixBase):
    """第 6 類 觸發（8.21.2.6；Phase 3G-G3a）：觸發時機 ``trigger``（``skill_triggers.yaml``）時對
    ``effect_target`` 結算 ``effects``；``limit`` 每回合／每輪最多 1 次。``melee_only``：只有近戰
    造成的才算（``on_damaged``）。``tag``／``status``／``surface`` 是帶參數的時機（同被動技能的
    ``trigger``）。"""

    category: Literal["trigger"]
    trigger: str = Field(pattern=ID_PATTERN)
    n: int | None = Field(default=None, ge=2, le=10)
    melee_only: bool = False
    effect_target: Literal["target", "self", "attacker"] = "target"
    effects: tuple[EffectSpec, ...] = Field(min_length=1, max_length=2)
    limit: Literal["per_turn", "per_round"] = "per_turn"
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    surface: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _check(self) -> TriggerAffix:
        if (self.trigger == "every_n_hits") != (self.n is not None):
            raise ValueError(f"詞條 {self.id}：n 只在 trigger: every_n_hits 時填寫（且必填）")
        if self.melee_only and self.trigger != "on_damaged":
            raise ValueError(f"詞條 {self.id}：melee_only 只能搭配 trigger: on_damaged")
        if (self.trigger == ON_CAST_TAG) != (self.tag is not None):
            raise ValueError(f"詞條 {self.id}：tag 只在 trigger: on_cast_tag 時填寫（且必填）")
        if self.status is not None and self.trigger != ON_STATUS_APPLIED:
            raise ValueError(f"詞條 {self.id}：status 只能搭配 trigger: on_status_applied")
        if self.surface is not None and self.trigger != ON_ENTER_SURFACE:
            raise ValueError(f"詞條 {self.id}：surface 只能搭配 trigger: on_enter_surface")
        self._check_summon_downed()
        return self

    def _check_summon_downed(self) -> None:
        """``on_summon_downed``（3-33f2）：效果是恰好 1 個 ``sacrifice_summon``（有 ``element``
        是爆炸、省略是治療），以倒下的召喚物為中心結算（``effect_target: target``）；其他時機
        不可用。"""
        uses = [e for e in self.effects if e.type == SACRIFICE_SUMMON]
        if self.trigger != ON_SUMMON_DOWNED:
            if uses:
                raise ValueError(
                    f"詞條 {self.id}：sacrifice_summon 只能搭配 trigger: on_summon_downed"
                )
            return
        if self.effect_target != "target" or len(self.effects) != 1 or len(uses) != 1:
            raise ValueError(
                f"詞條 {self.id}：on_summon_downed 必須是 effect_target: target "
                "與恰好 1 個 sacrifice_summon"
            )


CHARGE_GAIN_UNSUPPORTED: frozenset[str] = frozenset(
    {"every_n_hits", ON_CAST_TAG, ON_STATUS_APPLIED, ON_ENTER_SURFACE}
)
"""充能不能用來累積層數的觸發時機（需要參數：次數、標籤、狀態、表面）。"""


class ChargeAffix(_AffixBase):
    """第 7 類 充能（8.21.2.7；Phase 3G-G3a）：``gain_trigger`` 時累積 ``stack``（裝備版上限
    ``max_stacks``）；花 ``cost_stacks`` 層 ＋ ``cost_ap`` AP 啟動 ``effects``（行動面板的
    「更多動作」）。
    ``effect_target``：``target``＝啟動時選一個武器射程內的敵人；``self``＝作用在自己。"""

    category: Literal["charge"]
    stack: str = Field(pattern=ID_PATTERN)
    max_stacks: int = Field(ge=1, le=10)
    gain_trigger: str = Field(pattern=ID_PATTERN)
    cost_stacks: int = Field(ge=1)
    cost_ap: int = Field(ge=0, le=3)
    effects: tuple[EffectSpec, ...] = Field(min_length=1, max_length=2)
    effect_target: Literal["target", "self"] = "target"

    @model_validator(mode="after")
    def _check(self) -> ChargeAffix:
        if self.cost_stacks > self.max_stacks:
            raise ValueError(f"詞條 {self.id}：cost_stacks 不可超過 max_stacks")
        if self.gain_trigger in CHARGE_GAIN_UNSUPPORTED:
            raise ValueError(f"詞條 {self.id}：充能不能用需要參數的時機 {self.gain_trigger} 累積")
        return self


type CostStat = Literal[
    "damage_permille",
    "damage_taken_permille",
    "move",
    "defense_permille",
    "cooldown_delta",
    "turn_start_hp_loss",
    "hit",
]

_COST_BENEFIT_SIGN: dict[str, int] = {
    "damage_permille": 1,
    "damage_taken_permille": -1,
    "move": 1,
    "defense_permille": 1,
    "cooldown_delta": -1,
    "turn_start_hp_loss": -1,
    "hit": 1,
}
"""代價型各數值「對持有者有利」的方向（+1：越大越好；−1：越小越好）。"""


class CostPart(ContentModel):
    """代價型詞條的一個數值部分。

    - ``damage_permille``：造成的傷害 ±‰（計入全身傷害加成上限）。
    - ``damage_taken_permille``：受到的骰值傷害 ±‰。
    - ``move``：移動 ±（計入裝備移動加成上限）。
    - ``defense_permille``：防禦值 ±‰。
    - ``cooldown_delta``：施放技能時設定的冷卻 ±（結果不低於冷卻下限）。
    - ``turn_start_hp_loss``：回合開始時失去這麼多 HP（不會致死，最低剩 1）。
    - ``hit``：命中 ±。
    """

    stat: CostStat
    amount: int

    @field_validator("amount")
    @classmethod
    def _nonzero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount 不可為 0")
        return value

    @property
    def beneficial(self) -> bool:
        return self.amount * _COST_BENEFIT_SIGN[self.stat] > 0


class CostAffix(_AffixBase):
    """第 8 類 代價型（8.21.2.8）：``upside`` 必須全部對持有者有利、``downside`` 全部不利；
    全身最多 ``EquipmentCaps.cost_affixes`` 條（超過時穿戴驗證失敗）。"""

    category: Literal["cost"]
    upside: tuple[CostPart, ...] = Field(min_length=1, max_length=2)
    downside: tuple[CostPart, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def _check(self) -> CostAffix:
        if self.value is not None:
            raise ValueError(f"詞條 {self.id}：代價型的數值寫在 upside／downside，不用 value")
        if not all(p.beneficial for p in self.upside):
            raise ValueError(f"詞條 {self.id}：upside 必須全部是有利的數值")
        if any(p.beneficial for p in self.downside):
            raise ValueError(f"詞條 {self.id}：downside 必須全部是不利的數值")
        return self

    @property
    def parts(self) -> tuple[CostPart, ...]:
        return (*self.upside, *self.downside)


class ActionAffix(_AffixBase):
    """第 9 類 授予動作（8.21.2.9；結算在 G3）：裝備授予常駐技能 ``skill``（卸下即失去）。"""

    category: Literal["action"]
    skill: str = Field(pattern=r"^skill_[a-z0-9_]+$")


class ReactionAffix(_AffixBase):
    """第 10 類 授予反應（8.21.2.10；結算在 G3）。

    - ``extend_trigger``：既有反應 ``reaction`` 多一個觸發事件 ``event``（例如遠程也可格擋）。
    - ``grant``：授予反應 ``reaction``（例如 ``redirect_damage``：``range`` 格內的隊友被攻擊時替他
      承受）。
    - ``extra_uses``：反應 ``reaction`` 每輪可多觸發 ``uses`` 次。
    """

    category: Literal["reaction"]
    mode: Literal["extend_trigger", "grant", "extra_uses"]
    reaction: str = Field(pattern=ID_PATTERN)
    event: str | None = Field(default=None, pattern=ID_PATTERN)
    range: int | None = Field(default=None, ge=1, le=4)
    uses: int | None = Field(default=None, ge=1, le=2)
    limit: Literal["per_round"] | None = None

    @model_validator(mode="after")
    def _check(self) -> ReactionAffix:
        if (self.mode == "extend_trigger") != (self.event is not None):
            raise ValueError(f"詞條 {self.id}：event 只在 mode: extend_trigger 時填寫（且必填）")
        if (self.mode == "extra_uses") != (self.uses is not None):
            raise ValueError(f"詞條 {self.id}：uses 只在 mode: extra_uses 時填寫（且必填）")
        return self


class RuleAffix(_AffixBase):
    """第 11 類 改變規則（8.21.2.11；結算在 G3）：``rule_changes.yaml`` 的一條規則，只作用在持有者
    （或持有者造成的效果）；只出現在傳說物品上。"""

    category: Literal["rule"]
    rule: str = Field(pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _check(self) -> RuleAffix:
        if not self.legendary_only:
            raise ValueError(f"詞條 {self.id}：改變規則類必須 legendary_only: true")
        return self


type AffixDef = Annotated[
    StatAffix
    | ConditionalAffix
    | KeywordAffix
    | AttackAffix
    | WeaponTraitAffix
    | TriggerAffix
    | ChargeAffix
    | CostAffix
    | ActionAffix
    | ReactionAffix
    | RuleAffix,
    Field(discriminator="category"),
]
"""一條詞條（依 ``category`` 區分的聯合型別）。"""


class AffixTable(ContentModel):
    """``content/affixes.yaml``：詞條白名單。"""

    affixes: tuple[AffixDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> AffixTable:
        _unique([a.id for a in self.affixes], "詞條 ID")
        return self

    def by_id(self) -> dict[str, AffixDef]:
        return {a.id: a for a in self.affixes}

    def summary(self) -> str:
        counts = Counter(a.category for a in self.affixes)
        return f"{len(self.affixes)} 條詞條（{len(counts)} 類）"


def _format_value(value: int, unit: str) -> str:
    if unit == "permille":
        return f"{value / 10:g}%"
    return str(value)


def affix_text(affix: AffixDef, value: int | None) -> str:
    """詞條的玩家文字（``{n}`` 換成數值；條件已寫在 ``name_zh`` 裡）。"""
    text = affix.name_zh
    if value is not None:
        text = text.replace("{n}", _format_value(value, affix.value_unit))
    return text


def affix_strength(affix: AffixDef, value: int | None) -> int:
    """同 id 詞條比強弱用的數值（越大越強；重複詞條只生效最強的 1 條，08 8.21.5.3）：一般是擲出的
    數值；普攻連擊 ``combo`` 的 N 越小觸發越頻繁，所以取負數。"""
    amount = value or 0
    if isinstance(affix, AttackAffix) and affix.strike == "combo":
        return -amount
    return amount


def condition_zh(affix: ConditionalAffix) -> str:
    """條件數值的條件文字（顯示用）。"""
    text = condition_text(affix.condition)
    return f"不是「{text}」" if affix.negate else text


# ---------------------------------------------------------------------------
# 物品
# ---------------------------------------------------------------------------


class AffixRoll(ContentModel):
    """物品上的一條詞條：白名單 id ＋ 擲出的數值（詞條沒有 ``value`` 範圍時不填）。"""

    affix: str = Field(pattern=AFFIX_ID_PATTERN)
    value: int | None = None


class ItemDef(ContentModel):
    """一件物品（``content/items.yaml``）。

    - ``slot_type``：物品種類，決定能放的欄位（8.23）。
    - ``weapon``：武器類物品（``slot_type: weapon``）引用 ``weapons.yaml``，基礎數值沿用武器資料；
      其他種類不可填。
    - ``offhand``：副手類物品（``slot_type: offhand``）引用 ``offhands.yaml``（圓盾、塔盾、法書、
      法器珠；Phase 3I-2）；``offhand_def`` 是載入時嵌進去的定義（資料檔不要寫），讓裝備快照與戰鬥
      紀錄自成一體。沒有 ``offhand`` 的副手物品只有詞條，沒有副手基礎特性。
    - ``paired``：成對武器（雙匕首、雙手槍）：和雙手武器一樣占用副手。
    - ``tags``：物品標籤（例如盾 ``shield``，給「限盾」的詞條用）。
    - ``legendary``：傳說物品（可掛改變規則類詞條）。
    - ``affixes``：1～``EquipmentRules.max_affixes_per_item`` 條（同一件不可重複同一 id）。
    - 外觀（Phase 3G-G5a，只影響圖示，不影響任何規則；清單在
      ``content/equipment/appearance.yaml``，見 :mod:`trpg.content.appearance`）：
      ``kind`` 造型、``form`` 形制、``material`` 材質、
      ``dye`` 染色、``style`` 風格、``rarity`` 稀有度。全部選填；不認得的值由前端退回預設。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    slot_type: SlotType
    weapon: str | None = Field(default=None, pattern=ID_PATTERN)
    offhand: str | None = Field(default=None, pattern=ID_PATTERN)
    offhand_def: OffhandDef | None = None
    paired: bool = False
    tags: tuple[str, ...] = ()
    legendary: bool = False
    affixes: tuple[AffixRoll, ...] = Field(default=(), max_length=8)
    kind: str | None = Field(default=None, pattern=ID_PATTERN)
    form: str | None = Field(default=None, pattern=ID_PATTERN)
    material: str | None = Field(default=None, pattern=ID_PATTERN)
    dye: str | None = Field(default=None, pattern=ID_PATTERN)
    style: str | None = Field(default=None, pattern=ID_PATTERN)
    rarity: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _check(self) -> ItemDef:
        if (self.slot_type == "weapon") != (self.weapon is not None):
            raise ValueError(f"物品 {self.id}：weapon 只在 slot_type: weapon 時填寫（且必填）")
        if self.offhand is not None and self.slot_type != "offhand":
            raise ValueError(f"物品 {self.id}：只有副手類物品能填 offhand")
        if self.offhand_def is not None and self.offhand_def.id != self.offhand:
            raise ValueError(f"物品 {self.id}：offhand_def 必須是 offhand（{self.offhand}）的定義")
        if self.paired and self.slot_type != "weapon":
            raise ValueError(f"物品 {self.id}：只有武器能是成對武器（paired）")
        _unique([r.affix for r in self.affixes], f"物品 {self.id} 的詞條")
        bad = [t for t in self.tags if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"物品 {self.id}：標籤格式錯誤：{', '.join(bad)}")
        return self


class ItemTable(ContentModel):
    """``content/items.yaml``。"""

    items: tuple[ItemDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ItemTable:
        _unique([i.id for i in self.items], "物品 ID")
        return self

    def by_id(self) -> dict[str, ItemDef]:
        return {i.id: i for i in self.items}

    def summary(self) -> str:
        return f"{len(self.items)} 件物品"


# ---------------------------------------------------------------------------
# 裝備規則（遞減與硬上限）
# ---------------------------------------------------------------------------


class EquipmentCaps(ContentModel):
    """硬上限（8.21.5.3）。先遞減、再套上限。

    - ``damage_bonus_permille``：全身傷害加成（裝備來源合計）上限 ＋50%。
    - ``damage_reduction_permille``：總減傷上限 75%（＝ 1000 − ``core.element_mod_floor_permille``，
      由既有的元素修正下限執行；載入時檢查兩者一致）。
    - ``element_resist_permille``：單一元素抗性上限 50%（裝備不能把抗性推過這個值；範本本身更高的
      抗性不受影響）。
    - ``ap_gain_per_round``：每回合 AP 回復（所有來源合計）＋1（G3 的擊殺回 AP 接上）。
    - ``cooldown_min``：冷卻最低 1（冷卻本來就是 0 的技能不受影響）。
    - ``crit_range_min``：暴擊範圍最低 18（自然 18～20；G2 的武器特性與技能強化接上）。
    - ``move_bonus``：裝備的移動加成合計 ＋2。
    - ``cost_affixes``：代價型詞條全身最多 2 條（超過時穿戴驗證失敗）。
    - ``rule_affixes``：改變規則類詞條全身最多 1 條（同時生效的規則改變最多 1 個；超過時穿戴驗證
      失敗；同一條詞條 id 掛在兩件物品上只算 1 條）。
    - 觸發連鎖沿用 ``core.max_trigger_depth``（G3）。
    """

    damage_bonus_permille: int = Field(default=500, ge=0)
    damage_reduction_permille: int = Field(default=750, ge=0, le=1000)
    element_resist_permille: int = Field(default=500, ge=0, le=1000)
    ap_gain_per_round: int = Field(default=1, ge=0)
    cooldown_min: int = Field(default=1, ge=0)
    crit_range_min: int = Field(default=18, ge=2, le=20)
    move_bonus: int = Field(default=2, ge=0)
    cost_affixes: int = Field(default=2, ge=0)
    rule_affixes: int = Field(default=1, ge=0)


class EquipmentRules(ContentModel):
    """``content/rules/equipment.yaml``（嵌入規則包）。

    - ``diminishing_permille``：同 id 數值詞條依大到小的權重（第 1 條 1000‰、第 2 條 500‰、第 3 條
      250‰，之後 0）；加總後無條件捨去（往 0 的方向）。
    - ``max_affixes_per_item``：每件物品的詞條上限。
    """

    diminishing_permille: tuple[int, ...] = Field(default=(1000, 500, 250), min_length=1)
    max_affixes_per_item: int = Field(default=4, ge=1, le=8)
    caps: EquipmentCaps = EquipmentCaps()

    @model_validator(mode="after")
    def _check(self) -> EquipmentRules:
        weights = self.diminishing_permille
        if weights[0] != _PERMILLE or any(b > a for a, b in pairwise(weights)):
            raise ValueError("diminishing_permille 必須從 1000 開始、不遞增")
        if any(w < 0 for w in weights):
            raise ValueError("diminishing_permille 不可為負")
        return self

    def weight(self, rank: int) -> int:
        """第 ``rank`` 條（0 起算）的遞減權重（‰）。"""
        weights = self.diminishing_permille
        return weights[rank] if rank < len(weights) else 0


# ---------------------------------------------------------------------------
# 裝備快照（BattleSetup 用）
# ---------------------------------------------------------------------------


class EquippedAffix(ContentModel):
    """快照裡的一條詞條：完整定義 ＋ 擲出的數值。"""

    affix: AffixDef
    value: int | None = None

    @property
    def text_zh(self) -> str:
        return affix_text(self.affix, self.value)


class EquippedItem(ContentModel):
    """快照裡的一個欄位：欄位、物品（完整定義）與解析後的詞條。"""

    slot: Slot
    item: ItemDef
    affixes: tuple[EquippedAffix, ...] = ()


class Loadout(ContentModel):
    """一個單位的裝備快照（依欄位固定順序；空 ＝ 沒有裝備）。主手沒有物品時，單位的武器（舊的
    ``weapon``）視為主手的基礎武器。"""

    items: tuple[EquippedItem, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> Loadout:
        _unique([e.slot for e in self.items], "裝備欄位")
        order = [SLOT_INDEX[e.slot] for e in self.items]
        if order != sorted(order):
            raise ValueError("裝備快照必須依欄位固定順序排列")
        return self

    def by_slot(self) -> dict[str, EquippedItem]:
        return {e.slot: e for e in self.items}

    def item_in(self, slot: str) -> EquippedItem | None:
        return self.by_slot().get(slot)

    def offhand_def(self) -> OffhandDef | None:
        """副手欄的副手定義（沒有副手物品或物品沒有副手基礎特性時為 ``None``）。"""
        off = self.item_in("off_hand")
        return None if off is None else off.item.offhand_def


def loadout_held(weapon: WeaponDef, loadout: Loadout | None) -> dict[str, str]:
    """單位手上的主手武器與副手（ID → 中文名，Phase 3I-5），給技能的限定武器檢查用。"""
    offhand = None if loadout is None else loadout.offhand_def()
    return held_gear(weapon, offhand)


_WEAPON_CLASS_ZH = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器"}
_ITEM_TAG_ZH = {"shield": "盾"}


def _affix_slot_problems(
    item: ItemDef,
    affix: AffixDef,
    weapon: WeaponDef | None,
    weapons: Mapping[str, WeaponDef] | None = None,
) -> list[str]:
    """詞條能不能掛在這件物品上（種類、限定武器、標籤、傳說、法杖元素）。"""
    where = f"物品 {item.id} 的詞條 {affix.id}"
    problems: list[str] = []
    if item.slot_type not in affix.slots:
        allowed = "、".join(SLOT_TYPE_ZH[s] for s in affix.slots)
        problems.append(f"{where} 不能出現在{SLOT_TYPE_ZH[item.slot_type]}（可用：{allowed}）")
    is_weapon = item.slot_type == "weapon"
    if is_weapon and affix.weapons and item.weapon not in affix.weapons:
        names = "、".join(
            w.name_zh if (w := (weapons or {}).get(i)) is not None else i for i in affix.weapons
        )
        problems.append(f"{where} 只能出現在 {names} 上")
    if (
        is_weapon
        and affix.weapon_class is not None
        and weapon is not None
        and weapon.weapon_class != affix.weapon_class
    ):
        class_zh = _WEAPON_CLASS_ZH.get(affix.weapon_class, affix.weapon_class)
        problems.append(f"{where} 只能出現在{class_zh}上")
    needed = affix.item_tags.get(item.slot_type, ())
    if needed and not set(needed) & set(item.tags):
        tags = "、".join(_ITEM_TAG_ZH.get(t, t) for t in needed)
        problems.append(f"{where} 需要物品標籤：{tags}")
    if affix.legendary_only and not item.legendary:
        problems.append(f"{where} 只能出現在傳說物品上")
    if (
        isinstance(affix, AttackAffix)
        and affix.add_element is not None
        and weapon is not None
        and weapon.element is not Element.PHYSICAL
    ):
        problems.append(f"{where}：{weapon.name_zh} 已有元素，不能再加普攻元素")
    return problems


def rune_pair_problems(name: str, affixes: Iterable[AffixDef]) -> list[str]:
    """同一件裝備不能同時有「刻」與「引爆」的普攻符文詞條（Phase 3-31，6.25）。"""
    runes = {a.rune for a in affixes if isinstance(a, AttackAffix) and a.rune is not None}
    if {"inscribe", "detonate"} <= runes:
        return [f"{name}：{RUNE_BOTH_MESSAGE}"]
    return []


def item_problems(
    item: ItemDef,
    affixes: Mapping[str, AffixDef],
    weapons: Mapping[str, WeaponDef],
    rules: EquipmentRules,
    offhands: Mapping[str, OffhandDef] | None = None,
) -> list[str]:
    """物品本身的問題（跨檔案：詞條存在、可掛、數值在範圍內、條數上限、武器與副手存在）。"""
    problems: list[str] = []
    if item.offhand is not None and offhands is not None and item.offhand not in offhands:
        problems.append(f"物品 {item.id}：未知的副手 {item.offhand}")
    weapon: WeaponDef | None = None
    if item.weapon is not None:
        weapon = weapons.get(item.weapon)
        if weapon is None:
            problems.append(f"物品 {item.id}：未知的武器 {item.weapon}")
    if len(item.affixes) > rules.max_affixes_per_item:
        problems.append(
            f"物品 {item.id}：詞條最多 {rules.max_affixes_per_item} 條（有 {len(item.affixes)} 條）"
        )
    for roll in item.affixes:
        affix = affixes.get(roll.affix)
        if affix is None:
            problems.append(f"物品 {item.id}：未知的詞條 {roll.affix}（不在白名單）")
            continue
        problems += _affix_slot_problems(item, affix, weapon, weapons)
        problems += _value_problems(item, affix, roll.value)
    known = [a for roll in item.affixes if (a := affixes.get(roll.affix)) is not None]
    return problems + rune_pair_problems(f"物品 {item.id}", known)


def _value_problems(item: ItemDef, affix: AffixDef, value: int | None) -> list[str]:
    where = f"物品 {item.id} 的詞條 {affix.id}"
    if affix.value is None:
        return [] if value is None else [f"{where} 沒有數值，不可填 value"]
    if value is None:
        return [f"{where} 需要 value（{affix.value.min}～{affix.value.max}）"]
    if not affix.value.min <= value <= affix.value.max:
        return [f"{where} 的 value {value} 超出範圍 {affix.value.min}～{affix.value.max}"]
    return []


def resolve_loadout(
    equipment: Mapping[Slot, str] | Mapping[str, str],
    items: Mapping[str, ItemDef],
    affixes: Mapping[str, AffixDef],
) -> Loadout:
    """把「欄位 → 物品 id」解析成 :class:`Loadout` 快照（內嵌物品與詞條定義）。未知的欄位、物品或
    詞條拋出 :class:`ValueError`；合法性（占用、種類、代價型條數）由 :func:`loadout_problems`
    檢查。"""
    entries: list[EquippedItem] = []
    for slot in SLOTS:
        item_id = equipment.get(slot)
        if item_id is None:
            continue
        item = items.get(item_id)
        if item is None:
            raise ValueError(f"欄位 {slot}：未知的物品 {item_id}")
        rolled: list[EquippedAffix] = []
        for roll in item.affixes:
            affix = affixes.get(roll.affix)
            if affix is None:
                raise ValueError(f"物品 {item_id}：未知的詞條 {roll.affix}")
            rolled.append(EquippedAffix(affix=affix, value=roll.value))
        entries.append(EquippedItem(slot=slot, item=item, affixes=tuple(rolled)))
    unknown = sorted(set(equipment) - set(SLOTS))
    if unknown:
        raise ValueError(f"未知的裝備欄位：{', '.join(unknown)}")
    return Loadout(items=tuple(entries))


def loadout_problems(loadout: Loadout, weapon: WeaponDef, rules: EquipmentRules) -> list[str]:
    """穿戴的合法性（8.23、8.21.5.2）：

    - 物品種類符合欄位（``slot_type``）；副手不能放第二把武器。
    - 主手物品的武器必須是單位的武器（``weapon``，舊資料的主手）。
    - 雙手武器與成對武器占用副手（副手必須空著）。
    - 同一枚戒指不能裝兩次（``ring_1`` 與 ``ring_2`` 不可是同一個物品 id）。
    - 代價型詞條全身最多 ``caps.cost_affixes`` 條；改變規則類詞條全身最多 ``caps.rule_affixes``
      個（不同的詞條 id）。
    - 每件物品的詞條可以掛在這件物品上（:func:`_affix_slot_problems`）、數值在範圍內。
    """
    problems: list[str] = []
    by_slot = loadout.by_slot()
    for entry in loadout.items:
        item = entry.item
        expected = SLOT_TYPE_OF[entry.slot]
        if item.slot_type != expected:
            if entry.slot == "off_hand" and item.slot_type == "weapon":
                problems.append(f"副手不能放第二把武器：{item.name_zh}")
            else:
                problems.append(
                    f"{SLOT_ZH[entry.slot]}只能放{SLOT_TYPE_ZH[expected]}類物品：{item.name_zh}"
                    f"（{SLOT_TYPE_ZH[item.slot_type]}）"
                )
        main_weapon = weapon if entry.slot == "main_hand" else None
        for equipped in entry.affixes:
            problems += _affix_slot_problems(item, equipped.affix, main_weapon)
            problems += _value_problems(item, equipped.affix, equipped.value)
        if len(entry.affixes) > rules.max_affixes_per_item:
            problems.append(f"{item.name_zh}：詞條最多 {rules.max_affixes_per_item} 條")
        problems += rune_pair_problems(item.name_zh, (e.affix for e in entry.affixes))
    main = by_slot.get("main_hand")
    if main is not None and main.item.weapon is not None and main.item.weapon != weapon.id:
        problems.append(
            f"主手物品 {main.item.name_zh} 的武器（{main.item.weapon}）必須和單位的武器"
            f"（{weapon.id}）相同"
        )
    paired = weapon.paired or (main is not None and main.item.paired)
    if paired and weapon.two_handed:
        problems.append(f"雙手武器（{weapon.name_zh}）不能是成對武器")
    if (weapon.two_handed or paired) and "off_hand" in by_slot:
        kind = "成對武器" if paired and not weapon.two_handed else "雙手武器"
        blocked = by_slot["off_hand"].item.name_zh
        problems.append(f"主手是{kind}（{weapon.name_zh}），副手被占用，不能放 {blocked}")
    ring_1, ring_2 = by_slot.get("ring_1"), by_slot.get("ring_2")
    if ring_1 is not None and ring_2 is not None and ring_1.item.id == ring_2.item.id:
        problems.append(f"同一枚戒指不能裝兩次：{ring_1.item.name_zh}")
    costs = sum(1 for e in loadout.items for a in e.affixes if a.affix.category == "cost")
    if costs > rules.caps.cost_affixes:
        problems.append(f"代價型詞條全身最多 {rules.caps.cost_affixes} 條（目前 {costs} 條）")
    rule_ids = {a.affix.id for e in loadout.items for a in e.affixes if a.affix.category == "rule"}
    if len(rule_ids) > rules.caps.rule_affixes:
        problems.append(
            f"改變規則類詞條全身最多 {rules.caps.rule_affixes} 個（目前 {len(rule_ids)} 個）"
        )
    return problems
