"""修正規則的改變種類（``content/modifier_changes.yaml``；Phase 3T-1）。

每一種 ``change``（``damage_permille``、``hit_bonus``……）的可套用對象、是否「選目標之前就決定」、
是否讓技能變形、預算單位與點數鍵、玩家名稱都在 YAML 宣告（唯一來源）。數值範圍與型別仍是
:class:`~trpg.content.skills.ModifierChange` 的欄位；兩邊的種類一致由
:func:`modifier_change_problems` 檢查（:func:`~trpg.content.library.load_library` 呼叫）。

:mod:`trpg.content.skills` 的模組常數（``MODIFIER_CHANGES``、``CHANGE_TARGETS``……）在 schema
驗證當下就要用，那時還沒有載入完整的內容庫，所以由 :func:`bundled_modifier_changes` 讀專案內建的
``content/``（同 :mod:`trpg.content.yaml_sources`，不受 ``TRPG_CONTENT_DIR`` 影響）。
"""

from __future__ import annotations

from collections.abc import Collection
from functools import cache
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import bundled_content_dir, load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "CHANGE_TARGET_KEYS",
    "MODIFIER_CHANGES_FILE",
    "ChangeBudget",
    "ModifierChangeDef",
    "ModifierChangeTable",
    "bundled_modifier_changes",
    "modifier_change_problems",
]

MODIFIER_CHANGES_FILE = "modifier_changes.yaml"

type ChangeTarget = Literal[
    "attack",
    "shove",
    "trip",
    "interact",
    "all_attacks",
    "all_skills",
    "skill_tags",
    "weapon_skills",
]
CHANGE_TARGET_KEYS: tuple[str, ...] = (
    "attack",
    "shove",
    "trip",
    "interact",
    "all_attacks",
    "all_skills",
    "skill_tags",
    "weapon_skills",
)
"""``applies_to`` 的代碼（:meth:`trpg.content.skills.ModifierTarget.keys`）。"""


class ChangeBudget(ContentModel):
    """一種改變每次使用的價值（:func:`trpg.skillgen.budget` 的修正規則點數）。

    - ``structured``：由其他資料算出（傷害‰、治療‰、推擊格數、命中後效果、形狀轉換），算法在
      ``trpg.skillgen.budget`` 的 ``STRUCTURED_CHANGES``。
    - ``magnitude``：``|數值| ÷ per`` 份；``count``：列表的項數份；``flag``：每次 1 份。
      每份的價值是 ``skill_budget.yaml`` 的 ``modifier.points_milli.<points>``（數值為負時改用
      ``points_if_negative``；``signed`` 時負的數值點數取負）。
    """

    unit: Literal["structured", "magnitude", "count", "flag"]
    points: str | None = Field(default=None, pattern=ID_PATTERN)
    points_if_negative: str | None = Field(default=None, pattern=ID_PATTERN)
    signed: bool = False
    per: int = Field(default=1, ge=1)
    note: str | None = None
    """預算說明（``{value}`` 數值、``{count}`` 項數；省略＝改變的 ID）。"""
    hit_gated: bool = False
    """命中後才生效（使用次數 × ``modifier.hit_rate_permille``）。"""

    @model_validator(mode="after")
    def _check(self) -> ChangeBudget:
        if self.unit == "structured":
            if self.points is not None or self.points_if_negative is not None:
                raise ValueError("budget.unit 為 structured 時不填 points")
        elif self.points is None:
            raise ValueError(f"budget.unit 為 {self.unit} 時必須填 points")
        return self

    def point_keys(self) -> tuple[str, ...]:
        """引用的 ``points_milli`` 鍵。"""
        return tuple(k for k in (self.points, self.points_if_negative) if k is not None)


class ModifierChangeDef(ContentModel):
    """一種修正規則的改變（欄位意義見 ``content/modifier_changes.yaml`` 檔頭）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    applies_to: tuple[ChangeTarget, ...] = Field(min_length=1)
    self_only: bool = False
    reshapes: bool = False
    per_turn_limit: bool = False
    nonzero: bool = False
    true_only: bool = False
    budget: ChangeBudget

    @model_validator(mode="after")
    def _check(self) -> ModifierChangeDef:
        if len(set(self.applies_to)) != len(self.applies_to):
            raise ValueError(f"{self.id} 的 applies_to 不可重複")
        if self.reshapes and not self.self_only:
            raise ValueError(f"{self.id}：讓技能變形的改變（reshapes）必須是 self_only")
        return self


class ModifierChangeTable(ContentModel):
    """``content/modifier_changes.yaml``。"""

    changes: tuple[ModifierChangeDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> ModifierChangeTable:
        ids = [c.id for c in self.changes]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"修正規則的改變種類重複：{'、'.join(dup)}")
        return self

    def by_id(self) -> dict[str, ModifierChangeDef]:
        return {c.id: c for c in self.changes}

    @property
    def ids(self) -> tuple[str, ...]:
        """依檔案順序的改變種類。"""
        return tuple(c.id for c in self.changes)

    def summary(self) -> str:
        return f"{len(self.changes)} 種修正規則改變"


@cache
def bundled_modifier_changes() -> ModifierChangeTable:
    """專案內建的 ``content/modifier_changes.yaml``（schema 匯入時讀；只讀一次）。"""
    return load_content_file(bundled_content_dir() / MODIFIER_CHANGES_FILE, ModifierChangeTable)


def modifier_change_problems(
    table: ModifierChangeTable, fields: Collection[str], point_keys: Collection[str]
) -> list[str]:
    """YAML 與 ``ModifierChange`` 的欄位（``fields``）、``points_milli`` 的鍵（``point_keys``）是否
    對得上（中文，依種類排序）；沒有問題時為空列表。"""
    ids = set(table.ids)
    have = set(fields)
    problems = [
        f"{i} 沒有 ModifierChange 的欄位（請補 trpg.content.skills）" for i in sorted(ids - have)
    ]
    problems += [
        f"ModifierChange 的欄位 {f} 沒有宣告（請補 {MODIFIER_CHANGES_FILE}）"
        for f in sorted(have - ids)
    ]
    keys = set(point_keys)
    for change in sorted(table.changes, key=lambda c: c.id):
        problems += [
            f"{change.id} 的預算點數鍵 {k} 不在 skill_budget.yaml 的 modifier.points_milli"
            for k in change.budget.point_keys()
            if k not in keys
        ]
    return problems
