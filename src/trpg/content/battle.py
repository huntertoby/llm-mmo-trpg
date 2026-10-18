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
    "Dice",
    "ReactionRule",
    "ReactionUnless",
    "ReactionWhen",
    "StatusDef",
    "StatusTable",
    "StatusTickDamage",
    "TerrainDef",
    "TerrainTable",
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


class WeaponDef(ContentModel):
    """一把武器。

    - ``range``：射程（曼哈頓距離）；``1`` 為近戰（相鄰）。
    - ``crit_range``：暴擊的最低自然骰值，``20`` 表示只有自然 20，``19`` 表示 19–20。
    - ``weapon_class``：武器大類（Phase 2A）：``melee`` 近戰、``ranged`` 遠程、``focus`` 法器；
      技能的 ``weapon_req`` 與之對照。法器的攻擊加值也計入法術技的命中。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    weapon_class: Literal["melee", "ranged", "focus"]
    range: int = Field(ge=1)
    dice: Dice
    flat: int = 0
    attack_bonus: int = 0
    scaling_attr: Attribute
    element: Element = Element.PHYSICAL
    crit_range: int = Field(default=20, ge=2, le=20)
    two_handed: bool = False

    @property
    def is_melee(self) -> bool:
        return self.range == 1


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


class StatusDef(ContentModel):
    """一種狀態。

    - ``duration``：預設持續回合；``None`` 表示不倒數（直到被移除或到期條件成立）。
    - ``expires``：``turn_end`` 每次在帶有者的回合結束時 −1，歸零移除；
      ``own_turn_start`` 在帶有者的下個回合開始時移除；``never`` 只能由效果或動作移除。
    - ``stacking``：重複施加時的規則；目前只有 ``refresh``（刷新持續時間，不疊加）。

    Phase 2B-1 的數值效果欄位（千分比一律 ‰，1000 = ×1；多個狀態的同一欄位依序相乘、逐步
    無條件捨去）：

    - ``move_permille``：回合開始時的移動點數倍率（緩速 500）。
    - ``prevents_move``：不能主動移動（定身；強制位移照常）。
    - ``skip_turn``：回合開始時跳過整個回合，且不能執行反應（暈眩）。
    - ``damage_dealt_permille``：自己造成的攻擊傷害（``cause: attack``）倍率（虛弱 750）。
    - ``damage_taken_permille``：受到的骰值傷害倍率（易傷 1250；不含墜落、致命地形等百分比傷害）。
    - ``healing_received_permille``：受到的治療倍率（中毒 500）。
    - ``save_attr``：由技能或動作施加時，守方抵抗用的屬性（省略表示命中即施加）。
    - ``control_group``：控制類別（``movement``、``hard``），成功施加後觸發控制遞減。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    duration: int | None = Field(default=None, ge=1)
    expires: Literal["turn_end", "own_turn_start", "never"]
    stacking: Literal["refresh"] = "refresh"
    on_turn_start_damage: StatusTickDamage | None = None
    move_permille: int = Field(default=1000, ge=0, le=1000)
    prevents_move: bool = False
    skip_turn: bool = False
    damage_dealt_permille: int = Field(default=1000, ge=0, le=10000)
    damage_taken_permille: int = Field(default=1000, ge=0, le=10000)
    healing_received_permille: int = Field(default=1000, ge=0, le=10000)
    save_attr: Attribute | None = None
    control_group: Literal["movement", "hard"] | None = None

    @model_validator(mode="after")
    def _check(self) -> StatusDef:
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
    event: Literal["targeted_by_melee", "targeted_by_attack", "enemy_leaves_adjacent"]


class ReactionUnless(ContentModel):
    self_stamina_below: int | None = Field(default=None, ge=0)


class ReactionRule(ContentModel):
    """玩家（或範本）預先設定的反應規則（``docs/專案計畫.md`` 5.2.1 的格式）。

    ``mode``：``auto`` 條件成立時自動執行；``prompt`` 暫停結算並詢問（``resolve`` 回傳
    ``pending``，以 ``resume`` 繼續）。
    """

    reaction: str = Field(pattern=ID_PATTERN)
    when: ReactionWhen
    unless: ReactionUnless | None = None
    mode: Literal["auto", "prompt"] = "auto"


# ---------------------------------------------------------------------------
# 單位範本
# ---------------------------------------------------------------------------

_MAX_ATTR = 999
_PERMILLE = 1000


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
