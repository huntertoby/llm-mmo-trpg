"""遭遇的敵方陣容（Phase 5A-3；``docs/phases/Phase5計畫.md`` 7.2 第 5 項）。

5A-2 的遇敵只產生 :class:`~trpg.world.state.EncounterResult`（地點、地圖、戰鬥種子…）；本模組依
該地點的遭遇表（``content/world/encounters/``）抽出敵方陣容，並把陣容解析成可以直接放進戰鬥的
單位範本。不開戰（開戰在 5A-4）。

亂數（代決 5A3-6）：``Rng(fnv1a64(f"{battle_seed}:lineup"))``。``battle_seed`` 已經由世界的
``battle`` 串流衍生，所以同一個 ``EncounterResult`` 一定得到相同陣容，不動角色的亂數計數。

規則（09 9.6.6）：

1. 依權重抽陣容。實地地圖上看得見的敵人（Phase 6C-1，``EncounterResult.contact``）改用那一隊的
   ``group``，亂數改用 ``Rng(fnv1a64(f"{lineup_seed}:lineup"))``（地圖上顯示的陣容＝開戰的陣容）。
2. 精英巢穴：固定精英（單位＋詞綴）放在第一個。
3. 一般營地（``camp``）而且陣容沒有精英：``randint(0, 999) < camp_elite_permille`` 時，從可以套用
   本區某個詞綴的成員中均勻抽 1 名，再從可以套用的詞綴中均勻抽 1 個，把它升級成精英——不增加
   人數、不加等級（「強度以建議等級為準、一場最多 1 名」）。其他地點種類不混精英。

**增援**（Phase 5A-6，:func:`reinforce_lineup`；玩法 PM 定，18.4 補充「危險度 3 的增援」）：情境判定
給的每一筆 ``reinforce``，從同地點遭遇表各陣容出現過的非精英單位（去重、依 ID 排序；已到遠程上限時
不抽遠程）用 ``Rng(fnv1a64(f"{battle_seed}:reinforce"))`` 均勻抽 1 名排在陣容最後；陣容已滿
4 名（或沒有可抽的單位）時改成「敵人先手」（代決 5A6-3）。等級照地點，由開戰時一起成長。

**遭遇加人**（Phase 5B-4c，世界級線頭到期結局）：遇敵當下的世界旗標
（``EncounterResult.world_flags``）符合遭遇表 ``surges`` 的旗標、地點種類、時段時，一般抽到的陣容在
敵方最後多 1 名（混精英之後；滿 4 名不加；遭遇變化不加）。不消耗亂數。

**精英單挑**（RG-2，#162）：固定精英、懸賞、遭遇變化的 ``elite.duel`` 為真時，陣容標 ``duel``（那名
精英排最前）；提出、回應與一對一組場在 :mod:`trpg.world.duel`。不消耗亂數。

**第三方**（Phase 5B-M3 三方混戰）：陣容的 ``third`` 照順序放進 :attr:`EncounterLineup.third`（套用
等級門檻）；營地混精英、固定精英、增援只作用在敵方 ``members``（代決 5BM3-9）。不消耗亂數。
"""

from __future__ import annotations

from collections.abc import Collection

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_encounters import (
    MAX_GROUP_SIZE,
    EncounterGroupDef,
    EncounterTable,
    LocationEncounters,
)
from trpg.content.world_enemies import EnemyCatalog
from trpg.shared.rng import Rng, fnv1a64
from trpg.world.common import world_map_of
from trpg.world.errors import WorldError
from trpg.world.state import EncounterResult

