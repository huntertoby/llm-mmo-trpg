"""任務與線頭面板的後端欄位（PNL-3；``docs/art/資訊面板-移植需求.md`` 2.4、#24、#26）：
任務步驟「地點｜要做的事」分欄、委託人頭像、線頭「剩 …」。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.world.helpers import NOON, hero, make_world
from trpg.api.world_story_view import _left_zh, quest_log, split_step, thread_views
from trpg.content.library import ContentLibrary
from trpg.world.state import CharacterState, QuestState, ThreadState
from trpg.world.step import new_character

HOUR = 3600
DAY = 24 * HOUR


def _char(library: ContentLibrary, **updates: Any) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    return char.model_copy(update=updates)


@pytest.mark.parametrize(
    ("text", "place", "task"),
    [
        ("渡口石階：趕走搶渡船的盜賊", "渡口石階", "趕走搶渡船的盜賊"),
        ("角魔古祭壇：赫琳的背叛（祭司的護衛）", "角魔古祭壇", "赫琳的背叛（祭司的護衛）"),
        ("A：B：C", "A", "B：C"),  # 只拆第一個「：」
        ("在餘燼集打聽斷崖幫的運輸隊", None, "在餘燼集打聽斷崖幫的運輸隊"),  # 沒有「：」整句放右欄
        ("：只有後半", None, "：只有後半"),
        ("只有前半：", None, "只有前半："),
    ],
)
def test_split_step(text: str, place: str | None, task: str) -> None:
    assert split_step(text) == (place, task)


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0, "剩不到 1 小時"),
        (HOUR - 1, "剩不到 1 小時"),
        (HOUR, "剩 1 小時"),
        (5 * HOUR + 59, "剩 5 小時"),
        (DAY, "剩 1 天"),
        (2 * DAY + 23 * HOUR, "剩 2 天 23 小時"),
    ],
)
def test_left_zh(seconds: int, text: str) -> None:
    assert _left_zh(seconds) == text


def test_quest_log_splits_steps_and_gives_giver_portrait(library: ContentLibrary) -> None:
    accepted = QuestState(quest="starter_ferry", steps_done=1, started_at=NOON)
    char = _char(library, quests=(accepted,))
    (quest,) = quest_log(library, char)
    assert quest.giver_zh == "渡婆婆"
    assert quest.giver_region == "cloud_ridge"
    assert quest.giver_portrait is not None  # 渡婆婆的人設卡有頭像
    first, second = quest.steps[0], quest.steps[1]
    assert (first.place_zh, first.task_zh, first.done) == ("渡口石階", "趕走搶渡船的盜賊", True)
    assert first.text_zh == "渡口石階：趕走搶渡船的盜賊"  # 舊欄位照舊
    assert (second.place_zh, second.current) == ("竹林小徑", True)
    for step in quest.steps:
        assert step.task_zh is not None and step.task_zh != ""


def test_thread_left_text_and_old_expires_kept(library: ContentLibrary) -> None:
    state = ThreadState(
        thread="peddler_owes_you",
        skeleton="broken_ferry",
        region="cloud_ridge",
        created_at=NOON,
        expires_at=NOON + 2 * DAY + 23 * HOUR + 10,
    )
    char = _char(library, threads=(state,))
    (view,) = thread_views(library, make_world(), char, NOON)
    assert view.left_zh == "剩 2 天 23 小時"
    assert view.expires_zh == "2 天 23 小時後到期"  # HUD 追蹤列照舊
