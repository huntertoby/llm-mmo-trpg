"""BAL-9 掃描：近戰朝 Boss 靠近權重（boss_approach）與 Boss 輪數旋鈕（只在模擬覆寫）。

用法::

    uv run python scripts/bal9_sweep.py boss --values 0,3,6,10 --seeds 30 --jobs 8 \
        --out docs/phases/BAL-9/boss_approach.md
    uv run python scripts/bal9_sweep.py rounds --configs "6;6,1500;6,0,1" --seeds 30 --jobs 8 \
        --out docs/phases/BAL-9/boss_rounds.md

``boss``：每個 ``boss_approach`` 值跑 Boss 戰（有召喚 3 包 ＋ 無召喚 3 包，每包 ``--seeds`` 場）。
``rounds``：每組設定 ``boss_approach,boss_hp_permille,focus``：
Boss HP 倍率（‰；0 ＝ 不改，在 library 副本上改頭目範本 HP）、
``focus``（1 ＝ 召喚物 AI 的 ``auto_focus_boss`` 強制開啟；0 ＝ 現行）。
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from trpg.content.library import ContentLibrary, load_library
from trpg.sim.attrition import AttritionConfig, run_boss_config


def with_boss_approach(library: ContentLibrary, value: int) -> ContentLibrary:
    """每個行為模式的 ``boss_approach`` 設為 ``value``（library 副本）。"""
    table = library.ai_profiles
    profiles = [
        p.model_copy(update={"weights": p.weights.model_copy(update={"boss_approach": value})})
        for p in table.profiles
    ]
    return dataclasses.replace(library, ai_profiles=table.model_copy(update={"profiles": profiles}))


def with_focus_boss(library: ContentLibrary) -> ContentLibrary:
    table = library.ai_profiles
    profiles = [
        p.model_copy(update={"summon": p.summon.model_copy(update={"auto_focus_boss": True})})
        for p in table.profiles
    ]
    return dataclasses.replace(library, ai_profiles=table.model_copy(update={"profiles": profiles}))


def with_boss_hp(library: ContentLibrary, permille: int) -> ContentLibrary:
    """Boss 戰頭目（陣容第一名）的範本 HP ×‰（library 副本；其餘不動）。"""
    boss_tpl_id = library.roguelite.boss.enemies[0]
    tpl = library.units[boss_tpl_id]
    new_hp = tpl.max_hp * permille // 1000
    units = {**library.units, boss_tpl_id: tpl.model_copy(update={"max_hp": new_hp})}
    return dataclasses.replace(library, units=units)


def fmt(label: str, library: ContentLibrary, seeds: int, jobs: int) -> str:
    r = run_boss_config(library, AttritionConfig(), list(range(seeds)), jobs=jobs)
    return (
        f"| {label} | {r.summon_win:.1f}%（{r.summon_n}）／{r.summon_rounds:.1f} "
        f"| {r.plain_win:.1f}%（{r.plain_n}）／{r.plain_rounds:.1f} |"
    )


HEAD = "| 設定 | Boss 有召喚勝率／輪數 | Boss 無召喚勝率／輪數 |\n|---|---|---|\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("boss", "rounds"))
    p.add_argument("--values", default="0,3,6,10")
    p.add_argument("--configs", default="")
    p.add_argument("--seeds", type=int, default=30)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    base = load_library()
    rows: list[str] = []
    if args.mode == "boss":
        for v in (int(x) for x in args.values.split(",")):
            lib = with_boss_approach(base, v)
            rows.append(fmt(f"boss_approach={v}", lib, args.seeds, args.jobs))
            print(rows[-1], flush=True)
    else:
        for part in (c.strip() for c in args.configs.split(";") if c.strip()):
            appr, hp, focus = (int(x) for x in [*part.split(","), "0", "0"][:3])
            lib = with_boss_approach(base, appr)
            if hp:
                lib = with_boss_hp(lib, hp)
            if focus:
                lib = with_focus_boss(lib)
            label = f"approach={appr} hp={hp or '—'}‰ focus={focus}"
            rows.append(fmt(label, lib, args.seeds, args.jobs))
            print(rows[-1], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(HEAD + "\n".join(rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
