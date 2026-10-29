"""跨檔案驗證：:func:`skill_problems` 與其輔助函式。"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from trpg.content.skills.conditions import ConditionSpec
from trpg.content.skills.constants import (
    ADD_STACK,
    CONSUME_STACK,
    CONSUME_STATUS,
    DAMAGE_MULTIPLIER,
    GAMBLE,
    GRANT_SKILL,
    INSCRIBE,
    REFUND_AP,
    REFUND_COOLDOWN,
    RULE_CHANGE,
    SELF_DAMAGE_OF_HIT,
    ZONE,
    rarity_rank,
)
from trpg.content.skills.effects import EffectSpec
from trpg.content.skills.primitives import (
    ConditionDef,
    PrimitiveDef,
    PrimitiveParam,
    default_affects,
)
from trpg.content.skills.queries import on_hit_carrier
from trpg.content.skills.shapes import ShapeDef
from trpg.content.skills.skill import SkillDef, _int_param_problems
from trpg.shared.types import Surface

if TYPE_CHECKING:
    from trpg.content.skill_triggers import SkillTriggerDef
    from trpg.content.stacks import StackDef


def _count_problem(where: str, primitive: PrimitiveDef, name: str, value: object) -> str | None:
    """``count`` 型參數（Phase 3D-8a）：``all`` 或 ``min``–``max`` 的整數。"""
    spec = primitive.params[name]
    if value == "all":
        return None
    low, high = spec.min or 1, spec.max
    if isinstance(value, int) and low <= value and (high is None or value <= high):
        return None
    return f"{where}.{name}：{primitive.id} 的 {name} 必須在 {low}–{high} 或 all，收到 {value!r}"


def _value_problem(
    where: str, primitive: PrimitiveDef, name: str, value: object, refs: _Refs
) -> str | None:
    """單一原語參數值的問題（範圍或引用不存在）。"""
    spec = primitive.params[name]
    if spec.type == "count":
        return _count_problem(where, primitive, name, value)
    if spec.type == "int":
        assert isinstance(value, int)
        below = spec.min is not None and value < spec.min
        above = spec.max is not None and value > spec.max
        if below or above:
            return (
                f"{where}.{name}：{primitive.id} 的 {name} "
                f"必須在 {spec.min}–{spec.max}，收到 {value}"
            )
    elif spec.type == "surface" and value is Surface.NONE:
        return f"{where}.{name}：不能產生 none 表面"
    else:
        return _reference_problem(where, name, spec.type, value, refs)
    return None


def _reference_problem(where: str, name: str, kind: str, value: object, refs: _Refs) -> str | None:
    """引用其他資料檔 ID 的參數（狀態、物件、層數、召喚物範本）是否存在。"""
    known: dict[str, tuple[Collection[object] | None, str]] = {
        "status": (refs.status_ids, "狀態"),
        "object": (refs.object_ids, "物件"),
        "stack": (refs.stacks, "層數"),
        "summon": (refs.summon_ids, "召喚物範本"),
        "summon_trait": (refs.summon_trait_ids, "召喚物小特性"),
        "infusion": (refs.infusion_ids, "灌注關鍵字"),
        "rule_change": (refs.rule_change_ids, "規則改變"),
        "form": (refs.form_ids, "形態"),
    }
    entry = known.get(kind)
    if entry is None or entry[0] is None or value in entry[0]:
        return None
    return f"{where}.{name}：未知的{entry[1]} {value!r}"


@dataclass(frozen=True, slots=True)
class _Refs:
    """跨檔案驗證用的引用表。"""

    primitives: dict[str, PrimitiveDef]
    status_ids: set[str]
    object_ids: set[str]
    conditions: dict[str, ConditionDef]
    stacks: dict[str, StackDef] | None = None
    summon_ids: set[str] | None = None
    rule_change_ids: set[str] | None = None
    unsafe_statuses: frozenset[str] | None = None
    """不能當反噬的狀態（硬控、跳過回合、持續傷害；Phase 3D-7a）；``None`` 不檢查。"""
    scale_cap_max: int | None = None
    """``scaling.cap_permille`` 的上限（``core.yaml`` 的 ``scale_cap_max_permille``；Phase 3D-7b）；
    ``None`` 不檢查。"""
    summon_trait_ids: set[str] | None = None
    """``summon`` 的 ``trait`` 可用的小特性 ID（Phase 3-33f2）；``None`` 不檢查。"""
    infusion_ids: set[str] | None = None
    """``summon`` 的 ``infusion`` 可用的灌注關鍵字 ID（Phase 3-33f2）；``None`` 不檢查。"""
    form_ids: set[str] | None = None
    """``enter_form`` 的 ``form`` 可用的形態 ID（Phase 3J-1a）；``None`` 不檢查。"""


def _condition_problems(where: str, condition: ConditionSpec, refs: _Refs) -> list[str]:
    """條件的類型存在、必要參數齊全、參數在範圍內、引用的狀態與表面存在。"""
    definition = refs.conditions.get(condition.type)
    if definition is None:
        known = ", ".join(sorted(refs.conditions))
        return [f"{where}.type：未知的條件 {condition.type!r}（可用：{known}）"]
    problems: list[str] = []
    values = condition.param_values()
    for name, value in values.items():
        spec = definition.params.get(name)
        if spec is None:
            problems.append(f"{where}.{name}：條件 {definition.id} 不接受參數 {name}")
        elif spec.type == "int":
            assert isinstance(value, int)
            if (spec.min is not None and value < spec.min) or (
                spec.max is not None and value > spec.max
            ):
                problems.append(
                    f"{where}.{name}：條件 {definition.id} 的 {name} "
                    f"必須在 {spec.min}–{spec.max}，收到 {value}"
                )
        elif spec.type == "status" and value not in refs.status_ids:
            problems.append(f"{where}.{name}：未知的狀態 {value!r}")
        elif spec.type == "surface" and value is Surface.NONE:
            problems.append(f"{where}.{name}：條件的表面不能是 none")
    for name, spec in definition.params.items():
        if spec.required and name not in values:
            problems.append(f"{where}.{name}：條件 {definition.id} 缺少必要參數 {name}")
    return problems


def _forbidden_affects_message(where: str, primitive_id: str, affects: str) -> str:
    if primitive_id == INSCRIBE:  # 刻印的對象只有影響的格子（玩法 PM 2026-10-24）
        return f"{where}.affects：刻印只能刻在影響的格子上，對象要選「格子」（tiles）"
    return f"{where}.affects：{primitive_id} 不能搭配 affects: {affects}"


def _effect_problems(
    skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs, *, on_hit: bool = False
) -> list[str]:
    where = f"effects[{index}]"
    primitive = refs.primitives.get(effect.type)
    if primitive is None:
        known = ", ".join(sorted(refs.primitives))
        return [f"{where}.type：未知的效果原語 {effect.type!r}（可用：{known}）"]
    problems: list[str] = []
    if effect.condition is not None:
        problems += _condition_problems(f"{where}.condition", effect.condition, refs)
    values = effect.param_values()
    for name, value in values.items():
        if name not in primitive.params:
            problems.append(f"{where}.{name}：效果 {primitive.id} 不接受參數 {name}")
        elif (problem := _value_problem(where, primitive, name, value, refs)) is not None:
            problems.append(problem)
    for name, spec in primitive.params.items():
        required = param_required_for(
            spec,
            category=skill.category,
            sibling_filled=lambda n: any(
                e.type == primitive.id and getattr(e, n, None) is not None for e in skill.effects
            ),
        )
        if required and name not in values:
            problems.append(f"{where}.{name}：效果 {primitive.id} 缺少必要參數 {name}")
    affects = effect.affects or default_affects(primitive)
    if primitive.acts_on == "caster" and affects != "self":
        problems.append(f"{where}.affects：{primitive.id} 只能對施放者（self），收到 {affects}")
    if primitive.acts_on != "tile" and affects == "tiles":
        problems.append(f"{where}.affects：{primitive.id} 是對單位的效果，不能用 tiles")
    if affects in primitive.forbid_affects:
        problems.append(_forbidden_affects_message(where, primitive.id, affects))
    if (
        primitive.allowed_shapes is not None
        and skill.shape.type not in primitive.allowed_shapes
        and not on_hit  # 命中後效果只作用在目標那 1 格，不看載體技能的形狀
    ):
        allowed = "、".join(primitive.allowed_shapes)
        problems.append(f"{where}：{primitive.id} 只能搭配形狀 {allowed}，收到 {skill.shape.type}")
    problems += _stack_effect_problems(skill, where, effect, affects, refs)
    problems += _consume_status_problems(skill, index, effect, refs)
    problems += _zone_problems(skill, index, effect, refs)
    problems += _gamble_problems(skill, index, effect, refs)
    problems += _on_kill_problems(skill, index, effect, refs)
    problems += _scaling_problems(where, effect, refs)
    return problems


def _on_kill_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``on_kill`` 的跨檔案檢查（Phase 3D-8b）：一般原語（治療、護盾、施加狀態）當成同一技能的
    效果檢查（參數、引用）；``refund_ap``、``refund_cooldown`` 不是原語，已由 schema 檢查。"""
    problems: list[str] = []
    for i, sub in enumerate(effect.on_kill or ()):
        if sub.type in (REFUND_AP, REFUND_COOLDOWN):
            continue
        prefix = "effects[0]"
        carrier = skill.model_copy(update={"effects": (sub,)})
        problems += [
            f"effects[{index}].on_kill[{i}]{p.removeprefix(prefix)}"
            for p in _effect_problems(carrier, 0, sub, refs)
        ]
    return problems


