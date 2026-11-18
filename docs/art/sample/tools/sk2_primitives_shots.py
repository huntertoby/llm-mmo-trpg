"""Re-shoot the SK-2 primitive art samples (docs/art/SK-2原語-美術.md).

Usage (from the repo root):
    uv run python -I <this script> <chrome tmp> [name ...] [--out <dir>]
    uv run python -I <this script> <tmp> --query "part=anim&case=hook" --out <dir>
    uv run python -I <this script> <tmp> --audit

Same mechanism as rg_marks_shots.py (imported; PAGE / SHOTS swapped): each part of
sk2-primitives.html draws one sheet into a canvas, the data URL goes into
<textarea id="out">, headless Chrome --dump-dom reads it. True-1x and nearest-neighbour
sheets are PNG, the rest JPEG quality 80. No remote-debugging port; always --mute-audio.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rg_marks_shots as r

r.PAGE = r.ART / "sample" / "sk2-primitives.html"
D = "shots/sk2-primitives/"
r.SHOTS = [
    ("icons", "part=icons", D + "1-icons-v2.png"),
    ("icons-t1", "part=icons-t1", D + "2-icons-true1x-v2.png"),
    ("near", "part=near", D + "3-icons-near-v2.png"),
    ("full96", "part=full96", D + "4-icons-full96-v2.png"),
    ("absorb", "part=anim&case=absorb", D + "5-anim-absorb-v2.jpg"),
    ("contagion", "part=anim&case=contagion", D + "6-anim-contagion-v2.jpg"),
    ("hook", "part=anim&case=hook", D + "7-anim-hook-v2.jpg"),
    ("hook_lava", "part=anim&case=hook_lava", D + "8-anim-hook-lava-v2.jpg"),
    ("hook_giant", "part=anim&case=hook_giant", D + "9-anim-hook-giant-v2.jpg"),
    ("anim-t1", "part=anim-t1", D + "10-anim-true1x-v2.png"),
    ("status", "part=status", D + "11-status-spread-v2.png"),
    ("status-t1", "part=status-t1", D + "12-status-spread-true1x-v2.png"),
    ("field-1600", "part=field&w=1600", D + "13-field-1600-v2.png"),
    ("field-800", "part=field&w=800", D + "14-field-800-v2.png"),
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
