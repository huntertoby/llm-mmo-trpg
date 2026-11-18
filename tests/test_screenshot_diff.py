"""``scripts/screenshot_diff.py``（TL-1）：截圖比對腳本。

測試用的 PNG 都在這裡用標準庫產生（幾個像素大），不放圖檔。
"""

from __future__ import annotations

import importlib.util
import struct
import sys
import zlib
from pathlib import Path
from types import ModuleType

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "screenshot_diff.py"

Pixel = tuple[int, int, int, int]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("screenshot_diff", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["screenshot_diff"] = module
    spec.loader.exec_module(module)
    return module


sd = _load()


# ---------------------------------------------------------------------------
# 測試用 PNG 編碼器（可指定色彩型態與每列濾波）
# ---------------------------------------------------------------------------


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _filter(ftype: int, line: bytes, prev: bytes, bpp: int) -> bytes:
    out = bytearray(len(line))
    for i, value in enumerate(line):
        left = line[i - bpp] if i >= bpp else 0
        up = prev[i]
        upleft = prev[i - bpp] if i >= bpp else 0
        pred = [0, left, up, (left + up) >> 1, _paeth(left, up, upleft)][ftype]
        out[i] = (value - pred) & 0xFF
    return bytes(out)


def _encode_row(
    row: list[Pixel], color_type: int, depth: int, palette: list[Pixel] | None
) -> bytes:
    """一列 RGBA 轉成指定色彩型態的原始位元組（濾波前）。"""
    if depth == 16:  # 只測 16 位元 RGBA；低位元組放雜值，解碼應丟掉
        return bytes(b for px in row for c in px for b in (c, 0x5A))
    if color_type == 3:
        assert palette is not None
        idx = [palette.index(px) for px in row]
        per = 8 // depth
        packed = bytearray()
        for start in range(0, len(idx), per):
            byte = 0
            for k, v in enumerate(idx[start : start + per]):
                byte |= v << (8 - depth * (k + 1))
            packed.append(byte)
        return bytes(packed)
    channels: dict[int, tuple[int, ...]] = {6: (0, 1, 2, 3), 2: (0, 1, 2), 0: (0,), 4: (0, 3)}
    return bytes(px[i] for px in row for i in channels[color_type])


def make_png(
    pixels: list[list[Pixel]],
    *,
    color_type: int = 6,
    filters: tuple[int, ...] = (0,),
    palette: list[Pixel] | None = None,
    depth: int = 8,
) -> bytes:
    """把 RGBA 像素編成 PNG；``filters`` 依列循環使用。"""
    height, width = len(pixels), len(pixels[0])
    lines = [_encode_row(row, color_type, depth, palette) for row in pixels]
    bpp = max(1, {6: 4, 2: 3, 0: 1, 4: 2, 3: 1}[color_type] * depth // 8)
    raw = bytearray()
    prev = bytes(len(lines[0]))
    for y, line in enumerate(lines):
        ftype = filters[y % len(filters)]
        raw.append(ftype)
        raw += _filter(ftype, line, prev, bpp)
        prev = line
    ihdr = struct.pack(">IIBBBBB", width, height, depth, color_type, 0, 0, 0)
    body = _chunk(b"IHDR", ihdr)
    if color_type == 3:
        assert palette is not None
        body += _chunk(b"PLTE", bytes(c for px in palette for c in px[:3]))
        body += _chunk(b"tRNS", bytes(px[3] for px in palette))
    signature: bytes = sd.PNG_SIGNATURE
    return signature + body + _chunk(b"IDAT", zlib.compress(bytes(raw))) + _chunk(b"IEND", b"")


def grid(width: int, height: int) -> list[list[Pixel]]:
    """有漸層的小圖，讓每種濾波都有非零的預測值。"""
    return [
        [
            ((x * 37 + y * 11) % 256, (x * 5 + y * 71) % 256, (x * y * 13) % 256, 255)
            for x in range(width)
        ]
        for y in range(height)
    ]


def rgba_rows(pixels: list[list[Pixel]]) -> tuple[bytes, ...]:
    return tuple(bytes(c for px in row for c in px) for row in pixels)


# ---------------------------------------------------------------------------
# 解碼
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filters", [(0,), (1,), (2,), (3,), (4,), (0, 1, 2, 3, 4)])
def test_decode_rgba_every_filter(filters: tuple[int, ...]) -> None:
    pixels = grid(7, 6)
    img = sd.decode_png(make_png(pixels, filters=filters))
    assert (img.width, img.height) == (7, 6)
    assert img.rows == rgba_rows(pixels)


def test_decode_rgb_and_gray_and_gray_alpha() -> None:
    pixels = grid(5, 4)
    rgb = sd.decode_png(make_png(pixels, color_type=2, filters=(4, 1)))
    assert rgb.rows == rgba_rows([[(r, g, b, 255) for r, g, b, _ in row] for row in pixels])

    gray_px = [[(v, v, v, 255) for v in (0, 90, 200)], [(255, 255, 255, 255)] * 3]
    gray = sd.decode_png(make_png(gray_px, color_type=0, filters=(2,)))
    assert gray.rows == rgba_rows(gray_px)

    ga_px = [[(10, 10, 10, 0), (200, 200, 200, 128)]]
    ga = sd.decode_png(make_png(ga_px, color_type=4, filters=(3,)))
    assert ga.rows == rgba_rows(ga_px)


@pytest.mark.parametrize("depth", [8, 4, 2, 1])
def test_decode_palette_with_transparency(depth: int) -> None:
    palette: list[Pixel] = [(255, 0, 0, 255), (0, 0, 255, 0)]
    pixels = [[palette[(x + y) % 2] for x in range(9)] for y in range(3)]
    img = sd.decode_png(make_png(pixels, color_type=3, palette=palette, depth=depth))
    assert img.rows == rgba_rows(pixels)


def test_decode_16_bit_takes_high_byte() -> None:
    pixels = grid(3, 2)
    img = sd.decode_png(make_png(pixels, color_type=6, depth=16, filters=(4,)))
    assert img.rows == rgba_rows(pixels)


def test_encode_then_decode_round_trip() -> None:
    rows = [bytes([1, 2, 3, 4, 5, 6]), bytes([7, 8, 9, 10, 11, 12])]
    img = sd.decode_png(sd.encode_png_rgb(2, 2, rows))
    assert img.rows == (bytes([1, 2, 3, 255, 4, 5, 6, 255]), bytes([7, 8, 9, 255, 10, 11, 12, 255]))


def test_rejects_non_png_and_interlaced() -> None:
    with pytest.raises(sd.PngError):
        sd.decode_png(b"\xff\xd8\xff\xe0 jpeg")
    data = bytearray(make_png(grid(2, 2)))
    # IHDR 的 interlace 位元組在簽名 8＋長度 4＋型態 4＋12 位元組之後
    data[8 + 8 + 12] = 1
    ihdr_body = bytes(data[16:29])
    data[29:33] = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_body))
    with pytest.raises(sd.PngError, match="交錯"):
        sd.decode_png(bytes(data))


