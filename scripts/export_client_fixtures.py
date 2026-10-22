"""把前端測試用的內容快照寫到 ``client/src/``（Phase 3E-2e）。

用法::

    uv run python scripts/export_client_fixtures.py

- ``client/src/battle/fixtures/glossary.json``：``/api/glossary`` 的回應（vitest 共用設定載入）。
- ``client/src/render/fixtures/unitDolls.json``：單位範本 ID 到紙娃娃外觀的對照（紙娃娃測試用）。

真相來源是 ``content/``；``tests/api/test_client_fixtures.py`` 檢查兩個檔沒有過期。
"""

from __future__ import annotations

import sys
from pathlib import Path

from trpg.api.fixtures import glossary_fixture_text, unit_dolls_fixture_text
from trpg.content.library import load_library

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = PROJECT_ROOT / "client" / "src" / "battle" / "fixtures" / "glossary.json"
UNIT_DOLLS = PROJECT_ROOT / "client" / "src" / "render" / "fixtures" / "unitDolls.json"


def main() -> int:
    library = load_library()
    GLOSSARY.write_text(glossary_fixture_text(library), encoding="utf-8", newline="\n")
    UNIT_DOLLS.write_text(unit_dolls_fixture_text(library), encoding="utf-8", newline="\n")
    for path in (GLOSSARY, UNIT_DOLLS):
        print(f"已寫入 {path.relative_to(PROJECT_ROOT).as_posix()}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
