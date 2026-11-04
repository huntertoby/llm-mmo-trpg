"""就地開打：從實地地圖切 12×12 戰場（Phase 6C-2；21.4、21.9 第 6 條、21.10 第 4、7 條）。

- **開打距離**（6E-3，#124，21.10 第 26 條）：雙方最近兩單位之間隔 N 個空格（曼哈頓距離 N＋1，
  不看高低差）；我方先手 ``field.gap_ally_first``（2），敵方先手或沒有先手
  ``field.gap_other``（3）。
  敵方帶頭的留在地圖上看到的位置；主角從接觸點沿走來的方向（``FieldContact.came_from``）往回退到
  符合距離的格子，退不了就在走得到、符合距離的格子裡挑最靠近接觸點的。放不下時依序試另一個距離、
  再試 ``field.gap_fallback``（1），都不行才退回模板。
- **切法**：以「主角與那一隊帶頭的中點」（捨去小數）為中心切規則 ``field.cut_size`` 見方
  （12×12）；靠邊時往內平移，不超出實地地圖。地形、高低差、物件、表面照實地地圖；``region``
  由呼叫端換皮（``reskin`` 照舊），勝利條件一律全滅，``archetype``、``tags``、``weather`` 照地點
  原本的戰鬥地圖模板。
- **起始區**：我方從主角、敵方從那一隊帶頭的格子起算，只取走得到的格子；排序＝（在自己這一側優先：
  離自己的起點比離對方近 → 等距 → 比較近對方）、離自己起點的曼哈頓距離、y、x，並且雙方起始區的
  每一格都至少隔 N 格（部署時怎麼挑都不會更近）。所以主角、敵方帶頭的各站在自己的起點。至少敵方
  ``field.min_enemy_cells`` 格、我方 ``field.min_ally_cells`` 格（單位比較多時照單位數）。先手的
  那一方先挑（沒有先手照敵方先挑）。
- **第三方**（6E-3b，21.10 第 26 條細節）：三方混戰時世界層另畫第三方起始區（不靠引擎自動排）：
  走得到、不在雙方起始區、離我方起始區每一格至少隔 ``field.gap_third``（2）格（這次試的距離比它小
  時照這次的距離）的格子，照引擎原本的排法（離敵方起始區最近, y, x）取單位數那麼多格；排不出來＝
  這個距離放不下，照順序試下一個。
- **主角的方向**（6E-3b，21.10 第 10、26 條）：主角不能擺在敵方帶頭單位朝向的背後半邊（往前 < 0；
  正側面可以）。往回退到的格子在背後就改挑符合距離、不在背後、最靠近接觸點的格子；全在背後＝這個
  距離放不下。舊資料沒有朝向（``FieldContact.enemy_facing``）時不限方向。
- **不合法就退回模板**（:data:`~trpg.world.actions.CutFallback`）：實地地圖不到 12×12、接觸點
  不可站、
  三種距離都放不下（``zones``）、``check_map`` 沒過；另外 Boss 地圖、遭遇指定了模板才有的撤離／
  守點、接觸資料沒有敵人位置（6C-2 以前的存檔）時也用模板。

確定性：只依內容與遭遇資料計算，不耗亂數；所有集合都排序後才取（守則 2）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.maps import BOSS_ARCHETYPE, MapDef, check_map, passable_grid, reachable_from
from trpg.shared.types import Team
from trpg.world.actions import BattlefieldCut, CutFallback
from trpg.world.common import rules_of
from trpg.world.state import EncounterResult, Facing, FieldContact

__all__ = [
    "FALLBACK_ZH",
    "Battlefield",
    "UnitCounts",
    "contact_battlefield",
    "cut_battlefield",
    "cut_origin",
]

type XY = tuple[int, int]

_FACING_VECTORS: Final[dict[Facing, XY]] = {"n": (0, -1), "e": (1, 0), "s": (0, 1), "w": (-1, 0)}

FALLBACK_ZH: Final[dict[CutFallback, str]] = {
    "no_field": "找不到實地地圖",
    "no_enemy_at": "舊存檔的遭遇沒有敵人位置",
    "boss": "Boss 戰用專屬地圖",
    "objective": "這場的勝利條件只有原本的戰場有",
    "too_small": "地圖不到 12×12",
    "zones": "站位放不下（隔 3、2、1 格都試過）",
    "check_map": "切出來的戰場不合法",
}
"""退回模板的原因（畫面與報告用）。"""


@dataclass(frozen=True)
class UnitCounts:
    """這場的單位數（決定起始區要幾格）。"""

    allies: int
    enemies: int
    third: int = 0


@dataclass(frozen=True)
class Battlefield:
    """開戰用的戰鬥地圖：切出來的（``cut`` 有值）或模板（``cut`` 為 ``None``）。``fallback`` 是碰到
    地圖上的敵人卻退回模板的原因（不是地圖上碰到的遭遇＝``None``）。"""

    map: MapDef
    cut: BattlefieldCut | None = None
    fallback: CutFallback | None = None


def cut_origin(center: XY, size: XY, cut: int) -> XY:
    """以 ``center`` 為中心的 ``cut``×``cut`` 左上角；越過地圖邊緣就往內推（地圖不夠大時貼 0）。"""
    w, h = size
    x0 = min(max(center[0] - cut // 2, 0), max(w - cut, 0))
    y0 = min(max(center[1] - cut // 2, 0), max(h - cut, 0))
    return x0, y0


def _manhattan(a: XY, b: XY) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _side_key(own: XY, other: XY) -> Callable[[XY], tuple[int, int, int, int]]:
    """起始區的排序：自己這一側優先、離自己起點近、y、x。"""

    def key(cell: XY) -> tuple[int, int, int, int]:
        mine, theirs = _manhattan(cell, own), _manhattan(cell, other)
        side = 0 if mine < theirs else (1 if mine == theirs else 2)
        return (side, mine, cell[1], cell[0])

    return key


def _pick(cells: set[XY], own: XY, other: XY, count: int, taken: set[XY]) -> list[XY]:
    ordered = sorted((c for c in cells if c not in taken), key=_side_key(own, other))
    return ordered[:count]


def _window_data(
    field: FieldMapDef, window: tuple[XY, int], template: MapDef, name_zh: str
) -> dict[str, Any]:
    (x0, y0), cut = window
    rows = range(y0, y0 + cut)
    heights = "\n".join(field.height_rows()[y][x0 : x0 + cut] for y in rows)
    terrain = "\n".join(field.terrain_rows()[y][x0 : x0 + cut] for y in rows)
    used = sorted({ch for line in terrain.splitlines() for ch in line})

    def inside(at: XY) -> bool:
        return x0 <= at[0] < x0 + cut and y0 <= at[1] < y0 + cut

    def shift(at: XY) -> list[int]:
        return [at[0] - x0, at[1] - y0]

    return {
        "id": f"cut_{field.id}_{x0}_{y0}",
        "name_zh": name_zh,
        "archetype": template.archetype,
        "size": [cut, cut],
        "heights": heights,
        "terrain": terrain,
        "legend": {ch: field.legend[ch] for ch in used},
        "objects": [{"at": shift(o.at), "kind": o.kind} for o in field.objects if inside(o.at)],
        "surfaces": [
            {"at": shift(s.at), "surface": s.surface.value, "duration": s.duration}
            for s in field.surfaces
            if inside(s.at)
        ],
        "weather": template.weather,
        "tags": list(template.tags),
    }


def _behind(cell: XY, enemy_at: XY, facing: Facing | None) -> bool:
    """``cell`` 在 ``enemy_at``（面向 ``facing``）的背後半邊（21.10 第 10 條：往前 < 0）；``None``＝
    不知道朝向，一律不算。"""
    if facing is None:
        return False
    fx, fy = _FACING_VECTORS[facing]
    return (cell[0] - enemy_at[0]) * fx + (cell[1] - enemy_at[1]) * fy < 0


def _third_zone(
    cells: set[XY], taken: tuple[list[XY], list[XY]], count: int, reach: int
) -> list[XY] | None:
    """第三方起始區（6E-3b）：``cells``（從敵方起點走得到的格子）裡不在雙方起始區、離我方每一格
    至少 ``reach``（曼哈頓距離）的格子，照引擎自動排的順序（離敵方起始區最近, y, x）取 ``count``
    格；不夠＝``None``。"""
    ally, enemy = taken
    used = set(ally) | set(enemy)
    found = sorted(
        (c for c in cells if c not in used and all(_manhattan(c, a) >= reach for a in ally)),
        key=lambda c: (min(_manhattan(c, e) for e in enemy), c[1], c[0]),
    )
    return found[:count] if len(found) >= count else None


def _far(cells: set[XY], others: list[XY], reach: int) -> set[XY]:
    """``cells`` 裡離 ``others`` 每一格都至少 ``reach``（曼哈頓距離）的格子。"""
    return {c for c in cells if all(_manhattan(c, o) >= reach for o in others)}


def _zones(
    library: ContentLibrary,
    probe: MapDef,
    anchors: tuple[XY, XY],
    counts: UnitCounts,
    spacing: tuple[bool, int],
) -> dict[str, list[list[int]]] | None:
    """我方、敵方起始區；放不下＝``None``。``anchors``＝（我方起點, 敵方起點）（切出來的座標）；
    ``spacing``＝（我方先挑, 雙方起始區每一格之間至少的曼哈頓距離＝隔幾格＋1，6E-3）。"""
    ally_at, enemy_at = anchors
    ally_first, reach = spacing
    rules = library.ruleset
    passable = passable_grid(probe, rules.terrain.by_id(), rules.objects.by_id())
    if not (passable[ally_at[1]][ally_at[0]] and passable[enemy_at[1]][enemy_at[0]]):
        return None
    grid = probe.grid()
    ally_cells = reachable_from(ally_at, grid, passable, rules.core)
    enemy_cells = reachable_from(enemy_at, grid, passable, rules.core)
    field_rules = rules_of(library).field
    need_ally = max(field_rules.min_ally_cells, counts.allies)
    need_enemy = max(field_rules.min_enemy_cells, counts.enemies)
    if ally_first:
        ally = _pick(_far(ally_cells, [enemy_at], reach), ally_at, enemy_at, need_ally, set())
        enemy = _pick(_far(enemy_cells, ally, reach), enemy_at, ally_at, need_enemy, set(ally))
    else:
        enemy = _pick(_far(enemy_cells, [ally_at], reach), enemy_at, ally_at, need_enemy, set())
        ally = _pick(_far(ally_cells, enemy, reach), ally_at, enemy_at, need_ally, set(enemy))
    if len(ally) < need_ally or len(enemy) < need_enemy:
        return None
    zones = {"ally": [list(c) for c in ally], "enemy": [list(c) for c in enemy]}
    if counts.third:
        third_reach = min(field_rules.gap_third + 1, reach)
        third = _third_zone(enemy_cells, (ally, enemy), counts.third, third_reach)
        if third is None:
            return None
        zones["third"] = [list(c) for c in third]
    return zones


def _sign(v: int) -> int:
    return (v > 0) - (v < 0)


@dataclass(frozen=True)
class _Approach:
    """主角怎麼擺（實地地圖的格子）：接觸點、走到接觸點的前一格（``None``＝不知道）、走得到的格子
    與一步最多往上爬幾層。"""

    contact: XY
    came_from: XY | None
    facing: Facing | None
    """敵方帶頭的朝向（主角不擺在它的背後半邊）；``None``＝不限。"""
    reach: frozenset[XY]
    grid: list[list[tuple[int, str]]]
    climb: int


def _approach(
    library: ContentLibrary,
    field: FieldMapDef,
    contact: XY,
    heading: tuple[XY | None, Facing | None],
) -> _Approach | None:
    """``heading``＝（走到接觸點的前一格, 敵方帶頭的朝向）。"""
    rules = library.ruleset
    passable = passable_grid(field, rules.terrain.by_id(), rules.objects.by_id())
    if not (field.in_bounds(*contact) and passable[contact[1]][contact[0]]):
        return None
    grid = field.grid()
    reach = frozenset(reachable_from(contact, grid, passable, rules.core))
    came_from, facing = heading
    return _Approach(contact, came_from, facing, reach, grid, rules.core.max_climb_height)


def _back_off(way: _Approach, enemy_at: XY, reach: int) -> XY | None:
    """主角站的格子（21.10 第 26 條第 2 點）：從接觸點沿走來的方向往回退，退到離敵方帶頭的
    曼哈頓距離剛好 ``reach`` 的那一格；退不了（沒有方向、撞牆、爬不上去、越退越遠還是不對）或退到的
    格子在敵方帶頭的背後半邊（6E-3b）就在走得到、距離剛好 ``reach``、不在背後半邊的格子裡挑最靠近
    接觸點的（同距離照 y、x）。都沒有＝``None``。"""

    def fits(c: XY) -> bool:
        return _manhattan(c, enemy_at) == reach and not _behind(c, enemy_at, way.facing)

    cell = way.contact
    if way.came_from is not None:
        step = (_sign(way.came_from[0] - cell[0]), _sign(way.came_from[1] - cell[1]))
        if step[0] != 0 and step[1] != 0:  # 不是四方向相鄰（不該發生）：照 x 方向退
            step = (step[0], 0)
        while step != (0, 0) and _manhattan(cell, enemy_at) < reach:
            nxt = (cell[0] + step[0], cell[1] + step[1])
            if nxt not in way.reach:
                break
            here_h = way.grid[cell[1]][cell[0]][0]
            if way.grid[nxt[1]][nxt[0]][0] - here_h > way.climb:
                break
            cell = nxt
        if fits(cell):
            return cell
    cells = [c for c in way.reach if fits(c)]
    if not cells:
        return None
    return min(cells, key=lambda c: (_manhattan(c, way.contact), c[1], c[0]))


def cut_battlefield(
    library: ContentLibrary,
    field: FieldMapDef,
    *,
    ally_at: XY,
    enemy_at: XY,
    counts: UnitCounts,
    first: Team | None,
    template: MapDef,
    name_zh: str | None = None,
    came_from: XY | None = None,
    enemy_facing: Facing | None = None,
) -> tuple[MapDef, BattlefieldCut] | CutFallback:
    """從 ``field`` 切出戰場（見模組說明）；不合法時回傳退回模板的原因。``ally_at``（接觸點）、
    ``enemy_at``、``came_from``（走到接觸點的前一格）是實地地圖的格子，``enemy_facing`` 是敵方帶頭的
    朝向（主角不擺在背後半邊；``None``＝不限）；``first`` 是先手
    （``Team.ALLY``＝我方先挑起始格、隔 ``field.gap_ally_first`` 格）。

    開打距離（6E-3，#124）：依 :meth:`~trpg.content.world_rules.FieldRules.gaps` 的順序試，每個
    距離：敵方帶頭的不動，主角照 :func:`_back_off` 擺，再以雙方帶頭的中點切 12×12、排起始區；
    都放不下才回傳 ``"zones"``（或最後一次的 ``"check_map"``）。"""
    rules = rules_of(library).field
    cut = rules.cut_size
    if field.width < cut or field.height < cut:
        return "too_small"
    way = _approach(library, field, ally_at, (came_from, enemy_facing))
    if way is None:
        return "zones"
    source = _Source(library, field, template, name_zh or field.name_zh or template.name_zh)
    ally_first = first is Team.ALLY
    reason: CutFallback = "zones"
    for gap in rules.gaps(ally_first):
        hero = _back_off(way, enemy_at, gap + 1)
        if hero is None:
            continue
        found = _cut_at(source, (hero, enemy_at), counts, (ally_first, gap))
        if not isinstance(found, str):
            return found
        if found == "check_map":
            reason = found
    return reason


@dataclass(frozen=True)
class _Source:
    library: ContentLibrary
    field: FieldMapDef
    template: MapDef
    name_zh: str


def _cut_at(
    source: _Source, anchors: tuple[XY, XY], counts: UnitCounts, spacing: tuple[bool, int]
) -> tuple[MapDef, BattlefieldCut] | CutFallback:
    """以（主角, 敵方帶頭的）的中點切一塊、隔 ``spacing[1]`` 格排起始區。"""
    library, field = source.library, source.field
    cut = rules_of(library).field.cut_size
    (ax, ay), (ex, ey) = anchors
    x0, y0 = cut_origin(((ax + ex) // 2, (ay + ey) // 2), field.size, cut)
    data = _window_data(field, ((x0, y0), cut), source.template, source.name_zh)
    probe = MapDef.model_validate({**data, "start_zones": {"ally": [[0, 0]], "enemy": [[0, 1]]}})
    local = ((ax - x0, ay - y0), (ex - x0, ey - y0))
    ally_first, gap = spacing
    zones = _zones(library, probe, local, counts, (ally_first, gap + 1))
    if zones is None:
        return "zones"
    battle = MapDef.model_validate({**data, "start_zones": zones})
    rules = library.ruleset
    if check_map(battle, rules.terrain.by_id(), rules.core, rules.objects.by_id()):
        return "check_map"
    info = BattlefieldCut(field_map=field.id, x=x0, y=y0, width=cut, height=cut, gap=gap)
    return battle, info


def _contact_fallback(
    library: ContentLibrary, encounter: EncounterResult, template: MapDef
) -> tuple[FieldContact, FieldMapDef, XY] | CutFallback:
    contact = encounter.contact
    assert contact is not None
    field = library.field_maps.get(contact.map)
    if field is None:
        return "no_field"
    if contact.enemy_at is None:
        return "no_enemy_at"
    if template.archetype == BOSS_ARCHETYPE:
        return "boss"
    if encounter.objective is not None and template.supports_objective(encounter.objective):
        return "objective"
    return contact, field, contact.enemy_at


def contact_battlefield(
    library: ContentLibrary,
    encounter: EncounterResult,
    template: MapDef,
    counts: UnitCounts,
    first: Team | None,
) -> Battlefield:
    """遭遇的戰鬥地圖（未換皮）：碰到地圖上的敵人（``encounter.contact``）就切 12×12，不合法就用
    ``template``（:func:`~trpg.world.battle.encounter_map` 選的模板）並記下原因；其他遭遇照舊用
    ``template``。"""
    if encounter.contact is None:
        return Battlefield(map=template)
    found = _contact_fallback(library, encounter, template)
    if isinstance(found, str):
        return Battlefield(map=template, fallback=found)
    contact, field, enemy_at = found
    place = library.world_maps.get(encounter.region)
    location = None if place is None else place.location_by_id().get(encounter.location)
    cut = cut_battlefield(
        library,
        field,
        ally_at=(contact.x, contact.y),
        enemy_at=enemy_at,
        counts=counts,
        first=first,
        template=template,
        name_zh=None if location is None else location.name_zh,
        came_from=contact.came_from,
        enemy_facing=contact.enemy_facing,
    )
    if isinstance(cut, str):
        return Battlefield(map=template, fallback=cut)
    battle, info = cut
    return Battlefield(map=battle, cut=info)
