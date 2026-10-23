"""下載 Noto Sans TC（400、700）woff2 與 OFL 授權檔到 client/src/assets/fonts/noto-sans-tc/。

只允許三個來源：fonts.googleapis.com（CSS2）、fonts.gstatic.com（woff2）、
raw.githubusercontent.com 的 google/fonts OFL.txt。可重跑；產生 noto-sans-tc.css。
"""

from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com", "raw.githubusercontent.com"}
CSS_URL = "https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap"
OFL_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/OFL.txt"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
OUT_DIR = (
    Path(__file__).resolve().parent.parent / "client" / "src" / "assets" / "fonts" / "noto-sans-tc"
)


def fetch(url: str) -> bytes:
    host = urllib.parse.urlparse(url).hostname
    if host not in ALLOWED_HOSTS or not url.startswith("https://"):
        raise ValueError(f"不允許的來源：{url}")
    if host == "raw.githubusercontent.com" and url != OFL_URL:
        raise ValueError(f"不允許的來源：{url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data: bytes = resp.read()
    return data


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    css = fetch(CSS_URL).decode("utf-8")
    blocks = re.findall(r"@font-face\s*\{(.*?)\}", css, flags=re.S)
    out_css: list[str] = []
    files: list[tuple[str, int]] = []
    for idx, body in enumerate(blocks):
        weight = re.search(r"font-weight:\s*(\d+)", body)
        url = re.search(r"url\((https://[^)]+)\)", body)
        rng = re.search(r"unicode-range:\s*([^;]+);", body)
        if weight is None or url is None or rng is None:
            raise ValueError(f"無法解析 @font-face：{body}")
        name = f"noto-sans-tc-{weight.group(1)}-{idx:03d}.woff2"
        data = fetch(url.group(1))
        (OUT_DIR / name).write_bytes(data)
        files.append((name, len(data)))
        out_css.append(
            "@font-face {\n"
            '  font-family: "Noto Sans TC";\n'
            "  font-style: normal;\n"
            f"  font-weight: {weight.group(1)};\n"
            "  font-display: swap;\n"
            f'  src: url("./{name}") format("woff2");\n'
            f"  unicode-range: {rng.group(1).strip()};\n"
            "}\n"
        )
    (OUT_DIR / "noto-sans-tc.css").write_text(
        "/* scripts/fetch_font.py 產生；Noto Sans TC，OFL 1.1（見 OFL.txt）。 */\n"
        + "\n".join(out_css),
        encoding="utf-8",
    )
    (OUT_DIR / "OFL.txt").write_bytes(fetch(OFL_URL))
    total = sum(s for _, s in files)
    for name, size in files:
        print(f"{name}\t{size}")
    print(f"woff2 檔數：{len(files)}；總大小：{total} bytes（{total / 1024 / 1024:.2f} MiB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