__all__ = [
    "EncounterLineup",
    "LineupMember",
    "Reinforcement",
    "elite_kinds",
    "lineup_rng",
    "lineup_templates",
    "reinforce_lineup",
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
    third: tuple[LineupMember, ...] = ()
    """第三方（Phase 5B-M3 三方混戰：和我方、敵方都敵對）；舊資料沒有＝空。"""
    variant: str | None = None
    """用了哪個遭遇變化（劇情旗標；Phase 5B-4b 線頭到期結局）；``None``＝一般抽陣容。"""
    bounty: str | None = None
    """懸賞陣容（Phase 5F-1）；``None``＝不是懸賞。"""
    duel: bool = Field(default=False, exclude_if=lambda v: not v)
    """排最前的精英會提出單挑（RG-2，#162：固定精英、懸賞、遭遇變化的 ``elite.duel``）；不輸出
    ``False``，既有紀錄不變。"""

    @property
    def has_elite_affix(self) -> bool:
        return any(m.affix is not None for m in self.members)


def lineup_rng(battle_seed: int) -> Rng:
    """陣容用的亂數：``fnv1a64("{battle_seed}:lineup")``。"""
    return Rng(fnv1a64(f"{battle_seed}:lineup".encode()))


def roll_lineup(
    library: ContentLibrary, encounter: EncounterResult, flags: Collection[str] = ()
) -> EncounterLineup:
    """依遭遇表抽出 ``encounter`` 的敵方陣容（確定性；規則見模組說明）。``flags``＝角色的劇情旗標：
    地點有對應的遭遇變化（Phase 5B-4b 線頭到期結局）時改用變化的陣容（不抽、不混營地精英）。"""
    table = library.world_encounters.get(encounter.region)
    if table is None:
        raise WorldError(f"區域 {encounter.region} 沒有遭遇表")
    entry = table.location_by_id().get(encounter.location)
    if entry is None:
        raise WorldError(f"地點 {encounter.location} 沒有遭遇表")
    place = world_map_of(library, encounter.region).location_by_id()[encounter.location]
    kind = place.kind
    gate_level = place.level_min if place.level_min is not None else encounter.level
    variant = entry.variant_for(flags)
    if variant is not None:
        group = table.group_by_id()[variant.group]
        members = [LineupMember(unit=_gated(u, entry, gate_level)) for u in group.units]
        if variant.elite is not None:
            members.insert(0, LineupMember(unit=variant.elite.unit, affix=variant.elite.affix))
        return EncounterLineup(
            region=encounter.region,
            location=encounter.location,
            group=group.id,
            members=tuple(members),
            third=tuple(LineupMember(unit=_gated(u, entry, gate_level)) for u in group.third),
            variant=variant.flag,
            duel=variant.elite is not None and variant.elite.duel,
        )
    bounty = _bounty_lineup(library, table, encounter)
    if bounty is not None:
        return bounty
    contact = encounter.contact
    if contact is None:
        rng = lineup_rng(encounter.battle_seed)
        group = _pick_group(rng, table, entry)
    else:  # 6C-1 看得見的敵人：陣容是地圖上那一隊（種子＝地圖上顯示的那一份）
        rng = lineup_rng(contact.lineup_seed)
        fixed = table.group_by_id().get(contact.group)
        group = _pick_group(rng, table, entry) if fixed is None else fixed
    members = [LineupMember(unit=_gated(u, entry, gate_level)) for u in group.units]
    third = tuple(LineupMember(unit=_gated(u, entry, gate_level)) for u in group.third)
    catalog = library.enemy_catalog()
    if entry.elite is not None:
        members.insert(0, LineupMember(unit=entry.elite.unit, affix=entry.elite.affix))
    elif kind == "camp":
        members = _maybe_mix_elite(rng, table, catalog, members)
    members = _surge(table, encounter, kind, members)
    return EncounterLineup(
        region=encounter.region,
        location=encounter.location,
        group=group.id,
        members=tuple(members),
        third=third,
        duel=entry.elite is not None and entry.elite.duel,
    )


def lineup_templates(
    library: ContentLibrary, lineup: EncounterLineup, *, third: bool = False
) -> tuple[UnitTemplate, ...]:
    """把陣容解析成單位範本（變體已套用、精英詞綴已套用），依陣容順序；``third`` 時解析第三方。"""
    catalog = library.enemy_catalog()
    result: list[UnitTemplate] = []
    for member in lineup.third if third else lineup.members:
        template = catalog.template(member.unit)
        if member.affix is not None:
            template = catalog.with_affix(template, member.affix)
        result.append(template)
    return tuple(result)


class Reinforcement(BaseModel):
    """增援的結果：加了增援的陣容、加了幾名、是否改成敵人先手。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lineup: EncounterLineup
    added: int = 0
    enemy_first: bool = False


def reinforce_lineup(
    library: ContentLibrary, encounter: EncounterResult, lineup: EncounterLineup, count: int
) -> Reinforcement:
    """情境判定的增援（見模組說明）；``count`` 是 ``reinforce`` 的筆數，0 時原樣。"""
    if count <= 0:
        return Reinforcement(lineup=lineup)
    table = library.world_encounters.get(encounter.region)
    entry = None if table is None else table.location_by_id().get(encounter.location)
    if table is None or entry is None:  # 6D-R2：主城、Boss 等沒有遭遇表的地點不增援
        return Reinforcement(lineup=lineup)
    catalog = library.enemy_catalog()
    groups = table.group_by_id()
    place = world_map_of(library, encounter.region).location_by_id()[encounter.location]
    level = place.level_min if place.level_min is not None else encounter.level
    names = sorted({_gated(u, entry, level) for g in entry.groups for u in groups[g.group].units})
    pool = [n for n in names if not catalog.is_elite(catalog.template(n))]
    members = list(lineup.members)
    ranged = sum(1 for t in lineup_templates(library, lineup) if catalog.is_ranged(t))
    rng = Rng(fnv1a64(f"{encounter.battle_seed}:reinforce".encode()))
    added = 0
    enemy_first = False
    for _ in range(count):
        ranged_ok = ranged < (table.ranged_cap if entry.ranged_cap is None else entry.ranged_cap)
        options = [n for n in pool if ranged_ok or not catalog.is_ranged(catalog.template(n))]
        if len(members) >= MAX_GROUP_SIZE or not options:
            enemy_first = True
            continue
        name = options[rng.randint(0, len(options) - 1)]
        members.append(LineupMember(unit=name))
        ranged += catalog.is_ranged(catalog.template(name))
        added += 1
    grown = lineup.model_copy(update={"members": tuple(members)})
    return Reinforcement(lineup=grown, added=added, enemy_first=enemy_first)


def elite_kinds(library: ContentLibrary, lineup: EncounterLineup) -> tuple[str, ...]:
    """陣容裡的精英種類（06 6.34.2 精英首殺；代決 5A6-7）：精英範本（``elite`` 標籤）以單位 ID 算，
    一般單位套詞綴的以 ``<單位>+<詞綴>`` 算。排序、不重複。"""
    catalog = library.enemy_catalog()
    kinds: set[str] = set()
    for member in lineup.members:
        if catalog.is_elite(catalog.template(member.unit)):
            kinds.add(member.unit)
        elif member.affix is not None:
            kinds.add(f"{member.unit}+{member.affix}")
    return tuple(sorted(kinds))


def _surge(
    table: EncounterTable, encounter: EncounterResult, kind: str, members: list[LineupMember]
) -> list[LineupMember]:
    """世界旗標有效時的遭遇加人（5B-4c；遭遇表 ``surges``）：符合旗標、地點種類、時段的每一筆在
    敵方最後加 1 名（滿 4 名不加；代決 5B4c-10）。不耗亂數。"""
    out = list(members)
    for surge in table.surges:
        if (
            surge.flag in encounter.world_flags
            and kind in surge.kinds
            and (surge.day_phase is None or surge.day_phase == encounter.day_phase)
            and len(out) < MAX_GROUP_SIZE
        ):
            out.append(LineupMember(unit=surge.unit))
    return out


def _gated(unit: str, entry: LocationEncounters, level: int) -> str:
    """單位的等級門檻（``unit_min_levels``）：等級不夠時換成指定的單位。"""
    for gate in entry.unit_min_levels:
        if gate.unit == unit and level < gate.min_level:
            return gate.otherwise
    return unit


def _bounty_lineup(
    library: ContentLibrary, table: EncounterTable, encounter: EncounterResult
) -> EncounterLineup | None:
    """懸賞陣容（Phase 5F-1）：懸賞的陣容＋精英排最前；不抽、不混營地精英、不加人。內容改掉懸賞
    時退回一般抽陣容。"""
    season = library.world_season
    if encounter.bounty is None or season is None:
        return None
    bounty = season.bounty_by_id().get(encounter.bounty)
    if bounty is None:
        return None
    group = table.group_by_id()[bounty.group]
    elite = LineupMember(unit=bounty.elite.unit, affix=bounty.elite.affix)
    return EncounterLineup(
        region=encounter.region,
        location=encounter.location,
        group=group.id,
        members=(elite, *(LineupMember(unit=u) for u in group.units)),
        bounty=bounty.id,
        duel=bounty.elite.duel,
    )


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
