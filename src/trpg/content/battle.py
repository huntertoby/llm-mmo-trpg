"""戰鬥用的內容 schema：骰子、地形、武器、狀態、單位範本。

對應資料檔：``content/terrain.yaml``、``content/weapons.yaml``、``content/statuses.yaml``、
``content/units/*.yaml``。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, field_validator, model_serializer, model_validator

from trpg.content.parts import BossPart, SealSkillBreak, check_parts
from trpg.content.schemas import ContentModel
from trpg.content.slots import Slot
from trpg.shared.bonus_text import bonus_text
from trpg.shared.fmt import signed_zh
from trpg.shared.types import Attribute, Element, ResistGroup, Surface

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from trpg.content.rules import CoreRules

__all__ = [
    "ID_PATTERN",
    "SUMMON_MODES",
    "ArmorBreak",
    "Blessing",
    "BlockBonus",
    "BossPart",
    "BossPhase",
    "CreatureLook",
    "DeathSurfaceSpec",
    "Dice",
    "DollGear",
    "DollLook",
    "Entangle",
    "FormationSpec",
    "HitCondition",
    "HpBelowTrigger",
    "LookBeard",
    "LookBeastEars",
    "LookChoice",
    "LookEyeStyle",
    "LookFace",
    "LookFrame",
    "LookHair",
    "OffhandDef",
    "OffhandTable",
    "OpeningStatus",
    "PhaseSpawn",
    "PhaseTile",
    "PhaseTrigger",
    "ReactionRule",
    "ReactionUnless",
    "ReactionWhen",
    "Reap",
    "RoundTrigger",
    "ShareDamageSpec",
    "StatusDef",
    "StatusTable",
    "StatusTickDamage",
    "StatusTickHeal",
    "SummonDetonate",
    "SummonHitRule",
    "SummonLook",
    "SummonLookBody",
    "SummonLookSize",
    "SummonLookTrait",
    "SummonMode",
    "SummonPlatform",
    "SummonPulse",
    "SummonSnare",
    "TagDownTrigger",
    "TerrainDef",
    "TerrainTable",
    "TotemSpec",
    "UnitTemplate",
    "WardSpec",
    "WeaponDef",
    "WeaponLook",
    "WeaponTable",
    "check_phases",
    "part_reference_problems",
    "template_part_problems",
    "weapon_attr_examples_zh",
]

ID_PATTERN = r"^[a-z][a-z0-9_]*$"
"""內容 ID 與標籤的格式：小寫英文開頭的 snake_case。"""

_DICE_RE = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*$")
_MAX_DICE_COUNT = 100
_MAX_DICE_SIDES = 1000


def _unique_ids(ids: list[str], what: str) -> None:
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    if dup:
        raise ValueError(f"重複的{what} ID：{', '.join(dup)}")


# ---------------------------------------------------------------------------
# 骰子
# ---------------------------------------------------------------------------


class Dice(ContentModel):
    """``NdM`` 骰子（資料檔中寫成字串 ``"2d6"``，序列化時也輸出字串）。"""

    count: int = Field(ge=1, le=_MAX_DICE_COUNT)
    sides: int = Field(ge=1, le=_MAX_DICE_SIDES)

    @model_validator(mode="before")
    @classmethod
    def _parse_text(cls, data: object) -> object:
        if isinstance(data, str):
            match = _DICE_RE.match(data)
            if match is None:
                raise ValueError(f"骰子格式應為 NdM（例如 2d6），收到 {data!r}")
            return {"count": int(match.group(1)), "sides": int(match.group(2))}
        return data

    @model_serializer(mode="plain")
    def _to_text(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.count}d{self.sides}"


# ---------------------------------------------------------------------------
# 地形
# ---------------------------------------------------------------------------


class TerrainDef(ContentModel):
    """一種地形。

    - ``walkable``：單位能否主動走進這一格（``chasm``、``lava`` 為否）。
    - ``deadly``：致命地形。單位被強制位移進來時，一般單位死亡；``elite`` 改受最大 HP 一定比例的
      傷害並移到最近的安全格。
    - ``blocks_sight``：阻擋穿越這一格的視線（全掩護，例如 ``wall``）。
    - ``glyph``：``trpg map show`` 與戰鬥網格顯示用的單一 ASCII 字元。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    glyph: str = Field(min_length=1, max_length=1, pattern=r"^[!-~]$")
    walkable: bool
    deadly: bool = False
    blocks_sight: bool = False