# ---------------------------------------------------------------------------
# 比對資料夾
# ---------------------------------------------------------------------------


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _modified(
    pixels: list[list[Pixel]], cells: list[tuple[int, int]], delta: int
) -> list[list[Pixel]]:
    out = [list(row) for row in pixels]
    for x, y in cells:
        r, g, b, a = out[y][x]
        out[y][x] = ((r + delta) % 256, g, b, a)
    return out


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    old, new = tmp_path / "old", tmp_path / "new"
    base = grid(10, 10)
    _write(old / "same.png", make_png(base))
    _write(new / "same.png", make_png(base))
    # 同樣的像素、不同的濾波：檔案位元組不同，但不算變化
    _write(old / "refiltered.png", make_png(base, filters=(0,)))
    _write(new / "refiltered.png", make_png(base, filters=(4, 1)))
    _write(old / "sub/big.png", make_png(base))
    _write(new / "sub/big.png", make_png(_modified(base, [(x, 0) for x in range(10)], 50)))
    _write(old / "small.png", make_png(base))
    _write(new / "small.png", make_png(_modified(base, [(3, 3)], 4)))
    _write(old / "resized.png", make_png(grid(10, 10)))
    _write(new / "resized.png", make_png(grid(10, 12)))
    _write(old / "gone.png", make_png(base))
    _write(new / "added.png", make_png(base))
    _write(new / "photo.jpg", b"not compared")
    return old, new


