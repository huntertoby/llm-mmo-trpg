"""Phase ENG-1 S2：鎖定事件觸發函式的串接順序。

``effects_for`` 依註冊順序串接，註冊順序來自模組的匯入順序。一個事件有 2 個以上觸發函式時，順序
會影響佇列裡的效果順序（也就影響亂數與戰鬥結果），改檔名或調整匯入都可能默默改變它。

這裡只鎖定、不決定順序：測試失敗時先查是哪個匯入變了，不要直接改 ``EXPECTED``——那代表實際結算
的順序變了，要走 ``LOG_FORMAT`` 的流程並先問 PM。
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from trpg.engine.triggers import _TRIGGERS

EXPECTED: dict[str, list[str]] = {
    "unit_downed": [
        "trpg.engine.bombs._bomb_on_downed",
        "trpg.engine.death_surfaces._surface_on_downed",
        "trpg.engine.delayed._cancel_on_downed",
    ],
}

ENTRIES = [
    "trpg.engine",
    "trpg.api.app",
    "trpg.cli.main",
    "trpg.sim.batch",
    # 直接從葉模組進入：順序不能取決於先碰到哪一個觸發模組
    "trpg.engine.bombs",
    "trpg.engine.death_surfaces",
    "trpg.engine.delayed",
    "trpg.engine.triggers",
]

_DUMP = """
import importlib, json, sys
importlib.import_module(sys.argv[1])
from trpg.engine.triggers import _TRIGGERS
names = lambda fns: [f.__module__ + '.' + f.__qualname__ for f in fns]
print(json.dumps({k: names(v) for k, v in _TRIGGERS.items()}))
"""


def _multi(triggers: dict[str, list[str]]) -> dict[str, list[str]]:
    return {event: names for event, names in triggers.items() if len(names) >= 2}


def test_events_with_multiple_triggers_keep_their_order() -> None:
    current = {k: [f"{f.__module__}.{f.__qualname__}" for f in v] for k, v in _TRIGGERS.items()}
    assert _multi(current) == EXPECTED


@pytest.mark.parametrize("entry", ENTRIES)
def test_order_is_the_same_from_every_entry_in_a_fresh_interpreter(entry: str) -> None:
    done = subprocess.run(
        [sys.executable, "-c", _DUMP, entry],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert _multi(json.loads(done.stdout.splitlines()[-1])) == EXPECTED
