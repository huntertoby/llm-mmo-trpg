"""Phase 5B-M3：三方混戰（``docs/phases/Phase5計畫.md`` 第 20 節）。

第三陣營 ``Team.THIRD`` 和我方、敵方都敵對：起始位置、勝負、AI 選目標、範圍技的敵我、反應、召喚物
歸屬、難度倍率與確定性。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    make_state,
    spawn,
    template,
)
from trpg.content.battle import UnitTemplate
from trpg.content.maps import MapDef
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.actions import Attack
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import DamageDealt, ReactionTriggered, ShieldGained, UnitSummoned
from trpg.engine.objectives import check_battle_end, check_round_end
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, BattleSetupError, UnitSpawn
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

FLAT = "\n".join(["0000000"] * 7)
U1, U2, U3, U4, U5 = (UnitId(f"unit_000{i}") for i in range(1, 6))

Placed = Sequence[tuple[tuple[int, int], UnitTemplate | str]]


def _map(allies: Placed, enemies: Placed, third: Placed = (), *, third_zone: bool = True) -> MapDef:
    m = make_map(FLAT, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    if third and third_zone:
        zones = dict(m.start_zones)
        zones[Team.THIRD] = tuple(p for p, _ in third)
        m = m.model_copy(update={"start_zones": zones})
    return m


def _spawns(allies: Placed, enemies: Placed, third: Placed) -> list[UnitSpawn]:
    result = [spawn(Team.ALLY, p, t) for p, t in allies]
    result += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    result += [spawn(Team.THIRD, p, t) for p, t in third]
    return result


def _state(allies: Placed, enemies: Placed, third: Placed = (), seed: int = 0) -> BattleState:
    return make_state(_map(allies, enemies, third), _spawns(allies, enemies, third), seed=seed)


def _hero(**overrides: object) -> UnitTemplate:
    return template("hero_fighter", reactions=[], skills=[], **overrides)


def _plain(base: str = "bandit", **overrides: object) -> UnitTemplate:
    return template(base, reactions=[], skills=[], **overrides)


def _always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 18 if sides == 20 else min(2, sides))


# ---------------------------------------------------------------------------
# 陣營關係與起始位置
# ---------------------------------------------------------------------------


def test_team_relations() -> None:
    assert Team.THIRD.display_name == "第三方"
    assert Team.THIRD.hostile_to(Team.ALLY) and Team.THIRD.hostile_to(Team.ENEMY)
    assert Team.ENEMY.hostile_to(Team.THIRD) and Team.ALLY.hostile_to(Team.ENEMY)
    assert not Team.THIRD.hostile_to(Team.THIRD)
    assert Team.ALLY.opponent is Team.ENEMY and Team.ENEMY.opponent is Team.ALLY
    assert Team.THIRD.opponent is Team.ALLY


def test_third_zone_is_optional_but_ally_and_enemy_are_required() -> None:
    m = _map([((0, 0), _hero())], [((6, 6), _plain())])
    assert Team.THIRD not in m.start_zones  # 驗證通過
    data = m.model_dump(mode="json")
    data["start_zones"] = {"ally": [[0, 0]], "third": [[3, 3]]}
    with pytest.raises(ValueError, match="start_zones 缺少 enemy"):
        MapDef.model_validate(data)


def test_third_spawns_in_its_zone() -> None:
    allies = [((0, 0), _hero())]
    enemies = [((6, 6), _plain())]
    third = [((0, 6), _plain("sect_swordsman"))]
    m = _map(allies, enemies, third)
    spawns = [s.model_copy(update={"position": None}) for s in _spawns(allies, enemies, third)]
    state = make_state(m, spawns)
    assert state.units[U3].team is Team.THIRD
    assert state.units[U3].xy == (0, 6)


def test_third_without_zone_spawns_next_to_enemy_zone() -> None:
    allies = [((0, 0), _hero())]
    enemies = [((6, 6), _plain()), ((5, 6), _plain())]
    third = [((0, 0), _plain("sect_swordsman")), ((0, 0), _plain("sect_acolyte"))]
    m = _map(allies, enemies, third, third_zone=False)
    spawns = [s.model_copy(update={"position": None}) for s in _spawns(allies, enemies, third)]
    state = make_state(m, spawns)
    # 敵方起始區 (6,6)、(5,6)；最近的空格依 (距離, y, x)：(5,5)、(6,5)、(4,6)
    assert [state.units[u].xy for u in (U4, U5)] == [(5, 5), (6, 5)]


def test_manual_position_wins_and_third_alone_is_not_enough() -> None:
    state = _state([((0, 0), _hero())], [((6, 6), _plain())], [((3, 3), _plain("sect_swordsman"))])
    assert state.units[U3].xy == (3, 3)
    m = _map([((0, 0), _hero())], [((6, 6), _plain())])
    no_enemy = [spawn(Team.ALLY, (0, 0), _hero()), spawn(Team.THIRD, (6, 6), _plain())]
    with pytest.raises(BattleSetupError):
        start_battle(make_setup(m, no_enemy), 0)


def test_opening_facing_of_third_looks_at_others() -> None:
    state = _state([((0, 3), _hero())], [((6, 3), _plain())], [((3, 0), _plain())])
    assert state.units[U3].facing == "south"


# ---------------------------------------------------------------------------
# 勝負
# ---------------------------------------------------------------------------


def _ended(state: BattleState) -> BattleState:
    ctx = Ctx(state)
    check_battle_end(ctx)
    return ctx.state


def test_enemy_wiped_but_third_alive_keeps_fighting() -> None:
    state = _state([((0, 0), _hero())], [((6, 6), _plain())], [((3, 3), _plain())])
    state.units[U2].downed = True
    state.units[U2].hp = 0
    assert not _ended(state).ended
    state.units[U3].downed = True
    state.units[U3].hp = 0
    done = _ended(state)
    assert done.ended and done.winner is Team.ALLY and done.end_reason == "eliminate"


def test_allies_wiped_is_a_loss_recorded_as_enemy_win() -> None:
    state = _state([((0, 0), _hero())], [((6, 6), _plain())], [((3, 3), _plain())])
    state.units[U2].downed = True
    state.units[U2].hp = 0
    state.units[U1].downed = True
    state.units[U1].hp = 0
    done = _ended(state)
    assert done.ended and done.winner is Team.ENEMY


def test_third_on_defend_point_loses_it() -> None:
    allies = [((0, 0), _hero())]
    enemies = [((6, 6), _plain())]
    third = [((3, 3), _plain())]
    m = make_map(
        FLAT,
        None,
        ally=[(0, 0)],
        enemy=[(6, 6)],
        objective={"kind": "defend", "rounds": 5, "tiles": [[3, 3]]},
    )
    state = make_state(m, _spawns(allies, enemies, third))
    ctx = Ctx(state)
    assert check_round_end(ctx)
    assert ctx.state.winner is Team.ENEMY and ctx.state.end_reason == "point_lost"


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_enemy_ai_attacks_adjacent_third() -> None:
    state = _state([((0, 0), _hero())], [((3, 3), _plain())], [((3, 4), _plain(max_hp=5))])
    action = UtilityAI(library().ai_profiles)(give_turn(state, U2))
    assert isinstance(action, Attack) and action.target_id == U3


def test_third_ai_attacks_both_sides() -> None:
    lib = library()
    near_enemy = _state([((0, 0), _hero())], [((3, 3), _plain(max_hp=5))], [((3, 4), _plain())])
    action = UtilityAI(lib.ai_profiles)(give_turn(near_enemy, U3))
    assert isinstance(action, Attack) and action.target_id == U2
    near_ally = _state([((3, 3), _hero(max_hp=5))], [((6, 0), _plain())], [((3, 4), _plain())])
    action = UtilityAI(lib.ai_profiles)(give_turn(near_ally, U3))
    assert isinstance(action, Attack) and action.target_id == U1


def test_ally_ai_attacks_third() -> None:
    state = _state([((3, 3), _hero())], [((6, 0), _plain())], [((3, 4), _plain(max_hp=5))])
    action = UtilityAI(library().ai_profiles)(give_turn(state, U1))
    assert isinstance(action, Attack) and action.target_id == U3


# ---------------------------------------------------------------------------
# 範圍技與反應
# ---------------------------------------------------------------------------

BLAST = make_skill(
    "skill_t_third_blast",
    {"type": "square3", "range": 4},
    [{"type": "damage", "dice": "1d4", "element": "fire", "affects": "enemies"}],
)
MEND = make_skill(
    "skill_t_third_mend",
    {"type": "square3", "range": 4},
    [{"type": "heal", "dice": "2d6", "affects": "allies"}],
)


def _skill_state(caster_team: Team) -> BattleState:
    """施放者 U1 在 (3,0)；(3,3) 是另一個陣營、(4,3) 是第三方、(2,3) 是施放者的同陣營。"""
    caster = caster_template([BLAST, MEND])
    other = Team.ENEMY if caster_team is not Team.ENEMY else Team.ALLY
    spawns = [
        spawn(caster_team, (3, 0), caster),
        spawn(other, (3, 3), _plain(max_hp=60)),
        spawn(Team.THIRD, (4, 3), _plain(max_hp=60)),
        spawn(caster_team, (2, 3), _plain(max_hp=60)),
    ]
    ally_cells = [s.position for s in spawns if s.team is Team.ALLY and s.position is not None]
    enemy_cells = [s.position for s in spawns if s.team is Team.ENEMY and s.position is not None]
    m = make_map(FLAT, None, ally=ally_cells, enemy=enemy_cells)
    state = make_state(m, spawns, skills=[BLAST, MEND])
    for unit in state.units.values():
        unit.hp = 30
    return give_turn(state, U1)


@pytest.mark.parametrize("caster_team", [Team.ALLY, Team.ENEMY])
def test_enemy_area_skill_hits_third_but_not_own_team(
    monkeypatch: pytest.MonkeyPatch, caster_team: Team
) -> None:
    _always_hit(monkeypatch)
    state = _skill_state(caster_team)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=BLAST.id, target_pos=Pos(x=3, y=3)))
    hit = {e.target_id for e in result.events if isinstance(e, DamageDealt)}
    assert hit == {U2, U3}
    healed = resolve(state, UseSkill(unit_id=U1, skill_id=MEND.id, target_pos=Pos(x=3, y=3)))
    hp = {u: healed.state.units[u].hp for u in (U2, U3, U4)}
    assert hp[U4] > 30 and hp[U2] == 30 and hp[U3] == 30


def test_third_blocks_enemy_attack(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    blocker = template("bandit", skills=[])  # 預設反應：格擋
    state = _state([((0, 0), _hero())], [((3, 3), _plain())], [((3, 4), blocker)])
    result = resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U3))
    reacted = [(e.unit_id, e.reaction) for e in result.events if isinstance(e, ReactionTriggered)]
    assert (U3, "block") in reacted


def test_kin_ward_only_protects_own_team(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    lib = library()
    swordsman = template("sect_swordsman", reactions=[], max_hp=60)
    # 第三方的修士被敵方攻擊：第三方的道童相護、敵方的道童不管
    state = _state(
        [((0, 0), _hero())],
        [((3, 2), _plain()), ((5, 3), lib.unit("sect_acolyte"))],
        [((3, 3), swordsman), ((2, 4), lib.unit("sect_acolyte"))],
    )
    result = resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U4))
    reacted = [(e.unit_id, e.reaction) for e in result.events if isinstance(e, ReactionTriggered)]
    assert reacted == [(U5, "kin_ward")]
    assert any(isinstance(e, ShieldGained) and e.unit_id == U4 for e in result.events)


def test_third_summon_belongs_to_third() -> None:
    caster = caster_template(["skill_summon_ice_spirit"])
    spawns = [
        spawn(Team.ALLY, (0, 0), _hero()),
        spawn(Team.ENEMY, (6, 6), _plain()),
        spawn(Team.THIRD, (3, 3), caster),
    ]
    m = make_map(FLAT, None, ally=[(0, 0)], enemy=[(6, 6)])
    state = give_turn(make_state(m, spawns), U3)
    result = resolve(
        state, UseSkill(unit_id=U3, skill_id="skill_summon_ice_spirit", target_pos=Pos(x=3, y=4))
    )
    [event] = [e for e in result.events if isinstance(e, UnitSummoned)]
    assert result.state.units[event.unit_id].team is Team.THIRD


# ---------------------------------------------------------------------------
# 難度倍率
# ---------------------------------------------------------------------------


def _scaled_hit(source: UnitId, target: UnitId, permille: int = 2000) -> int:
    allies = [((0, 0), _hero(max_hp=200))]
    enemies = [((6, 6), _plain(max_hp=200))]
    third = [((3, 3), _plain(max_hp=200))]
    m = _map(allies, enemies, third)
    state = start_battle(
        make_setup(m, _spawns(allies, enemies, third), enemy_damage_permille=permille), 0
    )
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=target, source_id=source, flat=10, cause="attack")])
    return next(e.amount for e in ctx.events if isinstance(e, DamageDealt))


def test_difficulty_scales_only_hits_on_allies() -> None:
    def scaled(source: UnitId, target: UnitId) -> bool:
        return _scaled_hit(source, target) > _scaled_hit(source, target, permille=1000)

    assert scaled(U2, U1)  # 敵方打我方
    assert scaled(U3, U1)  # 第三方打我方
    assert not scaled(U2, U3)  # 敵方打第三方
    assert not scaled(U3, U2)  # 第三方打敵方
    assert not scaled(U1, U3)  # 我方打第三方


# ---------------------------------------------------------------------------
# 整場與確定性
# ---------------------------------------------------------------------------


def _three_way_setup() -> BattleSetup:
    lib = library()
    allies = [((0, 2), "hero_fighter"), ((0, 3), "hero_archer"), ((0, 4), "hero_mage")]
    enemies = [((6, 2), "bandit"), ((6, 3), "bandit"), ((6, 4), "bandit_archer")]
    third = [((3, 0), "sect_swordsman"), ((4, 0), "sect_acolyte")]
    spawns = [
        UnitSpawn(
            template=lib.unit(t),
            weapon=lib.weapon_of(lib.unit(t)),
            team=team,
            position=p,
        )
        for team, group in ((Team.ALLY, allies), (Team.ENEMY, enemies), (Team.THIRD, third))
        for p, t in group
    ]
    return make_setup(_map(allies, enemies, third), spawns, max_rounds=30)


def test_three_way_battle_is_deterministic_and_replays() -> None:
    setup = _three_way_setup()
    first = run_battle(setup, 3)
    second = run_battle(setup, 3)
    assert first.state.ended
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
    teams = {u.id: u.team for u in first.state.units.values()}
    pairs = {
        (teams[e.source_id], teams[e.target_id])
        for e in first.events
        if isinstance(e, DamageDealt) and e.source_id in teams and e.target_id in teams
    }
    assert (Team.ENEMY, Team.THIRD) in pairs or (Team.THIRD, Team.ENEMY) in pairs
    restored = BattleSetup.model_validate_json(setup.model_dump_json())
    assert [u.team for u in restored.units].count(Team.THIRD) == 2
    replayed = replay(restored, 3, first.actions)
    assert replayed.state.winner == first.state.winner
    assert [e.model_dump() for e in replayed.events] == [e.model_dump() for e in first.events]
