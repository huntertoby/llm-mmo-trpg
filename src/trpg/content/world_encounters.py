"""大世界的遭遇表（``content/world/encounters/<region>.yaml``，Phase 5A-3）。

一區一檔：地點 → 陣容（權重）、精英巢穴的固定精英、本區常見的精英詞綴、每場遠程上限與一般營地混進
精英的機率。依據 ``docs/design/09-世界與敘事.md`` 9.6.6（#82：混族、遠程上限、營地混精英）、
``docs/design/18-雲嶺內容.md`` 18.2、18.3；數值是開發 PM 的初值（``docs/phases/Phase5計畫.md``
0.2 Q5、第 7 節）。抽陣容的規則在 :mod:`trpg.world.encounters`。
"""

from __future__ import annotations

import re
from collections.abc import Collection
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.schemas import ContentModel
from trpg.content.world_enemies import EnemyCatalog
from trpg.content.world_map import LocationMapDef

__all__ = [
    "MAX_GROUP_SIZE",
    "MAX_THIRD_SIZE",
    "MIN_GROUP_SIZE",
    "NO_ENCOUNTER_KINDS",
    "ArmorMod",
    "ArmorMods",
    "EncounterGroupDef",
    "EncounterSurge",
    "EncounterTable",
    "EncounterVariant",
    "FixedElite",
    "GroupWeight",
    "LocationEncounters",
    "UnitMinLevel",
    "encounter_table_problems",
]

MIN_GROUP_SIZE = 1
"""一場敵人最少 1 名（OB-7b，#155 2026-11-12 修訂：新手第 1 步渡口 1 隻、主角＋賽倫 2 打 1）。
第一季只有 ``bandit_raiders`` 是 1 名，其他陣容仍 ≥ 2（內容測試鎖住）。"""
MAX_GROUP_SIZE = 4
"""一場敵人最多 4 名（地圖敵方起始區 4 格；3 人隊伍對 2～4 名，代決 5A3-9）。"""
MAX_THIRD_SIZE = 3
"""三方混戰的第三方最多 3 名（Phase 5B-M3，代決 5BM3-9）。"""
NO_ENCOUNTER_KINDS = frozenset({"town", "gate"})
"""遇敵機率為 0 的地點種類（5A-2：城鎮、傳送點），不需要遭遇表。"""


