"""把目前 API 的 OpenAPI 寫到 ``client/openapi.json``（Phase 3-3）。

用法::

    uv run python scripts/export_openapi.py
    corepack pnpm -C client gen:api      # 由 openapi.json 產生 client/src/api/schema.d.ts

``tests/api/test_openapi_snapshot.py`` 檢查兩者一致（API 改了而沒重新產生就失敗）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from trpg.api.app import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = PROJECT_ROOT / "client" / "openapi.json"


def openapi_text(spec: dict[str, Any]) -> str:
    """固定格式（縮排 2、保留中文、結尾換行），讓 git diff 穩定。"""
    return json.dumps(spec, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    spec = create_app().openapi()
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(openapi_text(spec), encoding="utf-8", newline="\n")
    print(f"已寫入 {OPENAPI_PATH.relative_to(PROJECT_ROOT).as_posix()}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
