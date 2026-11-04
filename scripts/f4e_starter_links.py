"""6F-4e／6F-4f：起始兩招的觸發關係（#129）與第 1 招的分布。

每種開局跑 ``runs`` 個種子（預設 10），輸出兩張表：

- 觸發關係：「關鍵字」（:func:`~trpg.roguelite.start.links_between`）、「造得出」（第 2 招若是條件
  傷害，條件對象是第 1 招實際造得出來的；6F-4d 的口徑，結算事實）、最常見的 4 組起始兩招；
- 第 1 招分布（法術版、武器版同一個配方合併計）：前三名與占比，以及第 1 招造得出狀態或表面的
  比例。

    uv run python scripts/f4e_starter_links.py [runs]

量「前」時把 ``PYTHONPATH`` 指到舊版的 ``src``（內容跟著它的 ``content/``）。6F-4f 加了三個會用到
潮濕、倒地、標記的開局（舊版也能跑）。
"""

from __future__ import annotations

import sys
from collections import Counter

from trpg.content.composer_rules import recipe_display_names
from trpg.content.library import load_library
from trpg.roguelite.start import links_between, new_keyword_run
from trpg.skillgen.exploit_match import condition_target, made_targets

STARTS = {
    "A 火焰法杖 點燃＋帶電": ("fire_staff", ("ignite", "charged")),
    "B 匕首 冰凍＋隱蔽": ("dagger", ("frozen", "concealed")),
    "巨劍 倒地＋撞擊": ("greatsword", ("prone", "collision")),
    "弓 標記＋高處": ("bow", ("marked", "high_ground")),
    "雷電法杖 潮濕＋帶電": ("lightning_staff", ("wet", "charged")),
    "匕首 潮濕＋隱蔽": ("dagger", ("wet", "concealed")),
    "火焰法杖 倒地＋點燃": ("fire_staff", ("prone", "ignite")),
    "單手劍 標記＋倒地": ("one_handed_sword", ("marked", "prone")),
}


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    library = load_library()
    spell_name = {  # 武器版名稱 → 法術版名稱（同一個配方合併計）
        n: r.name_zh
        for r in library.composer.whiteboard.active
        for n in recipe_display_names(r).values()
    }
    links: list[str] = []
    firsts: list[str] = []
    for name, (weapon, keywords) in STARTS.items():
        linked, real, made, pairs, first_names = 0, 0, 0, Counter[str](), Counter[str]()
        for seed in range(1, runs + 1):
            run = new_keyword_run(library, weapon, keywords, seed)
            known = {**library.skills, **{s.id: s for s in run.generated_skills}}
            first, second = (known[s] for s in run.hero.skills[:2])
            made += bool(made_targets(first, library))
            if links_between(library, first, second):
                linked += 1
                target = condition_target(second)
                real += target is None or target in made_targets(first, library)
            pairs[f"{first.name_zh}＋{second.name_zh}"] += 1
            first_names[spell_name.get(first.name_zh, first.name_zh)] += 1
        shown = "、".join(f"{p} ×{n}" for p, n in pairs.most_common(4))
        links.append(f"| {name} | {linked}/{runs} | {real}/{runs} | {shown} |")
        top = "、".join(
            f"{p} {n}/{runs}（{n * 100 // runs}%）" for p, n in first_names.most_common(3)
        )
        firsts.append(f"| {name} | {made}/{runs} | {len(first_names)} | {top} |")
    print("| 開局 | 關鍵字 | 造得出 | 起始兩招（次數） |")
    print("|---|---|---|---|")
    print("\n".join(links))
    print()
    print("| 開局 | 第 1 招造得出東西 | 第 1 招種類數 | 前三名（占比） |")
    print("|---|---|---|---|")
    print("\n".join(firsts))


if __name__ == "__main__":
    main()
