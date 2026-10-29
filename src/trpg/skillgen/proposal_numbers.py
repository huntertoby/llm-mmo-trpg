"""提議模型的數值欄位（Phase 4-L3；決定 #3「LLM 只選結構、數值由預算器補」）。

提議模型（:mod:`trpg.skillgen.proposal`）不含數值欄位：骰子、倍率、持續回合、距離、AP、法力、
冷卻、條件的門檻等都不是 LLM 的事。這個模組集中定義「哪些欄位算數值」（全部取自內容資料：
``skill_primitives.yaml`` 與 ``skill_conditions.yaml`` 的 ``int``／``dice`` 參數），並提供：

- :func:`split_numbers`：完整技能資料 → （只剩結構的資料, 被移除的數值清單）；
- :func:`apply_numbers`：把數值清單放回結構（測試與預算器用）；
- :func:`minimal_filler`：保守的預設補值（只補驗證必填的欄位、取最小值；不保證通過預算，
  真正的數值由 4-L5 的預算器 ``composer_tuning.tune`` 決定）。

資料一律是 ``SkillDef`` 形狀的 JSON 字典（``model_dump(mode="json")``）。
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from copy import deepcopy
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import PrimitiveParam, param_required_for

__all__ = [
    "SCALING_NUMBER_FIELDS",
    "TOP_LEVEL_NUMBER_FIELDS",
    "TRIGGER_NUMBER_FIELDS",
    "VARIANT_NUMBER_FIELDS",
    "NumberFiller",
    "NumberPath",
    "RemovedNumber",
    "apply_numbers",
    "fixed_filler",
    "minimal_filler",
    "numeric_param_names",
    "split_numbers",
]

type NumberPath = tuple[str | int, ...]
type RemovedNumber = tuple[NumberPath, Any]
type NumberFiller = Callable[[dict[str, Any]], dict[str, Any]]
"""``SkillDef`` 形狀的字典（只有結構）→ 補好數值的字典。"""

NUMERIC_PARAM_TYPES = frozenset({"int", "dice"})
SCALING_NUMBER_FIELDS = ("per_step_permille", "cap_permille")
"""``scaling``（依情況縮放）只留 ``by``（依什麼縮放），步進與上限是數值。"""
TOP_LEVEL_NUMBER_FIELDS = ("ap_cost",)
"""技能層級的數值欄位（另外還有 :data:`COST_NUMBER_FIELDS`）。"""
COST_NUMBER_FIELDS = (
    "mana",
    "stamina",
    "cooldown",
    "source",
    "uses_per_battle",
    "stacks",
    "hp_percent",
)
"""``cost`` 的數值欄位（Phase 4-L8 加上源力、每場次數、層數需求、HP 代價：提議只選「要不要」，
見 :mod:`trpg.skillgen.proposal_costs`）。"""
TRIGGER_NUMBER_FIELDS = ("max_per_round", "max_distance")
VARIANT_NUMBER_FIELDS = ("range_delta",)
NESTED_EFFECT_KEYS = ("then", "win", "lose", "on_kill", "effects")
DEFAULT_ACTIVE_AP = 2
"""預算器不調整 AP，所以預設補 2（多數手寫主動技能的值）。"""
MIN_DICE = "1d4"
DEFAULT_SCALING = {"per_step_permille": 10, "cap_permille": 100}
LEGENDARY = "legendary"
MIN_SOURCE = 1
"""傳說技能補的源力（``cost.source`` 的最小值；Phase 4-L8）。"""
MIN_COOLDOWN = 1
"""帶 ``refund_cooldown`` 的技能補的冷卻（4-L8b）。"""


def numeric_param_names(params: Mapping[str, PrimitiveParam]) -> frozenset[str]:
    """一個原語（或條件）的數值參數名稱：型別為 ``int`` 或 ``dice``。"""
    return frozenset(n for n, spec in params.items() if spec.type in NUMERIC_PARAM_TYPES)


# ---------------------------------------------------------------------------
# 走訪
# ---------------------------------------------------------------------------


def _nested_effects(
    effect: Mapping[str, Any], path: NumberPath
) -> Iterator[tuple[NumberPath, Any]]:
    yield path, effect
    for key in NESTED_EFFECT_KEYS:
        items = effect.get(key)
        if isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    yield from _nested_effects(item, (*path, key, i))


def _walk_effects(
    data: Mapping[str, Any], *, followup: bool = True
) -> Iterator[tuple[NumberPath, dict[str, Any]]]:
    """技能內的所有效果字典（含巢狀、變奏、失手反噬 ``cost.on_miss`` 與複合技能第二段裡的；
    ``followup=False`` 時不含第二段），附路徑。"""
    for i, effect in enumerate(data.get("effects") or ()):
        if isinstance(effect, dict):
            yield from _nested_effects(effect, ("effects", i))
    cost = data.get("cost")
    if isinstance(cost, dict):
        for i, effect in enumerate(cost.get("on_miss") or ()):
            if isinstance(effect, dict):
                yield from _nested_effects(effect, ("cost", "on_miss", i))
    if followup:
        yield from _followup_effects(data)
    for v, variant in enumerate(data.get("variants") or ()):
        if not isinstance(variant, dict):
            continue
        add = variant.get("add_effect")
        if isinstance(add, dict):
            yield from _nested_effects(add, ("variants", v, "add_effect"))
        swap = variant.get("replace_effect")
        if isinstance(swap, dict) and isinstance(swap.get("effect"), dict):
            yield from _nested_effects(swap["effect"], ("variants", v, "replace_effect", "effect"))


def _followup_effects(data: Mapping[str, Any]) -> Iterator[tuple[NumberPath, dict[str, Any]]]:
    """複合技能第二段（``followup``，Phase 4-L8）的效果字典，附路徑。"""
    follow = data.get("followup")
    if not isinstance(follow, dict):
        return
    for i, effect in enumerate(follow.get("effects") or ()):
        if isinstance(effect, dict):
            yield from _nested_effects(effect, ("followup", "effects", i))


def _walk_conditions(data: Mapping[str, Any]) -> Iterator[tuple[NumberPath, dict[str, Any]]]:
    if isinstance(data.get("condition"), dict):
        yield ("condition",), data["condition"]
    follow = data.get("followup")
    if isinstance(follow, dict) and isinstance(follow.get("condition"), dict):
        yield ("followup", "condition"), follow["condition"]
    for path, effect in _walk_effects(data):
        if isinstance(effect.get("condition"), dict):
            yield (*path, "condition"), effect["condition"]


def _node(data: Any, path: NumberPath) -> Any:
    for key in path:
        data = data[key]
    return data


# ---------------------------------------------------------------------------
# 拆分與還原
# ---------------------------------------------------------------------------


def _effect_params(library: ContentLibrary) -> dict[str, dict[str, PrimitiveParam]]:
    """效果類型 → 參數表：原語，加上只能巢狀的效果（Phase 4-L8b）。"""
    table = library.ruleset.primitives
    out = {p.id: p.params for p in table.primitives}
    out.update({n.id: n.params for n in table.nested_only_effects})
    return out


def split_numbers(
    data: Mapping[str, Any], library: ContentLibrary
) -> tuple[dict[str, Any], list[RemovedNumber]]:
    """移除所有數值欄位，回傳（結構, 被移除的 ``(路徑, 值)``）。輸入不會被修改。"""
    out = deepcopy(dict(data))
    removed: list[RemovedNumber] = []

    def take(path: NumberPath, node: dict[str, Any], keys: Sequence[str]) -> None:
        for key in keys:
            if key in node:
                removed.append(((*path, key), node.pop(key)))

    primitives = _effect_params(library)
    for path, effect in _walk_effects(out):
        params = primitives.get(str(effect.get("type")))
        if params is not None:
            take(path, effect, sorted(numeric_param_names(params)))
        scaling = effect.get("scaling")
        if isinstance(scaling, dict):
            take((*path, "scaling"), scaling, SCALING_NUMBER_FIELDS)
    conditions = library.ruleset.conditions.by_id()
    for path, cond in _walk_conditions(out):
        definition = conditions.get(str(cond.get("type")))
        if definition is not None:
            take(path, cond, sorted(numeric_param_names(definition.params)))
    take((), out, TOP_LEVEL_NUMBER_FIELDS)
    if isinstance(out.get("cost"), dict):
        take(("cost",), out["cost"], COST_NUMBER_FIELDS)
        if not out["cost"]:
            del out["cost"]
    if isinstance(out.get("trigger"), dict):
        take(("trigger",), out["trigger"], TRIGGER_NUMBER_FIELDS)
    for v, variant in enumerate(out.get("variants") or ()):
        if isinstance(variant, dict):
            take(("variants", v), variant, VARIANT_NUMBER_FIELDS)
    return out, removed


def apply_numbers(structure: Mapping[str, Any], removed: Iterable[RemovedNumber]) -> dict[str, Any]:
    """:func:`split_numbers` 的反向：把數值放回結構（缺少的中間字典會建立）。"""
    out = deepcopy(dict(structure))
    for path, value in removed:
        node: Any = out
        for key in path[:-1]:
            if isinstance(node, dict) and key not in node:
                node[key] = {}
            node = node[key]
        node[path[-1]] = value
    return out


def fixed_filler(removed: Iterable[RemovedNumber]) -> NumberFiller:
    """固定把某份數值放回去的補值器（測試用：結構往返）。"""
    items = list(removed)
    return lambda data: apply_numbers(data, items)


# ---------------------------------------------------------------------------
# 保守的預設補值
# ---------------------------------------------------------------------------


def _filled_in(effects: Sequence[Mapping[str, Any]], type_id: str, name: str) -> bool:
    return any(e.get("type") == type_id and e.get(name) is not None for e in effects)


def _min_value(spec: PrimitiveParam) -> Any:
    return MIN_DICE if spec.type == "dice" else (spec.min if spec.min is not None else 1)


def _fill_conditions(out: dict[str, Any], library: ContentLibrary) -> None:
    conditions = library.ruleset.conditions.by_id()
    for _, cond in _walk_conditions(out):
        definition = conditions.get(str(cond.get("type")))
        if definition is None:
            continue
        for name in sorted(numeric_param_names(definition.params)):
            if definition.params[name].required and cond.get(name) is None:
                cond[name] = _min_value(definition.params[name])


def _fill_cost(out: dict[str, Any], library: ContentLibrary, category: str) -> None:
    """AP、源力與最低花費：主動技能 AP 取 2；傳說技能必須花源力（3C-4a），補最小值；主動法術技
    至少 1 法力、主動武器技至少 1 耐力（06 6.10）。"""
    active = out.get("kind") == "active"
    if active and out.get("ap_cost") is None:
        out["ap_cost"] = DEFAULT_ACTIVE_AP
    if out.get("rarity") == LEGENDARY:
        cost = dict(out.get("cost") or {})
        cost.setdefault("source", MIN_SOURCE)
        out["cost"] = cost
    if active and category in ("weapon", "spell"):
        resource = library.budget.resource_of(category)  # type: ignore[arg-type]
        cost = dict(out.get("cost") or {})
        if not isinstance(cost.get(resource), int) or cost[resource] < 1:
            cost[resource] = 1
        out["cost"] = cost
    if any(e.get("type") == "refund_cooldown" for _, e in _walk_effects(out, followup=False)):
        # 擊殺時冷卻歸零（4-L8b）要有冷卻可以歸零
        cost = dict(out.get("cost") or {})
        cost.setdefault("cooldown", MIN_COOLDOWN)
        out["cost"] = cost


def minimal_filler(library: ContentLibrary) -> NumberFiller:
    """保守的預設補值器：只補驗證必填的數值（int 取最小值、骰子取 ``1d4``、主動技能 AP 取 2、
    ``scaling`` 取小的步進與上限、傳說技能 1 點源力）；選填的數值保持省略（引擎用預設值）。不保證
    通過預算——真正的數值由 4-L5 的預算器決定。"""
    primitives = _effect_params(library)

    def fill_effects(group: list[dict[str, Any]], category: str) -> None:
        for effect in group:
            type_id = str(effect.get("type"))
            params = primitives.get(type_id)
            if params is None:
                continue
            for name in sorted(numeric_param_names(params)):
                spec = params[name]
                required = param_required_for(
                    spec,
                    category=category,
                    sibling_filled=functools.partial(_filled_in, group, type_id),
                )
                if required and effect.get(name) is None:
                    effect[name] = _min_value(spec)
            if isinstance(effect.get("scaling"), dict):
                effect["scaling"].update(DEFAULT_SCALING)

    def fill(data: dict[str, Any]) -> dict[str, Any]:
        out = deepcopy(data)
        category = str(out.get("category"))
        # 第二段（followup）是另一個骨架的技能：必填與否只看第二段自己的效果
        fill_effects([e for _, e in _walk_effects(out, followup=False)], category)
        fill_effects([e for _, e in _followup_effects(out)], category)
        _fill_conditions(out, library)
        _fill_cost(out, library, category)
        return out

    return fill
