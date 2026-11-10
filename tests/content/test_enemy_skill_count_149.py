"""#149 敵人招式數（CB-2a；``docs/design/18-雲嶺內容.md`` 18.2）：掃描第一季遭遇表與懸賞的敵人，
招數達到 18.2 的表格（技能欄每筆算 1 招，含被動、反應；不含普攻）。"""

from __future__ import annotations

from collections.abc import Iterator

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_enemies import EnemyCatalog

MOB, ELITE, BOSS = 2, 3, 3
REGIONS = ("cloud_ridge", "ashen_waste")
EXEMPT = {
    "bandit_rookie",  # 18.2 例外：新手第 1 場專用（使用者「照推薦 寫入」）
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


def _first_season(library: ContentLibrary) -> Iterator[UnitTemplate]:
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


def _phase_counts(unit: UnitTemplate) -> list[tuple[str, int]]:
    current = unit.skills
    counts: list[tuple[str, int]] = []
    for phase in unit.phases:
        current = phase.skills if phase.skills is not None else current
        counts.append((phase.id, len(current)))
    return counts


def _shortfalls(library: ContentLibrary) -> list[str]:
    problems: list[str] = []
    for unit in _first_season(library):
        if "boss" in unit.tags:
            problems += [f"{unit.id}/{p}={n}" for p, n in _phase_counts(unit) if n < BOSS]
        else:
            need = ELITE if "elite" in unit.tags else MOB
            if len(unit.skills) < need:
                problems.append(f"{unit.id}={len(unit.skills)}")
    return problems


def test_the_scan_covers_the_first_season(library: ContentLibrary) -> None:
    names = {u.id for u in _first_season(library)}
    assert len(names) >= 40
    assert {"rift_shard_lord", "ashen_heart", "sect_mist_lock_master", "forge_scar"} <= names
    assert "heart_ember_lizard" in names  # 階段召喚的小怪也算
    assert not names & EXEMPT


def test_every_first_season_enemy_has_enough_moves(library: ContentLibrary) -> None:
    assert _shortfalls(library) == []


def test_rookies_stay_as_they_were(library: ContentLibrary) -> None:
    assert library.units["bandit_rookie"].skills == ()
    assert library.units["bandit_archer_rookie"].skills == ("skill_fire_arrow",)


def test_three_pillars_phase_has_three_moves(library: ContentLibrary) -> None:
    lord = library.units["rift_shard_lord"]
    assert _phase_counts(lord)[0] == ("three_pillars", 3)


def _table_affixes(library: ContentLibrary, catalog: EnemyCatalog) -> list[tuple[str, str]]:
    """(敵人, 詞綴)：隨機混精英可能抽到的組合。"""
    pairs: set[tuple[str, str]] = set()
    for region in REGIONS:
        table = library.world_encounters[region]
        for group in table.groups:
            for name in group.units:
                template = catalog.template(name)
                if name not in EXEMPT:
                    pairs |= {
                        (name, a) for a in catalog.applicable_affixes(template, table.affixes)
                    }
    return sorted(pairs)


def test_random_elites_reach_three_moves(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    pairs = _table_affixes(library, catalog)
    assert pairs
    short = [
        (name, affix)
        for name, affix in pairs
        if len(catalog.with_affix(catalog.template(name), affix).skills) < ELITE
    ]
    assert short == []


def test_fixed_elites_reach_three_moves(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    season = library.world_season
    assert season is not None
    elites = [b.elite for b in season.bounties]
    for region in REGIONS:
        elites += [
            loc.elite for loc in library.world_encounters[region].locations if loc.elite is not None
        ]
    for elite in elites:
        template = catalog.template(elite.unit)
        if elite.affix is not None:
            template = catalog.with_affix(template, elite.affix)
        assert len(template.skills) >= ELITE, elite


def test_affixes_carry_the_designated_moves(library: ContentLibrary) -> None:
    affixes = library.enemy_catalog().enemies
    assert affixes is not None
    by_id = affixes.affix_by_id()
    assert by_id["mist_veiled"].add_skills == ("skill_mist_shift",)
    assert by_id["heart_linked"].add_skills == ("skill_guardian_aegis",)
    assert by_id["hard_shelled"].add_skills == ("skill_parry_riposte",)


def test_the_mist_shade_copies_the_new_move(library: ContentLibrary) -> None:
    assert "skill_shadow_ambush" in library.units["sect_mist_swordsman"].skills
    shade = library.ruleset.summon_def("summon_mist_shade").template
    assert "skill_shadow_ambush" in shade.skills


def test_new_moves_are_enemy_only(library: ContentLibrary) -> None:
    for skill_id in (
        "skill_slime_glob",
        "skill_cinder_dive",
        "skill_venom_gore",
        "skill_frost_feather",
    ):
        assert library.skills[skill_id].enemy_only, skill_id


def _dice_average_times_two(library: ContentLibrary, skill_id: str) -> int:
    """招式主傷害骰的平均值 × 2（整數比較）。"""
    damage = next(e for e in library.skills[skill_id].effects if e.type == "damage")
    assert damage.dice is not None
    return damage.dice.count * (damage.dice.sides + 1)


def test_the_three_pillars_filler_hits_no_harder_than_shard_erosion(
    library: ContentLibrary,
) -> None:
    """CB-2d：三柱階段第 3 招換成火花連鎖，傷害不高於晶蝕（PM 決定）。"""
    pillars = library.units["rift_shard_lord"].skills
    assert "skill_shock_follow" not in pillars
    assert "skill_spark_chain" in pillars
    assert _dice_average_times_two(library, "skill_spark_chain") <= _dice_average_times_two(
        library, "skill_shard_erosion"
    )


def test_the_mist_lock_master_last_phase_swapped_whirlwind_for_execute(
    library: ContentLibrary,
) -> None:
    last = next(p for p in library.units["sect_mist_lock_master"].phases if p.id == "return_to_one")
    assert last.skills is not None
    assert "skill_execute" in last.skills
    assert "skill_whirlwind" not in last.skills


def test_an_affix_whose_move_is_already_known_is_not_applied(library: ContentLibrary) -> None:
    """硬殼帶 parry_riposte：已有這招的甲蟲不套，改抽其他詞綴（18.2；走 applicable_affixes）。"""
    catalog = library.enemy_catalog()
    beetle = catalog.template("lava_beetle")
    assert "skill_parry_riposte" in beetle.skills
    assert catalog.affix_problem(beetle, "hard_shelled") is not None
    assert catalog.applicable_affixes(beetle, ("hard_shelled", "regenerating")) == ["regenerating"]
