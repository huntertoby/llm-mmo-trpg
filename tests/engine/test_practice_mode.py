"""靶場測試模式（Phase PR-1，#147；``docs/design/21-探索地圖與城鎮.md`` 21.5）：全部實際跑引擎。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.cli.battle import cmd_replay
from trpg.content.maps import MapDef
from trpg.content.skills import SkillDef
from trpg.engine import (
    Attack,
    BattleState,
    EndTurn,
    Move,
    ResolveResult,
    Run,
    UseRaceSkill,
    UseSkill,
    resolve,
    start_battle,
)
from trpg.engine.actions import Action, Shove, Trip
from trpg.engine.battle import simulate_preview
from trpg.engine.effects import DamageEffect, run_effects
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    ManeuverRolled,
    SkillCooldownChanged,
    StatusSaveRolled,
    TurnEnded,
    UnitDowned,
)
from trpg.engine.ids import PRONE
from trpg.engine.practice import PracticeRules
from trpg.engine.preview import preview
from trpg.engine.runner import BattleLog, log_replay_problem, replay, run_battle
from trpg.engine.setup import BattleSetup
from trpg.shared.types import Element, Pos, Team, UnitId

HERO = UnitId("unit_0001")
DUMMY = UnitId("unit_0002")
OTHER = UnitId("unit_0003")
FLAT = "0000000\n0000000\n0000000"
CD_SKILL = make_skill(
    "skill_practice_cd",
    {"type": "single", "range": 5},
    [{"type": "damage", "dice": "1d4", "element": "fire"}],
    cost={"mana": 5, "cooldown": 3},
)
LIMITED_SKILL = make_skill(
    "skill_practice_once",
    {"type": "single", "range": 5},
    [{"type": "damage", "dice": "1d4", "element": "fire"}],
    cost={"mana": 5, "uses_per_battle": 1},
)
STUN_SKILL = make_skill(
    "skill_practice_stun",
    {"type": "single", "range": 5},
    [{"type": "apply_status", "status": "root", "duration": 1}],
)
SKILLS = (CD_SKILL, LIMITED_SKILL, STUN_SKILL)


def _setup(
    *,
    practice: bool = True,
    game_map: MapDef | None = None,
    hero_at: tuple[int, int] = (1, 1),
    dummy_at: tuple[int, int] = (2, 1),
    other: bool = False,
    race: str | None = None,
    max_rounds: int | None = None,
) -> BattleSetup:
    hero = caster_template(SKILLS, race=race)
    spawns = [
        spawn(Team.ALLY, hero_at, hero),
        spawn(Team.ENEMY, dummy_at, "training_dummy"),
    ]
    if other:
        spawns.append(spawn(Team.ENEMY, (5, 2), no_reactions("bandit")))
    mapped = game_map if game_map is not None else make_map(FLAT, enemy=[(6, 2), (6, 1), (6, 0)])
    setup = make_setup(mapped, spawns, skills=SKILLS, max_rounds=max_rounds)
    return setup.model_copy(update={"practice": PracticeRules() if practice else None})


def _state(**kwargs: object) -> BattleState:
    return give_turn(start_battle(_setup(**kwargs), 3), HERO)  # type: ignore[arg-type]


def _of[E: EventBase](result: ResolveResult, cls: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, cls)]


def _attack() -> Attack:
    return Attack(unit_id=HERO, target_id=DUMMY)


def _cast(skill: SkillDef, target: UnitId = DUMMY) -> UseSkill:
    return UseSkill(unit_id=HERO, skill_id=skill.id, target_id=target)


def _passed(result: ResolveResult) -> bool:
    return any(e.unit_id == HERO for e in _of(result, TurnEnded))


# --------------------------------------------------------------------- 冷卻、次數、資源


def test_cooldown_is_cleared_after_cast() -> None:
    result = resolve(_state(), _cast(CD_SKILL))
    assert result.state.units[HERO].cooldowns == {}
    assert _of(result, SkillCooldownChanged)[-1].remaining == 0


def test_uses_per_battle_are_not_counted() -> None:
    first = resolve(_state(), _cast(LIMITED_SKILL)).state
    assert first.units[HERO].skill_uses == {}
    resolve(give_turn(first, HERO), _cast(LIMITED_SKILL))  # 第二次仍合法


def test_race_skill_uses_are_not_counted() -> None:
    state = _state(race="human")
    result = resolve(state, UseRaceSkill(unit_id=HERO))
    assert result.state.units[HERO].skill_uses == {}
    resolve(give_turn(result.state, HERO), UseRaceSkill(unit_id=HERO))


def test_every_resource_is_full_after_an_action() -> None:
    state = _state()
    hero = state.units[HERO]
    hero.ap, hero.stamina, hero.mana, hero.hp, hero.source = 3, 0, 0, 1, 0
    hero.cooldowns, hero.form_cooldowns = {CD_SKILL.id: 2}, {"form_x": 2}
    hero.skill_uses = {LIMITED_SKILL.id: 1}
    me = resolve(state, Move(unit_id=HERO, path=(Pos(x=1, y=1), Pos(x=1, y=0)))).state.units[HERO]
    core = state.ruleset.core
    assert me.ap == core.ap_per_turn + core.ap_carry_max
    assert (me.stamina, me.mana, me.hp) == (me.max_stamina, me.max_mana, me.max_hp)
    assert me.source == core.source_max
    assert (me.cooldowns, me.form_cooldowns, me.skill_uses) == ({}, {}, {})


def test_ammo_is_refilled() -> None:
    gunner = template("hero_fighter", reactions=[], skills=())
    setup = make_setup(
        make_map(FLAT, enemy=[(6, 2)]),
        [
            spawn(Team.ALLY, (1, 1), gunner, weapon="pistol"),
            spawn(Team.ENEMY, (2, 1), "training_dummy"),
        ],
    ).model_copy(update={"practice": PracticeRules()})
    state = give_turn(start_battle(setup, 3), HERO)
    magazine = state.units[HERO].weapon.magazine
    assert magazine > 0
    state.units[HERO].ammo = 0
    me = resolve(state, Run(unit_id=HERO)).state.units[HERO]
    assert me.ammo == magazine


def test_run_can_be_repeated_and_keeps_its_bonus() -> None:
    state = _state()
    first = resolve(state, Run(unit_id=HERO)).state
    me = first.units[HERO]
    assert me.ran_this_turn is False
    assert me.move_points == state.units[HERO].move_points + state.ruleset.core.run_move_bonus
    resolve(first, Run(unit_id=HERO))


# --------------------------------------------------------------------- 自動過輪


@pytest.mark.parametrize(
    "action",
    [
        pytest.param(_attack(), id="attack"),
        pytest.param(_cast(CD_SKILL), id="skill"),
        pytest.param(UseRaceSkill(unit_id=HERO), id="race_skill"),
    ],
)
def test_casts_and_attacks_pass_the_round(action: Action) -> None:
    result = resolve(_state(race="human"), action)
    assert _passed(result)
    assert result.state.active_unit != HERO


@pytest.mark.parametrize(
    "action",
    [
        pytest.param(Move(unit_id=HERO, path=(Pos(x=1, y=1), Pos(x=1, y=0))), id="move"),
        pytest.param(Run(unit_id=HERO), id="run"),
        pytest.param(Shove(unit_id=HERO, target_id=DUMMY), id="shove"),
        pytest.param(Trip(unit_id=HERO, target_id=DUMMY), id="trip"),
    ],
)
def test_basic_actions_do_not_pass_the_round(action: Action) -> None:
    result = resolve(_state(), action)
    assert not _passed(result)
    assert result.state.active_unit == HERO


def test_attacking_only_air_still_counts_by_action_kind() -> None:
    """打物件也是普攻：照動作種類過輪（21.5 第 4 點「不論有沒有打到木樁」）。"""
    game_map = make_map(FLAT, objects=[(3, 1, "crate")], enemy=[(6, 2)])
    state = _state(game_map=game_map, dummy_at=(6, 0))
    obj = next(iter(state.objects))
    result = resolve(state, Attack(unit_id=HERO, target_object_id=obj))
    assert _passed(result)


def test_auto_pass_waits_for_the_paused_decision() -> None:
    fighter = template("hero_fighter", reactions=[], skills=())  # 近戰普攻才會被格擋
    setup = make_setup(
        make_map(FLAT, enemy=[(6, 2)]),
        [spawn(Team.ALLY, (1, 1), fighter), spawn(Team.ENEMY, (2, 1), "training_dummy")],
    ).model_copy(update={"practice": PracticeRules()})
    state = give_turn(start_battle(setup, 3), HERO)
    dummy = state.units[DUMMY]
    block = library().ruleset.reactions.default_rules
    dummy.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in block)
    dummy.stamina = dummy.max_stamina = 99
    paused = resolve(state, _attack())
    assert paused.pending is not None
    assert not _passed(paused) and paused.state.active_unit == HERO
    assert _passed(answered(paused))


def test_preview_does_not_pass_or_refill() -> None:
    state = _state()
    low, high = simulate_preview(state, _cast(CD_SKILL))
    for sim in (low, high):
        assert sim.state.active_unit == HERO
        assert sim.state.units[HERO].ap == state.units[HERO].ap - (CD_SKILL.ap_cost or 0)
        assert sim.state.units[HERO].cooldowns


# --------------------------------------------------------------------- 必中與對抗


def test_natural_one_still_hits_the_dummy_and_cannot_crit() -> None:
    result = resolve(with_rolls(_state(), [(20, 1)]), _attack())
    rolled = _of(result, AttackRolled)[0]
    assert rolled.natural == 1 and rolled.hit and not rolled.crit
    assert _of(result, DamageDealt)


def test_natural_twenty_on_the_dummy_is_a_crit() -> None:
    rolled = _of(resolve(with_rolls(_state(), [(20, 20)]), _attack()), AttackRolled)[0]
    assert rolled.hit and rolled.crit


def test_practice_keeps_rng_consumption_of_a_landed_attack() -> None:
    real = resolve(with_rolls(_state(practice=False), [(20, 18)]), _attack())
    practice = resolve(with_rolls(_state(), [(20, 18)]), _attack())
    assert _of(real, AttackRolled)[0].hit
    assert practice.state.rng_state == real.state.rng_state


def test_only_tagged_targets_are_always_hit_in_practice() -> None:
    state = with_rolls(_state(other=True, dummy_at=(6, 0), hero_at=(4, 2)), [(20, 1)])
    rolled = _of(resolve(state, Attack(unit_id=HERO, target_id=OTHER)), AttackRolled)[0]
    assert rolled.natural == 1 and not rolled.hit


def test_status_save_on_the_dummy_always_succeeds() -> None:
    result = resolve(with_rolls(_state(), [(20, 1)]), _cast(STUN_SKILL))
    assert _of(result, StatusSaveRolled)[0].applied
    assert result.state.units[DUMMY].has_status("root")


def test_shove_and_trip_contests_always_succeed() -> None:
    shove = resolve(with_rolls(_state(), [(20, 1)]), Shove(unit_id=HERO, target_id=DUMMY))
    assert _of(shove, ManeuverRolled)[0].success
    assert shove.state.units[DUMMY].xy == (3, 1)  # 被推走不歸位
    trip = resolve(with_rolls(_state(), [(20, 1)]), Trip(unit_id=HERO, target_id=DUMMY))
    assert _of(trip, ManeuverRolled)[0].success
    assert trip.state.units[DUMMY].has_status(PRONE)


def test_preview_shows_full_chance_against_the_dummy() -> None:
    state = _state()
    attack = preview(state, _attack())
    assert attack.hit_chance == 1
    assert attack.crit_chance is not None and 0 < attack.crit_chance < 1
    stun = preview(state, _cast(STUN_SKILL))
    assert stun.targets[0].status_chances[0].apply_chance == 1
    assert preview(state, Shove(unit_id=HERO, target_id=DUMMY)).hit_chance == 1


# --------------------------------------------------------------------- 不倒下


def _lethal(target: UnitId) -> DamageEffect:
    return DamageEffect(target_id=target, mode="lethal", cause="status", element=Element.FIRE)


def test_hero_never_goes_down() -> None:
    result = run_effects(_state(), [_lethal(HERO)])
    assert not _of(result, UnitDowned)
    assert _of(result, DamageDealt)[0].hp_after == 1
    hero = result.state.units[HERO]
    assert hero.alive and hero.hp == hero.max_hp


def test_dummy_stays_at_one_then_refills_next_round() -> None:
    result = run_effects(_state(), [_lethal(DUMMY)])
    assert not _of(result, UnitDowned)
    assert result.state.units[DUMMY].hp == 1 and result.state.units[DUMMY].alive
    assert not result.state.ended
    state = result.state
    start_round = state.round
    while state.round == start_round:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    assert state.units[DUMMY].hp == state.units[DUMMY].max_hp


def test_ordinary_enemy_still_goes_down_in_practice() -> None:
    state = _state(other=True, dummy_at=(6, 0))
    result = run_effects(state, [_lethal(OTHER)])
    assert [e.unit_id for e in _of(result, UnitDowned)] == [OTHER]


def test_dummy_pushed_into_deadly_terrain_returns_home_full() -> None:
    terrain = ".......\n...x...\n......."
    game_map = make_map(FLAT, terrain, enemy=[(6, 2)])
    state = _state(game_map=game_map, hero_at=(1, 1), dummy_at=(2, 1))
    state.units[DUMMY].hp = 50
    result = resolve(with_rolls(state, [(20, 15)]), Shove(unit_id=HERO, target_id=DUMMY))
    dummy = result.state.units[DUMMY]
    assert dummy.alive and dummy.xy == (2, 1)
    assert dummy.hp == dummy.max_hp
    assert not _of(result, UnitDowned)


# --------------------------------------------------------------------- 實戰與技能工坊不受影響


def test_no_flag_means_no_practice_rules() -> None:
    state = with_rolls(_state(practice=False), [(20, 1)])
    result = resolve(state, _attack())
    assert not _of(result, AttackRolled)[0].hit
    assert result.state.active_unit == HERO and not _passed(result)
    assert (
        result.state.units[HERO].ap
        == state.units[HERO].ap - state.ruleset.core.basic_attack_ap_cost
    )


def test_workshop_dummy_without_flag_can_go_down() -> None:
    result = run_effects(_state(practice=False), [_lethal(DUMMY)])
    assert [e.unit_id for e in _of(result, UnitDowned)] == [DUMMY]


def test_no_flag_cooldown_is_kept() -> None:
    result = resolve(_state(practice=False), _cast(CD_SKILL))
    assert result.state.units[HERO].cooldowns == {CD_SKILL.id: 3}


# --------------------------------------------------------------------- 重播


def test_practice_battle_log_replays_identically(tmp_path: Path) -> None:
    setup = _setup(max_rounds=6)
    run = run_battle(setup, 11)
    assert run.state.end_reason == "round_limit"
    assert not any(isinstance(e, UnitDowned) for e in run.events)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    assert log.setup.practice == PracticeRules()
    assert log_replay_problem(log) is None
    again = replay(log.setup, log.seed, log.actions)
    assert [e.model_dump_json() for e in again.events] == [e.model_dump_json() for e in run.events]
    assert again.state.rng_state == run.state.rng_state
    path = tmp_path / "practice.json"
    path.write_text(log.model_dump_json(), encoding="utf-8")
    out: list[str] = []

    class _Out:
        def write(self, text: str) -> int:
            out.append(text)
            return len(text)

    assert cmd_replay(path, _Out()) == 0  # type: ignore[arg-type]
