"""靈感閃現「選變體」改版樣張（flash-choice.html）的截圖。

    S=docs/art/sample/tools/flash_choice_shots.py
    uv run --with pillow python $S            # 全部
    uv run --with pillow python $S new-800    # 只拍指名的
    uv run --with pillow python $S --true1x   # 只拍真 1 倍裁切
    uv run --with pillow python $S --plain new-800   # 指名的另拍一張 &plain=1（檔名加 -plain）

給使用者看的一律 plain（不畫「改過的字」的金色虛線）：compare-1600／compare-800 本身就是 plain；
帶標記的給玩法 PM：compare-marked-*、new-*、picks-*、stress-* 等。

輸出 docs/art/shots/flash-choice/：一般截圖 jpg 品質 80；
真 1 倍裁切與最近鄰放大存 PNG（true1x-*.png）。
無頭 Chrome 參數沿用 qicons_shots.py（--mute-audio、file:///，不開伺服器），
Chrome 設定檔用自己的暫存資料夾（不和別的畫圖 agent 打架）。
網址一律帶 mute=1。Pillow 只用來轉 jpg 與裁切放大。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qicons_shots as q

PAGE = "flash-choice.html"
OUT = q.ART / "shots" / "flash-choice"
TMP = Path(tempfile.gettempdir()) / "flash-choice-shots"
PROFILE = TMP / "chrome-profile"
BASE = [f"--user-data-dir={PROFILE}" if a.startswith("--user-data-dir=") else a for a in q.BASE]

# (檔名, 網址參數, 頁寬)
SHOTS = [
    ("compare-1600", "state=compare&vw=1600&plain=1", 1720),
    ("compare-800", "state=compare&vw=800&plain=1", 1440),
    ("compare-marked-1600", "state=compare&vw=1600", 1720),
    ("compare-marked-800", "state=compare&vw=800", 1440),
    ("new-1600", "state=panel&vw=1600", 760),
    ("new-800", "state=panel&vw=800", 530),
    ("tip-1600", "state=panel&vw=1600&pick=4&tip=weaponDmg", 760),
    ("tip-800", "state=panel&vw=800&pick=3&tip=puddle", 530),
    ("tip-power-800", "state=panel&vw=800&pick=2&tip=power", 530),
    ("base-1600", "state=panel&vw=1600&base=1", 760),
    ("base-800", "state=panel&vw=800&base=1", 530),
    ("picks-1600", "state=picks&vw=1600", 1520),
    ("picks-800", "state=picks&vw=800", 1080),
    ("stress-800", "state=stress&vw=800", 1620),
    ("stress-1600", "state=stress&vw=1600", 2260),
    ("transform-none-800", "state=transform&vw=800&pick=4", 530),
    ("marks", "state=marks", 1640),
    ("terms", "state=terms", 880),
    # 11-13 橫向排法（layout=row：四張並排；grid：2×2，800 的建議版）
    ("row-1600", "state=panel&vw=1600&layout=row", 760),
    ("row-800", "state=panel&vw=800&layout=row", 530),
    ("row-800-pick", "state=panel&vw=800&layout=row&pick=4", 530),
    ("row-800-alt", "state=panel&vw=800&layout=grid", 530),
    ("row-800-alt-pick", "state=panel&vw=800&layout=grid&pick=4", 530),
    ("row-stress-800", "state=stress&vw=800&layout=row", 1620),
    ("row-stress-800-alt", "state=stress&vw=800&layout=grid", 1620),
    ("row-stress-1600", "state=stress&vw=1600&layout=row", 2260),
    ("compare-row-1600", "state=rowcompare&vw=1600&layout=row&plain=1", 1520),
    ("compare-row-800", "state=rowcompare&vw=800&layout=row&plain=1", 1080),
    ("compare-row-800-alt", "state=rowcompare&vw=800&layout=grid&plain=1", 1080),
]
# 真 1 倍：(檔名, 網址參數, 頁寬, 要裁的區塊名（頁面量的 data-rects）, 放大倍率)
TRUE1X = [
    ("true1x-marks", "state=marks", 1640, "marks", 4),
    ("true1x-rows-opt2-800", "state=rows&vw=800&pick=2", 530, "opt2", 4),
    ("true1x-transform-foot-800", "state=transform&vw=800&pick=4&un=2", 530, "foot", 4),
    ("true1x-asm-800", "state=panel&vw=800&base=1", 530, "asm", 4),
    ("true1x-base-800", "state=panel&vw=800&pick=4", 530, "base", 4),
    ("true1x-opt1-800", "state=panel&vw=800&pick=4", 530, "opt1", 4),
    ("true1x-diffs4-800", "state=panel&vw=800&pick=4", 530, "diffs4", 4),
    ("true1x-icons-800", "state=panel&vw=800&pick=4", 530, "icons", 6),
    ("true1x-row-800", "state=panel&vw=800&layout=row&pick=4", 530, "opts", 4),
]


def url(query: str) -> str:
    return q.url(PAGE, f"{query}&mute=1")


def dump(query: str, width: int) -> str:
    cmd = [*BASE, f"--window-size={width},900", "--dump-dom", url(query)]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    return done.stdout.decode("utf-8", "replace")


def shoot_png(query: str, width: int, out: Path, scale: float = 1) -> bool:
    found = re.search(r'data-h="(\d+)"', dump(query, width))
    if found is None:
        print(f"{query}: page did not finish (no data-h)")
        return False
    height = int(found.group(1))
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *BASE,
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
        "--enable-logging=stderr",
        "--v=0",
        f"--screenshot={out}",
        url(query),
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    console = [
        ln
        for ln in done.stderr.decode("utf-8", "replace").splitlines()
        if "CONSOLE" in ln and "willReadFrequently" not in ln
    ]
    note = f"  console: {console[:5]}" if console else ""
    print(f"{query} @{width}: {height}px -> {out.name}{note}")
    return out.exists() and not console


def shoot_jpg(query: str, width: int, out: Path) -> bool:
    png = TMP / (out.stem + ".png")
    if not shoot_png(query, width, png):
        return False
    Image.open(png).convert("RGB").save(out, "JPEG", quality=80)
    return True


def rects(query: str, width: int) -> dict[str, list[float]]:
    found = re.search(r'data-rects="([^"]*)"', dump(query, width))
    return json.loads(unescape(found.group(1))) if found else {}


def true1x(name: str, query: str, width: int, key: str, zoom: int) -> bool:
    png = TMP / f"{name}-full.png"
    if not shoot_png(query, width, png, 1):
        return False
    box = rects(query, width).get(key)
    if box is None:
        print(f"{name}: no rect {key}")
        return False
    x, y, w, hh = (round(v) for v in box)
    img = Image.open(png).convert("RGB").crop((x, y, x + w, y + hh))
    img.save(OUT / f"{name}.png")
    img.resize((w * zoom, hh * zoom), Image.NEAREST).save(OUT / f"{name}-x{zoom}.png")
    print(f"  crop {key} {w}x{hh} -> {name}.png, {name}-x{zoom}.png")
    return True


def main() -> int:
    args = sys.argv[1:]
    names = [a for a in args if not a.startswith("--")]
    TMP.mkdir(parents=True, exist_ok=True)
    ok = True
    plain = "--plain" in args
    if "--true1x" not in args:
        for name, query, width in SHOTS:
            if names and name not in names:
                continue
            if plain:
                ok &= shoot_jpg(f"{query}&plain=1", width, OUT / f"{name}-plain.jpg")
                continue
            ok &= shoot_jpg(query, width, OUT / f"{name}.jpg")
    if plain:
        return 0 if ok else 1
    for name, query, width, key, zoom in TRUE1X:
        if names and name not in names and "--true1x" not in args:
            continue
        ok &= true1x(name, query, width, key, zoom)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
