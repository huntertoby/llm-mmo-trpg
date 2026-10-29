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
from trpg.content.skills import COMPOSITE_MOVES, PrimitiveDef, SkillRarity, rarity_rank
from trpg.shared.rng import Rng
from trpg.shared.tokens import PROMPT_TOKEN_BUDGET, estimate_tokens
from trpg.skillgen.proposal import (
    CLOSED_SKELETONS,
    NESTED_EFFECT_TYPES,
    PROPOSAL_KINDS,
    ProposalModels,
    build_proposal_models,
    composite_allowed,
    kind_choices,
    reaction_events,
)
from trpg.skillgen.proposal_costs import cost_entries
from trpg.skillgen.proposal_followup import (
    FOLLOWUP_DOC,
    followup_shape_ids,
    followup_when_entries,
    release_entries,
)
from trpg.skillgen.proposal_layouts import layout_hint, plan_layouts
from trpg.skillgen.proposal_numbers import numeric_param_names

__all__ = [
    "DEFAULT_SUBSET_TOKEN_BUDGET",
    "MAX_KEYWORDS",
    "ProposalRequest",
    "ProposalSubset",
    "SubsetError",
    "available_payload",
    "build_subset_models",
    "json_chars",
    "json_tokens",
    "legal_core_primitives",
    "menu_order",
    "select_subset",
    "subset_tokens",
]

