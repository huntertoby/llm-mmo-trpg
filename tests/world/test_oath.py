"""立誓與解除誓約的接點（Phase 5A-6；``docs/phases/Phase5計畫.md`` 11.2 第 8 項）。

18.6 的 15 種模板與戰鬥判定在 5C-3；這裡用最小的測試樣本（代決 5A6-9）。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathProposal, OathTable, oath_problems
from trpg.world.actions import (
    OathReleasedEvent,
    OathSwornEvent,
    ReleaseOathAction,
    SwearOathAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

SAMPLE = OathTable.model_validate(
    {
        "templates": [
            {"id": "no_items", "name_zh": "不使用道具", "difficulty": "easy"},
            {
                "id": "melee_kills",
                "name_zh": "每場至少用近戰擊殺 N 名敵人",
                "difficulty": "medium",
                "params": [{"id": "n", "kind": "int", "min": 1, "max": 2}],
            },
            {
                "id": "one_element",
                "name_zh": "只用某一種元素的技能造成傷害",
                "difficulty": "hard",
                "params": [{"id": "element", "kind": "choice", "choices": ["fire", "ice"]}],
            },
        ]
    }
)


@pytest.fixture(scope="module")
def sworn_lib(library: ContentLibrary) -> ContentLibrary:
    return dataclasses.replace(library, world_oaths=SAMPLE)


def _swear(template: str, **params: str | int) -> SwearOathAction:
    return SwearOathAction(
        proposal=OathProposal(template=template, params=params), player_text="我絕不後退"
    )


def test_static_problems() -> None:
    assert oath_problems(SAMPLE, OathProposal(template="no_items")) == []
    assert oath_problems(SAMPLE, OathProposal(template="nope"))
    assert oath_problems(SAMPLE, OathProposal(template="melee_kills"))  # 缺參數
    assert oath_problems(SAMPLE, OathProposal(template="melee_kills", params={"n": 3}))
    assert oath_problems(SAMPLE, OathProposal(template="one_element", params={"element": "dark"}))
    assert oath_problems(SAMPLE, OathProposal(template="no_items", params={"x": 1}))


def test_swear_and_release_with_cooldown(sworn_lib: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    sworn = world_step(sworn_lib, world, make_char(), _swear("melee_kills", n=2), NOON)
    oath = sworn.char.oath
    assert oath is not None
    assert (oath.template, oath.params, oath.difficulty, oath.sworn_at) == (
        "melee_kills",
        {"n": 2},
        "medium",
        NOON,
    )
    assert isinstance(sworn.events[0], OathSwornEvent)
    with pytest.raises(WorldActionError, match="同時只能有 1 個"):
        world_step(sworn_lib, world, sworn.char, _swear("no_items"), NOON)
    released = world_step(sworn_lib, world, sworn.char, ReleaseOathAction(), NOON + 10)
    assert released.char.oath is None
    assert released.char.oath_cooldown_until == NOON + 10 + 86400
    assert isinstance(released.events[0], OathReleasedEvent)
    with pytest.raises(WorldActionError, match="1 天"):
        world_step(sworn_lib, world, released.char, _swear("no_items"), NOON + 86000)
    again = world_step(sworn_lib, world, released.char, _swear("no_items"), NOON + 10 + 86400)
    assert again.char.oath is not None


def test_swear_rejections(
    library: ContentLibrary, sworn_lib: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    with pytest.raises(WorldActionError, match="誓約模板"):
        world_step(library, world, make_char(), _swear("no_items"), NOON)  # 內容還沒有模板
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        world_step(sworn_lib, world, make_char(location="ferry_steps"), _swear("no_items"), NOON)
    with pytest.raises(WorldActionError, match="必須是"):
        world_step(sworn_lib, world, make_char(), _swear("one_element", element="dark"), NOON)
    with pytest.raises(WorldActionError, match="沒有誓約"):
        world_step(sworn_lib, world, make_char(), ReleaseOathAction(), NOON)
