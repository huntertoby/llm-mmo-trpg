"""Re-shoot the 3x3 Ashen Heart samples (GB art A1 + A2; docs/art/GB巨型頭目-美術.md).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/giant_boss_shots.py <chrome tmp> [name ...] [--out <dir>]
    uv run python -I docs/art/sample/tools/giant_boss_shots.py <tmp> --query part=probe --out <dir>
    uv run python -I docs/art/sample/tools/giant_boss_shots.py <tmp> --anchor

- Each part of giant-boss.html draws one sheet into a canvas and puts its data URL
  (PNG for true-1x / nearest-neighbour sheets, JPEG quality 80 otherwise) in
  <textarea id="out">; this script reads it with headless Chrome --dump-dom and writes
  the file, so pixels are exactly the canvas (no window size / DPR effects).
- No remote-debugging port is opened. Always --mute-audio; the URL carries ?mute=1.
- <chrome tmp> is your own scratch folder (the Chrome profile goes there).
- --anchor prints the measured bounding boxes (model px, relative to the anchor).
- --hash prints the A3 part-icon fingerprints (vent/seam/core x 20/16/12 px x res 1/2).
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
PAGE = ART / "sample" / "giant-boss.html"
DEST = "shots/giant-boss/"

# (name, query, output path relative to docs/art)
SHOTS = [
    ("sprites-1600", "part=sprites&w=1600", DEST + "1a-sprites-1600-t1.png"),
    ("sprites-1600-nn", "part=sprites&w=1600&g=nn", DEST + "1a2-sprites-1600-nn.png"),
    ("sprites-800", "part=sprites&w=800", DEST + "1b-sprites-800-t1.png"),
    ("big", "part=big", DEST + "1c-sprites-big.jpg"),
    ("anchor", "part=anchor", DEST + "1d-anchor.jpg"),
    ("shed", "part=shed", DEST + "1e-shed-1600-nn.png"),
    ("field-1600", "part=field&w=1600", DEST + "2a-field-1600-t1.png"),
    ("field-800", "part=field&w=800", DEST + "2b-field-800-t1.png"),
    ("field-1600-p3", "part=field&w=1600&p3=1", DEST + "2c-field-1600-p3-t1.png"),
    ("field-800-p3", "part=field&w=800&p3=1", DEST + "2d-field-800-p3-t1.png"),
    ("marks-1600", "part=marks&w=1600", DEST + "3a-marks-1600-t1.png"),
    ("marks-800", "part=marks&w=800", DEST + "3b-marks-800-t1.png"),
    ("marks-nn", "part=marks-nn", DEST + "3c-marks-nn.png"),
    ("seam-800", "part=seam-800", DEST + "3d-seam-800.png"),
    ("icons", "part=icons", DEST + "4a-icons.png"),
    ("icons-t1", "part=icons-t1", DEST + "4b-icons-t1.png"),
    ("icons-marks", "part=icons-marks", DEST + "4c-icons-marks.png"),
]

OUT_RE = re.compile(r'<textarea id="out">([^<]*)</textarea>')
ANCHOR_RE = re.compile(r'data-anchor="([^"]*)"')
HASH_RE = re.compile(r'data-hash="([^"]*)"')


def dump(tmp: Path, query: str) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--user-data-dir={tmp / 'chrome-prof-gb'}",
        "--virtual-time-budget=90000",
        "--window-size=1280,900",
        "--enable-logging=stderr",
        "--v=0",
        "--dump-dom",
        f"{PAGE.as_uri()}?{query}&mute=1",
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=900, check=False)
    errors = [
        ln
        for ln in done.stderr.decode("utf-8", "replace").splitlines()
        if "CONSOLE" in ln and "willReadFrequently" not in ln
    ]
    if errors:
        print(f"{query}: console {errors[:5]}")
    return done.stdout.decode("utf-8", "replace")


def save(found: re.Match[str] | None, dest: Path, name: str) -> bool:
    if not found or "," not in found.group(1):
        print(f"{name}: page did not finish (no #out)")
        return False
    data = base64.b64decode(found.group(1).split(",", 1)[1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"{name}: {len(data) // 1024} KB -> {dest}")
    return True


def anchor(tmp: Path) -> int:
    html = dump(tmp, "part=anchor")
    found = ANCHOR_RE.search(html)
    if not found:
        print("anchor: page did not finish")
        return 1
    data = json.loads(found.group(1).replace("&quot;", '"'))
    for row in data["rows"]:
        print(row["k"], "body", row["body"], "all", row["all"])
    print("top", data["top"], "side", data["side"], "bottom", data["bot"])
    print("S1600", data["S1600"], "S800", data["S800"])
    return 0


def icon_hash(tmp: Path) -> int:
    html = dump(tmp, "part=icons")
    found = HASH_RE.search(html)
    if not found:
        print("hash: page did not finish")
        return 1
    for key, val in json.loads(found.group(1).replace("&quot;", '"')).items():
        print(key, val)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    tmp = Path(argv[0])
    rest = argv[1:]
    if "--anchor" in rest:
        return anchor(tmp)
    if "--hash" in rest:
        return icon_hash(tmp)
    out_dir = ART
    if "--out" in rest:
        i = rest.index("--out")
        out_dir = Path(rest[i + 1])
        rest = rest[:i] + rest[i + 2 :]
    if "--query" in rest:  # ad-hoc: <out>/probe.jpg|png
        i = rest.index("--query")
        query = rest[i + 1]
        ext = ".png" if "true1x" in query else ".jpg"
        ok = save(OUT_RE.search(dump(tmp, query)), out_dir / f"probe{ext}", "probe")
        return 0 if ok else 1
    names = set(rest)
    ok = True
    for name, query, rel in SHOTS:
        if names and name not in names:
            continue
        dest = out_dir / rel if out_dir == ART else out_dir / Path(rel).name
        ok = save(OUT_RE.search(dump(tmp, query)), dest, name) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
