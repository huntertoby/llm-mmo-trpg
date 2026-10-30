"""第 1、2 次閃現小變化的選項數覆蓋掃描（BAL-10a，只量不調；不改任何模板與規則）。

對所有內建技能與白板配方，在「最低可用角色階級～3 階」（照角色階級重配後），模擬：
第 1 次閃現（不指定類別）→ 依序選每一個選項 → 第 2 次閃現（不指定類別），記錄每次的選項數與各
類別的合法小變化數（``category_counts``，最多算到指定類別出題的 3 個）。第 2 次在第 1 次選了任一
選項的各分支都看（取最小值與平均）。不連模型，只用引擎模板。

輸出 Markdown 到標準輸出（相同參數必得逐字相同）；``--csv`` 另存每個（技能, 階級）一列的 CSV。

用法::

    uv run python scripts/flash_minor_coverage.py --skills skill_a,skill_b --seeds 1 --board-seeds 0
    uv run python scripts/flash_minor_coverage.py --jobs 8 --csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.skills.constants import MAX_EFFECTS
from trpg.sim.parallel import run_tasks
from trpg.skillgen.flash_category import allowed_categories, template_kinds
from trpg.skillgen.flash_offer import (
    FlashOffer,
    FlashRequest,
    UsageSource,
    category_counts,
    make_offer,
    skill_before,
)
from trpg.skillgen.flash_offer import choose as flash_choose
from trpg.skillgen.flash_state import SkillFlash, acquire
from trpg.skillgen.random_composer import ComposeError, default_library
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.whiteboard import WHITEBOARD_KINDS, compose_whiteboard


def _load_audit() -> ModuleType:
    """借用同資料夾的稽核腳本（BAL-2）：不合法原因判定。"""
    path = Path(__file__).resolve().parent / "flash_category_audit.py"
    spec = importlib.util.spec_from_file_location("flash_category_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass 要從 sys.modules 找到模組
    spec.loader.exec_module(module)
    return module


audit = _load_audit()

MAX_ROLE_TIER = 3
SHORT = 2
"""選項數少於這個數就算不足。"""


@dataclass(frozen=True, slots=True)
class Row:
    """一個（技能, 角色階級）跨種子的彙總。"""

    origin: str
    skill_id: str
    kind: str
    skill_tier: int
    role_tier: int
    seeds: int
    n1_min: int
    n1_avg: float
    n2_min: int
    n2_avg: float
    cats1: str
    """第 1 次各類別的合法小變化數（``類別:數``，數最多 3）。"""
    cats2_min: str
    """第 2 次選項最少的那個分支的各類別合法數。"""
    reasons1: str
    reasons2: str
    tags: str
    """技能（照角色階級重配後）的結構特徵。"""


def _subjects(
    library: ContentLibrary, skill_ids: Sequence[str] | None, board_seeds: int
) -> list[tuple[str, SkillDef]]:
    out: list[tuple[str, SkillDef]] = []
    ids = sorted(library.skills) if skill_ids is None else list(skill_ids)
    out.extend(("builtin", library.skills[i]) for i in ids)
    if skill_ids is None:
        for tier in (1, 2, 3):
            for kind in WHITEBOARD_KINDS:
                for seed in range(1, board_seeds + 1):
                    try:
                        board = compose_whiteboard(seed, kind=kind, tier=tier, library=library)
                    except ComposeError:
                        continue
                    out.append(("whiteboard", board))
    return sorted(out, key=lambda t: (t[0], t[1].id))


def _request(skill: SkillDef, state: SkillFlash, role_tier: int, seed: int) -> FlashRequest:
    return FlashRequest(base=skill, state=state, usage=SkillUsage(), seed=seed, tier=role_tier)


def _cats(library: ContentLibrary, request: FlashRequest) -> dict[str, int]:
    return {c: n for c, n in category_counts(library, request).items() if n > 0}


def _fmt(counts: dict[str, int]) -> str:
    return ",".join(f"{c}:{n}" for c, n in sorted(counts.items())) or "-"


def _tags(skill: SkillDef) -> list[str]:
    """技能的結構特徵（判斷哪些模板套不上）。"""
    tags = [f"形狀:{skill.shape.type}", f"AP{skill.ap_cost or 1}"]
    if skill.followup is not None:
        tags.append("複合技")
    if skill.trap is not None:
        tags.append("陷阱")
    if skill.variants:
        tags.append("變奏")
    if skill.cost.on_miss:
        tags.append("失手反噬")
    if skill.is_activatable:
        tags.append("常駐")
    types = {e.type for e in skill.effects}
    if "summon" in types:
        tags.append("召喚")
    if "damage" not in types:
        tags.append("無傷害")
    if len(skill.effects) >= MAX_EFFECTS:
        tags.append("效果滿")
    return tags


def _why_active(op: str, skill: SkillDef) -> str:
    """主動／被動／反應技各改法「結構不符」的具體原因（照 ``flash_ops`` 的判斷）。"""
    blocked = skill.followup is not None or skill.trap is not None
    reasons: dict[str, str] = {
        "area": "複合技／陷阱不改形狀" if blocked else "形狀已到上限或沒有可增大的參數",
        "range": "複合技／陷阱不改形狀" if blocked else "沒有固定整數射程或已達上限",
        "reshape": "複合技／陷阱不改形狀" if blocked else "沒有傷害效果或已是該形狀",
        "terrain_area": "沒有升降地形效果",
        "multi_hit": "複合技／陷阱／無傷害／效果已滿",
        "followup": "複合技／陷阱／變奏／失手反噬／常駐／無傷害／禁用效果",
        "light": "AP 已是 1" if (skill.ap_cost or 1) <= 1 else "其他",
        "element": "沒有傷害效果／陷阱／效果已滿／元素已有",
        "kill_refund": "無傷害效果（或已有擊殺返還）",
        "summon_toughen": "不是單隻召喚",
        "extend": "沒有可延長的狀態／表面／區域",
        "converge_single": "陷阱／沒有威力／不是多格範圍／骨架或效果不允許單體",
        "converge_step": "陷阱／沒有威力／已是最小一級（或環形、連鎖、光環）",
    }
    return reasons.get(op, "其他")


def _reasons(
    library: ContentLibrary, request: FlashRequest, current: SkillDef, role_tier: int, origin: str
) -> list[str]:
    """這次請求裡，每個「沒有任何合法變體」的小變化模板的主要原因（``模板:原因``）。"""
    table = library.flash
    before = skill_before(library, request)
    allowed = set(allowed_categories(table, before, major=False))
    subject = audit.Subject(current, role_tier, origin)
    source = UsageSource()
    out: list[str] = []
    for template in table.minor:
        if template.category not in allowed:
            continue
        if before.kind not in template_kinds(table, template):
            continue
        variants = source._variants(library, request, template, before)
        if not variants:
            out.append(f"{template.id}:無候選變體")
            continue
        results = [audit.classify(library, subject, template, v, request) for v in variants]
        if "legal" in results:
            continue
        why = results[0].removeprefix("illegal:")
        if why.startswith("階級不足"):
            continue  # 最低階級以下本來就不出，不算缺口
        if why.endswith("/其他"):
            why = why.removesuffix("其他") + _why_active(template.op, current)
        out.append(f"{template.id}:{why}")
    return out


def _one_seed(
    library: ContentLibrary, skill: SkillDef, role_tier: int, seed: int, origin: str
) -> tuple[int, list[int], str, str, list[str], list[str]]:
    """回傳（第 1 次選項數, 各分支第 2 次選項數, 第 1 次類別, 最少分支的類別, 原因1, 原因2）。"""
    state0 = acquire(skill.id)
    request1 = _request(skill, state0, role_tier, seed)
    offer1: FlashOffer = make_offer(library, request1)
    n1 = len(offer1.options)
    cats1 = _fmt(_cats(library, request1))
    reasons1 = (
        _reasons(
            library, request1, audit.at_role_tier(library, skill, role_tier), role_tier, origin
        )
        if n1 < SHORT
        else []
    )
    branches: list[tuple[int, str, list[str]]] = []
    for index in range(n1):
        state1, picked = flash_choose(state0, offer1, index)
        request2 = _request(skill, state1, role_tier, seed)
        n2 = len(make_offer(library, request2).options)
        if n2 < SHORT:
            branches.append(
                (
                    n2,
                    _fmt(_cats(library, request2)),
                    _reasons(library, request2, picked, role_tier, origin),
                )
            )
        else:
            branches.append((n2, "", []))
    n2s = [b[0] for b in branches]
    worst = min(branches, key=lambda b: b[0]) if branches else (0, "-", [])
    return n1, n2s, cats1, worst[1] or "-", reasons1, worst[2]


def scan_chunk(library: ContentLibrary, task: tuple[list[tuple[str, SkillDef]], int]) -> list[Row]:
    subjects, seeds = task
    rows: list[Row] = []
    for origin, skill in subjects:
        for role_tier in range(max(1, skill.tier), MAX_ROLE_TIER + 1):
            n1s: list[int] = []
            n2s: list[int] = []
            cats1 = cats2 = "-"
            r1: Counter[str] = Counter()
            r2: Counter[str] = Counter()
            worst2 = 99
            for seed in range(1, seeds + 1):
                n1, branch, c1, c2, why1, why2 = _one_seed(library, skill, role_tier, seed, origin)
                n1s.append(n1)
                n2s.extend(branch)
                r1.update(why1)
                r2.update(why2)
                if n1 <= min(n1s):
                    cats1 = c1
                if branch and min(branch) < worst2:
                    worst2, cats2 = min(branch), c2
            rows.append(
                Row(
                    origin=origin,
                    skill_id=skill.id,
                    kind=str(skill.kind),
                    skill_tier=skill.tier,
                    role_tier=role_tier,
                    seeds=seeds,
                    n1_min=min(n1s),
                    n1_avg=sum(n1s) / len(n1s),
                    n2_min=min(n2s) if n2s else 0,
                    n2_avg=sum(n2s) / len(n2s) if n2s else 0.0,
                    cats1=cats1,
                    cats2_min=cats2,
                    reasons1="; ".join(k for k, _ in sorted(r1.items())),
                    reasons2="; ".join(k for k, _ in sorted(r2.items())),
                    tags=",".join(_tags(audit.at_role_tier(library, skill, role_tier))),
                )
            )
    return rows


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return [*lines, ""]


def report_summary(rows: Sequence[Row]) -> list[str]:
    lines = ["## 1. 彙總：技能種類 × 角色階級", ""]
    groups: dict[tuple[str, str, int], list[Row]] = defaultdict(list)
    for r in rows:
        groups[(r.origin, r.kind, r.role_tier)].append(r)
    body: list[list[str]] = []
    for (origin, kind, tier), g in sorted(groups.items()):
        s1 = sum(r.n1_min < SHORT for r in g)
        s2 = sum(r.n2_min < SHORT for r in g)
        z2 = sum(r.n2_min == 0 for r in g)
        body.append(
            [
                origin,
                kind,
                str(tier),
                str(len(g)),
                f"{s1} ({s1 * 100 / len(g):.0f}%)",
                f"{s2} ({s2 * 100 / len(g):.0f}%)",
                str(z2),
                f"{sum(r.n1_avg for r in g) / len(g):.2f}",
                f"{sum(r.n2_avg for r in g) / len(g):.2f}",
            ]
        )
    lines += _table(
        [
            "來源",
            "種類",
            "角色階級",
            "（技能, 階級）數",
            "第1次<2",
            "第2次(任一分支)<2",
            "其中第2次=0",
            "第1次平均",
            "第2次平均",
        ],
        body,
    )
    return lines


def _why_text(r: Row) -> str:
    """不足那一次的原因（兩次都不足時合併）。"""
    parts = [r.reasons1] if r.n1_min < SHORT else []
    if r.n2_min < SHORT:
        parts.append(r.reasons2)
    return "; ".join(sorted({t.strip() for p in parts for t in p.split(";") if t.strip()}))


def report_short(rows: Sequence[Row]) -> list[str]:
    lines = ["## 2. 不足清單（第 1 或第 2 次選項 < 2；跨種子取最小）", ""]
    short = [r for r in rows if r.n1_min < SHORT or r.n2_min < SHORT]
    lines.append(f"共 {len(short)} 列（技能, 角色階級）。\n")
    body = [
        [
            r.skill_id,
            r.origin,
            r.kind,
            f"{r.skill_tier}/{r.role_tier}",
            f"{r.n1_min}/{r.n1_avg:.1f}",
            f"{r.n2_min}/{r.n2_avg:.1f}",
            r.cats1,
            r.cats2_min,
            r.tags,
            _why_text(r) or "-",
        ]
        for r in short
    ]
    lines += _table(
        [
            "技能",
            "來源",
            "種類",
            "技能階/角色階",
            "第1次 最小/平均",
            "第2次 最小/平均",
            "第1次有的類別:數",
            "第2次(最少分支)有的類別:數",
            "技能結構",
            "沒有合法變體的模板:原因（不含階級不足）",
        ],
        body,
    )
    return lines


def report_reasons(rows: Sequence[Row]) -> list[str]:
    lines = ["## 3. 不合法模板原因彙總（不足列中出現的次數，依種類）", ""]
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        if r.n1_min >= SHORT and r.n2_min >= SHORT:
            continue
        for item in filter(None, _why_text(r).split("; ")):
            counts[(r.kind, item)] += 1
    body = [
        [k, i, str(n)]
        for (k, i), n in sorted(counts.items(), key=lambda kv: (kv[0][0], -kv[1], kv[0][1]))
    ]
    lines += _table(["種類", "模板:原因", "不足列數"], body)
    return lines


def report_tags(rows: Sequence[Row]) -> list[str]:
    lines = ["## 4. 依技能結構特徵的缺口率", ""]
    total: Counter[tuple[str, str]] = Counter()
    first: Counter[tuple[str, str]] = Counter()
    second: Counter[tuple[str, str]] = Counter()
    for r in rows:
        for tag in r.tags.split(","):
            key = (r.kind, tag)
            total[key] += 1
            first[key] += int(r.n1_min < SHORT)
            second[key] += int(r.n2_min < SHORT)
    body = [
        [
            k,
            t,
            str(n),
            f"{first[(k, t)]} ({first[(k, t)] * 100 / n:.0f}%)",
            f"{second[(k, t)]} ({second[(k, t)] * 100 / n:.0f}%)",
        ]
        for (k, t), n in sorted(total.items())
    ]
    lines += _table(["種類", "結構特徵", "列數", "第1次<2", "第2次<2"], body)
    return lines


def to_csv(rows: Sequence[Row]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "origin",
            "skill_id",
            "kind",
            "skill_tier",
            "role_tier",
            "seeds",
            "n1_min",
            "n1_avg",
            "n2_min",
            "n2_avg",
            "cats1",
            "cats2_min",
            "reasons1",
            "reasons2",
            "tags",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.origin,
                r.skill_id,
                r.kind,
                r.skill_tier,
                r.role_tier,
                r.seeds,
                r.n1_min,
                f"{r.n1_avg:.2f}",
                r.n2_min,
                f"{r.n2_avg:.2f}",
                r.cats1,
                r.cats2_min,
                r.reasons1,
                r.reasons2,
                r.tags,
            ]
        )
    return buf.getvalue()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skills", help="只測這些內建技能 ID（逗號分隔；給了就不測白板）")
    parser.add_argument("--seeds", type=int, default=2, help="每個（技能, 階級）的出題種子數")
    parser.add_argument("--board-seeds", type=int, default=6, help="每個（階級, 種類）的白板配方數")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--csv", help="另存每個（技能, 階級）一列的 CSV 路徑")
    args = parser.parse_args(argv)
    library = default_library()
    ids = None if args.skills is None else [s for s in args.skills.split(",") if s]
    subjects = _subjects(library, ids, args.board_seeds)
    n = args.jobs * 4
    chunks = [subjects[i::n] for i in range(n)]
    parts = run_tasks(scan_chunk, library, [(c, args.seeds) for c in chunks if c], jobs=args.jobs)
    rows = sorted((r for p in parts for r in p), key=lambda r: (r.origin, r.skill_id, r.role_tier))
    out = [
        f"# 第 1、2 次閃現小變化覆蓋掃描（受測 {len(subjects)} 個技能或配方、"
        f"{len(rows)} 列（技能, 階級）、"
        f"每列 {args.seeds} 個種子）\n"
    ]
    out += report_summary(rows)
    out += report_short(rows)
    out += report_reasons(rows)
    out += report_tags(rows)
    sys.stdout.write("\n".join(out) + "\n")
    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        Path(args.csv).write_text(to_csv(rows), encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
