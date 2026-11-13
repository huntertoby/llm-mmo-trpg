"""Re-shoot the duel art for non-sword main hands (docs/art/RG樣張.md section 9.9).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/rg_duel_weapons_shots.py <chrome tmp> [name ...]
    uv run python -I docs/art/sample/tools/rg_duel_weapons_shots.py <chrome tmp> --audit

Borrows rg_units_shots.py (headless Chrome --dump-dom, data URL in #out, no
remote-debugging port, --mute-audio, ?mute=1); only the page and the list differ.
--audit prints the sword-version fingerprints (four duels x res 1/2) from <pre id="audit">.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rg_units_shots as r

r.PAGE = r.ART / "sample" / "rg-duel-weapons.html"
r.DIALOGS = []
r.SHOTS = [
    # duel-weapons-0-before.jpg (part=now) was shot before 9.9 changed rgUnits.js; re-shooting
    # it now would draw the new version, so it is not in the list.
    # v2 (review D-1..D-3) only changed the crossing: 1-sil is not re-shot; v1 files are kept.
    ("sil", "part=sil", "shots/rg-units/duel-weapons-1-sil.png"),
    ("cross", "part=cross", "shots/rg-units/duel-weapons-2-cross-v2.png"),
    ("duel", "part=duel", "shots/rg-units/duel-weapons-3-duel-v2.png"),
    ("duel-x4", "part=x4", "shots/rg-units/duel-weapons-4-duel-x4-v2.png"),
    ("small", "part=small", "shots/rg-units/duel-weapons-5-small-259-v2.png"),
    ("contact", "part=contact", "shots/rg-units/duel-weapons-6-contact-v2.png"),
]
AUDIT_ARGC = 2
AUDIT_RE = re.compile(r'<pre id="audit">([^<]*)</pre>')


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if len(argv) >= AUDIT_ARGC and argv[1] == "--audit":
        found = AUDIT_RE.search(r.dump(Path(argv[0]), "part=audit"))
        print(html.unescape(found.group(1)) if found else "no audit")
        return 0 if found else 1
    return r.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
