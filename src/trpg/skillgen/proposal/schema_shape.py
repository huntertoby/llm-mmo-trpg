"""送給約束解碼的 JSON schema 再收緊（Phase LB-2）：把驗證器的跨欄位規則寫成 schema 能表達的分支。

pydantic 模型與驗證器都不變（驗證一律用模型本身）；這裡只改「送給 LLM 伺服器的 schema」，讓約束
解碼直接排除一定會被驗證器擋下的組合：

- :func:`split_variants`：變奏（``Variant``）的替換內容必須是 ``shape``、``range_delta``
  （LB-2b 起開放）、``element``、``add_effect``、``replace_effect`` 其中 1～2 項（``SkillDef``
  的變奏驗證器）。LM Studio 的約束解碼不支援 ``maxProperties``（LB-2 實測會被忽略），所以拆成
  「恰好這幾項」的分支（``anyOf``）。
- :func:`limit_variants`：變奏數量的稀有度上限（``core.variant_max_by_rarity``）寫進 ``maxItems``；
  上限 0 時拿掉 ``variants`` 欄位（LB-2c 起題目沒要求變奏時也是 0）。
- :func:`fix_category`（LB-2c，玩法 PM 4.1.18 第 3 點）：骨架規定了 ``category``／``weapon_req``
  時（被動一律 ``spell``／``any``，06 6.3.1；驗證器 ``passive.category``），頂層只留那一類的分支，
  兩個欄位都寫成 ``const``。

三者都只讓 schema 變窄（任何符合新 schema 的 JSON 都符合原本的 schema），不會讓驗證器放行原本
擋下的提議。

另外 :func:`drop_descriptions` 去掉 ``description``、:func:`prune_defs` 去掉沒被引用的定義：伺服器
只拿 schema 做約束解碼、不放進 prompt（LB-2 實測 prompt token 數與 schema 大小無關），模型讀不到
說明文字，留著只會讓 schema 變大（頂層依類別分支後寬題目會超過 ``SCHEMA_CHAR_LIMIT``）。說明要給
模型看，一律寫進 prompt 的資料區。
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from itertools import combinations
from typing import Any

__all__ = [
    "VARIANT_SWAP_FIELDS",
    "VARIANT_SWAP_MAX",
    "drop_descriptions",
    "fix_category",
    "limit_variants",
    "prune_defs",
    "shape_schema",
    "split_variants",
]

VARIANT_SWAP_FIELDS: tuple[str, ...] = (
    "shape",
    "range_delta",
    "element",
    "add_effect",
    "replace_effect",
)
"""變奏的替換內容欄位（提議模型有的；LB-2b 起含 ``range_delta``，只開 +1～+2）。5 項取 1 或 2
＝ 15 個分支。"""
VARIANT_SWAP_MAX = 2
"""每個變奏最多幾項替換內容（``SkillDef`` 的變奏驗證器：1～2 項）。"""
_VARIANT_KEYS = frozenset({"id", "name_zh", "when"})


def _is_variant(node: Mapping[str, Any]) -> bool:
    props = node.get("properties")
    return isinstance(props, Mapping) and set(props) >= _VARIANT_KEYS


def _non_null(prop: Mapping[str, Any]) -> dict[str, Any]:
    """``{"anyOf": [X, {"type": "null"}]}`` → ``X``（分支裡這一項必填、不能是 null）。"""
    options = prop.get("anyOf")
    if isinstance(options, list):
        kept = [o for o in options if o != {"type": "null"}]
        if len(kept) == 1:
            out = dict(kept[0])
            if "description" in prop and "description" not in out:
                out["description"] = prop["description"]
            return out
        if len(kept) != len(options):
            return {**prop, "anyOf": kept}
    return dict(prop)


def _variant_branches(node: Mapping[str, Any]) -> dict[str, Any]:
    props: Mapping[str, Any] = node["properties"]
    swaps = [f for f in VARIANT_SWAP_FIELDS if f in props]
    base = {k: v for k, v in props.items() if k not in VARIANT_SWAP_FIELDS}
    required = [k for k in node.get("required", []) if k in base]
    branches: list[dict[str, Any]] = []
    for size in range(1, VARIANT_SWAP_MAX + 1):
        for chosen in combinations(swaps, size):
            branch_props = {**base, **{f: _non_null(props[f]) for f in chosen}}
            branches.append(
                {
                    "type": "object",
                    "properties": branch_props,
                    "required": [*required, *chosen],
                    "additionalProperties": False,
                }
            )
    out: dict[str, Any] = {"anyOf": branches}
    if "description" in node:
        out["description"] = node["description"]
    return out


def split_variants(schema: Mapping[str, Any]) -> dict[str, Any]:
    """把 ``$defs`` 裡的變奏模型改成「恰好 1～2 項替換內容」的分支（回傳新 schema）。"""
    out = copy.deepcopy(dict(schema))
    defs = out.get("$defs")
    if not isinstance(defs, dict):
        return out
    for name, node in list(defs.items()):
        if isinstance(node, dict) and _is_variant(node):
            defs[name] = _variant_branches(node)
    return out


def _limit(node: Any, limit: int) -> None:
    if isinstance(node, list):
        for item in node:
            _limit(item, limit)
        return
    if not isinstance(node, dict):
        return
    props = node.get("properties")
    if isinstance(props, dict) and isinstance(props.get("variants"), dict):
        if limit <= 0:
            del props["variants"]
            if isinstance(node.get("required"), list) and "variants" in node["required"]:
                node["required"].remove("variants")
        else:
            current = props["variants"].get("maxItems", limit)
            props["variants"]["maxItems"] = min(int(current), limit)
    for key, value in node.items():
        if key != "properties":
            _limit(value, limit)
        elif isinstance(value, dict):
            for sub in value.values():
                _limit(sub, limit)


def limit_variants(schema: Mapping[str, Any], limit: int) -> dict[str, Any]:
    """技能層級的 ``variants`` 依稀有度上限設 ``maxItems``；上限 0 時拿掉欄位（回傳新 schema）。"""
    out = copy.deepcopy(dict(schema))
    _limit(out, limit)
    return out


def drop_descriptions(node: Any) -> Any:
    """遞迴去掉 ``description``（``properties``／``$defs`` 的鍵是名稱，不去；回傳新物件）。"""
    if isinstance(node, list):
        return [drop_descriptions(v) for v in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "description":
            continue
        if key in ("properties", "$defs") and isinstance(value, dict):
            out[key] = {name: drop_descriptions(sub) for name, sub in value.items()}
        else:
            out[key] = drop_descriptions(value)
    return out


_REF_PREFIX = "#/$defs/"


def _refs(node: Any, found: set[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _refs(item, found)
    elif isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
            found.add(ref.removeprefix(_REF_PREFIX))
        for value in node.values():
            _refs(value, found)


def prune_defs(schema: Mapping[str, Any]) -> dict[str, Any]:
    """去掉從根走不到的 ``$defs``（例如稀有度不能帶變奏時的變奏模型；回傳新 schema）。"""
    out = dict(schema)
    defs = out.get("$defs")
    if not isinstance(defs, dict):
        return out
    root = {k: v for k, v in out.items() if k != "$defs"}
    reached: set[str] = set()
    _refs(root, reached)
    todo = sorted(reached)
    while todo:
        name = todo.pop()
        found: set[str] = set()
        _refs(defs.get(name), found)
        for new in sorted(found - reached):
            reached.add(new)
            todo.append(new)
    out["$defs"] = {k: v for k, v in defs.items() if k in reached}
    return out


def _resolve(node: Any, defs: Mapping[str, Any]) -> Any:
    if isinstance(node, Mapping):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
            return defs.get(ref.removeprefix(_REF_PREFIX))
    return node


def _allowed(prop: Any, defs: Mapping[str, Any]) -> frozenset[Any] | None:
    """欄位可填的值（``const`` 或 ``enum``，``$ref`` 先解開）；看不出來時 ``None``。"""
    node = _resolve(prop, defs)
    if not isinstance(node, Mapping):
        return None
    if "const" in node:
        return frozenset({node["const"]})
    values = node.get("enum")
    return frozenset(values) if isinstance(values, list) else None


def _fits(values: frozenset[Any] | None, value: str) -> bool:
    return values is None or value in values


def fix_category(schema: Mapping[str, Any], category: str, weapon_req: str) -> dict[str, Any]:
    """頂層（技能提議的各分支）的 ``category``／``weapon_req`` 固定成 ``category``／``weapon_req``
    （``const``）；明確不收這兩個值的分支拿掉（回傳新 schema）。

    分支在根的 ``oneOf``／``anyOf``（``$ref`` 指到 ``$defs``）；沒有分支時根本身就是技能。沒有
    ``category`` 欄位的分支不動；全部分支都不收時照原樣回傳（保守：不讓 schema 變成沒有解）。"""
    out = copy.deepcopy(dict(schema))
    defs: Mapping[str, Any] = out.get("$defs") or {}
    key = next((k for k in ("oneOf", "anyOf") if isinstance(out.get(k), list)), None)
    items: list[Any] = list(out[key]) if key is not None else [out]
    kept: list[Any] = []
    for item in items:
        node = _resolve(item, defs)
        props = node.get("properties") if isinstance(node, dict) else None
        if not isinstance(props, dict) or "category" not in props:
            kept.append(item)
            continue
        if not (
            _fits(_allowed(props["category"], defs), category)
            and _fits(_allowed(props.get("weapon_req"), defs), weapon_req)
        ):
            continue
        props["category"] = {"const": category, "type": "string"}
        if "weapon_req" in props:
            props["weapon_req"] = {"const": weapon_req, "type": "string"}
        kept.append(item)
    if not kept:
        return copy.deepcopy(dict(schema))
    if key is not None:
        out[key] = kept
    return out


def shape_schema(
    schema: Mapping[str, Any],
    *,
    variant_limit: int,
    category: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """送給約束解碼的 schema：:func:`limit_variants` → :func:`split_variants` →
    （``category`` 有給時）:func:`fix_category` → :func:`drop_descriptions` → :func:`prune_defs`。
    ``category`` 是（``category``, ``weapon_req``）。"""
    shaped = split_variants(limit_variants(schema, variant_limit))
    if category is not None:
        shaped = fix_category(shaped, *category)
    return prune_defs(drop_descriptions(shaped))
