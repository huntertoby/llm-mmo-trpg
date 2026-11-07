"""QK 移植並排圖（左：docs/art/closeup/ 樣張、右：遊戲畫的）與鎖格差異統計。

用法：
  uv run --no-project --with pillow python -I docs/art/sample/tools/qk_compare.py \
    <遊戲特寫資料夾> <輸出資料夾>
遊戲特寫資料夾放 key/、parts/ 兩個子資料夾
（doll-gallery.html?skin=q&dump=1 ＋ closeups_save.py 存出來的 PNG）。
輸出：每格一張並排 jpg（品質 80）、每組一張總表；印出 13 格鎖格（closeup/locked/）的像素差統計。
"""

import pathlib
import sys

from PIL import Image, ImageChops, ImageDraw

DIFF_THRESHOLD = 8  # 通道差大於此值才算一個不同的像素

root = pathlib.Path(__file__).resolve().parents[2] / "closeup"
game, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")


def pair(a: Image.Image, b: Image.Image) -> Image.Image:
    w, h = a.width + b.width + 12, max(a.height, b.height)
    im = Image.new("RGB", (w, h), (10, 10, 14))
    im.paste(a.convert("RGB"), (0, 0))
    im.paste(b.convert("RGB"), (a.width + 12, 0))
    ImageDraw.Draw(im).rectangle([a.width, 0, a.width + 11, h], fill=(232, 187, 72))
    return im


for sub in ("key", "parts"):
    files = sorted((root / sub).glob("*.png"))
    tiles = []
    for f in files:
        g = game / sub / f.name
        if not g.exists():
            print(f"缺 {sub}/{f.name}")
            continue
        im = pair(Image.open(f), Image.open(g))
        im.save(out / f"{sub}_{f.stem}.jpg", quality=80)
        tiles.append(im)
    # 總表：每張縮成寬 900，直排，每 12 張一頁
    for p in range(0, len(tiles), 12):
        page = [t.resize((900, round(t.height * 900 / t.width))) for t in tiles[p : p + 12]]
        sheet = Image.new("RGB", (900, sum(t.height for t in page)), (10, 10, 14))
        y = 0
        for t in page:
            sheet.paste(t, (0, y))
            y += t.height
        sheet.save(out / f"_sheet_{sub}_{p // 12 + 1:02d}.jpg", quality=80)

print("鎖格差異（closeup/locked/ vs 遊戲；差＝任一通道差 > 8 的像素；標題列 40px 另計）")
for base in sorted((root / "locked").glob("*/*.png")):
    rel = base.relative_to(root / "locked")
    g = game / rel
    if not g.exists():
        print(f"  {rel.as_posix()}：缺檔")
        continue
    a, b = Image.open(base).convert("RGB"), Image.open(g).convert("RGB")
    if a.size != b.size:
        print(f"  {rel.as_posix()}：尺寸不同 {a.size} → {b.size}")
        continue
    d = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > DIFF_THRESHOLD else 0)
    total = a.width * a.height
    n = sum(1 for v in d.getdata() if v)
    body = d.crop((0, 40, a.width, a.height))
    nb = sum(1 for v in body.getdata() if v)
    print(
        f"  {rel.as_posix()}：差 {n} 像素（{100 * n / total:.2f}%），"
        f"標題列以外 {nb}（{100 * nb / total:.2f}%），範圍 {d.getbbox()}"
    )
