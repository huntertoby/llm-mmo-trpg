"""截圖比對（TL-1）：比對新舊兩組截圖資料夾，逐張算像素差異。

依相對路徑配對兩邊的 PNG，列出：
- 有變化的圖（差異像素比例超過 ``--threshold``，由大到小）；
- 細微變化（有差異但沒超過門檻）；
- 只在舊的、只在新的、尺寸不同的、無法讀取的。

專案沒有 Pillow／numpy，所以 PNG 用標準庫（``zlib``＋``struct``）自己解：支援
所有非交錯（non-interlaced）的 PNG 色彩型態與位元深度；交錯 PNG 列為無法讀取。
JPEG 不比（無相依可解），只統計略過幾張。

單一像素的色差＝RGBA 四個通道差值的最大值（0～255；16 位元取高位元組），
大於 ``--pixel-tol`` 才算這個像素有變。差異比例＝有變的像素 ÷ 總像素。

結束碼：0＝沒有超過門檻的變化；1＝有變化（超過門檻、只在一邊、尺寸不同）；
2＝輸入錯誤（資料夾不存在、兩邊都沒有 PNG、有 PNG 讀不了）。

用法：
    uv run python scripts/screenshot_diff.py 舊資料夾 新資料夾
    uv run python scripts/screenshot_diff.py 舊 新 --threshold 0.001 --pixel-tol 8 \\
        --diff-out 差異圖資料夾 --format markdown --out 摘要.md
"""

# PNG 規格的色彩型態（0/2/3/4/6）、濾波型態（0～4）、位元深度（8/16）都是規格裡的固定數字。
# ruff: noqa: PLR2004

from __future__ import annotations

import argparse
import io
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

EXIT_OK = 0
EXIT_CHANGED = 1
EXIT_INPUT_ERROR = 2

# 預設值取保守：任何一個像素有任何色差都算變化，任何變化都算超過門檻。
DEFAULT_THRESHOLD = 0.0
DEFAULT_PIXEL_TOL = 0

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
_VALID_DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}


class PngError(ValueError):
    """PNG 檔不合格式或用了不支援的功能。"""


@dataclass(frozen=True)
class Image:
    """解碼後的圖：``rows`` 每列是 ``width * 4`` 位元組的 RGBA（8 位元）。"""

    width: int
    height: int
    rows: tuple[bytes, ...]


# ---------------------------------------------------------------------------
# PNG 解碼
# ---------------------------------------------------------------------------


def _read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(PNG_SIGNATURE):
        raise PngError("不是 PNG 檔（檔頭不符）")
    chunks: list[tuple[bytes, bytes]] = []
    pos = len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if len(body) != length:
            raise PngError("檔案被截斷")
        chunks.append((kind, body))
        pos += 12 + length
        if kind == b"IEND":
            break
    return chunks


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter_row(ftype: int, line: bytearray, prev: bytes, bpp: int) -> None:
    """就地還原一列的濾波（PNG 規格第 9 節）。"""
    n = len(line)
    if ftype == 0:
        return
    if ftype == 1:
        for i in range(bpp, n):
            line[i] = (line[i] + line[i - bpp]) & 0xFF
    elif ftype == 2:
        for i in range(n):
            line[i] = (line[i] + prev[i]) & 0xFF
    elif ftype == 3:
        for i in range(n):
            left = line[i - bpp] if i >= bpp else 0
            line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
    elif ftype == 4:
        for i in range(n):
            left = line[i - bpp] if i >= bpp else 0
            upleft = prev[i - bpp] if i >= bpp else 0
            line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
    else:
        raise PngError(f"未知的濾波型態 {ftype}")


def _samples(line: bytes, depth: int, count: int) -> list[int]:
    """把一列拆成 ``count`` 個樣本（8 位元以下的打包樣本、16 位元取高位元組前的原值）。"""
    if depth == 8:
        return list(line[:count])
    if depth == 16:
        return [line[2 * i] for i in range(count)]
    per_byte = 8 // depth
    mask = (1 << depth) - 1
    out: list[int] = []
    for byte in line:
        for k in range(per_byte):
            out.append((byte >> (8 - depth * (k + 1))) & mask)
            if len(out) == count:
                return out
    return out


