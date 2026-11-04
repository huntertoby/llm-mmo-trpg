"""6F-4d 第 6 項：witness 的兩條件建構（6F-4c ``condition_proposals``）前後對照，只用靜態建構。

題目照 6E-W 報告第 2 節的 8 組開局（兩個關鍵字＋指定武器大類，也就是會做 witness 檢查的那一類），
角色階級 1～3，各 ``seeds`` 個種子，``make_topic`` 出題（反應技 100‰，同實戰）。不呼叫 LLM。

- 「前」：把 ``condition_proposals`` 換成空的（6F-4c 之前的建構）；
- 「後」：目前的程式。

輸出：出得了題（可行）／這一格不請 LLM（退回）的比例、題目和「前」不同的題數、新救回的題目例子。

    uv run python scripts/f4d_witness_compare.py [每組每階的種子數＝10] [-j 2]
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from trpg.skillgen import proposal_witness
from trpg.skillgen.proposal_topic import TopicRequest, make_topic
from trpg.skillgen.random_composer import default_library

SETUPS: dict[str, tuple[str, tuple[str, str]]] = {
    "火焰法杖 點燃＋帶電": ("focus", ("ignite", "charged")),
    "匕首 冰凍＋隱蔽": ("melee", ("frozen", "concealed")),
    "巨劍 倒地＋撞擊": ("melee", ("prone", "collision")),
    "弓 標記＋高處": ("ranged", ("marked", "high_ground")),
    "冰霜法杖 冰凍＋潮濕": ("focus", ("frozen", "wet")),
    "戰鎚 撞擊＋點燃": ("melee", ("collision", "ignite")),
    "圖騰法杖 召喚物＋中毒": ("focus", ("summon", "poisoned")),
    "長槍 帶電＋標記": ("melee", ("charged", "marked")),
}
TIERS = (1, 2, 3)
_ORIGINAL = proposal_witness.condition_proposals


def _none(*_args: Any, **_kwargs: Any) -> Iterator[dict[str, Any]]:
    return iter(())


def _job(args: tuple[str, int, bool]) -> tuple[str, int, list[str | None]]:
    """``<開局>#<階級>``：每個種子的題目摘要（``None`` ＝ 退回，不請 LLM）。"""
    name, seeds, with_conditions = args
    # 行程池會重用 worker：每次都要設定（不能只在「前」換掉）
    proposal_witness.condition_proposals = _ORIGINAL if with_conditions else _none  # type: ignore[assignment]
    library = default_library()
    setup, tier_text = name.split("#")
    tier = int(tier_text)
    weapon_class, keywords = SETUPS[setup]
    out: list[str | None] = []
    for seed in range(seeds):
        topic = TopicRequest(
            tier=tier,
            keywords=keywords,
            seed=seed,
            uses={},
            weapon_class=weapon_class,
            reaction_permille=100,
        )
        made = make_topic(library, topic)
        if made is None:
            out.append(None)
            continue
        request = made[0]
        out.append(
            f"{request.kind or 'active'}／{request.rarity}／{request.core_primitive or '不指定'}"
        )
    return name, int(with_conditions), out


def _arg(flag: str) -> str | None:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None


def main() -> None:
    numbers = [a for i, a in enumerate(sys.argv[1:], 1) if a.isdigit() and sys.argv[i - 1] != "-j"]
    seeds = int(numbers[0]) if numbers else 10
    workers = min(8, int(_arg("-j") or 2))
    names = [f"{s}#{t}" for s in SETUPS for t in TIERS]
    jobs = [(n, seeds, w) for n in names for w in (False, True)]
    found: dict[tuple[str, int], list[str | None]] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for name, flag, out in pool.map(_job, jobs):
            found[(name, flag)] = out
    total = len(names) * seeds
    print(f"8 組開局 × 階級 1～3 × 種子 {seeds} 個 ＝ {total} 格（兩個關鍵字＋指定武器大類）")
    print("| | 前（無兩條件建構） | 後（6F-4c 兩條件建構） |")
    print("|---|---|---|")
    before = [t for n in names for t in found[(n, 0)]]
    after = [t for n in names for t in found[(n, 1)]]
    for label, pick in (
        ("可行（出題）", lambda t: t is not None),
        ("退回（不請 LLM）", lambda t: t is None),
    ):
        b = sum(1 for t in before if pick(t))
        a = sum(1 for t in after if pick(t))
        print(
            f"| {label} | {b}/{total}（{b * 100 // total}%） | {a}/{total}（{a * 100 // total}%） |"
        )
    changed = [(b, a) for b, a in zip(before, after, strict=True) if b != a]
    worse = sum(1 for b, a in changed if b is not None and a is None)
    print(f"| 題目不同 | — | {len(changed)} 格（其中前可行、後退回 {worse} 格） |")
    print()
    print("每組（前／後 退回數）：")
    for setup in SETUPS:
        b = sum(1 for t in range(1, 4) for x in found[(f"{setup}#{t}", 0)] if x is None)
        a = sum(1 for t in range(1, 4) for x in found[(f"{setup}#{t}", 1)] if x is None)
        print(f"- {setup}：{b} → {a}（共 {3 * seeds} 格）")
    examples = Counter(f"{b} → {a}" for b, a in changed)
    print()
    print("題目改變的例子（前 → 後，次數）：")
    for text, n in examples.most_common(10):
        print(f"- {text} ×{n}")


if __name__ == "__main__":
    main()