class TerrainTable(ContentModel):
    """``content/terrain.yaml``。"""

    terrain: tuple[TerrainDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> TerrainTable:
        _unique_ids([t.id for t in self.terrain], "地形")
        glyphs = [t.glyph for t in self.terrain]
        dup = sorted(g for g, n in Counter(glyphs).items() if n > 1)
        if dup:
            raise ValueError(f"重複的地形顯示字元：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, TerrainDef]:
        return {t.id: t for t in self.terrain}

    def summary(self) -> str:
        return f"{len(self.terrain)} 種地形"


# ---------------------------------------------------------------------------
# 武器
# ---------------------------------------------------------------------------


class ArmorBreak(ContentModel):
    """武器特性「破甲」（Phase 3-24a1）：普攻命中後，目標的防禦值變化 ``defense_permille``（‰，
    負值為降低，例如 ``-100`` ＝ 防禦 −10%），持續 ``rounds`` 回合（狀態 ``armor_broken``）。"""

    defense_permille: int = Field(le=-1, ge=-1000)
    rounds: int = Field(ge=1, le=5)


class Reap(ContentModel):
    """武器特性「收割」（Phase 3I-1，08 8.11）：結算傷害前，目標 **當下** HP ≤ 最大 HP 的
    ``hp_permille``‰ 時，這次傷害 +``damage_permille``‰；適用普攻與武器技，計入全身傷害加成上限。"""

    hp_permille: int = Field(ge=1, le=1000)
    damage_permille: int = Field(ge=1, le=1000)


class Entangle(ContentModel):
    """武器特性「纏繞」（Phase 3I-1，08 8.11）：普攻命中後施加狀態 ``entangled``——目標下一個回合
    開始時移動點數 −``move_penalty``（最低 0），持續到該回合結束；重複施加只刷新、不疊加；不擲抵抗、
    不算控制類別。"""

    move_penalty: int = Field(ge=1, le=6)


class Blessing(ContentModel):
    """武器特性「祝禱」（Phase 3-24a1）：普攻命中時，最近的隊友（不含自己與召喚物）回復
    ``dice`` ＋ ``flat`` 點 HP；沒有可回復的隊友時不發動。"""

    flat: int = Field(default=0, ge=0)
    dice: Dice | None = None

    @model_validator(mode="after")
    def _check(self) -> Blessing:
        if self.flat == 0 and self.dice is None:
            raise ValueError("祝禱的回復量不可為 0（flat 與 dice 至少填一個）")
        return self


_NEUTRAL_PERMILLE = 1000


class RangeMod(ContentModel):
    """武器特性「距離修正」（Phase 3-24a2，火槍的貼臉懲罰與遠距加成）：攻擊距離在
    ``min_distance``～``max_distance``（含；省略 ＝ 不設上限）格時，普攻命中 ``hit``、傷害 ×
    ``damage_permille``‰。多條重疊時全部生效（命中相加、傷害相乘）。"""

    min_distance: int = Field(ge=1)
    max_distance: int | None = Field(default=None, ge=1)
    hit: int = Field(default=0, ge=-10, le=10)
    damage_permille: int = Field(default=1000, ge=0, le=3000)

    @model_validator(mode="after")
    def _check(self) -> RangeMod:
        if self.max_distance is not None and self.max_distance < self.min_distance:
            raise ValueError("range_mod 的 max_distance 不可小於 min_distance")
        if self.hit == 0 and self.damage_permille == _NEUTRAL_PERMILLE:
            raise ValueError("range_mod 沒有任何修正（hit 與 damage_permille 至少改一個）")
        return self

    def covers(self, distance: int) -> bool:
        return distance >= self.min_distance and (
            self.max_distance is None or distance <= self.max_distance
        )

    def label_zh(self) -> str:
        if self.min_distance == 1 and self.max_distance == 1:
            return "貼臉（相鄰）"
        if self.max_distance is None:
            return f"{self.min_distance} 格以上"
        if self.max_distance == self.min_distance:
            return f"{self.min_distance} 格"
        return f"{self.min_distance}～{self.max_distance} 格"


class Steady(ContentModel):
    """武器特性「站定」（Phase 3-24a2，火槍的站定狙擊）：本回合還沒主動移動時開火，普攻命中
    ``+hit``、暴擊範圍擴大 ``crit_range``（可和瞄準、背刺疊加）。"""

    hit: int = Field(default=0, ge=0, le=10)
    crit_range: int = Field(default=0, ge=0, le=10)

    @model_validator(mode="after")
    def _check(self) -> Steady:
        if self.hit == 0 and self.crit_range == 0:
            raise ValueError("steady 沒有任何加成（hit 與 crit_range 至少填一個）")
        return self


class WeaponDef(ContentModel):
    """一把武器。

    - ``range``：射程（曼哈頓距離）；``1`` 為近戰（相鄰）。
    - ``crit_range``：暴擊的最低自然骰值，``20`` 表示只有自然 20，``19`` 表示 19–20。
    - ``weapon_class``：武器大類（Phase 2A）：``melee`` 近戰、``ranged`` 遠程、``focus`` 法器；
      技能的 ``weapon_req`` 與之對照。法器的攻擊加值也計入法術技的命中。

    武器小特性（Phase 3-24a1）一律是下列參數，引擎只讀參數、不寫死數值（之後的「武器特性強化」
    詞條改這些參數即可）：

    - ``secondary_scaling_attr``：第二縮放屬性；有值時攻擊值與傷害用兩屬性合成一個值，取法由
      ``attr_mode`` 決定（Phase 3H-1；3I-1 依 08 8.11、玩法決定 #46 改）：兩個屬性同類（都是物理或
      都是心智）為 ``max`` 取較高者；一物理一心智為 ``mean`` 取平均（無條件捨去，兩個都要點）。
      schema 檢查兩者一致。沒有第二屬性時 ``attr_mode`` 不影響結果。
    - ``armor_break``：破甲，見 :class:`ArmorBreak`。
    - ``knockback``：震退——普攻命中後把目標沿攻擊方向推這麼多格（沿用推擊與撞擊規則）。
    - ``reach``：觸及——藉機攻擊的範圍（目標從 ``reach`` 格內走到 ``reach`` 格外時可以反應）；
      不可超過 ``range``。
    - ``blessing``：祝禱，見 :class:`Blessing`。
    - ``summon_dice_bonus``：統御——持有者召喚物的普攻多加這麼多顆傷害骰。
    - ``lob``：拋射——視線可以越過這麼多層高的障礙（物件、地形高差；牆壁與黑暗不行）。

    第二批提前的武器小特性（Phase 3I-1，08 8.11「提前武器的特性細節」）：

    - ``counter``：反擊（拳套）——相鄰敵人的近戰攻擊命中持有者、持有者沒倒下時，以內建反應
      ``counter_attack`` 自動對攻擊者普攻一次（佔本輪反應，不花 AP、不花耐力）；
    - ``reap``：收割（鐮刀），見 :class:`Reap`；
    - ``entangle``：纏繞（鞭），見 :class:`Entangle`。

    第二批其他武器（Phase 3I-4，08 8.11 雙匕首與火器）：

    - ``paired``：成對武器（雙匕首、雙手槍）——算一件武器、占雙手（副手欄位被占用）；握法欄位
      ``two_handed`` 仍是 ``False``（成對武器的物品帶 ``paired: true``，工坊的「成對武器」勾選框
      由此推導）；
    - ``strikes``：普攻一次連打幾下（雙匕首 2）；每一下各自擲命中與傷害（背刺時每一下都吃加成），
      目標在第一下倒下就不再打第二下；武器技不受影響（武器技仍只打一次）。

    遠程武器小特性（Phase 3-24a2；同樣只是參數，引擎只讀參數）：

    - ``pierce_line``：穿透一直線——普攻命中（結算）目標之後，子彈／弩箭沿同一直線繼續飛，最多再
      擊中這麼多名射程內、視線未被擋住的敵人（各自擲命中與傷害）；
    - ``pierce_permille``（BAL-9c）：穿透到後方敵人的傷害千分比（1000 ＝ 不打折；不是 1000 時
      穿透的那幾下不再觸發分裂與連擊）；
    - ``ignore_height``：不受高度影響——這把武器的攻擊沒有高打低、低打高的命中修正；
    - ``magazine``／``reload_ap``：彈匣容量與裝填的 AP 花費（0 ＝ 不用裝填）；開火一次用掉 1 發，
      彈匣空了不能普攻，要先裝填（彈匣空時才能裝填）；有彈匣的武器是直射——不可同時有 ``lob``；
    - ``gunshot``：槍聲——普攻開火會解除自己的隱蔽狀態；
    - ``steady``：站定，見 :class:`Steady`；
    - ``ignore_cover``：普攻無視半掩護；
    - ``armor_pierce_permille``：普攻命中判定時，目標防禦值穿透這麼多‰（250 ＝ 防禦 −25%）；
    - ``range_mod``：距離修正，見 :class:`RangeMod`。

    只由「武器特性強化」詞條開啟的參數（Phase 3-32a；武器本身預設 0，引擎只讀參數）：

    - ``high_range``：站得比目標高（高處）時，普攻射程再加這麼多格（弓的高處射程強化）；
    - ``backstab_dice``：從背後近戰攻擊（背刺）時，普攻傷害骰再多加這麼多顆（匕首的背刺強化）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    weapon_class: Literal["melee", "ranged", "focus"]
    range: int = Field(ge=1)
    dice: Dice
    flat: int = 0
    attack_bonus: int = 0
    scaling_attr: Attribute
    secondary_scaling_attr: Attribute | None = None
    attr_mode: Literal["mean", "max"] = "mean"
    element: Element = Element.PHYSICAL
    crit_range: int = Field(default=20, ge=2, le=20)
    two_handed: bool = False
    paired: bool = False
    strikes: int = Field(default=1, ge=1, le=3)
    backstab_first_only: bool = False
    """（BAL-8 B18）連擊武器：背刺（命中與暴擊加成）只算第一下；預設 False ＝ 每下都吃。"""
    armor_break: ArmorBreak | None = None
    knockback: int = Field(default=0, ge=0, le=3)
    reach: int = Field(default=1, ge=1)
    blessing: Blessing | None = None
    summon_dice_bonus: int = Field(default=0, ge=0, le=3)
    lob: int = Field(default=0, ge=0, le=2)
    counter: bool = False
    reap: Reap | None = None
    entangle: Entangle | None = None
    pierce_line: int = Field(default=0, ge=0, le=8)
    pierce_permille: int = Field(default=1000, ge=0, le=1000)
    ignore_height: bool = False
    magazine: int = Field(default=0, ge=0, le=6)
    reload_ap: int = Field(default=1, ge=1, le=3)
    gunshot: bool = False
    steady: Steady | None = None
    ignore_cover: bool = False
    armor_pierce_permille: int = Field(default=0, ge=0, le=1000)
    range_mod: tuple[RangeMod, ...] = ()
    high_range: int = Field(default=0, ge=0, le=2)
    backstab_dice: int = Field(default=0, ge=0, le=2)
    summon_only: bool = False
    """召喚物專用的武器（Phase 3-33e1）：不列入開局可選的武器，也不給玩家裝備。"""
    enemy_only: bool = False
    """敵人專用的武器（6F-1，例 ``bow_guard``）：開局畫面（``/api/runs/start-options``）不列出。
    只影響選單；隨機開局與掉落照舊（不改種子 → 結果的對應）。"""
    look: WeaponLook | None = None
    """預設外觀（Phase 3E-2e）：紙娃娃主手與武器小圖示的造型；經 glossary API 給前端。"""

    @model_validator(mode="after")
    def _check(self) -> WeaponDef:
        if self.magazine > 0 and self.lob > 0:
            raise ValueError(f"武器 {self.id}：有彈匣的武器是直射，不可同時有 lob（拋射）")
        if self.secondary_scaling_attr == self.scaling_attr:
            raise ValueError(f"武器 {self.id}：secondary_scaling_attr 不可和 scaling_attr 相同")
        second = self.secondary_scaling_attr
        if second is not None:  # 08 8.11（#46）：同類取較高、一物理一心智取平均
            same = second.is_physical == self.scaling_attr.is_physical
            if self.attr_mode != ("max" if same else "mean"):
                raise ValueError(
                    f"武器 {self.id}：雙屬性同類（都是物理或都是心智）要 attr_mode: max，"
                    "一物理一心智要 attr_mode: mean"
                )
        if self.paired and self.two_handed:
            raise ValueError(f"武器 {self.id}：成對武器（paired）不可同時是雙手武器（two_handed）")
        if self.reach > self.range:
            raise ValueError(f"武器 {self.id}：reach（{self.reach}）不可超過 range（{self.range}）")
        return self

    @property
    def is_melee(self) -> bool:
        """近戰類武器（含長柄）：看大類，不看射程（矛的射程是 2，仍是近戰）。"""
        return self.weapon_class == "melee"

    def scaling_value(self, get: Callable[[Attribute], int]) -> int:
        """武器的縮放屬性值（Phase 3H-1，08 8.11）：單屬性為該屬性，雙屬性依 ``attr_mode``——
        ``mean`` 取平均（無條件捨去；一物理一心智），``max`` 取較高者（同類）。``get`` 讀屬性值；
        引擎傳入有效屬性（含狀態加值），卡片傳入面板的屬性。普攻與反應攻擊的傷害加成、技能卡的
        「目前 +N」都經過這裡。"""
        value = get(self.scaling_attr)
        if self.secondary_scaling_attr is None:
            return value
        other = get(self.secondary_scaling_attr)
        return max(value, other) if self.attr_mode == "max" else (value + other) // 2

    def scaling_names_zh(self) -> str:
        """縮放屬性的中文：單屬性「力量」，雙屬性「敏捷／力量（取較高）」或「體質／力量（取平均）」。"""
        if self.secondary_scaling_attr is None:
            return self.scaling_attr.display_name
        names = f"{self.scaling_attr.display_name}／{self.secondary_scaling_attr.display_name}"
        return f"{names}（{'取較高' if self.attr_mode == 'max' else '取平均'}）"

    def skill_scaling_names_zh(self, secondary: Attribute | None = None) -> str:
        """武器技實際吃的屬性（3-55）：武器自己的縮放屬性；技能帶心智第二屬性（3I-3）時再和它取平均，
        例「力量與智力（取平均）」「敏捷／力量（取較高）與智力（取平均）」。"""
        names = self.scaling_names_zh()
        return names if secondary is None else f"{names}與{secondary.display_name}（取平均）"

    def attack_formula_zh(
        self, core: CoreRules, get: Callable[[Attribute], int] | None = None
    ) -> str:
        """普攻的傷害算法（3-41c，08 8.11）：「普攻：1d8＋力量 × 0.3」；``get`` 有值時附目前加成
        「（目前 +4）」。倍率取自 ``rules/core.yaml``，加成用 :meth:`scaling_value`（和引擎同一個
        算法：骰值＋固定傷害＋屬性值 × 倍率，之後才乘各種倍率並無條件捨去）。"""
        permille = core.basic_attack_attr_multiplier_permille
        dice = f"{self.dice}＋{self.flat}" if self.flat else str(self.dice)
        text = f"普攻：{dice}＋{self.scaling_names_zh()} × {permille / 1000:g}"
        if get is not None:
            text += f"（{bonus_text(self.scaling_value(get), permille)}）"
        return text

    def rule_lines_zh(
        self, core: CoreRules, get: Callable[[Attribute], int] | None = None
    ) -> tuple[str, ...]:
        """武器卡的共用規則（Phase 3-41b，清單 7.2、7.3）：握法（單手／雙手）與近戰武器共用的背刺。
        數字取自 ``rules/core.yaml``，改規則說明跟著變。第一行是普攻的傷害算法（3-41c；``get`` 見
        :meth:`attack_formula_zh`）。"""
        lines = [
            self.attack_formula_zh(core, get),
            "雙手：占用副手欄位，不能再裝備盾或副手物品"
            if self.two_handed
            else "成對：算一件武器、占用雙手，不能再裝備盾或副手物品"
            if self.paired
            else "單手：副手欄位可以放盾或副手物品",
        ]
        if self.secondary_scaling_attr is not None:
            names = f"{self.scaling_attr.display_name}、{self.secondary_scaling_attr.display_name}"
            how = "取較高者" if self.attr_mode == "max" else "取平均"
            lines.append(f"雙屬性：普攻與武器技吃{names}，{how}")
        if self.is_melee:
            lines.append(
                f"背刺（近戰共用規則）：從目標背後攻擊，命中 +{core.backstab_hit_bonus}、"
                f"暴擊範圍 +{core.backstab_crit_range_bonus}"
            )
        return tuple(lines)

    def trait_lines_zh(self, *, on_hit_only: bool = False) -> tuple[str, ...]:
        """武器小特性的說明（每個特性一行；資料欄位的數值直接帶入，改參數說明跟著變）。
        ``on_hit_only``：只列普攻命中時發動的特性（預覽用：破甲、震退、祝禱）。"""
        lines: list[str] = []
        if self.armor_break is not None:
            pct = -self.armor_break.defense_permille / 10
            lines.append(f"破甲：命中後目標防禦 −{pct:g}%，{self.armor_break.rounds} 回合")
        if self.knockback:
            lines.append(f"震退：普攻命中推 {self.knockback} 格（會撞擊）")
        if self.reach > 1 and not on_hit_only:
            lines.append(f"觸及 {self.reach} 格：{self.reach} 格內的藉機攻擊")
        if self.blessing is not None:
            amount = f"{self.blessing.dice}" if self.blessing.dice is not None else ""
            if self.blessing.flat:
                amount += f"{'+' if amount else ''}{self.blessing.flat}"
            lines.append(f"祝禱：普攻命中時，最近的隊友回復 {amount} HP")
        if self.entangle is not None:
            penalty = self.entangle.move_penalty
            lines.append(f"纏繞：普攻命中後，目標下回合移動 −{penalty}（不疊加、不擲抵抗）")
        if on_hit_only:
            return tuple(lines)
        lines.extend(_weapon_batch_two_lines(self))
        lines.extend(_weapon_ranged_lines(self))
        if self.summon_dice_bonus:
            lines.append(f"統御：你的召喚物攻擊 +{self.summon_dice_bonus} 顆傷害骰")
        if self.lob:
            lines.append(f"拋射：可越過 {self.lob} 格高的障礙射擊")
        if self.high_range:
            lines.append(f"居高射遠：站得比目標高時，射程 +{self.high_range}")
        if self.backstab_dice:
            lines.append(f"背刺強化：從背後攻擊時，傷害骰 +{self.backstab_dice} 顆")
        return tuple(lines)


def _weapon_batch_two_lines(w: WeaponDef) -> list[str]:
    """第二批提前武器的常駐特性說明（Phase 3I-1）：反擊、收割（纏繞是命中特性，在呼叫端）。"""
    lines: list[str] = []
    if w.strikes > 1:
        lines.append(
            f"連擊：普攻與單體武器技都打 {w.strikes} 下，每一下各自擲命中與傷害；"
            "背刺時每一下都吃背刺加成（武器技的附加效果只結算一次）"
        )
    if w.counter:
        lines.append("反擊：相鄰敵人的近戰攻擊命中你時，自動回擊一次（佔本輪反應，不花 AP 與耐力）")
    if w.reap is not None:
        lines.append(
            f"收割：目標 HP ≤ {w.reap.hp_permille / 10:g}% 時，普攻與武器技傷害 "
            f"+{w.reap.damage_permille / 10:g}%"
        )
    return lines


def _weapon_ranged_lines(w: WeaponDef) -> list[str]:
    lines: list[str] = []
    if w.pierce_line:
        text = "穿透：命中後箭矢貫穿同一直線上的後方敵人"
        if w.pierce_permille < _NEUTRAL_PERMILLE:
            text += f"（後方敵人受 {w.pierce_permille / 10:g}% 傷害）"
        lines.append(text)
    if w.ignore_height:
        lines.append("不受高度影響：命中沒有高低差修正")
    if w.magazine:
        lines.append(f"彈匣 {w.magazine} 發：開火後空膛，裝填花 {w.reload_ap} AP（空膛時才能裝填）")
        lines.append("直射：不能拋射，視線被擋就不能打")
    if w.gunshot:
        lines.append("槍聲：開火會解除自己的隱蔽")
    if w.steady is not None:
        parts = [f"命中 {signed_zh(w.steady.hit)}"] if w.steady.hit else []
        parts += [f"暴擊範圍 {signed_zh(w.steady.crit_range)}"] if w.steady.crit_range else []
        lines.append(f"站定狙擊：本回合未移動時開火，{'、'.join(parts)}")
    if w.ignore_cover or w.armor_pierce_permille:
        parts = ["無視半掩護"] if w.ignore_cover else []
        if w.armor_pierce_permille:
            parts.append(f"穿透 {w.armor_pierce_permille / 10:g}% 防禦")
        lines.append(f"直射穿甲：{'、'.join(parts)}")
    for mod in w.range_mod:
        parts = [f"命中 {signed_zh(mod.hit)}"] if mod.hit else []
        if mod.damage_permille != _NEUTRAL_PERMILLE:
            pct = (mod.damage_permille - _NEUTRAL_PERMILLE) / 10
            parts.append(f"傷害 {'+' if pct > 0 else '−'}{abs(pct):g}%")
        lines.append(f"{mod.label_zh()}：{'、'.join(parts)}")
    return lines


def weapon_attr_examples_zh(
    weapons: Iterable[WeaponDef], weapon_req: str, *, per_group: int = 2, max_groups: int = 5
) -> str:
    """沒有持有者時的武器屬性例子（3-55，由武器資料產生、不寫死）：「劍、斧＝力量；匕首＝敏捷／力量
    （取較高）」。只列玩家用得到的武器（不含召喚物專用）、大類符合 ``weapon_req``（``any`` 不限）；
    依 ID 排序，同屬性的武器合成一組（武器多的組在前），每組最多 ``per_group`` 把、最多
    ``max_groups`` 組（超過接「…」）。"""
    groups: dict[str, list[str]] = {}
    for weapon in sorted(weapons, key=lambda w: w.id):
        if weapon.summon_only or weapon_req not in ("any", weapon.weapon_class):
            continue
        groups.setdefault(weapon.scaling_names_zh(), []).append(weapon.name_zh)
    parts = []
    for attrs, names in sorted(groups.items(), key=lambda kv: -len(kv[1])):  # 穩定排序：同數量依 ID
        more = "等" if len(names) > per_group else ""
        parts.append("、".join(names[:per_group]) + more + f"＝{attrs}")
    return "；".join(parts[:max_groups]) + ("…" if len(parts) > max_groups else "")


class WeaponTable(ContentModel):
    """``content/weapons.yaml``。"""

    weapons: tuple[WeaponDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> WeaponTable:
        _unique_ids([w.id for w in self.weapons], "武器")
        return self

    def by_id(self) -> dict[str, WeaponDef]:
        return {w.id: w for w in self.weapons}

    def summary(self) -> str:
        return f"{len(self.weapons)} 把武器"


# ---------------------------------------------------------------------------
# 副手（Phase 3I-2，08 8.11）
# ---------------------------------------------------------------------------


class BlockBonus(ContentModel):
    """圓盾「格擋反應強化」（Phase 3I-2，08 8.11）：持有者的格擋反應多減傷 ``permille_per_point``‰ ×
    副手縮放屬性值，最多 ``max_permille``‰（再加上格擋反應本身的減傷，總減傷不超過 100%）。
    確切數值設計未定，初值保守（見 Phase3I-2 報告「待 PM 決定」）。"""

    permille_per_point: int = Field(ge=1, le=100)
    max_permille: int = Field(ge=1, le=500)


class OffhandDef(ContentModel):
    """一種副手（``content/offhands.yaml``，Phase 3I-2，08 8.11 副手表）。

    - ``scaling_attr``／``secondary_scaling_attr``／``attr_mode``：縮放屬性，規則同武器——同類
      （都是物理或都是心智）取較高 ``max``、一物理一心智取平均 ``mean``（schema 檢查）。
    - ``block_bonus``：格擋反應強化（圓盾），依縮放屬性值，見 :class:`BlockBonus`；
    - ``ranged_cover``：自身半掩護（塔盾）——遠程攻擊打持有者時命中修正同半掩護
      （``core.half_cover_hit_penalty``）；攻擊者站得比持有者高 1 層以上時無視；與場上掩護物不疊加；
    - ``move_penalty``：持有者的移動點數 −N（塔盾）；
    - ``spell_damage_permille``：持有者的法術技傷害 +N‰（法書；計入全身 +50% 上限）；
    - ``spell_range_bonus``：持有者的法術技施放距離 +N（法器珠；不加範圍大小，
      射程為自身的技能不受影響）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    scaling_attr: Attribute
    secondary_scaling_attr: Attribute | None = None
    attr_mode: Literal["mean", "max"] = "max"
    block_bonus: BlockBonus | None = None
    ranged_cover: bool = False
    move_penalty: int = Field(default=0, ge=0, le=3)
    spell_damage_permille: int = Field(default=0, ge=0, le=500)
    spell_range_bonus: int = Field(default=0, ge=0, le=3)

    @model_validator(mode="after")
    def _check(self) -> OffhandDef:
        second = self.secondary_scaling_attr
        if second is not None:
            if second == self.scaling_attr:
                raise ValueError(f"副手 {self.id}：secondary_scaling_attr 不可和 scaling_attr 相同")
            same = second.is_physical == self.scaling_attr.is_physical
            if self.attr_mode != ("max" if same else "mean"):
                raise ValueError(
                    f"副手 {self.id}：雙屬性同類（都是物理或都是心智）要 attr_mode: max，"
                    "一物理一心智要 attr_mode: mean"
                )
        return self

    def scaling_value(self, get: Callable[[Attribute], int]) -> int:
        """副手的縮放屬性值（規則同 :meth:`WeaponDef.scaling_value`）。"""
        value = get(self.scaling_attr)
        if self.secondary_scaling_attr is None:
            return value
        other = get(self.secondary_scaling_attr)
        return max(value, other) if self.attr_mode == "max" else (value + other) // 2

    def scaling_names_zh(self) -> str:
        """縮放屬性的中文：單屬性「體質」，雙屬性「力量／體質（取較高）」。"""
        if self.secondary_scaling_attr is None:
            return self.scaling_attr.display_name
        names = f"{self.scaling_attr.display_name}／{self.secondary_scaling_attr.display_name}"
        return f"{names}（{'取較高' if self.attr_mode == 'max' else '取平均'}）"

    def block_extra_permille(self, get: Callable[[Attribute], int]) -> int:
        """圓盾的格擋強化（‰）：縮放屬性值 × 每點‰，最多 ``max_permille``；沒有強化為 0。"""
        bonus = self.block_bonus
        if bonus is None:
            return 0
        return min(bonus.max_permille, self.scaling_value(get) * bonus.permille_per_point)

    def trait_lines_zh(
        self, core: CoreRules, get: Callable[[Attribute], int] | None = None
    ) -> tuple[str, ...]:
        """副手卡的特性行（縮放屬性與每個常駐特性一行；數值取自資料與規則）。``get`` 有值時，
        格擋強化附「目前 +N%」。"""
        lines = [f"縮放屬性：{self.scaling_names_zh()}"]
        if self.block_bonus is not None:
            cap = self.block_bonus.max_permille / 10
            text = (
                f"格擋強化：格擋反應多減傷 縮放屬性 × {self.block_bonus.permille_per_point / 10:g}%"
                f"（最多 {cap:g}%）"
            )
            if get is not None:
                text += f"（目前 +{self.block_extra_permille(get) / 10:g}%）"
            lines.append(text)
        if self.ranged_cover:
            lines.append(
                f"遠程掩護：遠程攻擊打你時命中 −{core.half_cover_hit_penalty}（同半掩護；"
                "攻擊者站得高 1 層以上時無視）"
            )
        if self.move_penalty:
            lines.append(f"笨重：你的移動 −{self.move_penalty}")
        if self.spell_damage_permille:
            lines.append(
                f"法術增幅：你的法術技傷害 +{self.spell_damage_permille / 10:g}%"
                "（計入全身傷害加成上限）"
            )
        if self.spell_range_bonus:
            lines.append(
                f"法術延伸：你的法術技施放距離 +{self.spell_range_bonus}"
                "（不加範圍大小；射程為自身的技能不受影響）"
            )
        return tuple(lines)


class OffhandTable(ContentModel):
    """``content/offhands.yaml``。"""

    offhands: tuple[OffhandDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> OffhandTable:
        _unique_ids([o.id for o in self.offhands], "副手")
        return self

    def by_id(self) -> dict[str, OffhandDef]:
        return {o.id: o for o in self.offhands}

    def summary(self) -> str:
        return f"{len(self.offhands)} 種副手"


# ---------------------------------------------------------------------------
# 狀態
# ---------------------------------------------------------------------------


class StatusTickDamage(ContentModel):
    """回合開始時受到的持續傷害。"""

    dice: Dice
    element: Element


class StatusTickHeal(ContentModel):
    """回合開始時的持續治療（Phase 2D-1，再生）。"""

    dice: Dice


_NEUTRAL_PERMILLE = 1000
_MAX_DURATION_BONUS = 2


class DeathSurfaceSpec(ContentModel):
    """倒下時留下的表面（Phase 5A-M1，18.2.2 碎晶傀儡、19 熔岩獸「熔核爆裂」）。

    帶有這個狀態的單位倒下時，在倒下的格子與曼哈頓距離 ``radius`` 以內可以有表面的格子產生
    ``surface``；``duration`` 省略＝表面的預設持續回合。"""

    surface: Surface
    radius: int = Field(default=0, ge=0, le=2)
    duration: int | None = Field(default=None, ge=1, le=6)


def _check_kin_name(kin_tag: str | None, kin_name_zh: str | None) -> None:
    """``kin_name_zh``（同門標籤的中文名，5F-2b）只能和 ``kin_tag`` 一起寫。"""
    if kin_name_zh is not None and kin_tag is None:
        raise ValueError("kin_name_zh 必須和 kin_tag 一起寫")


class FormationSpec(ContentModel):
    """陣法範圍加成（Phase 5A-M2，18.2.1 劍陣弟子「劍陣」）。

    「同門」＝與持有者同陣營、存活、在場、不是自己、帶 ``kin_tag``、曼哈頓距離 ≤ ``range`` 的單位。
    倍率：有同門時 ``1000 + per_ally_permille × min(人數, max_allies)``，沒有時 ``alone_permille``；
    乘在持有者造成的攻擊傷害（``cause: attack``）上（``applies_to`` 目前只有 ``damage``）。"""

    kin_tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """同門標籤；省略＝任何友方都算。"""
    kin_name_zh: str | None = Field(default=None, min_length=1, exclude_if=lambda v: v is None)
    """同門標籤在畫面上的中文名（Phase 5F-2b；見 :class:`WardSpec`）。"""
    range: int = Field(default=3, ge=1, le=5)
    per_ally_permille: int = Field(ge=1, le=1000)
    max_allies: int = Field(ge=1, le=5)
    alone_permille: int = Field(default=1000, ge=100, le=1000)
    applies_to: Literal["damage"] = "damage"

    @model_validator(mode="after")
    def _kin_name_needs_tag(self) -> FormationSpec:
        _check_kin_name(self.kin_tag, self.kin_name_zh)
        return self


class WardSpec(ContentModel):
    """護陣（Phase 5A-M2b，18.2 陣眼石靈）：持有者還在場時，``range`` 格內帶 ``kin_tag`` 的友方
    （不含持有者自己）受到的骰值傷害 × ``taken_permille``‰；持有者倒下後立刻解除。多個護陣依
    單位 ID 順序相乘、逐步捨去。"""

    kin_tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """被護住的同門標籤；省略＝任何友方都算。"""
    kin_name_zh: str | None = Field(default=None, min_length=1, exclude_if=lambda v: v is None)
    """同門標籤在單位卡、狀態說明上的中文名（Phase 5F-2b，例：``mist_lock_core`` →「霧鎖真人」）；
    省略時照舊顯示標籤 ID。只能和 ``kin_tag`` 一起寫。"""
    range: int = Field(default=3, ge=1, le=24)
    taken_permille: int = Field(ge=0, le=999)
    """受到的骰值傷害倍率（‰）；0＝持有者在場時完全不受骰值傷害（Phase 5F-3 源晶柱）。"""

    @model_validator(mode="after")
    def _kin_name_needs_tag(self) -> WardSpec:
        _check_kin_name(self.kin_tag, self.kin_name_zh)
        return self


class ShareDamageSpec(ContentModel):
    """把傷害分給同門（Phase 5A-M2，18.2.1 詞綴「連心的」）。

    持有者受到傷害時，護盾與靈魂連結之後剩下的量有 ``permille``‰（捨去）平分給 ``range`` 格內帶
    ``kin_tag`` 的友方（依單位 ID，餘數從 ID 小的開始各多 1 點）；沒有這樣的友方時不分。"""

    kin_tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """同門標籤；省略＝任何友方都算。"""
    kin_name_zh: str | None = Field(default=None, min_length=1, exclude_if=lambda v: v is None)
    """同門標籤在畫面上的中文名（Phase 5F-2b；見 :class:`WardSpec`）。"""
    range: int = Field(default=1, ge=1, le=2)
    permille: int = Field(ge=1, le=900)

    @model_validator(mode="after")
    def _kin_name_needs_tag(self) -> ShareDamageSpec:
        _check_kin_name(self.kin_tag, self.kin_name_zh)
        return self


class StatusDef(ContentModel):
    """一種狀態。

    - ``duration``：預設持續回合；``None`` 表示不倒數（直到被移除或到期條件成立）。
    - ``expires``：``turn_end`` 每次在帶有者的回合結束時 −1，歸零移除；
      ``own_turn_start`` 在帶有者的下個回合開始時移除；``round_end``（Phase 5F-4b）每一輪結束時
      （環境回合之後）−1，歸零移除；``never`` 只能由效果或動作移除。
    - ``stacking``：重複施加時的規則；目前只有 ``refresh``（刷新持續時間，不疊加）。

    Phase 2B-1 的數值效果欄位（千分比一律 ‰，1000 = ×1；多個狀態的同一欄位依序相乘、逐步
    無條件捨去）：

    - ``move_permille``：回合開始時的移動點數倍率（緩速 500、加速 1500）。
    - ``move_reduction``（Phase 3I-1）：回合開始時移動點數再減狀態的數值
      （``StatusInstance.amount``），最低 0；多個時取最大（鞭的纏繞）。
    - ``ap_penalty``（Phase 3-50）：回合開始時 AP 少這麼多（最低 0；透支）。
    - ``prevents_move``：不能主動移動（定身；強制位移照常）。
    - ``skip_turn``：回合開始時跳過整個回合，且不能執行反應（暈眩）。
    - ``damage_dealt_permille``：自己造成的攻擊傷害（``cause: attack``）倍率（虛弱 750）。
    - ``damage_taken_permille``：受到的骰值傷害倍率（易傷 1250；不含墜落、致命地形等百分比傷害）。
    - ``physical_taken_permille``（Phase 3-54b）：受到的 **物理元素** 骰值傷害倍率（石膚 700）；
      與 ``damage_taken_permille`` 相乘。
    - ``move_delta``（Phase 3-54b）：回合開始時的移動點數加減（石膚 −1；只能是負數，最低 0）。
    - ``healing_received_permille``：受到的治療倍率（中毒 500）。
    - ``save_attr``：由技能或動作施加時，守方抵抗用的屬性（省略表示命中即施加）。
    - ``control_group``：控制類別（``movement``、``mental``、``hard``），成功施加後觸發控制遞減。

    Phase 2B-2 的預算欄位：

    - ``budget_points``：技能施加此狀態（預設持續時間）的預算點數；``None`` 表示不能由技能施加。
    - ``min_rarity``：技能使用此狀態的最低稀有度。
    - ``beneficial``（2B-3）：對帶有者有益（防禦、隱蔽）。光環骨架的核心狀態必須有益；
      隨機組合器不會對友方施加無益的狀態。

    Phase 2D-1 的欄位：

    - ``attr_bonus``：帶有者的有效屬性加值（多個狀態相加；先攻不受影響）。
    - ``on_turn_start_heal``：回合開始時治療（與 ``on_turn_start_damage`` 同一時點）。
    - ``forces_target``：嘲諷——帶有者對 **狀態來源以外** 的單位發動攻擊時有劣勢；來源倒下或離場
      時此狀態立即移除。
    - ``absorbs_damage``：護盾——狀態帶有吸收量（``StatusInstance.amount``），骰值傷害先扣護盾。

    Phase 2D-2 的欄位：

    - ``fear_source``：恐懼——主動移動時每一步都不能讓自己與狀態來源的曼哈頓距離變小；攻擊有劣勢；
      來源倒下或離場時此狀態立即移除。
    - ``blocks_spells``：沉默——不能使用 ``category: spell`` 的技能。
    - ``attack_range_cap``：致盲——攻擊與以單位為目標的技能只能選此距離以內的單位；攻擊有劣勢。
    - ``grants_advantage_against``：被標記——對帶有者的攻擊有優勢；不受隱蔽的「無法選為目標」限制。

    Phase 2E-2 的欄位：

    - ``stance``：姿態——持續到取消（``expires: never``），帶有者同時最多一個姿態狀態，施加新的會先
      移除舊的（原因 ``replaced``）；倒下／撤離時移除；淨化不移除。

    Phase 2H-1 的欄位：

    - ``removed_by_element``：帶有者受到這些元素的傷害（數值 > 0）時立即移除此狀態（原因
      ``thawed``；冰凍受火焰傷害解除）。

    Phase 3C-4a 的欄位：

    - ``prevents_death``：免死——帶有者受到傷害、HP 會降到 0 時改為 1 並移除此狀態（墜落與致命
      地形照樣生效）。

    Phase 3D-1 的欄位：

    - ``polarity``：增益／減益／中性分類（必填）。``steal_buff`` 只能奪取 ``buff``；``neutral``
      （姿態、隱蔽、免死、靈魂連結）帶有來源或唯一性語意，不能被奪取。

    Phase 3D-8a 的欄位：

    - ``prevents_concealment``：被揭露（``reveal``）——帶有者不算隱蔽（連黑暗表面與草叢也不算），
      也不能獲得 ``concealed`` 狀態。

    Phase 3C-4b 的欄位：

    - ``redirects_damage``：靈魂連結——帶有者受到的傷害有 ``StatusInstance.amount``‰ 轉給狀態來源
      （``source_id``，施放者）；來源倒下或離場時此狀態立即移除。

    Phase 3-24a1 的欄位：

    - ``defense_break``：破甲——帶有者的防禦值降低 ``StatusInstance.amount``‰（武器的
      ``armor_break`` 施加時帶入；``amount`` 省略時為 100‰）；多個破甲取最大的一個，不疊加。

    Phase 3I-6 的欄位：

    - ``attack_element``：攻擊元素（臨時附魔）——帶有者的普攻與沒有自己元素的武器技，物理傷害改成這個
      元素（優先順序見 :mod:`trpg.engine.attack_element`）。同時只會有一個這種狀態：施加新的會先移除
      舊的（原因 ``replaced``，後施放的覆蓋先施放的）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    duration: int | None = Field(default=None, ge=1)
    expires: Literal["turn_end", "own_turn_start", "round_end", "never"]
    stacking: Literal["refresh"] = "refresh"
    on_turn_start_damage: StatusTickDamage | None = None
    on_turn_start_heal: StatusTickHeal | None = None
    attr_bonus: dict[Attribute, int] = Field(default_factory=dict)
    forces_target: bool = False
    absorbs_damage: bool = False
    fear_source: bool = False
    blocks_spells: bool = False
    attack_range_cap: int | None = Field(default=None, ge=1)
    grants_advantage_against: bool = False
    stance: bool = False
    removed_by_element: tuple[Element, ...] = ()
    prevents_death: bool = False
    redirects_damage: bool = False
    prevents_concealment: bool = False
    defense_break: bool = False
    attack_element: Element | None = None
    attack_bonus: int = Field(default=0, ge=0, le=10)
    move_permille: int = Field(default=1000, ge=0, le=10000)
    move_reduction: bool = False
    ap_penalty: int = Field(default=0, ge=0, le=3)
    prevents_move: bool = False
    skip_turn: bool = False
    damage_dealt_permille: int = Field(default=1000, ge=0, le=10000)
    damage_taken_permille: int = Field(default=1000, ge=0, le=10000)
    physical_taken_permille: int = Field(default=1000, ge=0, le=10000)
    summon_damage_dealt_permille: int = Field(default=1000, ge=1000, le=3000)
    """號令（BAL-19f 追加）：帶有者的召喚物造成的攻擊傷害（``cause: attack``）倍率。"""
    element_dealt: Element | None = None
    """元素傷害加成（Phase 3W-2b，元素姿態）：帶有者造成這個元素的攻擊傷害再 ×
    ``element_dealt_permille``。"""
    element_dealt_permille: int = Field(default=1000, ge=1000, le=3000)
    element_dealt_wet_permille: int = Field(default=1000, ge=1000, le=3000)
    """元素姿態（Phase 3W-2c，雷霆架勢的「雷電導水」）：目標站在水上時，``element_dealt`` 元素的
    傷害再 × 這個倍率（‰）。只能與 ``element_dealt`` 一起設定。"""
    shield_reflect: int = Field(default=0, ge=0, le=5)
    """護盾附反傷（Phase 3W-2b，只有 ``absorbs_damage`` 的狀態）：護盾吸收一次相鄰（近戰）攻擊
    時，對攻擊者反彈這麼多點物理傷害。"""
    shield_end_heal: int = Field(default=0, ge=0, le=10)
    """護盾結束時（被打破或到期）回復持有者這麼多點生命。"""
    shield_break_surface: Surface | None = None
    """護盾被打破時在持有者自己的格子造出這種表面（例：水＝潮濕）。"""
    shield_break_status: str | None = Field(default=None, pattern=ID_PATTERN)
    """護盾被打破時對打破它的攻擊者施加這個狀態（例：標記）。"""
    shield_break_lightning: int = Field(default=0, ge=0, le=10)
    """護盾被打破時對打破它的攻擊者造成這麼多點雷電傷害（Phase 3W-2c，橋接「帶電」）。"""
    status_duration_bonus: dict[str, int] = Field(default_factory=dict)
    """帶有者施加的狀態多持續幾回合（Phase 3W-2b，元素姿態的小特色：``{burning: 1}`` ＝ 你造成的
    燃燒多 1 回合）。只加在有倒數回合的狀態上。"""
    move_delta: int = Field(default=0, ge=-3, le=0)
    healing_received_permille: int = Field(default=1000, ge=0, le=10000)
    save_attr: Attribute | None = None
    control_group: Literal["movement", "mental", "hard"] | None = None
    budget_points: int | None = Field(default=None, ge=0)
    min_rarity: Literal["common", "rare", "epic", "legendary"] = "common"
    beneficial: bool = False
    polarity: Literal["buff", "debuff", "neutral"]
    on_death_surface: DeathSurfaceSpec | None = None
    """（Phase 5A-M1）帶有者倒下時在原地留下表面（:class:`DeathSurfaceSpec`）。只能用在
    ``polarity: neutral``、``expires: never`` 的狀態（不被淨化、驅散、奪取，整場都在）。"""
    formation: FormationSpec | None = None
    """（Phase 5A-M2）陣法範圍加成（:class:`FormationSpec`）。限制同 ``on_death_surface``。"""
    ward: WardSpec | None = None
    """（Phase 5A-M2b）護陣（:class:`WardSpec`）。限制同 ``on_death_surface``。"""
    share_damage: ShareDamageSpec | None = None
    """（Phase 5A-M2）受到的傷害分給同門（:class:`ShareDamageSpec`）。限制同
    ``on_death_surface``。"""
    truce: bool = False
    """（Phase 5F-4b）休戰：帶有者不會受到任何傷害（含墜落、致命地形、最大 HP 比例），帶有者（或
    帶有者的召喚物）也不會對任何單位造成傷害；傷害直接略過、不發事件。只能用在 ``polarity:
    neutral`` 的狀態（不被淨化、驅散、奪取）。循環賽第 1 輪用（``league_truce``，
    ``expires: round_end``）。"""
    enemy_only: bool = False
    """（Phase 5F-5c，玩法 PM 2026-11-03 代決）只給敵人：只能由敵方單位範本的 ``opening_statuses``
    掛上，不能給玩家、影子、傭兵，也不能進技能池（技能引用它＝引用錯誤，生成器、候選、閃現、
    工坊、LLM 可選清單都排除）。必須沒有 ``budget_points``。"""

    @model_validator(mode="after")
    def _check(self) -> StatusDef:
        if self.enemy_only and self.budget_points is not None:
            raise ValueError(f"狀態 {self.id}：enemy_only 的狀態不能有 budget_points")
        for name, spec in (
            ("on_death_surface", self.on_death_surface),
            ("formation", self.formation),
            ("share_damage", self.share_damage),
            ("ward", self.ward),
        ):
            if spec is not None and (
                self.polarity != "neutral" or self.expires != "never" or self.duration is not None
            ):
                raise ValueError(
                    f"狀態 {self.id}：{name} 只能用在 polarity: neutral、expires: never、"
                    "不設 duration 的狀態"
                )
        if self.polarity == "buff" and not self.beneficial:
            raise ValueError(f"狀態 {self.id}：polarity: buff 必須 beneficial: true")
        if self.polarity == "debuff" and self.beneficial:
            raise ValueError(f"狀態 {self.id}：polarity: debuff 不可 beneficial: true")
        if self.stance and (self.expires != "never" or self.duration is not None):
            raise ValueError(f"狀態 {self.id}：姿態（stance）必須 expires: never 且不設 duration")
        self._check_elemental_stance()
        if self.truce and self.polarity != "neutral":
            raise ValueError(f"狀態 {self.id}：truce 只能用在 polarity: neutral 的狀態")
        riders = (
            self.shield_reflect
            or self.shield_end_heal
            or self.shield_break_surface
            or self.shield_break_status
            or self.shield_break_lightning
        )
        if riders and not self.absorbs_damage:
            raise ValueError(
                f"狀態 {self.id}：護盾附帶效果（shield_*）只能用在 absorbs_damage 的狀態"
            )
        if self.attack_element is Element.PHYSICAL:
            raise ValueError(f"狀態 {self.id}：attack_element 不能是 physical")
        if self.control_group is not None and self.save_attr is None:
            raise ValueError(f"狀態 {self.id}：有 control_group 的狀態必須設定 save_attr")
        if self.expires in ("turn_end", "round_end") and self.duration is None:
            raise ValueError(f"狀態 {self.id}：expires 為 {self.expires} 時必須設定 duration")
        return self

    @property
    def scales_with_magnitude(self) -> bool:
        """強度（BAL-12e，玩法決定 #76，06 6.3、6.34.9）能放大的數值型狀態：有每回合傷害或治療、
        倍率欄位（移動、造成／受到的傷害、受到的治療、元素加成）、屬性加值或攻擊加值。控制類狀態
        （``control_group``）與姿態（姿態用自己的幅度規則，3W-5b）不算；潮濕、標記、隱蔽這類沒有
        數值的狀態也不算。"""
        if self.control_group is not None or self.stance:
            return False
        permilles = (
            self.move_permille,
            self.damage_dealt_permille,
            self.damage_taken_permille,
            self.physical_taken_permille,
            self.healing_received_permille,
            self.element_dealt_permille,
            self.element_dealt_wet_permille,
        )
        return bool(
            self.on_turn_start_damage is not None
            or self.on_turn_start_heal is not None
            or any(v != _PERMILLE for v in permilles)
            or any(self.attr_bonus.values())
            or self.attack_bonus
        )

    @property
    def has_shield_riders(self) -> bool:
        """護盾狀態帶有反傷、結束回復、破盾造表面或破盾施加狀態（3W-2b）。"""
        return bool(
            self.shield_reflect
            or self.shield_end_heal
            or self.shield_break_surface
            or self.shield_break_status
            or self.shield_break_lightning
        )

    def _check_elemental_stance(self) -> None:
        """元素姿態（3W-2b）的欄位：元素與倍率成對；狀態持續加成每項 1～2 回合。"""
        if (self.element_dealt is None) != (self.element_dealt_permille == _NEUTRAL_PERMILLE):
            raise ValueError(f"狀態 {self.id}：element_dealt 與 element_dealt_permille 要一起設定")
        if self.element_dealt_wet_permille != _NEUTRAL_PERMILLE and self.element_dealt is None:
            raise ValueError(f"狀態 {self.id}：element_dealt_wet_permille 需要 element_dealt")
        if any(not 1 <= n <= _MAX_DURATION_BONUS for n in self.status_duration_bonus.values()):
            raise ValueError(f"狀態 {self.id}：status_duration_bonus 每項必須是 1 或 2")


class StatusTable(ContentModel):
    """``content/statuses.yaml``。"""

    statuses: tuple[StatusDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> StatusTable:
        _unique_ids([s.id for s in self.statuses], "狀態")
        return self

    def by_id(self) -> dict[str, StatusDef]:
        return {s.id: s for s in self.statuses}

    def summary(self) -> str:
        return f"{len(self.statuses)} 種狀態"


# ---------------------------------------------------------------------------
# 反應規則（單位範本引用；反應定義見 trpg.content.environment）
# ---------------------------------------------------------------------------


class ReactionWhen(ContentModel):
    """反應規則的觸發事件。``targeted_by_*`` 是被攻擊命中之後、傷害之前（內建格擋）；
    ``hit_by_*``、``ally_*``、``enemy_enters_adjacent`` 是反應技的事件（Phase 2E-2、3D-3，見
    ``ReactionSpec``）；``enemy_moves_in_range``（Phase 3D-8c）是內建反應「監視射擊」的事件
    （持有者帶有 ``overwatch`` 狀態時，敵人在武器射程與視線內完成一步移動）。"""

    event: Literal[
        "targeted_by_melee",
        "targeted_by_attack",
        "enemy_leaves_adjacent",
        "hit_by_melee",
        "hit_by_attack",
        "ally_hit_adjacent",
        "hit_by_spell",
        "ally_downed",
        "enemy_enters_adjacent",
        "ally_targeted",
        "ally_hit_near",
        "enemy_moves_in_range",
        "ally_hit_in_range",
        "kin_hit_in_range",
    ]
    """``kin_hit_in_range``（Phase 5A-M1）：內建反應「同門相護」的事件——範圍內帶同門標籤的友方
    被敵人的攻擊（普攻或技能）命中、傷害之前。"""


class ReactionUnless(ContentModel):
    self_stamina_below: int | None = Field(default=None, ge=0)


class ReactionRule(ContentModel):
    """玩家（或範本）預先設定的反應規則（``docs/專案計畫.md`` 5.2.1 的格式）。

    ``mode``：``auto`` 條件成立時自動執行；``prompt`` 暫停結算並詢問（``resolve`` 回傳
    ``pending``，以 ``resume`` 繼續）；``off`` 不觸發（Phase 3-4b，玩家以 ``SetReactionMode``
    設定）。
    """

    reaction: str = Field(pattern=ID_PATTERN)
    when: ReactionWhen
    unless: ReactionUnless | None = None
    mode: Literal["auto", "prompt", "off"] = "auto"


# ---------------------------------------------------------------------------
# 單位範本
# ---------------------------------------------------------------------------

_MAX_ATTR = 999
_PERMILLE = 1000


type SummonMode = Literal["focus", "guard", "follow", "hold"]
"""召喚物的模式（Phase 3-33c，6.29.2）：集火（打指定目標）、守護我、跟隨、待命。"""

SUMMON_MODES: tuple[SummonMode, ...] = ("focus", "guard", "follow", "hold")
"""模式的顯示順序（集火、守護我、跟隨、待命）。"""


class TotemSpec(ContentModel):
    """圖騰（Phase 3D-4b）：不移動、不攻擊的召喚物，只提供光環。

    圖騰自己的回合開始時，曼哈頓距離 ``radius`` 以內（含自己格）的友方（不含其他圖騰）獲得
    ``status`` ``duration`` 回合（已有則刷新）；其餘時間沒有任何動作（AP 為 0）。
    """

    radius: int = Field(ge=1, le=4)
    status: str = Field(pattern=ID_PATTERN)
    duration: int = Field(default=2, ge=1, le=4)


SummonLookBody = Literal["humanoid", "spirit", "construct", "beast", "plant", "totem"]
"""召喚物體型（Phase 3-33h1，``docs/archive/art/召喚物外觀.md``）：人形用紙娃娃，
其餘由前端程式繪製。"""
SummonLookSize = Literal["small", "medium", "large"]
SummonLookTrait = Literal[
    "shield", "translucent", "glow", "puddle", "fuse", "no_ring", "flying", "ground", "aura"
]
"""前端認得的 9 種特徵（Phase 3-33h2）；新增值由美術 PM 補畫法並同步
``docs/archive/art/召喚物外觀.md``。"""


class SummonLook(ContentModel):
    """召喚物外觀欄位（Phase 3-33h1）：純顯示資料，不進引擎結算。

    ``element`` 是關鍵字 ID（點燃、冰凍…，決定配色）；實際顯示以召喚物的灌注關鍵字為先，沒有灌注
    才用這裡的預設。``variant`` 的合法值由前端渲染器決定，不認得的值退回預設畫法；``trait`` 限前端
    認得的 9 個值。
    """

    body: SummonLookBody
    variant: str | None = Field(default=None, pattern=ID_PATTERN)
    element: str | None = Field(default=None, pattern=ID_PATTERN)
    size: SummonLookSize = "medium"
    trait: SummonLookTrait | None = None


class WeaponLook(ContentModel):
    """武器的預設外觀（Phase 3E-2e，純顯示資料）：紙娃娃主手與武器小圖示畫哪一種造型。

    ``kind``／``form``／``material`` 是前端認得的裝備造型（``content/equipment/appearance.yaml``），
    不認得時前端退回預設畫法；``element`` 讓法杖帶元素色。沒有 ``look`` 的武器，前端依武器大類退回。
    """

    kind: str = Field(pattern=ID_PATTERN)
    material: str = Field(pattern=ID_PATTERN)
    element: str | None = Field(default=None, pattern=ID_PATTERN)
    form: str | None = Field(default=None, pattern=ID_PATTERN)


DollSlot = Literal["head", "body", "hands", "feet", "cloak", "off_hand", "neck", "back", "waist"]
"""紙娃娃的外觀格；``neck``／``back``／``waist``（念珠、背物、腰掛）只給敵人範本用（Phase 5A-ART3，
純顯示，不是裝備格）。"""
DollHair = Literal["short", "long", "none", "bun"]

_HEX = r"^#[0-9a-fA-F]{6}$"


class DollGear(ContentModel):
    """範本身上的一件外觀裝備（Phase 3E-2e）：造型、材質與染色。

    Phase 5A-ART3：``form`` 形制（例如披風的 ``feather`` 白羽披肩）、``trim`` 鑲邊色（袍子）、
    ``apron`` 圍裙色（袍子前面一片）。前端不認得的 kind／form 不畫。"""

    kind: str = Field(pattern=ID_PATTERN)
    material: str = Field(pattern=ID_PATTERN)
    color: str | None = Field(default=None, pattern=_HEX)
    form: str | None = Field(default=None, pattern=ID_PATTERN)
    trim: str | None = Field(default=None, pattern=_HEX)
    apron: str | None = Field(default=None, pattern=_HEX)


class CreatureLook(ContentModel):
    """異形敵人的外觀（Phase 5A-ART1，``docs/art/敵人外觀.md`` 1.1；純顯示資料）。

    身形 × 材質 × 元素 × 大小 × 特徵。值只檢查格式、**不檢查是否認得**：前端不認得時退回
    （身形 → 軟泥、材質 → 毛皮、元素 → 無、大小 → 1、特徵 → 略過），讓 LLM 產生的新值也畫得出來。
    ``status_traits``：單位身上有該狀態時才多畫的特徵（灰燼之心有「熔殼」時畫甲蟲殼堆）。"""

    body: str = Field(pattern=ID_PATTERN)
    variant: str | None = Field(default=None, pattern=ID_PATTERN)
    material: str | None = Field(default=None, pattern=ID_PATTERN)
    element: str | None = Field(default=None, pattern=ID_PATTERN)
    size: str | None = Field(default=None, pattern=ID_PATTERN)
    tint: str | None = Field(default=None, pattern=_HEX)
    traits: tuple[Annotated[str, Field(pattern=ID_PATTERN)], ...] = Field(default=(), max_length=12)
    status_traits: dict[
        Annotated[str, Field(pattern=ID_PATTERN)],
        tuple[Annotated[str, Field(pattern=ID_PATTERN)], ...],
    ] = Field(default_factory=dict)


type LookFace = Literal["round", "oval", "square", "heart"]
"""臉型（#137）：圓臉（預設）、蛋臉、方臉、尖下巴。"""
type LookEyeStyle = Literal["square", "dot", "smile", "big"]
"""眼睛（#137）：方眼（預設）、圓點、笑眼、大眼。"""
type LookHair = Literal["short", "long", "bob", "ponytail", "twin", "spiky", "bun", "none"]
"""髮型（#137）：短髮、長髮、齊肩、馬尾、雙馬尾、刺蝟、髮髻、光頭。"""
type LookBeard = Literal["none", "stubble", "mustache", "goatee", "full"]
"""鬍子（#137）：無、鬍渣、八字鬍、山羊鬍、大鬍子。"""
type LookFrame = Literal["slim", "broad"]
"""體型（#137，疊在種族體型上）：纖細、壯碩；``None``＝標準。"""
type LookBeastEars = Literal["fox", "cat", "wolf", "rabbit"]
"""獸耳族的耳朵與尾巴（#138）。"""


BOSS_TAG = "boss"
"""頭目的標籤（QK-6a：頭目外觀固定，不依 id 變化）。"""


class LookChoice(ContentModel):
    """玩家自己選的外觀（Phase 6R-2，#137；07 7.7）：**只在畫面**，不影響數值、技能與技能生成，
    引擎不讀。每一項選填，``None``＝照種族預設。不存性別（#137：「先不要有性別」）。

    膚色、髮型、髮色、鬍子、眼色、獸耳要在該族的 ``look_options`` 內
    （:func:`trpg.content.races.look_choice_problems`）；臉型、眼睛、睫毛、體型各族都能選。
    前端在種族外觀**之後**套上（``client/src/render/appearance.ts``）。"""

    face: LookFace | None = None
    eye_style: LookEyeStyle | None = None
    lashes: bool | None = None
    eyes: str | None = Field(default=None, pattern=_HEX)
    hair: LookHair | None = None
    hair_color: str | None = Field(default=None, pattern=_HEX)
    skin: str | None = Field(default=None, pattern=_HEX)
    beard: LookBeard | None = None
    frame: LookFrame | None = None
    beast_ears: LookBeastEars | None = None

    def is_empty(self) -> bool:
        """全部照種族預設。"""
        return all(getattr(self, name) is None for name in type(self).model_fields)


class LookRange(ContentModel):
    """一般敵人的外觀範圍（Phase QK-6a，#137 第 4 點；``docs/art/外觀變化方案.md`` 第 4 節）：
    **只在畫面**，不影響戰鬥規則。開戰建立單位時依單位 id 的 FNV-1a 雜湊在範圍裡挑一組
    （:func:`trpg.content.enemy_looks.ordinary_enemy_doll`），寫進 ``DollLook.custom``。

    ``race`` 是**外觀參照的種族**（範圍必須在該族 ``look_options`` 內，載入時檢查），不是引擎的
    ``UnitTemplate.race``（不給種族技、不改被動）。各欄空＝這項不變（照範本）。只有人形（紙娃娃、
    沒有 ``creature``）、非召喚的範本可以寫；頭目照寫也不挑。"""

    race: str = Field(default="human", pattern=ID_PATTERN)
    skin: tuple[Annotated[str, Field(pattern=_HEX)], ...] = ()
    hair: tuple[LookHair, ...] = ()
    hair_color: tuple[Annotated[str, Field(pattern=_HEX)], ...] = ()
    beard: tuple[LookBeard, ...] = ()

    @model_validator(mode="after")
    def _check_range(self) -> LookRange:
        names = ("skin", "hair", "hair_color", "beard")
        if all(not getattr(self, name) for name in names):
            raise ValueError("look_range 至少要有一項範圍（skin／hair／hair_color／beard）")
        for name in names:
            values = getattr(self, name)
            if len(set(values)) != len(values):
                raise ValueError(f"look_range.{name} 不可重複")
        return self


class DollLook(ContentModel):
    """單位範本的紙娃娃外觀（Phase 3E-2e，純顯示資料，不進引擎結算）。

    頭身手腳披風與副手（``gear``）、膚色髮型（``skin``／``hair``／…）與稀有度外光；主手由武器的
    ``look`` 決定，``main_style`` 只覆寫主手的材質或顏色（例如生鏽的劍）。範本沒有 ``doll`` 時，
    前端依陣營退回預設外觀。

    Phase 5A-ART：``creature`` 有值時前端改用異形畫法（不畫紙娃娃；``rarity`` 仍是頭目外光）；
    ``affixes`` 是精英詞綴的外觀 id（套詞綴時由 :func:`trpg.content.world_enemies.apply_affix`
    加上）；``main_kind`` 覆寫主手造型（拂塵、符紙、傀儡線）、``main_tassel`` 劍穗色、
    ``bun_band`` 髮髻的髮帶色、``beard`` 鬍子、``build`` 體型；
    5A-ART5 加 ``main_glow`` 杖頭光色、``scale`` 戰場大小。都經 ``UnitView.doll_look`` 給前端
    （不改引擎）。
    """

    skin: str = Field(default="#f1c9a5", pattern=_HEX)
    hair: DollHair | None = None
    hair_color: str | None = Field(default=None, pattern=_HEX)
    pants: str | None = Field(default=None, pattern=_HEX)
    trim: str | None = Field(default=None, pattern=_HEX)
    eyes: str | None = Field(default=None, pattern=_HEX)
    skull: bool = False
    gear: dict[DollSlot, DollGear] = Field(default_factory=dict)
    main_material: str | None = Field(default=None, pattern=ID_PATTERN)
    main_color: str | None = Field(default=None, pattern=_HEX)
    rarity: Literal["epic", "legendary"] | None = None
    main_kind: str | None = Field(default=None, pattern=ID_PATTERN)
    main_tassel: str | None = Field(default=None, pattern=_HEX)
    bun_band: str | None = Field(default=None, pattern=_HEX)
    beard: bool = False
    build: Literal["stout", "tall"] | None = None
    main_glow: str | None = Field(default=None, pattern=_HEX)
    """杖頭光色（Phase 5A-ART5；青霧道童的綠光）：主手是杖時取代預設光色，附魔元素仍優先。"""
    scale: float | None = Field(default=None, ge=0.5, le=1.5)
    """人形在戰場上的大小倍率（Phase 5A-ART5；道童小一號 0.9）。

    精英 ×1.15 照乘；異形用 ``creature.size``。"""
    creature: CreatureLook | None = None
    affixes: tuple[Annotated[str, Field(pattern=ID_PATTERN)], ...] = Field(default=(), max_length=8)
    traits: tuple[Annotated[str, Field(pattern=ID_PATTERN)], ...] = Field(default=(), max_length=8)
    """人形也能帶的特徵（霧鎖真人的 ``mist`` 霧氣繞身、雷符師的 ``sparks`` 電光）；異形的特徵寫在
    ``creature.traits``。前端不認得的略過。"""
    custom: LookChoice | None = None
    """玩家自己選的外觀（Phase 6R-2，#137）：只有主角有；前端疊在種族外觀之後。單位範本不寫。"""


HitCondition = Literal["always", "target_in_water", "self_in_water"]
"""召喚物命中特性的條件（Phase 3-33e1）：無條件、目標站在水面上、自己站在水面上。"""


class SummonHitRule(ContentModel):
    """召喚物普攻命中後的條件特性（Phase 3-33e1；初值，未經模擬）。

    ``when`` 成立時：對目標施加 ``status``（``duration`` 回合）；並讓雷電沿著水面連鎖到目標附近
    （曼哈頓距離 ``chain_radius`` 以內）最多 ``chain_targets`` 名其他敵人，各吃武器骰 ×
    ``chain_permille``‰
    的傷害（元素取武器元素）。冰靈（命中潮濕目標時冰凍）、雷靈（站在水裡時連鎖）、鷹隼（揭露並標記）。
    """

    when: HitCondition = "always"
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    duration: int = Field(default=2, ge=1, le=6)
    chain_targets: int = Field(default=0, ge=0, le=3)
    chain_radius: int = Field(default=1, ge=1, le=3)
    chain_permille: int = Field(default=500, ge=0, le=2000)

    @model_validator(mode="after")
    def _has_effect(self) -> SummonHitRule:
        if self.status is None and self.chain_targets == 0:
            raise ValueError("命中特性至少要有狀態或連鎖")
        return self


class SummonDetonate(ContentModel):
    """召喚物的自爆（Phase 3-33e2a，爆裂傀儡；初值，未經模擬）。

    召喚物走到敵人相鄰的格子時（自己的回合開始時已經相鄰、或被打倒時也一樣）爆炸：曼哈頓距離
    ``radius`` 以內的敵人各受 ``dice`` ＋ ``flat`` 的 ``element`` 傷害，爆心與周圍各格留下
    ``surface``，召喚物自己消失。
    """

    radius: int = Field(default=1, ge=1, le=2)
    dice: Dice
    flat: int = Field(default=0, ge=0, le=20)
    element: Element = Element.FIRE
    surface: Surface | None = None


class SummonPulse(ContentModel):
    """召喚物自己的回合開始時的脈動（Phase 3-33e1，水精；3-33e2b 擴充）。

    - 在自己腳下造 ``surface``；
    - 治療曼哈頓距離 ``heal_radius`` 以內受傷的友方（不含自己；骰 ``heal_dice`` ＋ ``heal_flat``）；
    - 護盾（守護靈）：``shield_dice``／``shield_flat`` 有值時，給 **最虛弱** 的友方（含召喚者與其他
      召喚物，不含自己；HP 比例最低，再依 HP、單位 ID）一層護盾；
    - 拉扯（吸引圖騰）：``pull_radius`` 大於 0 時，把範圍內最近的一個敵人往自己拉近 1 格
      （確定性選目標：距離最近、再依座標 ``(y, x)``；拉不動的略過）。
    """

    surface: Surface | None = None
    heal_radius: int = Field(default=1, ge=1, le=3)
    heal_dice: Dice | None = None
    heal_flat: int = Field(default=0, ge=0, le=10)
    shield_dice: Dice | None = None
    shield_flat: int = Field(default=0, ge=0, le=10)
    pull_radius: int = Field(default=0, ge=0, le=4)

    @model_validator(mode="after")
    def _has_effect(self) -> SummonPulse:
        if (
            self.surface is None
            and self.heal_dice is None
            and self.heal_flat == 0
            and self.shield_dice is None
            and self.shield_flat == 0
            and self.pull_radius == 0
        ):
            raise ValueError("脈動至少要有表面、治療、護盾或拉扯")
        return self


class SummonSnare(ContentModel):
    """纏繞（Phase 3-33e2b，藤蔓）：敵人踏入（走進、被推進、被拉進）自己相鄰的格子時，施加
    ``status``（``duration`` 回合）；``prone`` 為真時並使其倒地。每隻每輪最多觸發 1 次。"""

    status: str = Field(default="slow", pattern=ID_PATTERN)
    duration: int = Field(default=2, ge=1, le=6)
    prone: bool = True


class SummonPlatform(ContentModel):
    """高台（Phase 3-33e2b，高台圖騰）：召喚時在旁邊（曼哈頓距離 1）升起 1 格高台（地形高度 +1），
    召喚物消失時恢復。目前只支援 1 層（恢復時不結算墜落）。"""

    height: int = Field(default=1, ge=1, le=1)


SUMMON_ROLES: tuple[str, ...] = (
    "melee",
    "ranged",
    "support",
    "totem",
    "scout",
    "assassin",
    "bomber",
)
"""召喚物定位（Phase 3-33f1）：近戰擋路、遠程、治療輔助、不動型（圖騰、藤蔓、土牆）、斥候、刺殺、
自爆。"""

type SummonRole = Literal["melee", "ranged", "support", "totem", "scout", "assassin", "bomber"]


class OpeningStatus(ContentModel):
    """範本開場就帶著的狀態（Phase 5A-M1：霧隱的開場隱蔽 1 回合、碎晶傀儡的死後碎片）。

    ``duration`` 省略＝狀態定義的預設；有限的持續回合在開戰時最多 2（5A-6b，
    ``OPENING_STATUS_MAX_DURATION``）。"""

    status: str = Field(pattern=ID_PATTERN)
    duration: int | None = Field(default=None, ge=1, le=2)


class HpBelowTrigger(ContentModel):
    """Boss 階段的觸發（Phase 5F-2）：HP ≤ 最大 HP × ``permille``‰ 時進入。"""

    kind: Literal["hp_below"]
    permille: int = Field(ge=1, le=999)

    @property
    def condition_zh(self) -> str:
        return f"HP {self.permille // 10}% 以下"


class TagDownTrigger(ContentModel):
    """Boss 階段的觸發（Phase 5F-3，賽季 Boss 的解謎）：同陣營、帶 ``tag`` 標籤的單位已倒下
    ``count`` 名以上時進入（例：3 根源晶柱都被打碎）。``tag_name_zh`` 是標籤在畫面上的中文名
    （省略時顯示標籤 ID）。"""

    kind: Literal["tag_down"]
    tag: str = Field(pattern=ID_PATTERN)
    count: int = Field(ge=1, le=8)
    tag_name_zh: str | None = Field(default=None, min_length=1)

    @property
    def condition_zh(self) -> str:
        return f"「{self.tag_name_zh or self.tag}」倒下 {self.count} 名"


class RoundTrigger(ContentModel):
    """Boss 階段的觸發（Phase 5F-3）：第 ``round`` 輪起進入（例：第 15 輪起傷害加倍，防止拖延）。"""

    kind: Literal["round_at"]
    round: int = Field(ge=2, le=99)

    @property
    def condition_zh(self) -> str:
        return f"第 {self.round} 輪起"


type PhaseTrigger = Annotated[
    HpBelowTrigger | TagDownTrigger | RoundTrigger, Field(discriminator="kind")
]
"""Boss 階段的觸發種類（依 ``kind`` 區分；新種類加在這裡，不動舊資料）。"""


class PhaseTile(ContentModel):
    """階段轉換時改變的一格（同地圖事件 ``terrain_change`` 的格子：高度、地形、表面；省略的
    不變）。"""

    at: tuple[int, int]
    height: int | None = Field(default=None, ge=0, le=3)
    terrain: str | None = Field(default=None, pattern=ID_PATTERN)
    surface: Surface | None = None

    @model_validator(mode="after")
    def _check(self) -> PhaseTile:
        if self.height is None and self.terrain is None and self.surface is None:
            raise ValueError("階段的 tiles 每一格至少要改變 height、terrain 或 surface 其中之一")
        return self


class PhaseSpawn(ContentModel):
    """階段轉換時召喚的單位（和 Boss 同陣營）。``at`` 省略＝Boss 當下的位置（改到最近的安全格）。"""

    template: str = Field(pattern=ID_PATTERN)
    count: int = Field(default=1, ge=1, le=4)
    at: tuple[int, int] | None = None


class BossPhase(ContentModel):
    """Boss 的一個階段（Phase 5F-2，09 9.6.8、18.2.3）。

    第 1 項是開場階段：只有 ``id``、``name_zh``（範本本身就是它）；之後每項必有 ``trigger``，
    進入時依序：移除狀態 → 換技能組 → 換行為模式 → 回復法力（BAL-21a）→ 施加狀態 → 改天氣 →
    改格子 → 召喚
    （:mod:`trpg.engine.boss_phases`）。省略的欄位不變。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    trigger: PhaseTrigger | None = None
    text_zh: str | None = Field(default=None, min_length=1)
    """轉換時的一句敘事（戰鬥紀錄與前端提示）。"""
    skills: tuple[str, ...] | None = Field(default=None, max_length=32)
    ai_profile: str | None = Field(default=None, pattern=ID_PATTERN)
    remove_statuses: tuple[str, ...] = ()
    add_statuses: tuple[OpeningStatus, ...] = ()
    weather: str | None = Field(default=None, pattern=ID_PATTERN)
    tiles: tuple[PhaseTile, ...] = ()
    spawns: tuple[PhaseSpawn, ...] = ()
    mana_restore: int | None = Field(default=None, ge=1, exclude_if=lambda v: v is None)
    """進入這個階段時回復的法力點數（BAL-21a；不超過最大法力）。``None``＝不回復（預設），不輸出，
    沒填的頭目規則包雜湊不變。"""

    @property
    def is_opening(self) -> bool:
        return self.trigger is None

    def changes_anything(self) -> bool:
        return bool(
            self.skills is not None
            or self.ai_profile is not None
            or self.remove_statuses
            or self.add_statuses
            or self.weather is not None
            or self.tiles
            or self.spawns
            or self.text_zh is not None
            or self.mana_restore is not None
        )


PHASES_MIN = 2
PHASES_MAX = 4
"""``phases`` 的項數範圍（開場階段＋1～3 次轉換；09 9.6.8「2～3 個階段」，留一格給之後的 Boss）。"""


def check_phases(phases: tuple[BossPhase, ...]) -> list[str]:
    """``UnitTemplate.phases`` 的結構問題（空列表＝沒問題）。"""
    if not phases:
        return []
    problems: list[str] = []
    if not PHASES_MIN <= len(phases) <= PHASES_MAX:
        problems.append("phases 要有 2～4 項（開場階段＋1～3 次轉換）")
    first = phases[0]
    if not first.is_opening or first.changes_anything():
        problems.append("phases 第 1 項是開場階段：只能有 id 與 name_zh")
    last = 1000
    for phase in phases[1:]:
        if phase.trigger is None:
            problems.append(f"階段 {phase.id} 缺少 trigger（只有第 1 項可以省略）")
            continue
        if not isinstance(phase.trigger, HpBelowTrigger):  # 5F-3：其他種類不排序
            continue
        if phase.trigger.permille >= last:
            problems.append(f"階段 {phase.id} 的 HP 門檻必須比前一個階段低")
        last = phase.trigger.permille
    ids = [p.id for p in phases]
    if len(set(ids)) != len(ids):
        problems.append("phases 的 id 不能重複")
    return problems


def template_part_problems(template: UnitTemplate) -> list[str]:
    """``UnitTemplate.parts``（PB-1a）的結構問題（範本驗證時檢查）：只給頭目、不給召喚物；2～4 個、
    ID 不重複、``hp_permille`` 加總 ≤ 600‰。"""
    parts = template.parts
    if not parts:
        return []
    problems: list[str] = []
    if BOSS_TAG not in template.tags:
        problems.append("只有帶 boss 標籤的單位能有 parts")
    if template.summon:
        problems.append("召喚物不能有 parts")
    return problems + check_parts(parts)


def part_reference_problems(template: UnitTemplate) -> list[str]:
    """``parts`` 引用同一範本其他欄位的問題（載入內容庫時檢查，不放在範本驗證——測試與工具常把
    ``phases``、``skills`` 換掉再組範本）：封的招要在 ``skills`` 或任一階段的技能組裡；
    ``exposed_in`` 是這個範本的階段 ID。訊息指出部位 ID。"""
    problems: list[str] = []
    phase_ids = {p.id for p in template.phases}
    skills = {*template.skills, *(s for p in template.phases for s in p.skills or ())}
    for part in template.parts:
        unknown = [p for p in part.exposed_in if p not in phase_ids]
        if unknown:
            problems.append(
                f"部位 {part.id} 的 exposed_in 不是這個單位的階段：{'、'.join(unknown)}"
            )
        for effect in part.on_break:
            if isinstance(effect, SealSkillBreak) and effect.skill not in skills:
                problems.append(
                    f"部位 {part.id} 封的招 {effect.skill} 不在這個單位的技能組（含各階段）裡"
                )
    return problems


class UnitTemplate(ContentModel):
    """``content/units/<id>.yaml``：一個單位範本（Phase 1 直接給定屬性與武器）。

    - ``resist``：4 組抗性（‰），未列出的分組為 0；可為負值表示易傷。
    - ``element_mods``：個別元素的弱點（正值）或抗性（負值），‰。
    - ``stamina``：耐力基礎（武器技、格擋等反應消耗）；省略時依武器大類（``rules/core.yaml`` 的
      ``resources.class_base``，BAL-15b），上限再加屬性加成。
    - ``reactions``：反應規則；省略時用 ``reactions.yaml`` 的 ``default_rules``；
      ``[]`` 表示沒有反應。
    - ``ai_profile``：效用 AI 的行為模式（``ai_profiles.yaml``）；省略時遠程武器用 ``archer``、
      其他用 ``brute``。
    - ``skills``：裝備的技能 ID（``content/skills/``，順序即 ``legal_actions`` 的順序）；數量上限依
      ``core.yaml`` 的 ``skill_slots``，``weapon_req`` 必須與武器的 ``weapon_class`` 相容
      （載入時檢查）。
    - ``max_mana``：法力基礎（戰鬥開始時為滿，只在營火回滿）；省略時依武器大類（BAL-15b），上限
      再加屬性加成並 × ``mana_cap_permille``。
    - ``summon``：召喚物範本（Phase 3D-4a；放在 ``content/units/summons/``，只能由 ``summon``
      原語產生，不能直接參戰）。
    - ``totem``：圖騰（Phase 3D-4b；不移動、不攻擊，只提供光環）。
    - ``equipment``：裝備（Phase 3G-G1）：欄位 → ``items.yaml`` 的物品 id。省略為沒有裝備；主手沒有
      物品時 ``weapon`` 就是主手（舊資料不必改）；主手有物品時，物品的武器必須等於 ``weapon``。
    - 元素修正 ＝ (1 − 分組抗性) × (1 + 個別弱點 − 個別抗性)，
      下限見 ``element_mod_floor_permille``。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    attributes: dict[Attribute, int]
    max_hp: int = Field(ge=1)
    speed: int = Field(default=5, ge=0)
    armor_bonus: int = 0
    weapon: str = Field(pattern=ID_PATTERN)
    resist: dict[ResistGroup, int] = Field(default_factory=dict, validate_default=True)
    element_mods: dict[Element, int] = Field(default_factory=dict)
    tags: tuple[str, ...] = ()
    stamina: int | None = Field(default=None, ge=0)
    reactions: tuple[ReactionRule, ...] | None = None
    ai_profile: str | None = Field(default=None, pattern=ID_PATTERN)
    skills: tuple[str, ...] = Field(default=(), max_length=32)
    max_mana: int | None = Field(default=None, ge=0)
    scaled_resources: bool = False
    """舊旗標（Phase 3H-2：只有主角的法力與耐力上限依屬性）。BAL-15b（玩法決定 #80）起敵我同一套
    公式，引擎不再看這個旗標；保留欄位讓舊存檔與舊資料照常載入。``max_mana``／``stamina`` 是基礎
    值（省略時依武器大類，``core.yaml`` 的 ``resources.class_base``），引擎再加屬性加成。"""
    summon: bool = False
    totem: TotemSpec | None = None
    """圖騰（Phase 3D-4b）：必須是召喚物、速度 0；沒有行動，只在自己的回合開始時給光環。"""
    default_mode: Literal["guard", "follow", "hold"] = "follow"
    """召喚物剛召喚時的模式（Phase 3-33c；6.29.5「AI 預設」欄：守衛＝``guard``、不動＝``hold``，
    其餘與沒寫＝``follow``）。集火要指定目標，不能當預設。"""
    role: SummonRole | None = None
    """召喚物定位（Phase 3-33f1，6.29.5「定位」欄）：決定 HP 係數（``core.yaml`` 的
    ``summon_role_hp_permille``）；召喚物必填，非召喚物不可填。"""
    doll: DollLook | None = None
    """紙娃娃外觀（Phase 3E-2e）：頭身手腳披風、膚色髮型；經 ``UnitView.doll_look`` 給前端，
    沒有時前端依陣營退回預設外觀。"""
    look: SummonLook | None = None
    """召喚物外觀（Phase 3-33h1）：**不寫在範本檔裡**——唯一來源是 ``content/summon_looks.yaml``，
    載入內容庫時依範本 ID 查表填入（Phase 3-33h2）；嵌入規則包，重播不依賴資料檔。"""
    innate: str | None = Field(default=None, pattern=ID_PATTERN)
    """固有的灌注關鍵字（Phase 3-33e1，6.29.5「關鍵字」欄）：召喚物一律帶有，效果見 ``core.yaml`` 的
    ``summon_infusions``；與召喚時施放者選的灌注關鍵字並存（相同時只算一次）。"""
    hit_rules: tuple[SummonHitRule, ...] = ()
    """普攻命中後的條件特性（Phase 3-33e1）。"""
    pulse: SummonPulse | None = None
    """回合開始的脈動（Phase 3-33e1）。"""
    detonate: SummonDetonate | None = None
    """自爆（Phase 3-33e2a）：走到敵人相鄰、回合開始時已相鄰或被打倒時爆炸並消失。"""
    snare: SummonSnare | None = None
    """纏繞（Phase 3-33e2b，藤蔓）：敵人踏入相鄰格時施加狀態。"""
    platform: SummonPlatform | None = None
    """召喚時在旁邊升起高台（Phase 3-33e2b，高台圖騰）。"""
    inert: bool = False
    """沒有行動（Phase 3-33e2a 土牆、3-33e2b）：AP 恆為 0（不移動、不攻擊）、不能操控，只有回合開始
    的脈動與被動特性；圖騰（``totem``）本來就是如此，這個旗標給沒有光環的純功能召喚物。"""
    equipment: dict[Slot, str] = Field(default_factory=dict)
    """裝備（Phase 3G-G1）：欄位 → 物品 id（``content/items.yaml``）。"""
    race: str | None = Field(default=None, pattern=ID_PATTERN)
    """可玩種族（Phase 3R-2，``content/races.yaml``）：帶種族的單位有 1 招種族技與 1 項環境被動
    （:mod:`trpg.engine.race.skills`、:mod:`trpg.engine.race_passives`）；省略＝無種族（預設）。"""
    level: int = Field(default=1, ge=1, le=99)
    """角色等級（Phase 3-33b）：召喚物的 HP 與傷害依施放者的等級成長；一輪的主角帶入目前等級，
    其他單位為 1。"""
    opening_statuses: tuple[OpeningStatus, ...] = ()
    """開場就帶著的狀態（Phase 5A-M1）：開戰時在擲先攻前施加、不擲抵抗（同
    ``UnitSpawn.opening_statuses``，先施加範本的）。"""
    look_range: LookRange | None = None
    """一般敵人的外觀範圍（Phase QK-6a，#137 第 4 點；純顯示）：開戰時依單位 id 挑一組寫進
    ``doll.custom``（:func:`trpg.content.enemy_looks.ordinary_enemy_doll`）。只有人形、非召喚的
    範本可以寫；頭目（``tags`` 含 ``boss``）就算有寫也不挑（外觀固定）。值要在
    ``look_range.race`` 的 ``look_options`` 內（載入內容庫時檢查）。"""
    phases: tuple[BossPhase, ...] = ()
    """Boss 的階段（Phase 5F-2）：HP 跌破門檻時換技能組／行為模式、加減狀態、改天氣與格子、召喚
    （:class:`BossPhase`、:mod:`trpg.engine.boss_phases`）；空＝沒有階段。"""
    parts: tuple[BossPart, ...] = Field(default=(), exclude_if=lambda v: not v)
    """頭目部位（PB-1a，05 5.12.2；:mod:`trpg.content.parts`）：只有帶 ``boss`` 標籤、不是召喚物的
    範本能有；空＝沒有部位（不輸出）。"""

    @model_validator(mode="after")
    def _check_parts(self) -> UnitTemplate:
        if not self.parts:
            return self
        problems = [f"單位 {self.id}：{p}" for p in template_part_problems(self)]
        if problems:
            raise ValueError("；".join(problems))
        return self

    @model_validator(mode="after")
    def _check_phases(self) -> UnitTemplate:
        problems = check_phases(self.phases)
        if problems:
            raise ValueError("；".join(problems))
        if self.phases and self.summon:
            raise ValueError("召喚物不能有 phases")
        return self

    @model_validator(mode="after")
    def _check_look_range(self) -> UnitTemplate:
        if self.look_range is None:
            return self
        if self.summon:
            raise ValueError("召喚物不能寫 look_range")
        if self.doll is None or self.doll.creature is not None:
            raise ValueError("look_range 只給人形（有 doll、沒有 creature）的範本")
        if self.doll.custom is not None:
            raise ValueError("寫了 doll.custom 的範本不能再寫 look_range")
        return self

    @model_validator(mode="after")
    def _check_totem(self) -> UnitTemplate:
        if self.totem is not None and not (self.summon and self.speed == 0):
            raise ValueError("圖騰必須是召喚物（summon: true）且 speed 為 0")
        return self

    @model_validator(mode="after")
    def _check_role(self) -> UnitTemplate:
        if self.summon and self.role is None:
            raise ValueError("召喚物必須填 role（定位：" + "、".join(SUMMON_ROLES) + "）")
        if self.role is not None and not self.summon:
            raise ValueError("定位 role 只有召喚物（summon: true）可以填")
        return self

    @model_validator(mode="after")
    def _check_look(self) -> UnitTemplate:
        if self.look is not None and not self.summon:
            raise ValueError("外觀欄位 look 只有召喚物（summon: true）可以填")
        if not self.summon and (
            self.innate
            or self.hit_rules
            or self.pulse
            or self.detonate
            or self.snare
            or self.platform
            or self.inert
        ):
            raise ValueError(
                "innate／hit_rules／pulse／detonate／snare／platform／inert"
                " 只有召喚物（summon: true）可以填"
            )
        return self

    @field_validator("equipment")
    @classmethod
    def _equipment_format(cls, value: dict[Slot, str]) -> dict[Slot, str]:
        bad = [i for i in value.values() if re.match(ID_PATTERN, i) is None]
        if bad:
            raise ValueError(f"物品 ID 格式錯誤：{', '.join(bad)}")
        return value

    @field_validator("skills")
    @classmethod
    def _skills_format(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        bad = [s for s in value if re.match(r"^skill_[a-z0-9_]+$", s) is None]
        if bad:
            raise ValueError(f"技能 ID 格式應為 skill_xxx：{', '.join(bad)}")
        if len(set(value)) != len(value):
            raise ValueError("技能不可重複裝備")
        return value

    @field_validator("attributes")
    @classmethod
    def _all_attributes(cls, value: dict[Attribute, int]) -> dict[Attribute, int]:
        missing = [a.value for a in Attribute if a not in value]
        if missing:
            raise ValueError(f"缺少屬性：{', '.join(missing)}")
        bad = [f"{a.value}={v}" for a, v in value.items() if not 1 <= v <= _MAX_ATTR]
        if bad:
            raise ValueError(f"屬性值必須在 1–{_MAX_ATTR}：{', '.join(bad)}")
        return {a: value[a] for a in Attribute}

    @field_validator("resist")
    @classmethod
    def _resist_range(cls, value: dict[ResistGroup, int]) -> dict[ResistGroup, int]:
        bad = [f"{g.value}={v}" for g, v in value.items() if not -_PERMILLE <= v <= _PERMILLE]
        if bad:
            raise ValueError(f"分組抗性必須在 -1000–1000‰：{', '.join(bad)}")
        return {g: value.get(g, 0) for g in ResistGroup}

    @field_validator("element_mods")
    @classmethod
    def _element_mod_range(cls, value: dict[Element, int]) -> dict[Element, int]:
        bad = [f"{e.value}={v}" for e, v in value.items() if v < -_PERMILLE]
        if bad:
            raise ValueError(f"個別元素修正不可低於 -1000‰：{', '.join(bad)}")
        return {e: value[e] for e in Element if e in value}

    @field_validator("tags")
    @classmethod
    def _tags_format(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        bad = [t for t in value if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"標籤必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(value)) != len(value):
            raise ValueError("標籤不可重複")
        return tuple(sorted(value))

    def summary(self) -> str:
        return f"{self.name_zh}（HP {self.max_hp}，武器 {self.weapon}）"
