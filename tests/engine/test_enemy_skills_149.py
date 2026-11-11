"""#149 敵人補招的引擎行為（CB-2a）：實際跑引擎驗證新招、冰鶴使緩速、三柱階段與詞綴帶招。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.content.battle import UnitTemplate
from trpg.engine import BattleState, ResolveResult, UseSkill, legal_actions, resolve
from trpg.engine.events import AttackRolled, DamageDealt, StatusApplied, SurfaceChanged
from trpg.engine.events.skills import SkillUsed
from trpg.shared.types import Attribute, Team

SEEDS = 60
SLUG_INT = 8
OLD_SLUG_INT = 4


def _arena(template: UnitTemplate, *, distance: int = 1, heroes: int = 1) -> BattleState:
    """目標（英雄）是 U1，被測的敵人是 U2（其餘英雄排在後面），輪到 U2。"""
    target, foe = (3, 3), (3 + distance, 3)
    extra = [(3, 3 + i) for i in range(1, heroes)]
    m = make_map(FLAT7, ally=[target, *extra], enemy=[foe])
    spawns = [
        spawn(Team.ALLY, target, "hero_fighter", skills=None),
        spawn(Team.ENEMY, foe, template),
        *(spawn(Team.ALLY, xy, "hero_archer", skills=None) for xy in extra),
    ]
    return give_turn(make_state(m, spawns), U2)


def _reseed(state: BattleState, seed: int) -> BattleState:
    fresh = state.clone()
    fresh.rng_state = (
        make_state(
            make_map(FLAT7, ally=[(0, 0)], enemy=[(6, 6)]),
            [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (6, 6), "bandit")],
            seed=seed,
        )
    ).rng_state
    return fresh


def _cast_at_u1(state: BattleState, skill_id: str, seed: int) -> ResolveResult:
    state = _reseed(state, seed)
    actions = [
        a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == skill_id
    ]
    assert actions, f"{skill_id} 沒有合法動作"
    u1_pos = state.units[U1].pos
    aimed = [a for a in actions if a.target_id == U1 or a.target_pos == u1_pos]
    return resolve(state, (aimed or actions)[0])


def _template(name: str) -> UnitTemplate:
    return library().enemy_catalog().template(name)


CASES = [
    ("magma_slug", "skill_slime_glob", 3, "slow"),
    ("fire_dust_bat", "skill_cinder_dive", 3, "burning"),
    ("sulfur_beast", "skill_venom_gore", 1, "poison"),
    ("frost_crane_archer", "skill_frost_feather", 3, "slow"),
]


@pytest.mark.parametrize(("unit", "skill_id", "distance", "status"), CASES)
def test_new_move_deals_damage_and_applies_its_status(
    unit: str, skill_id: str, distance: int, status: str
) -> None:
    state = _arena(_template(unit), distance=distance)
    landed = 0
    for seed in range(SEEDS):
        result = _cast_at_u1(state, skill_id, seed)
        assert any(isinstance(e, SkillUsed) for e in result.events)
        applied = [
            e
            for e in result.events
            if isinstance(e, StatusApplied) and e.status_id == status and e.target_id == U1
        ]
        if applied:
            landed += 1
            assert any(isinstance(e, DamageDealt) and e.target_id == U1 for e in result.events)
    assert landed > 0, f"{SEEDS} 個種子都沒有對目標施加 {status}"


def test_slime_leaves_no_surface() -> None:
    state = _arena(_template("magma_slug"), distance=3)
    for seed in range(SEEDS):
        result = _cast_at_u1(state, "skill_slime_glob", seed)
        assert not any(isinstance(e, SurfaceChanged) for e in result.events)


def test_slime_has_range_three() -> None:
    near = _arena(_template("magma_slug"), distance=3)
    assert any(
        isinstance(a, UseSkill) and a.skill_id == "skill_slime_glob" and a.target_id == U1
        for a in legal_actions(near)
    )


def test_frost_crane_slows_with_a_bow() -> None:
    frost = _template("frost_crane_archer")
    assert frost.weapon == "bow"
    skill = library().skills["skill_frost_feather"]
    status = next(e for e in skill.effects if e.type == "apply_status")
    assert status.condition is None


@pytest.mark.parametrize(
    ("unit", "phase_skills"),
    [
        (
            "rift_shard_lord",
            ("skill_cluster_bolt", "skill_shard_erosion", "skill_spark_chain"),
        ),
        ("ashen_heart", ("skill_lava_spout", "skill_fire_bolt", "skill_ashen_oath")),
        (
            "sect_mist_lock_master",
            ("skill_cluster_bolt", "skill_mist_shift", "skill_guardian_aegis"),
        ),
    ],
)
def test_first_boss_phase_can_cast_three_moves(
    unit: str, phase_skills: tuple[str, str, str]
) -> None:
    template = library().units[unit]
    assert set(template.skills) == set(phase_skills)
    for skill_id in phase_skills:
        state = _arena(template, distance=2, heroes=2)
        result = _cast_at_u1(state, skill_id, 0)
        assert any(isinstance(e, SkillUsed) and e.skill_id == skill_id for e in result.events)


@pytest.mark.parametrize(
    ("unit", "affix", "skill_id"),
    [
        ("mist_wolf", "mist_veiled", "skill_mist_shift"),
        ("sect_swordsman", "heart_linked", "skill_guardian_aegis"),
        ("ember_lizard", "hard_shelled", "skill_parry_riposte"),
    ],
)
def test_affix_adds_one_castable_move(unit: str, affix: str, skill_id: str) -> None:
    catalog = library().enemy_catalog()
    base = catalog.template(unit)
    elite = catalog.with_affix(base, affix)
    assert elite.skills == (*base.skills, skill_id)
    assert "elite" in elite.tags
    # 霧隱的開場隱蔽不影響能不能施放
    state = _arena(elite, distance=2, heroes=2)
    result = _cast_at_u1(state, skill_id, 0)
    assert any(isinstance(e, SkillUsed) and e.skill_id == skill_id for e in result.events)


def test_slime_accuracy_follows_intelligence_eight() -> None:
    """CB-2d：蛞蝓智力 8，黏液的命中判定實際帶入 8，比舊的 4 高。"""
    current = _template("magma_slug")
    assert current.attributes[Attribute.INT] == SLUG_INT
    old = current.model_copy(
        update={"attributes": {**current.attributes, Attribute.INT: OLD_SLUG_INT}}
    )
    rolls = {}
    for value, template in ((SLUG_INT, current), (OLD_SLUG_INT, old)):
        result = _cast_at_u1(_arena(template, distance=3), "skill_slime_glob", 0)
        roll = next(e for e in result.events if isinstance(e, AttackRolled))
        assert roll.attack_value == value
        rolls[value] = roll
    assert rolls[SLUG_INT].hit_modifier > rolls[OLD_SLUG_INT].hit_modifier
