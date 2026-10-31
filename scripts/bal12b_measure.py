"""BAL-12b 技能資料階梯與小變化第二段（只量＋建議；不改 content 與預設行為，覆寫只在本腳本的記憶體內）。

子命令（輸出 Markdown 到標準輸出；相同參數必得逐字相同）：

- ``overcap``：B-3W-5。完整技能（:func:`~trpg.skillgen.complete.complete_strength`）+150‰ 上限下仍
  超過的技能：逐步重走爬升，找出「把分數推過上限的那一步」（哪個旋鈕、從幾格到幾格），拆成原因；
  再試覆寫（完整技能專用的修正幅度細階梯、「大幅超過就停在 +120‰ 以下最接近的一階」），列每招前後值與
  行為快照（``tests/skillgen/fixtures/refactor_3wr2.json`` 的完整技能那一組）會變幾筆。
"""

from __future__ import annotations

import argparse
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

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen import complete
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.flash_derive import with_budget_bonus
from trpg.skillgen.random_composer import default_library

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/skillgen/fixtures/refactor_3wr2.json"
_PERMILLE = 1000
_MAGNITUDES = ("damage_permille", "heal_permille")


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
    leaf = path.split(".")[-1]
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

_real_strength_knobs = complete.strength_knobs
_real_complete_strength = complete.complete_strength


def _fine_modifier_knobs(step: int) -> Callable[..., list[Knob]]:
    """完整技能專用：修正型被動的傷害／治療幅度改成每 ``step``‰（升階重配、閃現照舊）。"""
    ladder = tuple(range(step, 1001, step))

    def knobs(skill: SkillDef, draft: Any, library: ContentLibrary) -> list[Knob]:
        out = _real_strength_knobs(skill, draft, library)
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


@contextmanager
def installed(name: str) -> Iterator[None]:
    spec = OVERRIDES[name]
    try:
        if spec.knob_step is not None:
            complete.strength_knobs = _fine_modifier_knobs(spec.knob_step)  # type: ignore[assignment]
        if spec.threshold is not None:
            complete.complete_strength = _stop_below(spec.threshold)
        yield
    finally:
        complete.strength_knobs = _real_strength_knobs
        complete.complete_strength = _real_complete_strength


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
    if g < 120:
        return "< 120"
    if g <= 150:
        return "120–150"
    if g <= 200:
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
                "、".join(c.skill_id.removeprefix("skill_") for c in cs[:8])
                + ("…" if len(cs) > 8 else ""),
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
    lines += ["", "「快照變」＝行為快照完整技能那一組會變的筆數（升階重配、閃現出題不經過這裡，不變）。", ""]

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
# 主程式
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("overcap")
    p.add_argument("--overrides", default=",".join(OVERRIDES))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(newline="\n")  # Windows 也輸出 LF
    library = default_library()
    out: list[str] = []
    if args.cmd == "overcap":
        out = report_overcap(library, args.overrides.split(","))
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
