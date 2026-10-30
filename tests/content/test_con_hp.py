"""體質與最大 HP（Phase 3-7）：公式、係數在 YAML、內容遷移後最終 HP 不變。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, template
from trpg.content.rules import CoreRules
from trpg.engine.lifecycle import make_unit
from trpg.shared.types import Attribute, Pos, Team, UnitId

# 遷移前（Phase 3-6）每個範本與 build 英雄的 ``max_hp``，亦即遷移後必須維持的最終 HP。
OLD_HP = {
    "bandit": 35,  # BAL-4b：基礎 HP ×1.2（24→29）
    "bandit_guard": 35,
    "bandit_archer": 31,  # BAL-4b（26→31）
    "bandit_archer_guard": 31,
    "bandit_boss": 80,
    "bandit_captain": 57,  # BAL-6 新增（45 加體質 14 的 12 點）
    "bandit_shieldbearer": 36,  # BAL-4b（20→24）
    "bandit_shieldbearer_guard": 36,
    "bandit_warlord": 84,  # BAL-9c：基礎 HP ×700‰（原型專用，原 110）
    "gear_tester_g2": 60,  # 3G-G2 新增
    "gear_tester_g3a": 60,  # 3G-G3a 新增
    "gear_tester_g3b": 60,  # 3G-G3b 新增
    "gear_tester_g3b_sentinel": 46,  # 3G-G3b 新增
    "gear_tester": 60,  # 3G-G1 新增（遷移之後）：範本的 HP，不含裝備加成
    "build:build_assassin": 50,
    "build:build_banisher": 40,
    "build:build_bomber": 40,
    "build:build_charger": 60,
    "build:build_detonator": 40,
    "build:build_runeweaver": 40,
    "build:build_fire": 40,
    "build:build_gambler": 56,
    "build:build_guardian": 60,
    "build:build_healer": 40,
    "build:build_push": 60,
    "build:build_ranged": 46,
    "build:build_seer": 40,
    "build:build_storm": 40,
    "build:build_striker": 40,
    "build:build_summoner": 42,
    "build:build_support": 40,
    "build:build_tank": 60,
    "build:build_telekinesis": 40,
    "build:build_trapper": 40,
    "build:build_wallburn": 60,
    "build:build_warlock": 40,
    "build:build_winged": 44,
    "hero_archer": 46,
    "hero_fighter": 60,
    "hero_mage": 40,
    "hero_stormcaller": 40,
    "sim_companion_archer": 46,
    "sim_companion_fighter": 60,
    "sim_duelist": 60,
    "variant_vanguard": 60,  # 3-25a 新增：戰士的數值
    "variant_tidecaller": 40,  # 3-25a 新增：法師的數值
    "variant_slinger": 46,  # 3-25a 新增：弓手的數值
    "std_enemy_t1": 30,
    "std_enemy_t2": 39,
    "std_enemy_t3": 49,
    "std_enemy_t4": 62,
    "std_enemy_t5": 77,
    "summon_afterimage": 14,
    "summon_bomb_puppet": 8,  # 3-33e2a 新增
    "summon_earth_wall": 20,
    "summon_foxfire_decoy": 1,  # 3R-2 新增（種族技「狐火誘餌」）
    "summon_elemental_spirit": 14,
    "summon_fire_spirit": 14,  # 3-33e1 新增
    "summon_golem": 24,
    "summon_hawk": 8,
    "summon_ice_spirit": 14,
    "summon_shade": 10,
    "summon_skeleton_warrior": 20,
    "summon_thunder_spirit": 14,
    "summon_war_totem": 18,
    "summon_war_wolf": 14,
    "summon_vine": 16,  # 3-33e2b 新增
    "summon_guardian_spirit": 14,  # 3-33e2b 新增
    "summon_pull_totem": 18,  # 3-33e2b 新增
    "summon_plateau_totem": 18,  # 3-33e2b 新增
    "summon_water_sprite": 12,
    "training_dummy": 300,
}


def _final_hp() -> dict[str, int]:
    lib = library()
    core = lib.ruleset.core
    rows = {t.id: core.template_max_hp(t) for t in lib.units.values()}
    rows.update(
        {s.template.id: core.template_max_hp(s.template) for s in lib.ruleset.summons.summons}
    )
    rows.update({"build:" + b.id: core.template_max_hp(b.hero) for b in lib.builds.sim_builds()})
    return rows


def test_coefficients_come_from_yaml() -> None:
    core = library().ruleset.core
    assert (core.hp_con_base, core.hp_per_con_point, core.level_hp_permille) == (10, 3, 50)


@pytest.mark.parametrize(("con", "expected"), [(8, 54), (10, 60), (14, 72)])
def test_max_hp_by_constitution(con: int, expected: int) -> None:
    core = library().ruleset.core
    assert core.max_hp_for(60, con) == expected


def test_max_hp_floor_is_one() -> None:
    assert library().ruleset.core.max_hp_for(5, 1) == 1


@pytest.mark.parametrize(("con", "expected"), [(8, 34), (10, 40), (14, 52)])
def test_engine_unit_hp_uses_constitution(con: int, expected: int) -> None:
    lib = library()
    base = lib.unit("hero_mage")  # 基礎 HP 40、體質 10
    attrs = {**base.attributes, Attribute.CON: con}
    unit = make_unit(
        UnitId("unit_1"),
        template=template("hero_mage", attributes=attrs),
        weapon=lib.weapons[base.weapon],
        team=Team.ALLY,
        pos=Pos(x=0, y=0),
        name="x",
        rules=lib.ruleset,
    )
    assert unit.max_hp == expected
    assert unit.hp == expected


def test_enemies_use_the_same_formula() -> None:
    lib = library()
    bandit = lib.unit("bandit")
    unit = make_unit(
        UnitId("unit_1"),
        template=bandit,
        weapon=lib.weapons[bandit.weapon],
        team=Team.ENEMY,
        pos=Pos(x=0, y=0),
        name="x",
        rules=lib.ruleset,
    )
    assert unit.max_hp == bandit.max_hp + 6  # 範本基礎 HP ＋ (12 − 10) × 3


def test_migration_keeps_every_template_final_hp() -> None:
    final = _final_hp()
    assert set(final) == set(OLD_HP)
    assert final == OLD_HP


def test_core_rules_type() -> None:
    assert isinstance(library().ruleset.core, CoreRules)
