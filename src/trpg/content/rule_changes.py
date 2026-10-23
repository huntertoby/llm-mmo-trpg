"""規則改變（Phase 3D-6，``docs/design/06-技能.md`` 6.16 F、6.14.4）。

``content/rule_changes.yaml`` 列出傳說技能可以引用的「規則改變」。每條規則屬於引擎內預先實作的
一 **類**（:data:`RULE_CHANGE_KINDS`）：新增一條同類規則（換元素、換狀態、換召喚物）只要改資料，
新增一類才要改引擎。

規則只影響持有者自己（「你的……」）：

- ``element_heals_allies``（``element``、``permille``）：你造成的 ``element`` 傷害打到友方（不含
  自己）時，改為治療傷害的 ``permille``‰。
- ``push_any_object``（沒有參數）：你可以推動任何擋路的物件（``blocks_move``，例如土牆、矮牆、
  倒木）；地形不行。
- ``pass_through_apply``（``status``、``duration``）：你步行時，每經過一格就對相鄰的敵人施加
  ``status``（每次移動每個敵人一次）。
- ``on_downed_spawn``（``unit``、``duration``）：你倒下時，在原地留下持續 ``duration`` 輪的
  召喚物 ``unit``（分身）。

每一類的預算點數放在 ``kinds``（初值，未經模擬；只給傳說）。引用的狀態與召喚物範本由
:class:`~trpg.content.library.Ruleset` 檢查。規則改變嵌入規則包，重播不依賴當下的資料檔。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.shared.types import Element

__all__ = [
    "ELEMENT_HEALS_ALLIES",
    "ON_DOWNED_SPAWN",
    "PASS_THROUGH_APPLY",
    "PUSH_ANY_OBJECT",
    "RULE_CHANGE_KINDS",
    "RuleChangeDef",
    "RuleChangeKind",
    "RuleChangeKindDef",
    "RuleChangeTable",
    "rule_change_sentence",
]

type RuleChangeKind = Literal[
    "element_heals_allies", "push_any_object", "pass_through_apply", "on_downed_spawn"
]
ELEMENT_HEALS_ALLIES = "element_heals_allies"
PUSH_ANY_OBJECT = "push_any_object"
PASS_THROUGH_APPLY = "pass_through_apply"
ON_DOWNED_SPAWN = "on_downed_spawn"
RULE_CHANGE_KINDS: tuple[str, ...] = (
    ELEMENT_HEALS_ALLIES,
    PUSH_ANY_OBJECT,
    PASS_THROUGH_APPLY,
    ON_DOWNED_SPAWN,
)
"""引擎認得的規則改變種類（新增一類要改引擎）。"""

_PARAMS: dict[str, frozenset[str]] = {
    ELEMENT_HEALS_ALLIES: frozenset({"element", "permille"}),
    PUSH_ANY_OBJECT: frozenset(),
    PASS_THROUGH_APPLY: frozenset({"status", "duration"}),
    ON_DOWNED_SPAWN: frozenset({"unit", "duration"}),
}
"""每一類必填（也只能填）的參數。"""

_ALL_PARAMS = ("element", "permille", "status", "duration", "unit")
_MAX_DURATION = 3


class RuleChangeDef(ContentModel):
    """一條規則改變（``content/rule_changes.yaml`` 的 ``rule_changes``）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    kind: RuleChangeKind
    element: Element | None = None
    permille: int | None = Field(default=None, ge=100, le=1000)
    """``element_heals_allies``：治療量 ＝ 原本傷害 × 這個千分比。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    duration: int | None = Field(default=None, ge=1, le=_MAX_DURATION)
    """``pass_through_apply`` 的狀態回合數；``on_downed_spawn`` 的分身持續輪數。"""
    unit: str | None = Field(default=None, pattern=ID_PATTERN)
    """``on_downed_spawn`` 的召喚物範本 ID（``content/units/summons/``）。"""

    @model_validator(mode="after")
    def _check(self) -> RuleChangeDef:
        need = _PARAMS[self.kind]
        given = {name for name in _ALL_PARAMS if getattr(self, name) is not None}
        missing = sorted(need - given)
        if missing:
            raise ValueError(f"規則改變 {self.id}（{self.kind}）缺少參數：{', '.join(missing)}")
        extra = sorted(given - need)
        if extra:
            raise ValueError(f"規則改變 {self.id}（{self.kind}）不接受參數：{', '.join(extra)}")
        if self.element is Element.PHYSICAL:
            raise ValueError(f"規則改變 {self.id}：element 不可是物理（physical）")
        return self


class RuleChangeKindDef(ContentModel):
    """一類規則改變的預算點數（Phase 3D-6；初值，未經模擬）。"""

    points: int = Field(ge=1)


class RuleChangeTable(ContentModel):
    """``content/rule_changes.yaml``：每一類的點數與全部規則改變（依 ID）。"""

    kinds: dict[RuleChangeKind, RuleChangeKindDef] = Field(default_factory=dict)
    rule_changes: tuple[RuleChangeDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> RuleChangeTable:
        ids = [r.id for r in self.rule_changes]
        if len(set(ids)) != len(ids):
            raise ValueError("規則改變 ID 重複")
        if self.rule_changes:
            missing = sorted(k for k in RULE_CHANGE_KINDS if k not in self.kinds)
            if missing:
                raise ValueError(f"kinds 缺少規則改變種類的點數：{', '.join(missing)}")
        return self

    def by_id(self) -> dict[str, RuleChangeDef]:
        return {r.id: r for r in self.rule_changes}

    def points(self, kind: str) -> int:
        """一類規則改變的預算點數；沒有資料時拋出 ``KeyError``。"""
        return self.kinds[kind].points  # type: ignore[index]

    def summary(self) -> str:
        return f"{len(self.rule_changes)} 條規則改變（{len(self.kinds)} 類）"


def rule_change_sentence(
    rule: RuleChangeDef,
    *,
    status_name: Callable[[str], str],
    summon_name: Callable[[str], str],
) -> str:
    """一條規則改變的規則句（不含名稱；Phase 3-41a 從 ``trpg.narrative.skills`` 搬來，讓傳說技能卡
    與改變規則類裝備詞條用同一句，清單 5.1）。"""
    if rule.kind == ELEMENT_HEALS_ALLIES:
        assert rule.element is not None and rule.permille is not None
        return (
            f"你造成的{rule.element.display_name}傷害打到友方（不含自己）時，改為治療"
            f"（原本傷害的 {rule.permille / 10:g}%）"
        )
    if rule.kind == PUSH_ANY_OBJECT:
        return "你可以推動任何擋路的物件（例如土牆、矮牆、倒木），可推倒的照樣倒下；地形與橋面不行"
    if rule.kind == PASS_THROUGH_APPLY:
        assert rule.status is not None
        return (
            f"你步行經過敵人的相鄰格時，對他施加「{status_name(rule.status)}」{rule.duration} 回合"
            "（每次移動每個敵人一次）"
        )
    assert rule.unit is not None
    return (
        f"你倒下時，在原地留下{summon_name(rule.unit)}（接替你的行動順序），持續 {rule.duration} 輪"
    )
