"""提議的驗證與錯誤回饋（:func:`evaluate_proposal`、:func:`feedback_payload`）。

自 :mod:`trpg.skillgen.proposal` 拆出（Phase R1d），內容未改。
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from pydantic import (
    TypeAdapter,
    ValidationError,
)

from trpg.content.keyword_derive import derive_keywords, skill_condition_specs
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    WIELDING_WEAPON,
    SkillDef,
    SkillRuleError,
    drop_icon_prop,
    error_path_of,
    rarity_rank,
    weapon_problem,
)
from trpg.skillgen.proposal.build import CATEGORIES
from trpg.skillgen.proposal.convert import to_skill_def
from trpg.skillgen.proposal.models import (
    _GENERAL_TAG,
    DIAGNOSTIC_INPUT_CHARS,
    ProposalContext,
    ProposalError,
    ProposalModels,
    ProposalResult,
    Stage,
)
from trpg.skillgen.proposal_numbers import (
    NumberFiller,
    minimal_filler,
)
from trpg.skillgen.proposal_passive import best_trigger
from trpg.skillgen.validate import validate_skill

_QUOTED = re.compile(r"'([^']*)'")


_PATH_PREFIX = re.compile(r"^([A-Za-z_][\w.\[\]]*)：(.*)$", re.DOTALL)


def _json_path(loc: Sequence[int | str], data: object) -> str:
    """pydantic 的 ``loc`` → JSON 路徑；discriminated union 插在路徑裡的標籤（例如 ``damage``）
    依原始輸入去掉，讓路徑與 LLM 送來的 JSON 一致。"""
    parts: list[str] = []
    node: object = data
    for item in loc:
        if isinstance(item, int):
            parts.append(f"[{item}]")
            node = node[item] if isinstance(node, list) and item < len(node) else None
            continue
        if (
            isinstance(node, dict)
            and item not in node
            and (
                item in (node.get("type"), node.get("event"), node.get("layout"), _GENERAL_TAG)
                or "~" in item  # 判別函式的分支標籤（4-L10a）
            )
        ):
            continue  # union 標籤
        parts.append(f".{item}" if parts else item)
        node = node.get(item) if isinstance(node, dict) else None
    return "".join(parts)


_MESSAGES: dict[str, Callable[[Mapping[str, Any]], str]] = {
    "missing": lambda _: "缺少必填欄位",
    "extra_forbidden": lambda _: "不認得的欄位（這個類型沒有這個參數）",
    "literal_error": lambda _: "不是可用的值",
    "enum": lambda _: "不是可用的值",
    "union_tag_invalid": lambda c: f"未知的類型 {c.get('tag')!r}",
    "union_tag_not_found": lambda c: f"缺少區分類型的欄位 {c.get('discriminator')}",
    "greater_than_equal": lambda c: f"必須 ≥ {c.get('ge')}",
    "less_than_equal": lambda c: f"必須 ≤ {c.get('le')}",
    "string_pattern_mismatch": lambda c: f"格式不符（{c.get('pattern')}）",
    "too_long": lambda c: f"最多 {c.get('max_length')} 項",
    "too_short": lambda c: f"至少 {c.get('min_length')} 項",
}
"""常見的 pydantic 錯誤型別 → 中文原因（其餘沿用原訊息；自訂驗證器的訊息本來就是中文）。"""


_ALLOWED_CTX = {
    "literal_error": "expected",
    "enum": "expected",
    "union_tag_invalid": "expected_tags",
}
"""哪些錯誤型別的 ``ctx`` 帶有可用值清單。"""


def _message_zh(error: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    kind = str(error["type"])
    ctx: Mapping[str, Any] = error.get("ctx") or {}
    render = _MESSAGES.get(kind)
    message = render(ctx) if render else str(error["msg"]).removeprefix("Value error, ")
    key = _ALLOWED_CTX.get(kind)
    allowed = tuple(_QUOTED.findall(str(ctx.get(key, "")))) if key else ()
    return message, allowed


_VARIANT_PATH = re.compile(r"^variants\.([^.\[]+)(?:\.(.*))?$")


def _proposal_path(path: str, skill: SkillDef | None = None) -> str:
    """``SkillDef`` 的錯誤路徑 → 提議的路徑（Phase 4-L10a）：``cost.on_miss`` 在提議裡是
    ``cost_on_miss``；跨檔案驗證以變奏 ID 標的 ``variants.<id>.…`` 換成 ``variants[i]`` 並把型態的
    效果對回變奏的 ``add_effect``／``replace_effect.effect``（見
    :meth:`~trpg.content.skills.SkillDef.variant_error_path`）。"""
    match = _VARIANT_PATH.match(path)
    if match is not None and skill is not None:
        ids = [v.id for v in skill.variants]
        if match.group(1) in ids:
            path = skill.variant_error_path(ids.index(match.group(1)), match.group(2) or "")
    return path.replace("cost.on_miss", "cost_on_miss")


def _skill_path(error: Mapping[str, Any], loc_path: str, message: str) -> str:
    """``SkillDef`` 自己的檢查（``stage: skill``）的路徑（Phase 4-L5b）：驗證器以
    :class:`~trpg.content.skills.SkillRuleError` 帶出的路徑優先；否則從訊息找效果的完整路徑
    （含巢狀的 ``then``、``on_kill``、賭注分支與失手反噬，4-L10a）；訊息講形狀時指向 ``shape``；
    都沒有就只用 pydantic 的位置（技能層級為空字串）。"""
    raw = (error.get("ctx") or {}).get("error")
    found = ""
    if isinstance(raw, SkillRuleError):
        found = raw.path
    elif found := error_path_of(message):
        pass
    elif "形狀" in message:
        found = "shape"
    if not found:
        return loc_path
    found = _proposal_path(found)
    return f"{loc_path}.{found}" if loc_path else found


def _pydantic_errors(exc: ValidationError, stage: Stage, data: object) -> list[ProposalError]:
    out: list[ProposalError] = []
    for error in exc.errors(include_url=False):
        message, allowed = _message_zh(error)
        path = _json_path(tuple(error["loc"]), data)
        code = str(error["type"])
        if stage == "skill":
            path = _skill_path(error, path, message)
            raw = (error.get("ctx") or {}).get("error")
            if isinstance(raw, SkillRuleError) and raw.code:
                code = raw.code
        out.append(
            ProposalError(
                stage=stage,
                path=path,
                code=code,
                message=message,
                allowed=allowed,
                loc=".".join(str(part) for part in error["loc"]),
                input=_input_text(error.get("input")),
            )
        )
    return out


def _input_text(value: object) -> str:
    """pydantic 錯誤的輸入值 → 診斷文字（LB-2；截到 :data:`DIAGNOSTIC_INPUT_CHARS` 字）。"""
    if value is None:
        return ""
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=repr)
    except (TypeError, ValueError):
        text = repr(value)
    if len(text) > DIAGNOSTIC_INPUT_CHARS:
        return text[: DIAGNOSTIC_INPUT_CHARS - 1] + "…"
    return text


def _rule_error(rule: str, message: str, skill: SkillDef | None = None) -> ProposalError:
    """跨檔案驗證的一項違規 → 錯誤：訊息開頭的路徑優先；變奏型態的違規（``variant.<id>.…``）
    指向該變奏（訊息提到的效果對回變奏換上或加上的效果）；其餘從訊息找效果路徑（4-L10a）。"""
    match = _PATH_PREFIX.match(message)
    if match is not None:
        path = _proposal_path(match.group(1), skill)
        return ProposalError(stage="rules", path=path, code=rule, message=match.group(2))
    path = error_path_of(message)
    variant = re.match(r"^variant\.([^.]+)\.", rule)
    if variant is not None and skill is not None:
        path = _proposal_path(f"variants.{variant.group(1)}.{path}".rstrip("."), skill)
    return ProposalError(stage="rules", path=_proposal_path(path), code=rule, message=message)


def _layout_hints(
    errors: list[ProposalError], models: ProposalModels, data: object = None
) -> list[ProposalError]:
    """頂層的錯誤補上完整的可用值（頂層依種類組與類別分支，pydantic 的錯誤只帶該支的值；
    4-L10a）：缺 ``layout`` 或版型不存在時列出可用的版型；``category`` 列出全部類別；``kind``
    列出這個版型可選的種類。"""
    layouts = tuple(f for f, _ in models.layouts)
    kinds = dict(models.kinds)
    layout = data.get("layout") if isinstance(data, dict) else None
    out: list[ProposalError] = []
    for error in errors:
        fixed = error
        if error.path == "" and error.code == "union_tag_not_found" and layouts:
            fixed = replace(error, path="layout", message="缺少版型欄位 layout", allowed=layouts)
        elif error.path == "" and error.code == "union_tag_invalid" and layouts:
            message = f"未知的版型 {layout!r}"
            fixed = replace(error, path="layout", message=message, allowed=layouts)
        elif error.path == "category" and error.code == "literal_error":
            fixed = replace(error, allowed=CATEGORIES)
        elif error.path == "kind" and error.code == "literal_error" and layout in kinds:
            fixed = replace(error, allowed=kinds[layout])
        out.append(fixed)
    return out


ELEMENT_ADVICE = "。請在技能 JSON 的頂層填 element: {elements}（效果裡各自的 element 不算）"
"""要求技能元素的互斥規則（``require.elements_any``，例 ``terrain_needs_earth``）附給 LLM 的建議
（LB-2：原訊息只說「技能元素要是 earth」，Gemma 只改效果的 element、頂層不填，連三次一樣）。"""
MAIN_DAMAGE_ADVICE = (
    "。replace_effect.index 請改成主傷害以外的效果位置（從 0 起算），或改用 add_effect 加一個效果"
)
"""變奏換掉主傷害時的建議（LB-2）。"""
SECONDARY_ADVICE = "。請刪掉多出的附帶效果（核心效果以外的都算），或改用附帶效果上限較高的骨架"
"""``skeleton.secondary_count`` 的建議（LB-2）。"""
RANGE_DELTA_ADVICE = (
    "。請拿掉這個變奏的 range_delta（改用 shape、element 或 add_effect），"
    "或把技能形狀改成有數字射程的形狀"
)
"""變奏的 ``range_delta`` 配上沒有數字射程的形狀時的建議（LB-2b：初版重測 Gemma 在 line、cone 上
連三次填 range_delta）。LB-2c（玩法 PM 4.1.18 第 5 點）：拿掉「例：single 並填數字 range」——
LB-2b 重測新出現 4 次 ``single 的 range 收到 0``，疑似這個例子引出來的。"""
PASSIVE_AFFECTS_ADVICE = '。請在這個效果明寫 "affects": "self"（沒寫時預設是 enemies 或 allies）'
"""``passive.affects`` 的建議（LB-2b：初版重測 Q12 的 Gemma 效果不寫 ``affects``，三次一樣）。"""
PASSIVE_BUDGET_ADVICE = (
    "。被動的可用預算看觸發的係數：請換係數高的觸發（這個稀有度最高的是 {trigger}），或換便宜的狀態"
)
"""被動技能 ``budget.over`` 的建議（LB-2c，玩法 PM 4.1.18 第 3 點：「換係數高的觸發或便宜的狀態」；
LB-2b 重測 Q12 的 Gemma 用「移動後」觸發＋統御狀態超預算 131%，同一份答案交三次）。``{trigger}``
是技能稀有度能用的觸發裡係數最高的（:func:`~trpg.skillgen.proposal_passive.best_trigger`）。"""


def _element_requirements(library: ContentLibrary) -> dict[str, tuple[str, ...]]:
    return {
        f"exclusion.{rule.id}": tuple(str(e) for e in rule.require.elements_any)
        for rule in library.exclusions.rules
        if rule.require is not None and rule.require.elements_any
    }


def _passive_budget_advice(library: ContentLibrary, skill: SkillDef) -> str:
    usable = [
        t.id
        for t in library.ruleset.skill_triggers.triggers
        if rarity_rank(t.min_rarity) <= rarity_rank(skill.rarity)
    ]
    best = best_trigger(library, usable)
    if best is None:
        return "。被動的可用預算看觸發的係數：請換係數高的觸發，或換便宜的狀態"
    name = str(best["event"]) + (f"（n: {best['n']}）" if "n" in best else "")
    return PASSIVE_BUDGET_ADVICE.format(trigger=name)


def advise(
    error: ProposalError, library: ContentLibrary, skill: SkillDef | None = None
) -> ProposalError:
    """在錯誤訊息後面附上可照做的修法（LB-2；只改給 LLM 的說明，不改判定）：

    - 要求技能元素的互斥規則：頂層的 ``element`` 要填哪個值（:data:`ELEMENT_ADVICE`）。
    - 變奏換掉主傷害：``replace_effect.index`` 換位置或改用 ``add_effect``。
    - ``skeleton.secondary_count``：刪掉多的附帶效果或換骨架。
    - 變奏的 ``range_delta`` 配上沒有數字射程的形狀（LB-2b）：拿掉 ``range_delta`` 或換形狀。
    - ``passive.affects``（LB-2b）：明寫 ``affects: self``。
    - 被動技能（``skill`` 有給、``kind: passive``）的 ``budget.over``（LB-2c）：換係數高的觸發或
      便宜的狀態（:data:`PASSIVE_BUDGET_ADVICE`）。
    """
    extra = ""
    elements = _element_requirements(library).get(error.code)
    if elements:
        extra = ELEMENT_ADVICE.format(elements=" 或 ".join(f'"{e}"' for e in elements))
    elif error.path.endswith("replace_effect.index") and "主傷害" in error.message:
        extra = MAIN_DAMAGE_ADVICE
    elif error.code == "skeleton.secondary_count":
        extra = SECONDARY_ADVICE
    elif error.path.endswith(".range_delta") and "range_delta" in error.message:
        extra = RANGE_DELTA_ADVICE
    elif error.code == "passive.affects":
        extra = PASSIVE_AFFECTS_ADVICE
    elif error.code == "budget.over" and skill is not None and skill.kind == "passive":
        extra = _passive_budget_advice(library, skill)
    return replace(error, message=error.message + extra) if extra else error


def evaluate_proposal(
    raw: str | Mapping[str, Any],
    models: ProposalModels,
    library: ContentLibrary,
    ctx: ProposalContext,
    *,
    fill: NumberFiller | None = None,
) -> ProposalResult:
    """驗證一份提議：提議格式 → 補數值並轉成技能 → 跨檔案驗證與預算（``validate_skill``）。

    ``fill`` 補數值；省略時用保守的最小補值（``proposal_numbers.minimal_filler``，不保證通過預算；
    正式流程由 4-L5 傳入預算器）。"""
    try:
        data: object = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except json.JSONDecodeError as exc:
        error = ProposalError("proposal", "", "json_invalid", f"不是合法的 JSON：{exc.msg}")
        return ProposalResult(None, (error,))
    if isinstance(data, Mapping):  # IP-1（06 6.36）：LLM 不帶 icon_prop，輸出裡有就丟掉、不算錯
        data = drop_icon_prop(data)
    try:
        proposal = TypeAdapter(models.skill).validate_python(data)
    except ValidationError as exc:
        errors = _layout_hints(_pydantic_errors(exc, "proposal", data), models, data)
        return ProposalResult(None, tuple(errors))
    try:
        skill = to_skill_def(proposal, ctx, fill or minimal_filler(library), library)
    except ValidationError as exc:
        errors = _pydantic_errors(exc, "skill", data)
        return ProposalResult(None, tuple(advise(e, library) for e in errors))
    violations = validate_skill(skill, library)
    if violations:
        rule_errors = tuple(
            advise(_rule_error(v.rule, v.message, skill), library, skill) for v in violations
        )
        return ProposalResult(None, rule_errors)
    extra = [*_unheld_errors(skill, ctx), *_topic_errors(skill, ctx, library)]
    return ProposalResult(None, tuple(extra)) if extra else ProposalResult(skill, ())


def _topic_errors(
    skill: SkillDef, ctx: ProposalContext, library: ContentLibrary
) -> list[ProposalError]:
    """題目要求（Phase 4-L6）：帶到題目的關鍵字、用到指定的核心原語。沒有題目要求時不檢查。"""
    errors: list[ProposalError] = []
    if ctx.keywords:
        found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
        lacking = tuple(k for k in ctx.keywords if k not in found)
        if lacking:
            errors.append(
                ProposalError(
                    stage="rules",
                    path="effects",
                    code="keyword.required",
                    message=f"技能必須製造或利用題目的關鍵字 {'、'.join(lacking)}，但提議沒有帶到",
                    allowed=lacking,
                )
            )
    if ctx.weapon_class is not None:
        problem = weapon_problem(skill, ctx.weapon_class, ctx.held or {})
        if problem is not None:
            errors.append(
                ProposalError(
                    stage="rules",
                    path="weapon_req",
                    code="weapon.incompatible",
                    message=f"技能與主角的武器不相容：{problem}",
                )
            )
    core = ctx.core_primitive
    if core is not None and all(e.type != core for e in skill.effects):
        errors.append(
            ProposalError(
                stage="rules",
                path="effects",
                code="core.required",
                message=f"題目指定核心原語 {core}：effects 裡必須有 type 為 {core} 的效果",
                allowed=(core,),
            )
        )
    return errors


def _unheld_errors(skill: SkillDef, ctx: ProposalContext) -> list[ProposalError]:
    """武器親和條件指定了主角沒拿的裝備（Phase 3I-5）：加成永遠不會成立，退回重提。"""
    if ctx.held is None:
        return []
    allowed = tuple(sorted(ctx.held))
    return [
        ProposalError(
            stage="rules",
            path="effects",
            code="gear.not_held",
            message=f"武器親和只能指定主角手上的裝備，收到 {cond.weapon}",
            allowed=allowed,
        )
        for cond in skill_condition_specs(skill)
        if cond.type == WIELDING_WEAPON and cond.weapon not in ctx.held
    ]


def feedback_payload(errors: Sequence[ProposalError], attempt: int, max_attempts: int) -> str:
    """重試時附給 LLM 的錯誤（JSON 文字；放在指令區之外的資料區）。"""
    body = {
        "attempt": attempt,
        "max_attempts": max_attempts,
        "errors": [e.to_json() for e in errors],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)
