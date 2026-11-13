"""Re-shoot the #163 player great-shield samples (docs/art/RG樣張.md section 10).

Usage (from the repo root):
    uv run python -I <this script> <chrome tmp> [name ...] [--out <dir>]
    uv run python -I <this script> <tmp> --audit          # print the self-check table
    uv run python -I <this script> <tmp> --query "part=materials&f=gold" --out <dir>

Borrows rg_units_shots.py (headless Chrome --dump-dom, canvas data URL from #out,
no remote-debugging port, --mute-audio, ?mute=1); only the page and the list differ.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rg_units_shots as r

r.PAGE = r.ART / "sample" / "rg-player-shield.html"
D = "shots/rg-player-shield/"
r.SHOTS = [
    ("dolls", "part=dolls", D + "1-hero-dolls.png"),
    ("lineup", "part=lineup", D + "2-lineup.png"),
    ("mat-sect", "part=materials&f=sect_great", D + "3-materials-sect.png"),
    ("mat-shell", "part=materials&f=molten_shell", D + "4-materials-shell.png"),
    ("icons", "part=icons", D + "5-icons.png"),
    ("t1", "part=t1", D + "6-icons-true1x.png"),
    ("bag", "part=bag", D + "7-bag.png"),
    ("scene-1600", "part=scene&w=1600", D + "8-scene-1600.png"),
    ("scene-800", "part=scene&w=800", D + "9-scene-800.png"),
    ("parts", "part=parts", D + "10-parts.jpg"),
]
r.DIALOGS = []

AUDIT_RE = re.compile(r'<pre id="audit">([^<]*)</pre>')


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if argv[1:2] == ["--audit"]:
        found = AUDIT_RE.search(r.dump(Path(argv[0]), "part=audit"))
        print(html.unescape(found.group(1)) if found else "no audit")
        return 0 if found else 1
    return r.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
