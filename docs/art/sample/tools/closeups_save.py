"""把 closeups.html 的 --dump-dom 輸出存成一張張 PNG（美術 PM 第 7 版，3 倍特寫）。

用法：uv run --no-project python -I closeups_save.py <dump.html> <輸出資料夾>
"""

import base64
import html
import pathlib
import re
import sys

dump, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
text = dump.read_text(encoding="utf-8")
n = 0
for m in re.finditer(r'<pre data-file="([^"]+)">data:image/png;base64,([^<]+)</pre>', text):
    (out / f"{html.unescape(m.group(1))}.png").write_bytes(base64.b64decode(m.group(2)))
    n += 1
print(n)
