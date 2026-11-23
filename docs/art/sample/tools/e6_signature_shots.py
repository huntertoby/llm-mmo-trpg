"""Re-shoot the E6 signature-effect samples (docs/art/E6-招牌-美術.md).

Usage (from the repo root; needs PIL):
    uv run --no-project --with pillow python -I <this script> <chrome tmp> [name ...]
    uv run --no-project --with pillow python -I <this script> <tmp> --audit

- DOM parts (cards, offer, world, panel, compare, icons, anim) are shot at window
  widths 1600 and 800 with --force-device-scale-factor=1: first --dump-dom reads the
  page height (data-h), then --screenshot at that height; saved as JPEG quality 80.
- "t1x" is a canvas sheet (true 1x icons + nearest-neighbour x6 drawn with
  imageSmoothingEnabled=false); its data URL is read from <textarea id="out"> and
  written as PNG unchanged.
- No remote-debugging port, no server (file:// only). Always --mute-audio and ?mute=1.
  One Chrome at a time, foreground; the Chrome profile lives in <chrome tmp>.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
PAGE = ART / "sample" / "e6-signature.html"
OUT_DIR = ART / "shots" / "e6-signature"

DOM_PARTS = [
    ("cards", "1-cards"),
    ("offer", "2-offer"),
    ("world", "3-world"),
    ("panel", "4-panel"),
    ("compare", "5-compare"),
    ("icons", "6-icons"),
    ("anim", "7-anim"),
]
WIDTHS = (1600, 800)
H_RE = re.compile(r'data-h="(\d+)"')
OUT_RE = re.compile(r'<textarea id="out">([^<]*)</textarea>')
AUDIT_RE = re.compile(r'<pre id="audit">([^<]*)</pre>')


def chrome(
    tmp: Path, query: str, width: int, height: int, extra: list[str]
) -> subprocess.CompletedProcess[bytes]:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--user-data-dir={tmp / 'chrome-prof-e6'}",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=20000",
        f"--window-size={width},{height}",
        *extra,
        f"{PAGE.as_uri()}?{query}&mute=1",
    ]
    return subprocess.run(cmd, capture_output=True, timeout=300, check=False)


def dump(tmp: Path, query: str, width: int = 1280) -> str:
    return chrome(tmp, query, width, 900, ["--dump-dom"]).stdout.decode("utf-8", "replace")


def shoot_dom(tmp: Path, part: str, stem: str, width: int) -> bool:
    found = H_RE.search(dump(tmp, f"part={part}", width))
    if not found:
        print(f"{part}@{width}: page did not finish (no data-h)")
        return False
    height = int(found.group(1)) + 16
    png = tmp / f"e6-{part}-{width}.png"
    png.unlink(missing_ok=True)
    chrome(tmp, f"part={part}", width, height, [f"--screenshot={png}"])
    if not png.exists():
        print(f"{part}@{width}: no screenshot")
        return False
    dest = OUT_DIR / f"{stem}-{width}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.open(png).convert("RGB").save(dest, "JPEG", quality=80)
    print(f"{width}x{height} -> {dest}")
    return True


def shoot_t1x(tmp: Path) -> bool:
    found = OUT_RE.search(dump(tmp, "part=t1x"))
    if not found or "," not in found.group(1):
        print("t1x: no canvas data")
        return False
    data = base64.b64decode(found.group(1).split(",", 1)[1])
    dest = OUT_DIR / "8-icons-true1x.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"{len(data) // 1024} KB -> {dest}")
    return True


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if not argv:
        print(__doc__)
        return 2
    tmp = Path(argv[0])
    tmp.mkdir(parents=True, exist_ok=True)
    if argv[1:2] == ["--audit"]:
        found = AUDIT_RE.search(dump(tmp, "part=audit"))
        print(found.group(1) if found else "no audit table")
        return 0 if found else 1
    names = set(argv[1:])
    ok = True
    for part, stem in DOM_PARTS:
        if names and part not in names:
            continue
        for width in WIDTHS:
            ok = shoot_dom(tmp, part, stem, width) and ok
    if not names or "t1x" in names:
        ok = shoot_t1x(tmp) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