MAX_KEYWORDS = 2
SCHEMA_CHAR_LIMIT = 125_000
"""JSON schema 字元數的健全性上限（Phase 4-L5c；schema 只用於約束解碼、不佔 prompt token，所以不算
進 token 估算，但太大的 schema 仍會拖慢解碼）。數值 ＝ 現況最大值 × 2，見 4-L5c 報告。"""
DEFAULT_SUBSET_TOKEN_BUDGET = PROMPT_TOKEN_BUDGET - 6_000
"""``available`` 的預設上限：總上限扣掉固定 prompt（系統指令、題目、玩家文字、重試回饋）
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
    core_primitive: str | None = None
    """題目指定的核心原語（Phase 4-L6，3C 節第 1 點）：只開放它當核心，附帶原語照舊；
    提議必須用到它。
    不在合法核心原語內時 :func:`select_subset` 丟 :class:`SubsetError`。"""
    menu_seed: int | None = None
    """輪替選單的種子（Phase 4-L6，3C 節第 2 點）：有值時附帶原語與條件只開放一部分
    （``skill_composer.yaml`` 的 ``llm_topic``），且 ``available`` 的順序由它打亂；
    ``None`` ＝ 全開、
    依 ID 排序（與 4-L5c 相同）。"""
    weapon_class: str | None = None
    """主角的武器大類（Phase 4-L6）：進 prompt 的題目區塊，技能的武器需求要相容。不影響子集。"""
    theme: str | None = None
    """主題詞 ID（``content/llm/world_*.yaml`` 的 ``themes``；Phase 4-L6，例如 ``nature`` 自然）。
    只進 prompt 的題目區塊，不影響子集。"""

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
    原因，供報告與除錯；``tokens`` 是 ``available`` 的估算（schema 不佔 prompt，4-L5c）；
    ``rarity`` 是題目的稀有度
    （Phase 4-L5b：``apply_status`` 只列這個稀有度能用的狀態；``None`` 為不篩）。
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
    rarity: SkillRarity | None = None
    menu_seed: int | None = None
    """``available`` 的順序種子（``None`` ＝ 依 ID 排序）；只影響呈現，不影響驗證。"""
    followup_skeletons: tuple[str, ...] = ()
    """複合技能第二段可用的骨架（Phase 4-L8；空的 ＝ 不開放 ``followup``）：主動技能、稀有度夠時為
    此稀有度可用的全部主動骨架（不受題目骨架限制）。"""
    followup_shapes: tuple[str, ...] = ()
    """複合技能第二段可用的形狀（Phase 4-L8；YAML 順序，稀有度夠的第二段形狀）。"""
    followup_moves: tuple[str, ...] = ()
    """複合技能第二段另外可用的施放者自身位移（Phase 4-L8；YAML 順序，稀有度夠的
    ``COMPOSITE_MOVES``，即使不在 ``primitives``）。"""


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
        rarity=subset.rarity,
        followup=bool(subset.followup_skeletons),
        followup_skeletons=subset.followup_skeletons or None,
        followup_shapes=subset.followup_shapes,
        followup_moves=subset.followup_moves,
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
    seed = subset.menu_seed
    payload: dict[str, Any] = {
        "layouts": _layout_entries(library, subset),
        "skeletons": [
            _skeleton_entry(library, library.skeletons[i], subset)
            for i in menu_order(subset.skeletons, seed, "skeletons")
        ],
        "primitives": [
            _primitive_entry(primitives[i])
            for i in menu_order(subset.primitives, seed, "primitives")
        ],
        "shapes": [
            {"id": i, "hint": shapes[i].llm_hint} for i in menu_order(subset.shapes, seed, "shapes")
        ],
        "conditions": [
            {"id": i, "hint": conditions[i].llm_hint}
            for i in menu_order(subset.conditions, seed, "conditions")
        ],
        "triggers": [
            {"id": i, "hint": triggers[i].llm_hint}
            for i in menu_order(subset.triggers, seed, "triggers")
        ],
        "keywords": [
            {"id": i, "name_zh": keywords[i].name_zh, "hint": keywords[i].description_zh}
            for i in sorted(subset.keywords)
        ],
    }
    payload.update(_extra_entries(library, subset))
    return payload


def _extra_entries(library: ContentLibrary, subset: ProposalSubset) -> dict[str, Any]:
    """依技能種類多列的結構（Phase 4-L8）：主動技能的代價欄位 ``costs`` 與複合技能 ``followup``；
    反應技能的觸發事件 ``reactions``。"""
    if subset.kind == "reaction":
        return {"reactions": [{"id": e, "hint": h} for e, h in reaction_events(library)]}
    if subset.kind != "active":
        return {}
    out: dict[str, Any] = {"costs": cost_entries(library, subset.rarity)}
    if subset.followup_skeletons:
        shapes = library.ruleset.shapes.by_id()
        primitives = library.ruleset.primitives.by_id()
        out["followup"] = {
            "hint": FOLLOWUP_DOC,
            "when": followup_when_entries(),
            "release": release_entries(),
            "skeletons": list(subset.followup_skeletons),
            "shapes": [{"id": i, "hint": shapes[i].llm_hint} for i in subset.followup_shapes],
            "moves": [
                {"id": i, "hint": primitives[i].llm_hint}
                for i in subset.followup_moves
                if i not in subset.primitives
            ],
        }
    return out


def menu_order(ids: Iterable[str], seed: int | None, label: str) -> list[str]:
    """選單的呈現順序：沒有種子依 ID 排序；有種子時由 ``Rng(seed).fork(label)`` 打亂排序後的清單
    （避免模型偏好排在前面的項目；只影響呈現，不影響驗證）。"""
    ordered = sorted(ids)
    return ordered if seed is None else Rng(seed).fork(f"menu/{label}").shuffled(ordered)


def _layout_entries(library: ContentLibrary, subset: ProposalSubset) -> list[dict[str, str]]:
    """版型（Phase 4-L5b）：``layout`` 的可用值與說明（schema 不進 prompt，模型只看得到這裡）。"""
    plans, _ = plan_layouts(
        library,
        primitives=subset.primitives,
        shapes=subset.shapes,
        kinds=kind_choices(library, subset.skeletons),
    )
    return [{"id": p.id, "hint": layout_hint(library, p)} for p in plans]


def _percent(permille: int) -> str:
    return f"{permille / 10:g}%"


def _skeleton_entry(
    library: ContentLibrary, skeleton: SkeletonDef, subset: ProposalSubset
) -> dict[str, Any]:
    """骨架的說明與結構（Phase 4-L5b）：核心原語與最低占比、附帶原語與數量上限、形狀；清單只列
    子集內的項目。"""
    available = set(subset.primitives)
    core = [i for i in skeleton.core.primitives if i in available]
    core_note = "至少要有一個核心效果"
    if skeleton.core.min_share_permille:
        core_note += (
            f"，核心效果的強度至少占全部效果的 {_percent(skeleton.core.min_share_permille)}"
        )
    if skeleton.core.affects:
        core_note += f"；核心效果的對象只能是 {'、'.join(skeleton.core.affects)}"
    if skeleton.core.beneficial_only:
        core_note += "；核心施加的狀態與表面必須是有益的"
    return {
        "id": skeleton.id,
        "hint": library.skeletons[skeleton.id].description_zh,
        "core": {"primitives": core, "note": core_note + "。"},
        "secondary": _secondary_entry(library, skeleton, available),
        "shapes": [s for s in skeleton.shapes if s in set(subset.shapes)],
    }


def _secondary_entry(
    library: ContentLibrary, skeleton: SkeletonDef, available: set[str]
) -> dict[str, Any]:
    rules = skeleton.secondary
    if rules.max_count <= 0:
        return {"primitives": [], "note": "不能有附帶效果。"}
    defs = library.ruleset.primitives.by_id()
    allowed: list[str] | str = "不限"
    if rules.primitives is not None:
        allowed = [
            i
            for i in rules.primitives
            if i in available and (not rules.harmful_only or defs[i].harmful)
        ]
    note = f"附帶效果（核心以外的效果）最多 {rules.max_count} 個"
    if rules.harmful_only:
        note += "，只能是有害的效果"
    caps = [
        f"{i} 的強度最多占 {_percent(limit)}"
        for i, limit in sorted(rules.max_share_permille.items())
        if i in available
    ]
    if caps:
        note += "；" + "、".join(caps)
    return {"primitives": allowed, "note": note + "。"}


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
    """子集的 ``available`` 的 token 估算（Phase 4-L5c：schema 只用於約束解碼，不佔 prompt token，
    不算在內；schema 另以 :func:`json_chars` 與 :data:`SCHEMA_CHAR_LIMIT` 檢查）。"""
    return json_tokens(available_payload(library, subset))


def json_chars(value: object) -> int:
    """JSON 值（緊湊、鍵排序、不跳脫中文）的字元數。"""
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


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
        self.kind = "active"

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
        """稀有度夠、而且（非主動技能的題目）不是只能用在主動技能的原語（依 YAML 順序）。"""
        wanted = set(ids)
        return [
            p.id
            for p in self.library.ruleset.primitives.primitives
            if p.id in wanted
            and _rarity_ok(p.min_rarity, self.rarity)
            and (self.kind == "active" or not p.active_only)
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
    → 補足（依 YAML 順序補其他合法原語與條件，直到 ``available`` 的估算達
    ``token_budget``；先砍條件、再砍附帶原語，優先收的最後砍，核心原語永不砍）。

    未知的骨架或關鍵字 ID 丟 ``ValueError``；沒有任何合法骨架或核心原語、或連核心結構都放不進
    ``token_budget`` 時丟 :class:`SubsetError`。
    """
    sel = _Selector(library, request)
    kind = sel.resolve_kind()
    sel.kind = kind
    wants = sel.keyword_wants()
    skeletons = [s for s in sel.candidate_skeletons(kind) if sel.viable(s, kind)]
    if not skeletons:
        reasons = "；".join(f"{k}：{v}" for k, v in sorted(sel.dropped.items())) or "沒有候選骨架"
        raise SubsetError(f"沒有可用的骨架（{reasons}）")

    if request.core_primitive is not None:
        skeletons = _with_core(sel, skeletons, request.core_primitive)
    plan = _plan(sel, skeletons, kind, wants)

    follow_skeletons, follow_shapes, follow_moves = _followup_scope(sel, kind)

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
            rarity=request.rarity,
            menu_seed=request.menu_seed,
            followup_skeletons=follow_skeletons,
            followup_shapes=follow_shapes,
            followup_moves=follow_moves,
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
    only = sel.request.core_primitive
    for skeleton in skeletons:
        core.update(sel.core_primitives(skeleton) if only is None else [only])
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
    if sel.request.menu_seed is not None:
        must = [*prioritized, *(i for i in sel.support_primitives(wanted) if i not in core)]
        ranked = _rotate(sel, ranked, must, "primitives", sel.library.composer.llm_topic)
        ranked_conditions = _rotate(
            sel, ranked_conditions, wanted_conditions, "conditions", sel.library.composer.llm_topic
        )
    return _Plan(
        core=tuple(sorted(core)),
        ranked_primitives=tuple(ranked),
        required_conditions=tuple(required),
        ranked_conditions=tuple(ranked_conditions),
        shapes=tuple(sorted(shapes)),
        triggers=tuple(sorted(triggers)),
    )


