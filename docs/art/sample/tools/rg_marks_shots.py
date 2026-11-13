"""Re-shoot the RG battle-mark samples (docs/art/RG樣張.md), version 2 (*-v2 files).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/rg_marks_shots.py <chrome tmp> [name ...] [--out <dir>]
    uv run python -I <this script> <tmp> --query "part=scene&w=800" --out <dir>

- Each part of rg-marks.html draws one sheet into a canvas and puts its data URL
  (PNG for true-1x / nearest-neighbour sheets, JPEG quality 80 for the others) in
  <textarea id="out">; this script reads it with headless Chrome --dump-dom and writes
  the file, so the pixels are exactly the canvas (no device-pixel-ratio effects).
- No remote-debugging port is opened. Always --mute-audio; the page URL carries ?mute=1.
  One Chrome at a time (foreground); the Chrome profile lives in <chrome tmp>.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
PAGE = ART / "sample" / "rg-marks.html"

# (name, query, output path relative to docs/art)
SHOTS = [
    ("scene-1600", "part=scene&w=1600", "shots/rg-marks/1-scene-1600-v2.png"),
    ("scene-800", "part=scene&w=800", "shots/rg-marks/2-scene-800-v2.png"),
    ("zoom-1600", "part=zoom&w=1600", "shots/rg-marks/3-zoom3-1600-v2.png"),
    ("zoom-800", "part=zoom&w=800", "shots/rg-marks/4-zoom3-800-v2.png"),
    ("anim", "part=anim", "shots/rg-marks/5-keyframes-v2.png"),
    ("collide", "part=collide", "shots/rg-marks/6-collide-v2.jpg"),
    ("ground", "part=ground", "shots/rg-marks/7-grounds-v2.jpg"),
    ("parts", "part=parts", "shots/rg-marks/8-parts-v2.png"),
]

OUT_RE = re.compile(r'<textarea id="out">([^<]*)</textarea>')


def dump(tmp: Path, query: str) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--user-data-dir={tmp / 'chrome-prof-rg'}",
        "--virtual-time-budget=60000",
        "--window-size=1280,900",
        "--enable-logging=stderr",
        "--v=0",
        "--dump-dom",
        f"{PAGE.as_uri()}?{query}&mute=1",
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    errors = [
        ln
        for ln in done.stderr.decode("utf-8", "replace").splitlines()
        if "CONSOLE" in ln and "willReadFrequently" not in ln
    ]
    if errors:
        print(f"{query}: console {errors[:5]}")
    return done.stdout.decode("utf-8", "replace")


def save(found: re.Match[str] | None, dest: Path) -> bool:
    if not found or "," not in found.group(1):
        return False
    data = base64.b64decode(found.group(1).split(",", 1)[1])
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
    rest = argv[1:]
    out_dir = ART
    if "--out" in rest:
        i = rest.index("--out")
        out_dir = Path(rest[i + 1])
        rest = rest[:i] + rest[i + 2 :]
    if "--query" in rest:
        i = rest.index("--query")
        html = dump(tmp, rest[i + 1])
        ext = ".png" if "data:image/png" in html else ".jpg"
        if not save(OUT_RE.search(html), out_dir / f"probe{ext}"):
            print("page did not finish")
            return 1
        return 0
    names = set(rest)
    ok = True
    for name, query, rel in SHOTS:
        if names and name not in names:
            continue
        dest = out_dir / rel if out_dir == ART else out_dir / Path(rel).name
        if not save(OUT_RE.search(dump(tmp, query)), dest):
            print(f"{name}: page did not finish (no #out)")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
