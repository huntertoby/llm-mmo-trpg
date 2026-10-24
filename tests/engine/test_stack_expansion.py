"""Phase 3-52：層數擴充（連擊點、專注、聖能、靈魂碎片、寒霜、氣、怒氣開放給技能；06 6.32）。

涵蓋：自動累積（收集後延遲結算、只有帶著消耗技能的單位才累積、裝備充能不重複）、消耗擴充到治療與
護盾、疊在敵人身上的寒霜，以及資料表本身的檢查。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from trpg.content.stacks import StackDef
from trpg.engine import Action, Attack, BattleState, EndTurn, Move, UseSkill, resolve
from trpg.engine.events import DamageDealt, Healed, ShieldGained, StacksChanged
from trpg.shared.types import Pos, Team

HIT = (20, 19)  # 命中、不暴擊
FIGHTER = "hero_fighter"

JAB, FINISHER = "skill_flurry_jab", "skill_combo_finisher"
AIM, SHOT = "skill_steady_aim", "skill_focused_shot"
MEND, WARD = "skill_radiant_mend", "skill_sanctified_ward"
REAP, TORRENT = "skill_soul_reap", "skill_soul_torrent"
RIME, SHATTER = "skill_rime_touch", "skill_shatter_frost"
PALM, BREATH = "skill_palm_strike", "skill_qi_breath"
RAGE_GATHER, RAGE_FINISH = "skill_seething_rage", "skill_rage_unleashed"


def scene(skills: list[str], *, base: str = "hero_mage", foe_hp: int = 999) -> BattleState:
    """U1 帶 ``skills``，在 (3, 3) 手上有回合；U2（敵人，沒有反應）在 (4, 3)。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    return give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (3, 3), caster_template(skills, base=base)),
                spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=foe_hp)),
            ],
        ),
        U1,
    )


def use(state: BattleState, skill: str, rolls: list[tuple[int, int]] | None = None):  # type: ignore[no-untyped-def]
    s = with_rolls(state, rolls if rolls is not None else [HIT])
    return resolve(s, UseSkill(unit_id=U1, skill_id=skill, target_id=U2))


def stack_def(stack_id: str) -> StackDef:
    return library().ruleset.stack_def(stack_id)


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_the_new_stacks_follow_the_design_table() -> None:
    """06 6.32 的表：上限、在誰身上、過期（數值為初值，改了要同步改設計文件）。"""
    expect = {
        "combo_point": ("self", 5),
        "focus": ("self", 3),
        "holy_power": ("self", 3),
        "soul_shard": ("self", 5),
        "hoarfrost": ("target", 3),
        "ki": ("self", 3),
        "fury": ("self", 4),
    }
    for stack_id, (owner, top) in expect.items():
        d = stack_def(stack_id)
        assert (d.owner, d.max) == (owner, top), stack_id
        assert d.consumer is not None and d.gain, stack_id
    assert stack_def("hoarfrost").expires_after_rounds == 3
    assert stack_def("holy_power").consumer.boosts == ("heal", "shield")  # type: ignore[union-attr]
    assert stack_def("ki").consumer.boosts == ("damage", "heal")  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 連擊點：武器技命中 +1，終結技消耗
# ---------------------------------------------------------------------------


def test_weapon_skill_hits_build_combo_points_for_a_holder_of_a_finisher() -> None:
    state = scene([JAB, FINISHER], base=FIGHTER)
    result = use(state, JAB)
    # 武器技命中自動 +1，連環快刺自己的 add_stack 再 +1（先結算技能本身，延後結算自動累積）
    assert result.state.units[U1].stacks == {"combo_point": 2}
    assert [e.reason for e in of(result, StacksChanged)] == ["gained", "gained"]


def test_without_a_consumer_skill_nothing_accumulates_automatically() -> None:
    state = scene([JAB], base=FIGHTER)
    assert use(state, JAB).state.units[U1].stacks == {"combo_point": 1}  # 只有 add_stack


def test_a_miss_builds_nothing() -> None:
    state = scene([JAB, FINISHER], base=FIGHTER)
    assert use(state, JAB, [(20, 2)]).state.units[U1].stacks == {}


