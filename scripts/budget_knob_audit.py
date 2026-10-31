"""預算旋鈕查修（BAL-11a，只量＋建議；不改 content 與預設行為，覆寫只在本腳本的記憶體內）。

子命令（輸出 Markdown 到標準輸出；相同參數必得逐字相同）：

- ``retune``：重調不進預算窗（BAL-10a 第 7 點）。對「第二個關鍵字」「蓄力」「恆久」「觸發」類模板，
  在第 1 次與第 2 次閃現（同 ``flash_minor_coverage.py`` 的分支）逐次套用；結構合法但重調失敗的，
  依調整器的最終狀態拆成原因（最弱仍超過上限、強度下限高於窗頂、階梯跳過窗、旋鈕到頂、占比限制、
  沒有可調旋鈕、驗證或縮放後未達下限）。``--override`` 換一種覆寫重跑，``--csv`` 存逐次結果，
  ``compare`` 對照兩份 CSV 算救回幾次。
- ``stance``：姿態冷卻折抵（BAL-10c 後）：哪些姿態路徑（閃現各次、完整技能、升階重配）還會帶冷卻、
  吃到冷卻折抵，以及「進入冷卻 ±1」換到的形態／姿態幅度。
- ``ladder``：舊階梯改細（接續段武器倍率、形態幅度、修正傷害）——用覆寫跑覆蓋掃描
  （``flash_minor_coverage.py`` 的 ``scan_chunk``），``--base`` 給現狀的 CSV 對照。
- ``snapshot``：覆寫下重算行為快照（``tests/skillgen/fixtures/refactor_3wr2.json``），
  列出會變的筆數。

用法::

    uv run python scripts/budget_knob_audit.py retune --jobs 8 --csv out/base.csv
    uv run python scripts/budget_knob_audit.py retune --jobs 8 --override floor_relax_20 --csv x.csv
    uv run python scripts/budget_knob_audit.py compare out/base.csv floor_relax_20=x.csv
    uv run python scripts/budget_knob_audit.py stance --jobs 8
    uv run python scripts/budget_knob_audit.py ladder --override fine_all --jobs 8 --base base.csv
    uv run python scripts/budget_knob_audit.py snapshot --override fine_all --jobs 8
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import ModuleType
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.sim.parallel import run_tasks
from trpg.skillgen import budget, composer_tuning, evolution, flash_derive, flash_ops
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.complete import complete_strength
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.flash_category import allowed_categories, template_kinds
from trpg.skillgen.flash_offer import (
    FlashRequest,
    UsageSource,
    make_offer,
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_offer import choose as flash_choose
from trpg.skillgen.flash_state import SkillFlash, Variation, acquire
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.skill_tier import retier
from trpg.skillgen.usage import SkillUsage

ROOT = Path(__file__).resolve().parent.parent
LIST_MAX = 20
SKILLS_MAX = 6
_power = evolution.budget_power


def _load(name: str) -> ModuleType:
    """借用同資料夾的腳本（覆蓋掃描；它再借用稽核腳本）。"""
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass 要從 sys.modules 找到模組
    spec.loader.exec_module(module)
    return module


def _orig(module: ModuleType, name: str) -> Any:
    """模組目前的屬性（覆寫前先存下來）。"""
    return vars(module)[name]


def _swap(module: ModuleType, name: str, value: Any) -> None:
    """覆寫模組屬性（只在本行程）。"""
    setattr(module, name, value)


coverage = _load("flash_minor_coverage")
audit = coverage.audit

RETUNE_TEMPLATES = (
    "keyword_imbue",
    "keyword_exploit",
    "support_keyword",
    "cost_charge",
    "extend_duration",
    "trigger_range",
    "trigger_range_wide",
    "trigger_potency",
    "trigger_cap",
)
"""第 1 項查的模板（BAL-10a 第 7 點：結構合法但重調失敗的大宗）。"""


# ---------------------------------------------------------------------------
# 覆寫（只在本行程的記憶體內；工作行程各自安裝）
# ---------------------------------------------------------------------------

_OP_STACK: list[tuple[str, str]] = []
"""目前正在套用的（小變化模板 ID, 變化鍵）（巢狀：重推歷程時一筆套一筆）。"""
_TRYING: list[str] = []
"""診斷中正在試的那個變化鍵（重推歷程時套用的前幾筆不記錄）。"""
_INSTALLED: dict[str, bool] = {}


def _in_scope() -> bool:
    return bool(_OP_STACK) and _OP_STACK[-1][0] in RETUNE_TEMPLATES


def _logging() -> bool:
    return _LOG is not None and bool(_OP_STACK) and _OP_STACK[-1][1] in _TRYING


_real_apply_variation: Callable[..., SkillDef | None] = _orig(flash_derive, "apply_variation")


def _tracked_apply_variation(
    library: ContentLibrary, skill: SkillDef, variation: Variation, **kwargs: Any
) -> SkillDef | None:
    template = variation.template if variation.source == "minor" else ""
    _OP_STACK.append((template, variation.key()))
    try:
        return _real_apply_variation(library, skill, variation, **kwargs)
    finally:
        _OP_STACK.pop()


_swap(flash_derive, "apply_variation", _tracked_apply_variation)


def _fine_multipliers(step: int) -> Callable[[ContentLibrary], tuple[int, ...]]:
    """武器倍率階梯：3000‰ 以下每 ``step``‰ 一格（與原階梯合併）。"""

    def ladder(library: ContentLibrary) -> tuple[int, ...]:
        base = evolution.multiplier_ladder(library)
        return tuple(sorted({*base, *range(base[0], 3000, step)}))

    return ladder


def _install_fine_knobs(step: int) -> None:
    """第 1 項覆寫 A：重調的武器倍率改成每 ``step``‰ 一格（只在第 1 項的模板）。"""
    real: Callable[..., list[Knob]] = _orig(evolution, "_knobs")
    ladder = _fine_multipliers(step)

    def knobs(category: str, effects: list[dict[str, Any]], library: ContentLibrary) -> list[Knob]:
        out = real(category, effects, library)
        if not _in_scope():
            return out
        fine = ladder(library)
        return [
            Knob(k.index, k.field, fine, k.weight) if k.field == "multiplier_permille" else k
            for k in out
        ]

    _swap(evolution, "_knobs", knobs)


def _install_floor_relax(permille: int) -> None:
    """第 1 項覆寫 B：強度下限放寬成閃現前分數 × (1 − ‰)（只在第 1 項的模板）。"""
    real: Callable[..., Fraction | None] = _orig(flash_derive, "power_floor")

    def power_floor(
        library: ContentLibrary,
        current: SkillDef,
        variation: Variation,
        replaced: Fraction | None = None,
    ) -> Fraction | None:
        floor = real(library, current, variation, replaced)
        if floor is None or variation.template not in RETUNE_TEMPLATES:
            return floor
        return floor * Fraction(1000 - permille, 1000)

    _swap(flash_derive, "power_floor", power_floor)


def _install_cooldown_offset() -> None:
    """第 1 項覆寫 C：重調多一個旋鈕＝代價折抵（同大變化 ``cost_attempts``：原代價做不出來時試冷卻
    +1、+2；只有主動技、只在第 1 項的模板）。"""
    real: Callable[..., SkillDef | None] = _orig(flash_derive, "retune")

    def retune(
        attempt: dict[str, Any],
        effects: list[dict[str, Any]],
        rng: Any,
        library: ContentLibrary,
        **kw: Any,
    ) -> SkillDef | None:
        done = real(attempt, effects, rng, library, **kw)
        if done is not None or not _in_scope() or attempt.get("kind") != "active":
            return done
        try:
            probe = SkillDef.model_validate({**attempt, "effects": effects})
        except ValueError:
            return None
        for index, cost in enumerate(evolution.cost_attempts(probe)[1:], start=1):
            trial = [dict(e) for e in effects]
            done = real({**attempt, "cost": cost}, trial, rng.fork(f"cd{index}"), library, **kw)
            if done is not None:
                return done
        return None

    _swap(flash_derive, "retune", retune)


def _install_modifier_ladder(step: int) -> None:
    """第 3 項：修正傷害／治療‰（``MODIFIER_LADDER``）每 ``step``‰ 一格（原 50～1000 每 25）。"""
    _swap(flash_ops, "MODIFIER_LADDER", tuple(range(step, 1001, step)))


def _install_followup_ladder(step: int) -> None:
    """第 3 項：接續段武器倍率（BAL-10b 接續段強化類）3000‰ 以下每 ``step``‰ 一格（原每 100）。"""
    real = _orig(flash_ops, "_followup_knob")
    ladder = _fine_multipliers(step)

    def knob(effect: dict[str, Any], library: ContentLibrary) -> tuple[str, tuple[Any, ...]]:
        name, values = real(effect, library)
        return (name, ladder(library)) if name == "multiplier_permille" else (name, values)

    _swap(flash_ops, "_followup_knob", knob)


def _install_fine_all() -> None:
    _install_modifier_ladder(10)
    _install_followup_ladder(25)


def _form_library(library: ContentLibrary, step: int) -> ContentLibrary:
    """第 3 項：形態幅度（``rules.form_magnitudes``）每 ``step``‰ 一格（原每 50）。"""
    values = tuple(range(1000, 2001, step))
    rules = library.flash.rules.model_copy(update={"form_magnitudes": values})
    return dataclasses.replace(library, flash=library.flash.model_copy(update={"rules": rules}))


def _install_modifier_ladder_flash(step: int) -> None:
    """同 :func:`_install_modifier_ladder`，但只在閃現的「強效」（``mod_potency``）用細階梯；
    升階重配、完整技能照舊。"""
    real: Callable[..., Any] = _orig(flash_ops, "_modifier_knobs")
    fine = tuple(range(step, 1001, step))

    def knobs(rules: list[dict[str, Any]], library: ContentLibrary, *, op: str) -> Any:
        if op != "mod_potency":
            return real(rules, library, op=op)
        old = _orig(flash_ops, "MODIFIER_LADDER")
        _swap(flash_ops, "MODIFIER_LADDER", fine)
        try:
            return real(rules, library, op=op)
        finally:
            _swap(flash_ops, "MODIFIER_LADDER", old)

    _swap(flash_ops, "_modifier_knobs", knobs)


def _install_form_flash(step: int) -> None:
    """同 ``form_<step>``，但只在閃現的形態幅度草稿（``_magnitude_drafts``）；
    升階重配、完整技能照舊。"""
    real: Callable[..., Any] = _orig(flash_ops, "_magnitude_drafts")
    cache: dict[int, ContentLibrary] = {}

    def drafts(skill: SkillDef, library: ContentLibrary, upkeep: int, **kw: Any) -> Any:
        fine = cache.setdefault(id(library), _form_library(library, step))
        return real(skill, fine, upkeep, **kw)

    _swap(flash_ops, "_magnitude_drafts", drafts)


def _install_fine_flash() -> None:
    _install_modifier_ladder_flash(10)
    _install_followup_ladder(25)
    _install_form_flash(25)


def _same(library: ContentLibrary) -> ContentLibrary:
    return library


def _nothing() -> None:
    return None


@dataclass(frozen=True, slots=True)
class Override:
    install: Callable[[], None] = _nothing
    library: Callable[[ContentLibrary], ContentLibrary] = _same
    note: str = ""


OVERRIDES: dict[str, Override] = {
    "none": Override(note="現狀"),
    "fine_knobs_25": Override(lambda: _install_fine_knobs(25), note="重調武器倍率每 25‰"),
    "floor_relax_20": Override(lambda: _install_floor_relax(20), note="強度下限 ×0.98"),
    "floor_relax_50": Override(lambda: _install_floor_relax(50), note="強度下限 ×0.95"),
    "cooldown_offset": Override(_install_cooldown_offset, note="多一個旋鈕：冷卻 +1／+2 折抵"),
    "mod_ladder_10": Override(lambda: _install_modifier_ladder(10), note="修正傷害每 10‰"),
    "mod_ladder_5": Override(lambda: _install_modifier_ladder(5), note="修正傷害每 5‰"),
    "followup_ladder_25": Override(lambda: _install_followup_ladder(25), note="接續段倍率每 25‰"),
    "followup_ladder_40": Override(lambda: _install_followup_ladder(40), note="接續段倍率每 40‰"),
    "form_20": Override(library=lambda lib: _form_library(lib, 20), note="形態幅度每 20‰"),
    "form_25": Override(library=lambda lib: _form_library(lib, 25), note="形態幅度每 25‰"),
    "fine_all": Override(
        _install_fine_all,
        library=lambda lib: _form_library(lib, 25),
        note="三個舊階梯一起改細（修正 10‰、接續段 25‰、形態 25‰）",
    ),
    "mod_ladder_10_flash": Override(
        lambda: _install_modifier_ladder_flash(10), note="修正傷害每 10‰（只在閃現）"
    ),
    "form_25_flash": Override(lambda: _install_form_flash(25), note="形態幅度每 25‰（只在閃現）"),
    "form_20_flash": Override(lambda: _install_form_flash(20), note="形態幅度每 20‰（只在閃現）"),
    "fine_flash": Override(
        _install_fine_flash, note="三個舊階梯只在閃現改細（修正 10‰、接續段 25‰、形態 25‰）"
    ),
}


def install(name: str) -> None:
    """安裝覆寫（同一行程只裝一種、只裝一次）。"""
    if name == "none" or _INSTALLED.get(name):
        return
    if _INSTALLED:
        raise RuntimeError(f"同一行程只能裝一種覆寫（已裝 {sorted(_INSTALLED)}）")
    OVERRIDES[name].install()
    _INSTALLED[name] = True


def library_for(name: str) -> ContentLibrary:
    return OVERRIDES[name].library(default_library())


# ---------------------------------------------------------------------------
# 第 1 項：重調失敗的原因
# ---------------------------------------------------------------------------

_real_tune = _orig(evolution, "tune")
_LOG: list[dict[str, Any]] | None = None
"""診斷模式時每次調整器呼叫的結果（``None`` ＝ 不記錄）。"""


def _probe_knobs(ev: Any, knobs: Sequence[Knob], ratio: Fraction, high: Fraction) -> dict[str, Any]:
    """每個還能往上的旋鈕各試一格：超過上限的（階梯跳過窗）、被占比擋的。旋鈕放回原位。"""
    over: list[Fraction] = []
    share = False
    shares = ev.shares
    for knob in knobs:
        if not knob.can_up():
            continue
        knob.pos += 1
        composer_tuning._apply(knob, ev.targets)
        one = ev.ratio()
        if one is not None and one > high:
            over.append(one - ratio)
        elif one is None or ev.shares > shares:
            share = True
        knob.pos -= 1
        composer_tuning._apply(knob, ev.targets)
        ev.ratio()
    if over:
        return {"cause": "階梯跳過窗", "step": min(over)}
    if share:
        return {"cause": "占比限制擋住旋鈕"}
    return {"cause": "旋鈕到頂"}


def _diagnose(  # noqa: PLR0917 - 同調整器的參數
    library: ContentLibrary,
    base: dict[str, Any],
    effects: list[dict[str, Any]],
    knobs: list[Knob],
    extra: Sequence[dict[str, Any]],
    min_ratio: Fraction | None,
    target_ratio: Fraction | None,
) -> dict[str, Any]:
    """調整器失敗後，依旋鈕的最終位置判斷原因（調整器本身不動）。"""
    ev = composer_tuning._Evaluator(library, base, effects, extra)
    low, high = composer_tuning.tuning_bounds(library)
    if min_ratio is not None or target_ratio is not None:
        high = ev.high = Fraction(1)
    ratio = ev.ratio()
    floor = max(low, min_ratio or low)
    info: dict[str, Any] = {"ratio": ratio, "floor": floor, "step": None}
    if ratio is None:
        return {**info, "cause": "草稿不合法（schema／預算器算不出）"}
    if all(k.pos == 0 for k in knobs) and ratio > high:
        return {**info, "cause": "最弱仍超過上限"}
    if ratio >= floor:
        return {**info, "cause": "占比限制（違規未清）"}
    if min_ratio is not None and min_ratio > high:
        return {**info, "cause": "強度下限高於窗頂"}
    if not knobs:
        return {**info, "cause": "沒有可調旋鈕"}
    return {**info, **_probe_knobs(ev, knobs, ratio, high)}


def _logged_tune(
    rng: Any,
    library: ContentLibrary,
    base: dict[str, Any],
    effects: list[dict[str, Any]],
    knobs: list[Knob],
    *,
    extra: Sequence[dict[str, Any]] = (),
    min_ratio: Fraction | None = None,
    target_ratio: Fraction | None = None,
) -> bool:
    ok = _real_tune(
        rng,
        library,
        base,
        effects,
        knobs,
        extra=extra,
        min_ratio=min_ratio,
        target_ratio=target_ratio,
    )
    if _LOG is not None and _logging():
        entry = (
            {"cause": "ok"}
            if ok
            else _diagnose(library, base, effects, knobs, extra, min_ratio, target_ratio)
        )
        _LOG.append(entry)
    return bool(ok)


_swap(evolution, "tune", _logged_tune)


_real_validate: Callable[..., list[Any]] = _orig(evolution, "validate_skill")
_real_rarity = _orig(evolution, "_rarity")
_real_floor_ratio: Callable[..., Fraction | None] = _orig(evolution, "_floor_ratio")
_real_carries = _orig(flash_derive, "_carries")
_VALIDATE = "調整後驗證不過"
_CARRY = "調整成功但沒帶上關鍵字"
_SCORE = "調整後分數低於下限"
_SCHEMA = "草稿 schema 不合法"


def _logged_validate(skill: SkillDef, library: ContentLibrary) -> list[Any]:
    """調整成功後的驗證：記下違規代碼（第一個）。"""
    found = _real_validate(skill, library)
    if _LOG is not None and _logging() and found:
        _LOG.append({"cause": _VALIDATE, "rule": found[0].rule})
    return found


def _logged_rarity(draft: dict[str, Any], effects: list[dict[str, Any]], library: Any) -> str:
    rarity = _real_rarity(draft, effects, library)
    if _LOG is not None and _logging() and rarity == "legendary" != draft.get("rarity"):
        _LOG.append({"cause": "稀有度升傳說"})
    return str(rarity)


def _schema_message(attempt: dict[str, Any], trial: list[dict[str, Any]], library: Any) -> str:
    """草稿為什麼不合法（pydantic 訊息的第一句，去掉數字）。"""
    try:
        skill_budget(SkillDef.model_validate({**attempt, "effects": trial}), library)
    except (ValueError, BudgetError) as exc:
        text = str(exc).splitlines()
        line = next((t for t in text if "error," in t), text[0] if text else "")
        line = line.split("error,", 1)[-1].split(" [", 1)[0].strip()
        return "".join("N" if ch.isdigit() else ch for ch in line)[:40]
    return "?"


def _logged_floor_ratio(
    attempt: dict[str, Any], trial: list[dict[str, Any]], floor: Fraction, library: Any
) -> Fraction | None:
    value = _real_floor_ratio(attempt, trial, floor, library)
    if _LOG is not None and _logging() and value is None:
        _LOG.append({"cause": _SCHEMA, "rule": _schema_message(attempt, trial, library)})
    return value


def _logged_carries(skill: SkillDef, variation: Variation, library: ContentLibrary) -> bool:
    ok = bool(_real_carries(skill, variation, library))
    if _LOG is not None and _logging() and not ok:
        _LOG.append({"cause": _CARRY})
    return ok


_swap(evolution, "validate_skill", _logged_validate)
_swap(evolution, "_rarity", _logged_rarity)
_swap(evolution, "_floor_ratio", _logged_floor_ratio)
_swap(flash_derive, "_carries", _logged_carries)

_CAUSE_ORDER = (
    "階梯跳過窗",
    "旋鈕到頂",
    "占比限制擋住旋鈕",
    "占比限制（違規未清）",
    "強度下限高於窗頂",
    "最弱仍超過上限",
    "沒有可調旋鈕",
    _CARRY,
    _SCORE,
    _VALIDATE,
    "稀有度升傳說",
    _SCHEMA,
    "其他（沒進調整器）",
)
"""一次變化有多份草稿與多次嘗試時，取最接近成功的原因（依此順序）。"""


def _cause_of(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """一次變化的原因：每份草稿／每次嘗試的結果取最接近成功的那個。調整器成功、但之後驗證不過、
    沒帶上關鍵字或分數低於下限的，各自記成那個原因。"""
    oks = sum(1 for e in entries if e["cause"] == "ok")
    later = sum(1 for e in entries if e["cause"] in (_VALIDATE, _CARRY))
    causes = [e for e in entries if e["cause"] != "ok"]
    if oks > later:
        causes.append({"cause": _SCORE})
    if not causes:
        return {"cause": "其他（沒進調整器）"}
    best = min(causes, key=lambda e: _CAUSE_ORDER.index(e["cause"]))
    if "rule" in best:
        return {**best, "cause": f"{best['cause']}（{best['rule']}）"}
    return best


@dataclass(frozen=True, slots=True)
class Attempt:
    """一次（技能, 角色階級, 種子, 第幾次, 分支, 變化）的套用結果。"""

    origin: str
    skill_id: str
    kind: str
    skeleton: str
    role_tier: int
    seed: int
    nth: int
    branch: str
    template: str
    variation: str
    status: str
    """``legal``、``structure``（結構不符）或 ``retune``（重調失敗）。"""
    cause: str = ""
    ratio: str = ""
    floor: str = ""
    step: str = ""

    def key(self) -> tuple[str, ...]:
        return (
            self.origin,
            self.skill_id,
            str(self.role_tier),
            str(self.seed),
            str(self.nth),
            self.branch,
            self.variation,
        )


def _fmt_ratio(value: Fraction | None) -> str:
    return "" if value is None else f"{float(value):.3f}"


def _try_one(
    library: ContentLibrary, request: FlashRequest, current: SkillDef, variation: Variation
) -> tuple[str, dict[str, Any]]:
    global _LOG  # noqa: PLW0603 - 診斷記錄
    _LOG = []
    _TRYING[:] = [variation.key()]
    try:
        legal = try_variation(library, request, variation) is not None
        entries = list(_LOG)
    finally:
        _LOG = None
        _TRYING.clear()
    if legal:
        return "legal", {}
    bonus = library.flash.rules.budget_bonus_permille(len(request.state.records) + 1)
    probe = flash_derive.with_budget_bonus(current, bonus)
    if not flash_derive._minor_drafts(probe, variation, library):
        return "structure", {}
    return "retune", _cause_of(entries)


def _attempts_for(  # noqa: PLR0917
    library: ContentLibrary,
    origin: str,
    skill: SkillDef,
    request: FlashRequest,
    current: SkillDef,
    nth: int,
    branch: str,
) -> list[Attempt]:
    table = library.flash
    before = skill_before(library, request)
    allowed = set(allowed_categories(table, before, major=False))
    source = UsageSource()
    out: list[Attempt] = []
    for template in table.minor:
        if template.id not in RETUNE_TEMPLATES or template.category not in allowed:
            continue
        if before.kind not in template_kinds(table, template):
            continue
        if (request.tier or skill.tier) < template.min_tier:
            continue
        for variation in source._variants(library, request, template, before):
            status, info = _try_one(library, request, current, variation)
            out.append(
                Attempt(
                    origin=origin,
                    skill_id=skill.id,
                    kind=str(current.kind),
                    skeleton=str(current.skeleton),
                    role_tier=request.tier or skill.tier,
                    seed=request.seed,
                    nth=nth,
                    branch=branch,
                    template=template.id,
                    variation=variation.key(),
                    status=status,
                    cause=info.get("cause", ""),
                    ratio=_fmt_ratio(info.get("ratio")),
                    floor=_fmt_ratio(info.get("floor")),
                    step=_fmt_ratio(info.get("step")),
                )
            )
    return out


def retune_chunk(
    context: tuple[str, ContentLibrary], task: tuple[list[tuple[str, SkillDef]], int]
) -> list[Attempt]:
    name, library = context
    install(name)
    subjects, seeds = task
    out: list[Attempt] = []
    for origin, skill in subjects:
        for role_tier in range(max(1, skill.tier), coverage.MAX_ROLE_TIER + 1):
            current = audit.at_role_tier(library, skill, role_tier)
            for seed in range(1, seeds + 1):
                state0 = acquire(skill.id)
                request1 = coverage._request(skill, state0, role_tier, seed)
                out += _attempts_for(library, origin, skill, request1, current, 1, "-")
                offer = make_offer(library, request1)
                for index, option in enumerate(offer.options):
                    state1, picked = flash_choose(state0, offer, index)
                    request2 = coverage._request(skill, state1, role_tier, seed)
                    branch = option.variation.key()
                    out += _attempts_for(library, origin, skill, request2, picked, 2, branch)
    return out


def _subjects(
    library: ContentLibrary, skills: str | None, board_seeds: int
) -> list[tuple[str, SkillDef]]:
    ids = None if skills is None else [s for s in skills.split(",") if s]
    return list(coverage._subjects(library, ids, board_seeds))


def _chunks[T](items: Sequence[T], jobs: int) -> list[list[T]]:
    n = max(1, jobs * 4)
    return [list(items[i::n]) for i in range(n) if items[i::n]]


ATTEMPT_FIELDS = (
    "origin",
    "skill_id",
    "kind",
    "skeleton",
    "role_tier",
    "seed",
    "nth",
    "branch",
    "template",
    "variation",
    "status",
    "cause",
    "ratio",
    "floor",
    "step",
)


def attempts_csv(rows: Sequence[Attempt]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(ATTEMPT_FIELDS)
    for r in rows:
        writer.writerow([getattr(r, f) for f in ATTEMPT_FIELDS])
    return buf.getvalue()


def read_attempts(path: str) -> list[Attempt]:
    with Path(path).open(encoding="utf-8", newline="") as fh:
        out = []
        for row in csv.DictReader(fh):
            ints = {k: int(row[k]) for k in ("role_tier", "seed", "nth")}
            out.append(Attempt(**{**row, **ints}))  # type: ignore[arg-type]
        return out


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return [*lines, ""]


def _quantiles(values: Sequence[float]) -> list[str]:
    xs = sorted(values)
    return [f"{xs[min(len(xs) - 1, int(len(xs) * p))]:.3f}" for p in (0, 0.5, 0.9)] + [
        f"{xs[-1]:.3f}"
    ]


BUCKETS = (
    "超過上限",
    "低於強度下限",
    "階梯跳過窗",
    "沒有可調旋鈕",
    "骨架占比",
    "調整後驗證不過",
    "草稿 schema 不合法",
)
"""規格的四類原因（前四個）＋量測多出來的三類。"""


def bucket(cause: str) -> str:
    """細原因 → 大類。"""
    if cause.startswith("最弱仍超過上限") or cause.endswith("budget.over）"):
        return "超過上限"
    if cause.startswith(("強度下限高於窗頂", "調整後分數低於下限", "旋鈕到頂")):
        return "低於強度下限"
    if cause.startswith("占比限制"):
        return "骨架占比"
    if cause.startswith(("階梯跳過窗", "沒有可調旋鈕", _SCHEMA)):
        return next(b for b in BUCKETS if cause.startswith(b))
    return "調整後驗證不過"


def _bucket_table(fails: Sequence[Attempt]) -> list[str]:
    templates = [t for t in RETUNE_TEMPLATES if any(r.template == t for r in fails)]
    grid = Counter((bucket(r.cause), r.template) for r in fails)
    body = [
        [b, *[str(grid[(b, t)]) for t in templates], str(sum(grid[(b, t)] for t in templates))]
        for b in BUCKETS
    ]
    sums = [str(sum(grid[(b, t)] for b in BUCKETS)) for t in templates]
    body.append(["合計", *sums, str(len(fails))])
    return _table(["大類", *templates, "合計"], body)


def _cause_rank(cause: str) -> int:
    return next((i for i, c in enumerate(_CAUSE_ORDER) if cause.startswith(c)), len(_CAUSE_ORDER))


def by_template(rows: Sequence[Attempt]) -> list[Attempt]:
    """同一次請求、同一個模板的所有變化（關鍵字、元素……）併成一列：有任一合法就算合法（出題只要
    一個）；否則有重調失敗就算重調失敗，原因取最接近成功的那個變化。"""
    groups: dict[tuple[str, ...], list[Attempt]] = defaultdict(list)
    for r in rows:
        groups[(*r.key()[:-1], r.template)].append(r)
    out = []
    for _key, rs in sorted(groups.items()):
        statuses = {r.status for r in rs}
        status = next(s for s in ("legal", "retune", "structure") if s in statuses)
        pick = min(
            (r for r in rs if r.status == status), key=lambda r: (_cause_rank(r.cause), r.variation)
        )
        out.append(dataclasses.replace(pick, variation="*", status=status))
    return out


def report_retune(rows: Sequence[Attempt], top: int = 12) -> list[str]:
    status_v = Counter(r.status for r in rows)
    grouped = by_template(rows)
    status = Counter(r.status for r in grouped)
    fails = [r for r in grouped if r.status == "retune"]
    lines: list[str] = [
        f"逐變化套用 {len(rows)} 次（合法 {status_v['legal']}、結構不符 {status_v['structure']}、"
        f"重調失敗 {status_v['retune']}）。**下面以「一次請求 × 一個模板」為一次**"
        f"（同模板的各關鍵字、元素併成一次，有任一合法就算合法）："
        f"{len(grouped)} 次，合法 {status['legal']}、"
        f"結構不符 {status['structure']}、**重調失敗 {status['retune']}**。\n",
        "### 大類 × 模板（重調失敗次數）",
        "",
    ]
    lines += _bucket_table(fails)
    lines += ["### 細原因 × 模板（重調失敗次數）", ""]
    templates = [t for t in RETUNE_TEMPLATES if any(r.template == t for r in fails)]
    causes = sorted({r.cause for r in fails}, key=lambda c: (_cause_rank(c), c))
    grid = Counter((r.cause, r.template) for r in fails)
    body = [
        [c, *[str(grid[(c, t)]) for t in templates], str(sum(grid[(c, t)] for t in templates))]
        for c in causes
    ]
    sums = [str(sum(grid[(c, t)] for c in causes)) for t in templates]
    body.append(["合計", *sums, str(len(fails))])
    lines += _table(["原因", *templates, "合計"], body)
    lines += ["### 原因 × 種類＃第幾次", ""]
    grid2 = Counter((r.cause, f"{r.kind}#{r.nth}") for r in fails)
    cols = sorted({f"{r.kind}#{r.nth}" for r in fails})
    lines += _table(["原因", *cols], [[c, *[str(grid2[(c, k)]) for k in cols]] for c in causes])
    jumps = [r for r in fails if r.cause == "階梯跳過窗" and r.step and r.ratio and r.floor]
    if jumps:
        lines += ["### 階梯跳過窗：最小一格的比例增量與離下限的缺口", ""]
        lines += _table(
            ["", "最小", "中位", "90%", "最大"],
            [
                ["一格增量", *_quantiles([float(r.step) for r in jumps])],
                ["缺口", *_quantiles([float(r.floor) - float(r.ratio) for r in jumps])],
            ],
        )
    lines += [f"### 最常見的技能（前 {top}）", ""]
    by_skill = Counter(r.skill_id for r in fails)
    causes_by: dict[str, Counter[str]] = defaultdict(Counter)
    for r in fails:
        causes_by[r.skill_id][r.cause] += 1
    ranked = sorted(by_skill.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    lines += _table(
        ["技能", "次數", "主要原因"],
        [
            [s, str(n), "、".join(f"{c} {m}" for c, m in causes_by[s].most_common(2))]
            for s, n in ranked
        ],
    )
    lines += ["### 骨架", ""]
    by_skel = Counter(r.skeleton for r in fails)
    total_skel = Counter(r.skeleton for r in grouped if r.status != "structure")
    lines += _table(
        ["骨架", "重調失敗", "結構合法的次數", "失敗率"],
        [
            [s, str(n), str(total_skel[s]), f"{n * 100 / total_skel[s]:.0f}%"]
            for s, n in sorted(by_skel.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    )
    return lines


def report_compare(base: Sequence[Attempt], other: Sequence[Attempt], name: str) -> list[str]:
    """兩份結果的對照（「一次請求 × 一個模板」；相同鍵、分支也相同才比較）。"""
    seeds = {r.seed for r in other}
    base = [r for r in base if r.seed in seeds]  # 覆寫只跑部分種子時，只比那些種子
    after = {(*r.key(), r.template): r for r in by_template(other)}
    saved: Counter[str] = Counter()
    saved_t: Counter[str] = Counter()
    broke = missing = 0
    grouped = by_template(base)
    for r in grouped:
        o = after.get((*r.key(), r.template))
        if o is None:
            missing += 1
            continue
        if r.status == "retune" and o.status == "legal":
            saved[r.cause] += 1
            saved_t[r.template] += 1
        if r.status == "legal" and o.status != "legal":
            broke += 1
    total = Counter(r.cause for r in grouped if r.status == "retune")
    note = OVERRIDES[name].note if name in OVERRIDES else ""
    lines = [
        f"#### 覆寫 `{name}`（{note}）",
        "",
        f"救回 **{sum(saved.values())}／{sum(total.values())}** 次；原本合法變不合法 {broke} 次；"
        f"分支不同無法對照 {missing} 次。\n",
    ]
    tb: Counter[str] = Counter()
    sb: Counter[str] = Counter()
    for c, n in total.items():
        tb[bucket(c)] += n
    for c, n in saved.items():
        sb[bucket(c)] += n
    lines += _table(
        ["大類", "原本失敗", "救回"], [[b, str(tb[b]), str(sb[b])] for b in BUCKETS if tb[b]]
    )
    lines.append("救回的模板：" + "、".join(f"{t} {n}" for t, n in sorted(saved_t.items())) + "\n")
    return lines


# ---------------------------------------------------------------------------
# 第 2 項：姿態冷卻折抵
# ---------------------------------------------------------------------------

_STANCE_LOG: list[tuple[str, str, int]] | None = None
"""（路徑, 技能 ID, 冷卻）——預算器被問到帶冷卻的姿態時記下。"""
_PATH: list[str] = []
_real_allowance = _orig(budget, "_allowance_parts")


def _probe_allowance(skill: SkillDef, *args: Any) -> Any:
    if _STANCE_LOG is not None and skill.kind == "stance" and skill.cost.cooldown:
        _STANCE_LOG.append((_PATH[-1] if _PATH else "?", skill.id, skill.cost.cooldown))
    return _real_allowance(skill, *args)


_swap(budget, "_allowance_parts", _probe_allowance)


@contextmanager
def _path(name: str) -> Iterator[None]:
    _PATH.append(name)
    try:
        yield
    finally:
        _PATH.pop()


def _walk_flash(
    library: ContentLibrary, skill: SkillDef, tier: int, seed: int, depth: int
) -> Iterator[tuple[int, SkillDef, str]]:
    """閃現各分支走到第 ``depth`` 次（每次所有選項；第 3 次是大變化／轉型）。
    產出（第幾次, 技能, 模板路徑）；    每一層最多留 12 個分支（控制時間）。"""
    frontier: list[tuple[SkillFlash, str]] = [(acquire(skill.id), "")]
    for nth in range(1, depth + 1):
        nxt: list[tuple[SkillFlash, str]] = []
        for state, trail in frontier:
            request = FlashRequest(
                base=skill, state=state, usage=SkillUsage(), seed=seed, tier=tier
            )
            offer = make_offer(library, request)
            for index, option in enumerate(offer.options):
                new_state, picked = flash_choose(state, offer, index)
                label = f"{trail}/{option.variation.template}"
                yield nth, picked, label
                nxt.append((new_state.model_copy(update={"used": True}), label))
        frontier = nxt[:12]


type StanceHit = tuple[str, str, int, str, int, int]
"""（路徑, 技能, 角色階級, 模板路徑, 冷卻, 第幾次）。"""


def stance_chunk(
    context: tuple[str, ContentLibrary], task: tuple[list[tuple[str, SkillDef]], int, int]
) -> list[StanceHit]:
    """姿態路徑上出現冷卻的地方（閃現各分支、完整技能、升階重配）。"""
    global _STANCE_LOG  # noqa: PLW0603
    name, library = context
    install(name)
    subjects, seeds, depth = task
    found: list[StanceHit] = []
    for _origin, skill in subjects:
        for tier in range(max(1, skill.tier), coverage.MAX_ROLE_TIER + 1):
            for seed in range(1, seeds + 1):
                for nth, picked, trail in _walk_flash(library, skill, tier, seed, depth):
                    if picked.kind == "stance" and picked.cost.cooldown:
                        found.append(("閃現", skill.id, tier, trail, picked.cost.cooldown, nth))
        _STANCE_LOG = []
        with _path("完整技能"):
            done = complete_strength(library, skill)
        lifted: list[SkillDef] = []
        with _path("升階重配"):
            for t in range(skill.tier + 1, coverage.MAX_ROLE_TIER + 1):
                lifted.append(retier(library, lifted[-1] if lifted else skill, t))
        for path, _sid, cd in _STANCE_LOG:
            found.append((path, skill.id, 0, "-", cd, 0))
        _STANCE_LOG = None
        for s in (done, *lifted):
            if s.kind == "stance" and s.cost.cooldown:
                found.append(("結果帶冷卻", skill.id, s.tier, "-", s.cost.cooldown, 0))
    return found


def _stance_gain(library: ContentLibrary, skill: SkillDef) -> dict[str, Any]:
    """「進入冷卻 ±1」換到的幅度：冷卻 0／1／2 時，同一份預算（比例 ≤ 1.00）能放的最高幅度。"""
    index = flash_ops._stance_index(skill, library)
    if index is None:
        return {}
    form = skill.form_id is not None
    rules = library.flash.rules
    values = rules.form_magnitudes if form else rules.stance_magnitudes
    out: dict[str, Any] = {"form": form, "start": skill.effects[index].magnitude_permille or 1000}
    data = skill.model_dump(mode="json", exclude_none=True)
    for cd in (0, 1, 2):
        best = None
        for value in values:
            effects = [dict(e) for e in data["effects"]]
            effects[index]["magnitude_permille"] = value
            cost = {k: v for k, v in data.get("cost", {}).items() if k != "cooldown"}
            if cd:
                cost["cooldown"] = cd
            try:
                probe = SkillDef.model_validate({**data, "cost": cost, "effects": effects})
                ratio = skill_budget(probe, library).ratio
            except (ValueError, BudgetError):
                break
            if ratio <= 1:
                best = value
        out[f"cd{cd}"] = best
    return out


def report_stance(library: ContentLibrary, found: Sequence[StanceHit]) -> list[str]:
    lines = ["### 姿態路徑上出現冷卻的地方", ""]
    if not found:
        lines.append("沒有：所有姿態路徑都不帶冷卻（不會吃到冷卻折抵）。\n")
    else:
        groups: dict[tuple[str, int], list[StanceHit]] = defaultdict(list)
        for f in found:
            groups[(f[0], f[5])].append(f)
        body = []
        for (path, nth), fs in sorted(groups.items()):
            skills = sorted({f[1] for f in fs})
            templates = Counter(f[3].rsplit("/", 1)[-1] for f in fs)
            body.append(
                [
                    path,
                    str(nth),
                    str(len(fs)),
                    "、".join(skills[:SKILLS_MAX]) + ("…" if len(skills) > SKILLS_MAX else ""),
                    "、".join(f"{t} {n}" for t, n in templates.most_common(4)),
                    "、".join(str(c) for c in sorted({f[4] for f in fs})),
                ]
            )
        lines += _table(
            ["路徑", "第幾次", "次數", "技能", "最後一步的模板", "冷卻"],
            body,
        )
    lines += [
        "### 「進入冷卻 ±1」換到的幅度（內建姿態、自己的階級；比例 ≤ 1.00 的最高幅度）",
        "",
    ]
    body = []

    def fmt(v: int | None) -> str:
        return "-" if v is None else str(v)

    for skill in sorted(library.skills.values(), key=lambda s: s.id):
        if skill.kind != "stance":
            continue
        g = _stance_gain(library, skill)
        if not g:
            continue
        d1 = None if g["cd0"] is None or g["cd1"] is None else g["cd1"] - g["cd0"]
        body.append(
            [
                skill.id,
                "形態" if g["form"] else "姿態",
                str(g["start"]),
                fmt(g["cd0"]),
                fmt(g["cd1"]),
                fmt(g["cd2"]),
                fmt(d1),
            ]
        )
    lines += _table(
        ["技能", "種類", "目前幅度", "冷卻 0", "冷卻 1", "冷卻 2", "冷卻 +1 換到"],
        body,
    )
    return lines


# ---------------------------------------------------------------------------
# 第 3 項：覆蓋掃描（覆寫下）
# ---------------------------------------------------------------------------


def ladder_chunk(
    context: tuple[str, ContentLibrary], task: tuple[list[tuple[str, SkillDef]], int]
) -> list[Any]:
    name, library = context
    install(name)
    return list(coverage.scan_chunk(library, task))


type CoverageKey = tuple[str, str, int]


def read_coverage(path: str) -> dict[CoverageKey, tuple[int, int]]:
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return {
            (r["origin"], r["skill_id"], int(r["role_tier"])): (int(r["n1_min"]), int(r["n2_min"]))
            for r in csv.DictReader(fh)
        }


def report_ladder(
    base: dict[CoverageKey, tuple[int, int]],
    after: dict[CoverageKey, tuple[int, int]],
    groups_of: dict[CoverageKey, str],
) -> list[str]:
    short = coverage.SHORT
    groups: dict[str, list[CoverageKey]] = defaultdict(list)
    for key in sorted(after):
        groups[groups_of[key]].append(key)

    def count(table: dict[CoverageKey, tuple[int, int]], keys: list[CoverageKey], i: int) -> int:
        if i < 0:
            return sum(1 for k in keys if k in table and min(table[k]) < short)
        return sum(1 for k in keys if k in table and table[k][i] < short)

    body = [
        [
            group,
            str(len(keys)),
            *[f"{count(base, keys, i)} → {count(after, keys, i)}" for i in (-1, 0, 1)],
        ]
        for group, keys in sorted(groups.items())
    ]
    lines = _table(["類別", "列數", "不足列", "第 1 次 <2", "第 2 次 <2"], body)
    changed = [k for k in sorted(after) if k in base and base[k] != after[k]]
    better = [k for k in changed if min(after[k]) >= short > min(base[k])]
    worse = [k for k in changed if min(base[k]) >= short > min(after[k])]
    lines.append(
        f"選項數有變的列 {len(changed)}；脫離不足 {len(better)}、新進不足 {len(worse)}。\n"
    )
    if better:
        lines.append("脫離不足：" + "、".join(f"{k[1]}@{k[2]}" for k in better) + "\n")
    if worse:
        lines.append("新進不足：" + "、".join(f"{k[1]}@{k[2]}" for k in worse) + "\n")
    return lines


def _group_of(row: Any, library: ContentLibrary) -> str:
    skill = library.skills.get(row.skill_id)
    if row.kind == "stance":
        form = skill is not None and skill.form_id is not None
        return f"{row.origin} 姿態" + ("（形態）" if form else "")
    if row.kind == "modifier":
        return f"{row.origin} 修正型被動"
    if "複合技" in row.tags.split(","):
        return f"{row.origin} 複合技"
    return f"{row.origin} {row.kind}"


# ---------------------------------------------------------------------------
# 行為快照（覆寫下）
# ---------------------------------------------------------------------------


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _guarded(fn: Callable[[], str]) -> str:
    try:
        return fn()
    except Exception as exc:  # 失敗本身也是要對照的行為
        return f"error:{type(exc).__name__}"


def _flash_digest(lib: ContentLibrary, key: str) -> str:
    skill_id, seed_s, tier_s = key.split("@")
    seed, tier = int(seed_s), int(tier_s)
    state: SkillFlash = acquire(skill_id).model_copy(update={"used": True})
    base = lib.skills[skill_id]
    parts: list[str] = []
    for pick in range(3):
        request = FlashRequest(base, state, SkillUsage(), seed, tier=tier)
        try:
            offer = make_offer(lib, request)
        except Exception as exc:
            parts.append(f"error:{type(exc).__name__}")
            break
        parts.append(_digest(offer.model_dump_json()))
        if not offer.options:
            break
        state, _ = flash_choose(state, offer, (seed + pick) % len(offer.options))
        state = state.model_copy(update={"used": True})
    return "/".join(parts)


def snapshot_chunk(
    context: tuple[str, ContentLibrary], task: list[tuple[str, str]]
) -> list[tuple[str, str, str]]:
    """（類別, 鍵, 摘要）——同 ``tests/skillgen/test_refactor_3wr2.py`` 的算法，但用覆寫後的內容。"""
    name, lib = context
    install(name)
    out: list[tuple[str, str, str]] = []
    for kind, key in task:
        if kind == "complete":

            def whole(key: str = key) -> str:
                return _digest(complete_strength(lib, lib.skills[key]).model_dump_json())

            value = _guarded(whole)
        elif kind == "retier":
            skills: list[SkillDef] = [lib.skills[key]]

            def step(tier: int, skills: list[SkillDef] = skills) -> str:
                skills.append(retier(lib, skills[-1], tier))
                return _digest(skills[-1].model_dump_json())

            value = "/".join([_guarded(lambda: step(2)), _guarded(lambda: step(3))])
        else:
            value = _flash_digest(lib, key)
        out.append((kind, key, value))
    return out


def _complete_power(context: tuple[str, ContentLibrary], task: list[str]) -> list[tuple[str, str]]:
    """完整技能的預算分數（看強度是否變）。"""
    name, lib = context
    install(name)
    out = []
    for key in task:

        def power(key: str = key) -> str:
            return f"{float(_power(complete_strength(lib, lib.skills[key]), lib)):.4f}"

        out.append((key, _guarded(power)))
    return out


def run_snapshot(name: str, jobs: int) -> list[str]:
    path = ROOT / "tests/skillgen/fixtures/refactor_3wr2.json"
    fixture = json.loads(path.read_text(encoding="utf-8"))
    tasks = [
        (kind, key) for kind in ("complete", "retier", "flash") for key in sorted(fixture[kind])
    ]
    library = library_for(name)
    parts = run_tasks(snapshot_chunk, (name, library), _chunks(tasks, jobs), jobs=jobs)
    changed: dict[str, list[str]] = defaultdict(list)
    for kind, key, value in (x for p in parts for x in p):
        if fixture[kind][key] != value:
            changed[kind].append(key)
    lines = [
        f"#### 覆寫 `{name}`（{OVERRIDES[name].note}）",
        "",
        f"行為快照會變：完整技能 {len(changed['complete'])}／{len(fixture['complete'])}、"
        f"升階重配 {len(changed['retier'])}／{len(fixture['retier'])}、"
        f"閃現出題 {len(changed['flash'])}／{len(fixture['flash'])}。\n",
    ]
    for kind in ("complete", "retier", "flash"):
        if changed[kind]:
            keys = sorted(changed[kind])
            lines.append(
                f"- {kind}：" + "、".join(keys[:LIST_MAX]) + ("…" if len(keys) > LIST_MAX else "")
            )
    if changed["complete"]:
        keys = sorted(changed["complete"])
        before_parts = run_tasks(
            _complete_power, ("none", default_library()), _chunks(keys, jobs), jobs=jobs
        )
        after_parts = run_tasks(_complete_power, (name, library), _chunks(keys, jobs), jobs=jobs)
        before = dict(x for p in before_parts for x in p)
        after = dict(x for p in after_parts for x in p)
        diffs = [(k, before[k], after[k]) for k in keys if before[k] != after[k]]
        lines.append(
            f"- 完整技能預算分數有變 {len(diffs)} 招："
            + "、".join(f"{k} {b}→{a}" for k, b, a in diffs[:12])
        )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("retune", "stance", "ladder", "snapshot"):
        p = sub.add_parser(cmd)
        p.add_argument("--override", default="none", choices=sorted(OVERRIDES))
        p.add_argument("--jobs", type=int, default=1)
        p.add_argument("--skills", help="只測這些內建技能 ID（逗號分隔；給了就不測白板）")
        p.add_argument("--seeds", type=int, default=2)
        p.add_argument("--board-seeds", type=int, default=6)
        p.add_argument("--csv")
        if cmd == "stance":
            p.add_argument("--depth", type=int, default=3)
        if cmd == "retune":
            p.add_argument("--from-csv", help="從之前存的逐次 CSV 重出報表")
        if cmd == "ladder":
            p.add_argument("--base", help="對照的覆蓋 CSV（現狀）")
    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("base")
    cmp_.add_argument("others", nargs="+", help="覆寫名=CSV 路徑")
    return parser


def _write_csv(path: str | None, text: str) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8", newline="")


def _cmd_retune(args: argparse.Namespace, library: ContentLibrary) -> list[str]:
    subjects = _subjects(library, args.skills, args.board_seeds)
    if args.from_csv:  # 只重出報表（不重跑）
        rows = read_attempts(args.from_csv)
    else:
        tasks = [(c, args.seeds) for c in _chunks(subjects, args.jobs)]
        parts = run_tasks(retune_chunk, (args.override, library), tasks, jobs=args.jobs)
        rows = sorted((x for p in parts for x in p), key=lambda r: (*r.key(), r.template))
        _write_csv(args.csv, attempts_csv(rows))
    head = (
        f"覆寫 `{args.override}`；受測 {len(subjects)} 個技能或配方、每階 {args.seeds} 個種子。\n"
    )
    return [head, *report_retune(rows)]


def _cmd_stance(args: argparse.Namespace, library: ContentLibrary) -> list[str]:
    subjects = [
        s for s in _subjects(library, args.skills, args.board_seeds) if s[1].kind == "stance"
    ]
    tasks = [(c, args.seeds, args.depth) for c in _chunks(subjects, args.jobs)]
    parts = run_tasks(stance_chunk, (args.override, library), tasks, jobs=args.jobs)
    found = sorted(x for p in parts for x in p)
    head = (
        f"受測姿態 {len(subjects)} 個（內建＋白板）、每階 {args.seeds} 個種子、"
        f"閃到第 {args.depth} 次（每層最多 12 個分支）。\n"
    )
    return [head, *report_stance(library, found)]


def _cmd_ladder(args: argparse.Namespace, library: ContentLibrary) -> list[str]:
    subjects = _subjects(library, args.skills, args.board_seeds)
    tasks = [(c, args.seeds) for c in _chunks(subjects, args.jobs)]
    parts = run_tasks(ladder_chunk, (args.override, library), tasks, jobs=args.jobs)
    rows = sorted((r for p in parts for r in p), key=lambda r: (r.origin, r.skill_id, r.role_tier))
    after = {(r.origin, r.skill_id, r.role_tier): (r.n1_min, r.n2_min) for r in rows}
    groups = {(r.origin, r.skill_id, r.role_tier): _group_of(r, library) for r in rows}
    _write_csv(args.csv, coverage.to_csv(rows))
    out = [f"覆寫 `{args.override}`（{OVERRIDES[args.override].note}）；{len(rows)} 列。\n"]
    if args.base:
        out += report_ladder(read_coverage(args.base), after, groups)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(newline="\n")  # Windows 也輸出 LF
    if args.cmd == "compare":
        base = read_attempts(args.base)
        out: list[str] = []
        for item in args.others:
            name, path = item.split("=", 1)
            out += report_compare(base, read_attempts(path), name)
    elif args.cmd == "snapshot":
        out = run_snapshot(args.override, args.jobs)
    else:
        library = library_for(args.override)
        commands = {"retune": _cmd_retune, "stance": _cmd_stance, "ladder": _cmd_ladder}
        out = commands[args.cmd](args, library)
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
