"""賭博型技能（Phase 3D-7a，``docs/phases/Phase3D計畫.md`` 7.1、7.3）：賭注（成敗兩個分支）、
失手反噬、反噬上限、重播。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from trpg.content.skills import SkillDef
from trpg.engine import UseSkill, legal_actions, state_from_json, state_to_json
from trpg.engine.events import (
    AttackRolled,
    BacklashTriggered,
    DamageDealt,
    GambleRolled,
    Healed,
    StatusApplied,
)
from trpg.shared.rng import Rng

FIRE: dict[str, Any] = {"type": "damage", "dice": "2d6", "element": "fire"}
SINGLE5: dict[str, Any] = {"type": "single", "range": 5}
DOUBLE: dict[str, Any] = {"type": "damage_multiplier", "damage_multiplier_permille": 2000}
HALF_BACK: dict[str, Any] = {"type": "self_damage_of_hit", "self_damage_permille_of_hit": 500}


def gamble(
    win: Sequence[dict[str, Any]] = (DOUBLE,),
    lose: Sequence[dict[str, Any]] = (HALF_BACK,),
    chance: int = 600,
) -> dict[str, Any]:
    effect: dict[str, Any] = {"type": "gamble", "chance_permille": chance}
    if win:
        effect["win"] = list(win)
    if lose:
        effect["lose"] = list(lose)
    return effect


def gamble_skill(
    *, win: Sequence[dict[str, Any]] = (DOUBLE,), lose: Sequence[dict[str, Any]] = (HALF_BACK,)
) -> SkillDef:
    return make_skill(SID, SINGLE5, [FIRE, gamble(win, lose)], cost={"mana": 0})


def script_randint(monkeypatch: pytest.MonkeyPatch, values: Sequence[int]) -> list[int]:
    """讓接下來的 ``Rng.randint``（所有骰子都經過它）依序回傳 ``values``；用完再擲會讓測試失敗。
    順序：命中 d20、賭注 d1000、傷害骰。"""
    queue = list(values)

    def randint(self: Rng, lo: int, hi: int) -> int:
        assert queue, "骰值用完了"
        value = queue.pop(0)
        assert lo <= value <= hi, f"{value} 不在 {lo}–{hi}"
        return value

    monkeypatch.setattr(Rng, "randint", randint)
    return queue


# ---------------------------------------------------------------------------
# 賭注
# ---------------------------------------------------------------------------


def test_the_gamble_win_branch_multiplies_the_hit_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(gamble_skill(), [(5, 3)])
    script_randint(monkeypatch, [19, 600, 3, 4])  # 命中；d1000 = 600（≤ 600 成功）；傷害骰
    won = cast(state, target_id=U2)
    (rolled,) = of(won, GambleRolled)
    assert (rolled.unit_id, rolled.skill_id, rolled.roll) == (U1, SID, 600)
    assert (rolled.chance_permille, rolled.success) == (600, True)
    (dmg,) = of(won, DamageDealt)
    script_randint(monkeypatch, [19, 601, 3, 4])  # d1000 = 601 失敗：同樣的骰子，傷害不加倍
    lost = cast(state, target_id=U2)
    (base,) = [e for e in of(lost, DamageDealt) if e.target_id == U2]
    assert dmg.amount in (2 * base.amount, 2 * base.amount + 1)
    assert dmg.multiplier_permille == 2000 and base.multiplier_permille == 1000


def test_the_gamble_lose_branch_hurts_the_caster_for_half_the_damage_dealt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(gamble_skill(), [(5, 3)])
    script_randint(monkeypatch, [19, 900, 3, 4])
    result = cast(state, target_id=U2)
    (rolled,) = of(result, GambleRolled)
    assert not rolled.success
    hit, back = of(result, DamageDealt)
    assert (hit.target_id, hit.cause) == (U2, "attack")
    assert (back.target_id, back.source_id, back.cause) == (U1, U1, "backlash")
    assert back.amount == hit.amount * 500 // 1000
    caster = result.state.units[U1]
    assert caster.hp == state.units[U1].hp - back.amount
    # 事件順序：命中 → 賭注 → 傷害 → 反噬
    order = [
        type(e) for e in result.events if isinstance(e, AttackRolled | GambleRolled | DamageDealt)
    ]
    assert order == [AttackRolled, GambleRolled, DamageDealt, DamageDealt]


def test_a_missed_attack_does_not_resolve_the_gamble(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(gamble_skill(), [(5, 3)])
    script_randint(monkeypatch, [1])  # 自然 1：失手，之後不再擲任何骰子（用完再擲會失敗）
    result = cast(state, target_id=U2)
    assert not of(result, GambleRolled) and not of(result, DamageDealt)


def test_the_gamble_branches_may_target_the_caster_or_the_enemy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    heal = {"type": "heal", "dice": "1d4", "affects": "self"}
    bite = {"type": "damage", "dice": "1d4", "element": "fire", "affects": "self"}
    state = battle(gamble_skill(win=[heal], lose=[bite]), [(5, 3)])
    state.units[U1].hp -= 10
    script_randint(monkeypatch, [19, 100, 3, 4, 2])  # 命中、成功、傷害骰 3 4、治療骰 2
    won = cast(state, target_id=U2)
    assert [e.target_id for e in of(won, Healed)] == [U1]
    script_randint(monkeypatch, [19, 700, 3, 4, 2])  # 失敗：對自己的傷害是反噬
    lost = cast(state, target_id=U2)
    assert [(e.target_id, e.cause) for e in of(lost, DamageDealt)] == [
        (U2, "attack"),
        (U1, "backlash"),
    ]


def test_a_gamble_does_not_make_the_caster_a_legal_target() -> None:
    state = battle(
        gamble_skill(lose=[{"type": "heal", "dice": "1d4", "affects": "self"}]), [(5, 3)]
    )
    actions = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]
    assert [a.target_id for a in actions] == [U2]


def test_a_gamble_roll_is_reproduced_by_the_replay_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """賭注只用戰鬥狀態內的亂數：同一個狀態施放兩次，擲出同樣的 d1000 與結果。"""
    state = battle(gamble_skill(), [(5, 3)])
    first = cast(state, target_id=U2)
    again = cast(state_from_json(state_to_json(state)), target_id=U2)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in again.events]
    assert state_to_json(first.state) == state_to_json(again.state)


def test_the_gamble_roll_follows_the_chance_over_many_seeds() -> None:
    state = battle(gamble_skill(), [(5, 3)])
    wins = rolls = 0
    for seed in range(300):
        s = state.clone()
        s.rng_state = Rng(seed).get_state()
        for e in of(cast(s, target_id=U2), GambleRolled):
            rolls += 1
            wins += e.success
    assert rolls > 100 and abs(wins / rolls - 0.6) < 0.12


# ---------------------------------------------------------------------------
# 失手反噬
# ---------------------------------------------------------------------------

PRONE_ON_MISS: dict[str, Any] = {
    "mana": 0,
    "on_miss": [{"type": "apply_status", "status": "prone"}],
}


def miss_skill(cost: dict[str, Any] | None = None) -> SkillDef:
    return make_skill(SID, SINGLE5, [FIRE], cost=cost or PRONE_ON_MISS)


@pytest.mark.parametrize("natural", [1, 2, 5])
def test_a_missed_attack_triggers_the_miss_backlash(
    monkeypatch: pytest.MonkeyPatch, natural: int
) -> None:
    state = battle(miss_skill(), [(5, 3)])
    script_randint(monkeypatch, [natural])
    result = cast(state, target_id=U2)
    assert not of(result, AttackRolled)[0].hit
    (trigger,) = of(result, BacklashTriggered)
    assert (trigger.unit_id, trigger.skill_id) == (U1, SID)
    (applied,) = [e for e in of(result, StatusApplied) if e.status_id == "prone"]
    assert applied.target_id == U1 and result.state.units[U1].has_status("prone")


def test_a_hit_does_not_trigger_the_miss_backlash(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(miss_skill(), [(5, 3)])
    script_randint(monkeypatch, [19, 3, 4])
    result = cast(state, target_id=U2)
    assert not of(result, BacklashTriggered)
    assert not result.state.units[U1].has_status("prone")


def test_a_natural_one_triggers_the_backlash_even_against_a_defenseless_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(miss_skill(), [(5, 3)])
    state.units[U2].attributes["dex"] = 1  # type: ignore[index]
    script_randint(monkeypatch, [1])
    assert of(cast(state, target_id=U2), BacklashTriggered)


# ---------------------------------------------------------------------------
# 反噬上限
# ---------------------------------------------------------------------------


def test_backlash_damage_never_kills_the_caster(monkeypatch: pytest.MonkeyPatch) -> None:
    full_back = {"type": "self_damage_of_hit", "self_damage_permille_of_hit": 1000}
    state = battle(gamble_skill(lose=[full_back]), [(5, 3)])
    state.units[U1].hp = 2
    script_randint(monkeypatch, [19, 999, 6, 6])
    result = cast(state, target_id=U2)
    back = [e for e in of(result, DamageDealt) if e.target_id == U1]
    assert back and back[0].cause == "backlash" and back[0].hp_after == 1
    assert result.state.units[U1].hp == 1 and result.state.units[U1].alive


def test_miss_backlash_damage_leaves_one_hp_and_shields_absorb_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cost = {"mana": 0, "on_miss": [{"type": "damage", "dice": "3d6", "element": "physical"}]}
    state = battle(miss_skill(cost), [(5, 3)])
    state.units[U1].hp = 4
    script_randint(monkeypatch, [2, 6, 6, 6])
    result = cast(state, target_id=U2)
    (back,) = of(result, DamageDealt)
    assert back.cause == "backlash" and result.state.units[U1].hp == 1


def test_other_damage_is_not_capped_by_the_backlash_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(make_skill(SID, SINGLE5, [FIRE]), [(5, 3)])
    state.units[U2].hp = 1
    script_randint(monkeypatch, [19, 6, 6])
    assert not result_alive(cast(state, target_id=U2), U2)


def result_alive(result: Any, uid: str) -> bool:
    return bool(result.state.units[uid].alive)


@pytest.mark.parametrize("seed", [12, 24])
def test_an_ai_battle_with_the_gambler_build_bets_and_replays_exactly(seed: int) -> None:
    """build_gambler 在 open_plain：種子 24 賭注失敗一次、種子 12 失手反噬一次（3D-7b 加了狂野之刃
    等技能後 AI 的選擇改變，所以拆成兩個種子）；紀錄重播的狀態與事件一致。

    3-20 跑步改變 AI 軌跡，種子原為 4、3（換成 24、5）；3-21a 守護、換位、瞄準後 5 換成 12。"""
    from tests.engine.test_zone_ai import _run  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run("build_gambler", "open_plain", seed)
    if seed == 24:
        assert [e.success for e in of(run, GambleRolled)] == [False]
        assert any(e.cause == "backlash" for e in of(run, DamageDealt))
    else:
        assert of(run, BacklashTriggered)
    again = replay(setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