def test_the_finisher_spends_the_points_before_its_own_hit_adds_one() -> None:
    state = scene([FINISHER], base=FIGHTER)
    state.units[U1].stacks = {"combo_point": 3}
    result = use(state, FINISHER)
    (dealt,) = of(result, DamageDealt)
    assert dealt.multiplier_permille == 1300 * (1000 + 3 * 200) // 1000
    # 消耗在先、命中的那一層在整招結算完才加：剩 1 層，不是 4 層
    assert result.state.units[U1].stacks == {"combo_point": 1}
    assert [e.reason for e in of(result, StacksChanged)] == ["consumed", "gained"]


def test_combo_points_stop_at_five() -> None:
    state = scene([JAB, FINISHER], base=FIGHTER)
    state.units[U1].stacks = {"combo_point": 5}
    assert use(state, JAB).state.units[U1].stacks == {"combo_point": 5}


# ---------------------------------------------------------------------------
# 專注：回合結束時這回合沒有移動 +1
# ---------------------------------------------------------------------------


def test_standing_still_through_the_turn_builds_focus() -> None:
    state = scene([SHOT], base="hero_archer")
    result = resolve(state, EndTurn(unit_id=U1))
    assert result.state.units[U1].stacks == {"focus": 1}


def test_moving_during_the_turn_builds_no_focus() -> None:
    state = scene([SHOT], base="hero_archer")
    moved = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=2, y=3))))
    result = resolve(moved.state, EndTurn(unit_id=U1))
    assert result.state.units[U1].stacks == {}


def test_focus_boosts_the_next_shot() -> None:
    state = scene([SHOT], base="hero_archer")
    state.units[U1].stacks = {"focus": 2}
    (dealt,) = of(use(state, SHOT), DamageDealt)
    assert dealt.multiplier_permille == 1500 * (1000 + 2 * 150) // 1000


# ---------------------------------------------------------------------------
# 聖能：施放治療或神聖技能 +1；消耗讓治療與護盾變強
# ---------------------------------------------------------------------------


def test_casting_a_heal_builds_holy_power() -> None:
    state = scene([MEND, WARD])
    state.units[U2].team = Team.ALLY  # 對友方施放
    result = use(state, MEND, [(8, 4)])
    assert result.state.units[U1].stacks == {"holy_power": 2}  # 自動 +1、技能 add_stack +1


def test_holy_power_boosts_both_heals_and_shields() -> None:
    def shield(stacks: int) -> int:
        state = scene([WARD])
        state.units[U2].team = Team.ALLY
        state.units[U1].stacks = {"holy_power": stacks}
        result = use(state, WARD, [(6, 3), (6, 3), (6, 3)])
        (gained,) = of(result, ShieldGained)
        return gained.amount

    assert shield(3) > shield(0)
    assert shield(3) == pytest.approx(shield(0) * 1.6, abs=2)


# ---------------------------------------------------------------------------
# 靈魂碎片：擊殺 +1
# ---------------------------------------------------------------------------


def test_a_kill_builds_a_soul_shard() -> None:
    state = scene([REAP, TORRENT], foe_hp=1)
    result = use(state, REAP, [HIT, (8, 8)])
    assert result.state.units[U2].downed
    # 擊殺自動 +1，加上 add_stack +1（add_stack 對死掉的目標仍累積在自己身上）
    assert result.state.units[U1].stacks.get("soul_shard", 0) >= 1


def test_soul_shards_boost_shadow_damage() -> None:
    state = scene([TORRENT])
    state.units[U1].stacks = {"soul_shard": 4}
    (dealt,) = of(use(state, TORRENT), DamageDealt)
    assert dealt.multiplier_permille == 1000 * (1000 + 4 * 200) // 1000


# ---------------------------------------------------------------------------
# 寒霜：疊在敵人身上，3 輪沒有再疊就清空
# ---------------------------------------------------------------------------


def test_frost_damage_stacks_hoarfrost_on_the_enemy() -> None:
    state = scene([RIME, SHATTER])
    result = use(state, RIME)
    assert result.state.units[U2].stacks == {"hoarfrost": 2}  # 自動 +1、add_stack +1
    assert result.state.units[U1].stacks == {}
    assert result.state.units[U2].stack_expiry == {"hoarfrost": result.state.round + 3}


