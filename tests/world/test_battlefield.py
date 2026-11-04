"""就地開打：從實地地圖切 12×12 戰場（Phase 6C-2；21.4、21.9 第 6 條、21.10 第 7 條）。

純函式的表格測試用測試自己的空曠地圖；開戰、戰後位置與重播用 6C-1 的渡口石階小地圖
（:mod:`tests.world.test_field_enemies`）；正式內容的每一隊都用相鄰的接觸點切一次。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.world.helpers import NOON, PARTY, make_world
from tests.world.test_field_enemies import (
    GUARD,
    _char,
    _grid,
    _library,
    _play,
    _seed_facing,
    _steps_map,
    _visit,
    _walk,
)
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef, check_map, passable_grid
from trpg.engine.battle import begin_battle
from trpg.engine.runner import apply_step
from trpg.shared.types import Team
from trpg.world.actions import BattleEndedEvent, BattleStartedEvent, FightAction, RetreatAction
from trpg.world.battle import _run, auto_steps, encounter_map, prepare_battle
from trpg.world.battlefield import (
    FALLBACK_ZH,
    UnitCounts,
    contact_battlefield,
    cut_battlefield,
    cut_origin,
)
from trpg.world.common import rules_of
from trpg.world.encounters import roll_lineup
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, loads_char, read_log
from trpg.world.state import CharacterState, EncounterResult, Facing, FieldContact, FieldPos
from trpg.world.step import world_step

type XY = tuple[int, int]

COUNTS = UnitCounts(allies=3, enemies=3)


def _open(
    size: XY = (30, 30), rows: list[str] | None = None, heights: list[str] | None = None
) -> FieldMapDef:
    """測試用的空曠實地地圖（石地）；``rows`` 可以畫牆（``#``）或深淵（``~``）。"""
    w, h = size
    return FieldMapDef.model_validate(
        {
            "id": "test_field",
            "name_zh": "測試空地",
            "region": "cloud_ridge",
            "location": "ferry_steps",
            "size": [w, h],
            "heights": _grid(heights or ["0" * w] * h),
            "terrain": _grid(rows or ["." * w] * h),
            "legend": {".": "stone", "#": "wall", "~": "chasm"},
            "entry": [0, 0],
        }
    )


@pytest.fixture(scope="module")
def template(field_library: ContentLibrary) -> MapDef:
    return next(m for k, m in sorted(field_library.maps.items()) if m.archetype == "open_plain")


def _cut(
    library: ContentLibrary,
    field: FieldMapDef,
    template: MapDef,
    ally: XY,
    enemy: XY,
    *,
    counts: UnitCounts = COUNTS,
    first: Team | None = None,
    came_from: XY | None = None,
) -> MapDef:
    found = cut_battlefield(
        library,
        field,
        ally_at=ally,
        enemy_at=enemy,
        counts=counts,
        first=first,
        template=template,
        came_from=came_from,
    )
    assert not isinstance(found, str), found
    return found[0]


def _dist(a: XY, b: XY) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------------------
# 切法：中心、靠邊平移
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("center", "size", "origin"),
    [
        ((15, 15), (30, 30), (9, 9)),  # 中間：中心往左上 6 格
        ((0, 0), (30, 30), (0, 0)),  # 左上角：往內推
        ((29, 29), (30, 30), (18, 18)),  # 右下角：不超出地圖
        ((3, 27), (30, 30), (0, 18)),  # 左下
        ((20, 5), (24, 18), (12, 0)),  # 右上（不是正方形的地圖）
        ((6, 6), (12, 12), (0, 0)),  # 剛好 12×12
    ],
)
def test_cut_origin_centers_and_shifts_inward(center: XY, size: XY, origin: XY) -> None:
    assert cut_origin(center, size, 12) == origin


def test_cut_copies_field_tiles(field_library: ContentLibrary, template: MapDef) -> None:
    rows = ["." * 30 for _ in range(30)]
    rows[12] = "." * 14 + "#" + "." * 15
    heights = ["0" * 30 for _ in range(30)]
    heights[10] = "0" * 16 + "2" + "0" * 13
    base = _open(rows=rows, heights=heights).model_dump(mode="json")
    field = FieldMapDef.model_validate({**base, "objects": [{"at": [18, 11], "kind": "crate"}]})
    # 隔 3 格：接觸點 (14, 15) 離 (18, 15) 剛好 4，主角不用退；中點 (16, 15) → (10, 9)
    battle = _cut(field_library, field, template, (14, 15), (18, 15))
    assert battle.size == (12, 12)  # 規則 field.cut_size
    assert battle.tile_terrain(4, 3) == "wall"  # 實地 (14, 12)
    assert battle.tile_height(6, 1) == 2  # 實地 (16, 10)
    assert [(o.at, o.kind) for o in battle.objects] == [((8, 2), "crate")]
    assert battle.region is None  # 換皮由 prepare_battle 做（reskin 照舊）
    assert battle.archetype == template.archetype
    assert battle.objective.kind == "eliminate"
    terrain = field_library.ruleset.terrain.by_id()
    objects = field_library.ruleset.objects.by_id()
    assert check_map(battle, terrain, field_library.ruleset.core, objects) == []


