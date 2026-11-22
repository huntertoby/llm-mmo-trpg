"""Re-shoot the E4 trigger icon samples (docs/art/E4-觸發圖示-美術.md).

Usage (from the repo root):
    uv run python -I <this script> <chrome tmp> [name ...] [--out <dir>]
    uv run python -I <this script> <tmp> --query "part=trials" --out <dir>
    uv run python -I <this script> <tmp> --audit

Same mechanism as ap2_borrow_shots.py (rg_marks_shots imported; PAGE / SHOTS swapped):
each part of e4-triggers.html draws one sheet into a canvas (nearest-neighbour cells are
drawn with imageSmoothingEnabled=false), the data URL goes into <textarea id="out">,
headless Chrome --dump-dom reads it. All sheets are PNG. No remote-debugging port;
always --mute-audio.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rg_marks_shots as r

r.PAGE = r.ART / "sample" / "e4-triggers.html"
D = "shots/e4-triggers/"
r.SHOTS = [
    ("icons", "part=icons", D + "1-icons.png"),
    ("icons-t1", "part=icons-t1", D + "2-icons-true1x.png"),
    ("near", "part=near", D + "3-icons-near.png"),
    ("all", "part=all", D + "4-all-triggers.png"),
    ("full96", "part=full96", D + "5-icons-full96.png"),
    ("trials", "part=trials", D + "6-trials.png"),
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
