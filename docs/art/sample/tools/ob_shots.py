"""重拍 #150／#147 三項樣張的整頁截圖與特寫（docs/art/OB與PR樣張.md 第 2 版）。

用法（在 repo 根目錄）：
    uv run python -I docs/art/sample/tools/ob_shots.py <Chrome 暫存資料夾> [檔名要含的字 ...]

- 每張先用無頭 Chrome 開 tools/ob-frame.html 讀 <html data-w data-h>，再用那個視窗大小截圖。
- 一律 --mute-audio；同一個暫存資料夾一次只跑一個 Chrome，所以是一張一張拍。
- 輸出：整頁在 docs/art/shots/ob/，特寫在 docs/art/closeup/ob/（檔名尾 -3x、-2x 是倍率）。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ART = Path(__file__).resolve().parents[2]
FRAME = (ART / "sample" / "tools" / "ob-frame.html").as_uri()

CLASS = "ob-range-class.html"
ENTRY = "ob-range-entry.html"
PRACTICE = "practice-battle.html"
GRAN = ENTRY + "?part=gran"
MASTER = ENTRY + "?part=master"


Shot = dict[str, object]


def full(name: str, src: str, w: int = 1280, h: int | str = "auto") -> Shot:
    """整頁截圖（shots/ob/）。"""
    return {
        "out": f"shots/ob/{name}.png",
        "src": src,
        "w": w,
        "h": h,
        "z": 1,
        "sel": "",
        "n": 0,
        "pad": 8,
        "c": "",
    }


def close(
    name: str,
    src: str,
    sel: str = "",
    z: float = 3,
    w: int = 1280,
    *,
    h: int | str = "auto",
    n: int = 0,
    pad: int = 8,
    c: str = "",
) -> Shot:
    """特寫（closeup/ob/）：sel＝只拍這個元件（第 n 個、留白 pad），或 c＝"x,y,w,h" 只拍一塊。"""
    return {
        "out": f"closeup/ob/{name}.png",
        "src": src,
        "w": w,
        "h": h,
        "z": z,
        "sel": sel,
        "n": n,
        "pad": pad,
        "c": c,
    }


SHOTS = [
    # ---- ① 選大類 ----
    full("class-1280-none", CLASS + "?state=none"),
    full("class-1280-hover", CLASS + "?state=hover"),
    full("class-1280-selected", CLASS + "?state=selected"),
    full("class-1280-rack-open", CLASS + "?state=selected&rack=open"),
    full("class-390-none", CLASS + "?state=none", 390),
    full("class-390-selected", CLASS + "?state=selected", 390),
    full("class-390-selected-viewport", CLASS + "?state=selected", 390, 844),
    full("class-390-rack-open", CLASS + "?state=selected&rack=open", 390),
    close("class-card-none-2x", CLASS + "?state=none", ".ob-class-card", 2),
    close("class-card-hover-2x", CLASS + "?state=hover", ".ob-class-card", 2),
    close("class-card-selected-2x", CLASS + "?state=selected", ".ob-class-card", 2, n=1),
    close("class-cards-hover-row-1x", CLASS + "?state=hover", ".ob-class-grid", 1),
    close("class-confirm-disabled-3x", CLASS + "?state=none", ".ob-confirm-panel", 2),
    close("class-confirm-enabled-3x", CLASS + "?state=selected", ".ob-confirm-panel", 2),
    close(
        "class-doll-melee-3x", CLASS + "?state=none", ".ob-class-card .range-preview-slot", 3, n=0
    ),
    close(
        "class-doll-ranged-3x", CLASS + "?state=none", ".ob-class-card .range-preview-slot", 3, n=1
    ),
    close(
        "class-doll-focus-3x", CLASS + "?state=none", ".ob-class-card .range-preview-slot", 3, n=2
    ),
    close("class-keeper-3x", CLASS + "?state=selected", ".range-keeper", 2),
    close("class-kit-melee-3x", CLASS + "?state=none", ".ob-kit", 3, n=0),
    close("class-kit-ranged-3x", CLASS + "?state=none", ".ob-kit", 3, n=1),
    close("class-kit-focus-3x", CLASS + "?state=none", ".ob-kit", 3, n=2),
    close("class-rack-closed-3x", CLASS + "?state=selected", ".ob-rack-panel", 2),
    close("class-rack-open-2x", CLASS + "?state=selected&rack=open", ".ob-rack-panel", 2),
    close("class-390-card-selected-3x", CLASS + "?state=selected", ".ob-class-card", 3, 390, n=1),
    close("class-390-confirm-3x", CLASS + "?state=selected", ".ob-confirm-panel", 3, 390),
    close("class-390-kit-cost-3x", CLASS + "?state=none", ".ob-kit", 3, 390, n=0),
    close("class-390-rack-open-3x", CLASS + "?state=selected&rack=open", ".ob-rack-panel", 3, 390),
    # ---- ② 工坊師傅選單 ----
    full("entry-master-1280-normal", MASTER + "&state=normal", 1280, 720),
    full("entry-master-1280-hover", MASTER + "&state=hover", 1280, 720),
    full("entry-master-390-normal", MASTER + "&state=normal", 390, 844),
    full("entry-master-390-hover", MASTER + "&state=hover", 390, 844),
    close("entry-master-panel-normal-3x", MASTER + "&state=normal", ".ob-master-panel", 3, h=720),
    close("entry-master-panel-hover-3x", MASTER + "&state=hover", ".ob-master-panel", 3, h=720),
    close("entry-master-menu-icons-4x", MASTER + "&state=normal", ".ob-menu", 4, h=720, pad=4),
    close("entry-master-people-3x", MASTER + "&state=normal", z=3, h=720, c="450,380,260,130"),
    close("entry-master-dummies-2x", MASTER + "&state=normal", z=2, h=720, c="680,330,440,350"),
    close("entry-master-pool-4x", MASTER + "&state=normal", z=4, h=720, c="950,340,160,160"),
    close("entry-master-racks-2x", MASTER + "&state=normal", z=2, h=720, c="0,120,280,570"),
    # ---- ② 葛蘭「正式選定」（整頁） ----
    full("entry-gran-1280", GRAN + "&sel=mix"),
    full("entry-gran-1280-one", GRAN + "&sel=one"),
    full("entry-gran-390", GRAN + "&sel=mix", 390),
    full("entry-gran-390-viewport", GRAN + "&sel=mix", 390, 844),
    close("entry-gran-head-3x", GRAN, ".range-keeper", 2),
    close("entry-gran-preview-3x", GRAN, ".range-preview", 3),
    close("entry-gran-racks-3x", GRAN, ".range-racks", 3),
    close("entry-gran-keywords-3x", GRAN, ".range-keywords", 3),
    close("entry-gran-try-3x", GRAN, ".range-weapon-card", 3, pad=30),
    close("entry-gran-actions-3x", GRAN, ".entry-actions", 3),
    close("entry-gran-kw-states-3x", GRAN + "&sel=one", ".range-keyword-list", 3),
    close("entry-gran-kw-rec-sel-3x", GRAN + "&sel=mix", '[data-state="rec-sel"]', 3),
    close("entry-gran-kw-rec-3x", GRAN + "&sel=one", '[data-state="rec"]', 3),
    close("entry-gran-kw-sel-3x", GRAN + "&sel=one", '[data-state="plain-sel"]', 3, pad=24),
    close("entry-gran-kw-plain-3x", GRAN + "&sel=one", '[data-state="plain"]', 3),
    close("entry-gran-try-normal-4x", GRAN, ".range-weapon-card .range-try", 4, pad=10),
    close(
        "entry-gran-try-hover-4x", GRAN + "&hover=try", ".range-weapon-card .range-try", 4, pad=10
    ),
    close("entry-gran-try-off-4x", GRAN + "&off=try", ".range-weapon-card .range-try", 4, pad=10),
    close("entry-gran-demo-normal-4x", GRAN + "&sel=one", ".range-demo", 4, pad=10, n=2),
    close("entry-gran-demo-hover-4x", GRAN + "&sel=one&hover=demo", ".range-demo", 4, pad=10),
    close("entry-gran-demo-off-4x", GRAN + "&sel=one&off=kw", '[data-state$="-off"]', 4, pad=6),
    close("entry-gran-390-bar-3x", GRAN, ".ob-choose-bar", 3, 390, pad=16),
    close("entry-gran-390-racks-3x", GRAN, ".range-racks", 3, 390),
    close("entry-gran-390-preview-3x", GRAN, ".range-preview", 3, 390),
    # ---- ③ 測試模式戰鬥版面 ----
    full("practice-1280", PRACTICE + "?mode=practice", 1280, 720),
    full("practice-1280-move", PRACTICE + "?mode=practice&act=move", 1280, 720),
    full("practice-1280-current", PRACTICE + "?mode=current", 1280, 720),
    full("practice-390", PRACTICE + "?mode=practice", 390, "auto"),
    full("practice-390-move", PRACTICE + "?mode=practice&act=move", 390, "auto"),
    full("practice-compare", PRACTICE + "?view=compare", 1600),
    close("practice-board-2x", PRACTICE + "?mode=practice", "canvas.ob-board", 2, h=720, pad=0),
    close(
        "practice-board-dummies-3x", PRACTICE + "?mode=practice", z=3, h=720, c="620,150,330,340"
    ),
    close("practice-board-hero-3x", PRACTICE + "?mode=practice", z=3, h=720, c="410,270,160,120"),
    close("practice-pool-4x", PRACTICE + "?mode=practice", z=4, h=720, c="740,275,180,170"),
    close("practice-bottom-3x", PRACTICE + "?mode=practice", ".battle-bottom", 3, h=720),
    close("practice-topbar-3x", PRACTICE + "?mode=practice", ".bhud-top", 3, h=720),
    close("practice-status-3x", PRACTICE + "?mode=practice", ".bhud-right", 3, h=720),
    close("practice-hero-preview-3x", PRACTICE + "?mode=practice", ".bhud-left", 3, h=720),
    close("practice-log-zoom-2x", PRACTICE + "?mode=practice", z=2, h=720, c="0,440,1280,130"),
    close(
        "practice-move-board-2x",
        PRACTICE + "?mode=practice&act=move",
        "canvas.ob-board",
        2,
        h=720,
        pad=0,
    ),
    close(
        "practice-move-bottom-3x", PRACTICE + "?mode=practice&act=move", ".battle-bottom", 3, h=720
    ),
    close("practice-current-top-3x", PRACTICE + "?mode=current", ".bhud-top", 3, h=720),
    close("practice-current-bottom-3x", PRACTICE + "?mode=current", ".battle-bottom", 3, h=720),
    close("practice-390-top-3x", PRACTICE + "?mode=practice", z=3, w=390, c="0,0,390,236"),
    close("practice-390-board-3x", PRACTICE + "?mode=practice", ".ob-phone-board", 3, 390, pad=0),
    close("practice-390-bottom-3x", PRACTICE + "?mode=practice", z=3, w=390, c="0,560,390,360"),
]


def frame_url(s: Shot) -> str:
    q = f"?src={quote(str(s['src']), safe='')}&w={s['w']}&h={s['h']}&z={s['z']}"
    if s["sel"]:
        q += f"&sel={quote(str(s['sel']), safe='')}&n={s['n']}&pad={s['pad']}"
    if s["c"]:
        q += f"&c={s['c']}"
    return FRAME + q


def run(profile: str, s: Shot) -> str:
    base = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--mute-audio",
        "--no-first-run",
        f"--user-data-dir={profile}",
        "--allow-file-access-from-files",
        "--hide-scrollbars",
        "--virtual-time-budget=12000",
    ]
    url = frame_url(s)
    dom = subprocess.run(
        [*base, "--window-size=1600,1200", "--dump-dom", url],
        capture_output=True,
        timeout=120,
        check=False,
    ).stdout.decode("utf-8", "replace")
    m = re.search(r'data-w="(\d+)" data-h="(\d+)"', dom)
    if m is None:
        return f"FAIL（讀不到大小） {s['out']}"
    w, h = int(m.group(1)), int(m.group(2))
    out = ART / str(s["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [*base, f"--window-size={w},{h}", f"--screenshot={out}", url],
        capture_output=True,
        timeout=120,
        check=False,
    )
    return f"{w}x{h} {s['out']}"


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__)
        return 2
    profile, keys = sys.argv[1], sys.argv[2:]
    todo = [s for s in SHOTS if not keys or any(k in str(s["out"]) for k in keys)]
    bad = 0
    for s in todo:
        line = run(profile, s)
        bad += line.startswith("FAIL")
        print(line, flush=True)
    print(f"拍了 {len(todo) - bad}／{len(todo)} 張")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
