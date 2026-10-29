"""提議格式的結構往返盤點（Phase 4-L8）：手寫技能有多少能用提議模型表達。

對內容庫的每一招手寫技能做 :func:`~trpg.skillgen.proposal.proposal_from_skill` → 以原本的數值
補回（:func:`~trpg.skillgen.proposal_numbers.fixed_filler`）→ :func:`evaluate_proposal`，結果與
原技能「除 ID 與來源外相同」才算往返成功（武器技與縮放例外清單的縮放屬性由引擎決定，不比對）。失敗的
技能依原因分類（:data:`CATEGORIES`），供報告與覆蓋率下限測試使用。

只讀內容資料、不呼叫 LLM；結果依技能 ID 排序，完全確定。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from trpg.content.keyword_derive import skill_condition_specs
from trpg.content.library import ContentLibrary
from trpg.content.skills import ENTER_FORM, LEAVE_FORM, SkillDef
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
    proposal_from_skill,
)
from trpg.skillgen.proposal_numbers import fixed_filler, split_numbers

__all__ = [
    "CATEGORIES",
    "CATEGORY_ZH",
    "Inventory",
    "InventoryRow",
    "round_trip_inventory",
    "same_structure",
]

CATEGORIES: tuple[str, ...] = (
    "modifier",
    "form",
    "followup",
    "reaction",
    "cost",
    "nested_only",
    "other",
)
"""失敗原因的分類（判定順序；一招技能只歸一類）。"""
CATEGORY_ZH: dict[str, str] = {
    "modifier": "修正規則（modifiers）",
    "form": "形態／種族專屬",
    "followup": "複合技能（followup）",
    "reaction": "反應（reaction）",
    "cost": "代價欄位",
    "nested_only": "只能巢狀的效果",
    "other": "其他",
}
_FORM_PRIMITIVES = frozenset({ENTER_FORM, LEAVE_FORM})
_COST_FIELDS = ("source", "uses_per_battle", "stacks", "hp_percent", "on_miss")


@dataclass(frozen=True, slots=True)
class InventoryRow:
    """一招技能的盤點結果：``ok`` 往返成功；失敗時 ``category`` 是分類、``detail`` 是原因摘要。"""

    skill_id: str
    ok: bool
    category: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Inventory:
    """全部手寫技能的盤點（依技能 ID 排序）。"""

    rows: tuple[InventoryRow, ...]

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.rows if r.ok)

    def by_category(self) -> dict[str, list[str]]:
        """分類 → 失敗的技能 ID（依 :data:`CATEGORIES` 的順序，只列有技能的分類）。"""
        out: dict[str, list[str]] = {}
        for category in CATEGORIES:
            ids = [r.skill_id for r in self.rows if not r.ok and r.category == category]
            if ids:
                out[category] = ids
        return out

    def details(self, category: str) -> Counter[str]:
        """某分類的原因摘要 → 技能數。"""
        return Counter(r.detail for r in self.rows if not r.ok and r.category == category)


def same_structure(a: SkillDef, b: SkillDef, library: ContentLibrary) -> bool:
    """往返等價：除了 ID 與來源（呼叫端決定）以外完全相同；武器技（縮放屬性看武器大類，3H-6）與
    ``skill_scaling.yaml`` 例外清單裡的技能（3H-7）不比對縮放屬性。``b`` 是原本的手寫技能。"""
    skip = {"id", "provenance"}
    excepted = {o.skill for o in library.skill_scaling.overrides}
    if b.category == "weapon" or b.id in excepted:
        skip |= {"scaling_attr", "secondary_scaling_attr"}
    return a.model_dump(exclude=skip) == b.model_dump(exclude=skip)


def _category(skill: SkillDef, library: ContentLibrary) -> str:
    """失敗技能的分類：依下列順序取第一個符合的（常駐類傳說的啟動 ``activation`` 歸「其他」，
    不算代價欄位）。"""
    effects = list(skill.iter_effects(include_followup=True, include_backlash=True))
    conditions = {c.type for c in skill_condition_specs(skill)}
    primitives = library.ruleset.primitives.by_id()
    cost = skill.cost
    checks = (
        ("modifier", bool(skill.modifiers) or skill.kind == "modifier"),
        (
            "form",
            "in_form" in conditions
            or any(e.type in _FORM_PRIMITIVES for e in effects)
            or any(e.form_bonus_permille is not None for e in effects),
        ),
        ("followup", skill.followup is not None),
        ("reaction", skill.reaction is not None or skill.kind == "reaction"),
        ("other", skill.activation is not None),
        ("cost", any(getattr(cost, name) not in (None, ()) for name in _COST_FIELDS)),
        ("nested_only", any(e.type not in primitives for e in effects)),
    )
    return next((category for category, hit in checks if hit), "other")


def _row(skill: SkillDef, library: ContentLibrary, models: ProposalModels) -> InventoryRow:
    try:
        proposal = proposal_from_skill(skill, library)
    except ValueError as exc:
        detail = "頂層欄位：" + str(exc).rsplit("：", 1)[-1]
        return InventoryRow(skill.id, False, _category(skill, library), detail)
    _, removed = split_numbers(skill.model_dump(mode="json", exclude_defaults=True), library)
    ctx = ProposalContext(tier=skill.tier, rarity=skill.rarity, rank=skill.rank)
    result = evaluate_proposal(proposal, models, library, ctx, fill=fixed_filler(removed))
    if result.skill is not None and same_structure(result.skill, skill, library):
        return InventoryRow(skill.id, True)
    if result.skill is not None:
        return InventoryRow(skill.id, False, "other", "往返後內容不同")
    codes = sorted({f"{e.stage}/{e.code}" for e in result.errors})
    if _known_rules_only(skill, library, codes):
        return InventoryRow(skill.id, True)
    return InventoryRow(skill.id, False, _category(skill, library), "、".join(codes))


_BUDGET_RANGE = frozenset({"rules/budget.over", "rules/budget.weak"})


def _known_rules_only(skill: SkillDef, library: ContentLibrary, codes: list[str]) -> bool:
    """手寫技能本身已知的規則問題（不是提議格式的問題）：最低花費（3-48c）、射程係數後超出預算
    範圍（3-49 已知例外）。結構可以表達，算往返成功。"""
    allowed: set[str] = set()
    if library.budget.min_cost_problem(skill.kind, skill.category, skill.cost):
        allowed.add("rules/cap.min_cost")
    if skill.id in library.budget.known_budget_exceptions:
        allowed |= _BUDGET_RANGE
    return bool(codes) and set(codes) <= allowed


def round_trip_inventory(
    library: ContentLibrary, models: ProposalModels | None = None
) -> Inventory:
    """對內容庫全部手寫技能做結構往返盤點（``models`` 省略時用完整的提議模型）。"""
    models = models or build_proposal_models(library)
    skills = sorted(library.skills.values(), key=lambda s: s.id)
    return Inventory(tuple(_row(s, library, models) for s in skills))
