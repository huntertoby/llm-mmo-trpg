"""程式不依地圖類型 ID 寫死分支（Phase WL-2 第 3 項）。

類型清單在 ``content/map_archetypes.yaml``；有特殊用途的類型看 ``in_random_pool``、``role``。這裡掃
``src/trpg`` 與 ``client/src``（不含測試），擋下「``archetype`` 跟字串字面值比較」的新寫法。前端原本
三處，QF-5 起 API 的地圖摘要帶 ``role``，前端改讀 ``role``，一處都不剩。"""

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


def test_frontend_has_no_branch_on_an_archetype_id() -> None:
    """QF-5（WL-2 裁定 1）：靶場、頭目地圖的判斷改讀 API 地圖摘要的 ``role``。"""
    paths = [
        p
        for p in sorted((ROOT / "client" / "src").rglob("*.ts*"))
        if ".test." not in p.name and not p.name.endswith(".d.ts")
    ]
    assert _hits(paths, _TS) == {}
