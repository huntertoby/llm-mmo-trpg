"""鎖格比對（美術 PM 第 11 版）：新產生的 3 倍特寫和 closeup/locked/ 的基準圖逐像素比對。

基準圖放在 docs/art/closeup/locked/<set>/<檔名>.png（set＝key 或 parts），新特寫在 docs/art/closeup/<set>/。
任何一格不同（尺寸或任一像素）或缺檔就失敗，結束碼 1，並列出是哪幾格。

用法：uv run --no-project --with pillow python -I docs/art/sample/tools/lockcheck.py [closeup 資料夾]
"""

import pathlib
import sys

from PIL import Image, ImageChops

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[2] / "closeup"
locked = sorted((root / "locked").glob("*/*.png"))
bad = []
for base in locked:
    rel = base.relative_to(root / "locked")
    new = root / rel
    if not new.exists():
        bad.append(f"{rel.as_posix()}：缺檔")
        continue
    a, b = Image.open(base).convert("RGBA"), Image.open(new).convert("RGBA")
    if a.size != b.size:
        bad.append(f"{rel.as_posix()}：尺寸不同 {a.size} → {b.size}")
        continue
    if a.tobytes() != b.tobytes():
        d = ImageChops.difference(a, b)
        box = d.getbbox(alpha_only=False)  # RGBA 的 getbbox 預設只看 alpha，不透明的圖會漏抓
        bad.append(f"{rel.as_posix()}：像素不同，範圍 {box}")
sys.stdout.reconfigure(encoding="utf-8")
print(f"鎖格 {len(locked)} 格，不同 {len(bad)} 格")
for line in bad:
    print("  " + line)
sys.exit(1 if bad or not locked else 0)
