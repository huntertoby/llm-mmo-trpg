"""資訊面板版面提案（info-panels.html）的截圖：每段 1600 寬與 800 寬各一張，jpg 品質 80。

    uv run python docs/art/sample/tools/info_panels_shots.py            # 全部
    uv run python docs/art/sample/tools/info_panels_shots.py notice event # 只拍指名的段
    uv run python docs/art/sample/tools/info_panels_shots.py --closeup   # 特寫（PNG）

特寫＝2 倍拍整段再裁一塊。輸出：docs/art/shots/info-panels/<段>-1600.jpg、<段>-800.jpg；
特寫 docs/art/shots/info-panels/closeup/*.png。沿用 qicons_shots.py 的無頭 Chrome 參數與 jpg
轉檔，但視窗寬度可指定、Chrome 設定檔用自己的資料夾（不和別的畫圖 agent 打架）。
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qicons_shots as q

PAGE = "info-panels.html"
OUT = q.ART / "shots" / "info-panels"
PROFILE = Path(tempfile.gettempdir()) / "info-panels-shots-chrome-profile"
q.BASE = [f"--user-data-dir={PROFILE}" if a.startswith("--user-data-dir=") else a for a in q.BASE]
PARTS = ["notice", "growth", "others", "lang", "event", "tips"]
WIDTHS = [1600, 800]
# 特寫：(檔名, 段, 頁寬, 裁切 x, y, w, h（CSS px，2 倍拍）)
CLOSEUPS = [
    ("notice-timeline", "notice", 1600, 820, 255, 720, 270),
    ("event-tiles", "event", 1600, 812, 345, 470, 270),
    ("growth-callouts", "growth", 1600, 820, 140, 720, 300),
]


def crop(src: Path, box: tuple[int, int, int, int], scale: int, out: Path) -> bool:
    """Crop a region of a shot with headless Chrome (no Pillow here)."""
    x, y, w, hh = box
    out.parent.mkdir(parents=True, exist_ok=True)
    page = Path(tempfile.gettempdir()) / "info-panels-crop.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><body style="margin:0;overflow:hidden">'
        f'<div style="width:{w * scale}px;height:{hh * scale}px;overflow:hidden;position:relative">'
        f'<img src="{src.as_uri()}" style="position:absolute;'
        f'left:{-x * scale}px;top:{-y * scale}px"></div>',
        encoding="utf-8",
    )
    cmd = [
        *q.BASE,
        f"--window-size={w * scale},{hh * scale}",
        "--force-device-scale-factor=1",
        f"--screenshot={out}",
        page.as_uri(),
    ]
    subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    print(f"crop -> {out.name}")
    return out.exists()


def height_of(query: str, width: int) -> int | None:
    cmd = [*q.BASE, f"--window-size={width},900", "--dump-dom", q.url(PAGE, query)]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    found = re.search(r'data-h="(\d+)"', done.stdout.decode("utf-8", "replace"))
    return int(found.group(1)) if found else None


def shoot(query: str, width: int, out: Path, scale: float = 1) -> bool:
    if out.suffix == ".jpg":
        png = out.with_suffix(".tmp.png")
        return shoot(query, width, png, scale) and q.to_jpeg(png, out)
    height = height_of(query, width)
    if height is None:
        print(f"{query}: page did not finish (no data-h)")
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *q.BASE,
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
        "--enable-logging=stderr",
        "--v=0",
        f"--screenshot={out}",
        q.url(PAGE, query),
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    console = [
        ln
        for ln in done.stderr.decode("utf-8", "replace").splitlines()
        if "CONSOLE" in ln and "willReadFrequently" not in ln
    ]
    print(
        f"{query} @{width}: {height}px -> {out.name}"
        + (f"  console: {console[:5]}" if console else "")
    )
    return not console


def main() -> int:
    args = sys.argv[1:]
    ok = True
    if "--closeup" in args:
        for name, part, width, *box in CLOSEUPS:
            full = Path(tempfile.gettempdir()) / f"info-panels-{part}-2x.png"
            ok &= shoot(f"part={part}", width, full, 2) and crop(
                full, tuple(box), 2, OUT / "closeup" / f"{name}.png"
            )
        return 0 if ok else 1
    parts = [a for a in args if a in PARTS] or [p for p in PARTS if p != "tips"]
    for part in parts:
        for width in WIDTHS:
            ok &= shoot(f"part={part}", width, OUT / f"{part}-{width}.jpg")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
