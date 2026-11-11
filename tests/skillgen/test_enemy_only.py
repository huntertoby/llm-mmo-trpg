"""Phase 5F-3b：``enemy_only`` 技能不進任何玩家技能池，敵人照常可以用。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.attribute_text import keyword_supply
from trpg.content.player_pool import is_player_skill, player_skills
from trpg.skillgen import candidates
from trpg.skillgen.keywords import keyword_pools
from trpg.skillgen.option_params import _ref_choices
from trpg.skillgen.proposal import grantable_skills

ENEMY_ONLY = frozenset(
    {
        "skill_mist_lock_peaks",
        "skill_mist_shift",
        "skill_rift_pulse_fire",
        "skill_rift_pulse_mist",
        "skill_rift_pulse_thunder",
        "skill_rift_shatter",
        "skill_rift_tremor",
        "skill_shard_erosion",
        "skill_summon_mist_shade",
        # 5F-5a 灰燼荒原的敵人技能（開發 PM 2026-11-03 通知）
        "skill_lava_spout",
        "skill_heart_inhale",
        "skill_heart_exhale",
        "skill_heart_meltdown",
        "skill_magma_breach",
        "skill_summon_ember_whelp",
        "skill_sulfur_breath",
        "skill_ember_bite",
        # CB-2a（#149）補招的敵人專用招
        "skill_slime_glob",
        "skill_cinder_dive",
        "skill_venom_gore",
        "skill_frost_feather",
        # CB-2e（#149）霧鎖真人第 3 階段的收霧斬
        "skill_mist_rend",
    }
)


def test_flagged_skills_are_exactly_the_enemy_skills() -> None:
    lib = library()
    assert {k for k, s in lib.skills.items() if s.enemy_only} == ENEMY_ONLY


def test_player_skills_excludes_enemy_only_and_keeps_order() -> None:
    lib = library()
    pool = player_skills(lib)
    assert not ENEMY_ONLY & set(pool)
    assert list(pool) == sorted(set(lib.skills) - ENEMY_ONLY)
    assert all(is_player_skill(s) for s in pool.values())


def test_enemy_only_flag_is_not_serialized_when_false() -> None:
    lib = library()
    assert "enemy_only" not in lib.skills["skill_blink"].model_dump()
    assert lib.skills["skill_mist_shift"].model_dump()["enemy_only"] is True


def test_enemies_still_use_their_skills() -> None:
    lib = library()
    lord = lib.units["rift_shard_lord"]
    phase_skills = {s for p in lord.phases for s in p.skills or ()}
    assert {"skill_rift_tremor", "skill_shard_erosion", "skill_rift_shatter"} <= phase_skills
    assert "skill_mist_shift" in lib.units["sect_mist_lock_master"].skills


def test_pool_entry_points_exclude_enemy_only() -> None:
    lib = library()
    for exclusive in (False, True):
        for starter in (False, True):
            pools = keyword_pools(lib, starter_only=starter, exclusive_only=exclusive)
            assert not ENEMY_ONLY & {s for ids in pools.values() for s in ids}
    for tier in range(1, 6):
        assert not ENEMY_ONLY & {s.id for s, _ in candidates._pool(lib, tier)}
        assert not ENEMY_ONLY & {s.id for s in candidates._general_pool(lib, tier)}
    assert not ENEMY_ONLY & set(grantable_skills(lib))
    assert not ENEMY_ONLY & {c.value for c in _ref_choices("skill", lib)}
    keywords = tuple(k.id for k in lib.keywords.keywords)
    for weapon in lib.weapons.values():
        assert not ENEMY_ONLY & {s.id for s in keyword_supply(lib, weapon, keywords)}
