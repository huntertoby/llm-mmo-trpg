"""6F-4b：起始兩招的觸發關係（#129）前後對照。

「前」＝把 ``whiteboard.exploit`` 設成 ``None``（不生成利用者白板，等同 6F-4 的行為）；
「後」＝目前的
內容。每種開局跑 ``runs`` 個種子（預設 10），輸出有觸發關係的次數與起始兩招名稱。

    uv run python scripts/archive/f4b_starter_links.py [runs]
"""

from __future__ import annotations

import dataclasses
import sys
from collections import Counter

from trpg.content.library import ContentLibrary, load_library
from trpg.roguelite.start import links_between, new_keyword_run

STARTS = {
    "A 火焰法杖 點燃＋帶電": ("fire_staff", ("ignite", "charged")),
    "B 匕首 冰凍＋隱蔽": ("dagger", ("frozen", "concealed")),
    "巨劍 倒地＋撞擊": ("greatsword", ("prone", "collision")),
    "弓 標記＋高處": ("bow", ("marked", "high_ground")),
    "（參考）雷電法杖 潮濕＋帶電": ("lightning_staff", ("wet", "charged")),
}


def _without_exploits(library: ContentLibrary) -> ContentLibrary:
    whiteboard = library.composer.whiteboard.model_copy(update={"exploit": None})
    composer = library.composer.model_copy(update={"whiteboard": whiteboard})
    return dataclasses.replace(library, composer=composer)


def _measure(library: ContentLibrary, runs: int) -> dict[str, tuple[int, Counter[str]]]:
    out: dict[str, tuple[int, Counter[str]]] = {}
    for name, (weapon, keywords) in STARTS.items():
        linked, pairs = 0, Counter[str]()
        for seed in range(1, runs + 1):
            run = new_keyword_run(library, weapon, keywords, seed)
            known = {**library.skills, **{s.id: s for s in run.generated_skills}}
            first, second = (known[s] for s in run.hero.skills[:2])
            if links_between(library, first, second):
                linked += 1
            pairs[f"{first.name_zh}＋{second.name_zh}"] += 1
        out[name] = (linked, pairs)
    return out


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    library = load_library()
    before = _measure(_without_exploits(library), runs)
    after = _measure(library, runs)
    print("| 開局 | 前（6F-4） | 後（6F-4b） | 後的起始兩招（次數） |")
    print("|---|---|---|---|")
    for name in STARTS:
        b, _ = before[name]
        a, pairs = after[name]
        shown = "、".join(f"{p} ×{n}" for p, n in pairs.most_common(4))
        print(f"| {name} | {b}/{runs} | {a}/{runs} | {shown} |")


if __name__ == "__main__":
    main()
