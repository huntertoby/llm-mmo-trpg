"""Re-shoot the boss-part samples (docs/art/頭目部位.md; page docs/art/sample/boss-parts.html).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/boss_parts_shots.py <chrome tmp> [name ...] [--out <dir>]
    uv run python -I docs/art/sample/tools/boss_parts_shots.py <tmp> --query "part=menu" --out <dir>

- Each part of boss-parts.html draws one sheet into a canvas and puts its data URL
  (JPEG quality 80, or PNG for the true-1x sheets) in <textarea id="out">; this script reads it
  with headless Chrome --dump-dom and writes the file (pixels are exactly the canvas).
- Always --mute-audio; the page URL carries ?mute=1. One Chrome at a time (foreground).
- <chrome tmp> is your own scratch folder (the Chrome profile goes there), so two agents
  shooting at the same time do not share a profile.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
PAGE = ART / "sample" / "boss-parts.html"

# (name, query, output path relative to docs/art)
SHOTS = [
    ("menu", "part=menu", "shots/boss-parts/1-menu.jpg"),
    ("icons", "part=icons", "shots/boss-parts/2-icons.jpg"),
    ("bars", "part=bars", "shots/boss-parts/3-bars.jpg"),
    ("field-1600", "part=field&w=1600", "shots/boss-parts/4-field-1600.jpg"),
    ("field-800", "part=field&w=800", "shots/boss-parts/5-field-800.jpg"),
    ("break", "part=break", "shots/boss-parts/6-break.jpg"),
    ("after", "part=after", "shots/boss-parts/7-after.jpg"),
    ("collide", "part=collide", "shots/boss-parts/8-collide.jpg"),
    ("true1x", "part=true1x", "closeup/boss-parts/true1x-icons-menu.png"),
    ("true1x-strip", "part=true1x&g=strip", "closeup/boss-parts/true1x-strip.png"),
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
        "--virtual-time-budget=90000",
        "--window-size=1280,900",
        "--enable-logging=stderr",
        "--v=0",
        "--dump-dom",
        f"{PAGE.as_uri()}?{query}&mute=1",
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=900, check=False)
    errors = [
        ln
        for ln in done.stderr.decode("utf-8", "replace").splitlines()
        if "CONSOLE" in ln and "willReadFrequently" not in ln
    ]
    if errors:
        print(f"{query}: console {errors[:5]}")
    return done.stdout.decode("utf-8", "replace")


def save(found: re.Match[str] | None, dest: Path, name: str) -> bool:
    if not found or "," not in found.group(1):
        print(f"{name}: page did not finish (no #out)")
        return False
    data = base64.b64decode(found.group(1).split(",", 1)[1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"{name}: {len(data) // 1024} KB -> {dest}")
    return True


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
    if "--query" in rest:  # ad-hoc: <out>/probe.jpg|png
        i = rest.index("--query")
        query = rest[i + 1]
        ext = ".png" if "true1x" in query else ".jpg"
        ok = save(OUT_RE.search(dump(tmp, query)), out_dir / f"probe{ext}", "probe")
        return 0 if ok else 1
    names = set(rest)
    ok = True
    for name, query, rel in SHOTS:
        if names and name not in names:
            continue
        dest = out_dir / rel if out_dir == ART else out_dir / Path(rel).name
        ok = save(OUT_RE.search(dump(tmp, query)), dest, name) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
