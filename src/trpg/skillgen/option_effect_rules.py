"""工坊的「效果參數事前停用」（Phase 3-48h，使用者：「是按得出來但是不允許」）。

驗證器會擋的，工坊在選的當下就標出來：效果的 **對象**（``affects``）與 **狀態**（``status``）選項，
若選了會讓驗證器報 :data:`~trpg.skillgen.validate.EFFECT_PARAM_RULES` 的規則，選項就附上
``info.unavailable_zh``（一句白話原因，能靠改別的欄位解決的會說明怎麼改）。

判斷與驗證器 **同源**：不另寫規則，而是把候選效果放進草稿，直接呼叫
:func:`~trpg.skillgen.validate.effect_param_violations`（它呼叫的是 :func:`validate_skill` 用的同
一批規則函式）。原因文字只負責把違規訊息換成白話與「怎麼改」。

歸屬方式（候選效果 ``c``、草稿已有的效果 ``context``）：

- 單一效果規則（骨架禁止的對象、自身形狀不打敵人、暈眩的形狀與冷卻……）：``c`` 單獨放進草稿的技能
  就違規 → 擋。
- 成對規則（同類控制不重複、傷害與友方治療不並存、姿態狀態）：``context + c`` 的違規次數比
  ``context`` 多 → 擋。

代價步驟還沒填冷卻時，假設之後會給足夠的冷卻（冷卻在後面的步驟選，而且代價步驟會標出下限）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import PrimitiveDef, SkillCost, SkillDef, default_affects
from trpg.skillgen.draft import Draft, DraftError, build_skill
from trpg.skillgen.option_fill import variants
from trpg.skillgen.option_models import Choice, EffectFix, FieldSpec
from trpg.skillgen.option_params import model_range
from trpg.skillgen.validate import Violation, effect_param_violations

__all__ = [
    "EffectProbe",
    "cooldown_requirement",
    "effect_fixes",
    "sensible_affects",
    "with_param_blocks",
]

PAIR_RULES: frozenset[str] = frozenset(
    {
        "exclusion.no_repeated_control_group",
        "exclusion.no_damage_with_ally_heal",
        "stance.status",
    }
)
"""要兩個以上的效果才會違規的規則（歸屬看違規次數有沒有增加）；其餘都是單一效果規則。"""
_SIDE_ZH = {"enemies": "敵方", "allies": "友方", "all": "敵我雙方", "self": "自己"}
_STEP_ZH = {"shape": "形狀", "cost": "代價", "skeleton": "骨架", "basics": "基本設定"}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _assumed_cooldown() -> int:
    return model_range(SkillCost.model_fields["cooldown"])[1] or 9


class EffectProbe:
    """一份草稿的探測器：把候選效果放進草稿，問驗證器「這個效果會違反哪些規則」。"""

    def __init__(self, draft: Draft, library: ContentLibrary) -> None:
        self.draft = draft
        self.library = library
        self._cache: dict[str, list[Violation]] = {}

    def _skill(self, effects: Sequence[Mapping[str, Any]]) -> SkillDef | None:
        draft = {k: v for k, v in self.draft.items() if k != "followup"}
        overrides: dict[str, Any] = {"effects": [dict(e) for e in effects]}
        if draft.get("rarity") is None:
            overrides["rarity"] = "epic"
        cost = dict(_mapping(draft.get("cost")))
        if "cooldown" not in cost:  # 冷卻在後面的「代價」步驟才選：假設之後會給足夠的冷卻
            overrides["cost"] = {**cost, "cooldown": _assumed_cooldown()}
        if any(e.get("type") == "place_trap" for e in effects) and draft.get("trap") is None:
            overrides["trap"] = {"trigger": "enter"}
        try:
            return build_skill(draft, overrides)
        except DraftError:
            return None

    def violations(self, effects: Sequence[Mapping[str, Any]]) -> list[Violation]:
        key = repr(effects)
        if key not in self._cache:
            skill = self._skill(effects)
            self._cache[key] = [] if skill is None else effect_param_violations(skill, self.library)
        return self._cache[key]

    def skill(self, effects: Sequence[Mapping[str, Any]]) -> SkillDef | None:
        return self._skill(effects)

    def blocked(
        self, candidate: Mapping[str, Any], context: Sequence[Mapping[str, Any]]
    ) -> list[Violation]:
        """``candidate`` 放進 ``context`` 之後，歸屬於它的違規（空串列＝可以選）。"""
        alone = [v for v in self.violations([candidate]) if v.rule not in PAIR_RULES]
        after = [v for v in self.violations([*context, candidate]) if v.rule in PAIR_RULES]
        before = Counter(v.rule for v in self.violations(context) if v.rule in PAIR_RULES)
        seen: Counter[str] = Counter()
        added: list[Violation] = []
        for violation in after:
            seen[violation.rule] += 1
            if seen[violation.rule] > before[violation.rule]:
                added.append(violation)
        return [*alone, *added]

    def why(self, candidate: Mapping[str, Any], context: Sequence[Mapping[str, Any]]) -> str | None:
        """``candidate`` 不能選的白話原因（含怎麼改）；可以選時為 ``None``。"""
        found = self.blocked(candidate, context)
        if not found:
            return None
        skill = self._skill([*context, candidate]) or self._skill([candidate])
        if skill is None:
            return found[0].message
        return explain(found[0], skill, candidate, self.library)


_FIXED_REASON: dict[str, str] = {
    "exclusion.self_shape_no_enemy_effect": (
        "自身形狀不能對敵方出手：把對象改成自己或友方，或回到「形狀」步驟換成別的形狀"
    ),
    "exclusion.no_damage_with_ally_heal": (
        "同一招不能同時有對敵人的傷害和對友方的治療：改選別的對象，或先移除另一邊的效果"
    ),
    "passive.affects": "這個被動作用在持有者自己，效果的對象只能是自己",
    "stance.misuse": "姿態狀態只能由姿態技能施加：回到「基本設定」把種類改成姿態，或改選別的狀態",
    "stance.status": "姿態技能施加的狀態必須是姿態狀態：改選姿態狀態",
    "stance.duration": "姿態狀態會一直持續到取消，不能設定持續回合",
    "on_kill.beneficial": "擊殺時的效果作用在你自己身上，只能施加有益的狀態",
}


def explain(
    violation: Violation, skill: SkillDef, effect: Mapping[str, Any], library: ContentLibrary
) -> str:
    """違規 → 白話原因；能改別的欄位解決的，說明回到哪一步改什麼。"""
    rule = violation.rule
    if rule in _FIXED_REASON:
        return _FIXED_REASON[rule]
    status = library.ruleset.statuses.by_id().get(str(effect.get("status")))
    name = status.name_zh if status is not None else str(effect.get("type"))
    skeleton = library.skeletons[skill.skeleton]
    if rule == "exclusion.stun_single_long_cooldown":
        return _stun_reason(name, skill, library)
    if rule == "exclusion.no_repeated_control_group":
        return f"已經有同類型的控制效果，同一招不能再放「{name}」：先移除那個效果"
    if rule == "skeleton.forbidden_affects":
        sides = "、".join(_SIDE_ZH.get(s, s) for s in skeleton.forbid_affects)
        return (
            f"「{skeleton.name_zh}」骨架不能有對{sides}的效果：改選自己或友方，"
            "或回到「骨架」步驟換一個骨架"
        )
    if rule == "skeleton.core_beneficial":
        return f"「{skeleton.name_zh}」骨架的核心效果只能是有益的狀態：改選有益的狀態"
    return violation.message


def _stun_reason(name: str, skill: SkillDef, library: ContentLibrary) -> str:
    rule = next(r for r in library.exclusions.rules if r.id == "stun_single_long_cooldown")
    need = rule.require.min_cooldown if rule.require is not None else None
    fixes: list[str] = []
    if skill.shape.type != "single":
        fixes.append("回到「形狀」步驟改成單體")
    if need is not None and (skill.cost.cooldown or 0) < need:
        fixes.append(f"到「代價」步驟把冷卻設成 {need} 回合以上")
    how = "、".join(fixes) if fixes else "調整形狀與冷卻"
    limit = f"形狀只能是單體、冷卻至少 {need} 回合" if need is not None else "有形狀與冷卻的限制"
    return f"「{name}」是硬控，{limit}：{how}"


# ---------------------------------------------------------------------------
# 選項停用
# ---------------------------------------------------------------------------


def sensible_affects(
    primitive: PrimitiveDef, shape: str, *, beneficial: bool | None = None
) -> tuple[str, ...]:
    """這個效果「合理」的對象，依偏好排序（對象預設與自動修正都從這裡挑）：有害的打敵方；有益的
    給自己或友方（自身形狀優先自己）。``beneficial`` 是狀態的有益／有害（只有施加狀態的原語）。"""
    if primitive.acts_on == "tile":
        return ("tiles",)
    if primitive.acts_on == "caster":
        return ("self",)
    harmful = primitive.harmful if beneficial is None else not beneficial
    if harmful:
        return ("enemies", "all")
    return ("self", "allies") if shape == "self" else ("allies", "self")


def _fill(choice: Choice) -> dict[str, Any] | None:
    fills = variants(choice)
    return fills[0] if fills else None


def _param(choice: Choice, name: str) -> FieldSpec | None:
    return next((p for p in choice.params if p.field == name and p.type == "choice"), None)


def _with_info(item: Choice, reason: str | None) -> Choice:
    if reason is None:
        return item
    return item.model_copy(update={"info": {**item.info, "unavailable_zh": reason}})


def _shape_type(draft: Draft) -> str:
    return str(_mapping(draft.get("shape")).get("type"))


def with_param_blocks(
    choices: list[Choice], draft: Draft, library: ContentLibrary, skeleton: SkeletonDef
) -> list[Choice]:
    """每個原語選項的 ``affects``、``status`` 子選項，會讓驗證器報錯的標上 ``unavailable_zh``；
    對象的預設值改成合法的偏好值；所有合理對象都被擋的原語整個標示不可用。"""
    del skeleton  # 規則由驗證器依骨架判斷
    probe = EffectProbe(draft, library)
    context = [dict(_mapping(e)) for e in draft.get("effects") or ()]
    by_id = library.ruleset.primitives.by_id()
    shape = _shape_type(draft)
    out: list[Choice] = []
    for choice in choices:
        primitive = by_id.get(str(choice.value))
        base = _fill(choice)
        if primitive is None or base is None:
            out.append(choice)
            continue
        out.append(
            _checked_choice(choice, primitive, base=base, probe=probe, context=context, shape=shape)
        )
    return out


def _checked_choice(
    choice: Choice,
    primitive: PrimitiveDef,
    *,
    base: dict[str, Any],
    probe: EffectProbe,
    context: list[dict[str, Any]],
    shape: str,
) -> Choice:
    affects = _param(choice, "affects")
    status = _param(choice, "status")
    params = list(choice.params)
    reasons: dict[str, str] = {}
    marked_affects: FieldSpec | None = None
    if affects is not None:
        marked, reasons = _mark_choices(affects, "affects", base, probe, context)
        marked_affects = _legal_default(marked, primitive, shape)
        params[params.index(affects)] = marked_affects
    if status is not None:
        params[params.index(status)] = _mark_statuses(
            status, marked_affects, primitive, base=base, probe=probe, context=context, shape=shape
        )
    updated = choice.model_copy(update={"params": tuple(params)})
    if marked_affects is None or status is not None or "unavailable_zh" in choice.info:
        return updated
    legal = {str(c.value) for c in marked_affects.choices if c.info.get("unavailable_zh") is None}
    sensible = sensible_affects(primitive, shape)
    if any(side in legal for side in sensible):
        return updated
    # 合理的對象全被擋（例：光環骨架或自身形狀的傷害，敵方出不去）：整個原語事前停用
    reason = probe.why({**base, "affects": sensible[0]}, context) or next(
        iter(reasons.values()), None
    )
    return _with_info(updated, reason or "目前沒有合適的對象可以選")


def _mark_choices(
    spec: FieldSpec,
    field: str,
    base: dict[str, Any],
    probe: EffectProbe,
    context: list[dict[str, Any]],
) -> tuple[FieldSpec, dict[str, str]]:
    marked: list[Choice] = []
    reasons: dict[str, str] = {}
    for item in spec.choices:
        reason = probe.why({**base, field: item.value}, context)
        if reason is not None:
            reasons[str(item.value)] = reason
        marked.append(_with_info(item, reason))
    return spec.model_copy(update={"choices": tuple(marked)}), reasons


def _legal_default(spec: FieldSpec, primitive: PrimitiveDef, shape: str) -> FieldSpec:
    """對象欄位的預設值改成「合理且合法」的第一個；省略對象時引擎用的預設值（``default_affects``）
    若不合法，這個欄位改為必填（玩家必須明確選）。"""
    legal = {str(c.value) for c in spec.choices if c.info.get("unavailable_zh") is None}
    required = spec.required or default_affects(primitive) not in legal
    for value in sensible_affects(primitive, shape):
        if value in legal:
            return spec.model_copy(update={"default": value, "required": required})
    return spec.model_copy(update={"required": required})


def _mark_statuses(
    spec: FieldSpec,
    affects: FieldSpec | None,
    primitive: PrimitiveDef,
    *,
    base: dict[str, Any],
    probe: EffectProbe,
    context: list[dict[str, Any]],
    shape: str,
) -> FieldSpec:
    marked: list[Choice] = []
    for item in spec.choices:
        beneficial = bool(item.info.get("beneficial"))
        candidate = {**base, "status": item.value}
        if affects is not None:
            side = _pick_side(affects, primitive, shape, beneficial)
            if side is not None:
                candidate["affects"] = side
        marked.append(_with_info(item, probe.why(candidate, context)))
    return spec.model_copy(update={"choices": tuple(marked)})


def _pick_side(
    affects: FieldSpec, primitive: PrimitiveDef, shape: str, beneficial: bool
) -> str | None:
    legal = {str(c.value) for c in affects.choices if c.info.get("unavailable_zh") is None}
    for value in sensible_affects(primitive, shape, beneficial=beneficial):
        if value in legal:
            return value
    return None


# ---------------------------------------------------------------------------
# 已加入的效果：對象不合法時的自動修正建議
# ---------------------------------------------------------------------------


def effect_fixes(
    draft: Draft, library: ContentLibrary, choices: Sequence[Choice]
) -> tuple[EffectFix, ...]:
    """草稿裡已有的效果，對象會讓驗證器報錯（例：光環骨架的效果還是預設的敵方）→ 建議改成合法的
    對象（前端照 ``conformScaling`` 的做法自動套用）。對象已合法時不建議；沒有合理的合法對象時
    ``value`` 為 ``None``（只附原因）。"""
    effects = [dict(_mapping(e)) for e in draft.get("effects") or ()]
    if not effects:
        return ()
    probe = EffectProbe(draft, library)
    by_id = library.ruleset.primitives.by_id()
    statuses = library.ruleset.statuses.by_id()
    shape = _shape_type(draft)
    out: list[EffectFix] = []
    for index, effect in enumerate(effects):
        stack_fix = _stack_fix(index, effect, library)
        if stack_fix is not None:  # 層數的對象由層數決定（3-52）
            out.extend(stack_fix)
            continue
        primitive = by_id.get(str(effect.get("type")))
        choice = next((c for c in choices if c.value == effect.get("type")), None)
        affects = None if choice is None else _param(choice, "affects")
        if primitive is None or affects is None or probe.skill([effect]) is None:
            continue
        context = effects[:index] + effects[index + 1 :]
        found = probe.why(effect, context)
        status = statuses.get(str(effect.get("status")))
        beneficial = None if status is None else status.beneficial
        wanted = _first_legal(
            affects,
            effect,
            primitive,
            probe=probe,
            context=context,
            shape=shape,
            beneficial=beneficial,
        )
        if effect.get("affects") is None and wanted is not None and status is not None:
            # 還沒選對象：施加狀態時預設依狀態的有益／有害（有益 → 友方／自己，有害 → 敵方）
            current = effect.get("affects") or sensible_affects(primitive, shape)[0]
            if wanted != current or found:
                out.append(EffectFix(index=index, value=wanted, reason_zh=found or ""))
            continue
        if found:
            out.append(EffectFix(index=index, value=wanted, reason_zh=found))
    return tuple(out)


def _stack_fix(
    index: int, effect: Mapping[str, Any], library: ContentLibrary
) -> list[EffectFix] | None:
    """累積／消耗層數的效果：對象由層數決定（累積在你身上 → 自己，疊在敵人身上 → 敵方；3-52）。
    不是層數效果回傳 ``None``（走一般流程）；對象已經對的回傳空串列。"""
    if effect.get("type") not in ("add_stack", "consume_stack"):
        return None
    stack = library.ruleset.stacks.by_id().get(str(effect.get("stack")))
    if stack is None:
        return []
    wanted = "self" if stack.owner == "self" else "enemies"
    if effect.get("affects") == wanted:
        return []
    where = "累積在你身上" if stack.owner == "self" else "疊在敵人身上"
    return [
        EffectFix(index=index, value=wanted, reason_zh=f"「{stack.name_zh}」{where}，對象自動決定")
    ]


def _first_legal(
    affects: FieldSpec,
    effect: dict[str, Any],
    primitive: PrimitiveDef,
    *,
    probe: EffectProbe,
    context: list[dict[str, Any]],
    shape: str,
    beneficial: bool | None,
) -> str | None:
    allowed = {str(c.value) for c in affects.choices}
    for value in sensible_affects(primitive, shape, beneficial=beneficial):
        if value in allowed and not probe.blocked({**effect, "affects": value}, context):
            return value
    return None


def cooldown_requirement(draft: Draft, library: ContentLibrary) -> tuple[int, str] | None:
    """已選的效果牽涉的冷卻下限：``(回合數, 原因)``（互斥規則的 ``require.min_cooldown``，例：暈眩
    與冰凍至少 4 回合）；沒有時回傳 ``None``。代價步驟用它標出冷卻欄位的下限。"""
    effects = [dict(_mapping(e)) for e in draft.get("effects") or ()]
    if not effects:
        return None
    probe = EffectProbe(draft, library)
    skill = probe.skill(effects)
    if skill is None:
        return None
    statuses = {str(e.get("status")) for e in effects if e.get("type") == "apply_status"}
    best: tuple[int, str] | None = None
    for rule in library.exclusions.rules:
        need = None if rule.require is None else rule.require.min_cooldown
        when = rule.when
        if need is None or when is None or when.statuses is None:
            continue
        if statuses & set(when.statuses) and (best is None or need > best[0]):
            names = "、".join(
                library.ruleset.statuses.by_id()[s].name_zh
                for s in sorted(statuses & set(when.statuses))
            )
            best = (need, f"{names}是硬控，冷卻至少 {need} 回合")
    return best
