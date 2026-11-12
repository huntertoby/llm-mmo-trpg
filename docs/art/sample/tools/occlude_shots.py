"""Re-shoot the occlusion-outline samples (docs/art/被遮擋剪影外框.md).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/occlude_shots.py <chrome tmp> [name ...] [--out <dir>]
    (v2: 11 sheets incl. "fragment"; ratios are measured at model pixels)
    uv run python -I docs/art/sample/tools/occlude_shots.py <chrome temp dir> --measure

- Each part of occlude-outline.html draws one sheet into a canvas and puts its data URL
  (JPEG quality 80, or PNG for the true-1x sheets) in <textarea id="out">; this script reads it
  with headless Chrome --dump-dom and writes the file, so the pixels are exactly the canvas
  (no device-pixel-ratio or window-size effects).
- Always --mute-audio; the page URL carries ?mute=1. One Chrome at a time (foreground).
- --measure prints the coverage table (?part=measure) instead of writing images.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
PAGE = ART / "sample" / "occlude-outline.html"

# (name, query, output path relative to docs/art)
SHOTS = [
    ("boss", "part=boss", "shots/occlude/1-boss.jpg"),
    ("pair", "part=pair", "shots/occlude/2-pairs.jpg"),
    ("flash", "part=flash", "shots/occlude/3-flash.jpg"),
    ("team", "part=team", "shots/occlude/4-team.jpg"),
    ("tune", "part=tune", "shots/occlude/5-tune.jpg"),
    ("true1x-1600", "part=true1x&w=1600", "closeup/occlude/6-true1x-1600.png"),
    ("true1x-800", "part=true1x&w=800", "closeup/occlude/6-true1x-800.png"),
    ("field-1600", "part=field&w=1600", "shots/occlude/7-field-1600.jpg"),
    ("field-800", "part=field&w=800", "shots/occlude/8-field-800.jpg"),
    ("collide", "part=collide", "shots/occlude/9-collide.jpg"),
    ("fragment", "part=fragment", "closeup/occlude/10-fragment-55-70.jpg"),
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
        f"--user-data-dir={tmp / 'chrome-prof'}",
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


def main(argv: list[str]) -> int:
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
    if "--query" in rest:  # ad-hoc: <out>/probe.jpg (e.g. "part=probe&s=sl-ally&z=5")
        i = rest.index("--query")
        found = OUT_RE.search(dump(tmp, rest[i + 1]))
        if not found:
            print("page did not finish")
            return 1
        dest = out_dir / "probe.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(found.group(1).split(",", 1)[1]))
        print(f"probe -> {dest}")
        return 0
    if "--measure" in rest:
        found = OUT_RE.search(dump(tmp, "part=measure"))
        print(found.group(1) if found else "page did not finish")
        return 0 if found else 1
    names = set(rest)
    ok = True
    for name, query, rel in SHOTS:
        if names and name not in names:
            continue
        found = OUT_RE.search(dump(tmp, query))
        if not found or "," not in found.group(1):
            print(f"{name}: page did not finish (no #out)")
            ok = False
            continue
        data = base64.b64decode(found.group(1).split(",", 1)[1])
        dest = out_dir / rel if out_dir == ART else out_dir / Path(rel).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"{name}: {len(data) // 1024} KB -> {dest}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