# ---------------------------------------------------------------------------
# 起始區：方向、先手、人數
# ---------------------------------------------------------------------------


def _placed(
    library: ContentLibrary, field: FieldMapDef, template: MapDef, **kw: Any
) -> tuple[MapDef, Any]:
    found = cut_battlefield(library, field, counts=COUNTS, template=template, **kw)
    assert not isinstance(found, str), found
    return found


# (接觸點, 前一格, 敵方帶頭的, 先手, 主角的實地格子, 隔幾格)
DISTANCE_CASES = [
    # 從背後相鄰接觸（我方先手）：往西退到隔 2 格
    ((15, 15), (14, 15), (16, 15), Team.ALLY, (13, 15), 2),
    # 被看到（敵方先手）、沒有先手：隔 3 格
    ((15, 15), (14, 15), (16, 15), Team.ENEMY, (12, 15), 3),
    ((15, 15), (14, 15), (16, 15), None, (12, 15), 3),
    # 往北走、從南邊相鄰：往南退
    ((15, 16), (15, 17), (15, 15), Team.ALLY, (15, 18), 2),
    ((15, 16), (15, 17), (15, 15), None, (15, 19), 3),
    # 視野內 4 格被看到：剛好隔 3 格，不用退
    ((15, 19), (15, 20), (15, 15), Team.ENEMY, (15, 19), 3),
    # 視野內 4 格、我方先手（不會發生，照規則仍隔 2 格）：退不了 → 符合距離、最靠近接觸點的格子
    ((15, 19), (15, 20), (15, 15), Team.ALLY, (15, 18), 2),
    # 巡邏走到身上（同一格）：沿走來的方向退
    ((15, 15), (16, 15), (15, 15), Team.ALLY, (18, 15), 2),
    # 沒有前一格（6E-3 以前的接觸）：符合距離、最靠近接觸點的格子（同距離照 y、x）
    ((15, 15), None, (16, 15), Team.ALLY, (15, 13), 2),
    # 靠邊：退到地圖邊緣
    ((2, 1), (3, 1), (1, 1), None, (5, 1), 3),
    ((27, 28), (26, 28), (28, 28), Team.ALLY, (25, 28), 2),
]


