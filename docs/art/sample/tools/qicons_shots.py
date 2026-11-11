"""Reshoot the Q-style icon sample pages with headless Chrome (muted, file:// URL, no server).

Pages: docs/art/sample/q-icons.html (style sample) and q-icons-weapons.html (batch 1).

Usage (from the repo root):
    uv run python docs/art/sample/tools/qicons_shots.py            # every shot of both pages
    uv run python docs/art/sample/tools/qicons_shots.py weapon hud  # style sample: only these parts
    uv run python docs/art/sample/tools/qicons_shots.py weapons     # batch 1: every weapons-* shot
    uv run python docs/art/sample/tools/qicons_shots.py weapons-b sword  # batch 1: only these
    uv run python docs/art/sample/tools/qicons_shots.py --audit     # style sample audit table
    uv run python docs/art/sample/tools/qicons_shots.py --audit weapons  # batch 1 audit table
    uv run python docs/art/sample/tools/qicons_shots.py --hash      # batch 1 pixel fingerprints
    uv run python docs/art/sample/tools/qicons_shots.py --zoom 3 --out <dir> status   # magnified
    uv run python docs/art/sample/tools/qicons_shots.py --page q-icons-weapons.html \
        --query "part=b" --out <dir>                                # one ad-hoc shot

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
STYLE_PAGE = "q-icons.html"
WEAPON_PAGE = "q-icons-weapons.html"
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
# Batch 1 close-ups: one per kind (17 weapon kinds + 4 off-hand kinds).
WEAPON_KINDS = [
    "sword",
    "greatsword",
    "dagger",
    "dual_dagger",
    "axe",
    "hammer",
    "spear",
    "scythe",
    "fist",
    "whip",
    "bow",
    "crossbow",
    "longgun",
    "shotgun",
    "pistol",
    "dual_pistol",
    "staff",
    "round_shield",
    "kite_shield",
    "tome",
    "orb",
]
# (name, page, query, output relative to docs/art, device scale factor)
Shot = tuple[str, str, str, str, float]
SHOTS: list[Shot] = [
    ("all", STYLE_PAGE, "part=all", "shots/qicons/q-icons.png", 1),
    ("scene", STYLE_PAGE, "part=scene", "shots/qicons/q-icons-scene.png", 1),
    ("scene", STYLE_PAGE, "part=scene", "shots/qicons/q-icons-scene@2x.png", 2),
    *[(part, STYLE_PAGE, f"part={part}", f"closeup/qicons/{part}.png", 1) for part in CLOSEUPS],
]
WEAPON_SHOTS: list[Shot] = [
    ("weapons-a", WEAPON_PAGE, "part=a&group=melee1", "shots/qicons/weapons-a-melee1.png", 1),
    ("weapons-a", WEAPON_PAGE, "part=a&group=melee2", "shots/qicons/weapons-a-melee2.png", 1),
    ("weapons-a", WEAPON_PAGE, "part=a&group=ranged", "shots/qicons/weapons-a-ranged.png", 1),
    ("weapons-a", WEAPON_PAGE, "part=a&group=off", "shots/qicons/weapons-a-off.png", 1),
    ("weapons-b", WEAPON_PAGE, "part=b", "shots/qicons/weapons-b.png", 1),
    ("weapons-c", WEAPON_PAGE, "part=c", "shots/qicons/weapons-c.png", 1),
    ("weapons-var", WEAPON_PAGE, "part=var", "shots/qicons/weapons-var.png", 1),
    ("weapons-scene", WEAPON_PAGE, "part=scene", "shots/qicons/weapons-scene.png", 1),
    ("weapons-scene", WEAPON_PAGE, "part=scene", "shots/qicons/weapons-scene@2x.png", 2),
    ("weapons-cmp", WEAPON_PAGE, "part=cmp", "shots/qicons/weapons-cmp-whip.png", 1),
    *[
        (kind, WEAPON_PAGE, f"part=close&kind={kind}", f"closeup/qicons/weapons/{kind}.png", 1)
        for kind in WEAPON_KINDS
    ],
]


def url(page: str, query: str) -> str:
    return f"{(ART / 'sample' / page).as_uri()}?{query}"


def dump_dom(page: str, query: str) -> str:
    cmd = [*BASE, "--window-size=1280,900", "--dump-dom", url(page, query)]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    return done.stdout.decode("utf-8", "replace")


def shoot(page: str, query: str, out: Path, scale: float) -> bool:
    found = re.search(r'data-h="(\d+)"', dump_dom(page, query))
    if not found:
        print(f"{query}: page did not finish (no data-h)")
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
        url(page, query),
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    console = [ln for ln in done.stderr.decode("utf-8", "replace").splitlines() if "CONSOLE" in ln]
    print(f"{query}: {height}px -> {out.name}" + (f"  console: {console[:5]}" if console else ""))
    return not console


def audit(page: str, part: str = "audit") -> bool:
    found = re.search(r'id="audit"[^>]*>(.*?)</div>', dump_dom(page, f"part={part}"), re.S)
    if not found:
        print("audit: no table in the page")
        return False
    print(html.unescape(found.group(1)))
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("parts", nargs="*", help="only shoot these (default: all shots)")
    parser.add_argument("--audit", action="store_true", help="print the audit table and exit")
    parser.add_argument("--zoom", type=float, default=0, help="shoot the named parts at this scale")
    parser.add_argument("--out", type=Path, default=None, help="output folder for --zoom/--query")
    parser.add_argument("--page", default=STYLE_PAGE, help="page for --query")
    parser.add_argument("--query", default="", help="shoot one ad-hoc query of --page into --out")
    parser.add_argument("--hash", action="store_true", help="print batch 1 pixel fingerprints")
    args = parser.parse_args()
    if args.hash:
        return 0 if audit(WEAPON_PAGE, "hash") else 1
    if args.audit:
        return 0 if audit(WEAPON_PAGE if "weapons" in args.parts else STYLE_PAGE) else 1
    ok = True
    if args.query:
        out_dir = args.out or Path(tempfile.gettempdir())
        name = re.sub(r"[^A-Za-z0-9_.-]+", "-", args.query)
        return 0 if shoot(args.page, args.query, out_dir / f"{name}.png", args.zoom or 1) else 1
    if args.zoom:
        out_dir = args.out or Path(tempfile.gettempdir())
        for part in args.parts or CLOSEUPS:
            target = out_dir / f"{part}@{args.zoom:g}x.png"
            ok = shoot(STYLE_PAGE, f"part={part}", target, args.zoom) and ok
        return 0 if ok else 1
    wanted = set(args.parts)
    every_weapon = "weapons" in wanted
    for name, page, query, rel, scale in [*SHOTS, *WEAPON_SHOTS]:
        is_weapon = page == WEAPON_PAGE
        if wanted and name not in wanted and not (is_weapon and every_weapon):
            continue
        ok = shoot(page, query, ART / rel, scale) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