def _to_rgba(
    line: bytes,
    width: int,
    color_type: int,
    depth: int,
    palette: list[tuple[int, int, int, int]],
) -> bytes:
    if color_type == 6 and depth == 8:
        return bytes(line)
    if color_type == 2 and depth == 8:
        out = bytearray(width * 4)
        out[0::4] = line[0::3]
        out[1::4] = line[1::3]
        out[2::4] = line[2::3]
        out[3::4] = b"\xff" * width
        return bytes(out)
    channels = _CHANNELS[color_type]
    vals = _samples(line, depth, width * channels)
    if color_type == 3:
        try:
            return b"".join(bytes(palette[v]) for v in vals)
        except IndexError as exc:
            raise PngError("調色盤索引超出範圍") from exc
    if color_type in (0, 4) and depth < 8:  # 灰階低位元：放大到 0～255
        scale = 255 // ((1 << depth) - 1)
        vals = [v * scale for v in vals]
    out = bytearray(width * 4)
    for x in range(width):
        px = vals[x * channels : (x + 1) * channels]
        if color_type == 0:
            out[x * 4 : x * 4 + 4] = bytes((px[0], px[0], px[0], 255))
        elif color_type == 4:
            out[x * 4 : x * 4 + 4] = bytes((px[0], px[0], px[0], px[1]))
        elif color_type == 2:
            out[x * 4 : x * 4 + 4] = bytes((px[0], px[1], px[2], 255))
        else:
            out[x * 4 : x * 4 + 4] = bytes((px[0], px[1], px[2], px[3]))
    return bytes(out)


