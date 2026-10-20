"""一次性遷移（Phase 3-7）：引擎改為「最大 HP ＝ 範本基礎 HP ＋（體質 − 10）× 3」之後，
把所有範本的基礎 ``max_hp`` 扣掉（體質 − 10）× 3，讓每個現有單位的最終 HP 與遷移前相同。

處理 ``content/units/**/*.yaml`` 與 ``content/sim/builds.yaml`` 的英雄範本。只改 ``max_hp:`` 的
數字，保留檔案其餘內容（含註解與換行）。**只能執行一次**（再次執行會再扣一次）；
用 ``--dry-run`` 預覽。

    uv run python scripts/migrate_con_hp.py [--dry-run]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "content"
CON_BASE = 10
HP_PER_CON = 3
_CON = re.compile(r"\bcon:\s*(\d+)")
_HP = re.compile(r"^(\s*max_hp:\s*)(\d+)(.*)$")


def migrate_text(text: str, name: str) -> tuple[str, list[tuple[int, int, int]]]:
    """回傳新文字與每個範本的 (體質, 舊 HP, 新 HP)。"""
    con: int | None = None
    changes: list[tuple[int, int, int]] = []
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        eol = line[len(body) :]
        if not body.lstrip().startswith("#"):
            found = _CON.search(body)
            if found is not None and "attributes" in body:
                con = int(found.group(1))
            hp = _HP.match(body)
            if hp is not None:
                if con is None:
                    raise SystemExit(f"{name}：max_hp 之前找不到 attributes（體質）")
                old = int(hp.group(2))
                new = old - (con - CON_BASE) * HP_PER_CON
                if new < 1:
                    raise SystemExit(f"{name}：新基礎 HP {new} < 1")
                changes.append((con, old, new))
                body = f"{hp.group(1)}{new}{hp.group(3)}"
                con = None
        out.append(body + eol)
    return "".join(out), changes


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = [*sorted((ROOT / "units").rglob("*.yaml")), ROOT / "sim" / "builds.yaml"]
    for path in files:
        text = path.read_bytes().decode("utf-8")
        new_text, changes = migrate_text(text, path.name)
        for con, old, new in changes:
            print(f"{path.relative_to(ROOT).as_posix()}: con {con} HP {old} -> 基礎 {new}")
        if not dry and new_text != text:
            path.write_bytes(new_text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
