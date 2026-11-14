"""Re-shoot the cooling well samples (docs/art/冷卻井-移植需求.md).

Usage (from the repo root):
    uv run python -I docs/art/sample/tools/cooling_well_shots.py <chrome tmp> [name ...]
    uv run python -I docs/art/sample/tools/cooling_well_shots.py <tmp> --query part=well --out <dir>

- Each part of cooling-well.html draws one sheet into a canvas and puts its data URL
  (PNG for true-1x sheets, JPEG quality 80 otherwise) in <textarea id="out">; this
  script reads it with headless Chrome --dump-dom and writes the file.
- No remote-debugging port is opened. Always --mute-audio; the URL carries ?mute=1.
- <chrome tmp> is your own scratch folder (the Chrome profile goes there).
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
PAGE = ART / "sample" / "cooling-well.html"
DEST = "shots/cooling-well/"

# (name, query, output path relative to docs/art)
SHOTS = [
    ("well", "part=well", DEST + "1-well-x4.jpg"),
    ("well-t1", "part=well-t1", DEST + "2-well-t1.png"),
    ("break-1600", "part=break&w=1600", DEST + "3-break-1600-t1.png"),
    ("break-800", "part=break&w=800", DEST + "4-break-800-t1.png"),
    ("pit-1600", "part=pit&w=1600", DEST + "5-pit-1600-t1.png"),
    ("pit-800", "part=pit&w=800", DEST + "6-pit-800-t1.png"),
    ("pit-broken", "part=pit-broken", DEST + "7-pit-broken-1600-t1.png"),
]

OUT_RE = re.compile(r'<textarea id="out">([^<]*)</textarea>')


def dump(tmp: Path, query: str) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        "--allow-file-access-from-files",
        f"--user-data-dir={tmp / 'chrome-prof-cw'}",
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


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    tmp = Path(argv[0])
    rest = argv[1:]
    out_dir = ART
    if "--out" in rest:
        i = rest.index("--out")
        out_dir = Path(rest[i + 1])
        rest = rest[:i] + rest[i + 2 :]
    if "--query" in rest:  # ad-hoc: <out>/probe.png
        i = rest.index("--query")
        ok = save(OUT_RE.search(dump(tmp, rest[i + 1])), out_dir / "probe.png", "probe")
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
