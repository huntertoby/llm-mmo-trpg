"""數值工坊的技能專用功能（NW-2a）：即時預算、預算例外的附帶改動、分組改預覽與常用預設組。

- **預算**（規格 5.3、T4）：用伺服器啟動時載入的內容庫＋改動套用後的這一招 ``SkillDef`` 算
  ``skill_budget``／``validate_skill``（預算只依賴表，不依賴別招）；數字和 ``trpg skills budget``
  同一個來源。
- **例外清單**（T5）：草稿讓某招超出合格區間 → 寫回時（使用者勾「我確定」）登記進
  ``skill_budget.yaml`` 的 ``known_budget_exceptions``，上方加一行工坊註解；某招（在清單裡的）
  回到區間 → 自動移除。超出區間＝``skill_budget(...).ok`` 為假（和
  ``tests/skillgen/test_range_budget.py`` 的判定相同；變奏的比例不在例外清單管轄內，超出仍是錯）。
- **分組改**（5.4、T6、T7）：一次最多 :data:`MAX_GROUP` 招；必須有篩選或勾選；取整一律整數運算
  （四捨五入、.5 進位），再夾在範圍內；階梯照 ``skill_composer.yaml``。
"""

from __future__ import annotations

import bisect
from collections.abc import Callable, Iterable, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import ValidationError

from trpg.api.tuning.check import Prepared, convert
from trpg.api.tuning.objects import concrete_fields, read_data
from trpg.api.tuning.schemas import (
    TuningBudgetFlag,
    TuningBudgetResult,
    TuningBudgetSegment,
    TuningBudgetVariant,
    TuningChangeIn,
    TuningFieldError,
    TuningGroupFilter,
    TuningGroupIn,
    TuningGroupPreset,
    TuningGroupPreview,
    TuningGroupRow,
    TuningLadders,
    TuningSideChange,
    TuningViolation,
)
from trpg.api.tuning.yaml_patch import (
    EXCEPTIONS_KEY,
    MISSING,
    PatchError,
    lookup,
    patch_exception_list,
)
from trpg.content.library import ContentLibrary
from trpg.content.loader import parse_yaml
from trpg.content.skills import SkillDef
from trpg.content.tuning_fields import TuningTarget, parse_path, target_files
from trpg.shared.fmt import ratio_pct
from trpg.skillgen.budget import BudgetError, BudgetReport, skill_budget
from trpg.skillgen.composer_parts import dice_ladder
from trpg.skillgen.validate import validate_skill

__all__ = [
    "BUDGET_FILE",
    "GROUP_PRESETS",
    "MAX_GROUP",
    "GroupError",
    "add_budget_side_changes",
    "budget_result",
    "group_preview",
    "ladders",
    "out_of_range",
    "permille",
    "select_skills",
]

BUDGET_FILE: Final = "skill_budget.yaml"
MAX_GROUP: Final = 100
_PERMILLE: Final = 1000
_DAMAGE_SITES: Final = ("effects", "followup")

type Verdict = Literal["ok", "over", "weak"]

GROUP_PRESETS: Final = (
    TuningGroupPreset(
        key="t1_ranged_weapon",
        label_zh="1 階遠程武器技",
        filter=TuningGroupFilter(
            tier=[1], category=["weapon"], weapon_req=["ranged"], kind=["active"], enemy_only=False
        ),
    ),
    TuningGroupPreset(
        key="t1_melee_weapon",
        label_zh="1 階近戰武器技",
        filter=TuningGroupFilter(
            tier=[1], category=["weapon"], weapon_req=["melee"], kind=["active"], enemy_only=False
        ),
    ),
    TuningGroupPreset(
        key="t1_arrows_1ap",
        label_zh="1 AP 箭類（1 階、遠程、AP 1、單體傷害）",
        filter=TuningGroupFilter(
            tier=[1],
            category=["weapon"],
            weapon_req=["ranged"],
            ap_cost=[1],
            kind=["active"],
            enemy_only=False,
            single_damage=True,
        ),
    ),
    TuningGroupPreset(
        key="t1_conditional_2ap",
        label_zh="2 AP 條件型（1 階武器技，帶條件段）",
        filter=TuningGroupFilter(
            tier=[1],
            category=["weapon"],
            ap_cost=[2],
            kind=["active"],
            enemy_only=False,
            has_condition=True,
        ),
    ),
)
"""常用預設組（規格 5.4）。"""


