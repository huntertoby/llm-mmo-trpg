"""頭目部位（PB-1a；``docs/design/05-戰鬥.md`` 5.12.2、``docs/玩法決定紀錄.md`` #152）。

部位是頭目身上的子目標（不是單位、不能被位移、不擋路）：打中部位時傷害照常算進頭目 HP，同時從
部位的小血條扣同樣的數字（頭目實際扣掉的 HP）。部位血量＝開場時頭目最大 HP × ``hp_permille``‰。

- ``reach``：打得到的條件（每個部位一種）——``any`` 任何方向、``behind`` 從背後近戰（沿用背刺的
  背後格）、``high_or_far`` 從比頭目高 ≥ 1 層的格子或曼哈頓距離 > 3、``disabled`` 頭目倒地、暈眩或
  冰凍時、``ranged`` 這次攻擊不是近戰（GB-1c，#164 R3：同背刺的近戰判斷；巨型頭目的噴口）。
- **巨型頭目的部位綁格**（GB-1c，05 5.12.4 第 3 點、19 19.2.3）：``tiles`` 是部位佔的格子（相對
  中心格的偏移 ``(dx, dy)``，北＝dy −1）；巨型頭目的部位必須有、不重疊、在佔格內，一格的頭目不能有。
  ``melee_from``：近戰要貼著部位的格子（``tile``）或貼著任何一面（``any_face``，核心）。
  ``counts_as_behind``：近戰打這個部位算從背後（R4：背刺加成、條件「目標背後」；遠程照一般部位）。
- ``exposed_in``：只有這些階段（``phases[*].id``）才露出；空＝全程露出。和 ``reach`` 並存。
- ``armor_bonus``／``resist``／``element_mods``：部位自己的防禦；沒寫＝和本體相同（``resist``、
  ``element_mods`` 只覆寫有寫的鍵）。
- ``on_break``：破掉的效果（1～2 項，依序結算；:data:`PartBreakEffect`）。

本模組只放資料 schema 與單檔結構檢查；跨檔引用（狀態存在、封的招在技能組裡、階段 ID）由
:func:`trpg.content.library.unit_checks.unit_part_problems` 與 ``UnitTemplate`` 的驗證檢查。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel
from trpg.shared.types import Element, ResistGroup

__all__ = [
    "PARTS_MAX",
    "PARTS_MIN",
    "PART_HP_TOTAL_MAX",
    "STAT_DOWN_STATS",
    "BossPart",
    "ControlBreak",
    "InterruptChargeBreak",
    "PartBreakEffect",
    "PartReach",
    "SealSkillBreak",
    "StatDownBreak",
    "StopMechanicBreak",
    "check_part_tiles",
    "check_parts",
    "max_part_hp",
    "opening_part_hp",
]

_ID = r"^[a-z][a-z0-9_]*$"
_PERMILLE = 1000

PARTS_MIN = 2
PARTS_MAX = 4
"""每隻頭目的部位數（05 5.12.2 第 1 點）。"""
PART_HP_TOTAL_MAX = 600
"""同一隻頭目的部位 ``hp_permille`` 加總上限（05 5.12.2 第 3 點）。"""

type PartReach = Literal["any", "behind", "high_or_far", "disabled", "ranged"]

type MeleeFrom = Literal["tile", "any_face"]
"""巨型頭目部位的近戰條件（GB-1c，T11）：``tile`` 貼著部位的格子；``any_face`` 貼著任何一面。"""

STAT_DOWN_STATS: tuple[str, ...] = (
    "move",
    "armor",
    "hit",
    *(f"resist.{g.value}" for g in ResistGroup),
    "damage_dealt",
)
"""``stat_down.stat`` 的允許值：``move``（格）、``armor``（點）、``hit``（點）、
``resist.<組>``（‰）、``damage_dealt``（造成的傷害倍率，‰；R4）。"""


class SealSkillBreak(ContentModel):
    """封住一招（換階段不解除）；頭目正在蓄力這一招就一起打斷。

    ``rounds``（GB-1c，T14）：有值時只封這麼多輪——從破壞那一輪（第 N 輪）起算，第 N＋rounds 輪
    開始解封；``None``＝永久（同段 1，不輸出）。"""

    type: Literal["seal_skill"] = "seal_skill"
    skill: str = Field(pattern=r"^skill_[a-z0-9_]+$")
    rounds: int | None = Field(default=None, ge=1, exclude_if=lambda v: v is None)


class StatDownBreak(ContentModel):
    """一項能力下降。``amount``：``move`` 格、``armor``／``hit`` 點、``resist.<組>`` 降低的抗性‰
    （都是正數＝降低量）；``damage_dealt`` 是造成傷害的倍率‰（750＝−25%）。"""

    type: Literal["stat_down"] = "stat_down"
    stat: str
    amount: int = Field(ge=1)

    @model_validator(mode="after")
    def _check(self) -> StatDownBreak:
        if self.stat not in STAT_DOWN_STATS:
            raise ValueError(
                f"stat_down 的 stat 只能是 {'、'.join(STAT_DOWN_STATS)}：收到 {self.stat}"
            )
        if self.stat == "damage_dealt" and self.amount >= _PERMILLE:
            raise ValueError("stat_down damage_dealt 的 amount 是倍率‰，要小於 1000")
        return self


class ControlBreak(ContentModel):
    """一次控制：走一般的施加狀態（照頭目原本的免疫、控制遞減與抵抗）。"""

    type: Literal["control"] = "control"
    status: str = Field(pattern=_ID)
    duration: int | None = Field(default=None, ge=1, le=3, exclude_if=lambda v: v is None)


class StopMechanicBreak(ContentModel):
    """停掉一個機制（本段只有「狀態」類）：移除該狀態，之後任何來源都加不上。"""

    type: Literal["stop_mechanic"] = "stop_mechanic"
    status: str = Field(pattern=_ID)


class InterruptChargeBreak(ContentModel):
    """打斷正在蓄力的任何強招（R4，不封招）；沒有蓄力時什麼都不發生。"""

    type: Literal["interrupt_charge"] = "interrupt_charge"


type PartBreakEffect = Annotated[
    SealSkillBreak | StatDownBreak | ControlBreak | StopMechanicBreak | InterruptChargeBreak,
    Field(discriminator="type"),
]


class BossPart(ContentModel):
    """頭目的一個部位（見模組說明）。"""

    id: str = Field(pattern=_ID)
    name_zh: str = Field(min_length=1)
    hp_permille: int = Field(default=200, ge=1, le=1000)
    reach: PartReach = "any"
    exposed_in: tuple[str, ...] = Field(default=(), exclude_if=lambda v: not v)
    armor_bonus: int | None = Field(default=None, exclude_if=lambda v: v is None)
    resist: dict[ResistGroup, int] | None = Field(default=None, exclude_if=lambda v: v is None)
    element_mods: dict[Element, int] | None = Field(default=None, exclude_if=lambda v: v is None)
    on_break: tuple[PartBreakEffect, ...] = Field(min_length=1, max_length=2)
    break_text_zh: str | None = Field(default=None, min_length=1, exclude_if=lambda v: v is None)
    """破掉時的一句敘事（戰鬥紀錄；沒寫時由效果自動組一句）。"""
    tiles: tuple[tuple[int, int], ...] = Field(default=(), exclude_if=lambda v: not v)
    """巨型頭目的部位格（GB-1c，T11）：相對中心格的偏移；空＝不綁格（一格的頭目，不輸出）。"""
    melee_from: MeleeFrom = Field(default="tile", exclude_if=lambda v: v == "tile")
    """巨型頭目部位的近戰條件（GB-1c；預設 ``tile`` 不輸出）。"""
    counts_as_behind: bool = Field(default=False, exclude_if=lambda v: not v)
    """近戰打這個部位算從背後（GB-1c，R4；``False`` 不輸出）。"""

    @model_validator(mode="after")
    def _check(self) -> BossPart:
        bad = [g.value for g, v in (self.resist or {}).items() if not -_PERMILLE <= v <= _PERMILLE]
        if bad:
            raise ValueError(f"部位 {self.id} 的 resist 必須在 -1000–1000‰：{', '.join(bad)}")
        if len(set(self.exposed_in)) != len(self.exposed_in):
            raise ValueError(f"部位 {self.id} 的 exposed_in 不能重複")
        if len(set(self.tiles)) != len(self.tiles):
            raise ValueError(f"部位 {self.id} 的 tiles 不能重複")
        return self


def check_parts(parts: tuple[BossPart, ...]) -> list[str]:
    """``UnitTemplate.parts`` 的結構問題（不看其他欄位；空列表＝沒問題）。"""
    if not parts:
        return []
    problems: list[str] = []
    if not PARTS_MIN <= len(parts) <= PARTS_MAX:
        problems.append(f"parts 要有 {PARTS_MIN}～{PARTS_MAX} 個部位（收到 {len(parts)} 個）")
    ids = [p.id for p in parts]
    if len(set(ids)) != len(ids):
        problems.append("parts 的 id 不能重複")
    total = sum(p.hp_permille for p in parts)
    if total > PART_HP_TOTAL_MAX:
        problems.append(f"所有部位的血量加總不能超過 {PART_HP_TOTAL_MAX}‰（收到 {total}‰）")
    return problems


def check_part_tiles(parts: tuple[BossPart, ...], footprint: int) -> list[str]:
    """部位綁格（GB-1c，T11）的問題：巨型頭目（``footprint`` > 1）的每個部位都要有 ``tiles``、
    在佔格內、彼此不重疊；一格的頭目的部位不能有 ``tiles``、``melee_from``、
    ``counts_as_behind``。"""
    problems: list[str] = []
    if footprint == 1:
        for part in parts:
            if part.tiles or part.melee_from != "tile" or part.counts_as_behind:
                problems.append(
                    f"部位 {part.id}：只有佔多格的頭目的部位能有 "
                    "tiles、melee_from、counts_as_behind"
                )
        return problems
    half = footprint // 2
    seen: dict[tuple[int, int], str] = {}
    for part in parts:
        if not part.tiles:
            problems.append(f"部位 {part.id}：佔多格的頭目的部位要有 tiles（部位佔的格子）")
        for dx, dy in part.tiles:
            if abs(dx) > half or abs(dy) > half:
                problems.append(f"部位 {part.id} 的格子 ({dx}, {dy}) 不在佔格內")
            elif (dx, dy) in seen:
                problems.append(f"部位 {part.id} 的格子 ({dx}, {dy}) 和部位 {seen[(dx, dy)]} 重疊")
            else:
                seen[(dx, dy)] = part.id
    return problems


def max_part_hp(max_hp: int, part: BossPart) -> int:
    """部位的最大血量：最大 HP × ``hp_permille``‰（無條件捨去、最低 1）。開場時以當下的最大 HP
    算一次存進 ``part_hp``，之後 ``max_hp`` 改變不重算。"""
    return max(1, max_hp * part.hp_permille // _PERMILLE)


def opening_part_hp(parts: tuple[BossPart, ...], max_hp: int) -> dict[str, int]:
    """開場的部位血量（部位 ID → 血量）。"""
    return {p.id: max_part_hp(max_hp, p) for p in parts}
