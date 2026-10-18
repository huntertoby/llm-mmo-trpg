"""技能驗證器（``docs/phases/Phase2B計畫.md`` 4.1–4.6）。

:func:`validate_skill` 依序檢查，回傳 **全部** 違規（空串列為通過）：

1. ``reference``：引用的形狀、原語、條件、狀態、物件存在、參數在範圍內（沿用
   :func:`trpg.content.skills.skill_problems`）。有這類問題時不再往下檢查。
2. ``cap.*``：硬性上限（4.3：效果數量、改寫規則型原語、``weapon_req`` 大類；推擊與拉扯的 2 格上限
   已由第 1 項的參數範圍檢查涵蓋）。
3. ``exclusion.<id>``：互斥規則（4.4，規則在 ``skill_exclusions.yaml``，通用處理）。
4. ``skeleton.*``：骨架結構（4.5）。
5. ``rarity.*``：稀有度限制（4.6）。
6. ``budget.*``：預算區間（4.2）。

訊息為繁體中文，指出技能、規則與數值。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import (
    EffectPattern,
    ShapePattern,
    SkeletonDef,
    SkillMatch,
)
from trpg.content.skills import (
    EffectSpec,
    SkillDef,
    rarity_rank,
    skill_problems,
)
from trpg.skillgen.budget import BudgetError, BudgetReport, skill_budget
from trpg.skillgen.mechanics import affect_set, resolved_affects

__all__ = ["Violation", "share_violations", "validate_skill"]

_PERMILLE = 1000
_MAX_EFFECTS = 4
_WEAPON_REQ = {"weapon": ("melee", "ranged"), "spell": ("focus", "any")}


@dataclass(frozen=True, slots=True)
class Violation:
    """一項違規：``rule`` 是規則代碼（例如 ``budget.over``、``exclusion.no_push_with_pull``）。"""

    skill_id: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.skill_id}［{self.rule}］{self.message}"


def _percent(value: Fraction) -> str:
    return f"{float(value) * 100:.1f}%"


def validate_skill(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """檢查 ``skill``，回傳全部違規；空串列表示通過。"""
    reference = _reference_violations(skill, library)
    if reference:
        return reference
    out = _cap_violations(skill, library)
    out += _passive_violations(skill, library)
    out += _stance_violations(skill, library)
    out += _exclusion_violations(skill, library)
    report, budget_out = _budget_violations(skill, library)
    out += _skeleton_violations(skill, library, report)
    out += _rarity_violations(skill, library)
    return out + budget_out


# ---------------------------------------------------------------------------
# 引用
# ---------------------------------------------------------------------------


def _reference_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    rules = library.ruleset
    problems = skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
        triggers=rules.skill_triggers.by_id(),
        stacks=rules.stacks.by_id(),
    )
    if skill.skeleton not in library.skeletons:
        problems.append(f"skeleton：沒有骨架資料檔 {skill.skeleton!r}")
    return [Violation(skill.id, "reference", p) for p in problems]


# ---------------------------------------------------------------------------
# 4.3 硬性上限
# ---------------------------------------------------------------------------


def _cap_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    out: list[Violation] = []

    def add(rule: str, message: str) -> None:
        out.append(Violation(skill.id, rule, message))

    if not 1 <= len(skill.effects) <= _MAX_EFFECTS:
        add("cap.effects", f"效果原語必須有 1 到 {_MAX_EFFECTS} 個，收到 {len(skill.effects)} 個")
    allowed = _WEAPON_REQ[skill.category]
    if skill.weapon_req not in allowed:
        add(
            "cap.weapon_req",
            f"weapon_req 只能是大類 {'、'.join(allowed)}（{skill.category}），"
            f"收到 {skill.weapon_req}",
        )
    out += _rule_rewrite_violations(skill, library)
    return out


def _rule_rewrite_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    primitives = library.ruleset.primitives.by_id()
    rewrites = [e.type for e in skill.effects if primitives[e.type].category == "rule_rewrite"]
    if not rewrites:
        return []
    out: list[Violation] = []
    budget = library.budget
    if len(rewrites) > budget.max_rule_rewrite:
        out.append(
            Violation(
                skill.id,
                "cap.rule_rewrite",
                f"改寫規則型原語最多 {budget.max_rule_rewrite} 個，收到 {len(rewrites)} 個"
                f"（{'、'.join(rewrites)}）",
            )
        )
    cost = skill.cost
    once = cost.uses_per_battle == 1
    slow = (cost.cooldown or 0) >= budget.rule_rewrite_min_cooldown
    if not (once or slow):
        out.append(
            Violation(
                skill.id,
                "cap.rule_rewrite_cost",
                f"有改寫規則型原語（{'、'.join(rewrites)}）的技能必須每場限一次，"
                f"或冷卻至少 {budget.rule_rewrite_min_cooldown} 回合"
                f"（目前：每場 {cost.uses_per_battle or '不限'}、冷卻 {cost.cooldown or 0}）",
            )
        )
    return out


def _passive_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """被動技能（2E-1 3.2）：法術技、任何武器；``target: self`` 時效果只能作用在持有者自己。

    ``trigger`` 的有無、時機存在、``n``、``target: other`` 與 ``has_other``、
    ``max_per_round`` 的範圍由 schema 與 :func:`trpg.content.skills.skill_problems` 檢查。
    """
    trigger = skill.trigger
    if skill.kind != "passive" or trigger is None:
        return []
    out: list[Violation] = []
    if skill.category != "spell" or skill.weapon_req != "any":
        out.append(
            Violation(
                skill.id,
                "passive.category",
                "被動技能必須是法術技且 weapon_req: any（觸發的效果自動命中，不看武器）",
            )
        )
    if trigger.target == "self":
        for index, effect in enumerate(skill.effects):
            affects = resolved_affects(library.ruleset, effect)
            if affects != "self":
                out.append(
                    Violation(
                        skill.id,
                        "passive.affects",
                        f"effects[{index}]（{effect.type}）：trigger.target 為 self 時，"
                        f"效果的 affects 只能是 self，收到 {affects}",
                    )
                )
    return out


def _stance_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """姿態（2E-2 4.3）：姿態技能的核心 ``apply_status`` 必須是 ``stance: true`` 的狀態，
    且不設持續回合；其他技能不得施加姿態狀態（取消只能靠 ``EndStance``，不會自己到期）。"""
    statuses = library.ruleset.statuses.by_id()
    out: list[Violation] = []
    for index, effect in enumerate(skill.effects):
        if effect.type != "apply_status" or effect.status not in statuses:
            continue
        is_stance = statuses[effect.status].stance
        where = f"effects[{index}]（{effect.status}）"
        if is_stance and skill.kind != "stance":
            out.append(
                Violation(
                    skill.id,
                    "stance.misuse",
                    f"{where}：姿態狀態只能由姿態技能（kind: stance）施加",
                )
            )
        elif skill.kind == "stance" and not is_stance:
            out.append(
                Violation(
                    skill.id, "stance.status", f"{where}：姿態技能施加的狀態必須是 stance: true"
                )
            )
        if is_stance and effect.duration is not None:
            out.append(
                Violation(
                    skill.id, "stance.duration", f"{where}：姿態狀態不設 duration（到取消為止）"
                )
            )
    if skill.kind == "stance" and not any(
        e.type == "apply_status" and e.status in statuses and statuses[e.status].stance
        for e in skill.effects
    ):
        out.append(Violation(skill.id, "stance.status", "姿態技能必須施加一個 stance: true 的狀態"))
    return out


# ---------------------------------------------------------------------------
# 4.4 互斥規則
# ---------------------------------------------------------------------------


def _shape_matches(skill: SkillDef, pattern: ShapePattern) -> bool:
    if skill.shape.type != pattern.type:
        return False
    given = pattern.model_dump(exclude={"type"}, exclude_none=True)
    have = skill.shape.param_values()
    return all(have.get(name) == value for name, value in given.items())


def _effect_matches(library: ContentLibrary, effect: EffectSpec, pattern: EffectPattern) -> bool:
    if pattern.type is not None and effect.type != pattern.type:
        return False
    if pattern.affects is None:
        return True
    actual = affect_set(resolved_affects(library.ruleset, effect))
    return bool(actual & set(pattern.affects))


def _repeated_control_group(skill: SkillDef, library: ContentLibrary) -> bool:
    statuses = library.ruleset.statuses.by_id()
    groups = [
        statuses[e.status].control_group
        for e in skill.effects
        if e.type == "apply_status" and e.status in statuses
    ]
    groups = [g for g in groups if g is not None]
    return len(groups) != len(set(groups))


def _match_shape_cost(skill: SkillDef, match: SkillMatch) -> bool:
    if match.kinds is not None and skill.kind not in match.kinds:
        return False
    if match.shapes is not None and not any(_shape_matches(skill, p) for p in match.shapes):
        return False
    if match.has_cooldown is not None and (skill.cost.cooldown is not None) != match.has_cooldown:
        return False
    return match.min_cooldown is None or (skill.cost.cooldown or 0) >= match.min_cooldown


def _match_primitives(skill: SkillDef, match: SkillMatch) -> bool:
    types = {e.type for e in skill.effects}
    if match.statuses is not None and not any(
        e.type == "apply_status" and e.status in match.statuses for e in skill.effects
    ):
        return False
    if match.primitives_any is not None and not types & set(match.primitives_any):
        return False
    return match.primitives_all is None or set(match.primitives_all) <= types


def _match_effects(skill: SkillDef, match: SkillMatch, library: ContentLibrary) -> bool:
    if match.effects_any is not None and not any(
        _effect_matches(library, e, p) for e in skill.effects for p in match.effects_any
    ):
        return False
    if match.effects_all is not None and not all(
        any(_effect_matches(library, e, p) for e in skill.effects) for p in match.effects_all
    ):
        return False
    return (
        match.repeated_control_group is None
        or _repeated_control_group(skill, library) == match.repeated_control_group
    )


def _matches(skill: SkillDef, match: SkillMatch, library: ContentLibrary) -> bool:
    """技能是否符合 ``match``（有填的欄位全部成立；空的比對永遠符合）。"""
    return (
        _match_shape_cost(skill, match)
        and _match_primitives(skill, match)
        and _match_effects(skill, match, library)
    )


def _facts(skill: SkillDef) -> str:
    """違規訊息附上的技能摘要：形狀、冷卻、效果。"""
    params = "、".join(f"{k} {v}" for k, v in skill.shape.param_values().items())
    shape = f"{skill.shape.type}（{params}）" if params else skill.shape.type
    cooldown = f"{skill.cost.cooldown} 回合" if skill.cost.cooldown else "無"
    effects = "、".join(
        f"{e.type}:{e.status}" if e.type == "apply_status" else e.type for e in skill.effects
    )
    return f"形狀 {shape}，冷卻 {cooldown}，效果 {effects}"


def _exclusion_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    out: list[Violation] = []
    for rule in library.exclusions.rules:
        if rule.when is not None and not _matches(skill, rule.when, library):
            continue
        broken = (rule.forbid is not None and _matches(skill, rule.forbid, library)) or (
            rule.require is not None and not _matches(skill, rule.require, library)
        )
        if broken:
            out.append(
                Violation(
                    skill.id,
                    f"exclusion.{rule.id}",
                    f"互斥規則「{rule.name_zh}」：{rule.message_zh}（{_facts(skill)}）",
                )
            )
    return out


# ---------------------------------------------------------------------------
# 4.5 骨架
# ---------------------------------------------------------------------------


def _skeleton_violations(
    skill: SkillDef, library: ContentLibrary, report: BudgetReport | None
) -> list[Violation]:
    skeleton = library.skeletons[skill.skeleton]
    if not skeleton.enabled:
        return [
            Violation(
                skill.id,
                "skeleton.disabled",
                f"骨架 {skeleton.id}（{skeleton.name_zh}）尚未啟用，不能使用",
            )
        ]
    out: list[Violation] = []

    def add(rule: str, message: str) -> None:
        out.append(Violation(skill.id, f"skeleton.{rule}", f"骨架 {skeleton.id}：{message}"))

    if skill.kind not in skeleton.kinds:
        add("kind", f"只適用 {'、'.join(skeleton.kinds)} 技能，收到 {skill.kind}")
    if skill.shape.type not in skeleton.shapes:
        add("shape", f"形狀只能是 {'、'.join(skeleton.shapes)}，收到 {skill.shape.type}")
    out += _effect_role_violations(skill, library, skeleton)
    if report is not None:
        out += _share_violations(skill, library, skeleton, report)
    if skeleton.requires_condition and not _has_condition(skill):
        add("condition", "技能或效果必須有條件")
    needed = skeleton.require_any_primitives
    if needed and not any(e.type in needed for e in skill.effects):
        add("required_primitive", f"效果至少要有 {'、'.join(needed)} 其中之一")
    forbidden = set(skeleton.forbid_affects)
    for index, effect in enumerate(skill.effects):
        actual = affect_set(resolved_affects(library.ruleset, effect))
        if actual & forbidden:
            add(
                "forbidden_affects",
                f"effects[{index}]（{effect.type}）的對象 {sorted(actual & forbidden)} 不被允許"
                f"（不得有對 {'、'.join(skeleton.forbid_affects)} 的效果）",
            )
    return out


def _has_condition(skill: SkillDef) -> bool:
    return skill.condition is not None or any(e.condition is not None for e in skill.effects)


def _is_core(library: ContentLibrary, skeleton: SkeletonDef, effect: EffectSpec) -> bool:
    if effect.type not in skeleton.core.primitives:
        return False
    if skeleton.core.affects is None:
        return True
    return resolved_affects(library.ruleset, effect) in skeleton.core.affects


def _effect_role_violations(
    skill: SkillDef, library: ContentLibrary, skeleton: SkeletonDef
) -> list[Violation]:
    """核心效果至少一個；附帶效果的原語、有害性與數量。"""
    out: list[Violation] = []
    primitives = library.ruleset.primitives.by_id()
    secondary = [(i, e) for i, e in enumerate(skill.effects) if not _is_core(library, skeleton, e)]
    if len(secondary) == len(skill.effects):
        names = "、".join(skeleton.core.primitives)
        out.append(
            Violation(
                skill.id, "skeleton.core", f"骨架 {skeleton.id}：沒有核心效果（需要 {names}）"
            )
        )
    if skeleton.core.beneficial_only:
        out += _beneficial_core_violations(skill, library, skeleton)
    rules = skeleton.secondary
    for index, effect in secondary:
        allowed = rules.primitives is None or effect.type in rules.primitives
        harmless = rules.harmful_only and not primitives[effect.type].harmful
        if not allowed or harmless:
            why = "不在允許的附帶原語內" if not allowed else "附帶效果必須是有害原語"
            out.append(
                Violation(
                    skill.id,
                    "skeleton.secondary",
                    f"骨架 {skeleton.id}：effects[{index}]（{effect.type}）{why}"
                    + (
                        f"（允許：{'、'.join(rules.primitives)}）"
                        if not allowed and rules.primitives
                        else ""
                    ),
                )
            )
    if len(secondary) > rules.max_count:
        out.append(
            Violation(
                skill.id,
                "skeleton.secondary_count",
                f"骨架 {skeleton.id}：附帶效果最多 {rules.max_count} 個，收到 {len(secondary)} 個",
            )
        )
    return out


def _beneficial_core_violations(
    skill: SkillDef, library: ContentLibrary, skeleton: SkeletonDef
) -> list[Violation]:
    """核心效果的狀態與表面必須有益（``beneficial``）。"""
    rules = library.ruleset
    statuses = rules.statuses.by_id()
    out: list[Violation] = []
    for index, effect in enumerate(skill.effects):
        if not _is_core(library, skeleton, effect):
            continue
        name: str | None = None
        if effect.type == "apply_status" and effect.status in statuses:
            if not statuses[effect.status].beneficial:
                name = f"狀態 {effect.status}"
        elif (
            effect.type == "create_surface"
            and effect.surface is not None
            and not rules.surfaces.get(effect.surface).beneficial
        ):
            name = f"表面 {effect.surface.value}"
        if name is not None:
            out.append(
                Violation(
                    skill.id,
                    "skeleton.core_beneficial",
                    f"骨架 {skeleton.id}：effects[{index}]（{effect.type}）的{name}不是有益的"
                    "（beneficial），不能作為核心",
                )
            )
    return out


def share_violations(
    skill: SkillDef, library: ContentLibrary, report: BudgetReport
) -> list[Violation]:
    """骨架的占比限制（核心效果的最低占比、個別原語的最高占比）；組合器調整強度時使用。"""
    return _share_violations(skill, library, library.skeletons[skill.skeleton], report)


def _share_violations(
    skill: SkillDef, library: ContentLibrary, skeleton: SkeletonDef, report: BudgetReport
) -> list[Violation]:
    """核心效果的最低占比與個別原語的最高占比（以效果點數計）。"""
    if report.raw <= 0:
        return []
    out: list[Violation] = []
    core_points = sum(
        (
            eb.points
            for eb, effect in zip(report.effects, skill.effects, strict=True)
            if _is_core(library, skeleton, effect)
        ),
        Fraction(0),
    )
    core_share = core_points / report.raw
    floor = Fraction(skeleton.core.min_share_permille, _PERMILLE)
    if core_share < floor:
        out.append(
            Violation(
                skill.id,
                "skeleton.core_share",
                f"骨架 {skeleton.id}：核心效果（{'、'.join(skeleton.core.primitives)}）占 "
                f"{_percent(core_share)}，低於下限 {_percent(floor)}",
            )
        )
    for primitive, limit_permille in sorted(skeleton.secondary.max_share_permille.items()):
        points = sum((eb.points for eb in report.effects if eb.type == primitive), Fraction(0))
        share, limit = points / report.raw, Fraction(limit_permille, _PERMILLE)
        if share > limit:
            out.append(
                Violation(
                    skill.id,
                    "skeleton.secondary_share",
                    f"骨架 {skeleton.id}：{primitive} 占 {_percent(share)}，"
                    f"超過上限 {_percent(limit)}",
                )
            )
    return out


# ---------------------------------------------------------------------------
# 4.6 稀有度
# ---------------------------------------------------------------------------


def _rarity_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    rules = library.ruleset
    have = rarity_rank(skill.rarity)
    needs: list[tuple[str, str, str]] = []  # (規則代碼, 說明, 最低稀有度)
    needs.append(
        ("shape", f"形狀 {skill.shape.type}", rules.shapes.by_id()[skill.shape.type].min_rarity)
    )
    skeleton = library.skeletons.get(skill.skeleton)
    if skeleton is not None:
        needs.append(("skeleton", f"骨架 {skeleton.id}", skeleton.min_rarity))
    if skill.trigger is not None:
        timing = rules.skill_triggers.by_id().get(skill.trigger.event)
        if timing is not None:
            needs.append(("trigger", f"觸發時機 {timing.id}", timing.min_rarity))
    primitives, statuses, conditions = (
        rules.primitives.by_id(),
        rules.statuses.by_id(),
        rules.conditions.by_id(),
    )
    cond_specs = [skill.condition] if skill.condition else []
    for effect in skill.effects:
        needs.append(("primitive", f"原語 {effect.type}", primitives[effect.type].min_rarity))
        if effect.type == "apply_status" and effect.status in statuses:
            needs.append(("status", f"狀態 {effect.status}", statuses[effect.status].min_rarity))
        if effect.condition is not None:
            cond_specs.append(effect.condition)
    needs += [("condition", f"條件 {c.type}", conditions[c.type].min_rarity) for c in cond_specs]
    out: list[Violation] = []
    seen: set[tuple[str, str]] = set()
    for rule, what, minimum in needs:
        if rarity_rank(minimum) > have and (rule, what) not in seen:
            seen.add((rule, what))
            out.append(
                Violation(
                    skill.id,
                    f"rarity.{rule}",
                    f"稀有度 {skill.rarity} 不能使用{what}（至少需要 {minimum}）",
                )
            )
    limit = library.budget.rarity[skill.rarity].max_effects
    if len(skill.effects) > limit:
        out.append(
            Violation(
                skill.id,
                "rarity.max_effects",
                f"稀有度 {skill.rarity} 的技能最多 {limit} 個效果，收到 {len(skill.effects)} 個",
            )
        )
    return out


# ---------------------------------------------------------------------------
# 4.2 預算
# ---------------------------------------------------------------------------


def _budget_violations(
    skill: SkillDef, library: ContentLibrary
) -> tuple[BudgetReport | None, list[Violation]]:
    try:
        report = skill_budget(skill, library)
    except BudgetError as exc:
        return None, [Violation(skill.id, "budget.unavailable", f"無法計算預算：{exc}")]
    if report.over_budget:
        return report, [
            Violation(
                skill.id,
                "budget.over",
                f"超出預算：total {float(report.total):.2f} ÷ 可用預算 {float(report.usable):.2f} "
                f"＝ {_percent(report.ratio)}"
                f"（上限 {_percent(report.max_ratio)}，階級 {skill.tier}）",
            )
        ]
    if report.too_weak:
        return report, [
            Violation(
                skill.id,
                "budget.weak",
                f"過弱：total {float(report.total):.2f} ÷ 可用預算 {float(report.usable):.2f} "
                f"＝ {_percent(report.ratio)}"
                f"（下限 {_percent(report.min_ratio)}，階級 {skill.tier}）",
            )
        ]
    return report, []
