"""6F-4c：起始兩招的觸發關係（#129）。

每種開局跑 ``runs`` 個種子（預設 10），輸出：

- 「關鍵字」：兩招有關鍵字層級的觸發關係
  （:func:`~trpg.roguelite.start.links_between`，6F-4b 的量法）；
- 「造得出」：有觸發關係，而且第 2 招若是條件傷害，條件對象是第 1 招實際造得出來的
  （:func:`~trpg.skillgen.exploit_match.made_targets`，6F-4c 第 2 項）；
- 起始兩招名稱（最常見的 4 組）。

    uv run python scripts/f4c_starter_links.py [runs]
"""

from __future__ import annotations

import sys
from collections import Counter

from trpg.content.library import load_library
from trpg.roguelite.start import links_between, new_keyword_run
from trpg.skillgen.exploit_match import condition_target, made_targets

STARTS = {
    "A 火焰法杖 點燃＋帶電": ("fire_staff", ("ignite", "charged")),
    "B 匕首 冰凍＋隱蔽": ("dagger", ("frozen", "concealed")),
    "巨劍 倒地＋撞擊": ("greatsword", ("prone", "collision")),
    "弓 標記＋高處": ("bow", ("marked", "high_ground")),
    "（參考）雷電法杖 潮濕＋帶電": ("lightning_staff", ("wet", "charged")),
}


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    library = load_library()
    print("| 開局 | 關鍵字 | 造得出 | 起始兩招（次數） |")
    print("|---|---|---|---|")
    for name, (weapon, keywords) in STARTS.items():
        linked, real, pairs = 0, 0, Counter[str]()
        for seed in range(1, runs + 1):
            run = new_keyword_run(library, weapon, keywords, seed)
            known = {**library.skills, **{s.id: s for s in run.generated_skills}}
            first, second = (known[s] for s in run.hero.skills[:2])
            if links_between(library, first, second):
                linked += 1
                target = condition_target(second)
                real += target is None or target in made_targets(first, library)
            pairs[f"{first.name_zh}＋{second.name_zh}"] += 1
        shown = "、".join(f"{p} ×{n}" for p, n in pairs.most_common(4))
        print(f"| {name} | {linked}/{runs} | {real}/{runs} | {shown} |")


if __name__ == "__main__":
    main()
