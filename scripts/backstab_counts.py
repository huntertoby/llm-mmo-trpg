"""背刺次數對照表（Phase 3C-6a 8.2B）：10 張地圖 × N 種子，預設陣容與 ``build_assassin``。

用法::

    uv run python scripts/backstab_counts.py [--seeds 5] [--out table.json]

只輸出摘要表（Markdown）。改前／改後對照：在舊版原始碼（``git archive`` 匯出）執行同一支腳本，
把 ``--out`` 的 JSON 存起來再比對。
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from trpg.cli.main import main as cli_main

MAPS = (
    "bridge_chasm",
    "cliff_outpost",
    "dark_forest",
    "frozen_lake",
    "lava_crossing",
    "narrow_halls",
    "oil_depot",
    "open_plain",
    "ruined_fort",
    "swamp",
)
KINDS = ("backstab:ally", "backstab:enemy", "ambush:ally", "ambush:enemy")


def _run(maps: str, seeds: int, ally_build: str | None) -> dict[str, dict[str, int]]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "r.json"
        argv = ["sim", "maps", "--maps", maps, "--seeds", str(seeds), "--json", str(out)]
        if ally_build:
            argv += ["--ally-build", ally_build]
        stdout, sys.stdout = sys.stdout, open(Path(tmp) / "log.txt", "w", encoding="utf-8")  # noqa: SIM115
        try:
            cli_main(argv)
        finally:
            sys.stdout.close()
            sys.stdout = stdout
        rows = json.loads(out.read_text(encoding="utf-8"))
    return {r["name"]: r["positional_events"] for r in rows}


def collect(seeds: int) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {}
    for label, build in (("default", None), ("assassin", "build_assassin")):
        per_map: dict[str, dict[str, int]] = {}
        for name in MAPS:
            counts = _run(name, seeds, build).get(name, {})
            per_map[name] = {k: counts.get(k, 0) for k in KINDS}
        result[label] = per_map
    return result


def render(data: dict[str, dict[str, dict[str, int]]], seeds: int) -> str:
    lines = [f"背刺次數（每張地圖 {seeds} 個種子合計；我方／敵方）", ""]
    for label in ("default", "assassin"):
        lines += [
            f"陣容：{label}",
            "",
            "| 地圖 | 我方背刺 | 敵方背刺 | 我方偷襲 | 敵方偷襲 |",
            "|---|---|---|---|---|",
        ]
        total = dict.fromkeys(KINDS, 0)
        for name in MAPS:
            row = data[label][name]
            lines.append(f"| {name} | " + " | ".join(str(row[k]) for k in KINDS) + " |")
            for k in KINDS:
                total[k] += row[k]
        lines.append("| 合計 | " + " | ".join(str(total[k]) for k in KINDS) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--out", type=Path, default=None, help="另存原始計數 JSON")
    args = parser.parse_args()
    data = collect(args.seeds)
    if args.out is not None:
        args.out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(render(data, args.seeds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
