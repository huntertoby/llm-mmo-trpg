"""場景物件的預覽資料（Phase 3C-5b，``docs/phases/Phase3C計畫.md`` 7A.5）。

``Preview.pierce``（穿透的射線與穿過的物件）、``Preview.topples``（推倒壓住的範圍）、
``Preview.hurls``（物件投擲與落地結果）給網頁預覽用。
"""

from __future__ import annotations

from tests.engine.test_hurl_object import O1, hurl
from tests.engine.test_hurl_object import arena as hurl_arena
from tests.engine.test_pierce import ARROW, FIRE_ARROW, U2, U3, aim, line_skill, shoot
from tests.engine.test_pierce import arena as pierce_arena
from tests.engine.test_topple import PILLAR, push
from tests.engine.test_topple import arena as topple_arena
from trpg.engine import preview
from trpg.shared.types import ObjectId


def test_a_pierce_preview_lists_the_route_and_the_pierced_object() -> None:
    state = pierce_arena(objects=[(2, 3, "crate")])
    info = preview(state, shoot()).pierce
    assert info is not None
    assert info.route == ((1, 3), (2, 3), (3, 3))
    assert info.objects == ((ObjectId("obj_0001"), (2, 3)),)
    assert info.behind == (U2,) and info.behind_permille == 700


def test_a_pierce_preview_without_objects_still_has_the_route() -> None:
    info = preview(pierce_arena(), shoot()).pierce
    assert info is not None and info.route == ((1, 3), (2, 3), (3, 3))
    assert info.objects == () and info.behind == ()


def test_a_non_pierce_skill_has_no_pierce_preview() -> None:
    state = pierce_arena((ARROW, FIRE_ARROW), objects=[(2, 3, "crate")])
    assert preview(state, shoot(skill=FIRE_ARROW)).pierce is None


def test_a_line_pierce_preview_covers_the_line_and_the_units_behind_the_crate() -> None:
    skill = line_skill()
    state = pierce_arena([skill], objects=[(2, 3, "crate")], foes=[(1, 3), (3, 3)])
    info = preview(state, aim("east", skill.id)).pierce
    assert info is not None
    assert info.route[:3] == ((1, 3), (2, 3), (3, 3))
    assert info.objects == ((ObjectId("obj_0001"), (2, 3)),)
    assert info.behind == (U3,)


def test_a_topple_preview_shows_the_crushed_tiles_and_the_rubble() -> None:
    state = topple_arena((2, 3), foes=[(4, 3), (5, 3)])
    result = preview(state, push())
    (info,) = result.topples
    assert info.object_id == PILLAR and info.pos == (3, 3) and info.direction == (1, 0)
    assert info.tiles == ((4, 3), (5, 3))
    assert info.units == (U2, U3)
    assert info.rubble == (3, 3)  # 兩格都有單位：倒塌物退回原格
    assert result.pierce is None and result.hurls == ()


def test_a_push_without_a_topplable_object_has_no_topple_preview() -> None:
    state = topple_arena((2, 3), kind="crate")
    assert preview(state, push()).topples == ()


def test_a_hurl_preview_shows_where_the_object_goes_and_what_happens() -> None:
    state = hurl_arena(objects=[(1, 3, "oil_barrel")])
    (info,) = preview(state, hurl((3, 3), O1)).hurls
    assert (info.object_id, info.from_pos, info.to_pos) == (O1, (1, 3), (3, 3))
    assert info.outcome == "exploded"
    crate = hurl_arena(objects=[(1, 3, "crate")])
    (shattered,) = preview(crate, hurl((3, 3), O1)).hurls
    assert shattered.outcome == "shattered" and shattered.kind == "crate"
