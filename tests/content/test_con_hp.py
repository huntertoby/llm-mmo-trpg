"""體質與最大 HP（Phase 3-7）：公式、係數在 YAML、內容遷移後最終 HP 不變。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, template
from trpg.content.rules import CoreRules
from trpg.engine.lifecycle import make_unit
from trpg.shared.types import Attribute, Pos, Team, UnitId

# 遷移前（Phase 3-6）每個範本與 build 英雄的 ``max_hp``，亦即遷移後必須維持的最終 HP。
# X10-2b：數值 ×10（量類換算；註解裡的舊數字維持換算前單位）。
OLD_HP = {
    "bandit": 350,  # BAL-4b：基礎 HP ×1.2（24→29）
    "bandit_guard": 350,
    "bandit_archer": 310,  # BAL-4b（26→31）
    "bandit_archer_guard": 310,
    "bandit_rookie": 270,  # 6F-4 C1 新手第 1 場；2026-11-21 使用者改值（基礎 210 ＋ 體質 60）
    "bandit_rookie_terrace": 210,  # CB-2d 梯田固定戰（15 ＋ 體質 12 的 6）
    "bandit_archer_rookie": 190,  # 6F-4 C1
    "bandit_boss": 800,
    "bandit_captain": 570,  # BAL-6 新增（45 加體質 14 的 12 點）
    "bandit_shieldbearer": 360,  # BAL-4b（20→24）
    "bandit_shieldbearer_guard": 360,
    "bandit_warlord": 840,  # BAL-9c：基礎 HP ×700‰（原型專用，原 110）
    "gear_tester_g2": 600,  # 3G-G2 新增
    "gear_tester_g3a": 600,  # 3G-G3a 新增
    "gear_tester_g3b": 600,  # 3G-G3b 新增
    "gear_tester_g3b_sentinel": 460,  # 3G-G3b 新增
    "gear_tester": 600,  # 3G-G1 新增（遷移之後）：範本的 HP，不含裝備加成
    "build:build_assassin": 590,  # BAL-12d：HP +20%（44→53）
    "build:build_banisher": 400,
    "build:build_bomber": 400,
    "build:build_charger": 600,
    "build:build_detonator": 400,
    "build:build_runeweaver": 400,
    "build:build_fire": 400,
    "build:build_gambler": 560,
    "build:build_guardian": 600,
    "build:build_healer": 400,
    "build:build_push": 600,
    "build:build_ranged": 460,
    "build:build_seer": 400,
    "build:build_storm": 400,
    "build:build_striker": 400,
    "build:build_summoner": 420,
    "build:build_support": 400,
    "build:build_tank": 600,
    "build:build_telekinesis": 400,
    "build:build_trapper": 400,
    "build:build_wallburn": 600,
    "build:build_warlock": 400,
    "build:build_winged": 440,
    "hero_archer": 460,
    "hero_fighter": 600,
    "hero_mage": 400,
    "hero_stormcaller": 400,
    "sim_companion_archer": 460,
    "sim_companion_fighter": 600,
    "sim_duelist": 600,
    "variant_vanguard": 600,  # 3-25a 新增：戰士的數值
    "variant_tidecaller": 400,  # 3-25a 新增：法師的數值
    "variant_slinger": 460,  # 3-25a 新增：弓手的數值
    "std_enemy_t1": 300,
    "std_enemy_t2": 390,
    "std_enemy_t3": 490,
    "std_enemy_t4": 620,
    "std_enemy_t5": 770,
    "summon_afterimage": 140,
    "summon_bomb_puppet": 80,  # 3-33e2a 新增
    "summon_earth_wall": 200,
    "summon_foxfire_decoy": 10,  # 3R-2 新增（種族技「狐火誘餌」）
    "summon_elemental_spirit": 140,
    "summon_fire_spirit": 140,  # 3-33e1 新增
    "summon_golem": 240,
    "summon_hawk": 80,
    "summon_ice_spirit": 140,
    "summon_shade": 100,
    "summon_skeleton_warrior": 200,
    "summon_thunder_spirit": 140,
    "summon_war_totem": 180,
    "summon_war_wolf": 140,
    "summon_vine": 160,  # 3-33e2b 新增
    "summon_guardian_spirit": 140,  # 3-33e2b 新增
    "summon_pull_totem": 180,  # 3-33e2b 新增
    "summon_plateau_totem": 180,  # 3-33e2b 新增
    "summon_water_sprite": 120,
    "summon_mist_shade": 60,  # 5F-1b 新增（霧中劍客的霧影分身）
    "training_dummy": 3000,
    "training_dummy_moving": 3000,  # TR-1：靶場會動的木樁（數值同 training_dummy）
    "sect_acolyte": 220,  # 5A-3 新增（雲嶺）
    "sect_swordsman": 360,  # 5A-3 新增（雲嶺）
    "sect_talisman_caster": 240,  # 5A-3 新增（雲嶺）
    "sect_shield_disciple": 360,  # RG-1 新增（雲嶺盾兵，照盜賊盾衛）
    "sect_alchemist": 320,  # 5A-3 新增（雲嶺）
    "sect_warrior_monk": 580,  # 5A-3 新增（雲嶺）
    "sect_array_disciple": 260,  # 5A-3 新增（雲嶺）
    "sect_mist_walker": 240,  # 5A-3 新增（雲嶺）
    "sect_crane_archer": 260,  # 5A-3 新增（雲嶺）
    "sect_puppeteer": 240,  # 5A-3 新增（雲嶺）
    "sect_array_stone": 480,  # 5A-3 新增（雲嶺）
    "sect_steward": 620,  # 5A-3 新增（雲嶺）
    "sect_mist_swordsman": 360,  # 5F-1b 新增（雲嶺懸賞「霧中劍客」本體）
    "sect_mist_lock_master": 1320,  # 5F-2 新增（雲嶺 Boss）；5F-2b HP 90 → 120
    "sect_summit_array_stone": 480,  # 5F-2 新增（雲頂觀陣眼）；5F-2b HP 30→40→30（玩法 PM 代決）
    "rift_shard_lord": 3920,  # 5F-3 新增（賽季 Boss 碎晶之主）
    "rift_pillar_mist": 600,  # 5F-3 新增（源晶柱）
    "rift_pillar_thunder": 600,
    "rift_pillar_fire": 600,
    "rift_crystal_golem": 380,  # 5F-3 新增（晶傀儡）
    "mist_wolf": 220,  # 5A-3 新增（雲嶺）
    "mountain_leopard": 260,  # 5A-3 新增（雲嶺）
    "stoneback_bear": 620,  # 5A-3 新增（雲嶺）
    "thunder_hawk": 140,  # 5A-3 新增（雲嶺）
    "mist_wraith": 220,  # 5A-3 新增（雲嶺）
    "shard_golem": 480,  # 5A-3 新增（雲嶺）
    # 5F-5a 新增（灰燼荒原：熔岩獸群、熔核領主、寒燼蜥、熔晶魅、灰燼之心、餘燼幼蜥）
    "ember_lizard": 180,
    "heart_ember_lizard": 180,  # 5F-5b：灰燼之心戰的殼縫餘燼蜥（同餘燼蜥）
    "ash_hound": 220,
    "lava_beetle": 560,
    "fire_dust_bat": 160,
    "lava_tortoise": 500,
    "molten_shell_trooper": 480,  # RG-1 新增（荒原盾兵）
    "ashen_berserker": 460,  # RG-2 新增（荒原狂戰士）
    "magma_slug": 480,
    "sulfur_beast": 400,
    "scorched_colossus": 700,
    "furnace_matriarch": 560,
    "molten_lord": 880,
    "frost_ember_lizard": 200,
    "molten_wraith": 220,
    "ashen_heart": 1540,  # 2026-11-21 使用者改值（基礎 1360 ＋ 體質 180）
    "summon_ember_whelp": 80,
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
    assert (core.hp_con_base, core.hp_per_con_point, core.level_hp_permille) == (100, 3, 50)


@pytest.mark.parametrize(("con", "expected"), [(80, 540), (100, 600), (140, 720)])
def test_max_hp_by_constitution(con: int, expected: int) -> None:
    core = library().ruleset.core
    assert core.max_hp_for(600, con) == expected


def test_max_hp_floor_is_one() -> None:
    assert library().ruleset.core.max_hp_for(5, 1) == 1


@pytest.mark.parametrize(("con", "expected"), [(80, 340), (100, 400), (140, 520)])
def test_engine_unit_hp_uses_constitution(con: int, expected: int) -> None:
    lib = library()
    base = lib.unit("hero_mage")  # 基礎 HP 400、體質 100（X10-2b ×10）
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
    assert unit.max_hp == bandit.max_hp + 60  # 範本基礎 HP ＋ (120 − 100) × 3


def test_migration_keeps_every_template_final_hp() -> None:
    final = _final_hp()
    assert set(final) == set(OLD_HP)
    assert final == OLD_HP


def test_core_rules_type() -> None:
    assert isinstance(library().ruleset.core, CoreRules)