class GroupError(ValueError):
    """分組改的參數不對（422，訊息是中文）。"""


def permille(value: Fraction) -> int:
    """比例 → ‰（四捨五入，.5 進位；整數運算）。"""
    scaled = value * _PERMILLE
    return int((scaled.numerator * 2 + scaled.denominator) // (scaled.denominator * 2))


def _verdict(report: BudgetReport) -> Verdict:
    if report.over_budget:
        return "over"
    return "weak" if report.too_weak else "ok"


_VERDICT_ZH: Final = {"ok": "合格", "over": "超出預算", "weak": "過弱", "error": "無法計算"}


def out_of_range(skill: SkillDef, library: ContentLibrary) -> BudgetReport | None:
    """超出合格區間時回預算明細（要登記成例外）；合格或算不出來回 ``None``。裝備附帶的招不算。"""
    if skill.id.startswith("skill_gear_"):
        return None
    try:
        report = skill_budget(skill, library)
    except BudgetError:
        return None
    return None if report.ok else report


def budget_result(
    skill: SkillDef, library: ContentLibrary, exceptions: Iterable[str] | None = None
) -> TuningBudgetResult:
    """一招的預算比例、判定、變奏、複合兩段與違規（同 ``trpg skills budget``）。"""
    rules = library.budget
    known = set(rules.known_budget_exceptions if exceptions is None else exceptions)
    common: dict[str, Any] = {
        "skill_id": skill.id,
        "min_ratio_permille": rules.min_ratio_permille,
        "max_ratio_permille": rules.max_ratio_permille,
        "known_exception": skill.id in known,
        "violations": [
            TuningViolation(rule=v.rule, message_zh=v.message)
            for v in validate_skill(skill, library)
        ],
    }
    try:
        report = skill_budget(skill, library)
    except BudgetError as exc:
        return TuningBudgetResult(
            **common,
            ratio_permille=None,
            ratio_text="—",
            verdict="error",
            verdict_zh=_VERDICT_ZH["error"],
            error_zh=f"無法計算預算：{exc}",
        )
    verdict = _verdict(report)
    return TuningBudgetResult(
        **common,
        ratio_permille=permille(report.ratio),
        ratio_text=ratio_pct(report.ratio),
        verdict=verdict,
        verdict_zh=_VERDICT_ZH[verdict],
        variants=[
            TuningBudgetVariant(
                id=form.id,
                name_zh=form.name_zh,
                ratio_permille=permille(form.report.ratio),
                ratio_text=ratio_pct(form.report.ratio),
                verdict=_verdict(form.report),
            )
            for form in report.variants
        ],
        segments=[
            TuningBudgetSegment(label=s.label, points=f"{float(s.total):.2f}")
            for s in report.segments
        ],
    )


# ---------------------------------------------------------------------------
# 例外清單的附帶改動
# ---------------------------------------------------------------------------


def _skill_of(text: str) -> SkillDef | None:
    try:
        return SkillDef.model_validate(parse_yaml(text.removeprefix("﻿")))
    except (ValidationError, ValueError):
        return None


def add_budget_side_changes(
    prepared: Prepared, content_dir: Path, library: ContentLibrary, date: str
) -> None:
    """草稿改到的技能：超出區間又不在清單 → 登記（``needs_confirm``）；在清單裡又回到區間 →
    移除。產生 ``skill_budget.yaml`` 的改後全文並放進 ``prepared``（寫回時一起 commit）。"""
    budget_path = content_dir / BUDGET_FILE
    raw = budget_path.read_bytes().decode("utf-8")
    current = lookup(parse_yaml(raw.removeprefix("﻿")), (EXCEPTIONS_KEY,))
    listed = set(current) if isinstance(current, list) else set()
    add: dict[str, str] = {}
    remove: list[str] = []
    for rel, text in sorted(prepared.texts.items()):
        if prepared.kinds.get(rel) != "skill":
            continue
        skill = _skill_of(text)
        if skill is None:
            continue
        report = out_of_range(skill, library)
        if report is not None and skill.id not in listed:
            add[skill.id] = ratio_pct(report.ratio)
            verdict: Literal["over", "weak"] = "over" if report.over_budget else "weak"
            prepared.needs_confirm.append(
                TuningBudgetFlag(
                    skill_id=skill.id,
                    name_zh=skill.name_zh,
                    ratio_permille=permille(report.ratio),
                    ratio_text=ratio_pct(report.ratio),
                    verdict=verdict,
                    message_zh=(
                        f"技能 {skill.name_zh}（{skill.id}）預算 {ratio_pct(report.ratio)} "
                        f"{'超出' if verdict == 'over' else '低於'}合格區間，"
                        "要寫回請勾「我確定」（會登記成預算例外）"
                    ),
                )
            )
        elif report is None and skill.id in listed:
            remove.append(skill.id)
    if not add and not remove:
        return
    try:
        text = patch_exception_list(raw, add, remove, date)
    except PatchError as exc:
        prepared.errors.append(
            TuningFieldError(
                file=BUDGET_FILE, path=EXCEPTIONS_KEY, message_zh=f"預算例外清單改不了：{exc}"
            )
        )
        return
    prepared.originals[BUDGET_FILE] = raw
    prepared.texts[BUDGET_FILE] = text
    prepared.side += [
        TuningSideChange(
            file=BUDGET_FILE,
            action="exception_add",
            skill_id=i,
            text_zh=f"預算例外清單加入 {i}（比例 {add[i]}，數值工坊 {date}）",
        )
        for i in sorted(add)
    ]
    prepared.side += [
        TuningSideChange(
            file=BUDGET_FILE,
            action="exception_remove",
            skill_id=i,
            text_zh=f"預算例外清單移除 {i}（回到合格區間）",
        )
        for i in sorted(remove)
    ]


# ---------------------------------------------------------------------------
# 分組改
# ---------------------------------------------------------------------------


def _has_damage_single(skill: SkillDef) -> bool:
    return skill.shape.type == "single" and any(e.type == "damage" for e in skill.effects)


def _matches(skill: SkillDef, f: TuningGroupFilter) -> bool:
    checks: list[tuple[Sequence[Any], Any]] = [
        (f.tier, skill.tier),
        (f.category, skill.category),
        (f.weapon_req, skill.weapon_req),
        (f.ap_cost, skill.ap_cost),
        (f.kind, skill.kind),
        (f.shape, skill.shape.type),
    ]
    if any(allowed and value not in allowed for allowed, value in checks):
        return False
    if f.tags and not set(f.tags) <= set(skill.tags):
        return False
    if f.enemy_only is not None and skill.enemy_only != f.enemy_only:
        return False
    has_condition = skill.condition is not None or any(e.condition for e in skill.effects)
    if f.has_condition is not None and has_condition != f.has_condition:
        return False
    shape_range = skill.shape.range
    ranged = skill.weapon_req == "ranged" or (isinstance(shape_range, int) and shape_range >= 2)  # noqa: PLR2004
    if f.ranged is not None and ranged != f.ranged:
        return False
    return f.single_damage is None or _has_damage_single(skill) == f.single_damage


def select_skills(
    content_dir: Path, target: TuningTarget, request: TuningGroupIn
) -> list[tuple[str, str, Any]]:
    """選到的招（依 ID 排序）：(ID, 相對路徑, 磁碟上的資料)。沒有篩選也沒勾、超過上限、勾了不存在的
    招都丟 :class:`GroupError`。"""
    no_filter = request.filter is None or request.filter.empty()
    if no_filter and not request.skills:
        raise GroupError("至少要選一個篩選條件或手動勾選技能（不提供「全部技能」）")
    files = {p.stem: p for p in target_files(content_dir, target)}
    unknown = sorted(set(request.skills) - set(files))
    if unknown:
        raise GroupError(f"沒有這些技能（或數值工坊不開）：{'、'.join(unknown)}")
    chosen: dict[str, Any] = {}
    for skill_id in sorted(files):
        picked = skill_id in request.skills
        data = None
        if not picked and not no_filter and request.filter is not None:
            data = read_data(files[skill_id])
            picked = _matches(SkillDef.model_validate(data), request.filter)
        if picked:
            chosen[skill_id] = data if data is not None else read_data(files[skill_id])
    if len(chosen) > MAX_GROUP:
        raise GroupError(f"一次最多 {MAX_GROUP} 招（這次 {len(chosen)} 招），請加篩選條件")
    rel = {k: files[k].relative_to(content_dir).as_posix() for k in chosen}
    return [(k, rel[k], chosen[k]) for k in sorted(chosen)]


def _round_div(num: int, den: int) -> int:
    """四捨五入的整數除法（.5 進位；``den`` > 0）。"""
    sign = -1 if num < 0 else 1
    return sign * ((abs(num) * 2 + den) // (den * 2))


_SCALAR_LIMITS: Final[dict[str, tuple[int | None, int | None]]] = {
    "ap_cost": (1, 3),
    "cost.stamina": (0, None),
    "cost.mana": (0, None),
    "cost.cooldown": (1, 6),
}
_ZERO_DEFAULT: Final = frozenset({"cost.stamina", "cost.mana"})


def _clamp(value: int, low: int | None, high: int | None) -> int:
    if low is not None:
        value = max(low, value)
    if high is not None:
        value = min(high, value)
    return value


def _apply_int(current: int, op_kind: str, value: int) -> int | None:
    if op_kind == "set":
        return value
    if op_kind == "add":
        return current + value
    if op_kind == "scale_permille":
        return _round_div(current * value, _PERMILLE)
    return None


def _ladder_step(ladder: Sequence[int], current: int, steps: int) -> int | None:
    """武器倍率階梯上走 ``steps`` 級（不在階梯上時以「比它大／小的最近一級」算第一級）。"""
    if steps == 0:
        return current
    if steps > 0:
        index = bisect.bisect_right(ladder, current) + steps - 1
    else:
        index = bisect.bisect_left(ladder, current) + steps
    return ladder[index] if 0 <= index < len(ladder) else None


def _dice_step(ladder: Sequence[str], current: str, steps: int) -> str | None:
    if current not in ladder:
        return None
    index = list(ladder).index(current) + steps
    return ladder[index] if 0 <= index < len(ladder) else None


type _Edit = tuple[str, Any, Any]
"""(具體路徑, 舊值, 新值)。"""


def _damage_edits(
    data: Any,
    target: TuningTarget,
    request: TuningGroupIn,
    library: ContentLibrary,
    limits: Callable[[str], tuple[int | None, int | None]],
) -> tuple[list[_Edit], str | None]:
    wanted = {"damage_base": False, "damage_conditional": True}.get(request.target)
    edits: list[_Edit] = []
    reasons: list[str] = []
    allowed = {p for _f, p, _l in concrete_fields(data, target)}
    op = request.op
    for path in sorted(allowed):
        parts = parse_path(path)
        if parts[0] not in _DAMAGE_SITES or parts[-1] not in ("multiplier_permille", "dice"):
            continue
        effect = lookup(data, parts[:-1])
        if not isinstance(effect, dict) or effect.get("type") != "damage":
            continue
        if wanted is not None and (effect.get("condition") is not None) != wanted:
            continue
        current = lookup(data, parts)
        new: Any = None
        if parts[-1] == "dice":
            if op.kind != "ladder":
                reasons.append("骰子不能直接乘倍率或加減，請改用 ±級")
                continue
            new = _dice_step(dice_ladder(library.composer.dice), str(current), op.value)
        elif op.kind == "ladder":
            new = _ladder_step(library.composer.multiplier_ladder(), int(current), op.value)
        else:
            raw = _apply_int(int(current), op.kind, op.value)
            new = None if raw is None else _clamp(raw, *limits(path))
        if new is None:
            reasons.append(f"{path}：已到階梯邊界或不在階梯上")
        elif new != current:
            edits.append((path, current, new))
    if edits:
        return edits, None
    return [], "；".join(dict.fromkeys(reasons)) or "沒有符合的傷害效果"


def _scalar_edit(
    data: Any,
    target: TuningTarget,
    request: TuningGroupIn,
    limits: Callable[[str], tuple[int | None, int | None]],
) -> tuple[list[_Edit], str | None]:
    path = request.target
    allowed = {p for _f, p, _l in concrete_fields(data, target)}
    if path not in allowed:
        return [], "這招沒有這個欄位（或數值工坊不開）"
    found = lookup(data, parse_path(path))
    current = None if found is MISSING else found
    if current == "weapon":
        return [], "射程是「武器射程」，不能改"
    if request.op.kind == "ladder":
        return [], "這個欄位沒有階梯，請用設定、加減或倍率"
    base = 0 if current is None and path in _ZERO_DEFAULT else current
    if base is None and request.op.kind != "set":
        return [], "這招沒有寫這個值（例如沒有冷卻），只能用「設定」"
    raw = _apply_int(int(base or 0), request.op.kind, request.op.value)
    low, high = _SCALAR_LIMITS.get(path) or limits(path)
    new = None if raw is None else _clamp(raw, low, high)
    if new is None or new == current or (current is None and new == base):
        return [], "改完和原值相同（或已到邊界）"
    return [(path, current, new)], None


def _ratio_of(data: Any, library: ContentLibrary) -> tuple[int | None, str | None]:
    skill = _skill_of_data(data)
    if skill is None:
        return None, "改完的技能不合 schema"
    try:
        return permille(skill_budget(skill, library).ratio), None
    except BudgetError as exc:
        return None, f"無法計算預算：{exc}"


def _skill_of_data(data: Any) -> SkillDef | None:
    try:
        return SkillDef.model_validate(data)
    except (ValidationError, ValueError):
        return None


def _set_path(data: Any, path: str, value: Any) -> None:
    parts = parse_path(path)
    node = data
    for part in parts[:-1]:
        if isinstance(part, str) and node.get(part) is None:
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def _verdict_of(ratio: int | None, library: ContentLibrary) -> Literal["ok", "over", "weak"]:
    rules = library.budget
    if ratio is not None and ratio > rules.max_ratio_permille:
        return "over"
    if ratio is not None and ratio < rules.min_ratio_permille:
        return "weak"
    return "ok"


def group_preview(
    content_dir: Path,
    target: TuningTarget,
    request: TuningGroupIn,
    library: ContentLibrary,
    limits: Callable[[Any, str], tuple[int | None, int | None]],
) -> TuningGroupPreview:
    """逐招列改動、前後預算比例與跳過原因（不寫任何檔；前端按「放進草稿」才併進草稿）。"""
    rows: list[TuningGroupRow] = []
    for skill_id, rel, data in select_skills(content_dir, target, request):
        name = str(data.get("name_zh") or skill_id)
        before, _err = _ratio_of(data, library)

        def bound(path: str, data: Any = data) -> tuple[int | None, int | None]:
            return limits(data, path)

        if request.target.startswith("damage_"):
            edits, reason = _damage_edits(data, target, request, library, bound)
        else:
            edits, reason = _scalar_edit(data, target, request, bound)
        if not edits:
            rows.append(
                TuningGroupRow(
                    skill_id=skill_id,
                    name_zh=name,
                    changes=[],
                    before_ratio_permille=before,
                    after_ratio_permille=before,
                    verdict="skipped",
                    skipped_reason_zh=reason,
                )
            )
            continue
        after_data = read_data(content_dir / rel)
        for path, _old, new in edits:
            _set_path(after_data, path, new)
        after, error = _ratio_of(after_data, library)
        rows.append(
            TuningGroupRow(
                skill_id=skill_id,
                name_zh=name,
                changes=[
                    TuningChangeIn(file=rel, path=p, old=_plain(o), new=_plain(convert(n, None)))
                    for p, o, n in edits
                ],
                before_ratio_permille=before,
                after_ratio_permille=after,
                verdict="error" if error else _verdict_of(after, library),
                skipped_reason_zh=error,
            )
        )
    return TuningGroupPreview(rows=rows, count=len(rows), max_skills=MAX_GROUP)


def _plain(value: Any) -> Any:
    return list(value) if isinstance(value, tuple) else value


def ladders(library: ContentLibrary) -> TuningLadders:
    """骰子與武器倍率的階梯（由弱到強；同分組改的 ``ladder``，NW-2b「±1 級」用）。"""
    return TuningLadders(
        dice=list(dice_ladder(library.composer.dice)),
        multipliers=list(library.composer.multiplier_ladder()),
    )
