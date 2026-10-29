"""閃現變化提議的評估（4-L9 加項；Phase 3W-7）。

用法::

    uv run python scripts/eval_flash_llm.py                       # Mock（不需網路與金鑰）
    uv run python scripts/eval_flash_llm.py --skills 30 --csv out.csv
    uv run python scripts/eval_flash_llm.py --real                # 真模型：先啟動本機模型

輸出通過率、一次通過率、補位率、退回率（超過 ``fallback_alert_permille`` 時提醒）、平均嘗試次數、
各錯誤代碼、各類別與模板命中，以及大變化選項的名稱抽樣。調整建議由 PM 決定，腳本不自動改任何設定。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trpg.content.library import load_library
from trpg.llm import OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.flash_eval import evaluate_flash, pick_skills
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--skills", type=int, default=20, help="評估的技能數（預設 20）")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--real", action="store_true", help="用 config/llm.toml 的本機模型")
    parser.add_argument("--csv", type=Path, default=None, help="另存每題明細")
    args = parser.parse_args(argv)
    library = load_library()
    config = load_llm_config()
    if args.real:
        client = OpenAICompatClient(config)
        source: LlmFlashSource = LlmFlashSource(client, max_attempts=config.max_retries)
        naming = lambda _id, _seed: client  # noqa: E731
    else:
        source = mock_flash_source(library, max_attempts=config.max_retries)

        def naming(skill_id: str, seed: int):  # type: ignore[no-untyped-def]
            return mock_naming_client(library, library.skills[skill_id], seed)

    skills = pick_skills(library, args.skills)
    result = evaluate_flash(
        library,
        source,
        skills,
        seed=args.seed,
        naming=naming,
        alert_permille=config.fallback_alert_permille,
    )
    print("\n".join(result.stats.summary_lines()))
    print("名稱抽樣　　　" + ("（無）" if not result.stats.name_samples else ""))
    for sample in result.stats.name_samples:
        print(f"  - {sample}")
    if args.csv is not None:
        args.csv.write_text("\n".join(result.csv_lines()) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