def _followup_scope(
    sel: _Selector, kind: str
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """複合技能第二段的骨架、形狀與自身位移（Phase 4-L8）：主動技能、稀有度不低於複合技能最低
    稀有度時，為此稀有度可用的主動骨架（排序）、第二段形狀與 ``COMPOSITE_MOVES``（YAML 順序）；
    否則都是空的（不開放）。"""
    if kind != "active" or not composite_allowed(sel.rarity):
        return (), (), ()
    skeletons = tuple(
        sorted(
            s.id
            for s in sel.library.skeletons.values()
            if s.enabled
            and "active" in s.kinds
            and s.id not in CLOSED_SKELETONS
            and sel._unusable_reason(s, "active") is None
        )
    )
    legal = [
        s.id for s in sel.library.ruleset.shapes.shapes if _rarity_ok(s.min_rarity, sel.rarity)
    ]
    moves = tuple(sel.legal_primitives(COMPOSITE_MOVES))
    return skeletons, tuple(followup_shape_ids(sel.library, legal)), moves


def _with_core(
    sel: _Selector, skeletons: list[SkeletonDef], core_primitive: str
) -> list[SkeletonDef]:
    """題目指定核心原語：只留核心可以用它的骨架；沒有就丟 :class:`SubsetError`。"""
    found = [s for s in skeletons if core_primitive in sel.core_primitives(s)]
    if not found:
        legal = "、".join(sorted({p for s in skeletons for p in sel.core_primitives(s)}))
        raise SubsetError(f"核心原語 {core_primitive} 不在合法的核心原語內（{legal}）")
    return found


def legal_core_primitives(library: ContentLibrary, request: ProposalRequest) -> tuple[str, ...]:
    """題目（忽略 ``core_primitive``）可以當核心的原語：合法骨架 × 稀有度足夠的核心原語，扣掉
    ``skill_composer.yaml`` 的 ``llm_topic.core_exclude``（依 YAML 順序）。題目沒有可用結構時丟
    :class:`SubsetError`。"""
    plain = replace(request, core_primitive=None, menu_seed=None)
    sel = _Selector(library, plain)
    kind = sel.resolve_kind()
    sel.kind = kind
    skeletons = [s for s in sel.candidate_skeletons(kind) if sel.viable(s, kind)]
    if not skeletons:
        raise SubsetError("沒有可用的骨架")
    found = {p for s in skeletons for p in sel.core_primitives(s)}
    excluded = set(library.composer.llm_topic.core_exclude)
    return tuple(
        p.id
        for p in library.ruleset.primitives.primitives
        if p.id in found and p.id not in excluded
    )


def _rotate(
    sel: _Selector, ranked: list[str], must: Iterable[str], label: str, rules: Any
) -> list[str]:
    """輪替選單：必收的（題目關鍵字要的與其巢狀所需）照收，其餘由種子抽最多 N 個（保持原順序）。"""
    limit = rules.secondary_count if label == "primitives" else rules.condition_count
    keep = set(must)
    rest = [i for i in ranked if i not in keep]
    seed = sel.request.menu_seed or 0
    picked = set(Rng(seed).fork(f"rotate/{label}").shuffled(rest)[:limit])
    for item in rest:
        if item not in picked:
            sel.drop(item, "輪替選單未收入")
    return [i for i in ranked if i in keep or i in picked]


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
