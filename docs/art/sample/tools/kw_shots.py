"""Shoot the KW-phase art samples (docs/art/KW樣張.md, page q-icons-kw.html).

Usage (from the repo root):
    uv run python docs/art/sample/tools/kw_shots.py            # every shot -> docs/art/shots/qicons-kw/
    uv run python docs/art/sample/tools/kw_shots.py cand hud   # only these
    uv run python docs/art/sample/tools/kw_shots.py --audit    # audit table (text)
    uv run python docs/art/sample/tools/kw_shots.py --hash     # fingerprints of the new art

Reuses qicons_shots.shoot()/audit() (headless Chrome, --mute-audio, file:// URL, no server,
no debugging port) with its own Chrome profile folder so another agent shooting at the same
time does not clash. Shots are taken at device scale 1, so the nearest-neighbour blow-ups in
the page are the true pixels; .jpg outputs are re-encoded at quality 80.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qicons_shots as q  # noqa: E402

PROFILE = Path(tempfile.gettempdir()) / "kw-shots-chrome-profile"
q.BASE = [a if not a.startswith("--user-data-dir=") else f"--user-data-dir={PROFILE}" for a in q.BASE]
PAGE = "q-icons-kw.html"
OUT = q.ART / "shots" / "qicons-kw"
# (name, query, file): true-1x / nearest-neighbour sheets are PNG, the rest JPEG 80.
SHOTS = [
    ("cand", "part=cand", "1-cand.png"),
    ("color", "part=color", "2-color.png"),
    ("near", "part=near", "3-near.png"),
    ("gear", "part=gear", "4-gear.png"),
    ("cond", "part=cond", "5-cond.png"),
    ("hud", "part=hud", "6-hud.png"),
    ("create", "part=create", "7-create.png"),
]


def main() -> int:
    args = sys.argv[1:]
    if "--audit" in args or "--hash" in args:
        return 0 if q.audit(PAGE, ("audit" if "--audit" in args else "hash") + "&mute=1") else 1
    ok = True
    for name, query, file in SHOTS:
        if args and name not in args:
            continue
        ok = q.shoot(PAGE, query + "&mute=1", OUT / file, 1) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
