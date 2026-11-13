"""RG-1：瞄準預告（#162，``docs/design/05-戰鬥.md`` 5.7「遠程瞄準預告」；
規格 ``docs/phases/PhaseRG計畫.md`` 1.1）。

每列一條規則句、實際跑引擎（內建的鶴唳穿雲，不另造測試技能）：施放＝瞄準（付代價、不擲命中），
施放者下一個自己的回合開始才射出；斷視線、隱蔽（照一般隱蔽規則，AF-1）、近戰打斷與目標倒下、
走出射程都讓它落空，隊友擋在中間改打擋住的人（AF-1，``test_af1_rules.py``）；自己陣營的單位不擋、
遠程打中弓手不打斷、普通射擊照舊不預告。
"""

from __future__ import annotations

from collections.abc import Sequence

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn, template
from trpg.content.skills.problems import _lock_on_problems
from trpg.engine import Attack, BattleState, ResolveResult, UseSkill, preview, resolve, telegraph
from trpg.engine.actions import EndTurn
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    AttackRolled,
    EffectFizzled,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    SkillFollowup,
)
from trpg.engine.lock_on import lock_target_of
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.shared.types import Pos, Team, UnitId

ARCHER, HERO, THIRD = (UnitId(f"unit_000{i}") for i in range(1, 4))
SHOT = "skill_crane_piercing_shot"
ROW = "0" * 12


def arena(
    hero: tuple[int, int] = (7, 4),
    *,
    third: tuple[Team, tuple[int, int], str] | None = None,
    terrain: str | None = None,
    seed: int = 0,
    heights: str | None = None,
    kit: tuple[str, ...] | None = None,
) -> BattleState:
    """雲鶴使 ARCHER（敵方）在 (1, 4)；主角 HERO（我方，不反應、HP 多）；``third`` 是第三名單位。"""
    rows = heights or "\n".join([ROW] * 9)
    m = make_map(rows, terrain, ally=[hero], enemy=[(1, 4)])
    archer = template("sect_crane_archer", reactions=[])
    if kit is not None:
        archer = archer.model_copy(update={"skills": kit})
    spawns = [
        spawn(Team.ENEMY, (1, 4), archer),
        spawn(Team.ALLY, hero, template("bandit", max_hp=300, reactions=[], speed=0)),
    ]
    if third is not None:
        team, xy, base = third
        spawns.append(spawn(team, xy, template(base, max_hp=300, reactions=[], speed=0)))
    return give_turn(make_state(m, spawns, seed=seed), ARCHER)


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def aim(state: BattleState, target: UnitId = HERO) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=ARCHER, skill_id=SHOT, target_id=target))


def to_archer_turn(state: BattleState) -> list[EventBase]:
    """結束回合直到雲鶴使的下一個回合開始（含那次回合開始的事件）。"""
    events: list[EventBase] = []
    s = state
    for _ in range(8):
        assert s.active_unit is not None
        result = resolve(s, EndTurn(unit_id=s.active_unit))
        events += result.events
        s = result.state
        if s.active_unit == ARCHER:
            return events
    raise AssertionError("沒有輪回雲鶴使")


def shots(events: Sequence[EventBase]) -> list[AttackRolled]:
    return [e for e in of(events, AttackRolled) if e.skill_id == SHOT]


def fizzles(events: Sequence[EventBase]) -> list[str]:
    return [e.reason for e in of(events, EffectFizzled) if e.reason.startswith("lock_on")]


# ---------------------------------------------------------------------------
# 宣告與射出
# ---------------------------------------------------------------------------


def test_aiming_pays_the_cost_and_marks_the_target_without_rolling() -> None:
    state = arena()
    result = aim(state)
    assert not shots(result.events)
    (charged,) = of(result.events, FollowupCharged)
    assert charged.lock_target_id == HERO and charged.tiles == (Pos(x=7, y=4),)
    archer = result.state.units[ARCHER]
    assert lock_target_of(archer) == HERO
    assert archer.cooldowns.get(SHOT) == 2  # 代價在瞄準時付
    assert archer.facing == "east"
    assert any("瞄準了" in (describe_event(e, result.state) or "") for e in result.events)


