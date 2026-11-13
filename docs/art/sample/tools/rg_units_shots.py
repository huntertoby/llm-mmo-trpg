"""Re-shoot the RG units and duel art samples (docs/art/RG樣張.md section 9).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/rg_units_shots.py <chrome tmp> [name ...] [--out <dir>]
    uv run python -I <this script> <tmp> --query "part=scene&w=800" --out <dir>

- Each part of rg-units.html draws one sheet into a canvas and puts its data URL
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
PAGE = ART / "sample" / "rg-units.html"

# (name, query, output path relative to docs/art)
SHOTS = [
    ("dolls", "part=dolls", "shots/rg-units/1-dolls.png"),
    ("shells", "part=shells", "shots/rg-units/2-shells.png"),
    ("lineup", "part=lineup", "shots/rg-units/3-lineup.png"),
    ("scene-1600", "part=scene&w=1600", "shots/rg-units/4-scene-1600.png"),
    ("scene-800", "part=scene&w=800", "shots/rg-units/5-scene-800.png"),
    ("zoom", "part=zoom", "shots/rg-units/6-scene-zoom3.png"),
    # v2 (art PM picked A/A/A): duel sheet shows only A; 7-duel.png (A vs B) is kept as a record
    ("duel", "part=duel2", "shots/rg-units/7-duel-v2.png"),
    ("parts", "part=parts", "shots/rg-units/8-parts.jpg"),
]

# Real-size dialog screenshots of rg-duel-dialog.html (window size, query, output)
DIALOG = ART / "sample" / "rg-duel-dialog.html"
DIALOGS = [
    # v2: only A; the B dialogs (11-, 12-) are kept as records and not re-shot
    ("dialog-1600", (1600, 900), "w=1600&v=A&e=wolf", "shots/rg-units/9-dialog-1600-A-v2.png"),
    ("dialog-800", (800, 600), "w=800&v=A&e=lord", "shots/rg-units/10-dialog-800-A-v2.png"),
    ("dialog-1600-scar", (1600, 900), "w=1600&v=A&e=scar", "shots/rg-units/13-dialog-1600-scar-v2.png"),
]

OUT_RE = re.compile(r'<textarea id="out">([^<]*)</textarea>')


def screenshot(tmp: Path, size: tuple[int, int], query: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--user-data-dir={tmp / 'chrome-prof-rgu'}",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=30000",
        f"--window-size={size[0]},{size[1]}",
        f"--screenshot={dest}",
        f"{DIALOG.as_uri()}?{query}&mute=1",
    ]
    subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    ok = dest.exists()
    print(f"{'ok' if ok else 'MISSING'} -> {dest}")
    return ok


def dump(tmp: Path, query: str) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--user-data-dir={tmp / 'chrome-prof-rgu'}",
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
    for name, size, query, rel in DIALOGS:
        if names and name not in names:
            continue
        dest = out_dir / rel if out_dir == ART else out_dir / Path(rel).name
        ok = screenshot(tmp, size, query, dest) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
