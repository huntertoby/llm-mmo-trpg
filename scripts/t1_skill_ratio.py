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

用法（Windows 一律 ``uv run python``）::

    uv run python scripts/t1_skill_ratio.py run [--seeds 250] [--jobs 6]
        [--skills a,b] [--weapons a,b] [--out 檔] [--detail]
    uv run python scripts/t1_skill_ratio.py report [檔] [--detail]

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

from trpg.sim.boss_probe import library_for
from trpg.sim.skill_ratio import (
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
    skill_summary,
    summary_cells,
    tier1_weapon_skills,
)

DEFAULT_SEEDS = 250
DEFAULT_JOBS = 6


def default_out() -> Path:
    return Path(tempfile.gettempdir()) / "t1_skill_ratio.json"


def run(args: argparse.Namespace) -> int:
    lib = library_for(None)
    skills = tier1_weapon_skills(lib)
    if args.skills:
        wanted = set(args.skills.split(","))
        skills = [s for s in skills if s.id in wanted]
    weapons_filter = set(args.weapons.split(",")) if args.weapons else None
    meta = {s.id: meta_of(lib, s) for s in skills}
    jobs = ratio_jobs(lib, skills, args.seeds, weapons_filter)
    print(
        f"{len(skills)} 招、{len(jobs)} 組（武器×招）、每組 {args.seeds} 種子、程序池 {args.jobs}",
        file=sys.stderr,
    )
    task = functools.partial(ratio_task, None)
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=get_context("spawn")) as pool:
        rows = list(pool.map(task, jobs, chunksize=1))
    rows.sort(key=lambda r: (class_rank(r["class"]), r["skill"], r["weapon"]))
    data = {"seeds": args.seeds, "dot_rounds": DOT_ROUNDS, "skills": meta, "rows": rows}
    out = Path(args.out) if args.out else default_out()
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
    by_skill: dict[str, list[dict[str, Any]]] = {}
    for r in data["rows"]:
        by_skill.setdefault(r["skill"], []).append(r)
    print(f"種子 {data['seeds']}／組；含持續＝施放後 {data['dot_rounds']} 輪；")
    print("比值＝技能每 AP ÷ 普攻每 AP；範圍是一般武器（不含雙匕首與綁定武器）")
    print("直接／含持續＝無條件或條件不成立；成立＝條件或變奏成立；綁定武器＝不成立情境下那把武器")
    low: list[tuple[str, str, float, str]] = []
    for wc in CLASS_ORDER:
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
    if detail:
        print_detail(data)


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
    path = Path(args.path) if args.path else default_out()
    data = json.loads(path.read_text(encoding="utf-8"))
    report_data(data, detail=args.detail)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="跑量測並寫 JSON")
    p_run.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    p_run.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    p_run.add_argument("--skills", default="", help="只跑這些招（逗號分隔）")
    p_run.add_argument("--weapons", default="", help="只跑這些武器（逗號分隔）")
    p_run.add_argument("--out", default="", help=f"JSON 路徑（預設 {default_out()}）")
    p_run.add_argument("--detail", action="store_true", help="另印逐武器明細")
    p_rep = sub.add_parser("report", help="從 JSON 重印摘要表")
    p_rep.add_argument("path", nargs="?", default="")
    p_rep.add_argument("--detail", action="store_true")
    args = parser.parse_args(argv)
    return run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    raise SystemExit(main())
