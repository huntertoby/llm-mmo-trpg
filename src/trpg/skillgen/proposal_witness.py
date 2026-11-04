"""出題的可行解檢查（Phase 6E-W）：題目至少要有一份 **實際通過完整驗證** 的寫法才出。

6S-2 的 :func:`~trpg.skillgen.proposal_topup.keywords_reachable` 是逐個關鍵字的必要條件，看不到這些
組合問題（roguelite 完整技能三選一的題目常有兩個關鍵字、指定武器大類，最容易踩到）：

- 兩個關鍵字各要一個附帶效果，但骨架的附帶效果只能 1 個（``skeleton.secondary_count``）；
- 兩種傷害元素要角色 2 階（``tier.element``），地形核心限大地元素（``terrain_needs_earth``）；
- 沒有數值的核心（揭露、驅散、淨地…）在附帶效果有占比上限的骨架上，補不到預算下限
  （``budget.weak``）；
- 骨架不允許的對象（光環不得對敵）、技能與主角的武器不相容。

做法：由引擎自己 **建構** 幾份最簡單的提議（核心效果 ＋ 每個題目關鍵字一個專屬效果；效果寫法取自
手寫技能與關鍵字推導表），交給和 LLM 提議完全相同的 :func:`~trpg.skillgen.proposal_budget.
evaluate_with_repair`（數值修補、結構補強、``validate_skill``、題目要求）。任何一份合格 ＝ 題目
可行。這是充分條件：找到的寫法真的合法；找不到時（最多 :data:`WITNESS_MAX` 份）視為不可行、換題。
**不放寬任何驗證或預算**——只決定要不要出這個題目。

確定性：候選的順序只依內容庫與題目（排序、不用亂數與內建 ``hash()``），同題目必得同結果。
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import replace
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.skillgen.proposal import ProposalContext, proposal_from_skill, reaction_events
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_layouts import layout_of_effects
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    ProposalSubset,
    SubsetError,
    build_subset_models,
    legal_core_primitives,
    select_subset,
)
from trpg.skillgen.proposal_topup import keyword_effect_rules

__all__ = ["WITNESS_MAX", "has_witness", "witness_proposals"]

WITNESS_MAX = 48
"""每個題目最多驗證幾份建構的提議（原型值；每份約 20～60 毫秒）。"""
_AFFECTS: tuple[str | None, ...] = ("enemies", "allies", "self", None)
"""核心效果的對象（``None`` ＝ 不填：擊倒、地形這類不吃 ``affects`` 的原語）。"""
_TEMPLATES_PER_PRIMITIVE = 4
_KEYWORD_WAYS = 4
_SHAPES = 4
_CORES = 3
_EVENTS = 2
_FIRST_SHAPES = ("single", "self")
_CATEGORIES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "melee": (("weapon", "melee", "str"), ("spell", "any", "int")),
    "ranged": (("weapon", "ranged", "dex"), ("spell", "any", "int")),
    "focus": (("spell", "focus", "int"),),
}
"""武器大類 → 要試的（category, weapon_req, scaling_attr）；與 ``weapon_problem`` 相容的組合。"""

_KEEP = frozenset(
    {"element", "status", "surface", "object", "stack", "unit", "tag", "infusion", "knock_prone"}
)
"""手寫寫法只留這些參數（推導表比對用的欄位）；條件、巢狀效果、數值都不帶，交給補值與補強。"""

_TEMPLATE_CACHE: list[tuple[ContentLibrary, dict[str, tuple[dict[str, Any], ...]]]] = []


def _key(effect: Mapping[str, Any]) -> str:
    return json.dumps(effect, sort_keys=True, ensure_ascii=False)


def _templates(library: ContentLibrary) -> dict[str, tuple[dict[str, Any], ...]]:
    """手寫技能（轉成提議）裡每種原語的效果寫法（去掉 ``affects``，依 JSON 排序）。"""
    for cached, found in _TEMPLATE_CACHE:
        if cached is library:
            return found
    table: dict[str, dict[str, dict[str, Any]]] = {}
    for skill_id in sorted(player_skills(library)):
        try:
            data = proposal_from_skill(player_skills(library)[skill_id], library)
        except ValueError:
            continue
        for effect in data.get("effects", []):
            bare = {k: v for k, v in effect.items() if k in _KEEP or k == "type"}
            table.setdefault(str(bare["type"]), {})[_key(bare)] = bare
    found = {p: tuple(v[k] for k in sorted(v)) for p, v in table.items()}
    _TEMPLATE_CACHE[:] = [*_TEMPLATE_CACHE[-3:], (library, found)]
    return found


def _keyword_ways(
    library: ContentLibrary, keyword: str, primitives: Sequence[str]
) -> list[dict[str, Any]]:
    """關鍵字的專屬效果寫法（選單內的原語；推導表參數 ＋ 手寫技能裡符合參數的寫法）。"""
    templates = _templates(library)
    ways: dict[str, dict[str, Any]] = {}
    for rule in keyword_effect_rules(library, keyword):
        if rule.source_id not in primitives:
            continue
        params = dict(sorted(rule.params().items()))
        if rule.source_id == "damage":
            params.setdefault("element", "physical")
        plain = {"type": rule.source_id, **params}
        ways.setdefault(_key(plain), plain)
        for template in templates.get(rule.source_id, ()):
            if all(template.get(k) == v for k, v in params.items()):
                ways.setdefault(_key(template), dict(template))
                break
    return list(ways.values())[:_KEYWORD_WAYS]


def _with_affects(library: ContentLibrary, effect: Mapping[str, Any]) -> dict[str, Any]:
    """關鍵字效果的對象：有益狀態給友方、其他（有害狀態、傷害、有害原語）打敵方；不吃對象的不填。"""
    if effect["type"] not in {"apply_status", "damage", "delayed_damage"}:
        primitive = library.ruleset.primitives.by_id().get(str(effect["type"]))
        if primitive is None or not primitive.harmful:
            return dict(effect)
    status = library.ruleset.statuses.by_id().get(str(effect.get("status", "")))
    target = "allies" if status is not None and status.beneficial else "enemies"
    return {**effect, "affects": target}


def _enum(defs: Mapping[str, Any], node: object) -> list[Any]:
    """JSON Schema 節點的列舉值（追 ``$ref``、``anyOf``）；不是列舉時為空。"""
    if not isinstance(node, Mapping):
        return []
    if "enum" in node:
        return list(node["enum"])
    if "$ref" in node:
        return _enum(defs, defs.get(str(node["$ref"]).rsplit("/", 1)[-1]))
    for alternative in node.get("anyOf", ()):
        found = _enum(defs, alternative)
        if found:
            return found
    return []


def _required_enums(defs: Mapping[str, Any], core: str) -> dict[str, list[Any]] | None:
    """提議模型裡核心原語的必填列舉欄位（例：``apply_status`` 的 ``status``）與可用值；模型裡沒有
    這個原語、或有不能列舉的必填欄位時為 ``None``（只用手寫寫法）。"""
    for name in (f"Effect_{core}", f"Effect_{core}_plain"):
        found = defs.get(name)
        if not isinstance(found, Mapping):
            continue
        props = found.get("properties", {})
        out: dict[str, list[Any]] = {}
        for field in found.get("required", ()):
            if field in ("type", "affects"):
                continue
            values = _enum(defs, props.get(field))
            if not values:
                return None
            out[field] = values
        return out
    return None


def _allowed(effect: Mapping[str, Any], enums: Mapping[str, list[Any]] | None) -> bool:
    return enums is None or all(
        effect.get(field) in values for field, values in enums.items() if field in effect
    )


def _core_options(
    library: ContentLibrary, core: str, keywords: Sequence[str], defs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """核心效果的寫法：帶到題目關鍵字的寫法 → 手寫技能裡的寫法（只留選單可用的值）→ 必填列舉欄位
    的前幾個可用值 → 只有類型。"""
    enums = _required_enums(defs, core)
    options: dict[str, dict[str, Any]] = {}
    for keyword in keywords:
        for rule in keyword_effect_rules(library, keyword):
            if rule.source_id == core:
                way = {"type": core, **dict(sorted(rule.params().items()))}
                options.setdefault(_key(way), way)
    usable = [t for t in _templates(library).get(core, ()) if _allowed(t, enums)]
    for template in usable[:_TEMPLATES_PER_PRIMITIVE]:
        options.setdefault(_key(template), dict(template))
    if enums:
        fields = sorted(enums)
        lists = [enums[f][:_TEMPLATES_PER_PRIMITIVE] for f in fields]
        for combo in itertools.islice(itertools.product(*lists), _TEMPLATES_PER_PRIMITIVE):
            way = {"type": core, **dict(zip(fields, combo, strict=True))}
            options.setdefault(_key(way), way)
    if not enums:
        options.setdefault(_key({"type": core}), {"type": core})
    return [o for o in options.values() if _allowed(o, enums)]


def _skill_elements(library: ContentLibrary, core: str) -> tuple[str | None, ...]:
    """核心原語需要的技能元素（互斥規則 ``require.elements_any``，例：地形限大地）；不需要時為
    ``(None,)``。"""
    for rule in library.exclusions.rules:
        when, require = rule.when, rule.require
        if when is None or require is None or not require.elements_any:
            continue
        matches = [when, *(when.any_of or ())]
        if any(core in (m.primitives_any or ()) for m in matches):
            return tuple(require.elements_any)
    return (None,)


def _shape(library: ContentLibrary, shape_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {"type": shape_id}
    for name, spec in sorted(library.ruleset.shapes.by_id()[shape_id].params.items()):
        out[name] = max(spec.min, min(spec.max, 3))
    return out


def _shapes(library: ContentLibrary, subset: ProposalSubset, skeleton: str) -> list[str]:
    allowed = library.skeletons[skeleton].shapes
    found = [s for s in subset.shapes if s in allowed]
    return sorted(found, key=lambda s: (s not in _FIRST_SHAPES, s))[:_SHAPES]


def _cores(library: ContentLibrary, request: ProposalRequest) -> list[str]:
    if request.core_primitive is not None:
        return [request.core_primitive]
    return list(legal_core_primitives(library, request))[:_CORES]


def _extras(
    library: ContentLibrary, request: ProposalRequest, subset: ProposalSubset
) -> list[list[dict[str, Any]]]:
    """每個關鍵字各一個專屬效果的組合（第一份是不加，讓核心自己或結構補強帶關鍵字）。"""
    per = [
        [_with_affects(library, w) for w in _keyword_ways(library, k, subset.primitives)] or [{}]
        for k in request.keywords
    ]
    combos = [list(c) for c in itertools.product(*per)] if per else []
    return [[], *combos]


def _skeleton_proposals(
    library: ContentLibrary,
    request: ProposalRequest,
    subset: ProposalSubset,
    skeleton: str,
    defs: Mapping[str, Any],
) -> Iterator[dict[str, Any]]:
    categories = _CATEGORIES.get(request.weapon_class or "focus", _CATEGORIES["focus"])
    events = [e for e, _ in reaction_events(library)][:_EVENTS]
    extras = _extras(library, request, subset)
    core_ok = library.skeletons[skeleton].core.primitives
    for core in (c for c in _cores(library, request) if c in core_ok):
        for head, extra, affects, category, element, shape in itertools.product(
            _core_options(library, core, request.keywords, defs),
            extras,
            _AFFECTS,
            categories,
            _skill_elements(library, core),
            _shapes(library, subset, skeleton),
        ):
            first = dict(head) if affects is None else {**head, "affects": affects}
            data: dict[str, Any] = {
                "layout": layout_of_effects(library, [core]),
                "kind": subset.kind,
                "skeleton": skeleton,
                "category": category[0],
                "weapon_req": category[1],
                "scaling_attr": category[2],
                "shape": _shape(library, shape),
                "effects": [first, *(e for e in extra if e)],
            }
            if element is not None:
                data["element"] = element
            if subset.kind != "reaction":
                yield data
                continue
            for event in events:
                yield {**data, "reaction": {"event": event}}


def witness_proposals(
    library: ContentLibrary,
    request: ProposalRequest,
    subset: ProposalSubset,
    defs: Mapping[str, Any],
) -> Iterator[dict[str, Any]]:
    """依序要驗證的建構提議（確定性；各骨架輪流出一份，見模組說明）。``defs`` 是提議模型 JSON
    Schema 的 ``$defs``（列舉欄位的可用值）。"""
    streams = [
        _skeleton_proposals(library, request, subset, skeleton, defs)
        for skeleton in subset.skeletons
    ]
    while streams:
        alive = []
        for stream in streams:
            item = next(stream, None)
            if item is not None:
                alive.append(stream)
                yield item
        streams = alive


def has_witness(
    library: ContentLibrary,
    request: ProposalRequest,
    ctx: ProposalContext,
    *,
    seed: int,
    limit: int = WITNESS_MAX,
) -> bool:
    """題目至少有一份建構的提議通過完整驗證（含題目要求與武器相容）。``ctx`` 是送給提議迴圈的
    上下文；題目的關鍵字、核心、武器大類由 ``request`` 補上（與 ``propose_skill`` 相同）。"""
    try:
        subset = select_subset(library, request)
    except SubsetError:
        return False
    models = build_subset_models(library, subset)
    defs = models.json_schema().get("$defs", {})
    full = replace(
        ctx,
        keywords=request.keywords,
        core_primitive=request.core_primitive,
        weapon_class=request.weapon_class,
    )
    for data in itertools.islice(witness_proposals(library, request, subset, defs), limit):
        if evaluate_with_repair(data, models, library, full, seed=seed).ok:
            return True
    return False
