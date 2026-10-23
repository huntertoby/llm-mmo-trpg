"""提議的「型態」（Phase 4-L5b）：把原語的組合規則放進 schema，讓 LLM 看得見、也填不錯。

``SkillDef`` 的驗證器有一些「某原語要求整招技能的形狀、位置或其他效果的對象」的規則（例：
``charge_through`` 的形狀只能是 ``ground_tile``、必須是第一個效果、其他效果只能
``affects: self``）。這些規則的資料在 ``skill_primitives.yaml``（``allowed_shapes``、
``position``、``sole_effect``、``others_affect``、``max_per_skill``、``active_only``；見
:class:`~trpg.content.skills.CompositionRule`），這裡依同一份資料把提議拆成幾個 **型態**
（頂層欄位 ``form`` 區分的 discriminated union）：

- ``standard``（一般型態）：效果只能用「沒有組合規則」的原語，形狀不含要求特定原語的形狀
  （:data:`~trpg.content.skills.SHAPE_REQUIRED_PRIMITIVES`）。可以帶變奏。
- 每個有組合規則的原語一個型態（``form`` 為原語 ID）：形狀只有它允許的形狀；它本身加上
  「其他效果」——``sole_effect`` 時沒有其他效果、``others_affect: self`` 時其他效果是只作用在
  施放者的版本、否則是一般原語與形狀相容的其他特殊原語。``active_only`` 時 ``kind`` 只有
  ``active``。不帶變奏。

位置（第一個／最後一個）與數量上限仍由驗證器檢查（錯誤帶 path），型態說明會寫出來。純函式、
確定性：只看內容資料與呼叫端給的 ID 清單，結果依 YAML 順序。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    SHAPE_REQUIRED_PRIMITIVES,
    CompositionRule,
    PrimitiveDef,
    SkillDef,
)

__all__ = [
    "SELF_STATUS_PRIMITIVES",
    "SHAPE_FORM_PREFIX",
    "STANDARD_FORM",
    "FormPlan",
    "form_hint",
    "form_id",
    "form_of_effects",
    "is_special",
    "plan_forms",
    "skill_form",
]

STANDARD_FORM = "standard"
"""一般型態的 ``form`` 值。"""
SHAPE_FORM_PREFIX = "on_"
"""只有形狀限制的特殊原語依 ``allowed_shapes`` 合併成一個型態，ID 是 ``on_<形狀>_<形狀>…``。"""
_MAX_EFFECTS = 4
SELF_STATUS_PRIMITIVES: tuple[str, ...] = ("apply_status",)
"""雖然是有害原語（施加的狀態可能是減益），但對施放者自己使用有意義（施加增益）的原語。"""


@dataclass(frozen=True, slots=True)
class FormPlan:
    """一個型態（只有 ID，模型由 :mod:`trpg.skillgen.proposal` 依它產生）。

    - ``leads``：這個型態的特殊原語（一般型態為空）。
    - ``effects``：效果可用的原語（一般版本）；``self_effects``：只作用在施放者的版本
      （``others_affect: self`` 的型態用）。
    - ``kinds``：可選的技能種類；``max_effects``：效果數上限；``variants``：可否帶變奏。
    """

    id: str
    leads: tuple[str, ...]
    shapes: tuple[str, ...]
    effects: tuple[str, ...]
    self_effects: tuple[str, ...]
    kinds: tuple[str, ...]
    max_effects: int
    variants: bool


def _rules(library: ContentLibrary) -> dict[str, CompositionRule]:
    return {p.id: CompositionRule.of(p) for p in library.ruleset.primitives.primitives}


def is_special(rule: CompositionRule) -> bool:
    """原語有組合規則（形狀限制或牽涉其他效果的規則）→ 不在一般型態。"""
    return rule.allowed_shapes is not None or rule.cross_effect


def _self_ok(primitive: PrimitiveDef) -> bool:
    """「其他效果只作用在施放者」的型態可用的一般原語：能對施放者使用，而且對自己有意義——有益的
    原語，或施加狀態的原語（對自己施加增益狀態）。對自己造成傷害、推拉等有害原語不開放。"""
    if "self" in primitive.forbid_affects:
        return False
    return not primitive.harmful or primitive.id in SELF_STATUS_PRIMITIVES


def _shape_only(rule: CompositionRule) -> bool:
    return rule.allowed_shapes is not None and not rule.cross_effect


def form_id(rule: CompositionRule) -> str:
    """特殊原語所屬型態的 ID：牽涉其他效果的原語自成一個型態（ID 是原語 ID）；只有形狀限制的
    原語依 ``allowed_shapes`` 合併（``on_<形狀>…``）。"""
    if _shape_only(rule):
        assert rule.allowed_shapes is not None
        return SHAPE_FORM_PREFIX + "_".join(rule.allowed_shapes)
    return rule.primitive


def _form_shapes(leads: Sequence[str], rule: CompositionRule, shapes: Sequence[str]) -> list[str]:
    return [
        s
        for s in shapes
        if (rule.allowed_shapes is None or s in rule.allowed_shapes)
        and any(lead in SHAPE_REQUIRED_PRIMITIVES.get(s, (lead,)) for lead in leads)
    ]


def _companions(
    form: str,
    shapes: Sequence[str],
    special: Sequence[str],
    rules: Mapping[str, CompositionRule],
) -> list[str]:
    """可以放進型態 ``form`` 的其他特殊原語：只有形狀限制、而且允許型態的每個形狀。"""
    return [
        other
        for other in special
        if _shape_only(rules[other])
        and form_id(rules[other]) != form
        and set(shapes) <= set(rules[other].allowed_shapes or ())
    ]


def _groups(special: Sequence[str], rules: Mapping[str, CompositionRule]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for primitive in special:
        groups.setdefault(form_id(rules[primitive]), []).append(primitive)
    return groups


def plan_forms(
    library: ContentLibrary,
    *,
    primitives: Iterable[str],
    shapes: Iterable[str],
    kinds: Sequence[str],
) -> tuple[tuple[FormPlan, ...], tuple[tuple[str, str], ...]]:
    """依提議開放的原語、形狀與種類規劃型態。回傳（型態，排除的原語與中文原因）。

    ``primitives``、``shapes`` 依 YAML 順序處理（呼叫端給的順序不影響結果）。"""
    rules = _rules(library)
    wanted_p, wanted_s = set(primitives), set(shapes)
    ids = [p.id for p in library.ruleset.primitives.primitives if p.id in wanted_p]
    shape_ids = [s.id for s in library.ruleset.shapes.shapes if s.id in wanted_s]
    special = [i for i in ids if is_special(rules[i])]
    general = [i for i in ids if i not in special]
    defs = library.ruleset.primitives.by_id()
    forms: list[FormPlan] = []
    excluded: list[tuple[str, str]] = []
    std_shapes = tuple(s for s in shape_ids if s not in SHAPE_REQUIRED_PRIMITIVES)
    if general and std_shapes:
        forms.append(
            FormPlan(
                STANDARD_FORM, (), std_shapes, tuple(general), (), tuple(kinds), _MAX_EFFECTS, True
            )
        )
    for fid, leads in _groups(special, rules).items():
        rule = rules[leads[0]]  # 同一型態的原語 allowed_shapes 相同
        form_shapes = _form_shapes(leads, rule, shape_ids)
        active_only = all(rules[i].active_only for i in leads)
        form_kinds = tuple(k for k in kinds if k == "active" or not active_only)
        reason = "沒有它能用的形狀" if not form_shapes else None
        if reason is None and not form_kinds:
            reason = "只能用在主動技能"
        if reason is not None:
            excluded += [(i, reason) for i in leads]
            continue
        forms.append(
            _special_plan(
                fid,
                leads,
                shapes=form_shapes,
                kinds=form_kinds,
                general=general,
                selfish=[i for i in general if _self_ok(defs[i])],
                special=special,
                rules=rules,
            )
        )
    return tuple(forms), tuple(excluded)


def _special_plan(
    fid: str,
    leads: Sequence[str],
    *,
    shapes: Sequence[str],
    kinds: Sequence[str],
    general: Sequence[str],
    selfish: Sequence[str],
    special: Sequence[str],
    rules: Mapping[str, CompositionRule],
) -> FormPlan:
    rule = rules[leads[0]]
    effects: list[str] = list(leads)
    self_effects: list[str] = []
    if rule.others_affect == "self":
        self_effects = list(selfish)
    elif not rule.sole_effect:
        effects += [*general, *_companions(fid, shapes, special, rules)]
    return FormPlan(
        id=fid,
        leads=tuple(leads),
        shapes=tuple(shapes),
        effects=tuple(effects),
        self_effects=tuple(self_effects),
        kinds=tuple(kinds),
        max_effects=1 if rule.sole_effect else _MAX_EFFECTS,
        variants=False,
    )


def form_hint(library: ContentLibrary, plan: FormPlan) -> str:
    """型態的一句中文說明（schema 的 ``description`` 與 prompt 的 ``available.forms`` 共用）。"""
    if plan.id == STANDARD_FORM:
        return "一般技能：效果只用沒有特殊組合限制的原語，可以帶變奏。"
    defs = library.ruleset.primitives.by_id()
    rules = [CompositionRule.of(defs[i]) for i in plan.leads]
    rule = rules[0]
    parts = [f"形狀只能是 {'、'.join(plan.shapes)}"]
    if rule.sole_effect:
        parts.append("它必須是唯一的效果")
    if rule.position == "first":
        parts.append("它必須是第一個效果")
    if rule.position == "last":
        parts.append("它必須是最後一個效果")
    limited = [r.primitive for r in rules if r.max_per_skill == 1 and not r.sole_effect]
    if limited:
        parts.append(f"{'、'.join(limited)} 每個技能最多一個")
    if rule.others_affect == "self":
        parts.append("其他效果只作用在施放者（affects: self）")
    if all(r.active_only for r in rules):
        parts.append("只能是主動技能")
    parts.append("不能帶變奏")
    names = "、".join(f"{defs[i].name_zh}（{i}）" for i in plan.leads)
    return f"以{names}為主的技能：{'；'.join(parts)}。"


def form_of_effects(library: ContentLibrary, effect_types: Sequence[str]) -> str:
    """一組頂層效果類型屬於哪個型態（手寫技能 → 提議時用）：沒有特殊原語是一般型態；否則取第一個
    能容納其餘特殊原語的型態（都不行時取第一個，交給驗證回報錯誤）。"""
    rules = _rules(library)
    special = [t for t in dict.fromkeys(effect_types) if t in rules and is_special(rules[t])]
    if not special:
        return STANDARD_FORM
    all_shapes = tuple(s.id for s in library.ruleset.shapes.shapes)
    for primitive in special:
        rule = rules[primitive]
        fid = form_id(rule)
        others = [t for t in special if form_id(rules[t]) != fid]
        companions = _companions(fid, rule.allowed_shapes or all_shapes, special, rules)
        if not others or (
            not rule.sole_effect
            and rule.others_affect is None
            and all(t in companions for t in others)
        ):
            return fid
    return form_id(rules[special[0]])


def skill_form(library: ContentLibrary, skill: SkillDef) -> str:
    """手寫技能的型態（:func:`form_of_effects` 的便利包裝）。"""
    return form_of_effects(library, [e.type for e in skill.effects])
