"""等待動畫的短句（Phase RT-3）：`content/ui/narration_wait.yaml` 的 schema 與登記。"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.loader import load_content_file
from trpg.content.registry import KNOWN_CONTENT_FILES
from trpg.content.ui_wait import WAIT_SCENES, WaitNarration

WAIT_FILE = PROJECT_ROOT / "content" / "ui" / "narration_wait.yaml"

GOOD: dict[str, Any] = {
    "rotate_ms": 4000,
    "long_ms": 8000,
    "fail": "說書人停下了筆，再試一次？",
    "scenes": {
        "skill": {"lines": ["羽毛筆正描著。"], "long": "還沒停。"},
        "judge": {"lines": ["沙漏翻了過來……"], "long": "再等一下。"},
        "npc": {"lines": ["{name}想了想……"], "long": "{name}有很多話要說。"},
        "retell": {"lines": ["說書人翻到前幾頁……"], "long": "說來話長。"},
    },
}


def test_the_file_loads() -> None:
    table = load_content_file(WAIT_FILE, WaitNarration)
    assert sorted(table.scenes) == sorted(WAIT_SCENES)
    assert table.rotate_ms == 4000
    assert table.long_ms == 8000
    assert table.fail == "說書人停下了筆，再試一次？"
    assert len(table.scenes["skill"].lines) == 4
    assert all("{name}" in t for t in table.scenes["npc"].lines)
    assert "等待短句 4 個場合" in table.summary()


def test_registered_for_content_check() -> None:
    assert any(
        f.relative_path == "ui/narration_wait.yaml" and f.model is WaitNarration
        for f in KNOWN_CONTENT_FILES
    )


def test_good_example_passes() -> None:
    WaitNarration.model_validate(GOOD)


def _bad(path: tuple[str, ...], value: object) -> dict[str, Any]:
    data = copy.deepcopy(GOOD)
    cur: Any = data
    for key in path[:-1]:
        cur = cur[key]
    if value is None:
        del cur[path[-1]]
    else:
        cur[path[-1]] = value
    return data


@pytest.mark.parametrize(
    "data",
    [
        _bad(("scenes", "retell"), None),  # 缺場合
        _bad(("scenes", "extra"), {"lines": ["x"], "long": "y"}),  # 多場合
        _bad(("scenes", "skill", "lines"), []),  # 沒有句子
        _bad(("scenes", "skill", "long"), None),  # 缺提示句
        _bad(("scenes", "judge", "lines"), ["墨滴落下……"]),  # 古風詞
        _bad(("fail",), "毛筆停了"),  # 古風詞
        _bad(("scenes", "skill", "lines"), ["{name}在畫"]),  # 只有 npc 能用 {name}
        _bad(("long_ms",), 2000),  # 比輪替還短
        _bad(("rotate_ms",), 10),  # 太短
        _bad(("color",), "x"),  # 拼錯欄位
    ],
)
def test_bad_files_are_rejected(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        WaitNarration.model_validate(data)
