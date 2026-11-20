"""一輪營火畫面的 vitest 與開發頁夾具：``client/src/run/fixtures/run_campfire.json``（HC-3）。

用法::

    uv run python scripts/export_campfire_fixture.py
    uv run python scripts/export_flash_choice_fixture.py   # 選變體夾具的主角沿用這份，接著重產

整份是伺服器真的跑出來的 ``RunResponse``（``run_response``，和 ``GET /api/runs/{id}``
同一個函式），不是手寫：第一個開發起始包（點燃＋標記）、種子 :data:`SEED`，AI 代打
（閃現策略 ``mixed``）到第 3 場後的營火。這個種子停下來時剛好有測試要的幾種狀態：

- 第一招閃到第 3 次（含大變化，重閃三格、可傳承兩個小變化）；
- 一招完整技能（第 3 場後的完整技能三選一）；
- 還沒閃過、上場用過、現在可以閃的一招（技能卡的「可以閃現了」）；
- 穿著帶詞條的裝備，背包裡有換下來的武器（營火可以免費換裝）。

唯一改過的是靈感點：代打把點數花光了，這裡照 ``export_flash_choice_fixture.py`` 的重閃組設成
:data:`INSIGHT`，營火畫面的閃現、重閃鈕才會是能按的樣子。數值全是現在的單位（×10，HC-2 待決 3）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from trpg.api.run_presenter import run_response
from trpg.api.runs import RunSession
from trpg.content.library import load_library
from trpg.roguelite import auto_play
from trpg.roguelite.start import new_dev_run
from trpg.roguelite.state import RunState

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "client" / "src" / "run" / "fixtures" / "run_campfire.json"
SEED = 25
"""開發起始包第一個（``dev_blaze``）的這個種子，代打到第 3 場後的營火時有上面四種狀態
（HC-3 掃種子 1～59 挑的；``all`` 策略會把能閃的都閃掉）。"""
AFTER_BATTLE = 3
INSIGHT = 8
RUN_ID = "c55951351479"
"""沿用舊夾具的 ID（只是一個字串，畫面不顯示）。"""


def _at_campfire(run: RunState, _battle: object) -> bool:
    return run.node.kind == "campfire" and run.battles_done >= AFTER_BATTLE


def main() -> int:
    library = load_library()
    run = new_dev_run(library, library.dev_starters.packs[0].id, SEED)
    run, _ = auto_play(library, run, stop=_at_campfire, flash_policy="mixed")
    if not _at_campfire(run, None):
        print(
            f"種子 {SEED} 沒有走到第 {AFTER_BATTLE} 場後的營火（內容改過？換一個種子）",
            file=sys.stderr,
        )
        return 1
    run = run.model_copy(update={"insight": INSIGHT})
    response = run_response(RunSession(RUN_ID, library, run)).model_dump(mode="json")
    flashes = response["hero"]["flash"]
    major = response["hero"]["flash_rules"]["major_flash"]
    checks = {
        "閃到大變化的一招": any(len(f["records"]) == major and not f["complete"] for f in flashes),
        "完整技能": any(f["complete"] for f in flashes),
        "現在可以閃的一招": any(
            not f["records"] and not f["complete"] and f["can_flash"] for f in flashes
        ),
        "帶詞條的裝備": any(
            e["item"] is not None and e["item"]["affixes"] for e in response["hero"]["equipment"]
        ),
        "背包裡的裝備": bool(response["hero"]["backpack"]),
    }
    missing = [k for k, ok in checks.items() if not ok]
    if missing:
        print(f"種子 {SEED} 少了：{'、'.join(missing)}（內容改過？換一個種子）", file=sys.stderr)
        return 1
    OUT.write_text(
        json.dumps(response, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"已寫入 {OUT.relative_to(ROOT).as_posix()}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
