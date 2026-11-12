"""#149 敵人招式數（CB-2a；``docs/design/18-雲嶺內容.md`` 18.2）：掃描第一季遭遇表與懸賞的敵人，
招數達到 18.2 的表格（技能欄每筆算 1 招，含被動、反應；不含普攻）。"""

from __future__ import annotations

from trpg.content.enemy_moves import ELITE, EXEMPT, REGIONS
from trpg.content.enemy_moves import first_season_units as _first_season
from trpg.content.enemy_moves import move_shortfalls as _shortfalls
from trpg.content.enemy_moves import phase_counts as _phase_counts
from trpg.content.library import ContentLibrary
from trpg.content.world_enemies import EnemyCatalog

# NW-2a（R1）：判定函式搬到 trpg.content.enemy_moves（數值工坊共用），這裡只換來源、斷言不變。


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


def test_the_mist_lock_master_last_phase_uses_mist_rend(library: ContentLibrary) -> None:
    """CB-2e：execute（每場 0.06 次）換成收霧斬——放血斬的敵人版，數值相同、只給敵人。"""
    last = next(p for p in library.units["sect_mist_lock_master"].phases if p.id == "return_to_one")
    assert last.skills == ("skill_charged_cleave", "skill_first_strike", "skill_mist_rend")
    rend, source = library.skills["skill_mist_rend"], library.skills["skill_rending_strike"]
    assert rend.enemy_only
    assert not source.enemy_only
    for field in ("ap_cost", "shape", "effects", "cost", "condition", "weapon_req"):
        assert getattr(rend, field) == getattr(source, field), field


def test_the_three_pillars_phase_uses_thunder_clap(library: ContentLibrary) -> None:
    """CB-2e：三柱階段的聚雷（每回合 7%）換成現有的雷鳴震波；第 2 階段的聚雷不動。"""
    lord = library.units["rift_shard_lord"]
    assert lord.skills == ("skill_thunder_clap", "skill_shard_erosion", "skill_spark_chain")
    pulse = next(p for p in lord.phases if p.id == "rift_pulse")
    assert pulse.skills is not None
    assert "skill_cluster_bolt" in pulse.skills
    overload = next(p for p in lord.phases if p.id == "core_overload")
    assert overload.skills is not None
    assert "skill_rift_flicker" in overload.skills  # BAL-21c：skill_blink 換界隙閃擊
    assert "skill_blink" not in overload.skills


def test_the_ai_values_self_concealment(library: ContentLibrary) -> None:
    """CB-2e：AI 友方增益表補 concealed: 2（玩法 PM：只能是 2）。"""
    assert library.ai_profiles.ally_status_values["concealed"] == 2


def test_an_affix_whose_move_is_already_known_is_not_applied(library: ContentLibrary) -> None:
    """硬殼帶 parry_riposte：已有這招的甲蟲不套，改抽其他詞綴（18.2；走 applicable_affixes）。"""
    catalog = library.enemy_catalog()
    beetle = catalog.template("lava_beetle")
    assert "skill_parry_riposte" in beetle.skills
    assert catalog.affix_problem(beetle, "hard_shelled") is not None
    assert catalog.applicable_affixes(beetle, ("hard_shelled", "regenerating")) == ["regenerating"]