def _parse_palette(plte: bytes, trns: bytes) -> list[tuple[int, int, int, int]]:
    palette = []
    for i in range(len(plte) // 3):
        alpha = trns[i] if i < len(trns) else 255
        palette.append((plte[3 * i], plte[3 * i + 1], plte[3 * i + 2], alpha))
    return palette


def read_png_header(data: bytes) -> tuple[int, int]:
    """只讀寬高（尺寸不同時不必整張解碼）。"""
    chunks = _read_chunks(data)
    if not chunks or chunks[0][0] != b"IHDR":
        raise PngError("缺少 IHDR")
    width, height = struct.unpack(">II", chunks[0][1][:8])
    return int(width), int(height)


def decode_png(data: bytes) -> Image:
    """把 PNG 解成 8 位元 RGBA。"""
    chunks = _read_chunks(data)
    if not chunks or chunks[0][0] != b"IHDR":
        raise PngError("缺少 IHDR")
    width, height, depth, color_type, _comp, _filt, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1][:13]
    )
    if color_type not in _VALID_DEPTHS or depth not in _VALID_DEPTHS[color_type]:
        raise PngError(f"不支援的色彩型態／位元深度 {color_type}/{depth}")
    if interlace != 0:
        raise PngError("不支援交錯（interlaced）PNG")
    plte = b"".join(body for kind, body in chunks if kind == b"PLTE")
    trns = b"".join(body for kind, body in chunks if kind == b"tRNS")
    if color_type == 3 and not plte:
        raise PngError("調色盤圖缺少 PLTE")
    palette = _parse_palette(plte, trns)
    try:
        raw = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    except zlib.error as exc:
        raise PngError(f"IDAT 解壓失敗：{exc}") from exc
    bits_per_pixel = _CHANNELS[color_type] * depth
    stride = (width * bits_per_pixel + 7) // 8
    bpp = max(1, bits_per_pixel // 8)
    if len(raw) < height * (stride + 1):
        raise PngError("影像資料不足")
    rows: list[bytes] = []
    prev = bytes(stride)
    for y in range(height):
        start = y * (stride + 1)
        line = bytearray(raw[start + 1 : start + 1 + stride])
        _unfilter_row(raw[start], line, prev, bpp)
        prev = bytes(line)
        rows.append(_to_rgba(prev, width, color_type, depth, palette))
    return Image(width=width, height=height, rows=tuple(rows))


def encode_png_rgb(width: int, height: int, rows: list[bytes]) -> bytes:
    """把 RGB 8 位元的列寫成 PNG（濾波 0）。"""

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    return (
        PNG_SIGNATURE
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# 比對
# ---------------------------------------------------------------------------


def changed_pixels_in_row(old: bytes, new: bytes, pixel_tol: int) -> list[int]:
    """回傳這一列裡色差大於 ``pixel_tol`` 的像素 x 座標。"""
    if old == new:
        return []
    xs: list[int] = []
    for x in range(len(old) // 4):
        i = x * 4
        if old[i : i + 4] == new[i : i + 4]:
            continue
        diff = max(
            abs(old[i] - new[i]),
            abs(old[i + 1] - new[i + 1]),
            abs(old[i + 2] - new[i + 2]),
            abs(old[i + 3] - new[i + 3]),
        )
        if diff > pixel_tol:
            xs.append(x)
    return xs


def diff_image_rows(new: Image, changed: dict[int, list[int]]) -> list[bytes]:
    """差異圖：底圖是新圖轉灰、調淡，變化處標紅。"""
    out: list[bytes] = []
    for y, row in enumerate(new.rows):
        line = bytearray(new.width * 3)
        for x in range(new.width):
            i = x * 4
            gray = (row[i] * 299 + row[i + 1] * 587 + row[i + 2] * 114) // 1000
            alpha = row[i + 3]
            # 透明處以白底合成，再往白色拉一半，讓紅點顯眼。
            shade = (gray * alpha + 255 * (255 - alpha)) // 255
            shade = (shade + 255) // 2
            line[x * 3 : x * 3 + 3] = bytes((shade, shade, shade))
        for x in changed.get(y, []):
            line[x * 3 : x * 3 + 3] = b"\xff\x00\x00"
        out.append(bytes(line))
    return out


@dataclass(frozen=True)
class Change:
    path: str
    changed: int
    total: int

    @property
    def ratio(self) -> float:
        return self.changed / self.total if self.total else 0.0


@dataclass
class Report:
    old_dir: Path
    new_dir: Path
    threshold: float
    pixel_tol: int
    compared: int = 0
    changed: list[Change] = field(default_factory=list)
    minor: list[Change] = field(default_factory=list)
    only_old: list[str] = field(default_factory=list)
    only_new: list[str] = field(default_factory=list)
    size_mismatch: list[tuple[str, tuple[int, int], tuple[int, int]]] = field(default_factory=list)
    unreadable: list[tuple[str, str]] = field(default_factory=list)
    skipped_non_png: int = 0
    diff_out: Path | None = None

    @property
    def exit_code(self) -> int:
        if self.unreadable:
            return EXIT_INPUT_ERROR
        if self.changed or self.only_old or self.only_new or self.size_mismatch:
            return EXIT_CHANGED
        return EXIT_OK


def _collect(root: Path) -> tuple[dict[str, Path], int]:
    pngs: dict[str, Path] = {}
    others = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".png":
            pngs[rel] = path
        elif path.suffix.lower() in (".jpg", ".jpeg", ".gif", ".webp"):
            others += 1
    return pngs, others


def compare_pair(
    old_bytes: bytes, new_bytes: bytes, pixel_tol: int
) -> tuple[int, int, dict[int, list[int]], Image | None]:
    """回傳（有變的像素數、總像素、每列變化的 x、新圖）。尺寸不同時由呼叫端先擋。"""
    if old_bytes == new_bytes:
        width, height = read_png_header(new_bytes)
        return 0, width * height, {}, None
    old = decode_png(old_bytes)
    new = decode_png(new_bytes)
    changed: dict[int, list[int]] = {}
    count = 0
    for y in range(new.height):
        xs = changed_pixels_in_row(old.rows[y], new.rows[y], pixel_tol)
        if xs:
            changed[y] = xs
            count += len(xs)
    return count, new.width * new.height, changed, new


def _compare_one(report: Report, rel: str, old_path: Path, new_path: Path) -> None:
    old_bytes = old_path.read_bytes()
    new_bytes = new_path.read_bytes()
    old_size = read_png_header(old_bytes)
    new_size = read_png_header(new_bytes)
    if old_size != new_size:
        report.size_mismatch.append((rel, old_size, new_size))
        return
    count, total, rows, new_img = compare_pair(old_bytes, new_bytes, report.pixel_tol)
    report.compared += 1
    if count == 0:
        return
    change = Change(path=rel, changed=count, total=total)
    if change.ratio > report.threshold:
        report.changed.append(change)
        if report.diff_out is not None and new_img is not None:
            target = report.diff_out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                encode_png_rgb(new_img.width, new_img.height, diff_image_rows(new_img, rows))
            )
    else:
        report.minor.append(change)


def compare_dirs(
    old_dir: Path,
    new_dir: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    pixel_tol: int = DEFAULT_PIXEL_TOL,
    diff_out: Path | None = None,
) -> Report:
    report = Report(
        old_dir=old_dir,
        new_dir=new_dir,
        threshold=threshold,
        pixel_tol=pixel_tol,
        diff_out=diff_out,
    )
    old_pngs, old_others = _collect(old_dir)
    new_pngs, new_others = _collect(new_dir)
    report.skipped_non_png = old_others + new_others
    report.only_old = sorted(set(old_pngs) - set(new_pngs))
    report.only_new = sorted(set(new_pngs) - set(old_pngs))
    for rel in sorted(set(old_pngs) & set(new_pngs)):
        try:
            _compare_one(report, rel, old_pngs[rel], new_pngs[rel])
        except (PngError, OSError, struct.error) as exc:
            report.unreadable.append((rel, str(exc)))
    report.changed.sort(key=lambda c: (-c.ratio, c.path))
    report.minor.sort(key=lambda c: (-c.ratio, c.path))
    return report


# ---------------------------------------------------------------------------
# 輸出
# ---------------------------------------------------------------------------


def _pct(ratio: float) -> str:
    return f"{ratio * 100:.3f}%"


def _section(title: str, lines: list[str], markdown: bool) -> list[str]:
    head = f"## {title}（{len(lines)}）" if markdown else f"{title}（{len(lines)}）："
    body = [f"- {line}" if markdown else f"  {line}" for line in lines]
    return ["", head, *body] if lines else []


def format_report(report: Report, *, markdown: bool = False) -> str:
    """產生文字或 markdown 摘要。"""
    verdict = {
        EXIT_OK: "沒有超過門檻的變化",
        EXIT_CHANGED: "有變化",
        EXIT_INPUT_ERROR: "有檔案讀不了",
    }
    head = "# 截圖比對" if markdown else "截圖比對"
    lines = [
        head,
        "",
        f"舊：{report.old_dir.as_posix()}",
        f"新：{report.new_dir.as_posix()}",
        f"門檻：差異比例 > {_pct(report.threshold)}；單像素色差 > {report.pixel_tol}",
        f"結果：{verdict[report.exit_code]}（配對比對 {report.compared} 張）",
    ]
    if markdown:
        lines[2:6] = [f"- {line}" for line in lines[2:6]]
    if report.skipped_non_png:
        lines.append(("- " if markdown else "") + f"略過非 PNG 檔：{report.skipped_non_png} 個")

    def fmt(c: Change) -> str:
        return f"{c.path}：{_pct(c.ratio)}（{c.changed}／{c.total} 像素）"

    lines += _section("有變化", [fmt(c) for c in report.changed], markdown)
    lines += _section("細微變化（未超過門檻）", [fmt(c) for c in report.minor], markdown)
    lines += _section(
        "尺寸不同",
        [f"{p}：{o[0]}x{o[1]} → {n[0]}x{n[1]}" for p, o, n in report.size_mismatch],
        markdown,
    )
    lines += _section("只在舊的", report.only_old, markdown)
    lines += _section("只在新的", report.only_new, markdown)
    lines += _section("無法讀取", [f"{p}：{msg}" for p, msg in report.unreadable], markdown)
    if report.diff_out is not None and report.changed:
        lines += ["", f"差異圖：{report.diff_out.as_posix()}"]
    return "\n".join(lines) + "\n"


def _ratio_arg(text: str) -> float:
    value = float(text)
    if not 0.0 <= value < 1.0:
        raise argparse.ArgumentTypeError("門檻要在 0（含）到 1（不含）之間，例如 0.001＝0.1%")
    return value


def _tol_arg(text: str) -> int:
    value = int(text)
    if not 0 <= value <= 255:
        raise argparse.ArgumentTypeError("色差容忍要在 0～255 之間")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="比對新舊兩組截圖（PNG），列出有變化的圖與差異比例。",
        epilog="結束碼：0＝沒有超過門檻的變化；1＝有變化；2＝輸入錯誤。",
    )
    parser.add_argument("old", type=Path, help="舊截圖資料夾")
    parser.add_argument("new", type=Path, help="新截圖資料夾")
    parser.add_argument(
        "--threshold",
        type=_ratio_arg,
        default=DEFAULT_THRESHOLD,
        help="差異像素比例超過這個值才算有變化（0～1，預設 0：有任何差異就算）",
    )
    parser.add_argument(
        "--pixel-tol",
        type=_tol_arg,
        default=DEFAULT_PIXEL_TOL,
        help="單一像素 RGBA 通道差的最大值超過這個值才算這個像素有變（0～255，預設 0）",
    )
    parser.add_argument(
        "--diff-out", type=Path, help="把有變化的圖輸出差異圖（變化處標紅）到這個資料夾"
    )
    parser.add_argument(
        "--format", choices=("text", "markdown"), default="text", help="摘要格式（預設 text）"
    )
    parser.add_argument("--out", type=Path, help="摘要寫到這個檔（預設印到標準輸出）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    old_dir: Path = args.old
    new_dir: Path = args.new
    for label, d in (("舊", old_dir), ("新", new_dir)):
        if not d.is_dir():
            print(f"錯誤：{label}資料夾不存在或不是資料夾：{d}", file=sys.stderr)
            return EXIT_INPUT_ERROR
    report = compare_dirs(
        old_dir,
        new_dir,
        threshold=args.threshold,
        pixel_tol=args.pixel_tol,
        diff_out=args.diff_out,
    )
    if report.compared == 0 and not (
        report.only_old or report.only_new or report.size_mismatch or report.unreadable
    ):
        print("錯誤：兩個資料夾裡都沒有 PNG", file=sys.stderr)
        return EXIT_INPUT_ERROR
    text = format_report(report, markdown=args.format == "markdown")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        if isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