def test_the_shot_fires_at_the_start_of_the_archers_next_turn() -> None:
    first = aim(arena())
    events = to_archer_turn(first.state)
    follow = of(events, SkillFollowup)
    assert follow and follow[0].when == "delayed" and follow[0].skill_id == SHOT
    (roll,) = shots(events)
    assert roll.attacker_id == ARCHER and roll.target_id == HERO
    assert not fizzles(events)


def test_the_mark_follows_the_target_and_the_telegraph_names_it() -> None:
    state = aim(arena()).state
    state.units[HERO].pos = Pos(x=6, y=2)
    (charge,) = telegraph(state).charges
    assert charge.lock_target_id == HERO and charge.tiles == (Pos(x=6, y=2),)
    events = to_archer_turn(state)
    assert shots(events) and shots(events)[0].target_id == HERO


def test_a_plain_shot_is_not_telegraphed() -> None:
    result = resolve(arena(), Attack(unit_id=ARCHER, target_id=HERO))
    assert of(result.events, AttackRolled) and not of(result.events, FollowupCharged)


def test_lock_on_needs_a_unit_target() -> None:
    state = arena()
    result = preview(state, UseSkill(unit_id=ARCHER, skill_id=SHOT, target_id=HERO))
    assert any(isinstance(e, FollowupCharged) for e in result.min_events)
    assert all(not isinstance(e, AttackRolled) for e in result.min_events)


# ---------------------------------------------------------------------------
# 四種應對與其他落空
# ---------------------------------------------------------------------------


def test_breaking_line_of_sight_behind_cover_makes_it_miss() -> None:
    walls = "\n".join(["." * 12] * 4 + ["....#......."] + ["." * 12] * 4)
    state = aim(arena(hero=(7, 6), terrain=walls)).state
    state.units[HERO].pos = Pos(x=7, y=4)  # 躲到牆後：(4, 4) 的牆擋住
    events = to_archer_turn(state)
    assert fizzles(events) == ["lock_on_lost"] and not shots(events)


def test_entering_concealment_beyond_two_tiles_makes_it_miss() -> None:
    """AF-1：隱蔽照一般隱蔽規則（2 格內照射，見 ``test_af1_rules.py``）；2 格外落空。"""
    state = aim(arena(hero=(5, 4))).state  # 距離 4
    state.units[HERO].statuses.append(StatusInstance("concealed", remaining=3))
    events = to_archer_turn(state)
    assert fizzles(events) == ["lock_on_concealed"] and not shots(events)


def test_an_ally_standing_in_between_takes_the_shot() -> None:
    """AF-1（05 5.7）：改打擋住的人，不再整發落空。"""
    state = aim(arena(third=(Team.ALLY, (2, 0), "bandit"))).state
    state.units[THIRD].pos = Pos(x=4, y=4)  # 隊友走到弓手與目標之間
    events = to_archer_turn(state)
    assert not fizzles(events) and [r.target_id for r in shots(events)] == [THIRD]


def test_the_archers_own_side_does_not_block() -> None:
    state = aim(arena(third=(Team.ENEMY, (4, 4), "bandit"))).state
    events = to_archer_turn(state)
    assert not fizzles(events) and len(shots(events)) == 1


def test_a_melee_hit_on_the_archer_interrupts_the_aim() -> None:
    state = aim(arena(third=(Team.ALLY, (2, 4), "bandit"))).state
    state = give_turn(state, THIRD)
    hit = resolve(state, Attack(unit_id=THIRD, target_id=ARCHER))
    rolled = [e for e in of(hit.events, AttackRolled) if e.target_id == ARCHER]
    assert rolled[0].hit  # 固定種子（0）下這一下會中
    (cancel,) = of(hit.events, FollowupCancelled)
    assert cancel.reason == "interrupted" and cancel.unit_id == ARCHER
    assert lock_target_of(hit.state.units[ARCHER]) is None
    assert not shots(to_archer_turn(hit.state))


def test_a_ranged_hit_on_the_archer_does_not_interrupt() -> None:
    state = aim(arena(third=(Team.ALLY, (4, 1), "bandit_archer"))).state
    state = give_turn(state, THIRD)
    hit = resolve(state, Attack(unit_id=THIRD, target_id=ARCHER))
    assert not of(hit.events, FollowupCancelled)
    assert lock_target_of(hit.state.units[ARCHER]) == HERO