def _scaling_problems(where: str, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``scaling.cap_permille`` 不超過 ``core.scale_cap_max_permille``（Phase 3D-7b）。"""
    scaling = effect.scaling
    if scaling is None or refs.scale_cap_max is None or scaling.cap_permille <= refs.scale_cap_max:
        return []
    return [
        f"{where}.scaling.cap_permille：{scaling.cap_permille} 超過上限 {refs.scale_cap_max}"
        "（core.yaml 的 scale_cap_max_permille）"
    ]


def _branch_problems(
    where: str, skill: SkillDef, branch: tuple[EffectSpec, ...], refs: _Refs, *, backlash: bool
) -> list[str]:
    """賭注分支或失手反噬的跨檔案檢查（Phase 3D-7a）：真正的原語（傷害、治療、護盾、施加狀態）
    當成同一技能的效果檢查；對施放者自己的狀態不能是硬控、跳過回合或持續傷害（反噬不致命、不讓
    施放者跳過回合）；對敵方的效果需要技能本身有對敵方的效果（才有命中判定）。"""
    problems: list[str] = []
    carrier = skill.model_copy(update={"effects": branch})
    hostile = any(
        (e.affects or _default_affects_of(refs, e)) in ("enemies", "all")
        for e in skill.effects
        if e.type != GAMBLE
    )
    for i, sub in enumerate(branch):
        if sub.type in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
            continue
        prefix = f"effects[{i}]"
        problems += [
            f"{where}[{i}]{p.removeprefix(prefix)}" for p in _effect_problems(carrier, i, sub, refs)
        ]
        affects = "self" if backlash else sub.affects or _default_affects_of(refs, sub)
        unsafe = refs.unsafe_statuses or frozenset()
        if affects == "self" and sub.type == "apply_status" and sub.status in unsafe:
            problems.append(
                f"{where}[{i}].status：反噬不能使用硬控、跳過回合或持續傷害的狀態（{sub.status}）"
            )
        if affects in ("enemies", "all") and not hostile and not backlash:
            problems.append(f"{where}[{i}].affects：技能沒有對敵方的效果，沒有命中判定可以依據")
    return problems


def _default_affects_of(refs: _Refs, effect: EffectSpec) -> str:
    primitive = refs.primitives.get(effect.type)
    return "enemies" if primitive is None else default_affects(primitive)


def _gamble_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``gamble`` 的跨檔案檢查（Phase 3D-7a）：``win``／``lose`` 的效果。"""
    if effect.type != GAMBLE:
        return []
    problems: list[str] = []
    for name in ("win", "lose"):
        branch = getattr(effect, name) or ()
        problems += _branch_problems(
            f"effects[{index}].{name}", skill, branch, refs, backlash=False
        )
    return problems


def _zone_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``zone`` 的跨檔案檢查（Phase 3D-5）：``effects`` 當成同一技能的效果檢查（原語、參數、
    引用）。"""
    if effect.type != ZONE:
        return []
    problems: list[str] = []
    subs = effect.effects or ()
    carrier = skill.model_copy(update={"effects": subs})
    for sub_index, sub in enumerate(subs):
        problems += [
            f"effects[{index}].effects{p.removeprefix('effects')}"
            for p in _effect_problems(carrier, sub_index, sub, refs)
        ]
    return problems


def _consume_status_problems(
    skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs
) -> list[str]:
    """``consume_status`` 的跨檔案檢查：``then`` 的效果當成同一技能的效果檢查（原語、參數、引用），
    ``scale: stacks`` 的層數必須存在且是目標型。"""
    if effect.type != CONSUME_STATUS:
        return []
    problems: list[str] = []
    carrier = skill.model_copy(update={"effects": effect.then or ()})
    for sub_index, sub in enumerate(effect.then or ()):
        problems += [
            f"effects[{index}].then{p.removeprefix('effects')}"
            for p in _effect_problems(carrier, sub_index, sub, refs)
        ]
    if effect.scale == "stacks" and refs.stacks is not None and effect.stack is not None:
        stack = refs.stacks.get(effect.stack)
        if stack is None:
            problems.append(f"effects[{index}].stack：未知的層數 {effect.stack!r}")
        elif stack.owner != "target":
            problems.append(
                f"effects[{index}].stack：scale: stacks 需要目標型層數（owner: target）"
            )
    return problems


def _consumer_problems(skill: SkillDef, where: str, stack: StackDef) -> list[str]:
    """``consume_stack`` 的消耗規則（Phase 3-52，``stacks.yaml`` 的 ``consumer``）：技能要有被加成
    的效果（傷害、治療、護盾），並滿足 ``requires_any`` 的其中一項。"""
    consumer = stack.consumer
    if consumer is None:
        return []
    problems: list[str] = []
    no_boost, unmet = consumer.gaps(skill)
    if no_boost:
        problems.append(
            f"{where}.stack：消耗層數 {stack.id} 的技能至少要有{consumer.boost_names()}其中一種效果"
        )
    if unmet:
        problems.append(f"{where}.stack：層數 {stack.id} 只有符合條件的技能可以消耗（見層數說明）")
    return problems


def _stack_effect_problems(
    skill: SkillDef, where: str, effect: EffectSpec, affects: str, refs: _Refs
) -> list[str]:
    """層數原語的跨檔案檢查：層數的 ``owner`` 決定對象（``self`` 型只能對施放者自己、``target`` 型
    只能對敵方），累積量不超過上限；消耗還要符合層數的消耗規則。"""
    if effect.type not in (ADD_STACK, CONSUME_STACK) or refs.stacks is None:
        return []
    stack = refs.stacks.get(effect.stack or "")
    if stack is None:
        return []
    want = "self" if stack.owner == "self" else "enemies"
    problems: list[str] = []
    if affects != want:
        problems.append(
            f"{where}.affects：層數 {stack.id}（owner: {stack.owner}）的{effect.type}"
            f"只能是 affects: {want}，收到 {affects}"
        )
    if effect.type == ADD_STACK and effect.amount is not None and effect.amount > stack.max:
        problems.append(f"{where}.amount：超過層數 {stack.id} 的上限 {stack.max}")
    if effect.type == CONSUME_STACK:
        problems += _consumer_problems(skill, where, stack)
    return problems


def _cost_stack_problems(skill: SkillDef, stacks: dict[str, StackDef]) -> list[str]:
    """``cost.stacks``（施放前至少要有幾層）：對應 ``owner: self`` 的 ``consume_stack``。"""
    need = skill.cost.stacks
    if need is None:
        return []
    owned = [
        stacks[e.stack]
        for e in skill.effects
        if e.type == CONSUME_STACK and e.stack in stacks and stacks[e.stack].owner == "self"
    ]
    if not owned:
        return ["cost.stacks：需要一個 owner: self 的層數的 consume_stack 效果"]
    if need > owned[0].max:
        return [f"cost.stacks：{need} 超過層數 {owned[0].id} 的上限 {owned[0].max}"]
    return []


def param_required_for(
    spec: PrimitiveParam, *, category: str, sibling_filled: Callable[[str], bool]
) -> bool:
    """這個參數在這個技能裡是否必填：``required``，且 ``required_when`` 成立（沒有則一律必填）。
    ``sibling_filled(name)``：技能內同類型的效果是否有任何一個填了參數 ``name``。"""
    if not spec.required:
        return False
    if spec.required_when is None:
        return True
    return spec.required_when.applies(category=category, sibling_filled=sibling_filled)


def _trigger_problems(
    skill: SkillDef, triggers: dict[str, SkillTriggerDef], status_ids: set[str]
) -> list[str]:
    """被動技能的觸發設定：時機存在、``target: other`` 只用在有另一方的時機、``status`` 存在。"""
    spec = skill.trigger
    if spec is None:
        return []
    definition = triggers.get(spec.event)
    if definition is None:
        known = ", ".join(sorted(triggers))
        return [f"trigger.event：未知的觸發時機 {spec.event!r}（可用：{known}）"]
    if spec.target == "other" and not definition.has_other:
        return [
            f"trigger.target：觸發時機 {definition.id}（{definition.name_zh}）沒有另一方，"
            "target 只能是 self"
        ]
    if spec.status is not None and spec.status not in status_ids:
        return [f"trigger.status：未知的狀態 {spec.status!r}"]
    return []


def granted_skill_problems(
    skill: SkillDef, skills: Mapping[str, SkillDef], primitives: Mapping[str, PrimitiveDef]
) -> list[str]:
    """``grant_skill`` 的跨技能檢查（Phase 3D-8c，6.20）：被給的技能必須存在，而且是一般的主動技能
    ——不是傳說、不含改寫規則型與規則改變型原語、不是 ``grant_skill`` 技能（不連鎖）、也不是技能
    自己（空串列為通過）。"""
    problems: list[str] = []
    for index, effect in enumerate(skill.effects):
        if effect.type != GRANT_SKILL or effect.skill is None:
            continue
        where = f"effects[{index}].skill"
        granted = skills.get(effect.skill)
        if granted is None:
            problems.append(f"{where}：未知的技能 {effect.skill!r}")
            continue
        reasons: list[str] = []
        if granted.id == skill.id:
            reasons.append("不能給出自己")
        if granted.kind != "active":
            reasons.append(f"必須是主動技能（kind: {granted.kind}）")
        if granted.rarity == "legendary":
            reasons.append("不能是傳說技能")
        rewrite = sorted(
            {
                e.type
                for e in granted.effects
                if (p := primitives.get(e.type)) is not None
                and p.category in ("rule_rewrite", "rule_change")
            }
        )
        if rewrite:
            reasons.append(f"不能含改寫規則型原語（{'、'.join(rewrite)}）")
        if any(e.type == GRANT_SKILL for e in granted.effects):
            reasons.append("不能是 grant_skill 技能")
        if reasons:
            problems.append(f"{where}：被給的技能 {granted.id} " + "；".join(reasons))
    return problems


def skill_problems(
    skill: SkillDef,
    shapes: dict[str, ShapeDef],
    primitives: dict[str, PrimitiveDef],
    *,
    status_ids: set[str],
    object_ids: set[str],
    conditions: dict[str, ConditionDef],
    triggers: dict[str, SkillTriggerDef] | None = None,
    stacks: dict[str, StackDef] | None = None,
    dual_min_rarity: str | None = None,
    summon_ids: set[str] | None = None,
    rule_change_ids: set[str] | None = None,
    unsafe_statuses: frozenset[str] | None = None,
    scale_cap_max: int | None = None,
    summon_trait_ids: set[str] | None = None,
    infusion_ids: set[str] | None = None,
    form_ids: set[str] | None = None,
) -> list[str]:
    """技能引用的形狀、原語、條件、狀態、物件是否存在、參數是否在範圍內（繁體中文，空串列為通過）。

    ``summon_trait_ids``／``infusion_ids``（Phase 3-33f2）：``summon`` 的 ``trait``、``infusion``
    可用的 ID（省略時不檢查）。

    ``triggers``：觸發時機表（省略時不檢查被動的 ``trigger``）；``stacks``：層數表（省略時不檢查
    層數原語引用的層數）；``dual_min_rarity``：雙屬性縮放的最低稀有度（省略時不檢查）；
    ``summon_ids``：召喚物範本 ID（省略時不檢查 ``summon`` 的 ``unit``）；``rule_change_ids``：
    規則改變 ID（Phase 3D-6，省略時不檢查 ``rule_change`` 的 ``rule``）；``unsafe_statuses``：
    不能當反噬的狀態 ID（Phase 3D-7a，省略時不檢查）；``scale_cap_max``：``scaling`` 的
    ``cap_permille`` 上限（Phase 3D-7b，省略時不檢查）。
    """
    problems: list[str] = []
    if (
        dual_min_rarity is not None
        and skill.secondary_scaling_attr is not None
        and rarity_rank(skill.rarity) < rarity_rank(dual_min_rarity)
    ):
        problems.append(
            f"secondary_scaling_attr：雙屬性縮放最低稀有度為 {dual_min_rarity}，收到 {skill.rarity}"
        )
    shape = shapes.get(skill.shape.type)
    if shape is None:
        known = ", ".join(sorted(shapes))
        problems.append(f"shape.type：未知的形狀 {skill.shape.type!r}（可用：{known}）")
    else:
        problems += _int_param_problems("shape", skill.shape.param_values(), shape)
    if skill.trap is not None and skill.trap.shape not in shapes:
        known = ", ".join(sorted(shapes))
        problems.append(f"trap.shape：未知的形狀 {skill.trap.shape!r}（可用：{known}）")
    refs = _Refs(
        primitives,
        status_ids,
        object_ids,
        conditions,
        stacks,
        summon_ids,
        rule_change_ids,
        unsafe_statuses,
        scale_cap_max,
        summon_trait_ids,
        infusion_ids,
        form_ids,
    )
    if stacks is not None:
        problems += _cost_stack_problems(skill, stacks)
    self_status = skill.cost.self_status
    if self_status is not None and self_status.status not in status_ids:
        problems.append(f"cost.self_status：未知的狀態 {self_status.status!r}")
    if triggers is not None:
        problems += _trigger_problems(skill, triggers, status_ids)
    if skill.condition is not None:
        problems += _condition_problems("condition", skill.condition, refs)
    for index, effect in enumerate(skill.effects):
        problems += _effect_problems(skill, index, effect, refs)
    problems += _branch_problems("cost.on_miss", skill, skill.cost.on_miss, refs, backlash=True)
    problems += _modifier_problems(skill, refs)
    problems += _legendary_problems(skill, primitives)
    return problems


def legendary_cores(skill: SkillDef, primitives: dict[str, PrimitiveDef]) -> list[str]:
    """傳說的核心（Phase 3D-6，6.14.4 三擇一）：每個改寫規則型原語、修正規則（整組算一個）、
    每個規則改變各算一個，依出現順序回傳種類（``rule_rewrite``／``modifier``／``rule_change``）。"""
    cores = [
        "rule_rewrite"
        for e in skill.effects
        if e.type in primitives and primitives[e.type].category == "rule_rewrite"
    ]
    if skill.modifiers:
        cores.append("modifier")
    cores += ["rule_change" for e in skill.effects if e.type == RULE_CHANGE]
    return cores


def _legendary_problems(skill: SkillDef, primitives: dict[str, PrimitiveDef]) -> list[str]:
    """傳說技能（Phase 3C-4a、3D-6，6.14.4）＝ 恰好 1 個核心（改寫規則型原語、修正規則、規則改變
    三擇一）＋ 源力代價。"""
    if skill.rarity != "legendary":
        return []
    cores = legendary_cores(skill, primitives)
    if len(cores) == 1:
        return []
    found = "、".join(cores) if cores else "沒有"
    return [
        "rarity：傳說技能必須恰好有 1 個核心（改寫規則型原語、修正規則 modifiers、規則改變 "
        f"rule_change 三擇一），收到 {found}"
    ]


def _modifier_problems(skill: SkillDef, refs: _Refs) -> list[str]:
    """修正規則的跨檔案檢查：條件存在且參數合法、命中後效果的原語與引用（當成以 ``self`` 形狀
    施放的效果檢查）。"""
    problems: list[str] = []
    for rule_index, rule in enumerate(skill.modifiers):
        where = f"modifiers[{rule_index}]"
        if rule.condition is not None:
            problems += _condition_problems(f"{where}.condition", rule.condition, refs)
        effects = rule.change.on_hit_effects
        if not effects:
            continue
        carrier = on_hit_carrier(skill, effects)
        for index, effect in enumerate(effects):
            problems += [
                f"{where}.change.on_hit_{p}"
                for p in _effect_problems(carrier, index, effect, refs, on_hit=True)
            ]
    return problems
