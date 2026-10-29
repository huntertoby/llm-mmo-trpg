"""形態（Phase 3J-1a，``docs/design/06-技能.md`` 6.30）：``content/forms.yaml`` 的 schema。

形態是姿態的擴充：用 ``enter_form`` 原語（技能 ``kind: stance``）進入，同時只能有一個（和一般姿態
互斥）。資料定義每種形態的：

- ``category``：``physical`` 物理（維持費扣耐力）、``mental`` 心智（扣法力）；
- ``natural_weapon``：天生武器——形態內的普攻改用它（骰、近戰／遠程與射程、一或兩個屬性〔同類取
  較高、一物理一心智取平均，同 08 8.11〕、固定元素或「進入時選」的元素清單）。天生武器沒有詞條；
  特性 ``traits``（3J-1b：惡魔兩下、巨人推擊 +1、狼人流血、樹人觸及 2、貓背刺暴擊）；
- ``effects``：形態中的效果——防禦 %、移動、最大 HP %、受傷修正（依元素）、你施放的治療加成、
  高度差當平地；**不加六屬性**（6.30）；
- ``entry``：進入獎勵（每次進入觸發一次）；
- ``look``：外觀 id（3J-5 畫圖用；本段只傳給前端）。

數值全部是整數：百分比一律寫千分比（‰）。表格層級的 ``upkeep_stamina``／``upkeep_mana``（每回合
開始的維持費）與 ``cooldown``（離開後該形態的冷卻回合）也放在這裡（初值照 6.30）。

``trpg.content`` 不匯入引擎；引擎（:mod:`trpg.engine.forms`）依 ``id`` 查表，不寫死任何形態。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, Dice, WeaponDef
from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute, Element

__all__ = [
    "CHOSEN",
    "EntryBurst",
    "EntryHealAdjacent",
    "FormCategory",
    "FormDef",
    "FormEffects",
    "FormEntry",
    "FormTable",
    "NaturalCharge",
    "NaturalTraits",
    "NaturalWeapon",
    "TakenMod",
]

type FormCategory = Literal["physical", "mental"]
"""形態類別：物理（維持費扣耐力）、心智（維持費扣法力）。"""

CHOSEN = "chosen"
"""「進入時選的元素」：受傷修正與進入獎勵的範圍傷害可以寫它，代表形態目前的元素。"""

_MAX_ATTRS = 2
_MAX_MELEE_RANGE = 2
_NATURAL_PREFIX = "form_"


class NaturalTraits(ContentModel):
    """天生武器的特性（3J-1b；全部是參數，引擎只讀參數）。

    - ``strikes``：普攻一次打幾下，每一下各自擲命中與傷害（惡魔雙刃 2；同武器的 ``strikes``）；
    - ``knockback``：普攻命中把目標沿攻擊方向推這麼多格（巨人推擊 +1；同武器的 ``knockback``）；
    - ``reach``：觸及——藉機攻擊的範圍（樹人 2；同武器的 ``reach``，不可超過天生武器的射程）；
    - ``bleed``：普攻命中施加流血這麼多回合（狼人 1）；
    - ``backstab_crit``：背刺時暴擊範圍再多擴大這麼多（貓 1；疊在核心規則的背刺加成上）。
    """

    strikes: int = Field(default=1, ge=1, le=3)
    knockback: int = Field(default=0, ge=0, le=3)
    reach: int = Field(default=1, ge=1, le=_MAX_MELEE_RANGE)
    bleed: int = Field(default=0, ge=0, le=3)
    backstab_crit: int = Field(default=0, ge=0, le=3)


class NaturalCharge(ContentModel):
    """定向蓄力（3J-2，6.30 龍的蓄力吐息）：有它的天生武器，普攻＝選一個方向開始蓄力，**下一個自己
    的回合開始時**朝該方向以錐形（大小 ``size``）釋放天生武器的傷害（骰、屬性 × 0.3、元素）。
    蓄力中倒下、暈眩、冰凍、離開形態就取消；預告格同環境預告。"""

    size: int = Field(default=3, ge=2, le=4)
    """錐形的大小（``skill_shapes.yaml`` 的 ``cone`` 參數 ``size``）。"""


class NaturalWeapon(ContentModel):
    """天生武器（6.30）。``element`` 與 ``element_choices`` 最多填一個（都不填＝物理）；
    ``element_choices`` 是「進入時選」的清單（第一個是省略時的預設）。``damage_permille``：天生武器
    造成的傷害加成（‰；元素化身的「該元素傷害 +10%」＝ 100）。"""

    name_zh: str = Field(min_length=1)
    dice: Dice
    attack: Literal["melee", "ranged"]
    range: int = Field(default=1, ge=1, le=8)
    attrs: tuple[Attribute, ...] = Field(min_length=1, max_length=_MAX_ATTRS)
    element: Element | None = None
    element_choices: tuple[Element, ...] = ()
    damage_permille: int = Field(default=0, ge=0, le=1000)
    traits: NaturalTraits = NaturalTraits()
    """天生武器特性（3J-1b）；沒有特性時全是預設值。"""
    charge: NaturalCharge | None = None
    """定向蓄力（3J-2）：填了就是蓄力武器（龍的吐息），只能是遠程；普攻改成開始蓄力。"""

    @model_validator(mode="after")
    def _check(self) -> NaturalWeapon:
        if len(set(self.attrs)) != len(self.attrs):
            raise ValueError(f"天生武器 {self.name_zh}：attrs 不可重複")
        if self.element is not None and self.element_choices:
            raise ValueError(f"天生武器 {self.name_zh}：element 與 element_choices 最多填一個")
        if len(set(self.element_choices)) != len(self.element_choices):
            raise ValueError(f"天生武器 {self.name_zh}：element_choices 不可重複")
        if Element.PHYSICAL in self.element_choices:
            raise ValueError(f"天生武器 {self.name_zh}：element_choices 不可含物理")
        if self.attack == "melee" and self.range > _MAX_MELEE_RANGE:
            raise ValueError(f"天生武器 {self.name_zh}：近戰的射程最多 {_MAX_MELEE_RANGE}")
        if self.charge is not None and (
            self.attack != "ranged" or self.traits != NaturalTraits() or self.damage_permille
        ):
            raise ValueError(f"天生武器 {self.name_zh}：蓄力武器必須是遠程，沒有特性與傷害加成")
        if self.traits.reach > self.range:
            raise ValueError(f"天生武器 {self.name_zh}：觸及（reach）不可超過射程")
        return self

    def weapon_def(self, form_id: str, element: Element | None) -> WeaponDef:
        """形態內實際使用的武器資料（普攻改用它）：沒有詞條與小特性；兩個屬性同類取較高、一物理
        一心智取平均（08 8.11）。``element`` 是進入時選的元素（``element_choices`` 的其中之一）。"""
        first = self.attrs[0]
        second = self.attrs[1] if len(self.attrs) > 1 else None
        same = second is None or second.is_physical == first.is_physical
        chosen = self.element if self.element is not None else element
        return WeaponDef(
            id=f"{_NATURAL_PREFIX}{form_id}",
            name_zh=self.name_zh,
            weapon_class=self.attack,
            range=self.range,
            dice=self.dice,
            scaling_attr=first,
            secondary_scaling_attr=second,
            attr_mode="max" if same else "mean",
            element=Element.PHYSICAL if chosen is None else chosen,
            strikes=self.traits.strikes,
            knockback=self.traits.knockback,
            reach=self.traits.reach,
            summon_only=True,
        )


class TakenMod(ContentModel):
    """受到某元素傷害的倍率（‰；500 ＝ −50%、1500 ＝ +50%）。``element`` 可寫 ``chosen``（進入時
    選的元素）。"""

    element: Element | Literal["chosen"]
    permille: int = Field(ge=0, le=3000)


class FormEffects(ContentModel):
    """形態中的效果（6.30；不加六屬性）。

    - ``defense_permille``：防禦值加成（‰，直接加在防禦值的加成上，同防禦姿態；可為負）；
    - ``move``：每回合開始的移動點數加減（同石膚的 ``move_delta``，回合開始時結算）；
    - ``max_hp_permille``：最大 HP 加減（‰；進入時結算，目前 HP 不變但不超過新上限）；
    - ``damage_taken``：依元素的受傷倍率；
    - ``heal_permille``：你施放的治療量加成（‰）；
    - ``flat_height``：上坡高度差在這個層數以內時當平地走（不多花移動點數）。
    """

    defense_permille: int = Field(default=0, ge=-500, le=500)
    move: int = Field(default=0, ge=-3, le=3)
    max_hp_permille: int = Field(default=0, ge=-500, le=500)
    damage_taken: tuple[TakenMod, ...] = ()
    heal_permille: int = Field(default=0, ge=0, le=1000)
    flat_height: int = Field(default=0, ge=0, le=2)


class EntryBurst(ContentModel):
    """進入獎勵：``radius`` 格內（曼哈頓）的敵人受 ``dice`` 的 ``element`` 傷害（自動命中，不加
    屬性；
    ``element`` 可寫 ``chosen``）。"""

    radius: int = Field(ge=1, le=3)
    dice: Dice
    element: Element | Literal["chosen"]


class EntryHealAdjacent(ContentModel):
    """進入獎勵：治療相鄰友方（不含自己）``dice`` ＋ ``attr`` × ``attr_permille``‰。"""

    dice: Dice
    attr: Attribute
    attr_permille: int = Field(default=500, ge=0, le=1000)


class FormEntry(ContentModel):
    """進入獎勵（每次進入形態時觸發一次；6.30）。全部可省略，可同時填多個。

    - ``shield_max_hp_permille``：護盾＝最大 HP（進入後）× ‰，持續 ``shield_duration`` 回合；
    - ``heal_max_hp_permille``：回復最大 HP（進入後）× ‰；
    - ``next_attack_hit``／``next_attack_crit``：下一次擲命中的攻擊，命中 +N／暴擊範圍 +N（用掉或
      離開形態時失效）；
    - ``move``：本回合移動點數 +N；
    - ``conceal``：隱蔽 N 回合；
    - ``burst``：範圍傷害；``heal_adjacent``：治療相鄰友方；
    - ``collision_permille``：本回合（進入的那個自己的回合）你造成的撞擊傷害 +N‰（巨人 500）。
    """

    shield_max_hp_permille: int | None = Field(default=None, ge=1, le=1000)
    shield_duration: int = Field(default=2, ge=1, le=3)
    heal_max_hp_permille: int | None = Field(default=None, ge=1, le=1000)
    next_attack_hit: int = Field(default=0, ge=0, le=5)
    next_attack_crit: int = Field(default=0, ge=0, le=5)
    move: int = Field(default=0, ge=0, le=3)
    conceal: int | None = Field(default=None, ge=1, le=3)
    burst: EntryBurst | None = None
    heal_adjacent: EntryHealAdjacent | None = None
    collision_permille: int = Field(default=0, ge=0, le=2000)


class FormDef(ContentModel):
    """一種形態。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    category: FormCategory
    natural_weapon: NaturalWeapon
    effects: FormEffects = FormEffects()
    entry: FormEntry = FormEntry()
    look: str = Field(pattern=ID_PATTERN)
    """外觀 id（3J-5 依它畫整身外觀；前端不認得時退回原角色＋光環）。"""

    @model_validator(mode="after")
    def _check(self) -> FormDef:
        uses_chosen = any(m.element == CHOSEN for m in self.effects.damage_taken) or (
            self.entry.burst is not None and self.entry.burst.element == CHOSEN
        )
        if uses_chosen and not self.natural_weapon.element_choices:
            raise ValueError(f"形態 {self.id}：用了 chosen 元素，但天生武器沒有 element_choices")
        return self

    @property
    def element_choices(self) -> tuple[Element, ...]:
        """進入時可選的元素（沒有時為空）。"""
        return self.natural_weapon.element_choices


