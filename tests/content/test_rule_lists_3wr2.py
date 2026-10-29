"""Phase 3W-R2：從程式移到資料的原語分類與形狀清單（白板、升階重配、輔助技）都指向存在的內容。"""

from __future__ import annotations

from tests.engine.helpers import library


def test_listed_primitives_and_shapes_exist() -> None:
    lib = library()
    primitives = set(lib.ruleset.primitives.by_id())
    shapes = set(lib.ruleset.shapes.by_id())
    board = lib.composer.whiteboard
    growth = lib.budget.retier_growth
    support = lib.flash.support
    lists = {
        "whiteboard.self_move_effects": board.self_move_effects,
        "whiteboard.displace_effects": board.displace_effects,
        "whiteboard.terrain_effects": board.terrain_effects,
        "retier_growth.terrain_effects": growth.terrain_effects,
        "retier_growth.area_effects": growth.area_effects,
        "support.harm_effects": support.harm_effects,
        "support.help_effects": support.help_effects,
        "support.ally_effects": support.ally_effects,
    }
    for name, ids in lists.items():
        assert set(ids) <= primitives, f"{name} 有不存在的原語：{sorted(set(ids) - primitives)}"
    assert set(board.simple_shapes) <= shapes


def test_values_match_the_former_constants() -> None:
    """搬到資料前寫在程式裡的值（行為不變）。"""
    lib = library()
    board = lib.composer.whiteboard
    assert set(board.simple_shapes) == {"self", "single", "ground_tile", "cross", "square3"}
    assert set(board.self_move_effects) == {"teleport", "swap", "leap"}
    assert set(board.displace_effects) == {"teleport", "swap", "leap", "push", "pull"}
    assert set(board.terrain_effects) == {"raise_terrain", "lower_terrain"}
    growth = lib.budget.retier_growth
    assert set(growth.terrain_effects) == {"raise_terrain", "lower_terrain"}
    assert set(growth.area_effects) == {"raise_terrain", "lower_terrain", "create_surface"}
    support = lib.flash.support
    assert set(support.harm_effects) == {"damage", "delayed_damage"}
    assert set(support.help_effects) == {"heal", "shield"}
    assert set(support.ally_effects) == {"heal", "shield", "apply_status", "cleanse", "grant_ap"}
    assert (lib.budget.min_ratio_permille, lib.budget.max_ratio_permille) == (700, 1000)
