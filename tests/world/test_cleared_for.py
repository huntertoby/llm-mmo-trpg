"""玩家眼中的「已清空」（Phase 6F-3，巡檢 bug 2）。

渡口石階打贏共享的那一隊（夜晚的盾衛巡邏）後，世界照 21.10 第 9 條寫「已清空」（個人的駐守不算進
共享清空，規則不變）；但角色自己的個人隊伍（新手任務的「搶渡船的盜賊」）還站在地圖上時，區域圖不打勾、
提示不說「已清空」。表格測試實際跑 ``after_fight`` 與 ``world_step``。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_field_enemy_rules import NIGHT, _at, _lib, _touch, _win
from trpg.api.world_presenter import event_lines
from trpg.content.library import ContentLibrary
from trpg.world.actions import LocationClearedEvent
from trpg.world.field_enemies import cleared_for, field_enemies, personal_left
from trpg.world.state import FieldPos

PERSONAL = {"at": [10, 10], "group": "bandit_raiders", "personal": True}
SHARED = {"at": [6, 6], "group": "bandit_raiders"}
PLACE = ("cloud_ridge", "ferry_steps")


@pytest.mark.parametrize(
    ("spawns", "beat_personal", "expect"),
    [
        ([SHARED, PERSONAL], False, False),  # 巡檢 bug 2：個人隊伍還在 → 不算清空
        ([SHARED, PERSONAL], True, True),  # 個人的也打完 → 清空
        ([SHARED, {**PERSONAL, "day_phase": "night"}], False, True),  # 個人的這個時段不出現
        ([SHARED], False, True),  # 沒有個人隊伍：同世界的已清空
    ],
)
def test_cleared_for_table(
    field_library: ContentLibrary,
    spawns: list[dict[str, Any]],
    beat_personal: bool,
    expect: bool,
) -> None:
    library = _lib(field_library, spawns)
    world = make_world()
    char = _touch(library, _at(library, (6, 4)), (6, 5), world)
    world, char, events = _win(library, world, char, NOON)
    assert events and isinstance(events[0], LocationClearedEvent)  # 共享的打完：世界照舊寫清空
    assert world.is_cleared(*PLACE, NOON)
    if beat_personal:
        char = char.model_copy(update={"field": FieldPos(map="ferry_steps", x=10, y=8)})
        touched = _touch(library, char, (10, 9), world)
        world, char, _ = _win(library, world, touched, NOON)
    assert cleared_for(library, world, char, PLACE, NOON) is expect
    assert personal_left(library, char, *PLACE, NOON) is not expect
    lines = event_lines(library, "cloud_ridge", events, char, NOON)
    if expect:
        assert lines == ("渡口石階已清空，一段時間後敵人才會回來。",)
    else:
        assert lines == ("這一隊打散了，但渡口石階還有別的敵群。",)
        assert [e.index for e in field_enemies(library, world, char, NOON)] == [1]


def test_other_character_still_sees_own_personal_group(field_library: ContentLibrary) -> None:
    """世界的已清空是共享的；別的角色的個人隊伍下一趟還在，所以對他也不打勾。"""
    library = _lib(field_library, [SHARED, PERSONAL])
    world = make_world()
    char = _touch(library, _at(library, (6, 4)), (6, 5), world)
    world, _, _ = _win(library, world, char, NOON)
    bob = _at(library, (1, 6)).model_copy(update={"character_id": "bob"})
    assert world.is_cleared(*PLACE, NOON)
    assert not cleared_for(library, world, bob, PLACE, NOON)
    assert [e.index for e in field_enemies(library, world, bob, NOON)] == [1]


def test_without_now_keeps_old_line(field_library: ContentLibrary) -> None:
    """沒給 ``now``（舊的呼叫）照舊說「已清空」。"""
    library = _lib(field_library, [SHARED, PERSONAL])
    world = make_world()
    char = _touch(library, _at(library, (6, 4)), (6, 5), world)
    _, char, events = _win(library, world, char, NIGHT)
    assert event_lines(library, "cloud_ridge", events, char) == (
        "渡口石階已清空，一段時間後敵人才會回來。",
    )
