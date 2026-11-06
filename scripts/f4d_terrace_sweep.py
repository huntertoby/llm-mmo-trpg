"""6F-4d 第 4 項：雨中梯田固定戰 ``terrace_clash`` 的陣容掃描（新手第 3 步一路走過去）。

沿用 ``scripts/f4c_terrace_sweep.py`` 的玩法（先打完新手第 1、2 步，再從竹林小徑走到梯田固定戰，
路上碰到的每一場都打；BFS、效用 AI 代打、三選一跳過）。只在記憶體裡換掉 ``terrace_clash`` 的陣容
（敵方、第三方），巡邏照目前內容（``terrace_patrol``）。

目標：**每種開局** 的主角倒下（第 3 步路上倒下過）≤ 40%。每種開局預設 40 人（壓低波動；大世界種子
每次建世界都不同）。只印摘要表；平行跑（``-j``，預設 4，上限 8）。

    uv run python scripts/f4d_terrace_sweep.py [每種開局的人數＝40] [-j 4] [--current] [--only 0,2]

``--current``：只量目前的內容（不換陣容）。
"""

from __future__ import annotations

import dataclasses
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import f4_newbie_sim as sim  # type: ignore[import-not-found]  # 一次性量測腳本，同目錄匯入（已 sys.path.insert）
from f4c_terrace_sweep import Step3, _step3  # type: ignore[import-not-found]  # 一次性量測腳本，同目錄匯入（已 sys.path.insert）
from trpg.api import world as api_world
from trpg.api.app import create_app
from trpg.api.world import START_REGION
from trpg.content.library import ContentLibrary, load_library
from trpg.world.actions import AcceptQuestAction

GROUP = "terrace_clash"
CURRENT = "目前內容"
CANDIDATES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "原本：2 盜賊｜修士劍客＋雜兵": (("bandit", "bandit"), ("sect_swordsman", "sect_acolyte")),
    "新手盜賊＋盜賊｜劍客＋雜兵": (("bandit_rookie", "bandit"), ("sect_swordsman", "sect_acolyte")),
    "2 新手盜賊｜劍客＋雜兵": (
        ("bandit_rookie", "bandit_rookie"),
        ("sect_swordsman", "sect_acolyte"),
    ),
    "2 盜賊｜2 雜兵": (("bandit", "bandit"), ("sect_acolyte", "sect_acolyte")),
    "新手盜賊＋盜賊｜2 雜兵": (("bandit_rookie", "bandit"), ("sect_acolyte", "sect_acolyte")),
    "2 新手盜賊｜2 雜兵": (("bandit_rookie", "bandit_rookie"), ("sect_acolyte", "sect_acolyte")),
    # 第二輪（第一輪只有「2 新手盜賊｜劍客＋雜兵」每種開局都 ≤ 40%，巨劍剛好 40%）
    "2 新手盜賊｜修士劍客": (("bandit_rookie", "bandit_rookie"), ("sect_swordsman",)),
    "2 新手盜賊｜雜兵": (("bandit_rookie", "bandit_rookie"), ("sect_acolyte",)),
}
TARGET = 40
"""每種開局主角倒下的上限（%）。"""


def _variant(
    library: ContentLibrary, units: tuple[str, ...], third: tuple[str, ...]
) -> ContentLibrary:
    """記憶體裡換掉 ``terrace_clash`` 的敵方與第三方。"""
    table = library.world_encounters["cloud_ridge"]
    groups = tuple(
        g.model_copy(update={"units": units, "third": third}) if g.id == GROUP else g
        for g in table.groups
    )
    encounters = {
        **library.world_encounters,
        "cloud_ridge": table.model_copy(update={"groups": groups}),
    }
    return dataclasses.replace(library, world_encounters=encounters)


def _job(args: tuple[str, str, int]) -> tuple[str, str, Step3]:
    """一個候選 × 一種開局，``runs`` 個角色。"""
    candidate, start, runs = args
    api_world.spawn_region = lambda _library: START_REGION  # type: ignore[assignment]  # 跳過主城
    library = load_library()
    if candidate != CURRENT:
        library = _variant(library, *CANDIDATES[candidate])
    weapon, keywords = sim.STARTS[start]
    tally = Step3()
    for i in range(runs):
        with tempfile.TemporaryDirectory() as tmp:
            store = create_app(library, save_dir=Path(tmp)).state.world
            store.clock = lambda: sim.NOON
            cid = store.create(f"s{i}", weapon, keywords, seed=1000 + i).character_id
            store.act(cid, AcceptQuestAction(quest="starter_ferry"))
            scratch = sim.Tally()
            if not all(sim._play(store, cid, m, g, scratch) for m, g in sim.FIGHTS[:2]):
                continue
            _step3(store, cid, tally)
    return candidate, start, tally


def _pct(n: int, d: int) -> str:
    return f"{n}/{d}（{n * 100 // max(1, d)}%）"


def _row(name: str, per: dict[str, Step3]) -> str:
    cells = [_pct(per[s].down, per[s].reached) for s in sim.STARTS]
    total = Step3()
    for t in per.values():
        total.add(t)
    worst = max(t.down * 100 // max(1, t.reached) for t in per.values())
    ok = "達標" if worst <= TARGET else "—"
    return (
        f"| {name} | {' | '.join(cells)} | {_pct(total.down, total.reached)} | {worst}% {ok} | "
        f"{_pct(total.won_fixed, total.reached)} | {total.down_patrol}／{total.down_fixed} |"
    )


def _arg(flag: str) -> str | None:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None


def main() -> None:
    numbers = [a for i, a in enumerate(sys.argv[1:], 1) if a.isdigit() and sys.argv[i - 1] != "-j"]
    runs = int(numbers[0]) if numbers else 40
    workers = min(8, int(_arg("-j") or 4))
    names = [CURRENT] if "--current" in sys.argv else list(CANDIDATES)
    only = _arg("--only")
    if only:
        names = [n for i, n in enumerate(names) if str(i) in only.split(",")]
    jobs = [(n, s, runs) for n in names for s in sim.STARTS]
    results: dict[str, dict[str, Step3]] = {n: {} for n in names}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for candidate, start, tally in pool.map(_job, jobs):
            results[candidate][start] = tally
    print(f"每種開局 {runs} 人；分母＝打到第 3 步的角色數；倒下＝第 3 步路上主角倒下過")
    heads = " | ".join(f"{s} 倒下" for s in sim.STARTS)
    rest = "合計倒下 | 最差開局（≤40%） | 固定戰勝 | 倒在巡邏／固定戰"
    print(f"| 固定戰陣容（敵方｜第三方） | {heads} | {rest} |")
    print("|" + "---|" * (len(sim.STARTS) + 5))
    for name in names:
        print(_row(name, results[name]))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    main()
