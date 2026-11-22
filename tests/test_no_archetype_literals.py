"""程式不依地圖類型 ID 寫死分支（Phase WL-2 第 3 項）。

類型清單在 ``content/map_archetypes.yaml``；有特殊用途的類型看 ``in_random_pool``、``role``。這裡掃
``src/trpg`` 與 ``client/src``（不含測試），擋下「``archetype`` 跟字串字面值比較」的新寫法。前端還有
三處（後端 API 的地圖摘要沒有 ``role``），列在 :data:`FRONTEND_KNOWN`，數量只能變少。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_PY = re.compile(
    r"""archetype\s*(?:==|!=)\s*["']"""  # map_def.archetype == "boss"
    r"""|archetype\s+(?:not\s+)?in\s*[(\[{]\s*["']"""  # archetype in ("boss", ...)
    r"""|["'](?:test|training|boss)["']\s*(?:==|!=)\s*\w*\.?archetype\b"""
    r"""|\b[A-Z_]*ARCHETYPES?\s*(?::\s*[^=]+)?=\s*(?:frozenset|\(|\{|["'])"""  # 類型常數
    r"""|map_pool\)?\s*-\s*\{\s*["']"""  # set(region.map_pool) - {"boss"}
    r"""|\btype\s+\w*Archetype\w*\s*=\s*Literal"""  # 類型清單寫成 Literal
)
_TS = re.compile(r"""archetype\s*(?:===|!==|==|!=)\s*["']""")

FRONTEND_KNOWN: dict[str, int] = {
    "client/src/ui/workshop/TryoutPanel.tsx": 2,  # 靶場、頭目地圖的選單附註
    "client/src/workshop/tryout.ts": 1,  # isTrainingMap
}
"""前端已知的依類型 ID 分支（新類型走預設：沒有附註、不是靶場）；WL-2 報告「待 PM 決定」。"""


def _hits(paths: list[Path], pattern: re.Pattern[str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        hits = [f"{i}: {line.strip()}" for i, line in enumerate(lines, 1) if pattern.search(line)]
        if hits:
            found[path.relative_to(ROOT).as_posix()] = hits
    return found


def test_backend_has_no_branch_on_an_archetype_id() -> None:
    paths = sorted((ROOT / "src" / "trpg").rglob("*.py"))
    assert _hits(paths, _PY) == {}


def test_frontend_archetype_id_branches_only_shrink() -> None:
    paths = [
        p
        for p in sorted((ROOT / "client" / "src").rglob("*.ts*"))
        if ".test." not in p.name and not p.name.endswith(".d.ts")
    ]
    counts = {k: len(v) for k, v in _hits(paths, _TS).items()}
    assert set(counts) <= set(FRONTEND_KNOWN), counts
    assert all(counts[k] <= FRONTEND_KNOWN[k] for k in counts), counts
