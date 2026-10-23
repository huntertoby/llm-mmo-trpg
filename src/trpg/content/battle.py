"""戰鬥用的內容 schema：骰子、地形、武器、狀態、單位範本。

對應資料檔：``content/terrain.yaml``、``content/weapons.yaml``、``content/statuses.yaml``、
``content/units/*.yaml``。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Literal

from pydantic import Field, field_validator, model_serializer, model_validator

from trpg.content.schemas import ContentModel
from trpg.content.slots import Slot
from trpg.shared.types import Attribute, Element, ResistGroup, Surface

if TYPE_CHECKING:
    from trpg.content.rules import CoreRules

__all__ = [
    "ID_PATTERN",
    "SUMMON_MODES",
    "ArmorBreak",
    "Blessing",
    "Dice",
    "DollGear",
    "DollLook",
    "HitCondition",
    "ReactionRule",
    "ReactionUnless",
    "ReactionWhen",
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
    "TerrainDef",
    "TerrainTable",
    "TotemSpec",
    "UnitTemplate",
    "WeaponDef",
    "WeaponLook",
    "WeaponTable",
]

ID_PATTERN = r"^[a-z][a-z0-9_]*$"
"""內容 ID 與標籤的格式：小寫英文開頭的 snake_case。"""

_DICE_RE = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*$")
_MAX_DICE_COUNT = 100
_MAX_DICE_SIDES = 1000
_MIN_LISTED_LEVEL = 2
_MAX_SKILL_LEVEL = 9
"""技能等級的格式上限（實際上限是 ``skill_growth.yaml`` 的 ``max_level``，由引擎與一輪檢查）。"""


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
      ``attr_mode`` 決定（Phase 3H-1，08 8.11）：``mean`` 取平均（無條件捨去；重武器，要兩個都點）、
      ``max`` 取較高者（輕武器，靈巧）。沒有第二屬性時 ``attr_mode`` 不影響結果。
    - ``armor_break``：破甲，見 :class:`ArmorBreak`。
    - ``knockback``：震退——普攻命中後把目標沿攻擊方向推這麼多格（沿用推擊與撞擊規則）。
    - ``reach``：觸及——藉機攻擊的範圍（目標從 ``reach`` 格內走到 ``reach`` 格外時可以反應）；
      不可超過 ``range``。
    - ``blessing``：祝禱，見 :class:`Blessing`。
    - ``summon_dice_bonus``：統御——持有者召喚物的普攻多加這麼多顆傷害骰。
    - ``lob``：拋射——視線可以越過這麼多層高的障礙（物件、地形高差；牆壁與黑暗不行）。

    遠程武器小特性（Phase 3-24a2；同樣只是參數，引擎只讀參數）：

    - ``pierce_line``：穿透一直線——普攻命中（結算）目標之後，子彈／弩箭沿同一直線繼續飛，最多再
      擊中這麼多名射程內、視線未被擋住的敵人（各自擲命中與傷害）；
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
    armor_break: ArmorBreak | None = None
    knockback: int = Field(default=0, ge=0, le=3)
    reach: int = Field(default=1, ge=1)
    blessing: Blessing | None = None
    summon_dice_bonus: int = Field(default=0, ge=0, le=3)
    lob: int = Field(default=0, ge=0, le=2)
    pierce_line: int = Field(default=0, ge=0, le=8)
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
    look: WeaponLook | None = None
    """預設外觀（Phase 3E-2e）：紙娃娃主手與武器小圖示的造型；經 glossary API 給前端。"""

    @model_validator(mode="after")
    def _check(self) -> WeaponDef:
        if self.magazine > 0 and self.lob > 0:
            raise ValueError(f"武器 {self.id}：有彈匣的武器是直射，不可同時有 lob（拋射）")
        if self.secondary_scaling_attr == self.scaling_attr:
            raise ValueError(f"武器 {self.id}：secondary_scaling_attr 不可和 scaling_attr 相同")
        if self.reach > self.range:
            raise ValueError(f"武器 {self.id}：reach（{self.reach}）不可超過 range（{self.range}）")
        return self

    @property
    def is_melee(self) -> bool:
        """近戰類武器（含長柄）：看大類，不看射程（矛的射程是 2，仍是近戰）。"""
        return self.weapon_class == "melee"

    def rule_lines_zh(self, core: CoreRules) -> tuple[str, ...]:
        """武器卡的共用規則（Phase 3-41b，清單 7.2、7.3）：握法（單手／雙手）與近戰武器共用的背刺。
        數字取自 ``rules/core.yaml``，改規則說明跟著變。"""
        lines = [
            "雙手：占用副手欄位，不能再裝備盾或副手物品"
            if self.two_handed
            else "單手：副手欄位可以放盾或副手物品"
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
        if on_hit_only:
            return tuple(lines)
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


def _signed(value: int) -> str:
    return f"+{value}" if value > 0 else f"−{-value}"


def _weapon_ranged_lines(w: WeaponDef) -> list[str]:
    lines: list[str] = []
    if w.pierce_line:
        lines.append("穿透：命中後箭矢貫穿同一直線上的後方敵人")
    if w.ignore_height:
        lines.append("不受高度影響：命中沒有高低差修正")
    if w.magazine:
        lines.append(f"彈匣 {w.magazine} 發：開火後空膛，裝填花 {w.reload_ap} AP（空膛時才能裝填）")
        lines.append("直射：不能拋射，視線被擋就不能打")
    if w.gunshot:
        lines.append("槍聲：開火會解除自己的隱蔽")
    if w.steady is not None:
        parts = [f"命中 {_signed(w.steady.hit)}"] if w.steady.hit else []
        parts += [f"暴擊範圍 {_signed(w.steady.crit_range)}"] if w.steady.crit_range else []
        lines.append(f"站定狙擊：本回合未移動時開火，{'、'.join(parts)}")
    if w.ignore_cover or w.armor_pierce_permille:
        parts = ["無視半掩護"] if w.ignore_cover else []
        if w.armor_pierce_permille:
            parts.append(f"穿透 {w.armor_pierce_permille / 10:g}% 防禦")
        lines.append(f"直射穿甲：{'、'.join(parts)}")
    for mod in w.range_mod:
        parts = [f"命中 {_signed(mod.hit)}"] if mod.hit else []
        if mod.damage_permille != _NEUTRAL_PERMILLE:
            pct = (mod.damage_permille - _NEUTRAL_PERMILLE) / 10
            parts.append(f"傷害 {'+' if pct > 0 else '−'}{abs(pct):g}%")
        lines.append(f"{mod.label_zh()}：{'、'.join(parts)}")
    return lines


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
# 狀態
# ---------------------------------------------------------------------------


class StatusTickDamage(ContentModel):
    """回合開始時受到的持續傷害。"""

    dice: Dice
    element: Element


class StatusTickHeal(ContentModel):
    """回合開始時的持續治療（Phase 2D-1，再生）。"""

    dice: Dice


class StatusDef(ContentModel):
    """一種狀態。

    - ``duration``：預設持續回合；``None`` 表示不倒數（直到被移除或到期條件成立）。
    - ``expires``：``turn_end`` 每次在帶有者的回合結束時 −1，歸零移除；
      ``own_turn_start`` 在帶有者的下個回合開始時移除；``never`` 只能由效果或動作移除。
    - ``stacking``：重複施加時的規則；目前只有 ``refresh``（刷新持續時間，不疊加）。

    Phase 2B-1 的數值效果欄位（千分比一律 ‰，1000 = ×1；多個狀態的同一欄位依序相乘、逐步
    無條件捨去）：

    - ``move_permille``：回合開始時的移動點數倍率（緩速 500、加速 1500）。
    - ``prevents_move``：不能主動移動（定身；強制位移照常）。
    - ``skip_turn``：回合開始時跳過整個回合，且不能執行反應（暈眩）。
    - ``damage_dealt_permille``：自己造成的攻擊傷害（``cause: attack``）倍率（虛弱 750）。
    - ``damage_taken_permille``：受到的骰值傷害倍率（易傷 1250；不含墜落、致命地形等百分比傷害）。
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

    - ``prevents_death``：不死——帶有者受到傷害、HP 會降到 0 時改為 1 並移除此狀態（墜落與致命
      地形照樣生效）。

    Phase 3D-1 的欄位：

    - ``polarity``：增益／減益／中性分類（必填）。``steal_buff`` 只能奪取 ``buff``；``neutral``
      （姿態、隱蔽、不死、靈魂連結）帶有來源或唯一性語意，不能被奪取。

    Phase 3D-8a 的欄位：

    - ``prevents_concealment``：被揭露（``reveal``）——帶有者不算隱蔽（連黑暗表面與草叢也不算），
      也不能獲得 ``concealed`` 狀態。

    Phase 3C-4b 的欄位：

    - ``redirects_damage``：靈魂連結——帶有者受到的傷害有 ``StatusInstance.amount``‰ 轉給狀態來源
      （``source_id``，施放者）；來源倒下或離場時此狀態立即移除。

    Phase 3-24a1 的欄位：

    - ``defense_break``：破甲——帶有者的防禦值降低 ``StatusInstance.amount``‰（武器的
      ``armor_break`` 施加時帶入；``amount`` 省略時為 100‰）；多個破甲取最大的一個，不疊加。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    duration: int | None = Field(default=None, ge=1)
    expires: Literal["turn_end", "own_turn_start", "never"]
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
    attack_bonus: int = Field(default=0, ge=0, le=10)
    move_permille: int = Field(default=1000, ge=0, le=10000)
    prevents_move: bool = False
    skip_turn: bool = False
    damage_dealt_permille: int = Field(default=1000, ge=0, le=10000)
    damage_taken_permille: int = Field(default=1000, ge=0, le=10000)
    healing_received_permille: int = Field(default=1000, ge=0, le=10000)
    save_attr: Attribute | None = None
    control_group: Literal["movement", "mental", "hard"] | None = None
    budget_points: int | None = Field(default=None, ge=0)
    min_rarity: Literal["common", "rare", "epic", "legendary"] = "common"
    beneficial: bool = False
    polarity: Literal["buff", "debuff", "neutral"]

    @model_validator(mode="after")
    def _check(self) -> StatusDef:
        if self.polarity == "buff" and not self.beneficial:
            raise ValueError(f"狀態 {self.id}：polarity: buff 必須 beneficial: true")
        if self.polarity == "debuff" and self.beneficial:
            raise ValueError(f"狀態 {self.id}：polarity: debuff 不可 beneficial: true")
        if self.stance and (self.expires != "never" or self.duration is not None):
            raise ValueError(f"狀態 {self.id}：姿態（stance）必須 expires: never 且不設 duration")
        if self.control_group is not None and self.save_attr is None:
            raise ValueError(f"狀態 {self.id}：有 control_group 的狀態必須設定 save_attr")
        if self.expires == "turn_end" and self.duration is None:
            raise ValueError(f"狀態 {self.id}：expires 為 turn_end 時必須設定 duration")
        return self


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
        "enemy_moves_in_range",
        "ally_hit_in_range",
    ]


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
"""召喚物體型（Phase 3-33h1，``docs/art/召喚物外觀.md``）：人形用紙娃娃，其餘由前端程式繪製。"""
SummonLookSize = Literal["small", "medium", "large"]
SummonLookTrait = Literal[
    "shield", "translucent", "glow", "puddle", "fuse", "no_ring", "flying", "ground", "aura"
]
"""前端認得的 9 種特徵（Phase 3-33h2）；新增值由美術 PM 補畫法並同步 ``docs/art/召喚物外觀.md``。"""


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