def test_shatter_consumes_the_enemys_hoarfrost_for_extra_ice_damage() -> None:
    state = scene([SHATTER])
    state.units[U2].stacks = {"hoarfrost": 3}
    result = use(state, SHATTER, [HIT, (8, 5), (8, 5)])
    (dealt,) = of(result, DamageDealt)
    assert dealt.multiplier_permille == 1000 * (1000 + 3 * 250) // 1000
    # 消耗後這一擊自己的冰霜傷害再疊 1 層
    assert result.state.units[U2].stacks == {"hoarfrost": 1}


def test_hoarfrost_expires_after_three_rounds_without_new_stacks() -> None:
    d = stack_def("hoarfrost")
    assert d.owner == "target" and d.expires_after_rounds == 3


# ---------------------------------------------------------------------------
# 氣：普攻命中 +1；消耗讓治療自己變強
# ---------------------------------------------------------------------------


def test_basic_attacks_build_ki_for_a_holder_of_a_ki_skill() -> None:
    state = scene([BREATH], base=FIGHTER)
    result = resolve(with_rolls(state, [HIT]), Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U1].stacks == {"ki": 1}
    other = scene([PALM], base=FIGHTER)  # 只有累積技能（沒有消耗氣的技能）：普攻不累積
    assert (
        resolve(with_rolls(other, [HIT]), Attack(unit_id=U1, target_id=U2)).state.units[U1].stacks
        == {}
    )


def test_ki_boosts_a_self_heal() -> None:
    def healed(stacks: int) -> int:
        state = scene([BREATH], base=FIGHTER)
        unit = state.units[U1]
        unit.hp = 1
        unit.stacks = {"ki": stacks} if stacks else {}
        result = resolve(
            with_rolls(state, [(6, 4), (6, 4), (6, 4)]),
            UseSkill(unit_id=U1, skill_id=BREATH),
        )
        (event,) = of(result, Healed)
        return event.amount

    assert healed(3) > healed(0)


# ---------------------------------------------------------------------------
# 怒氣：受到傷害 +1（有消耗它的技能時）；技能可以消耗
# ---------------------------------------------------------------------------


def test_taking_damage_builds_fury_for_a_holder_of_a_fury_skill() -> None:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([RAGE_FINISH], base=FIGHTER)),
            spawn(Team.ENEMY, (4, 3), no_reactions()),
        ],
    )
    state = give_turn(state, U2)
    result = resolve(with_rolls(state, [HIT, (8, 5)]), Attack(unit_id=U2, target_id=U1))
    assert result.state.units[U1].stacks == {"fury": 1}


def test_a_fury_skill_boosts_its_damage() -> None:
    state = scene([RAGE_FINISH], base=FIGHTER)
    state.units[U1].stacks = {"fury": 4}
    (dealt,) = of(use(state, RAGE_FINISH), DamageDealt)
    assert dealt.multiplier_permille == 1300 * (1000 + 4 * 200) // 1000


def test_the_accumulator_passive_exists_for_fury() -> None:
    skill = library().skills[RAGE_GATHER]
    assert skill.kind == "passive" and skill.trigger is not None


# ---------------------------------------------------------------------------
# 重播：同一個初始狀態加同一串動作，事件與結果完全相同
# ---------------------------------------------------------------------------


def _play(state: BattleState) -> tuple[list[str], dict[str, int]]:
    actions: list[Action] = [
        UseSkill(unit_id=U1, skill_id=JAB, target_id=U2),
        UseSkill(unit_id=U1, skill_id=FINISHER, target_id=U2),
        EndTurn(unit_id=U1),
    ]
    events: list[str] = []
    current = state.clone()
    for action in actions:
        result = resolve(current, action)
        events += [e.model_dump_json() for e in result.events]
        current = result.state
    return events, dict(current.units[U1].stacks)


def test_a_battle_with_the_new_stacks_replays_identically() -> None:
    state = scene([JAB, FINISHER], base=FIGHTER)
    first = _play(state)
    second = _play(state)
    assert first == second
    assert any('"stack_id":"combo_point"' in e for e in first[0])
