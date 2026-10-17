"""產生 ``content/rules/hit_table.yaml``（命中修正的整數門檻對照表）。

用法::

    uv run python scripts/gen_hit_table.py            # 依 content/rules/core.yaml 重新產生
    uv run python scripts/gen_hit_table.py --check    # 只檢查檔案是否為最新（不寫檔）

讀取 ``core.yaml`` 的 ``hit_slope`` 與 ``hit_mod_cap``，以 ``decimal`` 高精度計算
``ceil(2^((2k − 1) / (2·slope)) × 10⁶)``（``k = −cap+1 … cap``），輸出成 YAML。
修改 ``hit_slope`` 或 ``hit_mod_cap`` 後必須重新執行；載入規則時會檢查兩者一致，
``tests/content/test_rules.py`` 也會重新計算並以 ``Fraction`` 精確驗證。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.rules import HIT_TABLE_SCALE, CoreRules, compute_hit_thresholds


def render_hit_table(slope: int, cap: int, scale: int = HIT_TABLE_SCALE) -> str:
    """回傳 hit_table.yaml 的完整內容（確定性的文字）。"""
    lines = [
        "# 命中修正對照表：由 scripts/gen_hit_table.py 產生，請勿手改。",
        "# 修正值至少為 mod 的條件：攻擊值 × scale >= 防禦值 × min_ratio_scaled",
        "# min_ratio_scaled = ceil(2^((2·mod − 1) / (2·slope)) × scale)；低於最小門檻時為 −cap。",
        f"slope: {slope}",
        f"cap: {cap}",
        f"scale: {scale}",
        "thresholds:",
    ]
    for t in compute_hit_thresholds(slope, cap, scale):
        lines.append(f"  - {{mod: {t.mod}, min_ratio_scaled: {t.min_ratio_scaled}}}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="產生 content/rules/hit_table.yaml")
    parser.add_argument("--content-dir", type=Path, default=None, help="內容資料夾")
    parser.add_argument("--check", action="store_true", help="只檢查，不寫檔")
    args = parser.parse_args(argv)
    content_dir: Path = args.content_dir or default_content_dir()
    core = load_content_file(content_dir / "rules" / "core.yaml", CoreRules)
    text = render_hit_table(core.hit_slope, core.hit_mod_cap)
    target = content_dir / "rules" / "hit_table.yaml"
    if args.check:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != text:
            print(f"{target} 不是最新，請執行 uv run python scripts/gen_hit_table.py")
            return 1
        print(f"{target} 為最新。")
        return 0
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"已寫入 {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
