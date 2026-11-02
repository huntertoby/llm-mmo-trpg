"""遭遇的敵方陣容（Phase 5A-3；``docs/phases/Phase5計畫.md`` 7.2 第 5 項）。

5A-2 的遇敵只產生 :class:`~trpg.world.state.EncounterResult`（地點、地圖、戰鬥種子…）；本模組依
該地點的遭遇表（``content/world/encounters/``）抽出敵方陣容，並把陣容解析成可以直接放進戰鬥的
單位範本。不開戰（開戰在 5A-4）。

亂數（代決 5A3-6）：``Rng(fnv1a64(f"{battle_seed}:lineup"))``。``battle_seed`` 已經由世界的
``battle`` 串流衍生，所以同一個 ``EncounterResult`` 一定得到相同陣容，不動角色的亂數計數。

規則（09 9.6.6）：

1. 依權重抽陣容。
2. 精英巢穴：固定精英（單位＋詞綴）放在第一個。
3. 一般營地（``camp``）而且陣容沒有精英：``randint(0, 999) < camp_elite_permille`` 時，從可以套用
   本區某個詞綴的成員中均勻抽 1 名，再從可以套用的詞綴中均勻抽 1 個，把它升級成精英——不增加
   人數、不加等級（「強度以建議等級為準、一場最多 1 名」）。其他地點種類不混精英。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_encounters import EncounterGroupDef, EncounterTable, LocationEncounters
from trpg.content.world_enemies import EnemyCatalog
from trpg.shared.rng import Rng, fnv1a64
from trpg.world.errors import WorldError
from trpg.world.state import EncounterResult

__all__ = [
    "EncounterLineup",
    "LineupMember",
    "lineup_rng",
    "lineup_templates",
    "roll_lineup",
]


class LineupMember(BaseModel):
    """陣容的一名成員：單位範本或變體 ID，以及套上的精英詞綴（沒有＝``None``）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit: str = Field(pattern=ID_PATTERN)
    affix: str | None = Field(default=None, pattern=ID_PATTERN)


class EncounterLineup(BaseModel):
    """一場遭遇的敵方陣容（5A-4 開戰前顯示給玩家看，可撤退；9.6.6）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    region: str
    location: str
    group: str
    """抽到的陣容 ID（遭遇表的 ``groups``）。"""
    members: tuple[LineupMember, ...] = Field(min_length=1)

    @property
    def has_elite_affix(self) -> bool:
        return any(m.affix is not None for m in self.members)


def lineup_rng(battle_seed: int) -> Rng:
    """陣容用的亂數：``fnv1a64("{battle_seed}:lineup")``。"""
    return Rng(fnv1a64(f"{battle_seed}:lineup".encode()))


def roll_lineup(library: ContentLibrary, encounter: EncounterResult) -> EncounterLineup:
    """依遭遇表抽出 ``encounter`` 的敵方陣容（確定性；規則見模組說明）。"""
    table = library.world_encounters.get(encounter.region)
    if table is None:
        raise WorldError(f"區域 {encounter.region} 沒有遭遇表")
    entry = table.location_by_id().get(encounter.location)
    if entry is None:
        raise WorldError(f"地點 {encounter.location} 沒有遭遇表")
    world_map = library.world_maps[encounter.region]
    kind = world_map.location_by_id()[encounter.location].kind
    rng = lineup_rng(encounter.battle_seed)
    group = _pick_group(rng, table, entry)
    members = [LineupMember(unit=u) for u in group.units]
    catalog = library.enemy_catalog()
    if entry.elite is not None:
        members.insert(0, LineupMember(unit=entry.elite.unit, affix=entry.elite.affix))
    elif kind == "camp":
        members = _maybe_mix_elite(rng, table, catalog, members)
    return EncounterLineup(
        region=encounter.region,
        location=encounter.location,
        group=group.id,
        members=tuple(members),
    )


def lineup_templates(library: ContentLibrary, lineup: EncounterLineup) -> tuple[UnitTemplate, ...]:
    """把陣容解析成單位範本（變體已套用、精英詞綴已套用），依陣容順序。"""
    catalog = library.enemy_catalog()
    result: list[UnitTemplate] = []
    for member in lineup.members:
        template = catalog.template(member.unit)
        if member.affix is not None:
            template = catalog.with_affix(template, member.affix)
        result.append(template)
    return tuple(result)


def _pick_group(rng: Rng, table: EncounterTable, entry: LocationEncounters) -> EncounterGroupDef:
    total = sum(g.weight for g in entry.groups)
    roll = rng.randint(0, total - 1)
    for weighted in entry.groups:
        if roll < weighted.weight:
            return table.group_by_id()[weighted.group]
        roll -= weighted.weight
    raise AssertionError("權重總和計算錯誤")  # pragma: no cover


def _maybe_mix_elite(
    rng: Rng, table: EncounterTable, catalog: EnemyCatalog, members: list[LineupMember]
) -> list[LineupMember]:
    """一般營地有機率把 1 名成員升級成精英（陣容已有精英時不混）。亂數照固定順序消耗。"""
    templates = [catalog.template(m.unit) for m in members]
    if any(catalog.is_elite(t) for t in templates):
        return members
    roll = rng.randint(0, 999)
    if roll >= table.camp_elite_permille:
        return members
    options = [(i, catalog.applicable_affixes(t, table.affixes)) for i, t in enumerate(templates)]
    eligible = [(i, affixes) for i, affixes in options if affixes]
    if not eligible:
        return members
    index, affixes = eligible[rng.randint(0, len(eligible) - 1)]
    affix = affixes[rng.randint(0, len(affixes) - 1)]
    upgraded = list(members)
    upgraded[index] = members[index].model_copy(update={"affix": affix})
    return upgraded
