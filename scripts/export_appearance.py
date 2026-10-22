"""把裝備外觀清單寫到 ``client/src/render/gearAppearance.json``（Phase 3G-G5a）。

用法::

    uv run python scripts/export_appearance.py

清單的真相來源是 ``content/equipment/appearance.yaml``；``tests/content/test_appearance.py`` 檢查
JSON 沒有過期。
"""

from __future__ import annotations

import sys
from pathlib import Path

from trpg.content.appearance import AppearanceTable, appearance_json
from trpg.content.loader import load_content_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "content" / "equipment" / "appearance.yaml"
TARGET = PROJECT_ROOT / "client" / "src" / "render" / "gearAppearance.json"


def main() -> int:
    table = load_content_file(SOURCE, AppearanceTable)
    TARGET.write_text(appearance_json(table), encoding="utf-8", newline="\n")
    print(f"已寫入 {TARGET.relative_to(PROJECT_ROOT).as_posix()}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
