"""BAL-19g：白板的新形狀照 06 6.34.9 的最低角色階級開放（直線長 6、連鎖跳躍 3 階；3×3 2 階；
錐形、環形與長 5 以內的直線 1 階）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.skillgen.random_composer import ComposeError
from trpg.skillgen.skill_tier import retier
from trpg.skillgen.validate import minimum_tier
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()
LINE_6_TIER = 3
CHAIN_TIER = 3
SHAPE_RECIPES = (
    "flame_lance",
    "thunder_lance",
    "frost_breath",
    "venom_mist",
    "whirl_slash",
    "shadow_ring",
    "chain_lightning",
)


def _boards(recipe_id: str, tier: int) -> list:  # type: ignore[type-arg]
    out = []
    for weapon_class in ("melee", "ranged", "focus"):
        for seed in range(6):
            try:
                out.append(
                    compose_whiteboard(
                        seed * 31 + 7,
                        kind="active",
                        weapon_class=weapon_class,
                        tier=tier,
                        library=LIB,
                        recipe_id=recipe_id,
                    )
                )
            except ComposeError:
                continue
    return out


@pytest.mark.parametrize("recipe_id", SHAPE_RECIPES)
def test_new_shape_boards_respect_minimum_character_tier(recipe_id: str) -> None:
    for tier in (1, 2, 3):
        for board in _boards(recipe_id, tier):
            assert minimum_tier(board, LIB) <= tier
            size = board.shape.param_values().get("size")
            if board.shape.type == "line" and tier < LINE_6_TIER:
                assert isinstance(size, int) and size < LIB.budget.min_character_tier.line_length
            if board.shape.type == "chain":
                assert tier >= CHAIN_TIER
            for higher in range(tier + 1, 4):  # 升階重配後仍在新階級的門檻內
                assert minimum_tier(retier(LIB, board, higher), LIB) <= higher


def test_chain_board_only_from_tier_three() -> None:
    assert not _boards("chain_lightning", 1)
    assert not _boards("chain_lightning", 2)
    assert _boards("chain_lightning", 3)


def test_tier_table_matches_design() -> None:
    table = LIB.budget.min_character_tier
    assert table.shapes.get("chain") == CHAIN_TIER
    assert table.shapes.get("square3") == 2
    assert (table.line_length, table.line_tier) == (6, LINE_6_TIER)
    assert "cone" not in table.shapes and "ring" not in table.shapes  # 1 階（「其餘全部」）