DollSlot = Literal["head", "body", "hands", "feet", "cloak", "off_hand"]
DollHair = Literal["short", "long", "none"]


class DollGear(ContentModel):
    """範本身上的一件外觀裝備（Phase 3E-2e）：造型、材質與染色。"""

    kind: str = Field(pattern=ID_PATTERN)
    material: str = Field(pattern=ID_PATTERN)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class DollLook(ContentModel):
    """單位範本的紙娃娃外觀（Phase 3E-2e，純顯示資料，不進引擎結算）。

    頭身手腳披風與副手（``gear``）、膚色髮型（``skin``／``hair``／…）與稀有度外光；主手由武器的
    ``look`` 決定，``main_style`` 只覆寫主手的材質或顏色（例如生鏽的劍）。範本沒有 ``doll`` 時，
    前端依陣營退回預設外觀。
    """

    skin: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    hair: DollHair | None = None
    hair_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    pants: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    trim: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    eyes: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    skull: bool = False
    gear: dict[DollSlot, DollGear] = Field(default_factory=dict)
    main_material: str | None = Field(default=None, pattern=ID_PATTERN)
    main_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    rarity: Literal["epic", "legendary"] | None = None


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


class UnitTemplate(ContentModel):
    """``content/units/<id>.yaml``：一個單位範本（Phase 1 直接給定屬性與武器）。

    - ``resist``：4 組抗性（‰），未列出的分組為 0；可為負值表示易傷。
    - ``element_mods``：個別元素的弱點（正值）或抗性（負值），‰。
    - ``stamina``：耐力（格擋等反應消耗）；省略時用 ``rules/core.yaml`` 的 ``default_stamina``。
    - ``reactions``：反應規則；省略時用 ``reactions.yaml`` 的 ``default_rules``；
      ``[]`` 表示沒有反應。
    - ``ai_profile``：效用 AI 的行為模式（``ai_profiles.yaml``）；省略時遠程武器用 ``archer``、
      其他用 ``brute``。
    - ``skills``：裝備的技能 ID（``content/skills/``，順序即 ``legal_actions`` 的順序）；數量上限依
      ``core.yaml`` 的 ``skill_slots``，``weapon_req`` 必須與武器的 ``weapon_class`` 相容
      （載入時檢查）。
    - ``max_mana``：法力上限（戰鬥開始時為滿，Phase 2A 不回復）。
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
    max_mana: int = Field(default=0, ge=0)
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
    level: int = Field(default=1, ge=1, le=99)
    """角色等級（Phase 3-33b）：召喚物的 HP 與傷害依施放者的等級成長；一輪的主角帶入目前等級，
    其他單位為 1。"""
    skill_levels: dict[str, int] = Field(default_factory=dict)
    """技能等級（Phase 3-26a）：技能 ID → 等級（2～5；省略的技能是 1 級）。只列出裝備中的技能；
    由一輪的存檔帶入，戰鬥設定因此包含等級，重播一致。"""

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

    @field_validator("skill_levels")
    @classmethod
    def _skill_levels_valid(cls, value: dict[str, int]) -> dict[str, int]:
        bad = [k for k, v in value.items() if not _MIN_LISTED_LEVEL <= v <= _MAX_SKILL_LEVEL]
        if bad:
            raise ValueError(
                f"技能等級必須是 {_MIN_LISTED_LEVEL}～{_MAX_SKILL_LEVEL}（1 級不必列出）："
                f"{', '.join(bad)}"
            )
        return value

    @model_validator(mode="after")
    def _levels_are_equipped(self) -> UnitTemplate:
        stray = sorted(set(self.skill_levels) - set(self.skills))
        if stray:
            raise ValueError(f"skill_levels 只能列出裝備中的技能：{', '.join(stray)}")
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
