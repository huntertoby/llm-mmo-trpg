"""AF-1：使用者「都照建議」的 A 段規則小修（玩法 PM 809c61f5b）。

每列一條規則句、實際跑引擎：

- 05 5.7 瞄準預告：目標的隊友擋在中間時，這一擊**改打擋住的那個人**（不再整發落空）；隱蔽照一般
  隱蔽規則（2 格內照射、2 格外落空）；瞄準預告只限敵方——我方單位放到 ``lock_on`` 招時直接出手。
- 06 6.32.1：一次出招，連擊點與氣各最多 +1——範圍武器技打中好幾個人也只 +1，雙匕首普攻打兩下也只
  +1 氣。

第 1、5 條另有 hypothesis 性質測試。
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, U3
from tests.engine.test_dual_dagger_skills_dd1 import HIT, MISS, d20s
from tests.engine.test_lock_on_rg1 import (
    ARCHER,
    HERO,
    SHOT,
    THIRD,
    aim,
    arena,
    fizzles,
    shots,
    to_archer_turn,
)
from tests.engine.test_stack_condition_kw1 import STRIKE, scene, weapon_skill
from trpg.engine import Attack, BattleState, resolve
from trpg.engine.actions import UseSkill
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    FollowupCharged,
    LockIntercepted,
    StacksChanged,
)
from trpg.engine.lock_on import lock_target_of
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team

SETTINGS = settings(
    max_examples=40 if os.environ.get("TRPG_FULL") == "1" else 12,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def damage_to(events: Sequence[EventBase], unit: str) -> int:
    return sum(e.amount for e in of(events, DamageDealt) if e.target_id == unit)


# ---------------------------------------------------------------------------
# 1. 隊友擋在中間：改打擋住的人
# ---------------------------------------------------------------------------


def test_an_ally_in_between_takes_the_shot_instead() -> None:
    state = aim(arena(third=(Team.ALLY, (2, 0), "bandit"))).state
    state.units[THIRD].pos = Pos(x=4, y=4)  # 隊友走到弓手與目標之間
    events = to_archer_turn(state)
    (roll,) = shots(events)
    assert roll.target_id == THIRD and not fizzles(events)
    assert damage_to(events, HERO) == 0
    (caught,) = of(events, LockIntercepted)
    assert (caught.target_id, caught.blocker_id) == (HERO, THIRD)
    assert "擋在" in (describe_event(caught, state) or "")


@SETTINGS
@given(
    blocker=st.integers(min_value=2, max_value=6),
    gap=st.integers(min_value=1, max_value=3),
    seed=st.integers(min_value=0, max_value=2**32),
)
def test_a_blocker_on_the_line_always_takes_the_shot(blocker: int, gap: int, seed: int) -> None:
    """性質：目標的隊友站在弓手與目標的直線上時，射出的那一箭一定對準擋住的人、被瞄準的人不受傷、
    不會因為擋住而落空；同種子重播結果相同。"""
    hero = min(blocker + gap, 9)
    base = aim(arena(hero=(hero, 4), third=(Team.ALLY, (2, 0), "bandit"), seed=seed)).state
    base.units[THIRD].pos = Pos(x=blocker, y=4)
    runs = []
    for _ in range(2):
        events = to_archer_turn(base.clone())
        runs.append([e.model_dump(mode="json") for e in events])
        rolled = shots(events)
        assert [r.target_id for r in rolled] == [THIRD]
        assert damage_to(events, HERO) == 0
        assert "lock_on_blocked" not in fizzles(events)
    assert runs[0] == runs[1]


def test_the_closest_blocker_takes_the_shot() -> None:
    state = aim(arena(third=(Team.ALLY, (2, 0), "bandit"))).state
    state.units[THIRD].pos = Pos(x=5, y=4)
    events = to_archer_turn(state)
    assert [r.target_id for r in shots(events)] == [THIRD]


# ---------------------------------------------------------------------------
# 2. 隱蔽照一般規則；瞄準預告只限敵方
# ---------------------------------------------------------------------------


def test_a_concealed_target_within_two_tiles_is_still_shot() -> None:
    state = aim(arena(hero=(3, 4))).state  # 距離 2：一般規則下隱蔽的目標仍可攻擊
    state.units[HERO].statuses.append(StatusInstance("concealed", remaining=3))
    events = to_archer_turn(state)
    assert not fizzles(events) and [r.target_id for r in shots(events)] == [HERO]


def test_a_concealed_target_beyond_two_tiles_makes_it_miss() -> None:
    state = aim(arena(hero=(4, 4))).state  # 距離 3
    state.units[HERO].statuses.append(StatusInstance("concealed", remaining=3))
    events = to_archer_turn(state)
    assert fizzles(events) == ["lock_on_concealed"] and not shots(events)


def test_a_player_side_unit_with_a_lock_on_skill_fires_at_once() -> None:
    """我方單位（例如複製了敵人的招）放 ``lock_on`` 招：沒有瞄準流程，當下就出手。"""
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(5, 3)])
    shooter = caster_template([SHOT], base="hero_archer")
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 3), shooter),
            spawn(Team.ENEMY, (5, 3), no_reactions(max_hp=300, resist={})),
        ],
    )
    state = give_turn(state, U1)
    state.units[U1].weapon = library().weapons["bow"]
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SHOT, target_id=U2))
    assert not of(result.events, FollowupCharged)
    assert [e.target_id for e in of(result.events, AttackRolled)] == [U2]
    assert lock_target_of(result.state.units[U1]) is None


def test_the_enemy_archer_still_aims() -> None:
    result = aim(arena())
    assert of(result.events, FollowupCharged) and lock_target_of(result.state.units[ARCHER])


# ---------------------------------------------------------------------------
# 5. 一次出招，連擊點與氣各最多 +1
# ---------------------------------------------------------------------------


def test_an_area_weapon_skill_gains_one_combo_point_however_many_it_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    line = {"type": "line", "size": 2}
    state = scene(weapon_skill(STRIKE, shape=line), foes=((4, 3), (5, 3)), weapon="dagger")
    d20s(monkeypatch, [HIT, HIT])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, direction="east"))
    assert {e.target_id for e in of(result.events, DamageDealt)} == {U2, U3}
    assert result.state.units[U1].stacks.get("combo_point", 0) == 1


KI_USER = "skill_qigong_wave"
"""消耗氣的技能：帶著它，普攻命中才會自動累積氣。"""


def ki_scene(weapon: str, foes: tuple[tuple[int, int], ...] = ((4, 3),)) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([KI_USER], base="hero_fighter"))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=300, resist={})) for xy in foes]
    state = give_turn(make_state(m, spawns), U1)
    state.units[U1].weapon = library().weapons[weapon]
    return state


@pytest.mark.parametrize(
    ("seq", "ki"), [([HIT, HIT], 1), ([HIT, MISS], 1), ([MISS, HIT], 1), ([MISS, MISS], 0)]
)
def test_a_dual_dagger_basic_attack_gains_at_most_one_ki(
    seq: list[int], ki: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = ki_scene("dual_dagger")
    d20s(monkeypatch, seq)
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    hits = [e for e in of(result.events, AttackRolled) if e.attacker_id == U1]
    assert len(hits) == 2  # 雙匕首普攻打兩下
    assert result.state.units[U1].stacks.get("ki", 0) == ki


@SETTINGS
@given(
    seed=st.integers(min_value=0, max_value=2**32),
    combo=st.integers(min_value=0, max_value=4),
    foes=st.integers(min_value=1, max_value=3),
    weapon=st.sampled_from(["dual_dagger", "dagger"]),
)
def test_one_cast_gains_at_most_one_combo_point(
    seed: int, combo: int, foes: int, weapon: str
) -> None:
    """性質：一次武器技（單體或直線打中 1～3 人、雙匕首或單手）連擊點最多 +1；同種子結果相同。"""
    line = {"type": "line", "size": foes}
    targets = tuple((4 + i, 3) for i in range(foes))
    state = scene(weapon_skill(STRIKE, shape=line), combo=combo, foes=targets, weapon=weapon)
    state.rng_state = Rng(seed).get_state()
    runs = []
    for _ in range(2):
        result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, direction="east"))
        gained = [e for e in of(result.events, StacksChanged) if e.reason == "gained"]
        assert len(gained) <= 1
        after = result.state.units[U1].stacks.get("combo_point", 0)
        assert after - combo == len(gained)
        runs.append([e.model_dump(mode="json") for e in result.events])
    assert runs[0] == runs[1]


@SETTINGS
@given(
    seed=st.integers(min_value=0, max_value=2**32),
    weapon=st.sampled_from(["dual_dagger", "dagger", "one_handed_sword"]),
)
def test_one_basic_attack_gains_at_most_one_ki(seed: int, weapon: str) -> None:
    """性質：一次普攻（雙匕首打兩下也一樣）氣最多 +1。"""
    state = ki_scene(weapon)
    state.rng_state = Rng(seed).get_state()
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    hit = any(e.hit for e in of(result.events, AttackRolled) if e.attacker_id == U1)
    assert result.state.units[U1].stacks.get("ki", 0) == (1 if hit else 0)


# ---------------------------------------------------------------------------
# 凝神拿掉定身代價（玩法 PM 交接 4.1.3 第 2 點）
# ---------------------------------------------------------------------------


def test_centering_no_longer_roots_the_caster() -> None:
    skill = library().skills["skill_centering"]
    assert skill.cost.self_status is None
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(6, 6)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template(["skill_centering"], base="hero_mage")),
        spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=300, resist={})),
    ]
    state = give_turn(make_state(m, spawns), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_centering"))
    me = result.state.units[U1]
    assert me.stacks.get("focus", 0) == 1
    assert me.get_status("root") is None
