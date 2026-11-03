"""BAL-10d 收束的量測（只量不調；不改任何模板與規則）。

1. **單發倍數**：內建多格傷害主動技（加一個量測用的 3×3 火球）在自己的階級，收成單體／縮小一級各
   閃一次，以及兩種練法閃滿之後，對單一目標的期望傷害相對原招的倍數；單發上限（同階、同 AP 單體
   預算 × ``single_hit_cap_permille``）也換算成原招的倍數。
   - (a) 先收束：第 1 次縮小一級（不行就收成單體）、第 2 次收成單體（已是單體就略過）、
     第 4、5 次蓄力。
   - (b) 先擴範圍：第 1、2 次範圍 +1、第 4 次收成單體、第 5 次蓄力。
   某一次套不上就略過那一次（表裡記「—」），第 3 次（大變化）兩種練法都略過，所以兩邊公平。
2. **AI 選中比例**：``trpg sim flash`` 的自動玩家（均衡為基準，另列集中、全指定、混合）整輪的閃現
   選擇裡，收束佔小變化選擇的比例。

輸出 Markdown 到標準輸出（相同參數必得逐字相同）。

用法::

    uv run python scripts/flash_converge_measure.py --seeds 24 --jobs 8 \
        > docs/phases/BAL-10/converge_bal10d.md
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from fractions import Fraction

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.auto import ALL_FLASH_POLICIES, FlashPolicy
from trpg.sim.flash_report import RunMetrics, run_flash_sim
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_derive import FlashError, derive_chain
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation
from trpg.skillgen.flash_trade import TRADES, cap_points, has_power, target_power
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.validate import validate_skill

SINGLE = "converge_single"
STEP = "converge_step"
CHARGE = "cost_charge"
AREA = "area_plus"
SEED = 7
PLAN_A: tuple[tuple[int, tuple[str, ...]], ...] = (
    (1, (STEP, SINGLE)),
    (2, (SINGLE,)),
    (4, (CHARGE,)),
    (5, (CHARGE,)),
)
PLAN_B: tuple[tuple[int, tuple[str, ...]], ...] = (
    (1, (AREA,)),
    (2, (AREA,)),
    (4, (SINGLE,)),
    (5, (CHARGE,)),
)
_SHORT = {SINGLE: "單", STEP: "縮", CHARGE: "蓄", AREA: "擴"}
_MULTI = frozenset({"line", "cone", "cross", "square3", "ring", "chain", "allies_in_radius"})


def _variation(library: ContentLibrary, template: str) -> Variation:
    found = library.flash.minor_template(template)
    assert found is not None, template
    return Variation(source="minor", template=template, category=found.category)


def _damage(skill: SkillDef, library: ContentLibrary) -> Fraction:
    return target_power(skill, library).get("damage", Fraction(0))


def _derive(library: ContentLibrary, skill: SkillDef, records: list[FlashRecord]) -> SkillDef:
    state = SkillFlash(base_id=skill.id, records=tuple(records))
    return derive_chain(library, skill, state, SEED)[-1]


def run_plan(
    library: ContentLibrary, skill: SkillDef, plan: Sequence[tuple[int, Sequence[str]]]
) -> tuple[SkillDef, str, int]:
    """依練法逐次套用（每次依序試候選、第一個套得上的）；回傳（最後的技能, 路徑說明, 套上幾次）。"""
    records: list[FlashRecord] = []
    current = skill
    path: list[str] = []
    for nth, choices in plan:
        for template in choices:
            if template == SINGLE and current.shape.type == "single":
                continue
            trial = [*records, FlashRecord(nth=nth, variation=_variation(library, template))]
            try:
                current = _derive(library, skill, trial)
            except FlashError:
                continue
            records = trial
            path.append(f"{nth}{_SHORT[template]}")
            break
        else:
            path.append(f"{nth}—")
    return current, " ".join(path), len(records)


def fireball(library: ContentLibrary) -> SkillDef:
    """量測用的 3×3 火球（暴風換成火元素、拿掉吹散）；不放進內容。"""
    data = library.skills["skill_tempest"].model_dump(mode="json")
    data.update(
        id="skill_probe_fireball",
        name_zh="火球（量測用）",
        tags=["fire", "spell", "area"],
        effects=[{"type": "damage", "dice": "2d8", "element": "fire"}],
    )
    skill = SkillDef.model_validate(data)
    problems = validate_skill(skill, library)
    if problems:
        raise SystemExit(f"量測用火球不合法：{problems}")
    return skill


def _subjects(library: ContentLibrary) -> list[SkillDef]:
    builtin = [
        s
        for s in sorted(library.skills.values(), key=lambda s: s.id)
        if s.kind == "active"
        and s.trap is None
        and s.shape.type in _MULTI
        and has_power(s, library)
        and _damage(s, library) > 0
    ]
    return [fireball(library), *builtin]


def _x(value: Fraction, base: Fraction) -> str:
    return "—" if base == 0 else f"{float(value / base):.2f}"


def _once(library: ContentLibrary, skill: SkillDef, template: str) -> SkillDef | None:
    try:
        return _derive(
            library, skill, [FlashRecord(nth=1, variation=_variation(library, template))]
        )
    except FlashError:
        return None


def _full(skill: SkillDef, library: ContentLibrary) -> Fraction:
    """同預算單發：這個結構把剛好一份同階、同 AP 單體預算（``tier_budget`` × AP 係數）花完時，對單一
    目標的期望傷害。附帶效果（狀態、表面……）的點數固定不動、剩下的全部給傷害；拿掉最後一次重調
    抽到的比例、閃現加成與代價折抵的差別，只看結構（收束後的形狀與附帶效果）本身。"""
    report = skill_budget(skill, library)
    damage_points = sum(
        (e.points for e in report.effects if e.type in ("damage", "delayed_damage")), Fraction(0)
    )
    if damage_points == 0:
        return Fraction(0)
    scale = report.total / report.raw  # 條件與協同倍率
    other = report.raw - damage_points
    plain = report.tier_budget * report.ap_coefficient
    return _damage(skill, library) * (plain / scale - other) / damage_points


def _row(library: ContentLibrary, skill: SkillDef, stats: Counter[str]) -> str:
    base = _damage(skill, library)
    cap = cap_points(skill_budget(skill, library), library)
    single = _once(library, skill, SINGLE)
    step = _once(library, skill, STEP)
    a, a_path, _ = run_plan(library, skill, PLAN_A)
    b, b_path, _ = run_plan(library, skill, PLAN_B)
    a_ok, b_ok = a.shape.type == "single", b.shape.type == "single"
    if not (a_ok and b_ok):
        verdict = "—"
    else:
        verdict = "是" if _full(b, library) <= _full(a, library) else "**否**"
    under = all(
        _damage(x, library) <= cap_points(skill_budget(x, library), library)
        for x, ok in ((a, a_ok), (b, b_ok))
        if ok
    )
    stats["rows"] += 1
    stats["single"] += single is not None
    stats["step"] += step is not None
    stats["both"] += a_ok and b_ok
    stats["b_le_a"] += verdict == "是"
    stats["over_cap"] += not under

    def cell(x: SkillDef, ok: bool) -> str:
        if not ok:
            return "（未收成單體）"
        ratio = skill_budget(x, library).ratio
        return (
            f"{_x(_damage(x, library), base)}（{float(ratio):.2f}／{_x(_full(x, library), base)}）"
        )

    shape = skill.shape.model_dump(mode="json", exclude_none=True)
    shape_text = "/".join(str(v) for v in shape.values())
    return (
        f"| {skill.id} | {shape_text} | {skill.tier} | {float(base):.1f} "
        f"| {'—' if single is None else _x(_damage(single, library), base)} "
        f"| {'—' if step is None else _x(_damage(step, library), base)} "
        f"| {a_path} | {cell(a, a_ok)} | {b_path} | {cell(b, b_ok)} "
        f"| {_x(cap, base)} | {verdict} | {'是' if under else '**否**'} |"
    )


def multiples_table(library: ContentLibrary) -> list[str]:
    head = (
        "| 技能 | 形狀 | 階 | 原招單發 | 收成單體 1 次 | 縮小一級 1 次 | (a) 路徑 "
        "| (a) 實際倍數（比例／同預算） | (b) 路徑 | (b) 實際倍數（比例／同預算） | 上限倍數 "
        "| (b)≤(a) | ≤上限 |"
    )
    lines = [head, "|" + "---|" * 13]
    stats = Counter[str]()
    lines += [_row(library, skill, stats) for skill in _subjects(library)]
    lines += [
        "",
        f"- 列數 {stats['rows']}；收成單體套得上 {stats['single']}、"
        f"縮小一級套得上 {stats['step']}；"
        f"(a)(b) 都收成單體 {stats['both']} 列，其中同預算單發 (b)≤(a) {stats['b_le_a']} 列；"
        f"超過單發上限 {stats['over_cap']} 列。",
        "- 「比例」＝最後的預算比例（總點數 ÷ 可用預算）。每一次閃現的重調都會在強度下限～100% "
        "之間重抽目標比例（收束只多 +40‰），蓄力還會加冷卻折抵，所以「實際倍數」隨最後一次重調、"
        "套上幾次（(a) 兩次蓄力到冷卻上限 5 後第 5 次套不上）浮動。",
        "- 「同預算」＝把一份同階、同 AP 單體預算剛好花完時的單發倍數（附帶效果的點數不動，其餘全"
        "給傷害）：拿掉比例、閃現加成與冷卻折抵的差別，只比結構。(b)≤(a) 用它判斷（預算守恆："
        "擴範圍時總點數不變、每個目標分到的變少，收束時再全部換回來，先擴再收不會多出預算）。",
    ]
    return lines


def _converge(pick_template: str) -> bool:
    return pick_template in TRADES


def ai_table(results: Sequence[RunMetrics]) -> list[str]:
    lines = [
        "| 策略 | 輪數 | 小變化選擇 | 其中範圍類 | 收束 | 收束／小變化 | 收成單體 | 縮小一級 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    order = ["balanced", *[p for p in ALL_FLASH_POLICIES if p != "balanced"]]
    for policy in order:
        runs = [r for r in results if r.policy == policy]
        picks = [p for r in runs for p in r.picks if p.source == "minor"]
        area = sum(1 for p in picks if p.category == "area")
        converge = [p for p in picks if _converge(p.template)]
        share = "—" if not picks else f"{100 * len(converge) / len(picks):.1f}%"
        lines.append(
            f"| {policy} | {len(runs)} | {len(picks)} | {area} | {len(converge)} | {share} "
            f"| {sum(1 for p in converge if p.template == SINGLE)} "
            f"| {sum(1 for p in converge if p.template == STEP)} |"
        )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=int, default=24, help="AI 模擬每個策略的種子數")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--no-ai", action="store_true", help="只量單發倍數")
    args = parser.parse_args(argv)
    library = default_library()
    out = [
        "# BAL-10d 收束量測",
        "",
        f"單發上限 {library.flash.rules.single_hit_cap_permille}‰（同階、同 AP 單體預算）；"
        f"每次閃現 +{library.flash.rules.budget_step_permille}‰；種子 {SEED}；"
        "倍數＝對單一目標的期望傷害 ÷ 原招（預算點數：骰子平均或武器倍率 × 基準，含條件倍率）。",
        "",
        "## 單發倍數與兩種練法",
        "",
        "路徑：`1縮` 第 1 次縮小一級、`2單` 第 2 次收成單體、`4蓄` 第 4 次蓄力、"
        "`1擴` 第 1 次範圍 +1、`—` 那一次套不上（略過）。第 3 次（大變化）兩種練法都略過。",
        "",
        *multiples_table(library),
    ]
    if not args.no_ai:
        policies: list[FlashPolicy] = list(ALL_FLASH_POLICIES)
        results = run_flash_sim(library, policies, range(1, args.seeds + 1), jobs=args.jobs)
        out += [
            "",
            f"## AI 選中收束的比例（每個策略 {args.seeds} 輪，種子 1–{args.seeds}）",
            "",
            "自動玩家一律選第一個選項（不指定類別時選項順序由種子洗牌）。",
            "",
            *ai_table(results),
        ]
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
