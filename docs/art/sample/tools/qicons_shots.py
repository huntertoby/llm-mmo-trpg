"""Reshoot docs/art/sample/q-icons.html with headless Chrome (muted, file:// URL, no server).

Usage (from the repo root):
    uv run python docs/art/sample/tools/qicons_shots.py            # every shot
    uv run python docs/art/sample/tools/qicons_shots.py weapon hud  # only these parts
    uv run python docs/art/sample/tools/qicons_shots.py --audit     # print the rule-6 audit table
    uv run python docs/art/sample/tools/qicons_shots.py --zoom 3 --out <dir> status   # magnified

The page reports its own height in <html data-h>, so each shot is taken twice: once to
read the height, once at that window size.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
URL = (ART / "sample" / "q-icons.html").as_uri()
PROFILE = Path(tempfile.gettempdir()) / "qicons-shots-chrome-profile"
BASE = [
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--mute-audio",
    "--no-first-run",
    "--allow-file-access-from-files",
    f"--user-data-dir={PROFILE}",
    "--hide-scrollbars",
    "--virtual-time-budget=20000",
]
CLOSEUPS = ["weapon", "skill", "item", "status", "hud", "event", "ctrl", "core", "gear"]
# (part, output relative to docs/art, device scale factor)
SHOTS: list[tuple[str, str, float]] = [
    ("all", "shots/qicons/q-icons.png", 1),
    ("scene", "shots/qicons/q-icons-scene.png", 1),
    ("scene", "shots/qicons/q-icons-scene@2x.png", 2),
    *[(part, f"closeup/qicons/{part}.png", 1) for part in CLOSEUPS],
]


def dump_dom(part: str) -> str:
    cmd = [*BASE, "--window-size=1280,900", "--dump-dom", f"{URL}?part={part}"]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    return done.stdout.decode("utf-8", "replace")


def shoot(part: str, out: Path, scale: float) -> bool:
    found = re.search(r'data-h="(\d+)"', dump_dom(part))
    if not found:
        print(f"{part}: page did not finish (no data-h)")
        return False
    height = int(found.group(1))
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *BASE,
        f"--window-size=1280,{height}",
        f"--force-device-scale-factor={scale}",
        "--enable-logging=stderr",
        "--v=0",
        f"--screenshot={out}",
        f"{URL}?part={part}",
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    console = [ln for ln in done.stderr.decode("utf-8", "replace").splitlines() if "CONSOLE" in ln]
    print(f"{part}: {height}px -> {out.name}" + (f"  console: {console[:5]}" if console else ""))
    return not console


def audit() -> bool:
    found = re.search(r'id="audit"[^>]*>(.*?)</div>', dump_dom("audit"), re.S)
    if not found:
        print("audit: no table in the page")
        return False
    print(html.unescape(found.group(1)))
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("parts", nargs="*", help="only shoot these parts (default: all shots)")
    parser.add_argument("--audit", action="store_true", help="print the audit table and exit")
    parser.add_argument("--zoom", type=float, default=0, help="shoot the named parts at this scale")
    parser.add_argument("--out", type=Path, default=None, help="output folder for --zoom shots")
    args = parser.parse_args()
    if args.audit:
        return 0 if audit() else 1
    ok = True
    if args.zoom:
        out_dir = args.out or Path(tempfile.gettempdir())
        for part in args.parts or CLOSEUPS:
            ok = shoot(part, out_dir / f"{part}@{args.zoom:g}x.png", args.zoom) and ok
        return 0 if ok else 1
    for part, rel, scale in SHOTS:
        if args.parts and part not in args.parts:
            continue
        ok = shoot(part, ART / rel, scale) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
