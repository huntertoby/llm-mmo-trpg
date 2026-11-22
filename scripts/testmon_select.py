"""試用 testmon（TS-2）：先只收集、不跑，算出這次 testmon 會選幾個測試、略過幾個。

``scripts/check.py --testmon`` 在「只跑後端」時呼叫這支，結果印在開頭那一行。用法::

    uv run python scripts/testmon_select.py      # 印一行 JSON：{"selected": …, "skipped": …, …}

做法：在同一個行程裡跑 ``pytest --collect-only -n 0 --testmon-forceselect --testmon-nocollect``
（只讀 ``.testmondata``、不寫新的覆蓋資料、不跑測試），收集完時記下：

- ``selected``：testmon 和 ``-m`` 篩完之後留下的測試數（真正跑的時候會跑這些）；
- ``skipped``：testmon 有執行紀錄（``duration`` 不是空的）、這次沒選到的測試數。
  標 slow、從沒在預設跑法執行過的測試只有佔位紀錄，不算進來；
- ``known``：testmon 有執行紀錄的測試數；``new_db``：還沒有 ``.testmondata``（第一次會全跑）。

只收集、不執行測試，所以不經看門狗。收集失敗時結束碼非零，``check.py`` 會退回不用 testmon。
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from typing import Any

import pytest

COLLECT_ARGS = (
    "--collect-only",
    "-q",
    "-n",
    "0",
    "--testmon-forceselect",
    "--testmon-nocollect",
)


class _Counter:
    """收集完時記下選到的測試與 testmon 的執行紀錄。"""

    def __init__(self) -> None:
        self.selected: list[str] = []
        self.known: set[str] = set()
        self.new_db = True
        self.active = False

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.selected = [item.nodeid for item in session.items]
        data: Any = getattr(session.config, "testmon_data", None)
        if data is None:
            return
        self.active = True
        self.new_db = bool(data.new_db)
        tests: dict[str, dict[str, Any]] = data.all_tests
        self.known = {name for name, row in tests.items() if row.get("duration") is not None}


def preview(extra: list[str] | None = None) -> dict[str, Any]:
    """收集一次，回傳 ``selected``、``skipped``、``known``、``new_db``、``exit``。"""
    counter = _Counter()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = pytest.main([*COLLECT_ARGS, *(extra or [])], plugins=[counter])
    selected = set(counter.selected)
    return {
        "exit": int(code),
        "active": counter.active,
        "selected": len(selected),
        "skipped": len(counter.known - selected),
        "known": len(counter.known),
        "new_db": counter.new_db,
    }


def main(argv: list[str] | None = None) -> int:
    result = preview(sys.argv[1:] if argv is None else argv)
    print(json.dumps(result, ensure_ascii=False))
    # pytest 收集成功時結束碼 0；收集不到任何測試是 5，也算成功（全部略過）。
    ok = result["active"] and result["exit"] in (0, 5)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
