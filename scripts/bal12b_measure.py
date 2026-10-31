"""BAL-12b 技能資料階梯與小變化第二段（只量＋建議）。

不改 content 與預設行為；覆寫只在本腳本的記憶體內。子命令（輸出 Markdown 到標準輸出；相同參數必得
逐字相同）：

- ``overcap``：B-3W-5。完整技能（:func:`~trpg.skillgen.complete.complete_strength`）+150‰ 上限下仍
  超過的技能：逐步重走爬升，找出「把分數推過上限的那一步」（哪個旋鈕、從幾格到幾格），拆成原因；
  再試覆寫（完整技能專用的修正幅度細階梯、「大幅超過就停在 +120‰ 以下最接近的一階」），列每招
  前後值與行為快照（``tests/skillgen/fixtures/refactor_3wr2.json`` 的完整技能那一組）會變幾筆。
- ``duration``：B-3W-4。點數固定的狀態／表面白板逐階升階重配，看持續回合、預算比例、實用比例
  （超過一般戰鬥輪數的回合不算），與「升階改加強度」「加層數參數」兩種做法的帳面值。
- ``minor``：小變化第二段。讀 BAL-11b 的覆蓋 CSV，第 2 次選項 < 2 的列依結構分組、列原因，
  建議補的模板與預估可救幾列（``--retune-csv`` 給 ``budget_knob_audit.py retune`` 的逐次結果時，
  加上重調失敗的大類）。

用法::

    uv run python scripts/bal12b_measure.py overcap
    uv run python scripts/bal12b_measure.py duration --seeds 4
    uv run python scripts/bal12b_measure.py minor --retune-csv retune_short.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen import complete
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.flash_derive import with_budget_bonus
from trpg.skillgen.random_composer import ComposeError, default_library
from trpg.skillgen.skill_tier import retier
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/skillgen/fixtures/refactor_3wr2.json"
_PERMILLE = 1000
_MAGNITUDES = ("damage_permille", "heal_permille")
TARGET_GAIN = 120
"""完整技能的 +120‰（``complete.budget_permille``）。"""
CAP_GAIN = 150
"""完整技能的上限 +150‰（``complete.cap_permille``）。"""
SMALL_OVER = 200
"""報表分檔：「小幅超過」的上緣。"""
LIST_MAX = 8
MAX_TIER = 3
SHORT = 2
"""選項數少於這個數就算不足（同 ``flash_minor_coverage.py``）。"""
TRAP_ROUNDS_MAX = 6
"""``TrapSpec.rounds`` 的上限。"""


def _table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 第 1 項：完整技能超過 +150‰
# ---------------------------------------------------------------------------


def _leaves(value: Any, prefix: str = "") -> dict[str, Any]:
    """巢狀字典／清單攤平成（路徑, 值）。"""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k in sorted(value):
            out.update(_leaves(value[k], f"{prefix}.{k}" if prefix else str(k)))
        return out
    if isinstance(value, list):
        out = {}
        for i, v in enumerate(value):
            out.update(_leaves(v, f"{prefix}[{i}]"))
        return out
    return {prefix: value}


_IGNORED = frozenset({"budget_bonus_permille"})


def _diff(before: SkillDef, after: SkillDef) -> list[tuple[str, Any, Any]]:
    a = _leaves(before.model_dump(mode="json"))
    b = _leaves(after.model_dump(mode="json"))
    keys = sorted(set(a) | set(b))
    return [(k, a.get(k), b.get(k)) for k in keys if a.get(k) != b.get(k) and k not in _IGNORED]


def _gain(power: Fraction, base: Fraction) -> int:
    return int((power / base - 1) * _PERMILLE)


@dataclass(frozen=True, slots=True)
class Step:
    path: str
    before: Any
    after: Any
    gain: int  # 這一步之後的 ‰


@dataclass(frozen=True, slots=True)
class Climb:
    skill_id: str
    kind: str
    category: str
    gain: int  # 現狀（照 complete_strength）
    capped_gain: int  # 只走不超過上限的步子停在哪
    steps: tuple[Step, ...]  # 超過上限那一次的完整爬升


def _walk(
    library: ContentLibrary, skill: SkillDef, cap: Fraction | None
) -> tuple[SkillDef, Fraction, list[Step]]:
    rules = library.flash.rules.complete
    base = complete.complete_power(skill, library)
    target = base * Fraction(_PERMILLE + rules.budget_permille, _PERMILLE)
    current = with_budget_bonus(skill, rules.budget_permille)
    power = complete.complete_power(current, library)
    steps: list[Step] = []
    for _ in range(complete._MAX_STEPS):
        if power >= target:
            break
        found = complete._next_step(library, rules, current, target, cap)
        if found is None:
            break
        changes = _diff(current, found[0])
        path = "、".join(c[0] for c in changes) or "(無)"
        old = "、".join(str(c[1]) for c in changes)
        new = "、".join(str(c[2]) for c in changes)
        current, power = found
        steps.append(Step(path, old, new, _gain(power, base)))
    return current, power, steps


def climb(library: ContentLibrary, skill: SkillDef) -> Climb:
    rules = library.flash.rules.complete
    base = complete.complete_power(skill, library)
    cap = base * Fraction(_PERMILLE + rules.cap_permille, _PERMILLE)
    _, capped_power, _ = _walk(library, skill, cap)
    after = complete.complete_strength(library, skill)
    gain = complete.complete_gain_permille(skill, after, library)
    steps: list[Step] = []
    if gain > rules.cap_permille:
        _, _, steps = _walk(library, skill, None)
    return Climb(
        skill.id, skill.kind, skill.category, gain, _gain(capped_power, base), tuple(steps)
    )


def _knob_name(path: str) -> str:
    """路徑（``effects[0].dice``）→ 旋鈕名（``dice``）；修正規則的 change 另標。"""
    leaf = path.rsplit(".", maxsplit=1)[-1]
    if path.startswith("modifiers"):
        return f"修正 {leaf}"
    if path.startswith("followup"):
        return f"接續段 {leaf}"
    if path.startswith("cost") or leaf in ("ap_cost", "stance_upkeep"):
        return f"減代價 {leaf}"
    return leaf


CAUSE_NOTES = {
    "dice": "骰子一階就超過",
    "multiplier_permille": "武器倍率一階就超過",
    "修正 damage_permille": "修正幅度階梯 25‰（小幅度時一格比例大）",
    "修正 heal_permille": "修正幅度階梯 25‰（小幅度時一格比例大）",
    "duration": "持續回合 +1（整數，一格比例大）",
    "distance": "距離 +1",
    "stacks": "層數 +1",
}


def _cause(c: Climb, cap: int) -> tuple[str, str]:
    """（旋鈕, 超過那一步「前 → 後」）。"""
    over = next((s for s in c.steps if s.gain > cap), None)
    if over is None:
        return "(不明)", ""
    names = sorted({_knob_name(p) for p in over.path.split("、")})
    return "＋".join(names), f"{over.before} → {over.after}"


# ---- 覆寫（只在本行程） ----------------------------------------------------

_real_strength_knobs = vars(complete)["strength_knobs"]
_real_complete_strength = complete.complete_strength


def _fine_modifier_knobs(step: int) -> Callable[..., list[Knob]]:
    """完整技能專用：修正型被動的傷害／治療幅度改成每 ``step``‰（升階重配、閃現照舊）。"""
    ladder = tuple(range(step, 1001, step))

    def knobs(skill: SkillDef, draft: Any, library: ContentLibrary) -> list[Knob]:
        out: list[Knob] = _real_strength_knobs(skill, draft, library)
        if skill.kind != "modifier":
            return out
        n = len(draft[1])
        return [
            Knob(k.index, k.field, ladder, k.weight)
            if k.index >= n and k.field in _MAGNITUDES
            else k
            for k in out
        ]

    return knobs


def _stop_below(threshold: int) -> Callable[[ContentLibrary, SkillDef], SkillDef]:
    """超過上限的結果若比原本多 > ``threshold``‰，改用「只走不超過上限的步子」停下的版本
    （＝ +120‰ 以下最接近的一階）。"""

    def strength(library: ContentLibrary, skill: SkillDef) -> SkillDef:
        rules = library.flash.rules.complete
        base = complete.complete_power(skill, library)
        target = base * Fraction(_PERMILLE + rules.budget_permille, _PERMILLE)
        cap = base * Fraction(_PERMILLE + rules.cap_permille, _PERMILLE)
        start = with_budget_bonus(skill, rules.budget_permille)
        capped, power = complete._climb(library, rules, start, target, cap)
        if power >= target:
            return capped
        over = complete._climb(library, rules, start, target, None)[0]
        if complete.complete_gain_permille(skill, over, library) > threshold:
            return capped
        return over

    return strength


@dataclass(frozen=True, slots=True)
class Override:
    note: str
    knob_step: int | None = None
    threshold: int | None = None


OVERRIDES: dict[str, Override] = {
    "none": Override("現狀"),
    "mod10": Override("修正幅度每 10‰（只在完整技能）", knob_step=10),
    "mod5": Override("修正幅度每 5‰（只在完整技能）", knob_step=5),
    "stop170": Override("超過 +170‰ 就停在 +120‰ 以下", threshold=170),
    "stop200": Override("超過 +200‰ 就停在 +120‰ 以下", threshold=200),
    "stop250": Override("超過 +250‰ 就停在 +120‰ 以下", threshold=250),
    "mod5_stop170": Override("修正每 5‰＋超過 +170‰ 停", knob_step=5, threshold=170),
    "mod5_stop200": Override("修正每 5‰＋超過 +200‰ 停", knob_step=5, threshold=200),
}


def _swap(name: str, value: Any) -> None:
    """覆寫 :mod:`~trpg.skillgen.complete` 的屬性（只在本行程）。"""
    setattr(complete, name, value)


@contextmanager
def installed(name: str) -> Iterator[None]:
    spec = OVERRIDES[name]
    try:
        if spec.knob_step is not None:
            _swap("strength_knobs", _fine_modifier_knobs(spec.knob_step))
        if spec.threshold is not None:
            _swap("complete_strength", _stop_below(spec.threshold))
        yield
    finally:
        _swap("strength_knobs", _real_strength_knobs)
        _swap("complete_strength", _real_complete_strength)


def gains(library: ContentLibrary, name: str) -> dict[str, tuple[int, str]]:
    """每招完整技能的（多幾 ‰, 行為快照摘要）。"""
    out: dict[str, tuple[int, str]] = {}
    with installed(name):
        for sid in sorted(library.skills):
            skill = library.skills[sid]
            try:
                after = complete.complete_strength(library, skill)
            except Exception as exc:  # 失敗本身也是行為
                out[sid] = (0, f"error:{type(exc).__name__}")
                continue
            gain = complete.complete_gain_permille(skill, after, library)
            out[sid] = (gain, _digest(after.model_dump_json()))
    return out


def _bucket(g: int) -> str:
    if g < TARGET_GAIN:
        return "< 120"
    if g <= CAP_GAIN:
        return "120–150"
    if g <= SMALL_OVER:
        return "151–200"
    return "> 200"


def report_overcap(library: ContentLibrary, names: Sequence[str]) -> list[str]:
    cap = library.flash.rules.complete.cap_permille
    climbs = [climb(library, library.skills[s]) for s in sorted(library.skills)]
    over = sorted((c for c in climbs if c.gain > cap), key=lambda c: (-c.gain, c.skill_id))
    lines = [
        "## 1. 完整技能 +150‰ 上限下仍超過（B-3W-5）",
        "",
        f"內建技能 {len(climbs)} 招；超過 +{cap}‰ 的 **{len(over)}** 招。",
        "「超過的那一步」＝不限上限重爬時第一個讓分數超過上限的步子；「只走上限內」＝只走不超過",
        "上限的步子時停在哪（即「+120‰ 以下最接近的一階」）。",
        "",
        "### 原因（依超過那一步的旋鈕）",
        "",
    ]
    by_cause: dict[str, list[Climb]] = {}
    causes: dict[str, tuple[str, str]] = {}
    for c in over:
        causes[c.skill_id] = _cause(c, cap)
        by_cause.setdefault(causes[c.skill_id][0], []).append(c)
    rows = []
    for knob, cs in sorted(by_cause.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        rows.append(
            [
                knob,
                CAUSE_NOTES.get(knob, ""),
                len(cs),
                f"{min(c.gain for c in cs)}～{max(c.gain for c in cs)}",
                "、".join(c.skill_id.removeprefix("skill_") for c in cs[:LIST_MAX])
                + ("…" if len(cs) > LIST_MAX else ""),
            ]
        )
    lines += _table(["超過那一步的旋鈕", "說明", "招數", "現狀 ‰", "技能（前 8）"], rows)
    lines.append("")
    kinds = Counter(c.kind for c in over)
    lines.append("技能種類：" + "、".join(f"{k} {n}" for k, n in sorted(kinds.items())) + "。\n")

    base = gains(library, "none")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["complete"]
    mismatch = sorted(k for k in fixture if fixture[k] != base[k][1])
    lines.append(
        f"自我檢查：現狀摘要與行為快照完整技能 {len(fixture)} 筆不一致 {len(mismatch)} 筆。\n"
    )
    results = {name: gains(library, name) for name in names}

    lines += ["### 覆寫結果", ""]
    rows = []
    for name in names:
        res = results[name]
        hist = Counter(_bucket(g) for g, _ in res.values())
        changed = sorted(k for k in fixture if fixture[k] != res[k][1])
        rows.append(
            [
                f"`{name}`",
                OVERRIDES[name].note,
                sum(1 for g, _ in res.values() if g > cap),
                max(g for g, _ in res.values()),
                hist["< 120"],
                hist["120–150"],
                hist["151–200"],
                hist["> 200"],
                len(changed),
            ]
        )
    lines += _table(
        ["覆寫", "說明", "> 150", "最大 ‰", "< 120", "120–150", "151–200", "> 200", "快照變"],
        rows,
    )
    lines += [
        "",
        "「快照變」＝行為快照完整技能那一組會變的筆數（升階重配、閃現出題不經過這裡，不變）。",
        "",
    ]

    lines += ["### 每招前後（‰）", ""]
    header = ["技能", "種類", "超過那一步", "只走上限內", *[f"`{n}`" for n in names]]
    rows = []
    for c in over:
        knob, move = causes[c.skill_id]
        rows.append(
            [
                c.skill_id.removeprefix("skill_"),
                c.kind,
                f"{knob} {move}",
                c.capped_gain,
                *[results[n][c.skill_id][0] for n in names],
            ]
        )
    lines += _table(header, rows)
    lines.append("")
    # 不在超過名單、但覆寫後數值有變的
    others = sorted(
        {
            sid
            for n in names
            for sid, (g, _) in results[n].items()
            if sid not in {c.skill_id for c in over} and g != base[sid][0]
        }
    )
    if others:
        lines += ["沒超過上限、但覆寫後有變的：", ""]
        lines += _table(
            ["技能", *[f"`{n}`" for n in names]],
            [[s.removeprefix("skill_"), *[results[n][s][0] for n in names]] for s in others],
        )
        lines.append("")
    return lines


# ---------------------------------------------------------------------------
# 第 2 項：升階持續回合上限 10（B-3W-4）
# ---------------------------------------------------------------------------

BATTLE_ROUNDS = 6
"""一般遭遇 4–6 輪的上緣（``docs/專案計畫.md`` 平衡目標）：持續超過這個回合數，一般戰鬥用不到。"""


@dataclass(frozen=True, slots=True)
class TierRow:
    recipe: str
    name: str
    kind: str
    seed: int
    tier: int
    effect: str
    shape: str
    duration: int
    ratio: Fraction
    target: Fraction
    control: bool
    complete_gain: int | None  # 3 階時的完整技能（+120‰）實際加了幾 ‰


def _main_effect(skill: SkillDef) -> Any:
    return next(e for e in skill.effects if e.type in ("apply_status", "create_surface"))


def _is_control(effect: Any, library: ContentLibrary) -> bool:
    if effect.type != "apply_status":
        return False
    return library.ruleset.statuses.by_id()[str(effect.status)].control_group is not None


def _fixed_recipes(library: ContentLibrary) -> list[tuple[str, Any]]:
    """點數固定的狀態／表面白板配方（核心效果是施加狀態或產生表面、species basic）。"""
    rules = library.composer.whiteboard
    out = []
    for kind in ("active", "passive", "reaction"):
        for recipe in rules.recipes(kind):
            if recipe.species == "basic" and recipe.effect.get("type") in (
                "apply_status",
                "create_surface",
            ):
                out.append((kind, recipe))
    return out


def budget_ratio(skill: SkillDef, library: ContentLibrary) -> Fraction:
    return skill_budget(skill, library).ratio


def tier_rows(library: ContentLibrary, seeds: int) -> list[TierRow]:
    rows: list[TierRow] = []
    for kind, recipe in _fixed_recipes(library):
        for seed in range(1, seeds + 1):
            try:
                skill = compose_whiteboard(
                    seed, kind=kind, tier=recipe.min_tier, library=library, recipe_id=recipe.id
                )
            except ComposeError:
                continue
            target = budget_ratio(skill, library)
            for tier in range(recipe.min_tier, 4):
                if tier > skill.tier:
                    skill = retier(library, skill, tier)
                effect = _main_effect(skill)
                gain = None
                if tier == MAX_TIER:
                    whole = complete.complete_strength(library, skill)
                    gain = complete.complete_gain_permille(skill, whole, library)
                rows.append(
                    TierRow(
                        recipe.id,
                        recipe.name_zh,
                        kind,
                        seed,
                        tier,
                        str(effect.status or effect.surface),
                        skill.shape.type if skill.shape is not None else "-",
                        effect.duration or 0,
                        budget_ratio(skill, library),
                        target,
                        _is_control(effect, library),
                        gain,
                    )
                )
    return rows


def _ceil(x: Fraction) -> int:
    return -(-x.numerator // x.denominator)


def _useful(r: TierRow) -> Fraction:
    """實用比例：超過一般戰鬥輪數的回合不算。"""
    if r.duration <= BATTLE_ROUNDS:
        return r.ratio
    return r.ratio * Fraction(BATTLE_ROUNDS, r.duration)


def _stacked(r: TierRow) -> str:
    """做法 B：層數 n ＝ ⌈持續 ÷ 6⌉、持續 ⌈持續 ÷ n⌉（點數 × 層數 × 持續 ÷ 預設）→ 帳面比例。"""
    if r.duration <= BATTLE_ROUNDS:
        return "-"
    n = _ceil(Fraction(r.duration, BATTLE_ROUNDS))
    dur = _ceil(Fraction(r.duration, n))
    ratio = r.ratio * Fraction(n * dur, r.duration)
    return f"{n}×{dur}→{float(ratio):.2f}"


def _strengthened(r: TierRow) -> str:
    """做法 A：持續停在 6、每回合強度 ×（持續 ÷ 6）（帳面比例不變、實用比例回到帳面）。"""
    if r.duration <= BATTLE_ROUNDS:
        return "-"
    return f"{BATTLE_ROUNDS}、×{r.duration / BATTLE_ROUNDS:.2f}"


def _span(values: Sequence[str]) -> str:
    uniq = sorted(set(values))
    return uniq[0] if len(uniq) == 1 else "／".join(uniq)


def report_duration(library: ContentLibrary, seeds: int) -> list[str]:
    rows = tier_rows(library, seeds)
    cap = library.budget.retier_growth.stretch["apply_status"]["duration"]
    lines = [
        "## 2. 升階持續回合上限 10（B-3W-4）",
        "",
        f"點數固定的狀態／表面白板配方 {len({r.recipe for r in rows})} 個 × 種子 1～{seeds}，"
        "在最低階級組出後逐階升階重配（`retier`）。",
        "- 比例＝預算比例（驗證窗 0.70～1.00）；目標＝最低階組出時的比例（3W-9b 重配維持比例）。",
        f"- 實用比例＝比例 × min(持續, {BATTLE_ROUNDS}) ÷ 持續：一般遭遇 4～6 輪，"
        "超過的回合帳面算點數、戰鬥裡用不到。",
        f"- A 加強度＝升階改加強度不加回合：持續停在 {BATTLE_ROUNDS}、每回合強度 ×（持續 ÷ "
        f"{BATTLE_ROUNDS}），帳面比例不變，實用比例回到帳面。",
        f"- B 層數＝施加狀態加層數參數：層數 ⌈持續 ÷ {BATTLE_ROUNDS}⌉、持續 ⌈持續 ÷ 層數⌉"
        "（點數 × 層數），列帳面比例。",
        "- 完整 ‰＝3 階這招做成完整技能（+120‰）實際加了多少（持續上限 10 擋住時加不上去）。",
        "",
    ]
    grouped: dict[tuple[str, int], list[TierRow]] = {}
    for r in rows:
        grouped.setdefault((r.recipe, r.tier), []).append(r)
    table = []
    for (recipe, tier), rs in sorted(grouped.items()):
        r0 = rs[0]
        n = len(rs)
        durs = sorted({r.duration for r in rs})
        table.append(
            [
                f"{r0.name}（{recipe}）",
                r0.kind,
                r0.effect + ("・控制" if r0.control else ""),
                tier,
                _span([r.shape for r in rs]),
                str(durs[0]) if len(durs) == 1 else f"{durs[0]}～{durs[-1]}",
                f"{float(sum((r.ratio for r in rs), Fraction(0)) / n):.2f}",
                f"{float(sum((r.target for r in rs), Fraction(0)) / n):.2f}",
                f"{float(sum((_useful(r) for r in rs), Fraction(0)) / n):.2f}",
                _span([_strengthened(r) for r in rs]),
                _span([_stacked(r) for r in rs]),
                "-" if tier != MAX_TIER else _span([str(r.complete_gain) for r in rs]),
            ]
        )
    lines += _table(
        [
            "配方",
            "種類",
            "狀態／表面",
            "階",
            "形狀",
            "持續",
            "比例",
            "目標",
            "實用比例",
            "A 加強度（持續、強度）",
            "B 層數（層×持續→比例）",
            "完整 ‰",
        ],
        table,
    )
    lines.append("")
    at_cap = [r for r in rows if r.duration == cap and not r.control]
    over = [r for r in rows if r.duration > BATTLE_ROUNDS and not r.control]
    short: dict[str, list[int]] = {}
    for r in rows:
        if r.complete_gain is not None:
            short.setdefault(r.recipe, []).append(r.complete_gain)
    lacking = [f"{k} {min(v)}～{max(v)}" for k, v in sorted(short.items()) if min(v) < TARGET_GAIN]
    total = sum(len(v) for v in short.values())
    under = sum(1 for v in short.values() for g in v if g < TARGET_GAIN)
    lines += [
        f"- 持續到頂（{cap}）的（非控制）{len(at_cap)} 列，其中帳面比例低於目標 "
        f"{sum(1 for r in at_cap if r.ratio < r.target)} 列；"
        f"持續 > {BATTLE_ROUNDS}（帳面有、戰鬥用不到）{len(over)}／{len(rows)} 列。",
        f"- 3 階完整技能加不到 +120‰ 的 {under}／{total} 個："
        + ("、".join(lacking) or "無")
        + "。",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# 第 3 項：小變化第二段（BAL-11b 不足名單）
# ---------------------------------------------------------------------------

COVERAGE_CSV = ROOT / "docs/phases/BAL-11/minor_coverage_bal11b.csv"
GROUPS = ("陷阱", "召喚", "常駐", "地面格", "被動與反應", "工具技", "其他")


@dataclass(frozen=True, slots=True)
class ShortRow:
    origin: str
    skill_id: str
    kind: str
    skill_tier: int
    role_tier: int
    n1: int
    n2: int
    reasons: tuple[tuple[str, str], ...]  # （模板, 原因）
    skill: SkillDef | None


def _reasons(text: str) -> tuple[tuple[str, str], ...]:
    out = []
    for part in text.split("; "):
        if ":" in part:
            tpl, why = part.split(":", 1)
            out.append((tpl.strip(), why.strip()))
    return tuple(out)


def _skill_of(library: ContentLibrary, row: dict[str, str]) -> SkillDef | None:
    tier = int(row["skill_tier"])
    if row["origin"] == "builtin":
        skill = library.skills[row["skill_id"]]
    else:
        seed = int(row["skill_id"].removeprefix("skill_rand_"))
        kind = "passive" if row["kind"] == "modifier" else row["kind"]
        kind = "active" if kind == "stance" else kind
        try:
            skill = compose_whiteboard(seed, kind=kind, tier=tier, library=library)
        except ComposeError:
            return None
    role = int(row["role_tier"])
    return retier(library, skill, role) if role > skill.tier else skill


def short_rows(library: ContentLibrary, path: Path) -> list[ShortRow]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for row in rows:
        n1, n2 = int(row["n1_min"]), int(row["n2_min"])
        if n2 >= SHORT:
            continue
        out.append(
            ShortRow(
                row["origin"],
                row["skill_id"],
                row["kind"],
                int(row["skill_tier"]),
                int(row["role_tier"]),
                n1,
                n2,
                _reasons(row["reasons2"] or row["reasons1"]),
                _skill_of(library, row),
            )
        )
    return out


_GROUP_RULES: tuple[tuple[str, Callable[[ShortRow, SkillDef], bool]], ...] = (
    ("陷阱", lambda _r, s: s.trap is not None),
    ("召喚", lambda _r, s: any(e.type == "summon" for e in s.effects)),
    ("常駐", lambda _r, s: s.is_activatable),
    ("地面格", lambda _r, s: s.shape is not None and s.shape.type == "ground_tile"),
    ("被動與反應", lambda r, _s: r.kind in ("passive", "reaction")),
    (
        "工具技",
        lambda r, s: r.kind == "active" and all(e.type != "damage" for e in s.effects),
    ),
)


def group_of(row: ShortRow) -> str:
    """依序判斷的結構分組（見 :data:`GROUPS`）。"""
    skill = row.skill
    if skill is None:
        return "其他"
    return next((g for g, rule in _GROUP_RULES if rule(row, skill)), "其他")


def _short_reason(why: str) -> str:
    return why.split("（", maxsplit=1)[0] if why.startswith("預算窗") else why


@dataclass(frozen=True, slots=True)
class Proposal:
    group: str
    template: str
    note: str
    applies: Callable[[ShortRow], bool]


def _eff(skill: SkillDef, kind: str) -> list[Any]:
    return [e for e in skill.effects if e.type == kind]


_LASTING = ("apply_status", "create_surface", "zone", "create_obstacle", "inscribe")
"""有存在回合、可以「延長」的效果（`summon` 另計）。"""


def _has_duration_target(skill: SkillDef) -> bool:
    """延長的對象（自身狀態、召喚物、場地、障礙、刻印）。"""
    return any(e.type in (*_LASTING, "summon") and e.duration for e in skill.effects)


def _cooldown_or_resource(skill: SkillDef) -> bool:
    """AP 已 1，但還有冷卻（> 1）或法力／耐力可減。"""
    cost = skill.cost
    return (skill.ap_cost or 1) == 1 and bool((cost.cooldown or 0) > 1 or cost.mana or cost.stamina)


def _failed(row: ShortRow, template: str, reason: str) -> bool:
    return any(t == template and w.startswith(reason) for t, w in row.reasons)


def _retune_has(row: ShortRow, templates: Sequence[str], cause: str) -> bool:
    """這一列（內建技能, 角色階級）的重調失敗裡有沒有 ``templates`` 之一的 ``cause``。

    白板沒有重調資料，一律否。"""
    found = RETUNE_CAUSES.get((row.skill_id, row.role_tier), set())
    return any(f"{t}／{cause}" in found for t in templates)


PROPOSALS: tuple[Proposal, ...] = (
    Proposal(
        "陷阱",
        "trap_rounds",
        "陷阱存在回合 +1（`trap.rounds` ≤ 6；觸發型 enter）",
        lambda r: (
            r.skill is not None
            and r.skill.trap is not None
            and r.skill.trap.trigger == "enter"
            and r.skill.trap.rounds < TRAP_ROUNDS_MAX
        ),
    ),
    Proposal(
        "陷阱",
        "trap_area",
        "觸發範圍 single → cross → square3（`trap.shape`）",
        lambda r: (
            r.skill is not None and r.skill.trap is not None and r.skill.trap.shape != "square3"
        ),
    ),
    Proposal(
        "召喚",
        "summon_duration",
        "召喚物存活回合 +1（`extend_duration` 放寬到召喚）",
        lambda r: r.skill is not None and any(e.duration for e in _eff(r.skill, "summon")),
    ),
    Proposal(
        "召喚",
        "cost_light_cd",
        "AP 已 1 時改成冷卻 −1 或資源 −1（`cost_light` 放寬；只減不拿掉）",
        lambda r: r.skill is not None and _cooldown_or_resource(r.skill),
    ),
    Proposal(
        "常駐",
        "rule_param_plus",
        "規則改變的參數 +1 格（例：殘影持續 2 → 3）；源力代價不減、AP 已 1",
        lambda r: r.skill is not None and r.skill.is_activatable,
    ),
    Proposal(
        "地面格",
        "tile_duration",
        "障礙／刻印／表面存在回合 +1（`extend_duration` 放寬）",
        lambda r: (
            r.skill is not None and any(e.type in _LASTING and e.duration for e in r.skill.effects)
        ),
    ),
    Proposal(
        "地面格",
        "tile_radius",
        "地面格 → 十字（同 3W-9b 表面放大；障礙、刻印、衝撞落點）",
        lambda r: (
            r.skill is not None
            and r.skill.shape is not None
            and r.skill.shape.type == "ground_tile"
        ),
    ),
    Proposal(
        "被動與反應",
        "trigger_fine",
        "觸發效果的細旋鈕（骰子之間加 +1 固定值）——不是新模板；救「效果 +」「連發」的階梯跳過窗",
        lambda r: _retune_has(r, ("trigger_potency", "trigger_cap"), "階梯跳過窗"),
    ),
    Proposal(
        "被動與反應",
        "trigger_cooldown_trade",
        "觸發冷卻換強度：觸發後 1～2 回合不再觸發，省下的換成效果（新欄位；每輪上限 ≤ 3、連鎖深度"
        " ≤ 3 照 6.6）；救「最弱仍超過上限」與「沒有可調旋鈕」",
        lambda r: (
            _retune_has(
                r,
                (
                    "trigger_potency",
                    "trigger_cap",
                    "keyword_imbue",
                    "keyword_exploit",
                    "extend_duration",
                ),
                "超過上限",
            )
            or _retune_has(r, ("trigger_potency",), "沒有可調旋鈕")
        ),
    ),
    Proposal(
        "工具技",
        "cost_light_cd",
        "AP 已 1 時改成冷卻 −1 或資源 −1（`cost_light` 放寬；只減不拿掉）",
        lambda r: (
            r.skill is not None
            and _failed(r, "cost_light", "結構不符")
            and _cooldown_or_resource(r.skill)
        ),
    ),
    Proposal(
        "工具技",
        "extend_self",
        "延長擴到自身狀態、召喚物、場地、障礙（`extend_duration` 放寬）",
        lambda r: (
            r.skill is not None
            and _failed(r, "extend_duration", "結構不符")
            and _has_duration_target(r.skill)
        ),
    ),
)

# ---- 試套（不重調）：結構上直接改一格，看在第 2 次閃現的預算上限（+80‰）下合不合法 -------------

SECOND_FLASH_BONUS = 80
"""第 2 次閃現時的預算上限加成（每次 +40‰）。"""
_NEXT_SHAPE = {"single": "cross", "cross": "square3"}


def _edit_trap_rounds(data: dict[str, Any]) -> bool:
    data["trap"]["rounds"] += 1
    return True


def _edit_trap_area(data: dict[str, Any]) -> bool:
    data["trap"]["shape"] = _NEXT_SHAPE[data["trap"]["shape"]]
    return True


def _edit_durations(types: Sequence[str]) -> Callable[[dict[str, Any]], bool]:
    def edit(data: dict[str, Any]) -> bool:
        hit = False
        for e in data["effects"]:
            if e["type"] in types and e.get("duration"):
                e["duration"] += 1
                hit = True
        return hit

    return edit


def _edit_cost_light(data: dict[str, Any]) -> bool:
    cost = data["cost"]
    if (cost.get("cooldown") or 0) > 1:
        cost["cooldown"] -= 1
        return True
    for name in ("mana", "stamina"):
        if cost.get(name):
            cost[name] -= 1
            return True
    return False


TRIALS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "trap_rounds": _edit_trap_rounds,
    "trap_area": _edit_trap_area,
    "summon_duration": _edit_durations(("summon",)),
    "cost_light_cd": _edit_cost_light,
    "tile_duration": _edit_durations(_LASTING),
    "extend_self": _edit_durations((*_LASTING, "summon")),
}


def trial_ok(library: ContentLibrary, skill: SkillDef, template: str) -> bool | None:
    """直接改一格（不重調）後，在 +80‰ 下通過驗證（含預算窗；過弱除外）？``None`` ＝ 沒有試法。"""
    edit = TRIALS.get(template)
    if edit is None:
        return None
    data = skill.model_dump(mode="json")
    if not edit(data):
        return False
    data["budget_bonus_permille"] = SECOND_FLASH_BONUS
    try:
        new = SkillDef.model_validate(data)
        return not validate_skill(new, library)
    except (ValidationError, BudgetError, ValueError, KeyError):
        return False


def _informative(rs: Sequence[ShortRow]) -> Counter[tuple[str, str]]:
    """組內的不合法（模板, 原因）——去掉「整組每一列都結構不符」的模板（那些本來就不是給這類技能的，
    例如接續段類之於非複合技），只留有機會的。"""
    struct = Counter(t for r in rs for t, w in r.reasons if w.startswith("結構不符"))
    noise = {t for t, n in struct.items() if n >= len(rs)}
    return Counter((t, _short_reason(w)) for r in rs for t, w in r.reasons if t not in noise)


RETUNE_BUCKETS = (
    ("最弱仍超過上限", "超過上限"),
    ("階梯跳過窗", "階梯跳過窗"),
    ("沒有可調旋鈕", "沒有可調旋鈕"),
    ("占比限制", "骨架占比"),
)


def _retune_bucket(cause: str) -> str:
    return next((b for p, b in RETUNE_BUCKETS if cause.startswith(p)), "其他")


RETUNE_CAUSES: dict[tuple[str, int], set[str]] = {}
"""（內建技能 ID, 角色階級）→ 重調失敗的「模板／大類」（:func:`load_retune` 填入）。"""


_ATTEMPT_KEY = ("skill_id", "role_tier", "seed", "nth", "branch", "template")


def load_retune(path: Path) -> dict[tuple[str, ...], tuple[str, str]]:
    """讀 ``budget_knob_audit.py retune --csv`` 的逐次結果。

    同一次請求、同模板的各變化併成一次（有一個合法就不算失敗）；回傳失敗的（鍵 → (模板, 大類)），
    並填 :data:`RETUNE_CAUSES`。"""

    status: dict[tuple[str, ...], list[dict[str, str]]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for a in csv.DictReader(fh):
            key: tuple[str, ...] = tuple(a[f] for f in _ATTEMPT_KEY)
            status.setdefault(key, []).append(a)
    fails: dict[tuple[str, ...], tuple[str, str]] = {}
    for key, attempts in sorted(status.items()):
        if any(a["status"] == "legal" for a in attempts):
            continue
        failed = [a for a in attempts if a["status"] == "retune"]
        if not failed:
            continue
        fails[key] = (key[5], _retune_bucket(failed[0]["cause"]))
        RETUNE_CAUSES.setdefault((key[0], int(key[1])), set()).add("／".join(fails[key]))
    return fails


def _retune_table(groups: dict[str, list[ShortRow]], path: Path) -> list[str]:
    """不足名單的內建技能（``budget_knob_audit.py retune --skills …``）：重調失敗依分組 × 大類。"""
    group_of_skill = {
        r.skill_id: g for g, rs in groups.items() for r in rs if r.origin == "builtin"
    }
    counts: dict[str, Counter[str]] = {}
    for key, (template, cause) in load_retune(path).items():
        g = group_of_skill.get(key[0])
        if g is not None:
            counts.setdefault(g, Counter())[f"{template}／{cause}"] += 1
    if not counts:
        return []
    lines = [
        "### 重調失敗的原因（內建技能；`budget_knob_audit.py retune`，種子 1～2）",
        "",
        "以「一次請求 × 一個模板」計（同 BAL-11a）；`12b_retune_short.md` 是完整輸出。",
        "",
    ]
    table = []
    for g in GROUPS:
        if g in counts:
            c = counts[g]
            table.append(
                [g, sum(c.values()), "；".join(f"{k}（{n}）" for k, n in c.most_common(5))]
            )
    lines += _table(["分組", "重調失敗", "主要（模板／大類，次數）"], table)
    lines.append("")
    return lines


def report_minor(library: ContentLibrary, path: Path, retune_csv: Path | None) -> list[str]:
    rows = short_rows(library, path)
    lines = [
        "## 3. 小變化第二段（BAL-11b 不足名單）",
        "",
        f"來源 `{path.relative_to(ROOT).as_posix()}`（BAL-11b 合併後重掃；不足名單 230 列＝"
        f"第 1 或第 2 次 < 2）。這裡看第 2 次選項 < 2 的 **{len(rows)}** 列，依結構分組"
        "（依序判斷：陷阱 → 召喚 → 常駐 → 地面格 → 被動與反應 → 無傷害主動的工具技 → 其他"
        "〔修正型被動、姿態，前幾段處理過〕）。"
        "原因取第 2 次最差分支的不合法模板；表裡去掉了「整組每一列都結構不符」的模板。",
        "",
    ]
    by_group: dict[str, list[ShortRow]] = {g: [] for g in GROUPS}
    for r in rows:
        by_group[group_of(r)].append(r)
    table = []
    for g in GROUPS:
        rs = by_group[g]
        if not rs:
            continue
        top = "；".join(f"{t}：{w}（{n}）" for (t, w), n in _informative(rs).most_common(4))
        table.append(
            [
                g,
                len(rs),
                sum(1 for r in rs if r.n2 == 0),
                len({r.skill_id + r.kind for r in rs}),
                top,
            ]
        )
    lines += _table(
        ["分組", "不足列", "第 2 次 = 0", "技能數", "有機會但不合法的（模板：原因，次數）"], table
    )
    lines.append("")
    kinds = Counter(_short_reason(w).split("/")[0] for r in rows for _, w in r.reasons)
    lines.append("原因大類：" + "、".join(f"{k} {n}" for k, n in kinds.most_common()) + "。\n")
    if retune_csv is not None and retune_csv.exists():
        lines += _retune_table(by_group, retune_csv)

    lines += ["### 建議模板與預估可救列數", ""]
    lines += [
        "- 套得上＝結構上這個模板能用的不足列。",
        f"- 直接套可行＝不重調、直接改一格，在第 2 次閃現的上限（+{SECOND_FLASH_BONUS}‰）下通過驗證"
        "（含預算窗）的列；「-」＝要新規則或要重調，沒有試。",
        "- 預估可救（上限）＝第 2 次選項＋套得上的新模板數 ≥ 2；（保守）＝只算直接套可行的。",
        "",
    ]
    table = []
    for g in GROUPS:
        props = [p for p in PROPOSALS if p.group == g]
        if not props:
            continue
        rs = by_group[g]
        ok: dict[tuple[str, str, int, str], bool] = {}
        for p in props:
            fits = [r for r in rs if p.applies(r)]
            tried = [
                (r, trial_ok(library, r.skill, p.template)) for r in fits if r.skill is not None
            ]
            for r, res in tried:
                ok[(r.skill_id, r.kind, r.role_tier, p.template)] = bool(res)
            feasible = "-" if p.template not in TRIALS else str(sum(1 for _, res in tried if res))
            table.append([g, f"`{p.template}`", p.note, len(fits), feasible, "", ""])
        high = sum(1 for r in rs if r.n2 + sum(1 for p in props if p.applies(r)) >= SHORT)
        low = sum(
            1
            for r in rs
            if r.n2 + sum(1 for p in props if ok.get((r.skill_id, r.kind, r.role_tier, p.template)))
            >= SHORT
        )
        table.append([g, "**合計**", "", "", "", f"{high}／{len(rs)}", f"{low}／{len(rs)}"])
    lines += _table(
        ["分組", "模板", "內容", "套得上", "直接套可行", "預估可救（上限）", "（保守）"], table
    )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("overcap")
    p.add_argument("--overrides", default=",".join(OVERRIDES))
    p = sub.add_parser("duration")
    p.add_argument("--seeds", type=int, default=4)
    p = sub.add_parser("minor")
    p.add_argument("--csv", default=str(COVERAGE_CSV))
    p.add_argument(
        "--retune-csv", help="budget_knob_audit.py retune --csv 的逐次結果（不足名單的內建技能）"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(newline="\n")  # Windows 也輸出 LF
    library = default_library()
    out: list[str] = []
    if args.cmd == "overcap":
        out = report_overcap(library, args.overrides.split(","))
    elif args.cmd == "duration":
        out = report_duration(library, args.seeds)
    elif args.cmd == "minor":
        retune_csv = Path(args.retune_csv) if args.retune_csv else None
        out = report_minor(library, Path(args.csv).resolve(), retune_csv)
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
