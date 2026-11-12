"""Reshoot the Q-style icon sample pages with headless Chrome (muted, file:// URL, no server).

Pages: docs/art/sample/q-icons.html (style sample), q-icons-weapons.html (batch 1),
q-icons-armor.html (batch 2), q-icons-skills.html (batch 3, skill main art), q-icons-parts.html
(batch 4), q-icons-status.html (batch 5, status icons) and q-icons-keywords.html (batch 5b,
the keyword chips on gear icons).

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
    uv run python docs/art/sample/tools/qicons_shots.py status      # batch 5: every status-* shot
    uv run python docs/art/sample/tools/qicons_shots.py --audit status   # batch 5 audit table
    uv run python docs/art/sample/tools/qicons_shots.py --hash status    # batch 5 fingerprints
    uv run python docs/art/sample/tools/qicons_shots.py style-status     # style sample status
    uv run python docs/art/sample/tools/qicons_shots.py keywords    # batch 5b: gear keyword chips
    uv run python docs/art/sample/tools/qicons_shots.py --audit keywords # batch 5b audit table
    uv run python docs/art/sample/tools/qicons_shots.py true1x keywords  # batch 5b true 1x
    uv run python docs/art/sample/tools/qicons_shots.py --zoom 3 --out <dir> status   # magnified
    uv run python docs/art/sample/tools/qicons_shots.py true1x      # true 1x sheets, all five pages
    uv run python docs/art/sample/tools/qicons_shots.py true1x weapons skills  # only these pages
    uv run python docs/art/sample/tools/qicons_shots.py --page q-icons-weapons.html \
        --query "part=b" --out <dir>                                # one ad-hoc shot

The page reports its own height in <html data-h>, so each shot is taken twice: once to
read the height, once at that window size.

"true1x" shoots the ?part=true1x sheets into docs/art/shots/qicons/true1x/: every icon at its
smallest size drawn at true 1x (canvas size == CSS px, the pixels a 100%-zoom screen shows) and
blown up nearest-neighbour, next to the current icon and the 2x-internal render the other
review sheets show. Pages: weapons | armor | skills | parts | status | keywords | style.
Shots are cut into
segments no taller than 1100px; they are not part of the default "every shot" run.
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
STATUS_PAGE = "q-icons-status.html"
KEYWORD_PAGE = "q-icons-keywords.html"
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
# True-1x fix (2026-11-12): the looks the true-1x re-check named, for fixed-path review close-ups.
T1X_WEAPONS = [
    "whip/leather",
    "whip/chain",
    "whip/bladed",
    "dual_pistol/revolver",
    "dual_dagger/kris",
    "dual_pistol/flintlock",
]
T1X_SKILLS = [
    "化身為龍",
    "化身為巨人",
    "化身為狼人",
    "化身為熊",
    "化身為貓",
    "化身為惡魔",
    "產下幼蜥",
    "召喚守護靈",
    "雙牙",
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
    # true-1x fix: the badge/gear looks that changed, 2x internal resolution next to true 1x.
    (
        "weapons-t1x",
        WEAPON_PAGE,
        "part=review&only=" + ",".join(T1X_WEAPONS),
        "closeup/qicons/weapons/t1x-fix.png",
        1,
    ),
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
    # true-1x fix: the looks the true-1x re-check named, current 40 next to Q 40/28/24.
    (
        "skills-t1x",
        SKILL_PAGE,
        "part=review&only=" + ",".join(T1X_SKILLS),
        "closeup/qicons/skills/t1x-fix.png",
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
    "status1",
    "status2",
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
    ("near&nfrom=9&nn=3", "near-4"),
]
# Batch 4 v2: the glyphs whose drawing changed in v2, as review sheets (2x row + true 1x row).
PARTS_V2 = {
    "v2-redraw-1": "skeleton:strike,skeleton:area,skeleton:trap,skeleton:displace,effect:dash,"
    "effect:charge_through,effect:dispel,effect:raise_terrain,effect:zone,effect:create_obstacle,"
    "effect:place_trap,surface:oil,status:root,status:stun,status:silenced",
    "v2-redraw-2": "status:vulnerable,condition:height_advantage,condition:from_behind,"
    "condition:target_isolated,"
    "condition:cast_tag_this_turn,condition:wielding_weapon,trigger:on_hit,trigger:on_kill,"
    "trigger:on_cast_tag,trigger:hit_by_spell,trigger:hit_by_attack,trigger:hit_by_melee,"
    "link:on_kill,change:grant_pierce,card:pin",
    "v2-shape": "shape:single,shape:self,shape:ground_tile,shape:square3,shape:cross,"
    "shape:ring,shape:cone,shape:line,shape:chain,shape:allies_in_radius,shape:unit_then_tile,"
    "shape:object_then_tile,shape:unit_pair",
    "v2-change": "change:cooldown_delta,change:ap_delta,change:form_upkeep_permille,"
    "change:form_entry_permille,change:damage_permille",
    "v2-status-new": "status:guarded,status:infused_fire,status:infused_holy,"
    "status:shielded_charged,status:empowered,status:stoneskin,status:regenerating,"
    "status:overwatch,status:defending,status:stance_guard,status:stance_bulwark,"
    "status:stance_ironwall,status:stance_fury,status:stance_holy_1,status:stance_shadow_1",
}
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
    *[
        ("parts-v2", PARTS_PAGE, f"part=review&only={only}", f"closeup/qicons/parts/{name}.png", 1)
        for name, only in PARTS_V2.items()
    ],
    ("parts-asm", PARTS_PAGE, "part=asm&from=0&n=12", "shots/qicons/parts-asm-1.png", 1),
    ("parts-asm", PARTS_PAGE, "part=asm&from=12&n=12", "shots/qicons/parts-asm-2.png", 1),
    ("parts-scene", PARTS_PAGE, "part=scene", "shots/qicons/parts-scene.png", 1),
    ("parts-scene", PARTS_PAGE, "part=scene", "shots/qicons/parts-scene@2x.png", 2),
]

# Batch 5 (status icons, every status the game shows): the A tables double as close-ups.
# "status" names this batch; the style sample's status close-up is "style-status".
STATUS_GROUPS = ["ctrl", "debuff", "buff", "shield", "neutral", "stance", "element", "boss"]
# Batch 5 v2: review sheets (2x row + true 1x row) of what changed, and the look-alike rows
# the review asked to see side by side (warm/cold hexagons, the rock vs earth and shells).
STATUS_V2 = {
    "v2-changed": "stun,frozen,slow,root,taunted,feared,silenced,"
    "race_stonewall,stance_blaze,stance_frost,crystal_surge_2,armor_broken",
    "v2-near-hex": "stance_fury,stance_blaze,stance_flame,stance_fire_1,"
    "stance_guard,stance_frost,stance_glacier,stance_ice_1",
    "v2-near-rock": "race_stonewall,stance_earth_1,hard_shell,molten_shell,"
    "rift_collapse,crystal_surge,crystal_surge_2,armor_broken,vulnerable,stoneskin",
}
STATUS_SHOTS: list[Shot] = [
    *[
        (
            "status-a",
            STATUS_PAGE,
            f"part=a&group={group}",
            f"closeup/qicons/status/a-{group}.png",
            1,
        )
        for group in STATUS_GROUPS
    ],
    ("status-cls", STATUS_PAGE, "part=cls", "closeup/qicons/status/cls.png", 1),
    ("status-b", STATUS_PAGE, "part=b&group=all", "shots/qicons/status-b.png", 1),
    *[
        ("status-b", STATUS_PAGE, f"part=b&group=near&nfrom={start}&nn=4", f"shots/qicons/{out}", 1)
        for start, out in ((0, "status-near-1.png"), (4, "status-near-2.png"))
    ],
    ("status-scene", STATUS_PAGE, "part=scene", "shots/qicons/status-scene.png", 1),
    ("status-scene", STATUS_PAGE, "part=scene", "shots/qicons/status-scene@2x.png", 2),
    *[
        (
            "status-v2",
            STATUS_PAGE,
            f"part=review&only={only}",
            f"closeup/qicons/status/{name}.png",
            2,
        )
        for name, only in STATUS_V2.items()
    ],
]

# Batch 5b (keyword chips on gear icons): the summary tables, the six-way size/ring comparison
# that picked the chip, the current-vs-Q sheet and the collision sheets (four keywords a shot).
KEYWORD_LAB = ["ignite,wet,charged,frozen", "prone,collision,marked,high_ground"]
KEYWORD_LAB.append("concealed,summon,poisoned,form")
KEYWORD_SHOTS: list[Shot] = [
    ("keywords-a", KEYWORD_PAGE, "part=a", "shots/qicons/keywords-a48.png", 1),
    ("keywords-a", KEYWORD_PAGE, "part=a&px=32", "shots/qicons/keywords-a32.png", 1),
    ("keywords-pair", KEYWORD_PAGE, "part=pair", "shots/qicons/keywords-pair.png", 1),
    ("keywords-cur", KEYWORD_PAGE, "part=cur&kn=6", "shots/qicons/keywords-cur-1.png", 1),
    ("keywords-cur", KEYWORD_PAGE, "part=cur&kfrom=6&kn=6", "shots/qicons/keywords-cur-2.png", 1),
    *[
        (
            "keywords-lab",
            KEYWORD_PAGE,
            f"part=lab&kw={kws}",
            f"closeup/qicons/keywords/lab-{n}.png",
            1,
        )
        for n, kws in enumerate(KEYWORD_LAB, start=1)
    ],
    *[
        (
            "keywords-cmp",
            KEYWORD_PAGE,
            f"part=cmp&kfrom={start}&kn=4&row=0",
            f"closeup/qicons/keywords/cmp-{start // 4 + 1}.png",
            1,
        )
        for start in (0, 4, 8)
    ],
    ("keywords-row", KEYWORD_PAGE, "part=cmp&kn=0", "closeup/qicons/keywords/row.png", 1),
]

# True 1x sheets: (page key, file prefix, page, group query, cells per shot). The page reports
# how many cells the group has in <html data-t1total>; shots are numbered -01, -02, ...
TRUE1X_MAX_HEIGHT = 1100
TRUE1X: list[tuple[str, str, str, str, int]] = [
    ("weapons", "weapons-badge20", WEAPON_PAGE, "group=badge", 21),
    ("weapons", "weapons-gear32", WEAPON_PAGE, "group=gear", 8),
    ("weapons", "weapons-rarity32", WEAPON_PAGE, "group=rar", 10),
    ("armor", "armor-gear32", ARMOR_PAGE, "group=all", 8),
    ("armor", "armor-dark32", ARMOR_PAGE, "group=dark", 8),
    ("skills", "skills-28", SKILL_PAGE, "group=28", 21),
    ("skills", "skills-24", SKILL_PAGE, "group=24", 21),
    ("parts", "parts-chip18", PARTS_PAGE, "group=chip", 21),
    ("parts", "parts-corner56", PARTS_PAGE, "group=corner", 21),
    ("parts", "parts-icon56", PARTS_PAGE, "group=asm", 10),
    ("status", "status-card20", STATUS_PAGE, "group=card", 28),
    ("status", "status-head11", STATUS_PAGE, "group=head", 32),
    ("keywords", "keywords-gear32", KEYWORD_PAGE, "group=g32", 15),
    ("keywords", "keywords-bag42", KEYWORD_PAGE, "group=g42", 12),
    ("keywords", "keywords-pair", KEYWORD_PAGE, "group=pair", 10),
    ("keywords", "keywords-all32", KEYWORD_PAGE, "group=all", 18),
    ("keywords", "keywords-all42", KEYWORD_PAGE, "group=all42", 15),
    ("style", "style-weapon20", STYLE_PAGE, "group=weapon", 99),
    ("style", "style-weapon-gear32", STYLE_PAGE, "group=wgear", 99),
    ("style", "style-skill24", STYLE_PAGE, "group=skill", 99),
    ("style", "style-item28", STYLE_PAGE, "group=item", 99),
    ("style", "style-status11", STYLE_PAGE, "group=status", 99),
    ("style", "style-hud", STYLE_PAGE, "group=hud", 99),
    ("style", "style-event", STYLE_PAGE, "group=event", 99),
]


def url(page: str, query: str) -> str:
    return f"{(ART / 'sample' / page).as_uri()}?{query}"


def dump_dom(page: str, query: str) -> str:
    cmd = [*BASE, "--window-size=1280,900", "--dump-dom", url(page, query)]
    done = subprocess.run(cmd, capture_output=True, timeout=240, check=False)
    return done.stdout.decode("utf-8", "replace")


def shoot(page: str, query: str, out: Path, scale: float, max_height: int = 0) -> bool:
    found = re.search(r'data-h="(\d+)"', dump_dom(page, query))
    if not found:
        print(f"{query}: page did not finish (no data-h)")
        return False
    height = int(found.group(1))
    if max_height and height > max_height:
        print(f"{query}: {height}px is taller than {max_height}px, use fewer cells per shot")
        return False
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
    console = [
        ln
        for ln in done.stderr.decode("utf-8", "replace").splitlines()
        if "CONSOLE" in ln and "willReadFrequently" not in ln  # a perf hint, not an error
    ]
    print(f"{query}: {height}px -> {out.name}" + (f"  console: {console[:5]}" if console else ""))
    return not console


def shoot_true1x(pages: set[str], out_dir: Path) -> bool:
    """Shoot the ?part=true1x sheets of the named pages (all five when none is named)."""
    ok = True
    for key, prefix, page, group, per in TRUE1X:
        if pages and key not in pages:
            continue
        found = re.search(r'data-t1total="(\d+)"', dump_dom(page, f"part=true1x&{group}&n=1"))
        if not found:
            print(f"true1x {prefix}: page did not finish (no data-t1total)")
            ok = False
            continue
        total = int(found.group(1))
        for stale in out_dir.glob(f"{prefix}-[0-9][0-9].png"):
            stale.unlink()  # a group that shrank would otherwise keep its old last segments
        for index, start in enumerate(range(0, total, per), start=1):
            query = f"part=true1x&{group}&from={start}&n={per}"
            target = out_dir / f"{prefix}-{index:02d}.png"
            ok = shoot(page, query, target, 1, TRUE1X_MAX_HEIGHT) and ok
    return ok


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
        else STATUS_PAGE
        if "status" in args.parts
        else KEYWORD_PAGE
        if "keywords" in args.parts
        else WEAPON_PAGE
    )
    if "true1x" in args.parts:
        out_dir = args.out or ART / "shots" / "qicons" / "true1x"
        return 0 if shoot_true1x(set(args.parts) - {"true1x"}, out_dir) else 1
    if args.hash:
        # "var" (batch 2 only): fingerprints of every material/dye/keyword variant.
        variants = "var" in args.parts and batch_page in (ARMOR_PAGE, WEAPON_PAGE)
        return 0 if audit(batch_page, "hash&sub=var" if variants else "hash") else 1
    if args.audit:
        batched = bool(
            {"armor", "weapons", "skills", "parts", "status", "keywords"} & set(args.parts)
        )
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
        STATUS_PAGE: "status" in wanted,
        KEYWORD_PAGE: "keywords" in wanted,
    }
    shots = [
        *SHOTS,
        *WEAPON_SHOTS,
        *ARMOR_SHOTS,
        *SKILL_SHOTS,
        *PARTS_SHOTS,
        *STATUS_SHOTS,
        *KEYWORD_SHOTS,
    ]
    for name, page, query, rel, scale in shots:
        # "status" is batch 5; the style sample's status close-up is asked for as "style-status".
        style_name = f"style-{name}" if page == STYLE_PAGE else name
        if page == STYLE_PAGE and name == "status":
            hit = style_name in wanted
        else:
            hit = name in wanted or style_name in wanted
        if wanted and not hit and not whole.get(page, False):
            continue
        ok = shoot(page, query, ART / rel, scale) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