def test_compare_dirs_lists_every_category(dirs: tuple[Path, Path]) -> None:
    old, new = dirs
    report = sd.compare_dirs(old, new)
    assert [(c.path, c.changed, c.total) for c in report.changed] == [
        ("sub/big.png", 10, 100),
        ("small.png", 1, 100),
    ]
    assert report.minor == []
    assert report.only_old == ["gone.png"]
    assert report.only_new == ["added.png"]
    assert report.size_mismatch == [("resized.png", (10, 10), (10, 12))]
    assert report.skipped_non_png == 1
    assert report.compared == 4
    assert report.exit_code == sd.EXIT_CHANGED


def test_pixel_tol_and_threshold(dirs: tuple[Path, Path]) -> None:
    old, new = dirs
    tolerant = sd.compare_dirs(old, new, pixel_tol=4)
    assert [c.path for c in tolerant.changed] == ["sub/big.png"]
    assert tolerant.minor == []

    loose = sd.compare_dirs(old, new, threshold=0.05)
    assert [c.path for c in loose.changed] == ["sub/big.png"]
    assert [c.path for c in loose.minor] == ["small.png"]


def test_exit_zero_when_only_minor_changes(tmp_path: Path) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    base = grid(10, 10)
    _write(old / "a.png", make_png(base))
    _write(new / "a.png", make_png(_modified(base, [(0, 0)], 1)))
    assert sd.main([str(old), str(new), "--threshold", "0.05"]) == sd.EXIT_OK
    assert sd.main([str(old), str(new)]) == sd.EXIT_CHANGED


def test_diff_image_marks_changed_pixels_red(dirs: tuple[Path, Path], tmp_path: Path) -> None:
    old, new = dirs
    out = tmp_path / "diff"
    sd.compare_dirs(old, new, diff_out=out)
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*.png")) == [
        "small.png",
        "sub/big.png",
    ]
    img = sd.decode_png((out / "small.png").read_bytes())
    red = [
        (x, y)
        for y, row in enumerate(img.rows)
        for x in range(10)
        if row[x * 4 : x * 4 + 4] == b"\xff\x00\x00\xff"
    ]
    assert red == [(3, 3)]


def test_main_markdown_summary_and_exit_codes(
    dirs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    old, new = dirs
    summary = tmp_path / "out" / "summary.md"
    assert sd.main([str(old), str(new), "--format", "markdown", "--out", str(summary)]) == 1
    text = summary.read_text(encoding="utf-8")
    assert "## 有變化（2）" in text
    assert text.index("sub/big.png：10.000%") < text.index("small.png：1.000%")
    assert "## 尺寸不同（1）" in text and "resized.png：10x10 → 10x12" in text
    assert "## 只在舊的（1）" in text and "## 只在新的（1）" in text
    assert "略過非 PNG 檔：1 個" in text

    assert sd.main([str(old), str(new)]) == 1
    assert "有變化（2）：" in capsys.readouterr().out


def test_main_input_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    empty_a, empty_b = tmp_path / "a", tmp_path / "b"
    empty_a.mkdir()
    empty_b.mkdir()
    assert sd.main([str(tmp_path / "missing"), str(empty_b)]) == sd.EXIT_INPUT_ERROR
    assert sd.main([str(empty_a), str(empty_b)]) == sd.EXIT_INPUT_ERROR
    assert "沒有 PNG" in capsys.readouterr().err

    _write(empty_a / "bad.png", b"\x89PNG\r\n\x1a\nbroken")
    _write(empty_b / "bad.png", b"\x89PNG\r\n\x1a\nbroken!")
    assert sd.main([str(empty_a), str(empty_b)]) == sd.EXIT_INPUT_ERROR

    with pytest.raises(SystemExit) as exc:
        sd.main([str(empty_a), str(empty_b), "--threshold", "2"])
    assert exc.value.code == sd.EXIT_INPUT_ERROR


def test_identical_folders_exit_zero(tmp_path: Path) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    _write(old / "x.png", make_png(grid(4, 4)))
    _write(new / "x.png", make_png(grid(4, 4)))
    assert sd.main([str(old), str(new)]) == sd.EXIT_OK
