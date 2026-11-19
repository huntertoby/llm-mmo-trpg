"""Re-shoot the AP-2 borrow art samples (docs/art/AP-2-美術.md).

Usage (from the repo root):
    uv run python -I <this script> <chrome tmp> [name ...] [--out <dir>]
    uv run python -I <this script> <tmp> --query "part=anim-t1&w=800" --out <dir>
    uv run python -I <this script> <tmp> --audit

Same mechanism as sk3_mechanics_shots.py (rg_marks_shots imported; PAGE / SHOTS swapped):
each part of ap2-borrow.html draws one sheet into a canvas, the data URL goes into
<textarea id="out">, headless Chrome --dump-dom reads it. True-1x and nearest-neighbour
sheets are PNG, the rest JPEG quality 80. No remote-debugging port; always --mute-audio.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rg_marks_shots as r

r.PAGE = r.ART / "sample" / "ap2-borrow.html"
D = "shots/ap2-borrow/"
r.SHOTS = [
    ("icons", "part=icons", D + "1-icons.png"),
    ("icons-t1", "part=icons-t1", D + "2-icons-true1x.png"),
    ("near", "part=near", D + "3-icons-near.png"),
    ("full96", "part=full96", D + "4-icons-full96.png"),
    ("statusrow", "part=statusrow", D + "5-status-row-true1x.png"),
    ("anim", "part=anim", D + "6-anim-keyframes.jpg"),
    ("anim-1600", "part=anim-t1&w=1600", D + "7-anim-true1x-1600.png"),
    ("anim-800", "part=anim-t1&w=800", D + "8-anim-true1x-800.png"),
]

AUDIT_RE = re.compile(r'<pre id="audit">([^<]*)</pre>')


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if argv[1:2] == ["--audit"]:
        found = AUDIT_RE.search(r.dump(Path(argv[0]), "part=audit"))
        print(found.group(1) if found else "no audit table")
        return 0 if found else 1
    return r.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
