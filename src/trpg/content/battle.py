"""戰鬥用的內容 schema：骰子、地形、武器、狀態、單位範本。

對應資料檔：``content/terrain.yaml``、``content/weapons.yaml``、``content/statuses.yaml``、
``content/units/*.yaml``。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import Field, field_validator, model_serializer, model_validator

from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute, Element, ResistGroup

__all__ = [
    "ID_PATTERN",
    "ArmorBreak",
    "Blessing",
    "Dice",
    "ReactionRule",
    "ReactionUnless",
    "ReactionWhen",
    "StatusDef",
    "StatusTable",
    "StatusTickDamage",
    "StatusTickHeal",
    "TerrainDef",
    "TerrainTable",
    "TotemSpec",
    "UnitTemplate",
    "WeaponDef",
    "WeaponTable",
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


class WeaponDef(ContentModel):
    """一把武器。

    - ``range``：射程（曼哈頓距離）；``1`` 為近戰（相鄰）。
    - ``crit_range``：暴擊的最低自然骰值，``20`` 表示只有自然 20，``19`` 表示 19–20。
    - ``weapon_class``：武器大類（Phase 2A）：``melee`` 近戰、``ranged`` 遠程、``focus`` 法器；
      技能的 ``weapon_req`` 與之對照。法器的攻擊加值也計入法術技的命中。

    武器小特性（Phase 3-24a1）一律是下列參數，引擎只讀參數、不寫死數值（之後的「武器特性強化」
    詞條改這些參數即可）：

    - ``secondary_scaling_attr``：第二縮放屬性；有值時攻擊值與傷害用兩屬性的平均（無條件捨去）。
    - ``armor_break``：破甲，見 :class:`ArmorBreak`。
    - ``knockback``：震退——普攻命中後把目標沿攻擊方向推這麼多格（沿用推擊與撞擊規則）。
    - ``reach``：觸及——藉機攻擊的範圍（目標從 ``reach`` 格內走到 ``reach`` 格外時可以反應）；
      不可超過 ``range``。
    - ``blessing``：祝禱，見 :class:`Blessing`。
    - ``summon_dice_bonus``：統御——持有者召喚物的普攻多加這麼多顆傷害骰。
    - ``lob``：拋射——視線可以越過這麼多層高的障礙（物件、地形高差；牆壁與黑暗不行）。
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
    element: Element = Element.PHYSICAL
    crit_range: int = Field(default=20, ge=2, le=20)
    two_handed: bool = False
    armor_break: ArmorBreak | None = None
    knockback: int = Field(default=0, ge=0, le=3)
    reach: int = Field(default=1, ge=1)
    blessing: Blessing | None = None
    summon_dice_bonus: int = Field(default=0, ge=0, le=3)
    lob: int = Field(default=0, ge=0, le=2)

    @model_validator(mode="after")
    def _check(self) -> WeaponDef:
        if self.secondary_scaling_attr == self.scaling_attr:
            raise ValueError(f"武器 {self.id}：secondary_scaling_attr 不可和 scaling_attr 相同")
        if self.reach > self.range:
            raise ValueError(f"武器 {self.id}：reach（{self.reach}）不可超過 range（{self.range}）")
        return self

    @property
    def is_melee(self) -> bool:
        """近戰類武器（含長柄）：看大類，不看射程（矛的射程是 2，仍是近戰）。"""
        return self.weapon_class == "melee"

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
        if self.summon_dice_bonus:
            lines.append(f"統御：你的召喚物攻擊 +{self.summon_dice_bonus} 顆傷害骰")
        if self.lob:
            lines.append(f"拋射：可越過 {self.lob} 格高的障礙射擊")
        return tuple(lines)


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


class TotemSpec(ContentModel):
    """圖騰（Phase 3D-4b）：不移動、不攻擊的召喚物，只提供光環。

    圖騰自己的回合開始時，曼哈頓距離 ``radius`` 以內（含自己格）的友方（不含其他圖騰）獲得
    ``status`` ``duration`` 回合（已有則刷新）；其餘時間沒有任何動作（AP 為 0）。
    """

    radius: int = Field(ge=1, le=4)
    status: str = Field(pattern=ID_PATTERN)
    duration: int = Field(default=2, ge=1, le=4)


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

    @model_validator(mode="after")
    def _check_totem(self) -> UnitTemplate:
        if self.totem is not None and not (self.summon and self.speed == 0):
            raise ValueError("圖騰必須是召喚物（summon: true）且 speed 為 0")
        return self

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
