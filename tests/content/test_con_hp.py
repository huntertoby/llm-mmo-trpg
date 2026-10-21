"""體質與最大 HP（Phase 3-7）：公式、係數在 YAML、內容遷移後最終 HP 不變。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library, template
from trpg.content.rules import CoreRules
from trpg.engine.lifecycle import make_unit
from trpg.shared.types import Attribute, Pos, Team, UnitId

# 遷移前（Phase 3-6）每個範本與 build 英雄的 ``max_hp``，亦即遷移後必須維持的最終 HP。
OLD_HP = {
    "bandit": 30,
    "bandit_archer": 26,
    "bandit_boss": 80,
    "bandit_shieldbearer": 32,
    "bandit_warlord": 110,
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
    "std_enemy_t1": 30,
    "std_enemy_t2": 39,
    "std_enemy_t3": 49,
    "std_enemy_t4": 62,
    "std_enemy_t5": 77,
    "summon_afterimage": 14,
    "summon_elemental_spirit": 14,
    "summon_skeleton_warrior": 20,
    "summon_war_totem": 18,
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
    assert unit.max_hp == 30  # 基礎 24 ＋ (12 − 10) × 3


def test_migration_keeps_every_template_final_hp() -> None:
    final = _final_hp()
    assert set(final) == set(OLD_HP)
    assert final == OLD_HP


def test_core_rules_type() -> None:
    assert isinstance(library().ruleset.core, CoreRules)