class FormTable(ContentModel):
    """``content/forms.yaml``。"""

    upkeep_stamina: int = Field(default=5, ge=0, le=20)
    """物理形態每回合開始扣的耐力（不夠付就自動解除）。"""
    upkeep_mana: int = Field(default=3, ge=0, le=20)
    """心智形態每回合開始扣的法力（不夠付就自動解除）。"""
    stance_upkeep_stamina: int = Field(default=2, ge=1, le=10)
    """一般姿態（``SkillDef.stance_upkeep``）每點維持費的耐力數（武器技姿態；3W-2b）。"""
    stance_upkeep_mana: int = Field(default=1, ge=1, le=10)
    """一般姿態每點維持費的法力數（法術技姿態；3W-2b）。"""
    cooldown: int = Field(default=2, ge=1, le=5)
    """離開一個形態（自己取消、被迫解除、切換）後該形態的冷卻回合（同技能冷卻的倒數）。"""
    forms: tuple[FormDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> FormTable:
        ids = [f.id for f in self.forms]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"forms.yaml：形態 ID 重複：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, FormDef]:
        return {f.id: f for f in self.forms}

    def upkeep(self, form: FormDef) -> tuple[Literal["stamina", "mana"], int]:
        """``form`` 每回合開始的維持費：（資源, 數量）。"""
        if form.category == "physical":
            return "stamina", self.upkeep_stamina
        return "mana", self.upkeep_mana

    def summary(self) -> str:
        return f"{len(self.forms)} 種形態"
