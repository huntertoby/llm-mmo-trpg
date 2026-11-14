"""組合器配方盤點（RC-0）：每個（關鍵字, 種類, 階級, 稀有度）格子各抽一段種子，記合法數與設計數。

合法＝和退回路徑 ``proposal_fallback._from_composer`` 收下的條件相同：組合器不丟 ``ComposeError``、
``validate_skill`` 無違規、``_fits``（種類、骨架、題目的全部關鍵字，只看專屬規則）。參數也照它：
種類非主動時骨架＝種類（被動、反應各有同名骨架），關鍵字照題目。
設計鍵＝骨架＋種類＋形狀類型＋效果類型（含狀態 ID）＋元素標籤（數值不同算同一個設計）。

只讀：不改 ``content/``，不跑戰鬥。輸出 JSON 與 Markdown 摘要；計時以外的欄位只由內容與參數決定，
平行與否結果相同（RC-1 補配方時用同一支腳本做改前改後對照）。

用法::

    uv run python scripts/recipe_census.py --workers 8
    uv run python scripts/recipe_census.py --seeds 5 --keywords summon --kinds active  # 試算
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef, rarity_rank
from trpg.content.skills.constants import SkillRarity
from trpg.content.world_rules import WorldRules
from trpg.shared.types import Element
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.keywords import has_keyword
from trpg.skillgen.proposal_fallback import wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError, select_subset
from trpg.skillgen.proposal_topup import keywords_reachable
from trpg.skillgen.random_composer import (
    _STACK_SKELETON,
    ComposeError,
    KeywordExhaustedError,
    _is_stack_keyword,
    compose_with_stats,
)
from trpg.skillgen.validate import validate_skill

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "phases" / "RC-0資料"
KINDS = ("active", "passive", "reaction")
RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic")
NO_KEYWORD = "-"
"""「不指定關鍵字」那一列的代號。"""
MAX_WORKERS = 8
DEFAULT_THIN = 12
"""挑選模式 K=12：不同設計數少於這個就算薄格。"""
DIAG_SEEDS = 50
"""空格、薄格的診斷：不帶關鍵字組幾個種子，看同種類本身組不組得出來、會不會碰巧帶到關鍵字。"""
_ELEMENTS = frozenset(e.value for e in Element)
FORMAT = "recipe-census/1"


# ---------------------------------------------------------------------------
# 格子與結果
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cell:
    keyword: str  # NO_KEYWORD ＝ 不指定
    kind: str
    tier: int
    rarity: SkillRarity

    def label(self) -> str:
        return f"{self.keyword}/{self.kind}/{self.tier}階/{self.rarity}"


@dataclass(slots=True)
class CellResult:
    keyword: str
    kind: str
    tier: int
    rarity: SkillRarity
    seeds: int
    legal: int
    designs: int
    structures: int
    reasons: dict[str, int]
    samples: dict[str, str]
    """每個不合法原因的第一個例子（種子最小的那個的訊息）。"""
    top_designs: list[list[Any]]
    """出現最多的前 5 個設計（設計鍵, 次數）。"""
    blocked_by_design: bool
    """這個種類的骨架稀有度下限高於這格（被動至少 epic、反應至少 rare）：遊戲裡本來就不會出這格。"""
    reachable: bool
    """遊戲出題的檢查（:func:`topic_reachable`）通過：規則上這格做得出帶關鍵字的技能。"""
    diag: dict[str, int] = field(default_factory=dict)
    timing: dict[str, float] = field(default_factory=dict)
    """計時（毫秒）；每次跑都不同，比對時排除。"""


# ---------------------------------------------------------------------------
# 單一格子
# ---------------------------------------------------------------------------

_LIBRARY: ContentLibrary | None = None


def _library() -> ContentLibrary:
    global _LIBRARY  # noqa: PLW0603 — 每個行程只載入一次內容庫
    if _LIBRARY is None:
        _LIBRARY = load_library()
    return _LIBRARY


def design_key(skill: SkillDef) -> tuple[Any, ...]:
    """骨架＋種類＋形狀類型＋效果類型（含狀態 ID）＋元素標籤。"""
    effects = tuple(
        sorted(e.type + ":" + str(getattr(e, "status", "") or "") for e in skill.effects)
    )
    elements = tuple(t for t in skill.tags if t in _ELEMENTS)
    return (skill.skeleton, skill.kind, skill.shape.type, effects, elements)


def _structure_key(skill: SkillDef) -> str:
    data = skill.model_dump(mode="json", exclude={"id", "name_zh", "narrative", "provenance"})
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _compose_reason(exc: ComposeError) -> str:
    if isinstance(exc, KeywordExhaustedError):
        return "keyword_exhausted"
    text = str(exc)
    for needle, code in (
        ("組合器做不出關鍵字", "keyword_not_composable"),
        ("重抽都做不出合格", "retry_exhausted"),
        ("抽到傳說", "legendary_skipped"),
        ("沒有階級", "no_tier_budget"),
    ):
        if needle in text:
            return code
    return "compose_error"


def _misfit(skill: SkillDef, request: ProposalRequest, kind: str, lib: ContentLibrary) -> str:
    """``_fits`` 不過的原因（依序檢查種類、骨架、關鍵字）。"""
    if skill.kind != kind:
        return f"not_fit.kind({skill.kind})"
    if request.skeleton is not None and skill.skeleton != request.skeleton:
        return "not_fit.skeleton"
    if not skill_has_keywords(skill, request.keywords, lib):
        return "not_fit.keyword"
    return ""


def _skeleton_for(kind: str, lib: ContentLibrary) -> str | None:
    return kind if kind != "active" and kind in lib.skeletons else None


def blocked_by_design(cell: Cell, lib: ContentLibrary) -> bool:
    skeleton = lib.skeletons.get(cell.kind)
    return skeleton is not None and rarity_rank(cell.rarity) < rarity_rank(skeleton.min_rarity)


def _diag_skeleton(cell: Cell, lib: ContentLibrary) -> str | None:
    """診斷用的骨架：和組合器指定關鍵字時一樣（層數關鍵字不指定骨架時固定蓄力骨架）。"""
    skeleton = _skeleton_for(cell.kind, lib)
    if skeleton is None and cell.keyword != NO_KEYWORD and _is_stack_keyword(cell.keyword, lib):
        return _STACK_SKELETON
    return skeleton


def topic_reachable(cell: Cell, lib: ContentLibrary) -> bool:
    """遊戲出 LLM 題目時的同一個檢查（``proposal_topic``：``select_subset`` 不出錯、選單帶得到
    題目關鍵字）。不通過＝規則上這個種類、稀有度、階級做不出帶這個關鍵字的技能，遊戲不會出這題。"""
    keywords = () if cell.keyword == NO_KEYWORD else (cell.keyword,)
    request = ProposalRequest(cell.tier, cell.rarity, kind=cell.kind, keywords=keywords)
    try:
        subset = select_subset(lib, request)
    except SubsetError:
        return False
    return keywords_reachable(lib, subset)


def _diagnose(cell: Cell, lib: ContentLibrary, seeds: int) -> dict[str, int]:
    """不帶關鍵字組同種類、同階級、同稀有度（層數關鍵字用蓄力骨架），數組得出來的有幾個帶這個關鍵字。

    ``keyword_hit``＝組合器認的（``has_keyword``，含通用規則）；``keyword_exclusive``＝退回路徑認的
    （只看專屬規則）。``plain_ok`` 是 0 → 本身就組不出來；兩個 hit 都是 0 → 缺配方；
    只有 ``keyword_hit`` → 組合器只帶到通用規則，退回路徑不收。"""
    skeleton = _diag_skeleton(cell, lib)
    keywords = () if cell.keyword == NO_KEYWORD else (cell.keyword,)
    out: Counter[str] = Counter()
    for seed in range(seeds):
        try:
            found = compose_with_stats(
                seed, tier=cell.tier, rarity=cell.rarity, skeleton=skeleton, library=lib
            )
        except ComposeError as exc:
            out["plain_fail." + _compose_reason(exc)] += 1
            continue
        skill = found.skill
        if skill.kind != cell.kind:
            out["plain_other_kind"] += 1
            continue
        out["plain_ok"] += 1
        if keywords and has_keyword(skill, cell.keyword, lib.keywords):
            out["keyword_hit"] += 1
        if keywords and skill_has_keywords(skill, keywords, lib):
            out["keyword_exclusive"] += 1
    for key in ("plain_ok", "keyword_hit", "keyword_exclusive"):
        out.setdefault(key, 0)
    return dict(sorted(out.items()))


def run_cell(cell: Cell, seeds: int, thin: int, diag_seeds: int) -> CellResult:
    lib = _library()
    keywords = () if cell.keyword == NO_KEYWORD else (cell.keyword,)
    skeleton = _skeleton_for(cell.kind, lib)
    request = ProposalRequest(
        tier=cell.tier,
        rarity=cell.rarity,
        kind=cell.kind,
        keywords=keywords,
    )
    kind = wanted_kind(lib, request)
    reasons: Counter[str] = Counter()
    samples: dict[str, str] = {}
    designs: Counter[tuple[Any, ...]] = Counter()
    structures: set[str] = set()
    times: list[float] = []
    legal = 0
    for seed in range(seeds):
        started = time.perf_counter()
        reason = ""
        sample = ""
        try:
            found = compose_with_stats(
                seed,
                tier=cell.tier,
                rarity=cell.rarity,
                skeleton=skeleton,
                library=lib,
                keyword=keywords[0] if keywords else None,
            )
        except ComposeError as exc:
            reason, sample = _compose_reason(exc), str(exc)
        else:
            skill = found.skill
            violations = validate_skill(skill, lib)
            if violations:
                reason, sample = f"validate.{violations[0].rule}", violations[0].message
            else:
                reason = _misfit(skill, request, kind, lib)
                sample = skill.id
                if not reason:
                    legal += 1
                    designs[design_key(skill)] += 1
                    structures.add(_structure_key(skill))
        times.append(time.perf_counter() - started)
        if reason:
            reasons[reason] += 1
            samples.setdefault(reason, f"seed {seed}: {sample}")
    top = sorted(designs.items(), key=lambda kv: (-kv[1], repr(kv[0])))[:5]
    result = CellResult(
        keyword=cell.keyword,
        kind=cell.kind,
        tier=cell.tier,
        rarity=cell.rarity,
        seeds=seeds,
        legal=legal,
        designs=len(designs),
        structures=len(structures),
        reasons=dict(sorted(reasons.items())),
        samples=dict(sorted(samples.items())),
        top_designs=[[list(_jsonable(k)), n] for k, n in top],
        blocked_by_design=blocked_by_design(cell, lib),
        reachable=not blocked_by_design(cell, lib) and topic_reachable(cell, lib),
        timing={
            "ms_mean": round(statistics.fmean(times) * 1000, 1) if times else 0.0,
            "ms_median": round(statistics.median(times) * 1000, 1) if times else 0.0,
            "ms_max": round(max(times) * 1000, 1) if times else 0.0,
            "total_s": round(sum(times), 2),
        },
    )
    if len(designs) < thin and not result.blocked_by_design and diag_seeds > 0:
        result.diag = _diagnose(cell, lib, diag_seeds)
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    return value


def _run_one(args: tuple[Cell, int, int, int]) -> CellResult:
    return run_cell(*args)


# ---------------------------------------------------------------------------
# 格子清單、頻率、彙整
# ---------------------------------------------------------------------------


def _world_rules(lib: ContentLibrary) -> WorldRules:
    if lib.world_rules is None:
        raise SystemExit("內容庫沒有大世界規則（content/world/rules.yaml）")
    return lib.world_rules


def player_tiers(lib: ContentLibrary) -> list[int]:
    """玩家拿得到的技能階級：原型升級、大世界成長的階級表，再加機遇「高 1 階」。"""
    world = _world_rules(lib)
    tiers = set(lib.roguelite.offer_tier_by_level) | set(world.hero_growth.skill_tier_by_level)
    if world.opportunity.tier_up_permille > 0:
        tiers.add(max(tiers) + 1)
    return sorted(t for t in tiers if t in lib.ruleset.core.tier_budget)


def tier_weights(lib: ContentLibrary) -> dict[int, int]:
    """各階級的相對頻率（千分比）：大世界成長表與原型升級表的平均；最高一階只在機遇高 1 階。"""
    world = _world_rules(lib)
    tiers = player_tiers(lib)
    tables = (lib.roguelite.offer_tier_by_level, world.hero_growth.skill_tier_by_level)
    share = dict.fromkeys(tiers, 0)
    for table in tables:
        for t in table:
            share[t] += 1000 // len(table) // len(tables)
    top = max(tiers)
    if share.get(top, 0) == 0:
        # 機遇高 1 階：只從最高常駐階級往上，乘機率
        share[top] = share[top - 1] * world.opportunity.tier_up_permille // 1000
    return share


def frequency(cell: Cell, lib: ContentLibrary, tiers: dict[int, int]) -> int:
    """玩家實際遇到這格的相對頻率（只用來排序）：種類比例 × 稀有度權重 × 階級頻率。"""
    kinds = {str(k): v for k, v in lib.composer.whiteboard.kind_permille.items()}
    rarities = {str(k): v for k, v in lib.composer.rarity_weights.items()}
    return kinds.get(cell.kind, 0) * rarities.get(cell.rarity, 0) * tiers.get(cell.tier, 0)


def build_cells(
    lib: ContentLibrary,
    keywords: Sequence[str] | None,
    kinds: Sequence[str],
    tiers: Sequence[int],
    rarities: Sequence[SkillRarity],
) -> list[Cell]:
    rows = [NO_KEYWORD, *lib.keywords.ids()] if keywords is None else list(keywords)
    return [Cell(k, kind, t, r) for k in rows for kind in kinds for t in tiers for r in rarities]


def run_census(
    cells: Iterable[Cell], seeds: int, thin: int, workers: int, diag_seeds: int = DIAG_SEEDS
) -> list[CellResult]:
    jobs = [(c, seeds, thin, diag_seeds) for c in cells]
    if workers <= 1:
        return [_run_one(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=min(workers, MAX_WORKERS)) as pool:
        return list(pool.map(_run_one, jobs, chunksize=1))


def classify(result: CellResult, thin: int) -> str:
    """``n/a``＝骨架稀有度下限擋掉的格子；``empty``／``thin``／``ok`` 照合法數與設計數。"""
    if result.blocked_by_design:
        return "n/a"
    if result.legal == 0:
        return "empty"
    if result.designs < thin:
        return "thin"
    return "ok"


def cause(result: CellResult) -> str:
    """空格、薄格的判斷：規則擋下、缺配方、只帶到通用規則或配方稀少（依出題檢查與診斷）。"""
    diag = result.diag
    keyword = result.keyword != NO_KEYWORD
    checks = (
        (
            bool(result.reasons.get("keyword_not_composable")),
            "內容標記組合器不做（composable: false）",
        ),
        (
            not result.reachable,
            "規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題）",
        ),
        (not diag, ""),
        (diag.get("plain_ok", 0) == 0, "規則或預算擋下：同骨架不帶關鍵字也組不出來"),
        (not keyword, "設計種類少"),
        (diag.get("keyword_exclusive", 0) > 0, "配方稀少：偶爾帶到專屬關鍵字"),
        (
            diag.get("keyword_hit", 0) > 0 or result.reasons.get("not_fit.keyword", 0) > 0,
            "只帶到通用規則：組合器認、退回路徑不收",
        ),
    )
    for hit, text in checks:
        if hit:
            return text
    return "缺配方：規則允許，但組合器這個種類從不帶這個關鍵字"


def stable_view(results: Sequence[CellResult]) -> list[dict[str, Any]]:
    """去掉計時後的結果（確定性比對用）。"""
    out = []
    for r in results:
        data = asdict(r)
        data.pop("timing")
        out.append(data)
    return out


# ---------------------------------------------------------------------------
# 輸出
# ---------------------------------------------------------------------------


def _top_reason(result: CellResult) -> str:
    if not result.reasons:
        return ""
    reason, count = max(result.reasons.items(), key=lambda kv: (kv[1], kv[0]))
    return f"{reason} {count}"


def write_outputs(
    results: Sequence[CellResult],
    lib: ContentLibrary,
    *,
    out_dir: Path,
    name: str,
    params: dict[str, Any],
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    thin = int(params["thin"])
    tiers = tier_weights(lib)
    payload = {
        "format": FORMAT,
        "params": params,
        "tier_weights_permille": tiers,
        "cells": [
            {
                **asdict(r),
                "status": classify(r, thin),
                "cause": cause(r) if classify(r, thin) in ("empty", "thin") else "",
                "frequency": frequency(Cell(r.keyword, r.kind, r.tier, r.rarity), lib, tiers),
            }
            for r in results
        ],
    }
    json_path = out_dir / f"{name}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md_path = out_dir / f"{name}.md"
    md_path.write_text(_markdown(results, lib, params, tiers), encoding="utf-8")
    return json_path, md_path


def _markdown(
    results: Sequence[CellResult],
    lib: ContentLibrary,
    params: dict[str, Any],
    tiers: dict[int, int],
) -> str:
    thin = int(params["thin"])
    status = Counter(classify(r, thin) for r in results)
    gaps = Counter(classify(r, thin) for r in results if r.reachable)
    lines = [
        "# 組合器配方盤點摘要",
        "",
        f"格式 `{FORMAT}`；種子 0～{params['seeds'] - 1}；薄格門檻：不同設計 < {thin}。"
        "由 `scripts/recipe_census.py` 產生，計時欄每次不同。",
        "",
        f"- 格子 {len(results)}：正常 {status['ok']}、薄 {status['thin']}、空 {status['empty']}、"
        f"設計上不存在 {status['n/a']}（骨架稀有度下限：被動至少 epic、反應至少 rare）",
        f"- 其中遊戲會出題（出題檢查通過）的：空 {gaps['empty']}、薄 {gaps['thin']}；"
        "其餘空格是規則上就沒有專屬來源（遊戲不出這題）",
        "",
        "## 依關鍵字（不含設計上不存在；「會出題」＝出題檢查通過的空格與薄格）",
        "",
        "| 關鍵字 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |",
        "|---|---|---|---|---|---|",
    ]
    for key, label in (("keyword", "關鍵字"), ("kind", "種類")):
        if key == "kind":
            lines += [
                "",
                "## 依種類",
                "",
                f"| {label} | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |",
                "|---|---|---|---|---|---|",
            ]
        for value in dict.fromkeys(getattr(r, key) for r in results):
            mine = [r for r in results if getattr(r, key) == value]
            c = Counter(classify(r, thin) for r in mine)
            g = Counter(classify(r, thin) for r in mine if r.reachable)
            lines.append(
                f"| {value} | {c['empty']} | {c['thin']} | {c['ok']} | {g['empty']} | {g['thin']} |"
            )
    flagged = [r for r in results if classify(r, thin) in ("empty", "thin")]
    flagged.sort(
        key=lambda r: (
            -frequency(Cell(r.keyword, r.kind, r.tier, r.rarity), lib, tiers),
            r.keyword,
            r.kind,
            r.tier,
            r.rarity,
        )
    )
    lines += [
        "",
        "## 空格與薄格（依玩家遇到的頻率排序）",
        "",
        "| 關鍵字 | 種類 | 階 | 稀有度 | 狀態 | 會出題 | 合法 | 設計 | 主要原因 | 判斷 | 中位 ms |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in flagged:
        lines.append(
            f"| {r.keyword} | {r.kind} | {r.tier} | {r.rarity} | {classify(r, thin)} | "
            f"{'是' if r.reachable else '否'} | {r.legal} | {r.designs} | {_top_reason(r)} | "
            f"{cause(r)} | "
            f"{r.timing.get('ms_median', '')} |"
        )
    lines += [
        "",
        "## 全部格子",
        "",
        "| 關鍵字 | 種類 | 階 | 稀有度 | 合法 | 設計 | 主要原因 | 平均 ms | 中位 ms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.blocked_by_design:
            continue
        lines.append(
            f"| {r.keyword} | {r.kind} | {r.tier} | {r.rarity} | {r.legal} | {r.designs} | "
            f"{_top_reason(r)} | {r.timing.get('ms_mean', '')} | "
            f"{r.timing.get('ms_median', '')} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 命令列
# ---------------------------------------------------------------------------


def _csv(text: str | None) -> list[str] | None:
    return None if text is None else [t for t in text.split(",") if t]


def _rarity(text: str) -> SkillRarity:
    for rarity in ("common", "rare", "epic", "legendary"):
        if text == rarity:
            return rarity
    raise SystemExit(f"未知的稀有度 {text!r}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--seeds", type=int, default=200, help="每格種子數（0～N-1）")
    parser.add_argument("--thin", type=int, default=DEFAULT_THIN, help="薄格門檻（不同設計數）")
    parser.add_argument("--workers", type=int, default=1, help=f"平行行程數（最多 {MAX_WORKERS}）")
    parser.add_argument("--keywords", help=f"只跑這些關鍵字（逗號分隔；{NO_KEYWORD} ＝不指定）")
    parser.add_argument("--kinds", default=",".join(KINDS))
    parser.add_argument("--tiers", help="逗號分隔；預設＝玩家拿得到的所有階級")
    parser.add_argument("--rarities", default=",".join(RARITIES))
    parser.add_argument("--diag-seeds", type=int, default=DIAG_SEEDS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--name", default="census", help="輸出檔名（不含副檔名）")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    lib = load_library()
    tiers_arg = _csv(args.tiers)
    tiers = [int(t) for t in tiers_arg] if tiers_arg else player_tiers(lib)
    kinds = _csv(args.kinds) or list(KINDS)
    rarities = [_rarity(r) for r in _csv(args.rarities) or RARITIES]
    cells = build_cells(lib, _csv(args.keywords), kinds, tiers, rarities)
    started = time.perf_counter()
    results = run_census(cells, args.seeds, args.thin, args.workers, args.diag_seeds)
    elapsed = time.perf_counter() - started
    params = {
        "seeds": args.seeds,
        "thin": args.thin,
        "kinds": kinds,
        "tiers": tiers,
        "rarities": rarities,
        "diag_seeds": args.diag_seeds,
    }
    json_path, md_path = write_outputs(
        results, lib, out_dir=args.out_dir, name=args.name, params=params
    )
    status = Counter(classify(r, args.thin) for r in results)
    print(
        f"{len(results)} 格（{elapsed:.0f} 秒）：正常 {status['ok']}、薄 {status['thin']}、"
        f"空 {status['empty']}、設計上不存在 {status['n/a']} → {json_path.name}、{md_path.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
