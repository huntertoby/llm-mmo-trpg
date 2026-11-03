"""就地開打：從實地地圖切 12×12 戰場（Phase 6C-2；21.4、21.9 第 6 條、21.10 第 4、7 條）。

- **切法**：以「我方接觸點與那一隊所在格的中點」（捨去小數）為中心切規則 ``field.cut_size``
  見方（12×12）；靠邊時往內平移，不超出實地地圖。地形、高低差、物件、表面照實地地圖；``region`` 由呼叫端換皮（``reskin``
  照舊），勝利條件一律全滅，``archetype``、``tags``、``weather`` 照地點原本的戰鬥地圖模板。
- **起始區**：我方從接觸點、敵方從那一隊所在格起算，只取走得到的格子；排序＝（在自己這一側優先：
  離自己的起點比離對方近 → 等距 → 比較近對方）、離自己起點的曼哈頓距離、y、x。所以主角站在接觸點、
  敵方帶頭的站在地圖上看到的位置。至少敵方 ``field.min_enemy_cells`` 格、我方
  ``field.min_ally_cells`` 格（單位比較多時照單位數）。先手的那一方先挑（同一格時歸先手方；沒有先手照敵方先挑）。第三方不另畫
  起始區（引擎自動排在敵方附近），但要留得出位置。
- **不合法就退回模板**（:data:`~trpg.world.actions.CutFallback`）：實地地圖不到 12×12、起點不可站、
  站位放不下、``check_map`` 沒過；另外 Boss 地圖、遭遇指定了模板才有的撤離／守點、接觸資料沒有敵人
  位置（6C-2 以前的存檔）時也用模板。

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
from trpg.world.state import EncounterResult, FieldContact

__all__ = [
    "FALLBACK_ZH",
    "Battlefield",
    "UnitCounts",
    "contact_battlefield",
    "cut_battlefield",
    "cut_origin",
]

type XY = tuple[int, int]

FALLBACK_ZH: Final[dict[CutFallback, str]] = {
    "no_field": "找不到實地地圖",
    "no_enemy_at": "舊存檔的遭遇沒有敵人位置",
    "boss": "Boss 戰用專屬地圖",
    "objective": "這場的勝利條件只有原本的戰場有",
    "too_small": "地圖不到 12×12",
    "zones": "站位放不下",
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


def _zones(
    library: ContentLibrary,
    probe: MapDef,
    anchors: tuple[XY, XY],
    counts: UnitCounts,
    ally_first: bool,
) -> dict[str, list[list[int]]] | None:
    """我方、敵方起始區；放不下＝``None``。``anchors``＝（我方起點, 敵方起點）（切出來的座標）。"""
    ally_at, enemy_at = anchors
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
        ally = _pick(ally_cells, ally_at, enemy_at, need_ally, set())
        enemy = _pick(enemy_cells, enemy_at, ally_at, need_enemy, set(ally))
    else:
        enemy = _pick(enemy_cells, enemy_at, ally_at, need_enemy, set())
        ally = _pick(ally_cells, ally_at, enemy_at, need_ally, set(enemy))
    if len(ally) < need_ally or len(enemy) < need_enemy:
        return None
    free = sum(1 for row in passable for ok in row if ok) - len(ally) - len(enemy)
    if free < counts.third:  # 第三方由引擎排在敵方附近，要留得出位置
        return None
    return {"ally": [list(c) for c in ally], "enemy": [list(c) for c in enemy]}


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
) -> tuple[MapDef, BattlefieldCut] | CutFallback:
    """從 ``field`` 切出戰場（見模組說明）；不合法時回傳退回模板的原因。``ally_at``、``enemy_at``
    是實地地圖的格子；``first`` 是先手（``Team.ALLY``＝我方先挑起始格）。"""
    cut = rules_of(library).field.cut_size
    if field.width < cut or field.height < cut:
        return "too_small"
    center = ((ally_at[0] + enemy_at[0]) // 2, (ally_at[1] + enemy_at[1]) // 2)
    x0, y0 = cut_origin(center, field.size, cut)
    name = name_zh or field.name_zh or template.name_zh
    data = _window_data(field, ((x0, y0), cut), template, name)
    probe = MapDef.model_validate({**data, "start_zones": {"ally": [[0, 0]], "enemy": [[0, 1]]}})
    anchors = ((ally_at[0] - x0, ally_at[1] - y0), (enemy_at[0] - x0, enemy_at[1] - y0))
    zones = _zones(library, probe, anchors, counts, first is Team.ALLY)
    if zones is None:
        return "zones"
    battle = MapDef.model_validate({**data, "start_zones": zones})
    rules = library.ruleset
    if check_map(battle, rules.terrain.by_id(), rules.core, rules.objects.by_id()):
        return "check_map"
    return battle, BattlefieldCut(field_map=field.id, x=x0, y=y0, width=cut, height=cut)


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
    )
    if isinstance(cut, str):
        return Battlefield(map=template, fallback=cut)
    battle, info = cut
    return Battlefield(map=battle, cut=info)
