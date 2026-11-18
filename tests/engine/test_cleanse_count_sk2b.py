"""淨化只移除 1 個減益（``cleanse`` 的 ``count: 1``，SK-2b，玩法交接 4.1.29 第 3 點）：控制類優先 →
剩餘回合最多（永久最多）→ 狀態表順序。省略 ``count`` 照舊移除全部。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, battle, cast, of
from trpg.engine import state_to_json
from trpg.engine.events import StatusRemoved
from trpg.engine.state import StatusInstance
from trpg.narrative.skills import effect_summary

SELF: dict[str, Any] = {"type": "self"}


def _cleansed(statuses: list[tuple[str, int | None]], **params: Any) -> list[str]:
    skill = make_skill(SID, SELF, [{"type": "cleanse", "affects": "self", **params}])
    state = battle(skill)
    state.units[U1].statuses = [StatusInstance(s, r, None) for s, r in statuses]
    result = cast(state)
    return [e.status_id for e in of(result, StatusRemoved)]


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([("bleed", 3), ("slow", 1)], ["slow"]),  # 控制類優先（緩速有 control_group）
        ([("bleed", 1), ("poison", 3)], ["poison"]),  # 都不是控制類：剩餘回合多的
        ([("stun", 1), ("root", 2)], ["root"]),  # 都是控制類：剩餘回合多的
        ([("root", 2), ("slow", 2)], ["slow"]),  # 一樣多：狀態表順序（slow 在 root 前）
        ([("weaken", None), ("poison", 5)], ["weaken"]),  # 永久算最多
        ([("hasted", 2)], []),  # 只有增益：沒有可移除的
    ],
)
def test_count_one_picks_one_debuff(
    statuses: list[tuple[str, int | None]], expected: list[str]
) -> None:
    assert _cleansed(statuses, count=1) == expected


def test_without_count_removes_every_debuff() -> None:
    assert _cleansed([("bleed", 3), ("slow", 1), ("poison", 2)]) == ["bleed", "poison", "slow"]
    assert _cleansed([("bleed", 3), ("slow", 1)], count="all") == ["bleed", "slow"]


def test_same_input_same_result() -> None:
    skill = make_skill(SID, SELF, [{"type": "cleanse", "affects": "self", "count": 1}])
    state = battle(skill)
    state.units[U1].statuses = [StatusInstance("bleed", 2, None), StatusInstance("slow", 2, None)]
    first, second = cast(state), cast(state)
    assert state_to_json(first.state) == state_to_json(second.state)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]


def test_card_text() -> None:
    lib = library()
    one = make_skill(SID, SELF, [{"type": "cleanse", "affects": "self", "count": 1}])
    assert "1 個負面狀態" in effect_summary(lib, one, one.effects[0])
    every = make_skill(SID, SELF, [{"type": "cleanse", "affects": "self"}])
    assert "所有負面狀態" in effect_summary(lib, every, every.effects[0])


def test_count_must_be_one_or_all() -> None:
    from trpg.skillgen.validate import validate_skill  # noqa: PLC0415

    bad = make_skill(SID, SELF, [{"type": "cleanse", "affects": "self", "count": 2}])
    assert any("count" in v.message for v in validate_skill(bad, library()))
