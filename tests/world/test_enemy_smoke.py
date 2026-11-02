"""雲嶺敵人的 smoke 測試（Phase 5A-3；``docs/phases/Phase5計畫.md`` 7.5）。

每個陣容（含變體）與每個精英詞綴都在現有戰鬥引擎裡生成並打完一場：用該地點的戰鬥地圖（沒有地圖
的地點用 ``dark_forest``）、3 名既有主角範本、效用 AI（同 ``trpg battle --ai utility``）、
``max_rounds`` 8；三方混戰的陣容（5B-M3）連第三方一起上場。只驗「能開打、能結束、不出錯」，
勝負與數值不在本段範圍（初值，不做平衡模擬）。開戰接線本身是 5A-4。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn
from trpg.shared.types import Team

HEROES = ("hero_fighter", "hero_archer", "hero_stormcaller")
FALLBACK_MAP = "dark_forest"
MAX_ROUNDS = 8


def _setup(
    library: ContentLibrary,
    map_id: str,
    enemies: Sequence[UnitTemplate],
    third: Sequence[UnitTemplate] = (),
) -> BattleSetup:
    allies = [library.unit(h) for h in HEROES]
    spawns = [
        UnitSpawn(
            template=t,
            weapon=library.weapon_of(t),
            equipment=library.loadout_of(t),
            team=team,
        )
        for team, templates in ((Team.ALLY, allies), (Team.ENEMY, enemies), (Team.THIRD, third))
        for t in templates
    ]
    map_def = library.map(map_id)
    return BattleSetup(
        map=map_def,
        ruleset=library.ruleset,
        units=tuple(spawns),
        max_rounds=MAX_ROUNDS,
        weather=library.weather_def(map_def.weather),
    )


Case = tuple[str, str, list[UnitTemplate], list[UnitTemplate]]


def _cases(library: ContentLibrary) -> list[Case]:
    """(說明, 地圖, 敵方範本, 第三方範本)：每個地點的每個陣容。"""
    table = library.world_encounters["cloud_ridge"]
    places = library.world_maps["cloud_ridge"].location_by_id()
    catalog = library.enemy_catalog()
    groups = table.group_by_id()
    cases: list[Case] = []
    for entry in table.locations:
        map_id = (places[entry.location].battle_maps or (FALLBACK_MAP,))[0]
        for weighted in entry.groups:
            enemies = [catalog.template(u) for u in groups[weighted.group].units]
            if entry.elite is not None:
                elite = catalog.template(entry.elite.unit)
                enemies.insert(0, catalog.with_affix(elite, entry.elite.affix))
            third = [catalog.template(u) for u in groups[weighted.group].third]
            cases.append((f"{entry.location}/{weighted.group}", map_id, enemies, third))
    return cases


def _assert_battle_ends(
    library: ContentLibrary,
    map_id: str,
    enemies: list[UnitTemplate],
    third: Sequence[UnitTemplate] = (),
) -> None:
    run = run_battle(
        _setup(library, map_id, enemies, third), seed=11, policy=UtilityAI(library.ai_profiles)
    )
    assert run.state.ended
    assert run.state.round <= MAX_ROUNDS
    assert run.actions


def test_three_way_groups(library: ContentLibrary) -> None:
    three_way = sorted(label for label, _m, _e, third in _cases(library) if third)
    assert three_way == [
        "crystal_rift/rift_scavengers",
        "crystal_rift/rift_wraiths",
        "rain_terraces/terrace_clash",
    ]


def test_every_group_fights_to_the_end(library: ContentLibrary) -> None:
    for label, map_id, enemies, third in _cases(library):
        try:
            _assert_battle_ends(library, map_id, enemies, third)
        except Exception as exc:  # 加上是哪個陣容，方便定位
            raise AssertionError(f"{label}（{map_id}）：{exc!r}") from exc


def test_groups_cover_every_new_enemy(library: ContentLibrary) -> None:
    fielded = {t.id for _l, _m, enemies, third in _cases(library) for t in enemies + third}
    new = {u for u, t in library.units.items() if {"sect", "beast", "construct"} & set(t.tags)}
    assert len(new) == 17
    assert library.world_enemies is not None
    variants = {v.id for v in library.world_enemies.variants}
    assert new | variants <= fielded


@pytest.mark.parametrize("affix", ["regenerating", "mist_veiled", "heart_linked", "berserk"])
def test_every_affix_fights_to_the_end(library: ContentLibrary, affix: str) -> None:
    catalog = library.enemy_catalog()
    candidates = ("mist_wolf", "sect_acolyte", "sect_crane_archer")
    base = next(
        catalog.template(u)
        for u in candidates
        if catalog.affix_problem(catalog.template(u), affix) is None
    )
    elite = catalog.with_affix(base, affix)
    _assert_battle_ends(library, "open_plain", [elite, catalog.template("mist_wolf")])
