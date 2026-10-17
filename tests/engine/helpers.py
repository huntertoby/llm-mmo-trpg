"""引擎測試用的小工具：自訂地圖與單位、控制骰子結果。"""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from pathlib import Path

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef
from trpg.engine import BattleSetup, BattleState, UnitSpawn, start_battle
from trpg.shared.rng import Rng, RngState
from trpg.shared.types import Attribute, Team, UnitId

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEMO_ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
DEMO_ENEMIES = ("bandit", "bandit_archer", "bandit_boss")


@cache
def library() -> ContentLibrary:
    return load_library(PROJECT_ROOT / "content")


def make_map(
    heights: str,
    terrain: str | None = None,
    *,
    ally: Sequence[tuple[int, int]] = ((0, 0),),
    enemy: Sequence[tuple[int, int]] | None = None,
) -> MapDef:
    """以字串建立地圖。``terrain`` 圖例：``.`` 石地、``x`` 深淵、``~`` 岩漿、``g`` 草地。"""
    rows = heights.strip().split("\n")
    w, h = len(rows[0]), len(rows)
    if terrain is None:
        terrain = "\n".join("." * w for _ in range(h))
    return MapDef.model_validate(
        {
            "id": "test_map",
            "name_zh": "測試",
            "size": [w, h],
            "heights": heights.strip(),
            "terrain": terrain.strip(),
            "legend": {".": "stone", "x": "chasm", "~": "lava", "g": "grass"},
            "start_zones": {
                "ally": [list(c) for c in ally],
                "enemy": [list(c) for c in (enemy or [(w - 1, h - 1)])],
            },
        }
    )


def template(base: str = "bandit", **overrides: object) -> UnitTemplate:
    """以既有範本為基礎修改欄位（例如 ``max_hp``、``tags``、``attributes``）。"""
    t = library().unit(base)
    if "attributes" in overrides and isinstance(overrides["attributes"], dict):
        attrs = dict(t.attributes)
        attrs.update({Attribute(k): v for k, v in overrides["attributes"].items()})
        overrides["attributes"] = attrs
    return UnitTemplate.model_validate({**t.model_dump(), **overrides})


def spawn(
    team: Team, pos: tuple[int, int], tmpl: UnitTemplate | str = "bandit", weapon: str | None = None
) -> UnitSpawn:
    lib = library()
    t = lib.unit(tmpl) if isinstance(tmpl, str) else tmpl
    w = lib.weapons[weapon or t.weapon]
    return UnitSpawn(template=t, weapon=w, team=team, position=pos)


def make_setup(
    map_def: MapDef, spawns: Sequence[UnitSpawn], *, max_rounds: int | None = None, **core: int
) -> BattleSetup:
    """``core`` 可覆寫 ``rules/core.yaml`` 的數值。

    例如 ``fall_damage_permille_per_level=200``。
    """
    rs = library().ruleset
    if core:
        rs = rs.model_copy(update={"core": rs.core.model_copy(update=core)})
    return BattleSetup(map=map_def, ruleset=rs, units=tuple(spawns), max_rounds=max_rounds)


def make_state(
    map_def: MapDef, spawns: Sequence[UnitSpawn], *, seed: int = 0, **core: int
) -> BattleState:
    return start_battle(make_setup(map_def, spawns, **core), seed)


def give_turn(state: BattleState, unit_id: str) -> BattleState:
    """回傳複本：把行動者換成 ``unit_id``，並給滿 AP 與移動點數（測試用）。"""
    s = state.clone()
    uid = UnitId(unit_id)
    s.active_unit = uid
    s.turn_pos = s.turn_order.index(uid)
    unit = s.units[uid]
    unit.ap = s.ruleset.core.ap_per_turn
    unit.move_points = unit.speed
    return s


def rng_state_for(rolls: Sequence[tuple[int, int]], limit: int = 2_000_000) -> RngState:
    """找一個亂數狀態，使接下來依序 ``roll(sides)`` 得到指定值：``[(20, 20), (8, 3)]``。"""
    for seed in range(limit):
        rng = Rng(seed)
        start = rng.get_state()
        if all(rng.roll(sides) == value for sides, value in rolls):
            return start
    raise AssertionError(f"找不到符合 {rolls} 的種子")


def with_rolls(state: BattleState, rolls: Sequence[tuple[int, int]]) -> BattleState:
    s = state.clone()
    s.rng_state = rng_state_for(rolls)
    return s
