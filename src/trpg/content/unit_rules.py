"""單位規則表：種族被動與裝備地形規則共用的規則種類與參數檢查（E2，08 8.29，#175）。

規則的種類是封閉清單（:data:`UNIT_RULE_SPECS`），每一種只能填它自己的參數
（:data:`UNIT_RULE_PARAM_FIELDS` 中的必填項）。來源有兩種：

- 種族的環境被動 :class:`trpg.content.races.RacePassive`（``races.yaml``，Phase 3R-1）；
- 裝備的第 12 類詞條「地形規則」 :class:`trpg.content.equipment.TerrainAffix`（``affixes.yaml``）。

兩者欄位名稱相同，結算由 :mod:`trpg.engine.rules.unit_rules` 依「種族先、再依裝備部位固定順序」
查詢；同一種規則只有第一個來源生效（8.29 E2 第 1 點）。本模組只有資料規則，不含結算。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from trpg.shared.types import Element, Surface

__all__ = [
    "EQUIPMENT_FORBIDDEN_RULES",
    "UNIT_RULE_PARAM_FIELDS",
    "UNIT_RULE_SPECS",
    "UnitRule",
    "UnitRuleSpec",
    "unit_rule_param_problems",
    "unit_rule_permille_problems",
]


@dataclass(frozen=True)
class UnitRuleSpec:
    """一種單位規則的參數規則。"""

    required: tuple[str, ...]


UNIT_RULE_SPECS: dict[str, UnitRuleSpec] = {
    "sight_penalty_reduction": UnitRuleSpec(("weathers", "permille")),
    "sight_bonus_on_map_tag": UnitRuleSpec(("map_tags", "amount")),
    "detect_hidden_nearby": UnitRuleSpec(("radius",)),
    "damage_taken_permille": UnitRuleSpec(("element", "permille")),
    "slip_immunity": UnitRuleSpec(("surfaces",)),
    "conduction_immunity": UnitRuleSpec(("surfaces",)),
    "knockback_reduction_at_hazard": UnitRuleSpec(("terrain", "amount")),
    "burn_immunity_on": UnitRuleSpec(("surfaces",)),
    "surface_move_bonus": UnitRuleSpec(("surfaces", "amount")),
    "weather_move_bonus": UnitRuleSpec(("weathers", "amount")),
    "fall_immunity": UnitRuleSpec(()),
    "trail_surface": UnitRuleSpec(("surfaces", "duration")),
    "flat_climb": UnitRuleSpec(("amount",)),
    "surface_damage_immunity": UnitRuleSpec(("surfaces",)),
}
"""允許的規則（封閉清單，只有環境互動的小規則；3R-2 照此結算）。``fall_immunity``（獸耳族
「輕身」，#138）：墜落不受傷（被推下或自己往下都算；致命地形照舊）。

E3（08 8.29 E3，#175）新增三種：

- ``trail_surface``（每一步留下表面，例「霜行」）：自己步行、衝刺的每一步，在離開的那一格留下
  ``surfaces`` 的唯一一種表面，持續 ``duration`` 個環境回合（:mod:`trpg.engine.trail`）；
- ``flat_climb``（攀岩）：上 ``amount`` 層以內當平地走
  （:func:`trpg.engine.rules.movement.unit_step_cost`）；
- ``surface_damage_immunity``：站在 ``surfaces`` 上不受回合開始的表面傷害
  （``cause="surface"``）。"""

UNIT_RULE_PARAM_FIELDS = (
    "weathers",
    "map_tags",
    "terrain",
    "surfaces",
    "element",
    "permille",
    "amount",
    "radius",
    "duration",
)
"""規則的參數欄位（每種規則只能填 :class:`UnitRuleSpec` 的 ``required``）。"""

EQUIPMENT_FORBIDDEN_RULES: frozenset[str] = frozenset({"damage_taken_permille"})
"""裝備地形規則不能用的種類（E2 保守做法）：元素減傷是數值抗性（裝備已有第 1 類的
``element_resist``），而且只在開戰時由種族併進元素修正（``race_element_mods``）。"""


class UnitRule(Protocol):
    """一條單位規則的唯讀介面（種族被動與裝備地形規則都符合）。"""

    @property
    def rule(self) -> str: ...
    @property
    def weathers(self) -> tuple[str, ...] | None: ...
    @property
    def map_tags(self) -> tuple[str, ...] | None: ...
    @property
    def terrain(self) -> tuple[str, ...] | None: ...
    @property
    def surfaces(self) -> tuple[Surface, ...] | None: ...
    @property
    def element(self) -> Element | None: ...
    @property
    def permille(self) -> int | None: ...
    @property
    def amount(self) -> int | None: ...
    @property
    def radius(self) -> int | None: ...
    @property
    def duration(self) -> int | None: ...


def unit_rule_param_problems(rule_def: UnitRule) -> tuple[str | None, list[str]]:
    """規則種類與參數的問題：``(未知種類的說明, 參數問題)``。種類未知時第一項是允許清單的文字
    （呼叫端組成自己的錯誤訊息），參數問題為空。"""
    spec = UNIT_RULE_SPECS.get(rule_def.rule)
    if spec is None:
        return "、".join(sorted(UNIT_RULE_SPECS)), []
    problems: list[str] = []
    for name in UNIT_RULE_PARAM_FIELDS:
        value = getattr(rule_def, name)
        if name in spec.required and value is None:
            problems.append(f"缺少必填參數 {name}")
        elif value is not None and name not in spec.required:
            problems.append(f"不可使用參數 {name}")
    trail = rule_def.surfaces if rule_def.rule == "trail_surface" else None
    if trail is not None and (len(trail) != 1 or Surface.NONE in trail):
        problems.append("trail_surface 的 surfaces 只能填一種表面（不能是 none）")
    return None, problems


def unit_rule_permille_problems(
    rule_def: UnitRule, *, max_sight_reduction: int, max_resist: int
) -> list[str]:
    """``permille`` 超出上限的地方（HC-4d：上限在 ``races.yaml`` 的 ``limits``）。"""
    if rule_def.permille is None:
        return []
    if rule_def.rule == "sight_penalty_reduction" and not (
        0 < rule_def.permille <= max_sight_reduction
    ):
        return [f"permille 必須在 1～{max_sight_reduction}（視線懲罰最多減半）"]
    if rule_def.rule == "damage_taken_permille" and not -max_resist <= rule_def.permille < 0:
        return [f"permille 必須為 −{max_resist}～−1（只能減傷，幅度有上限）"]
    return []
