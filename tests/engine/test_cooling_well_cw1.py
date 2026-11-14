"""CW-1 冷卻井（``docs/art/冷卻井-移植需求.md`` 第 5、6 節；玩法PM交接 4.1.12；05 5.12.4 第 1 點）。

- ``cooling_well``：``[blocks_move, breakable]``，不可燃、不爆炸；任何傷害打破（含火）都漏水。
- ``spill.radius: 1``＝3×3（切比雪夫），依 ``(y, x)`` 排序；巨型單位的佔格跳過、不發事件。
- 沒寫 ``radius`` 的舊物件（油桶）照舊十字 5 格，序列化不帶 ``radius``（舊規則包雜湊不變）。
- 熔心坑：4 口井在原本暫代水表面的座標，打破後的戰鬥重播一致。
"""

from __future__ import annotations

from tests.engine.helpers import (
    giant_template,
    library,
    make_map,
    make_state,
    spawn,
    spawn_giant,
)
from trpg.content.environment import SpillDef
from trpg.engine import BattleState
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.effects import DamageObjectEffect, run_effects
from trpg.engine.events import ObjectDestroyed, ObjectExploded, SurfaceChanged
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.setup import build_setup
from trpg.engine.state import state_to_json
from trpg.shared.types import Element, ObjectId, Surface, Team
from trpg.sim.lineup import default_lineup

O1 = ObjectId("obj_0001")
FLAT = "\n".join("000000000" for _ in range(9))


def _water(state: BattleState) -> list[tuple[int, int]]:
    return [
        (x, y)
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is Surface.WATER
    ]


def _well_scene(*, giant: bool = False) -> BattleState:
    m = make_map(FLAT, objects=[(6, 4, "cooling_well")], ally=[(8, 8)], enemy=[(0, 8)])
    spawns = [spawn(Team.ALLY, (8, 8)), spawn(Team.ENEMY, (0, 8))]
    if giant:
        m = m.model_copy(update={"giant_facing": {"test_giant": "east"}})
        spawns.append(spawn_giant(Team.ENEMY, (4, 4), giant_template(id="test_giant")))
    return make_state(m, spawns)


def test_the_object_definition_follows_the_gameplay_ruling() -> None:
    well = library().ruleset.object_def("cooling_well")
    assert well.name_zh == "冷卻井"
    assert well.tags == ("blocks_move", "breakable")
    assert well.explosion is None
    assert well.spill == SpillDef(surface=Surface.WATER, radius=1)
    # GB-4c（玩法PM交接 4.1.13）：說明句拿掉，資訊卡只留由 spill 產生的規則行
    assert well.description_zh is None


def test_breaking_the_well_makes_a_3x3_pool_in_row_order() -> None:
    result = run_effects(_well_scene(), [DamageObjectEffect(object_id=O1, flat=99)])
    destroyed = [e for e in result.events if isinstance(e, ObjectDestroyed)]
    assert [(e.object_id, e.cause) for e in destroyed] == [(O1, "damage")]
    changed = [e for e in result.events if isinstance(e, SurfaceChanged)]
    assert [(e.pos.x, e.pos.y) for e in changed] == [(x, y) for y in (3, 4, 5) for x in (5, 6, 7)]
    assert all(e.cause == f"spill:{O1}" for e in changed)
    assert _water(result.state) == [(x, y) for y in (3, 4, 5) for x in (5, 6, 7)]


def test_fire_damage_also_spills_water_and_never_explodes() -> None:
    result = run_effects(
        _well_scene(), [DamageObjectEffect(object_id=O1, flat=99, element=Element.FIRE)]
    )
    assert not any(isinstance(e, ObjectExploded) for e in result.events)
    assert len(_water(result.state)) == 9


def test_water_skips_the_tiles_a_giant_occupies() -> None:
    state = _well_scene(giant=True)
    result = run_effects(state, [DamageObjectEffect(object_id=O1, flat=99)])
    # 巨人佔 x 3～5、y 3～5：3×3 的左邊一欄 (5, 3～5) 不放
    assert _water(result.state) == [(x, y) for y in (3, 4, 5) for x in (6, 7)]
    changed = [e for e in result.events if isinstance(e, SurfaceChanged)]
    assert all(e.pos.x != 5 for e in changed)


def test_old_spill_without_radius_keeps_the_cross_and_its_serialization() -> None:
    barrel = library().ruleset.object_def("oil_barrel")
    assert barrel.spill is not None and barrel.spill.radius is None
    assert barrel.spill.model_dump() == {"surface": Surface.OIL}
    assert "radius" not in barrel.spill.model_dump_json()
    assert "description_zh" not in barrel.model_dump_json()
    m = make_map(FLAT, objects=[(4, 4, "oil_barrel")], ally=[(8, 8)], enemy=[(0, 8)])
    state = make_state(m, [spawn(Team.ALLY, (8, 8)), spawn(Team.ENEMY, (0, 8))])
    result = run_effects(state, [DamageObjectEffect(object_id=O1, flat=99)])
    oil = sorted(
        (x, y)
        for y in range(state.height)
        for x in range(state.width)
        if result.state.tile(x, y).surface is Surface.OIL
    )
    assert oil == [(3, 4), (4, 3), (4, 4), (4, 5), (5, 4)]


def test_molten_heart_pit_has_four_wells_and_a_battle_replays() -> None:
    lib = library()
    pit = lib.maps["molten_heart_pit"]
    wells = sorted(o.at for o in pit.objects if o.kind == "cooling_well")
    assert wells == [(3, 4), (3, 8), (7, 4), (8, 8)]
    assert not any(s.surface is Surface.WATER for s in pit.surfaces)
    allies, enemies = default_lineup(lib, "molten_heart_pit")
    setup = build_setup(lib, "molten_heart_pit", allies, enemies, max_rounds=30)
    first = run_battle(setup, 2, UtilityAI(lib.ai_profiles))
    assert first.state.winner is not None
    log = BattleLog.model_validate_json(first.to_log().model_dump_json())
    again = replay(log.setup, log.seed, log.actions)
    assert state_to_json(again.state) == state_to_json(first.state)
