"""技能驗證器（``docs/phases/Phase2B計畫.md`` 4.1–4.6）。

:func:`validate_skill` 依序檢查，回傳 **全部** 違規（空串列為通過）：

1. ``reference``：引用的形狀、原語、條件、狀態、物件存在、參數在範圍內（沿用
   :func:`trpg.content.library.skill_reference_problems`，與內容庫載入共用）。有這類問題時不再往下檢查。
2. ``cap.*``：硬性上限（4.3：效果數量、改寫規則型原語、``weapon_req`` 大類；推擊與拉扯的 2 格上限
   已由第 1 項的參數範圍檢查涵蓋）。
3. ``exclusion.<id>``：互斥規則（4.4，規則在 ``skill_exclusions.yaml``，通用處理）。
4. ``skeleton.*``：骨架結構（4.5）。
5. ``rarity.*``：稀有度限制（4.6）。
6. ``budget.*``：預算區間（4.2）。
7. （``keyword.required`` 已於 Phase 3-51 移除：沒有關鍵字的是「基礎技能」，不擋，06 6.27.1。）
8. ``scaling.weapon``／``scaling.range``：縮放屬性（含第二屬性）在 ``skill_scaling.yaml`` 的
   允許範圍內（Phase 3H-6、3H-7，06 6.10）。

修正技能（``kind: modifier``，Phase 3C-2）沒有效果原語，只檢查引用、骨架（啟用、kind、形狀）、
稀有度（骨架、規則條件與命中後效果的原語、狀態）與預算（見 :func:`_modifier_violations`）。

訊息為繁體中文，指出技能、規則與數值。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from fractions import Fraction

from trpg.content.library import ContentLibrary, gear_reference_problems, skill_reference_problems
from trpg.content.skill_rules import (
    EffectPattern,
    ShapePattern,
    SkeletonDef,
    SkillMatch,
)
from trpg.content.skills import (
    COMPOSITE_KIND_ZH,
    COMPOSITE_MOVES,
    GATHER_SHAPES,
    MAX_EFFECTS,
    ON_MISS_MIN_RARITY,
    REVIVE,
    SPLIT_SKELETONS,
    EffectSpec,
    SkillDef,
    rarity_rank,
    skill_elements,
)
from trpg.shared.types import Attribute
from trpg.skillgen.budget import BudgetError, BudgetReport, skill_budget, zone_cell_count
from trpg.skillgen.mechanics import affect_set, resolved_affects
from trpg.skillgen.scaling import attr_names_zh, scaling_basis_zh

__all__ = [
    "EFFECT_PARAM_RULES",
    "RARITY_STATUS_PRIMITIVES",
    "RarityNeed",
    "Violation",
    "effect_count",
    "effect_param_violations",
    "forbidden_affects_violations",
    "is_core_effect",
    "rarity_requirements",
    "share_violations",
    "validate_skill",
]

_PERMILLE = 1000
RARITY_STATUS_PRIMITIVES: tuple[str, ...] = ("apply_status",)
"""施加的狀態要檢查稀有度（``rarity.status``）的原語；LLM 提議模型依同一份清單篩狀態的列舉
（Phase 4-L5b）。"""
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
    resource = library.budget.cost_problem(skill.category, skill.cost)  # 3H-2，06 6.10
    out = [] if resource is None else [Violation(skill.id, "cap.resource", resource)]
    # 最低花費（3-48c；例外：花源力、裝備動作，06 6.10）——內建技能也照查（玩法 PM 2026-10-24 補齊）
    least = library.budget.min_cost_problem(skill.kind, skill.category, skill.cost, skill.tags)
    if least is not None:
        out.append(Violation(skill.id, "cap.min_cost", least))
    out += _rune_tag_violations(skill, library)
    out += _on_kill_status_violations(skill, library)
    out += _weapon_scaling_violations(skill, library) + _scaling_range_violations(skill, library)
    return [*out, *_structure_violations(skill, library)]


def _rune_tag_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """``rune.tag``（3-48c，06 6.25）：刻印的標籤只能用已定義的符文標籤（``skill_tags.yaml`` 有
    ``rune_zh`` 的）；新標籤由內容資料新增，不開放自訂（沒有技能能讀取或引爆）。"""
    runes = library.ruleset.skill_tags.rune_names()
    names = "、".join(f"{runes[t]}紋" for t in sorted(runes))
    return [
        Violation(
            skill.id,
            "rune.tag",
            f"刻印的標籤只能選已定義的符文標籤（{names}），收到「{effect.tag}」",
        )
        for effect in skill.iter_effects(include_followup=True)
        if effect.type == "inscribe" and effect.tag is not None and effect.tag not in runes
    ]


def _on_kill_status_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """``on_kill.beneficial``（3-48f，06 6.18）：擊殺時效果一律作用在施放者自己身上，施加的狀態
    只能是有益狀態（工坊已只列有益狀態；LLM 提議與 YAML 匯入也在這裡擋下）。"""
    statuses = library.ruleset.statuses.by_id()
    out: list[Violation] = []
    for effect in skill.iter_effects(include_followup=True):
        for sub in effect.on_kill or ():
            status = statuses.get(sub.status) if sub.type == "apply_status" and sub.status else None
            if status is not None and not status.beneficial:
                out.append(
                    Violation(
                        skill.id,
                        "on_kill.beneficial",
                        f"擊殺時效果會作用在你自己身上，只能施加有益的狀態；"
                        f"「{status.name_zh}」是負面狀態",
                    )
                )
    return out


def _weapon_scaling_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """``scaling.weapon``（Phase 3H-6，玩法決定 #45）：產生的武器技看手上武器的屬性，
    ``scaling_attr`` 必須是所需武器大類的主屬性、不帶第二縮放屬性。內建技能（欄位只當顯示提示）
    與進化而來的技能（有 ``parents``）不檢查。"""
    if (
        skill.category != "weapon"
        or skill.provenance.origin == "builtin"
        or skill.provenance.parents
    ):
        return []
    attr = library.skill_scaling.weapon_class_attr(skill.weapon_req)
    if skill.scaling_attr == attr:
        return []
    return [
        Violation(
            skill.id,
            "scaling.weapon",
            f"武器技的命中與傷害看手上武器的屬性：縮放屬性要設為 {attr.display_name}"
            f"（{skill.weapon_req} 武器的主屬性）；要加屬性請用第二縮放屬性（智力、感知、意志）",
        )
    ]


def _scaling_range_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """``scaling.range``（Phase 3H-7、3I-3，06 6.10）：主屬性與第二屬性都要在允許範圍內（法術技依
    效果推導的主題）；武器技的第二屬性只能是心智屬性（武器屬性＋一個心智屬性，#46）；身體類
    法術沒有第二屬性。``already``：``scaling.weapon`` 已經報過（不重複主屬性的問題）。"""
    second = skill.secondary_scaling_attr
    if skill.category == "weapon":
        pool = library.secondary_range(skill)
        if second is None or second in pool:
            return []
        message = (
            f"武器技的第二縮放屬性只能是心智屬性（{attr_names_zh(pool)}，取武器屬性與它的平均），"
            f"收到 {second.display_name}"
        )
        return [Violation(skill.id, "scaling.range", message)]
    allowed = library.scaling_range(skill)
    out: list[Violation] = []
    if skill.scaling_attr not in allowed:
        out.append(_range_violation(skill, library, skill.scaling_attr, "縮放屬性", allowed))
    if second is not None:
        pool = library.secondary_range(skill)
        if not pool:
            out.append(
                Violation(
                    skill.id,
                    "scaling.range",
                    f"第二縮放屬性 {second.display_name} 不能用："
                    f"{scaling_basis_zh(skill, library)}，"
                    "身體類的法術沒有第二屬性",
                )
            )
        elif second not in pool:
            out.append(_range_violation(skill, library, second, "第二縮放屬性", pool))
    return out


def _range_violation(
    skill: SkillDef,
    library: ContentLibrary,
    attr: Attribute,
    label: str,
    allowed: Sequence[Attribute],
) -> Violation:
    return Violation(
        skill.id,
        "scaling.range",
        f"{label} {attr.display_name} 不在這招的允許範圍：{scaling_basis_zh(skill, library)}，"
        f"只能看 {attr_names_zh(allowed)}",
    )


def _structure_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    if skill.is_modifier:
        return _modifier_violations(skill, library)
    if skill.followup is not None:
        return _composite_violations(skill, library)
    out = _cap_violations(skill, library)
    out += _passive_violations(skill, library)
    out += _stance_violations(skill, library)
    out += _exclusion_violations(skill, library)
    report, budget_out = _budget_violations(skill, library)
    out += _skeleton_violations(skill, library, report)
    out += _rarity_violations(skill, library)
    return out + budget_out + _variant_violations(skill, library, report)


def _variant_violations(
    skill: SkillDef, library: ContentLibrary, report: BudgetReport | None
) -> list[Violation]:
    """戰場變奏（Phase 3-25a，PM 決定 #6）：每個變奏型態本身照一般技能完整檢查（骨架、互斥、
    稀有度、預算窗……）；基礎型態的預算已含變奏加價（:func:`skill_budget`）；型態的預算取自
    ``report.variants``（含射程加價，Phase 3-25b），不重算。"""
    out: list[Violation] = []
    forms = {} if report is None else {f.id: f.report for f in report.variants}
    for variant in skill.variants:
        form = skill.variant_form(variant.id)
        checked = [
            v for v in _structure_violations(form, library) if not v.rule.startswith("budget.")
        ]
        if variant.id in forms:
            checked += _ratio_violations(form, forms[variant.id])
        out += [
            Violation(
                v.skill_id, f"variant.{variant.id}.{v.rule}", f"{variant.name_zh}：{v.message}"
            )
            for v in checked
        ]
    return out


# ---------------------------------------------------------------------------
# 複合技能（Phase 3F-3a，6.23）
# ---------------------------------------------------------------------------

COMPOSITE_SKELETON = "displace"
"""複合技能的位移段（技能本身）使用的骨架。"""
COMPOSITE_MIN_RARITY = "rare"
"""複合技能的最低稀有度（6.23）。"""


def effect_count(skill: SkillDef) -> int:
    """技能的效果原語數（複合技能兩段合計，6.6）。"""
    extra = 0 if skill.followup is None else len(skill.followup.effects)
    return len(skill.effects) + extra


def _composite_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """複合技能：兩段（技能本身與 :meth:`SkillDef.followup_skill`）各自照自己骨架的規則檢查——
    只有一個自身位移原語的段（位移段）與聚集段只檢查骨架與形狀（:func:`_move_segment_violations`），
    其他段完整檢查骨架；稀有度與效果數以兩段合計；預算以兩段加總 × 複合加成計算。"""
    follow = skill.followup_skill()
    assert follow is not None and skill.followup is not None
    when = skill.followup.when
    out = _cap_violations(skill, library)
    out += _segment_violations(skill.move_segment(), library, lone=when in _LONE_FIRST)
    second = _segment_violations(follow, library, lone=_is_lone_move(follow))
    label = "動作段" if when == "after_move" else "第二段"
    out += [Violation(v.skill_id, f"followup.{v.rule}", f"{label}：{v.message}") for v in second]
    out += _rarity_violations(skill, library)
    _, budget_out = _budget_violations(skill, library)
    return out + budget_out


_LONE_FIRST = ("after_move", "after_gather")
"""第一段只有一個原語、不跑核心與占比檢查的種類：位移段（一個自身位移）、聚集段（一個
``pull``）。"""


def _is_lone_move(segment: SkillDef) -> bool:
    return len(segment.effects) == 1 and segment.effects[0].type in COMPOSITE_MOVES


def _segment_violations(
    segment: SkillDef, library: ContentLibrary, *, lone: bool
) -> list[Violation]:
    """複合技能的一段：只有一個位移（或聚集）原語的段只檢查骨架、形狀與互斥；其他段照自己的骨架
    完整檢查（改寫型原語、復活、互斥、骨架的核心、附帶效果與占比）。"""
    if lone:
        return _move_segment_violations(segment, library) + _exclusion_violations(segment, library)
    try:
        report: BudgetReport | None = skill_budget(segment, library)
    except BudgetError:
        report = None
    out = _rule_rewrite_violations(segment, library)
    out += _revive_violations(segment, library)
    out += _exclusion_violations(segment, library)
    return out + _skeleton_violations(segment, library, report)


def _move_segment_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """位移段（或聚集段）：骨架 ``displace``（啟用、主動）、形狀在骨架允許的形狀內（聚集段的形狀由
    schema 限定在 :data:`~trpg.content.skills.GATHER_SHAPES`，不另外檢查）。效果只能是一個原語
    （schema 已檢查），所以不另外檢查核心與占比。"""
    if skill.skeleton != COMPOSITE_SKELETON:
        return [
            Violation(
                skill.id,
                "composite.skeleton",
                f"複合技能的位移段與聚集段骨架必須是 {COMPOSITE_SKELETON}，收到 {skill.skeleton}",
            )
        ]
    skeleton = library.skeletons[skill.skeleton]
    gather = skill.effects[0].type == "pull" and skill.shape.type in GATHER_SHAPES
    if skill.shape.type not in skeleton.shapes and not gather:
        return [
            Violation(
                skill.id,
                "skeleton.shape",
                f"骨架 {skeleton.id}：形狀只能是 {'、'.join(skeleton.shapes)}，"
                f"收到 {skill.shape.type}",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# 引用
# ---------------------------------------------------------------------------


def _reference_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    problems = skill_reference_problems(skill, library.ruleset, library.skills)
    # 限定武器與「手持某種武器」條件（3I-5）：引用的裝備存在、武器大類符合 weapon_req
    problems += gear_reference_problems(skill, library.weapons, library.offhands)
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

    count = effect_count(skill)
    if not 1 <= count <= MAX_EFFECTS:
        add("cap.effects", f"效果原語必須有 1 到 {MAX_EFFECTS} 個，收到 {count} 個")
    allowed = _WEAPON_REQ[skill.category]
    if skill.weapon_req not in allowed:
        add(
            "cap.weapon_req",
            f"weapon_req 只能是大類 {'、'.join(allowed)}（{skill.category}），"
            f"收到 {skill.weapon_req}",
        )
    if skill.trap is not None and all(e.type == "place_trap" for e in skill.effects):
        add(
            "trap.effects",
            "放置陷阱要有踩到後的效果：請新增一個效果（例如傷害），它就是踩到後的效果",
        )
    out += _self_cost_violations(skill, library)
    out += _rule_rewrite_violations(skill, library)
    out += _revive_violations(skill, library)
    return out


def _self_cost_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """自己付的代價（3-50，06 6.5）：允許清單、固定持續時間、限骨架（沉默只能放法術技）、一招
    最多 1 個自身狀態（透支不算，3-50b；``SkillCost.self_status`` 單一欄位即保證）。整體上限 50%
    由預算器的 ``total_cap`` 截斷。"""
    out: list[Violation] = []
    cost = skill.cost
    rule = library.budget.allowance.self_status
    status = cost.self_status
    if status is not None:
        if status.status not in rule.allowed:
            out.append(
                Violation(
                    skill.id,
                    "cap.self_status",
                    f"自身狀態代價只能是 {'、'.join(rule.allowed)}，收到 {status.status}",
                )
            )
        fixed = rule.fixed_duration.get(status.status)
        if fixed is not None and status.duration != fixed:
            out.append(
                Violation(
                    skill.id,
                    "cap.self_status_duration",
                    f"自身狀態 {status.status} 持續時間固定為 {fixed} 回合，收到 {status.duration}",
                )
            )
        if status.status in rule.spell_only and skill.category != "spell":
            out.append(
                Violation(
                    skill.id,
                    "cap.self_status_category",
                    f"自身狀態 {status.status} 只能放在法術技，收到 {skill.category}",
                )
            )
    return out


def _revive_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """復活（3D-8b）：技能必須每場限一次，或冷卻至少 ``rule_rewrite_min_cooldown`` 回合（與改寫規則
    型原語同一個門檻）。"""
    if not any(e.type == REVIVE for e in skill.effects):
        return []
    cost = skill.cost
    min_cooldown = library.budget.rule_rewrite_min_cooldown
    if cost.uses_per_battle == 1 or (cost.cooldown or 0) >= min_cooldown:
        return []
    return [
        Violation(
            skill.id,
            "cap.revive_cost",
            f"有復活（revive）的技能必須每場限一次，或冷卻至少 {min_cooldown} 回合"
            f"（目前：每場 {cost.uses_per_battle or '不限'}、冷卻 {cost.cooldown or 0}）",
        )
    ]


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
    min_cooldown = (
        budget.rule_rewrite_min_cooldown
        if cost.source is None
        else budget.rule_rewrite_min_cooldown_with_source
    )
    slow = (cost.cooldown or 0) >= min_cooldown
    if not (once or slow):
        paid = "（花源力）" if cost.source is not None else ""
        out.append(
            Violation(
                skill.id,
                "cap.rule_rewrite_cost",
                f"有改寫規則型原語（{'、'.join(rewrites)}）的技能{paid}必須每場限一次，"
                f"或冷卻至少 {min_cooldown} 回合"
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
    skeleton = library.skeletons.get(skill.skeleton)
    if skeleton is not None and _skeleton_category_mismatch(skill, skeleton):
        out.append(
            Violation(
                skill.id,
                "passive.category",
                f"骨架 {skeleton.id} 要求 category: {skeleton.required_category or '不限'}、"
                f"weapon_req: {skeleton.required_weapon_req or '不限'}"
                f"（收到 {skill.category}、{skill.weapon_req}）",
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


def _skeleton_category_mismatch(skill: SkillDef, skeleton: SkeletonDef) -> bool:
    wanted_category = skeleton.required_category
    wanted_weapon = skeleton.required_weapon_req
    return (wanted_category is not None and skill.category != wanted_category) or (
        wanted_weapon is not None and skill.weapon_req != wanted_weapon
    )


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
    if (
        skill.kind == "stance"
        and skill.form_id is None
        and not any(
            e.type == "apply_status" and e.status in statuses and statuses[e.status].stance
            for e in skill.effects
        )
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
    if match.elements_any is not None and not skill_elements(skill) & set(match.elements_any):
        return False
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
    if match.any_of is not None and not any(_matches(skill, m, library) for m in match.any_of):
        return False
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


def _modifier_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """修正技能：骨架（啟用、kind、形狀）、稀有度與預算；效果數量、互斥與骨架的核心效果規則
    不適用（沒有效果原語）。"""
    skeleton = library.skeletons[skill.skeleton]
    out: list[Violation] = []
    if not skeleton.enabled:
        out.append(
            Violation(skill.id, "skeleton.disabled", f"骨架 {skeleton.id} 尚未啟用，不能使用")
        )
    if skill.kind not in skeleton.kinds:
        out.append(
            Violation(
                skill.id,
                "skeleton.kind",
                f"骨架 {skeleton.id}：只適用 {'、'.join(skeleton.kinds)} 技能，收到 {skill.kind}",
            )
        )
    if skill.shape.type not in skeleton.shapes:
        out.append(
            Violation(
                skill.id,
                "skeleton.shape",
                f"骨架 {skeleton.id}：形狀只能是 {'、'.join(skeleton.shapes)}，"
                f"收到 {skill.shape.type}",
            )
        )
    out += _rarity_violations(skill, library)
    _, budget_out = _budget_violations(skill, library)
    return out + budget_out


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
    return out + forbidden_affects_violations(skill, library, skeleton)


def forbidden_affects_violations(
    skill: SkillDef, library: ContentLibrary, skeleton: SkeletonDef
) -> list[Violation]:
    """``skeleton.forbidden_affects``：效果的對象在骨架的 ``forbid_affects`` 內。驗證器與工坊的
    對象選項停用（:func:`effect_param_violations`）共用這一個函式。"""
    out: list[Violation] = []
    forbidden = set(skeleton.forbid_affects)
    for index, effect in enumerate(skill.effects):
        if effect.split_heal and skeleton.id in SPLIT_SKELETONS:
            continue  # 聖光雙效（3D-8a）：對敵傷害、對友治療是同一個效果，光環骨架也允許
        actual = affect_set(resolved_affects(library.ruleset, effect))
        if actual & forbidden:
            out.append(
                Violation(
                    skill.id,
                    "skeleton.forbidden_affects",
                    f"骨架 {skeleton.id}：effects[{index}]（{effect.type}）的對象 "
                    f"{sorted(actual & forbidden)} 不被允許"
                    f"（不得有對 {'、'.join(skeleton.forbid_affects)} 的效果）",
                )
            )
    return out


EFFECT_PARAM_EXCLUSIONS: tuple[str, ...] = (
    "self_shape_no_enemy_effect",
    "stun_single_long_cooldown",
    "no_repeated_control_group",
    "no_damage_with_ally_heal",
    "terrain_needs_earth",
)
"""互斥規則裡，由「效果的對象、狀態或元素」決定會不會違規的幾條（``skill_exclusions.yaml``）。"""
EFFECT_PARAM_RULES: tuple[str, ...] = (
    *(f"exclusion.{rule}" for rule in EFFECT_PARAM_EXCLUSIONS),
    "skeleton.forbidden_affects",
    "skeleton.core_beneficial",
    "passive.affects",
    "stance.misuse",
    "stance.status",
    "stance.duration",
    "on_kill.beneficial",
)
"""效果參數（對象、狀態）會牽涉的規則代碼。工坊在選項上事前停用這些規則會擋的選項
（:mod:`trpg.skillgen.option_effect_rules`，3-48h）。"""


def effect_param_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    """:data:`EFFECT_PARAM_RULES` 的違規。呼叫的是 :func:`validate_skill` 用的同一批規則函式，
    所以驗證器與工坊的選項停用不可能各說各話（3-48h：同源）。"""
    known = library.ruleset.primitives.by_id()
    if (
        skill.is_modifier
        or skill.skeleton not in library.skeletons
        or any(e.type not in known for e in skill.effects)
    ):
        return []
    out = _exclusion_violations(skill, library)
    out += _passive_violations(skill, library)
    out += _stance_violations(skill, library)
    skeleton = library.skeletons[skill.skeleton]
    out += forbidden_affects_violations(skill, library, skeleton)
    if skeleton.core.beneficial_only:
        out += _beneficial_core_violations(skill, library, skeleton)
    out += _on_kill_status_violations(skill, library)
    return [v for v in out if v.rule in EFFECT_PARAM_RULES]


def _has_condition(skill: SkillDef) -> bool:
    return skill.condition is not None or any(e.condition is not None for e in skill.effects)


def is_core_effect(library: ContentLibrary, skeleton: SkeletonDef, effect: EffectSpec) -> bool:
    """``effect`` 是不是骨架的核心效果（核心占比與預算器的旋鈕權重共用）。"""
    return _is_core(library, skeleton, effect)


def _is_core(library: ContentLibrary, skeleton: SkeletonDef, effect: EffectSpec) -> bool:
    if effect.split_heal and skeleton.id in SPLIT_SKELETONS:
        return True  # 聖光雙效（3D-8a）是光環與範圍骨架的核心
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
            for eb, effect in zip(report.effects, skill.effects, strict=False)  # 失手反噬列在最後
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


@dataclass(frozen=True, slots=True)
class RarityNeed:
    """一項稀有度需求：``rule`` 規則代碼（``shape``、``primitive``……）、``what`` 中文說明、
    ``minimum`` 最低稀有度。"""

    rule: str
    what: str
    minimum: str


_TERRAIN_PRIMITIVES: tuple[str, ...] = ("raise_terrain", "lower_terrain")
"""升降地形原語（Phase 3-54b：只有大地能用；影響格數越大稀有度要求越高）。"""


def _terrain_area_needs(skill: SkillDef, library: ContentLibrary) -> list[RarityNeed]:
    """升降地形的影響格數對應的最低稀有度（``terrain_area_rarity``，Phase 3-54b，06 6.33）。
    形狀沒有固定格數（連鎖）時略過（形狀自己有稀有度要求）。"""
    tiers = library.budget.terrain_area_rarity
    if not tiers or not any(e.type in _TERRAIN_PRIMITIVES for e in skill.effects):
        return []
    try:
        cells = zone_cell_count(skill, library)
    except BudgetError:
        return []
    minimum = next((t.rarity for t in reversed(tiers) if cells >= t.min_cells), None)
    if minimum is None:
        return []
    return [RarityNeed("terrain_area", f"升降地形影響 {cells} 格", minimum)]


def rarity_requirements(skill: SkillDef, library: ContentLibrary) -> list[RarityNeed]:
    """技能用到的每個形狀、骨架、觸發時機、原語、狀態、條件與失手反噬的最低稀有度（依出現順序，
    不去重）。驗證器的 ``rarity.*`` 與技能工坊的「最低稀有度」共用（Phase 3F-1）。"""
    rules = library.ruleset
    needs: list[RarityNeed] = []
    needs.append(
        RarityNeed(
            "shape", f"形狀 {skill.shape.type}", rules.shapes.by_id()[skill.shape.type].min_rarity
        )
    )
    skeleton = library.skeletons.get(skill.skeleton)
    if skeleton is not None:
        needs.append(RarityNeed("skeleton", f"骨架 {skeleton.id}", skeleton.min_rarity))
    if skill.trigger is not None:
        timing = rules.skill_triggers.by_id().get(skill.trigger.event)
        if timing is not None:
            needs.append(RarityNeed("trigger", f"觸發時機 {timing.id}", timing.min_rarity))
    primitives, statuses, conditions = (
        rules.primitives.by_id(),
        rules.statuses.by_id(),
        rules.conditions.by_id(),
    )
    if skill.cost.on_miss:  # 失手反噬至少 rare（3D-7a 驗收決定、設計 6.17）
        needs.append(RarityNeed("on_miss", "失手反噬 cost.on_miss", ON_MISS_MIN_RARITY))
    cond_specs = [skill.condition] if skill.condition else []
    cond_specs += [r.condition for r in skill.modifiers if r.condition is not None]
    on_hit = [e for r in skill.modifiers for e in r.change.on_hit_effects or ()]
    for effect in (*skill.effects, *on_hit):
        needs.append(
            RarityNeed("primitive", f"原語 {effect.type}", primitives[effect.type].min_rarity)
        )
        if effect.type in RARITY_STATUS_PRIMITIVES and effect.status in statuses:
            needs.append(
                RarityNeed("status", f"狀態 {effect.status}", statuses[effect.status].min_rarity)
            )
        if effect.condition is not None:
            cond_specs.append(effect.condition)
    needs += [
        RarityNeed("condition", f"條件 {c.type}", conditions[c.type].min_rarity) for c in cond_specs
    ]
    needs += _terrain_area_needs(skill, library)
    follow = skill.followup_skill()
    if (
        follow is not None and skill.followup is not None
    ):  # 複合技能：至少稀有，且不低於第二段的需求
        when = skill.followup.when
        kind = COMPOSITE_KIND_ZH[when]
        needs.append(RarityNeed("composite", f"複合技能（{kind}）", COMPOSITE_MIN_RARITY))
        label = "動作段" if when == "after_move" else "第二段"
        needs += [
            replace(n, what=f"{label}的{n.what}") for n in rarity_requirements(follow, library)
        ]
    return needs


def _rarity_violations(skill: SkillDef, library: ContentLibrary) -> list[Violation]:
    have = rarity_rank(skill.rarity)
    out: list[Violation] = []
    seen: set[tuple[str, str]] = set()
    for need in rarity_requirements(skill, library):
        rule, what, minimum = need.rule, need.what, need.minimum
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
    count = effect_count(skill)
    if count > limit:
        out.append(
            Violation(
                skill.id,
                "rarity.max_effects",
                f"稀有度 {skill.rarity} 的技能最多 {limit} 個效果，收到 {count} 個",
            )
        )
    return out


# ---------------------------------------------------------------------------
# 4.2 預算
# ---------------------------------------------------------------------------


GEAR_TAG = "gear"
"""裝備授予的常駐技能（Phase 3G-G3b）的標籤：不套「過弱」下限（詞條有自己的預算）。"""


def _budget_violations(
    skill: SkillDef, library: ContentLibrary
) -> tuple[BudgetReport | None, list[Violation]]:
    try:
        report = skill_budget(skill, library)
    except BudgetError as exc:
        return None, [Violation(skill.id, "budget.unavailable", f"無法計算預算：{exc}")]
    return report, _ratio_violations(skill, report)


def _ratio_violations(skill: SkillDef, report: BudgetReport) -> list[Violation]:
    if report.over_budget:
        return [
            Violation(
                skill.id,
                "budget.over",
                f"超出預算：total {float(report.total):.2f} ÷ 可用預算 {float(report.usable):.2f} "
                f"＝ {_percent(report.ratio)}"
                f"（上限 {_percent(report.max_ratio)}，階級 {skill.tier}）",
            )
        ]
    if report.too_weak and GEAR_TAG not in skill.tags:  # 裝備授予的技能：預算算在詞條上（8.21.2.9）
        return [
            Violation(
                skill.id,
                "budget.weak",
                f"過弱：total {float(report.total):.2f} ÷ 可用預算 {float(report.usable):.2f} "
                f"＝ {_percent(report.ratio)}"
                f"（下限 {_percent(report.min_ratio)}，階級 {skill.tier}）",
            )
        ]
    return []
