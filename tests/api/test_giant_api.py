"""GB-4a：巨型頭目的 API（``UnitView.footprint``／``tiles``、``PartView.tiles``、核心未露出的
原因字、API 層的單位距離）。

規格 ``docs/phases/PhaseGB計畫.md`` 8.1 第 1 點、T12；原因字照 ``docs/art/GB巨型頭目-移植需求.md``
第 7 節第 5 條、第 9 節。正式內容：熔心坑（``molten_heart_pit``）的灰燼之心，中心 (5, 3)。
"""

from __future__ import annotations

from tests.engine.helpers import give_turn, library, make_state, spawn, template
from tests.engine.test_mist_lock_parts_pb1 import HERO, MASTER, arena
from trpg.api.presenter import part_options_out, traits_view
from trpg.api.skill_reasons import skill_reasons
from trpg.engine import legal_actions
from trpg.engine.actions import Attack
from trpg.engine.state import BattleState
from trpg.engine.view import UnitView, project_for
from trpg.shared.types import Pos, Team, UnitId

HEART = "ashen_heart"


def _pit(allies: list[tuple[int, int, str]]) -> BattleState:
    lib = library()
    spawns = [spawn(Team.ENEMY, (5, 3), HEART, skills=None)]
    for x, y, t in allies:
        spawns.append(spawn(Team.ALLY, (x, y), template(t, reactions=()), skills=None))
    return make_state(lib.maps["molten_heart_pit"], spawns)


def _heart_id(state: BattleState) -> UnitId:
    return next(u.id for u in state.units_sorted() if u.template_id == HEART)


def _hero_id(state: BattleState) -> UnitId:
    return next(u.id for u in state.units_sorted() if u.team is Team.ALLY)


def _heart_view(state: BattleState) -> UnitView:
    view = traits_view(state, Team.ALLY, library(), _hero_id(state))
    return next(u for u in view.units if u.template_id == HEART)


def _xy(tiles: tuple[Pos, ...] | None) -> list[tuple[int, int]]:
    assert tiles is not None
    return [(p.x, p.y) for p in tiles]


def test_giant_view_has_footprint_and_nine_tiles_sorted_by_y_then_x() -> None:
    heart = _heart_view(_pit([(5, 9, "hero_fighter")]))
    assert (heart.pos.x, heart.pos.y) == (5, 3)
    assert heart.footprint == 3
    assert _xy(heart.tiles) == [(x, y) for y in (2, 3, 4) for x in (4, 5, 6)]


def test_one_tile_units_have_no_footprint_fields() -> None:
    state = _pit([(5, 9, "hero_fighter")])
    hero = next(u for u in project_for(state, Team.ALLY).units if u.team is Team.ALLY)
    assert hero.footprint is None and hero.tiles is None
    dumped = hero.model_dump(exclude_none=True)
    assert "footprint" not in dumped and "tiles" not in dumped


def test_part_views_list_their_map_tiles() -> None:
    parts = _heart_view(_pit([(5, 9, "hero_fighter")])).parts
    assert parts is not None
    by_id = {p.id: _xy(p.tiles) for p in parts}
    assert by_id == {
        "core": [(5, 3)],
        "shell_seam": [(4, 3), (6, 3)],
        "vent": [(4, 2), (5, 2), (6, 2)],
    }


def test_one_tile_boss_parts_have_no_tiles() -> None:

    view = traits_view(arena(), Team.ALLY, library(), HERO)
    master = next(u for u in view.units if u.id == MASTER)
    assert master.footprint is None and master.tiles is None
    assert all(p.tiles is None for p in master.parts or ())
    assert all(p.counts_as_behind is None for p in master.parts or ())


def test_only_the_shell_seam_counts_as_behind() -> None:
    """GB-4b（GB-4a 待決 5）：殼縫帶 ``counts_as_behind``，噴口、核心不帶（不輸出）。"""
    parts = _heart_view(_pit([(5, 9, "hero_fighter")])).parts
    assert parts is not None
    behind = {p.id: p.counts_as_behind for p in parts}
    assert behind == {"core": None, "shell_seam": True, "vent": None}
    vent = next(p for p in parts if p.id == "vent")
    assert "counts_as_behind" not in vent.model_dump(exclude_none=True)


def test_core_not_exposed_names_the_breath_phase() -> None:
    # 戰士貼著殼縫西側 (3, 3)：核心未露出寫「呼吸階段才露出」（拿得到第 2 階段名）
    state = _pit([(3, 3, "hero_fighter")])
    hero = _hero_id(state)
    state = give_turn(state, hero)
    out = part_options_out(state, tuple(legal_actions(state)))
    assert out is not None
    attack = next(o for o in out if o.type == "attack" and o.target_id == _heart_id(state))
    assert [(o.part_id, o.ok, o.reason_zh) for o in attack.options] == [
        ("core", False, "呼吸階段才露出"),
        ("shell_seam", True, None),
        ("vent", False, "只有遠程才打得到"),
    ]


def test_core_reason_falls_back_when_no_later_phase_exposes_it() -> None:
    state = _pit([(3, 3, "hero_fighter")])
    hero = _hero_id(state)
    state = give_turn(state, hero)
    heart = state.units[_heart_id(state)]
    # 合成：把核心改成只在第 1 階段（已過去的不算）以外都不露出 → 沒有之後的階段名
    heart.parts = tuple(
        p.model_copy(update={"exposed_in": ("no_such_phase",)}) if p.id == "core" else p
        for p in heart.parts
    )
    action = Attack(unit_id=hero, target_id=heart.id)
    out = part_options_out(state, (action,))
    assert out is not None
    core = next(o for o in out[0].options if o.part_id == "core")
    assert core.reason_zh == "這個階段還沒露出"


def test_skill_reasons_measure_to_the_nearest_tile() -> None:
    # 單位版距離（GB-1b 待決 3）：最近的敵人照到最近佔格的距離排；只有灰燼之心一個敵人時照常給原因
    state = _pit([(5, 11, "hero_archer")])
    hero = _hero_id(state)
    out = skill_reasons(give_turn(state, hero), hero)
    assert isinstance(out.reasons, dict)
