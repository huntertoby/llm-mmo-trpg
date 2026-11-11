"""Reshoot the Q-style icon sample pages with headless Chrome (muted, file:// URL, no server).

Pages: docs/art/sample/q-icons.html (style sample), q-icons-weapons.html (batch 1),
q-icons-armor.html (batch 2) and q-icons-skills.html (batch 3, skill main art).

Usage (from the repo root):
    uv run python docs/art/sample/tools/qicons_shots.py            # every shot of both pages
    uv run python docs/art/sample/tools/qicons_shots.py weapon hud  # style sample: only these parts
    uv run python docs/art/sample/tools/qicons_shots.py weapons     # batch 1: every weapons-* shot
    uv run python docs/art/sample/tools/qicons_shots.py weapons-b sword  # batch 1: only these
    uv run python docs/art/sample/tools/qicons_shots.py armor       # batch 2: every armor-* shot
    uv run python docs/art/sample/tools/qicons_shots.py armor-b helmet-armor  # batch 2: only these
    uv run python docs/art/sample/tools/qicons_shots.py --audit     # style sample audit table
    uv run python docs/art/sample/tools/qicons_shots.py --audit weapons  # batch 1 audit table
    uv run python docs/art/sample/tools/qicons_shots.py --audit armor    # batch 2 audit table
    uv run python docs/art/sample/tools/qicons_shots.py --hash      # batch 1 pixel fingerprints
    uv run python docs/art/sample/tools/qicons_shots.py --hash armor     # batch 2 fingerprints
    uv run python docs/art/sample/tools/qicons_shots.py skills      # batch 3: every skills-* shot
    uv run python docs/art/sample/tools/qicons_shots.py skills-b skills-a-form  # batch 3: these
    uv run python docs/art/sample/tools/qicons_shots.py --audit skills   # batch 3 audit table
    uv run python docs/art/sample/tools/qicons_shots.py --hash skills    # batch 3 fingerprints
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
ARMOR_PAGE = "q-icons-armor.html"
SKILL_PAGE = "q-icons-skills.html"
PARTS_PAGE = "q-icons-parts.html"
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

# Batch 2 close-ups: one per kind (18 armor kinds + 3 accessory kinds). Shot names carry an
# "-armor" suffix so they never collide with batch 1 kinds or style sample parts.
ARMOR_KINDS = [
    "hood",
    "hat",
    "circlet",
    "cap",
    "helmet",
    "robe",
    "leather",
    "mail",
    "plate",
    "coat",
    "cloth_gloves",
    "leather_gloves",
    "gauntlets",
    "bracers",
    "shoes",
    "boots",
    "iron_boots",
    "greaves",
    "ring",
    "pendant",
    "charm",
]
ARMOR_GROUPS = ["head", "body", "hands", "feet", "acc"]
ARMOR_SHOTS: list[Shot] = [
    *[
        ("armor-a", ARMOR_PAGE, f"part=a&group={group}", f"shots/qicons/armor-a-{group}.png", 1)
        for group in ARMOR_GROUPS
    ],
    ("armor-b", ARMOR_PAGE, "part=b", "shots/qicons/armor-b.png", 1),
    *[
        ("armor-c", ARMOR_PAGE, f"part=c&group={group}", f"shots/qicons/armor-c-{group}.png", 1)
        for group in ARMOR_GROUPS
    ],
    ("armor-var", ARMOR_PAGE, "part=var", "shots/qicons/armor-var.png", 1),
    ("armor-scene", ARMOR_PAGE, "part=scene", "shots/qicons/armor-scene.png", 1),
    ("armor-scene", ARMOR_PAGE, "part=scene", "shots/qicons/armor-scene@2x.png", 2),
    *[
        (
            f"{kind}-armor",
            ARMOR_PAGE,
            f"part=close&kind={kind}",
            f"closeup/qicons/armor/{kind}.png",
            1,
        )
        for kind in ARMOR_KINDS
    ],
]


# Batch 3 (skill main art): the A tables double as close-ups (4x vector + 1x nearest-neighbour).
SKILL_GROUPS = ["weapon", "off", "el", "summon", "form", "motion", "act1", "act2"]
V3_BOW_GUN = [
    "鷹眼標記",
    "專注一擊",
    "下擊風箭",
    "疾風箭",
    "鉤索箭",
    "抵近射擊",
    "掩護射擊",
    "斷腱射擊",
    "散彈驅離",
    "煙霧彈",
    "毒霧箭",
    "煙幕箭",
    "築高台",
    "淬毒箭",
    "火引箭靈",
    "高處狙擊",
    "遠距狙擊",
    "近距轟擊",
]
V3_OTHER = [
    "聖光印地",
    "冰牆術",
    "灰燼誓約",
    "聖焰壇",
    "霜華祝禱",
    "墓霜",
    "煙霧彈（裝備）",
    "聖水",
    "燈油瓶",
    "碎防拳",
    "鐵拳連打",
    "震擊",
    "穿陣刺",
    "穿透射擊",
    "風刃",
]
SKILL_SHOTS: list[Shot] = [
    *[
        (
            f"skills-a-{group}",
            SKILL_PAGE,
            f"part=a&group={group}",
            f"closeup/qicons/skills/a-{group}.png",
            1,
        )
        for group in SKILL_GROUPS
    ],
    ("skills-starters", SKILL_PAGE, "part=starters", "closeup/qicons/skills/starters.png", 1),
    ("skills-b", SKILL_PAGE, "part=b", "shots/qicons/skills-b.png", 1),
    ("skills-real", SKILL_PAGE, "part=real", "shots/qicons/skills-real.png", 1),
    ("skills-scene", SKILL_PAGE, "part=scene", "shots/qicons/skills-scene.png", 1),
    ("skills-scene", SKILL_PAGE, "part=scene", "shots/qicons/skills-scene@2x.png", 2),
    # v3: every look that changed in v3, current 40 next to Q 40/28/24 (1x, nearest-neighbour).
    (
        "skills-v3",
        SKILL_PAGE,
        "part=review&only=" + ",".join(V3_BOW_GUN),
        "closeup/qicons/skills/v3-bow-gun.png",
        1,
    ),
    (
        "skills-v3",
        SKILL_PAGE,
        "part=review&only=" + ",".join(V3_OTHER),
        "closeup/qicons/skills/v3-surface-fist-thrust.png",
        1,
    ),
]

# Batch 4 (skeleton badges, part chips, skill card glyphs, 56/96 assembled icons): the A tables
# double as close-ups (4x vector + 1x nearest-neighbour), one per group.
PARTS_GROUPS = [
    "skeleton",
    "effect1",
    "effect2",
    "effect3",
    "surface",
    "status",
    "condition",
    "cost",
    "trigger1",
    "trigger2",
    "link",
    "shape",
    "change",
    "element",
    "card1",
    "card2",
]
# (group query, file name suffix); the cross-category "near" sheets are shot three at a time.
PARTS_B_GROUPS = [
    ("skeleton", "skeleton"),
    ("effect", "effect"),
    ("surface,status", "surface-status"),
    ("condition,cost", "condition-cost"),
    ("trigger,link", "trigger-link"),
    ("shape,change", "shape-change"),
    ("element,card", "element-card"),
    ("near&nfrom=0&nn=3", "near-1"),
    ("near&nfrom=3&nn=3", "near-2"),
    ("near&nfrom=6&nn=3", "near-3"),
]
PARTS_SHOTS: list[Shot] = [
    *[
        (
            f"parts-a-{group}",
            PARTS_PAGE,
            f"part=a&group={group}",
            f"closeup/qicons/parts/a-{group}.png",
            1,
        )
        for group in PARTS_GROUPS
    ],
    *[
        (
            "parts-b",
            PARTS_PAGE,
            f"part=b&group={group}",
            f"shots/qicons/parts-b-{suffix}.png",
            1,
        )
        for group, suffix in PARTS_B_GROUPS
    ],
    ("parts-asm", PARTS_PAGE, "part=asm&from=0&n=12", "shots/qicons/parts-asm-1.png", 1),
    ("parts-asm", PARTS_PAGE, "part=asm&from=12&n=12", "shots/qicons/parts-asm-2.png", 1),
    ("parts-scene", PARTS_PAGE, "part=scene", "shots/qicons/parts-scene.png", 1),
    ("parts-scene", PARTS_PAGE, "part=scene", "shots/qicons/parts-scene@2x.png", 2),
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
    parser.add_argument("--hash", action="store_true", help="print pixel fingerprints")
    args = parser.parse_args()
    batch_page = (
        ARMOR_PAGE
        if "armor" in args.parts
        else SKILL_PAGE
        if "skills" in args.parts
        else PARTS_PAGE
        if "parts" in args.parts
        else WEAPON_PAGE
    )
    if args.hash:
        # "var" (batch 2 only): fingerprints of every material/dye/keyword variant.
        variants = "var" in args.parts and batch_page == ARMOR_PAGE
        return 0 if audit(batch_page, "hash&sub=var" if variants else "hash") else 1
    if args.audit:
        batched = bool({"armor", "weapons", "skills", "parts"} & set(args.parts))
        return 0 if audit(batch_page if batched else STYLE_PAGE) else 1
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
    whole = {
        WEAPON_PAGE: "weapons" in wanted,
        ARMOR_PAGE: "armor" in wanted,
        SKILL_PAGE: "skills" in wanted,
        PARTS_PAGE: "parts" in wanted,
    }
    shots = [*SHOTS, *WEAPON_SHOTS, *ARMOR_SHOTS, *SKILL_SHOTS, *PARTS_SHOTS]
    for name, page, query, rel, scale in shots:
        if wanted and name not in wanted and not whole.get(page, False):
            continue
        ok = shoot(page, query, ART / rel, scale) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
