"""完整技能生成的評估（Phase 4-L9）：升級候選、強制測試、自由測試。

用法::

    uv run python scripts/eval_llm_skills.py                          # Mock（不需網路與金鑰）
    uv run python scripts/eval_llm_skills.py --real --out-dir docs/phases/4-L9
    uv run python scripts/eval_llm_skills.py --real --suites forced --forced-per 3

輸出 Markdown（各組摘要、錯誤代碼表、強制測試每個原語的通過情形、自由測試的選中率與隨機組合器對照、
主題一致性抽樣）與 CSV（每題一列，不含 prompt）。平行請求數預設 8（本機模型的 ``MAX_SEQS``）。
調整建議由 PM 決定，腳本不自動改任何設定、hint、權重或 schema。
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.llm import load_llm_config
from trpg.llm.candidate_source import mock_client_for, mock_naming_client
from trpg.llm.skill_eval import (
    ClientFactory,
    EvalItem,
    ItemClient,
    ItemResult,
    NamingFactory,
    composer_baseline,
    csv_text,
    describe,
    errors_csv_text,
    forced_items,
    forced_table,
    free_items,
    free_table,
    real_client_factory,
    run_items,
    suite_summary,
    upgrade_items,
)

SUITES = ("upgrade", "forced", "free")
THEME_SAMPLES = 10


def _mock_factories(library: ContentLibrary, attempts: int) -> tuple[ClientFactory, NamingFactory]:
    def clients(item: EvalItem) -> ItemClient:
        return ItemClient(mock_client_for(library, item.request, item.seed, attempts))

    def naming(item: EvalItem, skill: SkillDef, _client: ItemClient) -> ItemClient:
        return ItemClient(mock_naming_client(library, skill, item.seed))

    return clients, naming


def _same_client(_item: EvalItem, _skill: SkillDef, client: ItemClient) -> ItemClient:
    return client


def _progress(label: str, quiet: bool):  # type: ignore[no-untyped-def]
    def report(done: int, total: int) -> None:
        if not quiet and (done % 10 == 0 or done == total):
            print(f"[{label}] {done}/{total}", file=sys.stderr, flush=True)

    return report


def _theme_lines(library: ContentLibrary, results: Sequence[ItemResult]) -> list[str]:
    picked = [r for r in results if r.ok and (r.item.request.keywords or r.item.request.theme)]
    picked += [r for r in results if r.ok and r not in picked]
    lines = [
        "| # | 題目（關鍵字／主題／核心） | 名稱 | 結構 | 概念 |",
        "|---:|---|---|---|---|",
    ]
    for result in picked[:THEME_SAMPLES]:
        req = result.item.request
        assert result.outcome is not None
        topic = "、".join(req.keywords) or "—"
        topic += f"／{req.theme or '—'}／{req.core_primitive or '—'}"
        lines.append(
            f"| {result.item.index} | {topic} | {result.name} | "
            f"{describe(library, result.outcome.skill)} | {result.concept} |"
        )
    return lines


def _low_forced(results: Sequence[ItemResult]) -> list[str]:
    by: dict[str, list[ItemResult]] = {}
    for result in results:
        by.setdefault(result.item.request.core_primitive or "?", []).append(result)
    return [p for p, group in by.items() if sum(r.ok for r in group) * 3 < len(group) * 2]


def _items(library: ContentLibrary, args: argparse.Namespace, suite: str) -> list[EvalItem]:
    if suite == "upgrade":
        return upgrade_items(library, args.upgrade, seed=args.seed)
    if suite == "forced":
        return forced_items(library, per=args.forced_per, seed=args.seed)
    return free_items(library, args.free, seed=args.seed)


def _section(
    library: ContentLibrary,
    suite: str,
    *,
    results: list[ItemResult],
    wall: float,
    args: argparse.Namespace,
    alert: int,
) -> list[str]:
    title = {"upgrade": "升級候選", "forced": "強制測試", "free": "自由測試"}[suite]
    lines = [f"## {title}", "", f"- 牆鐘時間 {wall:.0f} 秒（平行 {args.workers}）"]
    lines += suite_summary(results, alert_permille=alert)
    if suite == "upgrade":
        lines += ["", "### 主題一致性抽樣", "", *_theme_lines(library, results)]
    if suite == "forced":
        low = _low_forced(results)
        lines += ["", "### 每個核心原語", "", *forced_table(library, results), ""]
        lines.append("通過率低於 2/3 的原語：" + ("、".join(f"`{p}`" for p in low) or "無"))
    if suite == "free":
        baseline = composer_baseline(library, args.baseline, seed=args.seed)
        lines += [
            "",
            "### 選單與選中率（對照隨機組合器）",
            "",
            *free_table(library, results, baseline),
        ]
    return [*lines, ""]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--real", action="store_true", help="用 config/llm.toml 的本機模型")
    parser.add_argument("--suites", default=",".join(SUITES), help="逗號分隔：upgrade,forced,free")
    parser.add_argument("--upgrade", type=int, default=50, help="升級候選題數（預設 50）")
    parser.add_argument("--forced-per", type=int, default=3, help="強制測試每個原語題數（預設 3）")
    parser.add_argument("--free", type=int, default=300, help="自由測試題數（預設 300）")
    parser.add_argument("--baseline", type=int, default=300, help="隨機組合器對照的技能數")
    parser.add_argument("--workers", type=int, default=8, help="平行請求數（預設 8）")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", type=Path, default=None, help="寫入 Markdown 與 CSV 的資料夾")
    parser.add_argument("--tag", default="skills", help="輸出檔名前綴")
    parser.add_argument("--quiet", action="store_true", help="不印進度")
    args = parser.parse_args(argv)
    library = load_library()
    config = load_llm_config()
    if args.real:
        clients: ClientFactory = real_client_factory(config)
        naming: NamingFactory = _same_client
        label = f"{config.model}（{config.base_url}）"
    else:
        clients, naming = _mock_factories(library, config.max_retries)
        label = "Mock（proposal_from_skill）"
    report = [
        f"# 技能生成評估（{label}）",
        "",
        f"種子 {args.seed}；每題最多 {config.max_retries} 次",
        "",
    ]
    every: list[ItemResult] = []
    for suite in [s for s in args.suites.split(",") if s in SUITES]:
        items = _items(library, args, suite)
        start = time.perf_counter()
        results = run_items(
            library,
            items,
            clients,
            max_attempts=config.max_retries,
            workers=args.workers,
            naming=naming if suite == "upgrade" else None,
            progress=_progress(suite, args.quiet),
        )
        wall = time.perf_counter() - start
        report += _section(
            library,
            suite,
            results=results,
            wall=wall,
            args=args,
            alert=config.fallback_alert_permille,
        )
        every += results
    text = "\n".join(report)
    print(text)
    if args.out_dir is not None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / f"{args.tag}.md").write_text(text, encoding="utf-8")
        (args.out_dir / f"{args.tag}.csv").write_text(csv_text(every), encoding="utf-8")
        errors = errors_csv_text(every)
        (args.out_dir / f"{args.tag}_errors.csv").write_text(errors, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
