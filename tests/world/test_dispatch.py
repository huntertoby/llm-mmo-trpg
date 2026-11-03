"""世界動作的分派表（Phase 5D-R1）：每種世界動作恰好一個處理，經濟與鐵匠的子表涵蓋各自的動作。"""

from __future__ import annotations

from types import UnionType
from typing import get_args

from trpg.world.actions import WorldAction
from trpg.world.crafting import CRAFTING_ACTIONS, CRAFTING_HANDLERS
from trpg.world.economy import ECONOMY_ACTIONS, ECONOMY_HANDLERS
from trpg.world.step import HANDLERS


def _action_types() -> set[type]:
    union = get_args(WorldAction.__value__)[0]
    assert isinstance(union, UnionType)
    return set(get_args(union))


def test_every_world_action_has_one_handler() -> None:
    assert set(HANDLERS) == _action_types()


def test_sub_tables_cover_their_actions() -> None:
    assert set(ECONOMY_HANDLERS) == set(ECONOMY_ACTIONS)
    assert set(CRAFTING_HANDLERS) == set(CRAFTING_ACTIONS)