@pytest.mark.parametrize(
    ("contact", "came_from", "enemy", "first", "hero", "gap"),
    DISTANCE_CASES,
    ids=[f"{c[0]}->{c[2]}-{c[3]}" for c in DISTANCE_CASES],
)
def test_opening_distance(  # noqa: PLR0917 - pytest 參數化
    field_library: ContentLibrary,
    template: MapDef,
    contact: XY,
    came_from: XY | None,
    enemy: XY,
    first: Team | None,
    hero: XY,
    gap: int,
) -> None:
    """21.10 第 26 條：我方先手隔 2 格、其他隔 3 格；敵方帶頭的不動，主角沿走來的方向往回退。"""
    battle, info = _placed(
        field_library,
        _open(),
        template,
        ally_at=contact,
        enemy_at=enemy,
        first=first,
        came_from=came_from,
    )
    assert info.gap == gap
    x0, y0 = cut_origin(((hero[0] + enemy[0]) // 2, (hero[1] + enemy[1]) // 2), (30, 30), 12)
    assert (info.x, info.y) == (x0, y0)  # 以雙方帶頭的中點切
    a = (hero[0] - x0, hero[1] - y0)
    e = (enemy[0] - x0, enemy[1] - y0)
    allies = battle.start_zones[Team.ALLY]
    enemies = battle.start_zones[Team.ENEMY]
    assert (len(allies), len(enemies)) == (3, 4)  # field.min_ally_cells、min_enemy_cells
    assert allies[0] == a  # 主角
    assert enemies[0] == e  # 帶頭的站在地圖上看到的位置
    nearest = min(_dist(c, o) for c in allies for o in enemies)
    assert nearest == gap + 1  # 起始區任兩格之間都至少隔 gap 格（部署怎麼挑都一樣）
    assert all(_dist(c, a) < _dist(c, e) for c in allies)  # 我方在玩家這一側
    assert all(_dist(c, e) < _dist(c, a) for c in enemies)  # 敵方在敵群這一側


def test_blocked_retreat_takes_nearest_fitting_cell(
    field_library: ContentLibrary, template: MapDef
) -> None:
    """往回退撞牆：在走得到、符合距離的格子裡挑最靠近接觸點的（同距離照 y、x）。"""
    rows = [list("." * 30) for _ in range(30)]
    rows[16][13] = "#"
    field = _open(rows=["".join(r) for r in rows])
    battle, info = _placed(
        field_library,
        field,
        template,
        ally_at=(15, 16),
        enemy_at=(15, 15),
        first=None,
        came_from=(14, 16),
    )
    assert info.gap == 3
    assert battle.start_zones[Team.ALLY][0] == (12 - info.x, 16 - info.y)


def _corridor(length: int, east: int = 3, north: int = 0) -> FieldMapDef:
    """第 15 列的一條走廊：敵方 (20, 15) 往東 ``east`` 格、往西 ``length`` 格；``north``＝從
    (20, 14) 往北的岔路格數。其他都是牆。"""
    rows = [list("#" * 30) for _ in range(30)]
    for x in range(20 - length, 21 + east):
        rows[15][x] = "."
    for y in range(15 - north, 15):
        rows[y][20] = "."
    return _open(rows=["".join(r) for r in rows])


@pytest.mark.parametrize(
    ("length", "first", "gap"),
    [
        (6, None, 3),  # 放得下規定的距離
        (5, None, 2),  # 隔 3 放不下 → 另一個（2）
        (4, None, 1),  # 2 也放不下 → 隔 1
        (3, None, None),  # 都不行 → 退回模板
        (6, Team.ALLY, 2),
        (4, Team.ALLY, 1),  # 我方先手：2 → 3 → 1
        (3, Team.ALLY, None),
    ],
)
def test_fallback_distance_order(
    field_library: ContentLibrary,
    template: MapDef,
    length: int,
    first: Team | None,
    gap: int | None,
) -> None:
    found = cut_battlefield(
        field_library,
        _corridor(length),
        ally_at=(19, 15),
        enemy_at=(20, 15),
        counts=COUNTS,
        first=first,
        template=template,
        came_from=(18, 15),
    )
    if gap is None:
        assert found == "zones" and "站位放不下" in FALLBACK_ZH["zones"]
        return
    assert not isinstance(found, str), found
    battle, info = found
    assert info.gap == gap
    hero = (20 - gap - 1 - info.x, 15 - info.y)
    assert battle.start_zones[Team.ALLY][0] == hero


def test_gap_order_comes_from_rules(field_library: ContentLibrary) -> None:
    rules = rules_of(field_library).field
    assert (rules.gap_ally_first, rules.gap_other, rules.gap_fallback) == (2, 3, 1)
    assert rules.gaps(True) == (2, 3, 1)
    assert rules.gaps(False) == (3, 2, 1)
    assert rules.model_copy(update={"gap_fallback": 2}).gaps(False) == (3, 2)


def test_zone_grows_with_unit_count(field_library: ContentLibrary, template: MapDef) -> None:
    counts = UnitCounts(allies=5, enemies=6, third=2)
    battle = _cut(field_library, _open(), template, (15, 15), (18, 15), counts=counts)
    assert len(battle.start_zones[Team.ALLY]) == 5
    assert len(battle.start_zones[Team.ENEMY]) == 6
    assert len(battle.start_zones[Team.THIRD]) == 2  # 6E-3b：第三方另畫起始區


def test_two_sided_battle_has_no_third_zone(
    field_library: ContentLibrary, template: MapDef
) -> None:
    battle = _cut(field_library, _open(), template, (15, 15), (18, 15))
    assert Team.THIRD not in battle.start_zones  # 沒有第三方：照舊兩方


# ---------------------------------------------------------------------------
# 6E-3b／6E-3c：三方混戰的第三方、主角不擺到敵方帶頭的另一側
# ---------------------------------------------------------------------------

THIRD_COUNTS = UnitCounts(allies=3, enemies=3, third=2)


@pytest.mark.parametrize("first", [Team.ALLY, None])
def test_third_party_keeps_two_cells_from_allies(
    field_library: ContentLibrary, template: MapDef, first: Team | None
) -> None:
    """空曠地圖：第三方排在敵方附近（離敵方起始區最近, y, x），離我方起始區每一格至少隔 2 格。"""
    found = cut_battlefield(
        field_library,
        _open(),
        ally_at=(15, 15),
        enemy_at=(16, 15),
        counts=THIRD_COUNTS,
        first=first,
        template=template,
        came_from=(14, 15),
    )
    assert not isinstance(found, str), found
    battle, _ = found
    allies, enemies = battle.start_zones[Team.ALLY], battle.start_zones[Team.ENEMY]
    third = battle.start_zones[Team.THIRD]
    assert len(third) == 2 and not set(third) & (set(allies) | set(enemies))
    assert min(_dist(c, a) for c in third for a in allies) >= 3
    assert all(min(_dist(c, e) for e in enemies) == 1 for c in third)  # 貼著敵方
    assert _third_on_enemy_side(battle)
    terrain = field_library.ruleset.terrain.by_id()
    objects = field_library.ruleset.objects.by_id()
    assert check_map(battle, terrain, field_library.ruleset.core, objects) == []


# (往西幾格, 往東幾格, 往北的岔路格數, 第三方人數, 隔幾格＝None 退回模板, 第三方的實地格子)
THIRD_FALLBACK_CASES = [
    (6, 3, 0, 1, 3, [(19, 15)]),  # 隔 3 格：第三方只剩敵我中間 (19, 15)（離我方 (16, 15) 隔 2 格）
    (6, 3, 3, 2, 3, [(20, 12), (19, 15)]),  # 敵方背後的北邊岔路
    # 隔 3、2 格排不出第三方 → 雙方隔 1 格（我方 (18～16, 15)），第三方仍離我方隔 2 格（6E-3c）、
    # 在敵方那一側 (24, 15)（6E-3d）
    (5, 4, 0, 1, 1, [(24, 15)]),
    # 隔 3 格時敵方那側只剩北邊一格 → 隔 2 格：北邊 (20, 12) 與東邊 (22, 15)
    (5, 3, 3, 2, 2, [(20, 12), (22, 15)]),
    # 6E-3c 在隔 1 格排出 (24, 15)、(13, 15)；(13, 15) 在我方背後（離主角比離敵方帶頭的近）→ 6E-3d
    # 排不出 → 退回模板
    (8, 5, 0, 2, None, None),
    (6, 5, 0, 2, None, None),
    (7, 3, 0, 2, None, None),
    (6, 3, 0, 2, None, None),  # 都排不出 → 退回模板
]


def _third_on_enemy_side(battle: MapDef) -> bool:
    """第三方起始區每一格離敵方帶頭的（敵方起始區第一格）都比離主角（我方第一格）近（6E-3d）。"""
    hero, leader = battle.start_zones[Team.ALLY][0], battle.start_zones[Team.ENEMY][0]
    return all(_dist(c, leader) < _dist(c, hero) for c in battle.start_zones[Team.THIRD])


@pytest.mark.parametrize(("length", "east", "north", "third", "gap", "cells"), THIRD_FALLBACK_CASES)
def test_third_party_fallback_order(  # noqa: PLR0917 - pytest 參數化
    field_library: ContentLibrary,
    template: MapDef,
    length: int,
    east: int,
    north: int,
    third: int,
    gap: int | None,
    cells: list[XY] | None,
) -> None:
    """第三方排不出來時照「地形放不下」的順序：規定的距離 → 另一個 → 隔 1 格 → 退回模板；
    雙方退到隔 1 格時第三方也照樣離我方至少隔 2 格（6E-3c）；第三方離敵方帶頭的比離主角近
    （6E-3d）。"""
    found = cut_battlefield(
        field_library,
        _corridor(length, east, north),
        ally_at=(19, 15),
        enemy_at=(20, 15),
        counts=UnitCounts(allies=3, enemies=3, third=third),
        first=None,
        template=template,
        came_from=(18, 15),
    )
    if gap is None:
        assert found == "zones"
        return
    assert not isinstance(found, str), found
    battle, info = found
    assert info.gap == gap
    zone = battle.start_zones[Team.THIRD]
    assert list(zone) == [(x - info.x, y - info.y) for x, y in cells or []]
    assert min(_dist(c, a) for c in zone for a in battle.start_zones[Team.ALLY]) >= 3
    assert _third_on_enemy_side(battle)


def _pocket(west: int) -> FieldMapDef:
    """敵方 (20, 15) 東邊（x ≥ 21）全空；西邊只有第 15 列從接觸點 (19, 15) 往西共 ``west`` 格的
    死巷，其他都是牆。主角從西邊 (18, 15) 走來。"""
    rows = [list("#" * 30) for _ in range(30)]
    for x in range(20 - west, 21):
        rows[15][x] = "."
    for y in range(30):
        for x in range(21, 30):
            rows[y][x] = "."
    return _open(rows=["".join(r) for r in rows])


# (西邊死巷幾格, 先手, 隔幾格＝None 退回模板, 主角的實地格子)
OTHER_SIDE_CASES: list[tuple[int, Team | None, int | None, XY | None]] = [
    (4, None, 3, (16, 15)),  # 退得到規定的距離
    (4, Team.ALLY, 2, (17, 15)),
    # 隔 3 格在這一側放不下：東邊隔 3 格的格子離接觸點比離敵方遠（另一側）→ 照順序試隔 2 格
    (3, None, 2, (17, 15)),
    (2, None, 1, (18, 15)),  # 隔 3、2 都只剩另一側 → 隔 1 格
    (2, Team.ALLY, 1, (18, 15)),
    (1, None, None, None),  # 連隔 1 格都只剩另一側 → 退回模板（不會擺到敵方另一側）
    (1, Team.ALLY, None, None),
]


@pytest.mark.parametrize(("west", "first", "gap", "hero"), OTHER_SIDE_CASES)
def test_hero_not_placed_on_the_other_side(  # noqa: PLR0917 - pytest 參數化
    field_library: ContentLibrary,
    template: MapDef,
    west: int,
    first: Team | None,
    gap: int | None,
    hero: XY | None,
) -> None:
    """21.10 第 26 條細節（6E-3c）：主角不能被擺到敵方帶頭的另一側（離接觸點不能比離敵方帶頭的
    遠）；符合距離的格子都在另一側時照「地形放不下」的順序試下一個距離。"""
    found = cut_battlefield(
        field_library,
        _pocket(west),
        ally_at=(19, 15),
        enemy_at=(20, 15),
        counts=COUNTS,
        first=first,
        template=template,
        came_from=(18, 15),
    )
    if gap is None:
        assert found == "zones"
        return
    assert not isinstance(found, str), found
    battle, info = found
    assert info.gap == gap
    assert hero is not None
    assert battle.start_zones[Team.ALLY][0] == (hero[0] - info.x, hero[1] - info.y)
    assert _dist(hero, (19, 15)) <= _dist(hero, (20, 15))


@pytest.mark.parametrize("first", [Team.ALLY, Team.ENEMY, None])
def test_hero_side_ignores_enemy_facing(
    field_library: ContentLibrary, template: MapDef, first: Team | None
) -> None:
    """6E-3b 的「不擺在背後半邊」已撤回：從背後碰到時主角照舊往回退，留在自己這一側（隊友也照
    6C-2 的排序在這一側）。"""
    battle, info = _placed(
        field_library,
        _open(),
        template,
        ally_at=(15, 15),
        enemy_at=(16, 15),
        first=first,
        came_from=(14, 15),
    )
    hero = (13, 15) if first is Team.ALLY else (12, 15)
    assert battle.start_zones[Team.ALLY][0] == (hero[0] - info.x, hero[1] - info.y)
    leader = (16 - info.x, 15 - info.y)
    contact = (15 - info.x, 15 - info.y)
    assert all(_dist(c, contact) < _dist(c, leader) for c in battle.start_zones[Team.ALLY])


# ---------------------------------------------------------------------------
# 不合法就退回模板
# ---------------------------------------------------------------------------


def _walled_pocket() -> list[str]:
    """(15, 15) 被牆圍在只有 2 格的小角落裡（往東 (16, 15) 也是口袋），其他地方空曠。"""
    rows = [list("." * 30) for _ in range(30)]
    for x, y in ((14, 15), (15, 14), (16, 14), (17, 15), (15, 16), (16, 16)):
        rows[y][x] = "#"
    return ["".join(r) for r in rows]


def _split() -> list[str]:
    """第 15 欄是深淵（走不過去）。"""
    return ["." * 15 + "~" + "." * 14 for _ in range(30)]


@pytest.mark.parametrize(
    ("field", "ally", "enemy", "reason"),
    [
        (_open((11, 20)), (5, 5), (6, 5), "too_small"),  # 寬不到 12
        (_open((20, 11)), (5, 5), (6, 5), "too_small"),  # 高不到 12
        (_open(rows=_walled_pocket()), (15, 15), (13, 15), "zones"),  # 我方只有 2 格可站
        (_open(rows=_split()), (13, 15), (17, 15), "check_map"),  # 隔著深淵：走不到對方
    ],
)
def test_illegal_cut_falls_back(  # noqa: PLR0917 - pytest 參數化
    field_library: ContentLibrary,
    template: MapDef,
    field: FieldMapDef,
    ally: XY,
    enemy: XY,
    reason: str,
) -> None:
    found = cut_battlefield(
        field_library,
        field,
        ally_at=ally,
        enemy_at=enemy,
        counts=COUNTS,
        first=None,
        template=template,
    )
    assert found == reason
    assert reason in FALLBACK_ZH


def test_cut_is_deterministic(field_library: ContentLibrary, template: MapDef) -> None:
    field = _open(rows=_walled_pocket())
    runs = [_cut(field_library, field, template, (10, 20), (12, 17)) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


# ---------------------------------------------------------------------------
# 接上遭遇：哪些時候用模板
# ---------------------------------------------------------------------------


def _encounter(library: ContentLibrary, **contact: Any) -> EncounterResult:
    data: dict[str, Any] = {
        "map": "ferry_steps",
        "spawn": 0,
        "group": "bandit_raiders",
        "lineup_seed": 1,
        "x": 5,
        "y": 6,
        "retreat_to": FieldPos(map="ferry_steps", x=1, y=6),
        "enemy_at": (6, 6),
    }
    data.update(contact)
    return EncounterResult(
        region="cloud_ridge",
        location="ferry_steps",
        level=1,
        battle_map=None,
        battle_seed=7,
        weather="clear",
        day_phase="day",
        at=NOON,
        contact=FieldContact.model_validate(data),
    )


def test_contact_battlefield_cases(guard_lib: ContentLibrary) -> None:
    encounter = _encounter(guard_lib)
    template = encounter_map(guard_lib, encounter)
    cut = contact_battlefield(guard_lib, encounter, template, COUNTS, None)
    assert cut.cut is not None and cut.fallback is None
    assert (cut.cut.field_map, cut.cut.x, cut.cut.y, cut.cut.width) == ("ferry_steps", 0, 0, 12)
    plain = encounter.model_copy(update={"contact": None})
    assert contact_battlefield(guard_lib, plain, template, COUNTS, None).map == template
    old = _encounter(guard_lib, enemy_at=None)  # 6C-2 以前的存檔
    found = contact_battlefield(guard_lib, old, template, COUNTS, None)
    assert (found.map, found.cut, found.fallback) == (template, None, "no_enemy_at")
    boss = template.model_copy(update={"archetype": "boss"})
    assert contact_battlefield(guard_lib, encounter, boss, COUNTS, None).fallback == "boss"
    if template.supports_objective("escape"):
        escape = encounter.model_copy(update={"objective": "escape"})
        found = contact_battlefield(guard_lib, escape, template, COUNTS, None)
        assert found.fallback == "objective"
    gone = _encounter(guard_lib, map="no_such_field")
    assert contact_battlefield(guard_lib, gone, template, COUNTS, None).fallback == "no_field"


@pytest.fixture(scope="module")
def guard_lib(field_library: ContentLibrary) -> ContentLibrary:
    return _library(field_library, _steps_map([GUARD]))


def _narrow_map() -> FieldMapDef:
    """同渡口石階的小地圖，但只有 11 格寬（切不出 12×12 → 退回模板）。"""
    rows = ["#" * 11, *("#" + "." * 9 + "#" for _ in range(11)), "#" * 11]
    rows[6] = "." + rows[6][1:]
    base = _steps_map([GUARD])
    data = base.model_dump(mode="json")
    data.update({"size": [11, 13], "heights": _grid(["0" * 11] * 13), "terrain": _grid(rows)})
    return FieldMapDef.model_validate(data)


@pytest.fixture(scope="module")
def narrow_lib(field_library: ContentLibrary) -> ContentLibrary:
    found = FieldMapDef.model_validate(_narrow_map().model_dump())
    return _library(field_library, found)


def _touch(library: ContentLibrary, **updates: Any) -> tuple[Any, CharacterState, list[Any]]:
    """從入口 (1, 6) 往東走到駐守 (6, 6) 背後的相鄰格開打（我方先手）。"""
    seed = _seed_facing(GUARD, "e")
    start = _char(library, (1, 6), field_visit=_visit(seed), mercenaries=PARTY, **updates)
    world, live, entries = _play(
        library, start, [_walk((2, 6), (3, 6), (4, 6), (5, 6))], make_world()
    )
    assert live.pending_encounter is not None and live.pending_encounter.contact is not None
    return world, live, [start, entries]


def test_prepare_battle_uses_the_cut(guard_lib: ContentLibrary) -> None:
    _world, live, _ = _touch(guard_lib)
    prepared = prepare_battle(guard_lib, live)
    assert prepared.field_cut is not None and prepared.cut_fallback is None
    battle = prepared.setup.map
    field = guard_lib.field_maps["ferry_steps"]
    assert battle.region == "cloud_ridge"
    assert battle.height_rows() == [r[:12] for r in field.height_rows()[:12]]
    assert battle.terrain_rows() == [r[:12] for r in field.terrain_rows()[:12]]
    assert live.pending_encounter is not None and live.pending_encounter.contact is not None
    assert live.pending_encounter.contact.came_from == (4, 6)  # 從西邊走過來
    assert prepared.field_cut.gap == 2  # 從背後碰到（我方先手）：隔 2 格
    assert live.pending_encounter.contact.enemy_facing == "e"
    # 6E-3c：撤回「不擺在背後半邊」，照舊往回退 2 格到 (3, 6)（在自己這一側）
    assert battle.start_zones[Team.ALLY][0] == (3, 6)
    assert battle.start_zones[Team.ENEMY][0] == (6, 6)  # 駐守站在原地
    opening = begin_battle(prepared.setup, prepared.seed)
    hero = next(u for u in opening.state.units.values() if u.team is Team.ALLY)
    assert (hero.pos.x, hero.pos.y) == (3, 6)
    assert prepare_battle(guard_lib, live) == prepared  # 確定性


def test_old_save_without_enemy_at_uses_template(guard_lib: ContentLibrary) -> None:
    _world, live, _ = _touch(guard_lib)
    encounter = live.pending_encounter
    assert encounter is not None and encounter.contact is not None
    contact = encounter.contact.model_copy(update={"enemy_at": None})
    old = live.model_copy(
        update={"pending_encounter": encounter.model_copy(update={"contact": contact})}
    )
    prepared = prepare_battle(guard_lib, loads_char(dumps_char(old)))
    assert prepared.field_cut is None and prepared.cut_fallback == "no_enemy_at"
    assert prepared.setup.map == encounter_map(guard_lib, encounter)


# ---------------------------------------------------------------------------
# 戰後回到哪（Q8，21.10 第 7 條）與重播
# ---------------------------------------------------------------------------


def _battle_replays(prepared: Any, steps: Any) -> None:
    """戰鬥重播：同一份設定（含切出來的地圖）與步驟重算兩次，最終狀態逐位元相同。"""
    first, _ = _run(prepared, steps)
    opening = begin_battle(prepared.setup, prepared.seed)
    state = opening.state
    for step in steps:
        state = apply_step(state, step).state
    assert state == first
    copied = type(prepared.setup).model_validate_json(prepared.setup.model_dump_json())
    assert copied.map == prepared.setup.map  # 設定帶著切出來的 MapDef


@pytest.mark.parametrize(("lib_name", "cut"), [("guard_lib", True), ("narrow_lib", False)])
def test_fight_and_replay(request: pytest.FixtureRequest, lib_name: str, cut: bool) -> None:
    """就地開打一場、退回模板一場：打贏站在接觸點，世界日誌重播與戰鬥重播都一致。"""
    library: ContentLibrary = request.getfixturevalue(lib_name)
    world, live, (start, entries) = _touch(library, level=3)
    prepared = prepare_battle(library, live)
    assert (prepared.field_cut is not None) is cut
    assert prepared.cut_fallback == (None if cut else "too_small")
    steps = auto_steps(library, live)
    _battle_replays(prepared, steps)
    fight = FightAction(steps=steps)
    result = world_step(library, world, live, fight, NOON + 2)
    started = next(e for e in result.events if isinstance(e, BattleStartedEvent))
    assert (started.field_cut is not None) is cut
    assert started.battle_map == prepared.setup.map.id
    assert next(e for e in result.events if isinstance(e, BattleEndedEvent)).won
    assert result.char.field == FieldPos(map="ferry_steps", x=5, y=6, facing="e")  # 回接觸點
    entries.append(WorldLogEntry(seq=2, now=NOON + 2, character_id="alice", action=fight))
    log = read_log(dumps_log(entries))
    runs = [replay(library, make_world(), {"alice": start}, log.entries) for _ in range(2)]
    assert all(dumps_char(r.characters["alice"]) == dumps_char(result.char) for r in runs)
    assert all(r.world == result.world for r in runs)


def test_retreat_from_cut_returns_to_entrance(guard_lib: ContentLibrary) -> None:
    world, live, _ = _touch(guard_lib)
    assert prepare_battle(guard_lib, live).field_cut is not None
    back = world_step(guard_lib, world, live, RetreatAction(), NOON + 2).char
    assert back.pending_encounter is None
    assert back.field == FieldPos(map="ferry_steps", x=1, y=6, facing="e")  # 這張地圖的入口


# ---------------------------------------------------------------------------
# 正式內容：每一隊至少一個接觸點
# ---------------------------------------------------------------------------


def _contacts(library: ContentLibrary) -> list[tuple[FieldMapDef, int, XY, XY]]:
    """每張室外圖的每一隊：駐守點（巡邏的每個轉折點）四方向相鄰、站得上去的格子。"""
    rules = library.ruleset
    out: list[tuple[FieldMapDef, int, XY, XY]] = []
    for map_id in sorted(library.field_maps):
        field = library.field_maps[map_id]
        if field.is_interior or not field.spawns:
            continue
        passable = passable_grid(field, rules.terrain.by_id(), rules.objects.by_id())
        for index, spawn in enumerate(field.spawns):
            for ex, ey in dict.fromkeys((spawn.at, *spawn.patrol)):
                for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    ax, ay = ex + dx, ey + dy
                    if field.in_bounds(ax, ay) and passable[ay][ax]:
                        out.append((field, index, (ex, ey), (ax, ay)))
    return out


CONTENT_FALLBACKS: list[tuple[str, int, XY, XY, str, str]] = []
"""正式內容裡退回模板的接觸點（6E-3 開打距離之後重新驗證；寫在 6E-3 報告；6E-3b、6E-3c 仍是
0 個）。"""

CONTENT_THIRD_CUTS = 56
"""其中三方混戰的次數（第三方起始區都離我方至少隔 2 格，6E-3b；6E-3c 永遠隔 2 格）。"""

CONTENT_OTHER_GAP: list[tuple[str, int, XY, XY, str, int]] = [
    # 丹爐洞第 2 隊從南邊 (12, 12) 碰到（背後是牆）：隔 3 格的格子都在另一側 → 隔 2 格（6E-3c）
    ("elixir_cave", 1, (12, 11), (12, 12), "none", 2),
]
"""正式內容裡沒用規定距離的接觸點（主角不擺到敵方另一側之後，照順序改試下一個距離）。"""


@pytest.fixture(scope="module")
def content_library() -> ContentLibrary:
    """完整的正式內容（不換凍結的測試地圖）。"""
    return load_library()


_FACING_OF: dict[XY, Facing] = {(0, -1): "n", (1, 0): "e", (0, 1): "s", (-1, 0): "w"}


def _contact_facing(enemy: XY, ally: XY, first: Team | None) -> Facing:
    """接觸時敵方帶頭的朝向（照先手的定義）：我方先手＝背對主角（主角在背後）；沒有先手＝主角在正
    側面（朝向轉 90°）。6E-3c 起朝向不再影響擺位，照舊寫進接觸資料。"""
    away = (enemy[0] - ally[0], enemy[1] - ally[1])
    if first is Team.ALLY:
        return _FACING_OF[away]
    return _FACING_OF[(-away[1], away[0])]


def test_every_content_spawn_cuts(content_library: ContentLibrary) -> None:
    """正式內容每一隊的每個相鄰接觸點（四方向、筆直走過來），我方先手與沒有先手各切一次：都切得出
    合法的 12×12、隔的格數照規則（6C-2 輔助，6E-3 重新驗證）。退回模板的清單＝
    ``CONTENT_FALLBACKS``。"""
    library = content_library
    covered: set[tuple[str, int]] = set()
    fallbacks: list[tuple[str, int, XY, XY, str, str]] = []
    gaps: dict[tuple[str, int | None], int] = {}
    odd: list[tuple[str, int, XY, XY, str, int]] = []
    third = 0
    for (field, index, enemy, ally), first in (
        (c, f) for c in _contacts(library) for f in (Team.ALLY, None)
    ):
        spawn = field.spawns[index]
        place = library.world_maps[field.region].location_by_id()[field.place]
        encounter = EncounterResult(
            region=field.region,
            location=field.place,
            level=1,
            battle_map=place.battle_maps[0] if place.battle_maps else None,
            battle_seed=0,
            weather="clear",
            day_phase="day",
            at=NOON,
            contact=FieldContact(
                map=field.id,
                spawn=index,
                group=spawn.group,
                lineup_seed=0,
                x=ally[0],
                y=ally[1],
                retreat_to=FieldPos(map=field.id, x=field.entry[0], y=field.entry[1]),
                came_from=(2 * ally[0] - enemy[0], 2 * ally[1] - enemy[1]),
                enemy_at=enemy,
                enemy_facing=_contact_facing(enemy, ally, first),
            ),
        )
        lineup = roll_lineup(library, encounter)
        counts = UnitCounts(allies=3, enemies=len(lineup.members), third=len(lineup.third))
        template = encounter_map(library, encounter)
        found = contact_battlefield(library, encounter, template, counts, first)
        covered.add((field.id, index))
        side = "ally" if first is Team.ALLY else "none"
        if found.fallback is not None:
            fallbacks.append((field.id, index, enemy, ally, side, found.fallback))
            continue
        assert found.cut is not None and found.cut.gap is not None
        key = (side, found.cut.gap)
        gaps[key] = gaps.get(key, 0) + 1
        if found.cut.gap != (2 if first is Team.ALLY else 3):
            odd.append((field.id, index, enemy, ally, side, found.cut.gap))
        if lineup.third:
            third += 1
            zone = found.map.start_zones[Team.THIRD]
            near = min(_dist(c, a) for c in zone for a in found.map.start_zones[Team.ALLY])
            assert len(zone) == len(lineup.third) and near >= 3  # 第三方離我方至少隔 2 格
            assert _third_on_enemy_side(found.map)  # 第三方在敵方那一側（6E-3d）
    spawns = {
        (f.id, i)
        for f in library.field_maps.values()
        if not f.is_interior
        for i in range(len(f.spawns))
    }
    assert covered == spawns
    # 6E-3c 驗收：267 個接觸點 × 兩種先手；只有 1 個改用另一個距離
    assert gaps == {("ally", 2): 267, ("none", 3): 266, ("none", 2): 1}
    assert odd == CONTENT_OTHER_GAP
    assert third == CONTENT_THIRD_CUTS
    assert fallbacks == CONTENT_FALLBACKS
