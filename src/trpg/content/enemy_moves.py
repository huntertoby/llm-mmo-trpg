"""#149 敵人招式數的下限（CB-2a；``docs/design/18-雲嶺內容.md`` 18.2）：第一季遭遇表與懸賞的敵人，
招數要達到 18.2 的表格（技能欄每筆算 1 招，含被動、反應；不含普攻）。

原本寫在 ``tests/content/test_enemy_skill_count_149.py``；NW-2a（R1，使用者 2026-11-12「照建議」）
搬來給數值工坊用（招式組改到低於下限時警告、勾「我確定」才寫回），測試改呼叫這裡，判定不變。
**這不是載入檢查**：``load_library`` 不擋，只由測試與數值工坊用。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Final

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary

__all__ = [
    "BOSS",
    "ELITE",
    "EXEMPT",
    "MOB",
    "REGIONS",
    "first_season_units",
    "move_shortfalls",
    "phase_counts",
]

MOB, ELITE, BOSS = 2, 3, 3
"""一般 2 招、精英 3 招、頭目每階段 3 招。"""
REGIONS: Final = ("cloud_ridge", "ashen_waste")
EXEMPT: Final = frozenset(
    {
        "bandit_rookie",  # 18.2 例外：新手第 1 場專用（使用者「照推薦 寫入」）
        "bandit_rookie_terrace",  # 同上的 bandit_rookie，只有梯田固定戰的 HP 不同（CB-2d）
        "bandit_archer_rookie",
        "training_dummy",
        "training_dummy_moving",
        "rift_pillar_fire",  # 源晶柱
        "rift_pillar_mist",
        "rift_pillar_thunder",
        "sect_array_stone",  # 陣石
        "sect_summit_array_stone",
        "rift_crystal_golem",  # 碎晶之主階段召喚的晶傀儡
    }
)


def _lineup_names(library: ContentLibrary) -> set[str]:
    names: set[str] = set()
    for region in REGIONS:
        table = library.world_encounters[region]
        for group in table.groups:
            names |= set(group.all_units)
        names |= {s.unit for s in table.surges}
        names |= {loc.elite.unit for loc in table.locations if loc.elite is not None}
    season = library.world_season
    assert season is not None
    names |= {b.elite.unit for b in season.bounties}
    if season.season_boss is not None:
        names |= set(season.season_boss.units)
    return names


def _spawned_by_phases(units: dict[str, UnitTemplate]) -> set[str]:
    return {spawn.template for u in units.values() for p in u.phases for spawn in p.spawns}


def first_season_units(library: ContentLibrary) -> Iterator[UnitTemplate]:
    """第一季會遇到的敵人範本（變體已套用；含階段召喚的小怪；去掉 :data:`EXEMPT`），依 ID 排序。"""
    catalog = library.enemy_catalog()
    names = _lineup_names(library)
    templates = {n: catalog.template(n) for n in names}
    templates |= {
        n: library.units[n]
        for n in _spawned_by_phases(templates)
        if n in library.units and not library.units[n].summon
    }
    for name in sorted(templates):
        if name not in EXEMPT:
            yield templates[name]


def phase_counts(unit: UnitTemplate) -> list[tuple[str, int]]:
    """頭目每個階段（沒換招的沿用前一階段）的 (階段 ID, 招數)。"""
    current = unit.skills
    counts: list[tuple[str, int]] = []
    for phase in unit.phases:
        current = phase.skills if phase.skills is not None else current
        counts.append((phase.id, len(current)))
    return counts


def move_shortfalls(library: ContentLibrary) -> list[str]:
    """低於下限的：頭目 ``<單位>/<階段>=<招數>``、其他 ``<單位>=<招數>``（依單位 ID 排序）。"""
    problems: list[str] = []
    for unit in first_season_units(library):
        if "boss" in unit.tags:
            problems += [f"{unit.id}/{p}={n}" for p, n in phase_counts(unit) if n < BOSS]
        else:
            need = ELITE if "elite" in unit.tags else MOB
            if len(unit.skills) < need:
                problems.append(f"{unit.id}={len(unit.skills)}")
    return problems