def test_a_target_out_of_range_makes_it_miss() -> None:
    state = aim(arena()).state
    state.units[HERO].pos = Pos(x=11, y=8)  # 曼哈頓 14 > 弓的射程 8
    events = to_archer_turn(state)
    assert fizzles(events) == ["lock_on_lost"] and not shots(events)


def test_a_downed_target_makes_it_miss() -> None:
    state = aim(arena(third=(Team.ALLY, (11, 8), "bandit"))).state  # 還有人在場：戰鬥不結束
    state.units[HERO].downed = True
    events = to_archer_turn(state)
    assert fizzles(events) == ["lock_on_lost"] and not shots(events)
    assert lock_target_of(state.units[ARCHER]) == HERO  # 傳入的狀態不變


# ---------------------------------------------------------------------------
# 內容檢查、確定性
# ---------------------------------------------------------------------------


def test_lock_on_is_only_for_enemy_only_single_target_actives() -> None:
    skill = library().skills[SHOT]
    assert _lock_on_problems(skill) == []
    player = skill.model_copy(update={"enemy_only": False})
    assert any("enemy_only" in p for p in _lock_on_problems(player))
    aoe = library().skills["skill_lava_splash"].model_copy(update={"lock_on": True})
    assert len(_lock_on_problems(aoe)) >= 2  # 不是單體、有第二段


def test_the_three_ranged_enemies_carry_a_lock_on_skill() -> None:
    lib = library()
    for unit, skill in (
        ("sect_crane_archer", SHOT),
        ("sect_talisman_caster", "skill_binding_talisman"),
        ("lava_tortoise", "skill_lava_bomb"),
    ):
        assert skill in lib.unit(unit).skills and lib.skills[skill].lock_on
    assert "skill_high_ground_shot" not in lib.unit("sect_crane_archer").skills
    assert not lib.skills["skill_high_ground_shot"].lock_on  # 主角弓手的高處狙擊不動


@settings(max_examples=12, deadline=None)
@given(
    x=st.integers(min_value=3, max_value=9),
    y=st.integers(min_value=1, max_value=7),
    seed=st.integers(min_value=0, max_value=10_000),
)
def test_aim_and_release_replay_identically(x: int, y: int, seed: int) -> None:
    """性質：同一個起始狀態與同一串動作，瞄準與射出的事件每次相同（確定性）。"""
    assume(x - 1 + abs(y - 4) <= 8)  # 弓的射程 8 內才能瞄準
    base = arena(hero=(x, y), seed=seed)
    runs = []
    for _ in range(2):
        first = aim(base)
        runs.append(
            [e.model_dump(mode="json") for e in (*first.events, *to_archer_turn(first.state))]
        )
    assert runs[0] == runs[1]


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_the_archer_ai_aims_from_high_ground() -> None:
    """站得比目標高時（強力一擊多補一箭），雲鶴使在自己的回合裡會瞄準（AI 用「現在就射出」的預覽
    × ``lock_on_permille`` 估值）；平地上普攻比較划算，照舊普攻（同改之前的高處狙擊）。只帶這一招，
    免得鷹眼標記先用掉 AP。"""
    ai = UtilityAI(library().ai_profiles)
    high = "\n".join([ROW] * 4 + ["022000000000"] + [ROW] * 4)
    for heights, aims in ((high, True), (None, False)):
        state = arena(heights=heights, kit=(SHOT,))
        aimed = False
        while state.active_unit == ARCHER and not state.ended:
            result = resolve(state, ai(state))
            aimed = aimed or any(
                e.lock_target_id == HERO for e in of(result.events, FollowupCharged)
            )
            state = result.state
        assert aimed is aims


def test_the_preview_carries_the_fire_now_projection() -> None:
    p = preview(arena(), UseSkill(unit_id=ARCHER, skill_id=SHOT, target_id=HERO))
    assert p.lock_fire is not None
    assert any(isinstance(e, AttackRolled) for e in p.lock_fire.max_events)
    plain = preview(arena(), Attack(unit_id=ARCHER, target_id=HERO))
    assert plain.lock_fire is None
