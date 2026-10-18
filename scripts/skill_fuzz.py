"""隨機技能的執行驗收（Phase 2B-3 5.2）。

用法::

    uv run python scripts/skill_fuzz.py --count 1000 --seed-start 0
    uv run python scripts/skill_fuzz.py --show-battle 123      # 印出該種子技能的 AI 對戰紀錄

摘要印在標準輸出（不含時間，兩次執行完全相同）；執行時間印在標準錯誤。
有任何問題（組合失敗、未通過驗證、不可施放、例外）時結束代碼為 1。
"""

from __future__ import annotations

import argparse
import sys
import time

from trpg.cli.render import describe_event
from trpg.content.library import load_library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import RoundStarted
from trpg.engine.runner import run_battle
from trpg.sim.skill_fuzz import battle_setup, format_report, run_fuzz
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.skill_yaml import skill_to_yaml


def _show_battle(seed: int) -> int:
    library = load_library()
    skill = compose_random_skill(seed, library=library)
    print(skill_to_yaml(skill))
    setup = battle_setup(library, skill)

    def on_step(_step: object, result: object) -> None:
        state = result.state  # type: ignore[attr-defined]
        for event in result.events:  # type: ignore[attr-defined]
            if isinstance(event, RoundStarted):
                print(f"=== 第 {event.round} 輪 ===")
                continue
            text = describe_event(event, state)
            if text is not None:
                print(text)

    run = run_battle(setup, seed, UtilityAI(library.ai_profiles), on_step=on_step)
    winner = "平手" if run.state.winner is None else run.state.winner.display_name + "勝利"
    print(f"勝方：{winner}（第 {run.state.round} 輪結束）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=1000, help="技能個數（預設 1000）")
    parser.add_argument("--seed-start", type=int, default=0, help="起始種子（預設 0）")
    parser.add_argument(
        "--show-battle", type=int, default=None, help="只印出這個種子的 AI 對戰紀錄"
    )
    args = parser.parse_args(argv)
    if args.show_battle is not None:
        return _show_battle(args.show_battle)
    library = load_library()
    started = time.perf_counter()
    report = run_fuzz(library, count=args.count, seed_start=args.seed_start)
    elapsed = time.perf_counter() - started
    text = format_report(report)
    sys.stdout.write(text)
    print(f"執行時間 {elapsed:.1f} 秒", file=sys.stderr)
    clean = not report.compose_errors and all(
        o.violations == 0 and o.castable and o.error is None for o in report.outcomes
    )
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
