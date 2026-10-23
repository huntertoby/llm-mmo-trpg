"""提議的 schema 子集（Phase 4-L4）：依題目只留下相關的骨架、原語、形狀、條件、觸發。

本機模型的上下文只有 32k：整份提議 schema 約 5 萬 token，放不下。:func:`select_subset` 依
「稀有度 → 骨架範圍 → 題目關鍵字 → 大小上限」篩出 :class:`ProposalSubset`；
:func:`build_subset_models` 產生只含子集的提議模型（篩掉的值被提議時得到 ``union_tag_invalid`` 或
``literal_error``，``allowed`` 只列子集內的值）；:func:`available_payload` 產生 prompt 資料區的
``available``（每項只有 ID 與一句短說明，不含數值）。

純函式、確定性：同一題目永遠得到相同的子集（欄位一律排序後的 tuple）。不呼叫 LLM、不匯入
``trpg.llm``（大小估算用 ``trpg.shared.tokens``）。數值不在這一層（提議不含數值，由預算器補）。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordDef
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import PrimitiveDef, SkillRarity, rarity_rank
from trpg.shared.tokens import PROMPT_TOKEN_BUDGET, estimate_tokens
from trpg.skillgen.proposal import (
    CLOSED_SKELETONS,
    NESTED_EFFECT_TYPES,
    PROPOSAL_KINDS,
    ProposalModels,
    build_proposal_models,
)
from trpg.skillgen.proposal_numbers import numeric_param_names

__all__ = [
    "DEFAULT_SUBSET_TOKEN_BUDGET",
    "MAX_KEYWORDS",
    "ProposalRequest",
    "ProposalSubset",
    "SubsetError",
    "available_payload",
    "build_subset_models",
    "json_tokens",
    "select_subset",
    "subset_tokens",
]

MAX_KEYWORDS = 2
DEFAULT_SUBSET_TOKEN_BUDGET = PROMPT_TOKEN_BUDGET - 6_000
"""schema ＋ ``available`` 的預設上限：總上限扣掉固定 prompt（系統指令、題目、玩家文字、重試回饋）
的預留。:func:`trpg.llm.prompts.build_proposal_prompt` 會用實際的固定 prompt 大小算出更精確的值。"""
_KINDS = frozenset(PROPOSAL_KINDS)


class SubsetError(Exception):
    """題目沒有可用的結構（沒有合法骨架、核心原語，或大小放不下）；4-L5 會退回組合器。"""


@dataclass(frozen=True, slots=True)
class ProposalRequest:
    """提議的題目：階級、稀有度、種類、骨架與（至多 2 個）關鍵字。

    ``kind`` 省略時依骨架（沒有骨架則為 ``active``）。ID 是否存在於內容庫由 :func:`select_subset`
    檢查（未知 ID 丟 ``ValueError``）。
    """

    tier: int
    rarity: SkillRarity
    kind: str | None = None
    skeleton: str | None = None
    keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tier < 1:
            raise ValueError(f"階級必須 ≥ 1，收到 {self.tier}")
        if self.kind is not None and self.kind not in _KINDS:
            raise ValueError(
                f"技能種類 {self.kind!r} 不開放提議（可用：{'、'.join(PROPOSAL_KINDS)}）"
            )
        if len(self.keywords) > MAX_KEYWORDS or len(set(self.keywords)) != len(self.keywords):
            raise ValueError(f"關鍵字最多 {MAX_KEYWORDS} 個且不可重複，收到 {list(self.keywords)}")


@dataclass(frozen=True, slots=True)
class ProposalSubset:
    """:func:`select_subset` 的結果（欄位都是排序後的 tuple）。

    ``kind`` 是解析後的技能種類；``dropped`` 是（ID，中文原因）：題目要的或候選的東西沒進子集的
    原因，供報告與除錯；``tokens`` 是 schema ＋ ``available`` 的估算。
    """

    kind: str
    skeletons: tuple[str, ...]
    primitives: tuple[str, ...]
    shapes: tuple[str, ...]
    conditions: tuple[str, ...]
    triggers: tuple[str, ...]
    keywords: tuple[str, ...]
    dropped: tuple[tuple[str, str], ...] = ()
    tokens: int = 0


# ---------------------------------------------------------------------------
# 模型與 available
# ---------------------------------------------------------------------------


def build_subset_models(library: ContentLibrary, subset: ProposalSubset) -> ProposalModels:
    """只含子集的提議模型（:func:`~trpg.skillgen.proposal.build_proposal_models` 的便利包裝）。"""
    return build_proposal_models(
        library,
        primitives=subset.primitives,
        shapes=subset.shapes,
        conditions=subset.conditions,
        triggers=subset.triggers,
        skeletons=subset.skeletons,
    )


def available_payload(library: ContentLibrary, subset: ProposalSubset) -> dict[str, Any]:
    """prompt 資料區的 ``available``：只列子集內的項目（依 ID 排序），每項 ``{id, hint}``。

    ``hint`` 是 ``llm_hint``（骨架與關鍵字沒有 ``llm_hint``，用 ``description_zh``）；原語另帶
    ``params``（參數名 → 說明；數值參數由預算器補，不列）。不放數值、``min``／``max``。
    """
    rules = library.ruleset
    primitives = rules.primitives.by_id()
    shapes = rules.shapes.by_id()
    conditions = rules.conditions.by_id()
    triggers = rules.skill_triggers.by_id()
    keywords = rules.keywords.by_id()
    return {
        "skeletons": [
            {"id": i, "hint": library.skeletons[i].description_zh} for i in sorted(subset.skeletons)
        ],
        "primitives": [_primitive_entry(primitives[i]) for i in sorted(subset.primitives)],
        "shapes": [{"id": i, "hint": shapes[i].llm_hint} for i in sorted(subset.shapes)],
        "conditions": [
            {"id": i, "hint": conditions[i].llm_hint} for i in sorted(subset.conditions)
        ],
        "triggers": [{"id": i, "hint": triggers[i].llm_hint} for i in sorted(subset.triggers)],
        "keywords": [
            {"id": i, "name_zh": keywords[i].name_zh, "hint": keywords[i].description_zh}
            for i in sorted(subset.keywords)
        ],
    }


def _primitive_entry(primitive: PrimitiveDef) -> dict[str, Any]:
    numeric = numeric_param_names(primitive.params)
    return {
        "id": primitive.id,
        "hint": primitive.llm_hint,
        "params": {
            name: spec.llm_hint
            for name, spec in sorted(primitive.params.items())
            if name not in numeric
        },
    }


def subset_tokens(library: ContentLibrary, subset: ProposalSubset) -> int:
    """子集的 schema ＋ ``available`` 的 token 估算。"""
    schema = build_subset_models(library, subset).json_schema()
    return json_tokens(schema) + json_tokens(available_payload(library, subset))


def json_tokens(value: object) -> int:
    """JSON 值（緊湊、鍵排序、不跳脫中文）的 token 估算。"""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return estimate_tokens(text)


# ---------------------------------------------------------------------------
# 篩選
# ---------------------------------------------------------------------------


def _rarity_ok(minimum: str, rarity: str) -> bool:
    return rarity_rank(minimum) <= rarity_rank(rarity)


def _need(rarity: str) -> str:
    return f"稀有度不足（需要 {rarity}）"


class _Selector:
    """一次篩選的狀態。"""

    def __init__(self, library: ContentLibrary, request: ProposalRequest) -> None:
        self.library = library
        self.request = request
        rules = library.ruleset
        self.rarity = request.rarity
        self.primitive_defs = rules.primitives.by_id()
        self.shape_defs = rules.shapes.by_id()
        self.condition_defs = rules.conditions.by_id()
        self.trigger_defs = rules.skill_triggers.by_id()
        self.dropped: dict[str, str] = {}

    def drop(self, key: str, reason: str) -> None:
        self.dropped.setdefault(key, reason)

    # -- 骨架 ---------------------------------------------------------------

    def resolve_kind(self) -> str:
        request = self.request
        if request.kind is not None:
            return request.kind
        if request.skeleton is not None:
            skeleton = self._known_skeleton(request.skeleton)
            return next((k for k in PROPOSAL_KINDS if k in skeleton.kinds), "active")
        return "active"

    def _known_skeleton(self, skeleton_id: str) -> SkeletonDef:
        skeleton = self.library.skeletons.get(skeleton_id)
        if skeleton is None:
            raise ValueError(
                f"未知的骨架 {skeleton_id!r}（可用：{'、'.join(sorted(self.library.skeletons))}）"
            )
        return skeleton

    def candidate_skeletons(self, kind: str) -> list[SkeletonDef]:
        """題目指定的骨架，或全部 ``enabled``、適用此種類、提議模型開放的骨架。"""
        if self.request.skeleton is not None:
            skeleton = self._known_skeleton(self.request.skeleton)
            if skeleton.id in CLOSED_SKELETONS or not skeleton.enabled:
                raise SubsetError(f"骨架 {skeleton.id} 不開放提議")
            if kind not in skeleton.kinds:
                raise SubsetError(f"骨架 {skeleton.id} 不適用 {kind} 技能")
            return [skeleton]
        found = [
            s
            for _, s in sorted(self.library.skeletons.items())
            if s.enabled and kind in s.kinds and s.id not in CLOSED_SKELETONS
        ]
        return found

    def viable(self, skeleton: SkeletonDef, kind: str) -> bool:
        """骨架在這個稀有度下是否有合法的核心原語、形狀與（需要時）條件。"""
        why = self._unusable_reason(skeleton, kind)
        if why is not None:
            self.drop(skeleton.id, why)
        return why is None

    def _unusable_reason(self, skeleton: SkeletonDef, kind: str) -> str | None:
        checks = (
            (not _rarity_ok(skeleton.min_rarity, self.rarity), _need(skeleton.min_rarity)),
            (not self.core_primitives(skeleton), "沒有稀有度足夠的核心原語"),
            (
                bool(skeleton.require_any_primitives)
                and not self.legal_primitives(skeleton.require_any_primitives),
                "必要的原語稀有度不足",
            ),
            (not self.skeleton_shapes(skeleton), "沒有稀有度足夠的形狀"),
            (
                skeleton.requires_condition and not self.legal_conditions(),
                "需要條件，但此稀有度沒有可用的條件",
            ),
            (kind == "passive" and not self.legal_triggers(), "此稀有度沒有可用的觸發時機"),
        )
        return next((reason for failed, reason in checks if failed), None)

    # -- 合法清單（依 YAML 順序）---------------------------------------------------

    def legal_primitives(self, ids: Iterable[str]) -> list[str]:
        wanted = set(ids)
        return [
            p.id
            for p in self.library.ruleset.primitives.primitives
            if p.id in wanted and _rarity_ok(p.min_rarity, self.rarity)
        ]

    def core_primitives(self, skeleton: SkeletonDef) -> list[str]:
        return self.legal_primitives(skeleton.core.primitives)

    def secondary_primitives(self, skeleton: SkeletonDef) -> list[str]:
        """骨架允許的附帶原語（無附帶名額者沒有；primitives 省略為不限；harmful_only 只留有害）"""
        rules = skeleton.secondary
        if rules.max_count <= 0:
            return []
        pool = (
            [p.id for p in self.library.ruleset.primitives.primitives]
            if rules.primitives is None
            else list(rules.primitives)
        )
        legal = self.legal_primitives(pool)
        if rules.harmful_only:
            legal = [i for i in legal if self.primitive_defs[i].harmful]
        return legal

    def skeleton_shapes(self, skeleton: SkeletonDef) -> list[str]:
        return [
            s.id
            for s in self.library.ruleset.shapes.shapes
            if s.id in skeleton.shapes and _rarity_ok(s.min_rarity, self.rarity)
        ]

    def legal_conditions(self) -> list[str]:
        return [
            c.id
            for c in self.library.ruleset.conditions.conditions
            if _rarity_ok(c.min_rarity, self.rarity)
        ]

    def legal_triggers(self) -> list[str]:
        return [
            t.id
            for t in self.library.ruleset.skill_triggers.triggers
            if _rarity_ok(t.min_rarity, self.rarity)
        ]

    def support_primitives(self, primitives: Iterable[str]) -> list[str]:
        """必收原語的必填巢狀參數（``then``、``effects``）需要的原語（否則該原語無法表達）。"""
        found: set[str] = set()
        for pid in primitives:
            for name, spec in self.primitive_defs[pid].params.items():
                if spec.type == "effects" and spec.required:
                    found.update(NESTED_EFFECT_TYPES.get(name, ()))
        return self.legal_primitives(found)

    # -- 關鍵字 -------------------------------------------------------------------

    def keyword_defs(self) -> list[KeywordDef]:
        table = self.library.ruleset.keywords.by_id()
        out = []
        for keyword_id in self.request.keywords:
            if keyword_id not in table:
                raise ValueError(f"未知的關鍵字 {keyword_id!r}（可用：{'、'.join(sorted(table))}）")
            out.append(table[keyword_id])
        return out

    def keyword_wants(self) -> dict[str, set[str]]:
        """題目關鍵字的專屬規則（``grade`` 省略者）要的原語、條件、觸發、形狀。"""
        wants: dict[str, set[str]] = {
            "effect": set(),
            "condition": set(),
            "trigger": set(),
            "shape": set(),
        }
        for keyword in self.keyword_defs():
            for rule in (*keyword.makes, *keyword.uses):
                if rule.grade == "exclusive" and rule.source in wants:
                    wants[rule.source].add(rule.source_id)
        return wants


def _split(wanted: Iterable[str], allowed: Iterable[str], drop: Any, reason: str) -> list[str]:
    """``wanted`` 中在 ``allowed`` 內的留下（排序）；其餘記進 ``dropped``。"""
    ok = set(allowed)
    keep = []
    for item in sorted(set(wanted)):
        if item in ok:
            keep.append(item)
        else:
            drop(item, reason)
    return keep


def select_subset(
    library: ContentLibrary,
    request: ProposalRequest,
    *,
    token_budget: int = DEFAULT_SUBSET_TOKEN_BUDGET,
) -> ProposalSubset:
    """依題目篩出 schema 子集（純函式、確定性）。

    順序：骨架 → 稀有度 → 骨架範圍（原語、形狀）→ 題目關鍵字（專屬規則的原語與條件優先收）
    → 補足（依 YAML 順序補其他合法原語與條件，直到 schema ＋ ``available`` 的估算達
    ``token_budget``；先砍條件、再砍附帶原語，優先收的最後砍，核心原語永不砍）。

    未知的骨架或關鍵字 ID 丟 ``ValueError``；沒有任何合法骨架或核心原語、或連核心結構都放不進
    ``token_budget`` 時丟 :class:`SubsetError`。
    """
    sel = _Selector(library, request)
    kind = sel.resolve_kind()
    wants = sel.keyword_wants()
    skeletons = [s for s in sel.candidate_skeletons(kind) if sel.viable(s, kind)]
    if not skeletons:
        reasons = "；".join(f"{k}：{v}" for k, v in sorted(sel.dropped.items())) or "沒有候選骨架"
        raise SubsetError(f"沒有可用的骨架（{reasons}）")

    plan = _plan(sel, skeletons, kind, wants)

    def make(n_prims: int, n_conds: int) -> ProposalSubset:
        return ProposalSubset(
            kind=kind,
            skeletons=tuple(sorted(s.id for s in skeletons)),
            primitives=tuple(sorted([*plan.core, *plan.ranked_primitives[:n_prims]])),
            shapes=tuple(sorted(plan.shapes)),
            conditions=tuple(
                sorted([*plan.required_conditions, *plan.ranked_conditions[:n_conds]])
            ),
            triggers=tuple(sorted(plan.triggers)),
            keywords=tuple(sorted(request.keywords)),
        )

    def fits(n_prims: int, n_conds: int) -> bool:
        return subset_tokens(library, make(n_prims, n_conds)) <= token_budget

    n_prims = _largest(len(plan.ranked_primitives), lambda n: fits(n, 0))
    if n_prims is None:
        raise SubsetError(f"核心結構已超過 {token_budget} token，放不進 prompt")
    n_conds = _largest(len(plan.ranked_conditions), lambda n: fits(n_prims, n)) or 0
    for item in (*plan.ranked_primitives[n_prims:], *plan.ranked_conditions[n_conds:]):
        sel.drop(item, "超過大小上限，未收入")
    final = make(n_prims, n_conds)
    models = build_subset_models(library, final)
    for item, why in models.excluded_primitives:
        if item in models.primitive_ids:
            continue  # 只是不能用在變奏
        sel.drop(item, why)
    final = replace(final, primitives=tuple(sorted(models.primitive_ids)))
    return replace(
        final, dropped=tuple(sorted(sel.dropped.items())), tokens=subset_tokens(library, final)
    )


@dataclass(frozen=True, slots=True)
class _Plan:
    """篩選的中間結果：永遠收入的（核心原語與其巢狀所需、骨架必要的條件）與依優先順序排好的候選。

    ``ranked_*`` 先放題目關鍵字要的，再依 YAML 順序放其餘合法的；超過大小上限時從尾端砍起。"""

    core: tuple[str, ...]
    ranked_primitives: tuple[str, ...]
    required_conditions: tuple[str, ...]
    ranked_conditions: tuple[str, ...]
    shapes: tuple[str, ...]
    triggers: tuple[str, ...]


def _plan(
    sel: _Selector, skeletons: list[SkeletonDef], kind: str, wants: Mapping[str, set[str]]
) -> _Plan:
    core: set[str] = set()
    optional: set[str] = set()
    shapes: set[str] = set()
    for skeleton in skeletons:
        core.update(sel.core_primitives(skeleton))
        core.update(sel.legal_primitives(skeleton.require_any_primitives))
        optional.update(sel.secondary_primitives(skeleton))
        shapes.update(sel.skeleton_shapes(skeleton))
    conditions = sel.legal_conditions()
    triggers = sel.legal_triggers() if kind == "passive" else []

    wanted = _split(wants["effect"], core | optional, sel.drop, "骨架範圍外或稀有度不足，不收")
    wanted_conditions = _split(wants["condition"], conditions, sel.drop, "稀有度不足，不收")
    _split(wants["shape"], shapes, sel.drop, "骨架不允許或稀有度不足，不收")
    _split(wants["trigger"], triggers, sel.drop, "此題目不收觸發或稀有度不足")
    required = conditions[:1] if any(s.requires_condition for s in skeletons) else []

    core.update(sel.support_primitives(core))
    yaml_order = [p.id for p in sel.library.ruleset.primitives.primitives]
    prioritized = [i for i in yaml_order if i in wanted and i not in core]
    rest = [i for i in yaml_order if i in optional | set(sel.support_primitives(wanted))]
    ranked = [*prioritized, *(i for i in rest if i not in core and i not in prioritized)]
    ranked_conditions = [c for c in wanted_conditions if c not in required]
    ranked_conditions += [c for c in conditions if c not in required and c not in ranked_conditions]
    return _Plan(
        core=tuple(sorted(core)),
        ranked_primitives=tuple(ranked),
        required_conditions=tuple(required),
        ranked_conditions=tuple(ranked_conditions),
        shapes=tuple(sorted(shapes)),
        triggers=tuple(sorted(triggers)),
    )


def _largest(upper: int, ok: Any) -> int | None:
    """最大的 ``n`` ∈ [0, upper] 使 ``ok(n)`` 為真（假設單調）；連 0 都不行回傳 ``None``。"""
    if ok(upper):
        return upper
    if not ok(0):
        return None
    low, high = 0, upper  # ok(low) 為真、ok(high) 為假
    while high - low > 1:
        mid = (low + high) // 2
        if ok(mid):
            low = mid
        else:
            high = mid
    return low
