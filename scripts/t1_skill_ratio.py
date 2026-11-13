"""BAL-21e：1 階武器技的「每 AP 傷害 ÷ 普攻每 AP」比值表（只讀量測，不改任何內容）。

量測核心在 ``trpg.sim.skill_ratio``（NW-2c 搬家，數值工坊共用）；這支只留 CLI 與印表，輸出和搬家前
逐字相同。量法照開發 PM 的 #148 核對（共用筆記「核對-148示範招B案」）：主城靶場 ``training_range``、
``range_trial`` 的推薦配點（開局自由點數全照 ``recommended_allocation``）、打普通木樁 (6,4)；
近戰站 (6,5)、遠程站 (6,7)；每把武器每個情境預設 250 個種子取平均（含失手）。
比值＝（技能對木樁的傷害 ÷ 花掉的 AP）÷（普攻對木樁的傷害 ÷ 花掉的 AP）。

- 「直接」只算施放當下；「含持續」是施放後再過 ``DOT_ROUNDS`` 輪（主角每輪直接結束回合）木樁的
  總損血，涵蓋中毒、燃燒、表面、延遲段與召喚物（只在技能可能有後續傷害時另跑）。
- 條件類另跑「成立」：在施放前直接把狀態改成條件成立（目標加狀態、表面、高低差、隱匿、疊滿層、
  旁邊放一個我方木樁…），「不成立」是自然狀態（第 1 輪、背刺這兩種自然成立的，不成立另外做：
  等一輪、背後格放木樁擋住）。綁武器（``wielding_weapon``）不另跑，直接看那把武器的列。
- 變奏（``variants``）每個另跑一次「成立」。
- ``--category spell``（SR-1）：改量 1 階法器法術（``category: spell``、``weapon_req: focus``），
  基準是同一把法器的普攻每 AP；JSON 多 ``category``、meta 多 ``skeleton``／``element``，報表只印
  法器一節，另印參考線外的清單與分組摘要。預設 ``weapon`` 的輸出和加這個參數前逐字相同。

用法（Windows 一律 ``uv run python``）::

    uv run python scripts/t1_skill_ratio.py run [--category weapon|spell] [--seeds 250] [--jobs 6]
        [--skills a,b] [--weapons a,b] [--out 檔] [--detail]
    uv run python scripts/t1_skill_ratio.py report [檔] [--category weapon|spell] [--detail]

結果 JSON 預設寫到系統暫存區（``tempfile.gettempdir()``），不進 repo。
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
import tempfile
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from trpg.content.skills import SkillDef
from trpg.sim.boss_probe import library_for
from trpg.sim.skill_ratio import (
    CATEGORIES,
    CLASS_ORDER,
    CLASS_ZH,
    DOT_ROUNDS,
    LOW_RATIO,
    SINGLE_SHAPES,
    class_rank,
    low_tag,
    meta_of,
    odd_conditions,
    ratio_jobs,
    ratio_task,
    reference_checks,
    skill_summary,
    summary_cells,
    tier1_skills,
)

DEFAULT_SEEDS = 250
DEFAULT_JOBS = 6


def default_out(category: str = "weapon") -> Path:
    name = "t1_skill_ratio.json" if category == "weapon" else f"t1_skill_ratio_{category}.json"
    return Path(tempfile.gettempdir()) / name


def spell_meta(skill: SkillDef) -> dict[str, Any]:
    """法術多記的分組欄位：骨架、元素（第一個傷害效果的元素，沒有時看技能的 ``element``）。"""
    data = skill.model_dump(mode="json", exclude_none=True)
    elements = [
        str(e["element"]) for e in data["effects"] if e.get("type") == "damage" and e.get("element")
    ]
    element = elements[0] if elements else data.get("element")
    return {"skeleton": str(skill.skeleton), "element": str(element) if element else "—"}


def run(args: argparse.Namespace) -> int:
    lib = library_for(None)
    skills = tier1_skills(lib, args.category)
    if args.skills:
        wanted = set(args.skills.split(","))
        skills = [s for s in skills if s.id in wanted]
    weapons_filter = set(args.weapons.split(",")) if args.weapons else None
    meta = {s.id: meta_of(lib, s) for s in skills}
    if args.category != "weapon":
        for s in skills:
            meta[s.id] |= spell_meta(s)
    jobs = ratio_jobs(lib, skills, args.seeds, weapons_filter)
    print(
        f"{len(skills)} 招、{len(jobs)} 組（武器×招）、每組 {args.seeds} 種子、程序池 {args.jobs}",
        file=sys.stderr,
    )
    task = functools.partial(ratio_task, None)
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=get_context("spawn")) as pool:
        rows = list(pool.map(task, jobs, chunksize=1))
    rows.sort(key=lambda r: (class_rank(r["class"]), r["skill"], r["weapon"]))
    data: dict[str, Any] = {
        "seeds": args.seeds,
        "dot_rounds": DOT_ROUNDS,
        "skills": meta,
        "rows": rows,
    }
    if args.category != "weapon":
        data["category"] = args.category  # weapon 不寫：JSON 和加參數前逐字相同
    out = Path(args.out) if args.out else default_out(args.category)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"寫入 {out}", file=sys.stderr)
    report_data(data, detail=args.detail)
    return 0


# ---------------------------------------------------------------------------
# 重印
# ---------------------------------------------------------------------------


def _cond_zh(meta: dict[str, Any]) -> str:
    parts = list(meta["conds"]) + [f"變奏 {v}" for v in meta["variants"]]
    if meta["bound"]:
        parts.append("綁 " + "/".join(meta["bound"]))
    return "、".join(parts) if parts else "無"


def _skill_line(
    m: dict[str, Any], sid: str, rows: list[dict[str, Any]]
) -> tuple[str, float | None]:
    """摘要表的一列，與這招所有武器、情境的直接比值最高值（沒有可用武器時 ``None``）。"""
    head = f"| {m['name_zh']} `{sid}` | {m['ap']} | {m['shape']} | {_cond_zh(m)} "
    if not rows:
        return head + "| 沒有可用武器 | | | | | |", None
    s = skill_summary(m, rows)
    c = summary_cells(m, rows)
    line = (
        f"{head}| {c['plain']} | {c['plain_tot']} | {c['on']} | {c['on_tot']} "
        f"| {c['dual']} | {c['bound']} |"
    )
    every = s["plain"] + s["on"] + [x for v in s["vars"].values() for x in v]
    every += [x for v in s["bound"].values() for x in v]
    return line, max(every, default=0.0)


def report_data(data: dict[str, Any], *, detail: bool = False) -> None:
    meta: dict[str, dict[str, Any]] = data["skills"]
    spell = data.get("category", "weapon") != "weapon"
    by_skill: dict[str, list[dict[str, Any]]] = {}
    for r in data["rows"]:
        by_skill.setdefault(r["skill"], []).append(r)
    if spell:
        print("類別：1 階法器法術（category: spell、weapon_req: focus）；普攻＝同一把法器的普攻")
    print(f"種子 {data['seeds']}／組；含持續＝施放後 {data['dot_rounds']} 輪；")
    print("比值＝技能每 AP ÷ 普攻每 AP；範圍是一般武器（不含雙匕首與綁定武器）")
    print("直接／含持續＝無條件或條件不成立；成立＝條件或變奏成立；綁定武器＝不成立情境下那把武器")
    low: list[tuple[str, str, float, str]] = []
    classes = [wc for wc in CLASS_ORDER if any(m["class"] == wc for m in meta.values())]
    for wc in classes if spell else CLASS_ORDER:
        ids = [s for s in meta if meta[s]["class"] == wc]
        print(f"\n## {CLASS_ZH[wc]}（{len(ids)} 招）\n")
        print("| 招 | AP | 形狀 | 條件 | 直接 | 含持續 | 成立 直接 | 成立 含持續 ", end="")
        print("| 雙匕首 | 綁定武器 |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for sid in ids:
            line, best = _skill_line(meta[sid], sid, by_skill.get(sid, []))
            print(line)
            if best is not None and best < LOW_RATIO:
                low.append((wc, sid, best, low_tag(meta[sid])))
        by_weapon(data, wc)
    print(f"\n## 低於 {LOW_RATIO} 的招（直接傷害，取所有武器與情境的最高值仍 < {LOW_RATIO}）\n")
    print("| 大類 | 招 | 最高比值 | 類別 | 含持續最高 |")
    print("|---|---|---|---|---|")
    tags = ("無條件", "條件類", "非單體", "召喚", "非傷害招")
    low.sort(key=lambda t: (class_rank(t[0]), tags.index(t[3]), t[2], t[1]))
    for wc, sid, best, tag in low:
        tots = [
            float(res["ratio_tot"])
            for r in by_skill[sid]
            for res in r["scenarios"].values()
            if res.get("castable") and "ratio_tot" in res
        ]
        tot = f"{max(tots):.2f}" if meta[sid]["lingers"] and tots else "—"
        print(f"| {CLASS_ZH[wc]} | {meta[sid]['name_zh']} `{sid}` | {best:.2f} | {tag} | {tot} |")
    counts = "；".join(
        f"{CLASS_ZH[wc]}{tag} {sum(1 for t in low if t[0] == wc and t[3] == tag)}"
        for wc in CLASS_ORDER
        for tag in tags
        if any(t[0] == wc and t[3] == tag for t in low)
    )
    print(f"\n共 {len(low)} 招（{counts}）")
    odd = odd_conditions(data)
    print(f"\n條件檢查：施放前條件和情境不符 {len(odd)} 組")
    for line in odd:
        print(f"- {line}")
    if spell:
        print_reference(meta, by_skill)
        print_groups(meta, by_skill)
    if detail:
        print_detail(data)


# ---------------------------------------------------------------------------
# 法術才印的兩節（SR-1）
# ---------------------------------------------------------------------------


def _checks(m: dict[str, Any], rows: list[dict[str, Any]]) -> list[tuple[Any, float | None]]:
    return reference_checks(m, skill_summary(m, rows)) if rows else []


def print_reference(meta: dict[str, dict[str, Any]], by_skill: dict[str, list[Any]]) -> None:
    """參考線（D4，同工坊）：每招適用的線與比較值（範圍最高值）；列出低於或不可放的。"""
    print("\n## 參考線外（D4：無條件 ≥ 0.9、成立 ≥ 1.1、不成立 ≥ 0.6〔建議〕；比範圍最高值）\n")
    print("| 招 | AP | 類別 | 參考線 | 值 |")
    print("|---|---|---|---|---|")
    total = below = 0
    for sid, m in meta.items():
        for line, value in _checks(m, by_skill.get(sid, [])):
            total += 1
            if value is not None and value >= line.threshold:
                continue
            below += 1
            shown = "不可放" if value is None else f"{value:.2f}"
            mark = "〔建議〕" if line.tentative else ""
            print(
                f"| {m['name_zh']} `{sid}` | {m['ap']} | {low_tag(m)} "
                f"| {line.label_zh} ≥ {line.threshold}{mark} | {shown} |"
            )
    print(f"\n套參考線 {total} 條（招×線），低於或不可放 {below} 條")


def _best_plain(m: dict[str, Any], rows: list[dict[str, Any]]) -> float | None:
    vals = skill_summary(m, rows)["plain"] if rows else []
    return max(vals) if vals else None


def print_groups(meta: dict[str, dict[str, Any]], by_skill: dict[str, list[Any]]) -> None:
    """分組摘要：依 AP、元素、骨架、類別；值＝每招一般武器「直接」（條件類取不成立）的最高值。"""
    keys = (
        ("AP", lambda m: str(m["ap"])),
        ("元素", lambda m: str(m.get("element", "—"))),
        ("骨架", lambda m: str(m.get("skeleton", "—"))),
        ("類別", low_tag),
    )
    for title, key in keys:
        groups: dict[str, list[str]] = {}
        for sid, m in meta.items():
            groups.setdefault(key(m), []).append(sid)
        print(f"\n## 分組：{title}（直接，條件類取不成立；每招取最高值）\n")
        print("| 組 | 招 | 可放 | ≥ 0.9 | ≥ 0.6 | 中位數 | 最高 |")
        print("|---|---|---|---|---|---|---|")
        for name in sorted(groups):
            best = [_best_plain(meta[s], by_skill.get(s, [])) for s in groups[name]]
            vals = sorted(v for v in best if v is not None)
            med = f"{vals[len(vals) // 2]:.2f}" if vals else "—"
            hi = f"{vals[-1]:.2f}" if vals else "—"
            good = sum(1 for v in vals if v >= LOW_RATIO)
            ok = sum(1 for v in vals if v >= 0.6)  # noqa: PLR2004 - 「不成立」建議線
            print(f"| {name} | {len(best)} | {len(vals)} | {good} | {ok} | {med} | {hi} |")


def by_weapon(data: dict[str, Any], wc: str) -> None:
    """大類 × 武器：單體傷害招（形狀單體、有傷害效果）的直接比值（條件類取不成立）分布。"""
    meta = data["skills"]
    rows = [
        r
        for r in data["rows"]
        if r["class"] == wc
        and meta[r["skill"]]["damaging"]
        and meta[r["skill"]]["shape"] in SINGLE_SHAPES
    ]
    weapons = sorted({r["weapon"] for r in rows})
    if not weapons:
        return
    print(f"\n{CLASS_ZH[wc]} × 武器（單體傷害招的直接比值；條件類取不成立）\n")
    print("| 武器 | 普攻每 AP | 單體傷害招 | ≥ 0.9 | 中位數 | 最高 |")
    print("|---|---|---|---|---|---|")
    for w in weapons:
        vals = []
        basic = 0.0
        for r in rows:
            if r["weapon"] != w:
                continue
            basic = r["basic"]["imm"] / r["basic"]["ap"]
            name = "base" if "base" in r["scenarios"] else "off"
            res = r["scenarios"][name]
            if res.get("castable") and "ratio" in res:
                vals.append(float(res["ratio"]))
        vals.sort()
        med = vals[len(vals) // 2] if vals else 0.0
        hi = vals[-1] if vals else 0.0
        good = sum(1 for v in vals if v >= LOW_RATIO)
        print(f"| {w} | {basic:.2f} | {len(vals)} | {good} | {med:.2f} | {hi:.2f} |")


def print_detail(data: dict[str, Any]) -> None:
    print("\n## 逐武器明細\n")
    for r in data["rows"]:
        parts = []
        for name, res in r["scenarios"].items():
            if not res.get("castable"):
                parts.append(f"{name}=不可放")
                continue
            met = "" if res.get("met") is None else f" 成立{res['met']}"
            parts.append(f"{name}={res.get('ratio', 0):.2f}/{res.get('ratio_tot', 0):.2f}{met}")
        basic = r["basic"]["imm"] / r["basic"]["ap"]
        print(f"{r['skill']:28s} {r['weapon']:16s} 普攻 {basic:.2f}/AP  " + "  ".join(parts))


def report(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_out(args.category)
    data = json.loads(path.read_text(encoding="utf-8"))
    report_data(data, detail=args.detail)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="跑量測並寫 JSON")
    p_run.add_argument("--category", choices=CATEGORIES, default="weapon", help="武器技或法器法術")
    p_run.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    p_run.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    p_run.add_argument("--skills", default="", help="只跑這些招（逗號分隔）")
    p_run.add_argument("--weapons", default="", help="只跑這些武器（逗號分隔）")
    p_run.add_argument("--out", default="", help=f"JSON 路徑（預設 {default_out()}）")
    p_run.add_argument("--detail", action="store_true", help="另印逐武器明細")
    p_rep = sub.add_parser("report", help="從 JSON 重印摘要表")
    p_rep.add_argument("path", nargs="?", default="")
    p_rep.add_argument("--category", choices=CATEGORIES, default="weapon", help="沒給檔時的預設檔")
    p_rep.add_argument("--detail", action="store_true")
    args = parser.parse_args(argv)
    return run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    raise SystemExit(main())
