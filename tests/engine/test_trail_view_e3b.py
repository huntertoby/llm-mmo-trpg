"""E3b：格子視圖帶出霜行表面是誰留下的（``TileView.surface_trail``；名詞說明寫「〇〇沿路留下的冰」）。"""

from __future__ import annotations

from tests.engine.race_helpers import U1, race_state
from tests.engine.test_trail_e3 import _frost, _walk
from trpg.engine.view import project_for
from trpg.shared.types import Team


def test_tile_view_names_the_trail_owner_and_omits_it_otherwise() -> None:
    state = _frost(race_state(None, foes=((6, 6),)))
    before = project_for(state, Team.ALLY)
    assert all(t.surface_trail is None for t in before.tiles)
    assert all("surface_trail" not in t.model_dump() for t in before.tiles)  # 既有 JSON 不變
    after = project_for(_walk(state, (3, 3), (4, 3), (5, 3)).state, Team.ENEMY)
    trails = {(t.x, t.y): t.surface_trail for t in after.tiles if t.surface_trail is not None}
    assert trails == {(3, 3): U1, (4, 3): U1}
    tile = next(t for t in after.tiles if (t.x, t.y) == (3, 3))
    assert tile.model_dump(mode="json")["surface_trail"] == U1