class EncounterGroupDef(ContentModel):
    """一種陣容：單位範本 ID 或變體 ID，1～4 名（可重複；1 名只給新手渡口，OB-7b）。

    ``third``（Phase 5B-M3 三方混戰，09 9.6.6「兩方敵人互相敵對」）：同場的第三方，0～3 名；和我方、
    敵方都敵對。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    units: tuple[str, ...] = Field(min_length=MIN_GROUP_SIZE, max_length=MAX_GROUP_SIZE)
    third: tuple[str, ...] = Field(default=(), max_length=MAX_THIRD_SIZE)

    @property
    def all_units(self) -> tuple[str, ...]:
        """敵方加第三方（玩家面對的全部單位）。"""
        return self.units + self.third

    @model_validator(mode="after")
    def _ids(self) -> EncounterGroupDef:
        bad = [u for u in self.all_units if re.match(ID_PATTERN, u) is None]
        if bad:
            raise ValueError(f"陣容 {self.id}：單位 ID 格式錯誤 {', '.join(bad)}")
        return self


class GroupWeight(ContentModel):
    group: str = Field(pattern=ID_PATTERN)
    weight: int = Field(default=1, ge=1)


class FixedElite(ContentModel):
    """精英巢穴固定的精英（9.6.6「精英巢穴、懸賞固定有」）：單位＋詞綴。資料指定，所以本身已是
    精英的範本也可以套（Phase 5B-4c，18.7.4 懸賞的指定詞綴；HP 不再乘）。"""

    unit: str = Field(pattern=ID_PATTERN)
    affix: str = Field(pattern=ID_PATTERN)


class UnitMinLevel(ContentModel):
    """單位的等級門檻（5A-SIM2）：地點的敵人等級低於 ``min_level`` 時，陣容裡的 ``unit`` 換成
    ``otherwise``。"""

    unit: str = Field(pattern=ID_PATTERN)
    min_level: int = Field(ge=1)
    otherwise: str = Field(pattern=ID_PATTERN)


class EncounterVariant(ContentModel):
    """線頭到期結局的遭遇變化（Phase 5B-4b，18.4「線頭到期例」）：角色有劇情旗標 ``flag`` 時，這個
    地點的遭遇改用陣容 ``group``（＋固定精英 ``elite``，排最前面）；打贏那一場旗標就移除。"""

    flag: str = Field(pattern=ID_PATTERN)
    group: str = Field(pattern=ID_PATTERN)
    elite: FixedElite | None = None


class EncounterSurge(ContentModel):
    """世界旗標有效時的遭遇加人（Phase 5B-4c；18.4 補充「霧魅從裂痕湧出 → 之後 2 天雲嶺夜晚營地
    遭遇多 1 名霧魅」）：遇敵當下有世界旗標 ``flag``、地點種類在 ``kinds``、時段符合 ``day_phase``
    （``None``＝不限）時，一般抽到的陣容在敵方最後多 1 名 ``unit``（滿 4 名不加）。"""

    flag: str = Field(pattern=ID_PATTERN)
    unit: str = Field(pattern=ID_PATTERN)
    kinds: tuple[str, ...] = Field(default=("camp",), min_length=1)
    day_phase: Literal["day", "night"] | None = None


class ArmorMod(ContentModel):
    """一條護甲調整（Phase 5F-5a；19.4 骨架 13「每攔下 1 批碎片，灰燼之心第 1 階段護甲 −1」、
    18.4 骨架 14 世界線頭到期「灰燼之心第 1 階段護甲 +1」）：``world_flag``（遇敵當下有效的世界
    旗標）、``story_flag``（角色的劇情旗標）、``thread``（遇敵時刻還有效的線頭）恰好填一個；符合時
    加 ``amount``。"""

    world_flag: str | None = Field(default=None, pattern=ID_PATTERN)
    story_flag: str | None = Field(default=None, pattern=ID_PATTERN)
    thread: str | None = Field(default=None, pattern=ID_PATTERN)
    amount: int = Field(ge=-5, le=5)

    @model_validator(mode="after")
    def _one_source(self) -> ArmorMod:
        sources = [s for s in (self.world_flag, self.story_flag, self.thread) if s is not None]
        if len(sources) != 1:
            raise ValueError("armor_mods 每一條要恰好填 world_flag、story_flag、thread 其中一個")
        if self.amount == 0:
            raise ValueError("armor_mods 的 amount 不可為 0")
        return self


class ArmorMods(ContentModel):
    """開戰時調整陣容中 ``unit`` 的護甲（Phase 5F-5a）：符合的 ``mods`` 加總後夾在
    ``min_total``～``max_total``，結果護甲不低於 0。不耗亂數。"""

    unit: str = Field(pattern=ID_PATTERN)
    min_total: int = Field(default=-5, ge=-10, le=0)
    max_total: int = Field(default=5, ge=0, le=10)
    mods: tuple[ArmorMod, ...] = Field(min_length=1)

    def total(
        self,
        *,
        world_flags: Collection[str],
        story_flags: Collection[str],
        threads: Collection[str],
    ) -> int:
        """符合的調整總和（已夾在上下限內）。"""
        found = 0
        for mod in self.mods:
            if (
                (mod.world_flag is not None and mod.world_flag in world_flags)
                or (mod.story_flag is not None and mod.story_flag in story_flags)
                or (mod.thread is not None and mod.thread in threads)
            ):
                found += mod.amount
        return max(self.min_total, min(self.max_total, found))


class LocationEncounters(ContentModel):
    location: str = Field(pattern=ID_PATTERN)
    groups: tuple[GroupWeight, ...] = Field(min_length=1)
    ranged_cap: int | None = Field(default=None, ge=0)
    """這個地點每場遠程敵人的上限；省略＝用整區的 ``ranged_cap``（5A-SIM2：雲海吊橋 1）。"""
    unit_min_levels: tuple[UnitMinLevel, ...] = ()
    """單位的等級門檻（5A-SIM2：寒湖的石背熊 4 級以上才出現，其他換霧狼）。"""
    elite: FixedElite | None = None
    ally_first_threads: tuple[str, ...] = ()
    """持有其中任一條有效線頭時，在這個地點的戰鬥我方先手（Phase 5A-6；18.4 補充「斷崖幫寨的
    暗門」）。"""
    variants: tuple[EncounterVariant, ...] = ()
    """線頭到期結局的遭遇變化（Phase 5B-4b；第一個符合的旗標生效）。"""
    objective: Literal["escape", "defend"] | None = None
    """移動遇敵的勝利條件（Phase 5F-5a；19.9 #2 三村落的守點戰）：呼叫端沒有指定時用這個；
    骨架的戰鬥解法照舊優先。``None``＝一般勝利。"""
    armor_mods: ArmorMods | None = None
    """開戰時的護甲調整（Phase 5F-5a；灰燼之心）。"""

    def variant_for(self, flags: Collection[str]) -> EncounterVariant | None:
        return next((v for v in self.variants if v.flag in flags), None)

    @model_validator(mode="after")
    def _thread_ids(self) -> LocationEncounters:
        bad = [t for t in self.ally_first_threads if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"地點 {self.location}：線頭 ID 格式錯誤 {', '.join(bad)}")
        return self


class EncounterTable(ContentModel):
    """``content/world/encounters/<region>.yaml``。"""

    region: str = Field(pattern=ID_PATTERN)
    ranged_cap: int = Field(ge=0)
    """每場遠程敵人上限（9.6.6；雲嶺 2，18.2.1）。"""
    camp_elite_permille: int = Field(ge=0, le=1000)
    """一般營地（``camp``）混進 1 名精英的機率（9.6.6；初值）。"""
    affixes: tuple[str, ...] = ()
    """本區常見的精英詞綴（``world/enemies.yaml`` 的 ID）。"""
    groups: tuple[EncounterGroupDef, ...] = Field(min_length=1)
    locations: tuple[LocationEncounters, ...] = Field(min_length=1)
    surges: tuple[EncounterSurge, ...] = ()
    """世界旗標有效時的遭遇加人（Phase 5B-4c）。"""

    @model_validator(mode="after")
    def _check(self) -> EncounterTable:
        problems: list[str] = []
        for label, ids in (
            ("陣容", [g.id for g in self.groups]),
            ("地點", [loc.location for loc in self.locations]),
            ("詞綴", list(self.affixes)),
        ):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            if dupes:
                problems.append(f"{label}重複：{', '.join(dupes)}")
        groups = self.group_by_id()
        for loc in self.locations:
            names = [g.group for g in loc.groups]
            dupes = sorted({n for n in names if names.count(n) > 1})
            if dupes:
                problems.append(f"地點 {loc.location}：陣容重複 {', '.join(dupes)}")
            unknown = sorted(n for n in names if n not in groups)
            if unknown:
                problems.append(f"地點 {loc.location}：未知的陣容 {', '.join(unknown)}")
            elif loc.elite is not None:
                too_big = sorted(n for n in names if len(groups[n].units) + 1 > MAX_GROUP_SIZE)
                if too_big:
                    problems.append(
                        f"地點 {loc.location}：陣容加上固定精英超過 {MAX_GROUP_SIZE} 名"
                        f"（{', '.join(too_big)}）"
                    )
        if problems:
            raise ValueError("；".join(problems))
        return self

    def group_by_id(self) -> dict[str, EncounterGroupDef]:
        return {g.id: g for g in self.groups}

    def location_by_id(self) -> dict[str, LocationEncounters]:
        return {loc.location: loc for loc in self.locations}

    def summary(self) -> str:
        return (
            f"{len(self.locations)} 個地點、{len(self.groups)} 種陣容、遠程上限 {self.ranged_cap}、"
            f"營地精英 {self.camp_elite_permille}‰"
        )


def encounter_table_problems(
    table: EncounterTable,
    *,
    world_map: LocationMapDef | None,
    catalog: EnemyCatalog,
) -> list[str]:
    """跨檔案檢查（繁體中文、排序；空＝通過）。見 ``docs/phases/Phase5計畫.md`` 7.2 第 3 項。"""
    if world_map is None:
        return [f"區域 {table.region} 沒有地點圖"]
    problems: list[str] = []
    problems += _affix_problems(table, catalog)
    problems += _group_problems(table, catalog)
    problems += _location_problems(table, world_map, catalog)
    problems += _surge_problems(table, catalog)
    return sorted(problems)


def _surge_problems(table: EncounterTable, catalog: EnemyCatalog) -> list[str]:
    """遭遇加人（5B-4c）：單位存在、不是精英。"""
    problems: list[str] = []
    for surge in table.surges:
        where = f"遭遇加人 {surge.flag}"
        if not catalog.has(surge.unit):
            problems.append(f"{where}：未知的單位 {surge.unit}")
        elif catalog.is_elite(catalog.template(surge.unit)):
            problems.append(f"{where}：不能加精英（{surge.unit}）")
    return problems


def _affix_problems(table: EncounterTable, catalog: EnemyCatalog) -> list[str]:
    known = set() if catalog.enemies is None else set(catalog.enemies.affix_by_id())
    return [f"未知的詞綴：{a}" for a in table.affixes if a not in known]


def _group_problems(table: EncounterTable, catalog: EnemyCatalog) -> list[str]:
    problems: list[str] = []
    for group in table.groups:
        unknown = sorted({u for u in group.all_units if not catalog.has(u)})
        if unknown:
            problems.append(f"陣容 {group.id}：未知的單位 {', '.join(unknown)}")
            continue
        templates = [catalog.template(u) for u in group.all_units]  # 遠程上限敵方＋第三方合計
        problems += _lineup_problems(f"陣容 {group.id}", templates, table, catalog)
        problems += [
            f"陣容 {group.id}：第三方不能有精英（{u}）"
            for u in group.third
            if catalog.is_elite(catalog.template(u))
        ]
    return problems


def _lineup_problems(
    where: str, templates: list[UnitTemplate], table: EncounterTable, catalog: EnemyCatalog
) -> list[str]:
    problems: list[str] = []
    ranged = sum(1 for t in templates if catalog.is_ranged(t))
    if ranged > table.ranged_cap:
        problems.append(f"{where}：遠程 {ranged} 名，超過上限 {table.ranged_cap}")
    elites = sum(1 for t in templates if catalog.is_elite(t))
    if elites > 1:
        problems.append(f"{where}：精英 {elites} 名（一場最多 1 名）")
    return problems


def _location_problems(
    table: EncounterTable, world_map: LocationMapDef, catalog: EnemyCatalog
) -> list[str]:
    problems: list[str] = []
    places = world_map.location_by_id()
    listed = table.location_by_id()
    for loc_id in sorted(places):
        if places[loc_id].kind not in NO_ENCOUNTER_KINDS and loc_id not in listed:
            problems.append(f"地點 {loc_id} 會遇敵，但沒有遭遇表")
    groups = table.group_by_id()
    for loc_id, loc in sorted(listed.items()):
        place = places.get(loc_id)
        if place is None:
            problems.append(f"未知的地點：{loc_id}")
            continue
        if place.kind in NO_ENCOUNTER_KINDS:
            problems.append(f"地點 {loc_id}（{place.kind}）不會遇敵，不該有遭遇表")
        members = [groups[g.group] for g in loc.groups if g.group in groups]
        if any(not catalog.has(u) for m in members for u in m.all_units):
            continue  # 陣容的問題已經回報過
        problems += _gate_problems(loc, members, table, catalog)
        if loc.armor_mods is not None and all(loc.armor_mods.unit not in m.units for m in members):
            problems.append(f"地點 {loc_id}：armor_mods 的 {loc.armor_mods.unit} 不在任何陣容裡")
        problems += _variant_problems(loc, table, catalog)
        problems += _elite_problems(loc, place.kind, members, table, catalog)
    return problems


def _gate_problems(
    loc: LocationEncounters,
    members: list[EncounterGroupDef],
    table: EncounterTable,
    catalog: EnemyCatalog,
) -> list[str]:
    where = f"地點 {loc.location}"
    problems = [
        f"{where}：單位門檻用了未知的單位 {u}"
        for gate in loc.unit_min_levels
        for u in (gate.unit, gate.otherwise)
        if not catalog.has(u)
    ]
    cap = table.ranged_cap if loc.ranged_cap is None else loc.ranged_cap
    for group in members:
        ranged = sum(1 for u in group.all_units if catalog.is_ranged(catalog.template(u)))
        if ranged > cap:
            problems.append(f"{where}：陣容 {group.id} 遠程 {ranged} 名，超過地點上限 {cap}")
    return problems


def _elite_problems(
    loc: LocationEncounters,
    kind: str,
    members: list[EncounterGroupDef],
    table: EncounterTable,
    catalog: EnemyCatalog,
) -> list[str]:
    where = f"地點 {loc.location}"
    if kind != "elite_lair":
        problems = [f"{where}：只有精英巢穴可以填固定精英"] if loc.elite is not None else []
        if kind == "camp":
            problems += [
                f"{where}：陣容 {g.id} 沒有成員可以套用本區的詞綴"
                for g in members
                if not _can_mix_elite(g, table, catalog)
            ]
        return problems
    if loc.elite is None:
        return [f"{where}：精英巢穴必須有固定精英"]
    if not catalog.has(loc.elite.unit):
        return [f"{where}：未知的固定精英 {loc.elite.unit}"]
    try:
        reason = catalog.affix_problem(
            catalog.template(loc.elite.unit), loc.elite.affix, allow_elite=True
        )
    except KeyError:
        return [f"{where}：未知的詞綴 {loc.elite.affix}"]
    if reason is not None:
        return [f"{where}：固定精英不能套用詞綴（{reason}）"]
    elite = catalog.with_affix(catalog.template(loc.elite.unit), loc.elite.affix)
    lineup: list[str] = []
    for group in members:
        templates = [elite, *(catalog.template(u) for u in group.all_units)]
        lineup += _lineup_problems(f"{where} 的陣容 {group.id}", templates, table, catalog)
    return lineup


def _variant_problems(
    loc: LocationEncounters, table: EncounterTable, catalog: EnemyCatalog
) -> list[str]:
    """遭遇變化（5B-4b）：陣容存在、固定精英與詞綴合法、整場遠程與精英上限。"""
    where = f"地點 {loc.location} 的變化"
    groups = table.group_by_id()
    problems: list[str] = []
    for variant in loc.variants:
        group = groups.get(variant.group)
        if group is None:
            problems.append(f"{where} {variant.flag}：未知的陣容 {variant.group}")
            continue
        if any(not catalog.has(u) for u in group.units):
            continue  # 陣容的問題已經回報過
        templates = [catalog.template(u) for u in group.units]
        elite = variant.elite
        if elite is not None:
            if not catalog.has(elite.unit):
                problems.append(f"{where} {variant.flag}：未知的固定精英 {elite.unit}")
                continue
            try:
                reason = catalog.affix_problem(
                    catalog.template(elite.unit), elite.affix, allow_elite=True
                )
            except KeyError:
                problems.append(f"{where} {variant.flag}：未知的詞綴 {elite.affix}")
                continue
            if reason is not None:
                problems.append(f"{where} {variant.flag}：固定精英不能套用詞綴（{reason}）")
                continue
            templates.insert(0, catalog.with_affix(catalog.template(elite.unit), elite.affix))
            if len(templates) > MAX_GROUP_SIZE:
                problems.append(f"{where} {variant.flag}：加上精英超過 {MAX_GROUP_SIZE} 名")
        problems += _lineup_problems(f"{where} {variant.flag}", templates, table, catalog)
    return problems


def _can_mix_elite(group: EncounterGroupDef, table: EncounterTable, catalog: EnemyCatalog) -> bool:
    templates = [catalog.template(u) for u in group.units]
    if any(catalog.is_elite(t) for t in templates):
        return True
    known = set() if catalog.enemies is None else set(catalog.enemies.affix_by_id())
    affixes = tuple(a for a in table.affixes if a in known)
    return any(catalog.applicable_affixes(t, affixes) for t in templates)
