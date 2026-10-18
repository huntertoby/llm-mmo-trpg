"""``trpg.sim.metrics``（Phase 2C-1 驗收 4）：手工事件序列逐項核對，再用真實戰鬥交叉驗證。"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    AttackRolled,
    ChainLimitReached,
    DamageCause,
    DamageDealt,
    EventBase,
    Healed,
    RoundStarted,
    SkillUsed,
    StatusApplied,
    StatusRemoved,
    TurnStarted,
    UnitDowned,
    UnitSpawned,
)
from trpg.engine.runner import run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import Element, Pos, Team, UnitId
from trpg.sim.metrics import (
    BattleMetrics,
    UnitInfo,
    battle_metrics,
    metrics_from_events,
    run_tracked,
)

A1, A2, E1, BOSS = (UnitId(x) for x in ("a1", "a2", "e1", "boss"))
UNITS = [
    UnitInfo(A1, "hero_a", Team.ALLY, 50),
    UnitInfo(A2, "hero_b", Team.ALLY, 40),
    UnitInfo(E1, "grunt", Team.ENEMY, 30),
    UnitInfo(BOSS, "chief", Team.ENEMY, 100, ("boss",)),
]


class Stream:
    """依序建立事件（``seq`` 自動遞增）。"""

    def __init__(self) -> None:
        self.events: list[EventBase] = []
        self.round = 1

    def add[E: EventBase](self, event_type: type[E], /, **fields: Any) -> E:
        event = event_type(seq=len(self.events), round=self.round, **fields)
        self.events.append(event)
        return event

    def mark(self) -> int:
        return len(self.events)

    def damage(
        self,
        target: UnitId,
        source: UnitId | None,
        before: int,
        after: int,
        cause: DamageCause = "attack",
    ) -> None:
        self.add(
            DamageDealt,
            target_id=target,
            source_id=source,
            cause=cause,
            element=Element.PHYSICAL,
            rolls=(),
            crit=False,
            element_mod_ppm=1_000_000,
            amount=before - after,
            hp_before=before,
            hp_after=after,
        )

    def attack(self, attacker: UnitId, target: UnitId, skill_id: str | None) -> None:
        self.add(
            AttackRolled,
            attacker_id=attacker,
            target_id=target,
            rolls=(10,),
            advantage="none",
            natural=10,
            attack_value=0,
            defense_value_permille=0,
            hit_modifier=0,
            proficiency=0,
            situational=0,
            total=10,
            target_number=5,
            hit=True,
            crit=False,
            skill_id=skill_id,
        )

    def status(self, target: UnitId, status_id: str, source: UnitId | None) -> None:
        self.add(
            StatusApplied,
            target_id=target,
            status_id=status_id,
            duration=1,
            refreshed=False,
            source_id=source,
        )

    def turn(self, unit: UnitId) -> None:
        self.add(TurnStarted, unit_id=unit, ap=3, move_points=5)


def _scenario() -> tuple[list[EventBase], list[int]]:
    s = Stream()
    bounds: list[int] = []
    # 開場：第 1 輪開始（四個單位在場）
    s.add(RoundStarted)
    bounds.append(s.mark())
    # 動作 1：A1 用技能 skill_x 打 E1（直接 12、爆炸間接 8），墜落（無來源）2，治療 A2 5 點
    s.turn(A1)
    s.add(
        SkillUsed,
        unit_id=A1,
        skill_id="skill_x",
        name_zh="測試技能",
        ap=2,
        mana=0,
        mana_after=0,
        tiles=(Pos(x=0, y=0),),
    )
    s.attack(A1, E1, "skill_x")
    s.damage(E1, A1, 30, 18)
    s.damage(E1, A1, 18, 10, "explosion")
    s.damage(E1, None, 10, 8, "fall")
    s.add(Healed, target_id=A2, source_id=A1, rolls=(), amount=5, hp_before=35, hp_after=40)
    bounds.append(s.mark())
    # 動作 2：暈眩 E1；A1 誤傷 A2（友軍）10
    s.status(E1, "stun", A1)
    s.damage(A2, A1, 40, 30)
    bounds.append(s.mark())
    # 動作 3：E1 的回合（帶著 A1 施加的暈眩）；E1 對 A2 施加定身，環境對 A2 施加緩速
    s.turn(E1)
    s.status(A2, "root", E1)
    s.status(A2, "slow", None)
    s.add(StatusRemoved, target_id=E1, status_id="stun", reason="expired")
    bounds.append(s.mark())
    # 動作 4：A2 的回合（定身來自 E1、緩速來自環境）；A2 擊倒 E1（溢出的傷害不計）
    s.turn(A2)
    s.attack(A2, E1, None)
    s.damage(E1, A2, 8, 0)
    s.add(UnitDowned, unit_id=E1)
    bounds.append(s.mark())
    # 動作 5：A1 對 Boss 一擊 60（≥ 60% 最大 HP），連鎖上限 2 次
    s.attack(A1, BOSS, None)
    s.damage(BOSS, A1, 100, 40)
    s.add(ChainLimitReached, effect_kind="damage", depth=8)
    s.add(ChainLimitReached, effect_kind="damage", depth=8)
    bounds.append(s.mark())
    # 第 2 輪開始：E1 已倒下
    s.round = 2
    s.add(RoundStarted)
    bounds.append(s.mark())
    return s.events, bounds


def _metrics(events: list[EventBase], bounds: list[int] | None, **kw: Any) -> BattleMetrics:
    return metrics_from_events(
        seed=7,
        units=UNITS,
        events=events,
        bounds=bounds,
        ap_spent=kw.get("ap_spent", {}),
        winner=kw.get("winner", Team.ALLY),
        rounds=kw.get("rounds", 2),
        actions=kw.get("actions", 5),
    )


def _unit(m: BattleMetrics, unit_id: UnitId) -> Any:
    return next(u for u in m.units if u.unit_id == unit_id)


def test_damage_is_attributed_to_sources_and_split_into_direct_and_indirect() -> None:
    events, bounds = _scenario()
    m = _metrics(events, bounds)
    a1, a2, e1 = _unit(m, A1), _unit(m, A2), _unit(m, E1)
    assert (a1.damage_direct, a1.damage_indirect) == (12 + 60, 8)  # 技能 12 ＋ Boss 60；爆炸 8
    assert a1.damage_friendly == 10  # 誤傷 A2 不計入直接
    assert (a2.damage_direct, a2.damage_indirect) == (8, 0)  # 溢出的傷害只算實際扣掉的 HP
    assert e1.damage_taken == 12 + 8 + 2 + 8
    assert a2.damage_taken == 10
    assert m.environment_damage == {"enemy": 2}  # 墜落沒有來源
    assert m.team_damage(Team.ALLY) == 12 + 60 + 8 + 8
    assert m.team_damage(Team.ALLY, direct=True) == 12 + 60 + 8
    assert m.team_damage(Team.ALLY, direct=False) == 8
    assert m.team_damage(Team.ENEMY) == 0


def test_dpr_divides_by_the_rounds_the_unit_was_in_the_battle() -> None:
    events, bounds = _scenario()
    m = _metrics(events, bounds)
    # 第 1、2 輪開始時 A1、A2、Boss 都在場；E1 只有第 1 輪（第 1 輪被擊倒）
    assert [(u.unit_id, u.alive_rounds) for u in m.units] == [
        (A1, 2),
        (A2, 2),
        (E1, 1),
        (BOSS, 2),
    ]
    assert _unit(m, A1).dpr == Fraction(12 + 60 + 8, 2)
    assert _unit(m, A2).dpr == Fraction(8, 2)
    assert _unit(m, E1).dpr == 0


def test_kills_credit_the_last_damage_source_and_healing_the_healer() -> None:
    events, bounds = _scenario()
    m = _metrics(events, bounds)
    assert (_unit(m, A2).kills, _unit(m, A1).kills) == (1, 0)
    assert _unit(m, E1).downed and not _unit(m, A1).downed
    assert _unit(m, A1).healing_done == 5
    assert Counter(u.turns for u in m.units) == Counter({1: 3, 0: 1})  # A1、E1、A2 各一回合


def test_control_turns_are_attributed_to_the_last_applier() -> None:
    events, bounds = _scenario()
    m = _metrics(events, bounds)
    # E1 在自己回合開始時帶著 A1 的暈眩；A2 帶著 E1 的定身與環境的緩速
    assert _unit(m, A1).control_inflicted == {"stun": 1}
    assert _unit(m, E1).control_inflicted == {"root": 1}
    assert _unit(m, A2).control_inflicted == {}
    assert m.environment_control == {"slow": 1}


def test_skill_usage_attribution_follows_the_skill_until_the_next_attack() -> None:
    events, bounds = _scenario()
    m = _metrics(events, bounds)
    skill = m.skills["skill_x"]
    # 使用 1、擲骰 1、命中 1；直接傷害 12（之後 A2 的普攻不歸技能、爆炸是間接）；治療 5
    assert (skill.uses, skill.rolls, skill.hits, skill.damage, skill.healed) == (1, 1, 1, 12, 5)
    assert m.skill_users == {"skill_x": ("ally",)}
    assert set(m.skills) == {"skill_x"}


def test_anomaly_raw_data_boss_burst_chain_limit_and_result() -> None:
    events, bounds = _scenario()
    m = _metrics(events, bounds)
    assert m.chain_limit_count == 2
    assert m.boss_burst is not None and "60／100" in m.boss_burst
    assert m.one_shot_count == 0  # E1 在同一個動作內只受到 12 ＋ 8 ＋ 2
    assert (m.result, m.rounds, m.actions) == ("ally", 2, 5)
    assert _metrics(events, bounds, winner=None).result == "draw"
    assert _metrics(events, bounds, winner=Team.ENEMY).result == "enemy"


def test_boss_downed_in_round_one_is_a_burst_otherwise_each_action_is_checked() -> None:
    s = Stream()
    s.add(RoundStarted)
    first = s.mark()
    s.damage(BOSS, A1, 100, 60)
    s.damage(BOSS, A1, 60, 10)
    second = s.mark()
    s.damage(BOSS, A2, 10, 0)
    s.add(UnitDowned, unit_id=BOSS)
    m = _metrics(s.events, [first, second, s.mark()])
    assert m.boss_burst == "Boss 在第 1 輪被擊倒"
    # 第 2 輪才倒下、且每個動作都 < 60% 最大 HP：不是 burst
    s2 = Stream()
    s2.add(RoundStarted)
    b0 = s2.mark()
    s2.damage(BOSS, A1, 100, 70)
    b1 = s2.mark()
    s2.round = 2
    s2.damage(BOSS, A1, 70, 30)
    b2 = s2.mark()
    s2.damage(BOSS, A1, 30, 0)
    s2.add(UnitDowned, unit_id=BOSS)
    assert _metrics(s2.events, [b0, b1, b2, s2.mark()]).boss_burst is None


def test_boss_burst_threshold_is_sixty_percent_of_max_hp() -> None:
    def burst(after: int) -> str | None:
        s = Stream()
        s.add(RoundStarted)
        opening = s.mark()
        s.round = 2
        s.damage(BOSS, A1, 100, after)
        return _metrics(s.events, [opening, s.mark()]).boss_burst

    assert burst(41) is None  # 59%
    assert burst(40) is not None  # 剛好 60%


def test_one_shot_counts_actions_that_remove_a_non_boss_units_whole_hp() -> None:
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    # 動作 1：兩段傷害加起來 ≥ 30（最大 HP）→ one_shot
    s.damage(E1, A1, 30, 15)
    s.damage(E1, A1, 15, 0)
    s.add(UnitDowned, unit_id=E1)
    one = s.mark()
    # 動作 2：對 A2（最大 HP 40）分兩個動作各 25 → 都不是 one_shot
    s.damage(A2, E1, 40, 15)
    two = s.mark()
    s.damage(A2, E1, 15, 0)
    s.add(UnitDowned, unit_id=A2)
    three = s.mark()
    m = _metrics(s.events, [opening, one, two, three])
    assert m.one_shot_count == 1
    # 沒有動作邊界時整場視為一個動作 → A2 的 40 也算
    assert _metrics(s.events, None).one_shot_count == 2


def test_periodic_damage_is_not_part_of_the_single_action_damage() -> None:
    """持續傷害（status）與表面傷害是回合推進的結果，不計入 one_shot。"""
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    s.damage(E1, A1, 30, 15)
    s.damage(E1, None, 15, 0, "status")
    s.add(UnitDowned, unit_id=E1)
    assert _metrics(s.events, [opening, s.mark()]).one_shot_count == 0


def test_reinforcements_count_rounds_from_the_round_after_they_arrive() -> None:
    late = UnitId("late")
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    s.round = 2
    s.add(UnitSpawned, unit_id=late, template_id="grunt", team=Team.ENEMY, pos=Pos(x=1, y=1))
    s.add(RoundStarted)  # 第 3 輪開始時 late 才算在場
    s.round = 3
    s.add(RoundStarted)
    units = [*UNITS, UnitInfo(late, "grunt", Team.ENEMY, 30)]
    m = metrics_from_events(
        seed=1,
        units=units,
        events=s.events,
        bounds=[opening, s.mark()],
        ap_spent={},
        winner=None,
        rounds=3,
        actions=1,
    )
    assert next(u for u in m.units if u.unit_id == late).alive_rounds == 2
    assert next(u for u in m.units if u.unit_id == A1).alive_rounds == 3


def test_falls_and_deadly_terrain_use_the_source_carried_by_the_event() -> None:
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    # 動作 1：E1 被 A1 推下深淵，引擎在傷害事件上帶了推擊者 → 歸 A1，A1 得到擊倒
    s.damage(E1, A1, 30, 0, "deadly_terrain")
    s.add(UnitDowned, unit_id=E1)
    one = s.mark()
    # 動作 2：A1 自己走進深淵，沒有來源 → 歸環境
    s.damage(A1, None, 50, 0, "deadly_terrain")
    s.add(UnitDowned, unit_id=A1)
    m = _metrics(s.events, [opening, one, s.mark()])
    e1, a1 = _unit(m, E1), _unit(m, A1)
    assert e1.damage_taken == 30 and a1.damage_indirect == 30
    assert a1.kills == 1 and a1.damage_taken == 50
    assert m.environment_damage == {"ally": 50}


def test_fall_damage_with_a_source_counts_as_indirect_damage_of_that_unit() -> None:
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    s.damage(E1, A2, 30, 22, "fall")
    m = _metrics(s.events, [opening, s.mark()])
    assert (_unit(m, A2).damage_direct, _unit(m, A2).damage_indirect) == (0, 8)
    assert m.environment_damage == {}


def test_a_source_on_the_same_team_is_friendly_fire_not_dps() -> None:
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    s.damage(A2, A1, 40, 25, "fall")  # 隊友把人推下去
    m = _metrics(s.events, [opening, s.mark()])
    assert _unit(m, A1).damage_friendly == 15 and _unit(m, A1).damage_indirect == 0


def test_deadly_terrain_is_a_designed_kill_so_it_is_not_a_one_shot_but_can_burst_a_boss() -> None:
    s = Stream()
    s.add(RoundStarted)
    opening = s.mark()
    s.round = 2
    s.damage(E1, A1, 30, 0, "deadly_terrain")
    s.add(UnitDowned, unit_id=E1)
    one = s.mark()
    s.damage(BOSS, A1, 100, 40, "deadly_terrain")
    m = _metrics(s.events, [opening, one, s.mark()])
    assert m.one_shot_count == 0
    assert m.boss_burst is not None and "60／100" in m.boss_burst


# ---------------------------------------------------------------------------
# 真實戰鬥
# ---------------------------------------------------------------------------


def _real_run(map_id: str = "oil_depot", seed: int = 3) -> Any:
    lib = library()
    enc = lib.map(map_id).encounter
    assert enc is not None
    setup = build_setup(lib, map_id, enc.allies, enc.enemies, max_rounds=30)
    return setup, seed, lib


def test_real_battle_totals_are_consistent_with_the_event_log() -> None:
    setup, seed, lib = _real_run()
    run = run_tracked(setup, seed, UtilityAI(lib.ai_profiles), max_actions=20_000)
    m = battle_metrics(run)
    events = [e for e in run.events if isinstance(e, DamageDealt)]
    lost: Counter[UnitId] = Counter()
    for e in events:
        lost[e.target_id] += e.hp_before - e.hp_after
    assert {u.unit_id: u.damage_taken for u in m.units} == {
        u: lost.get(UnitId(u), 0) for u in (x.unit_id for x in m.units)
    }
    total_dealt = sum(u.damage_dealt + u.damage_friendly for u in m.units)
    traceable = sum(e.hp_before - e.hp_after for e in events if e.source_id is not None)
    assert total_dealt == traceable
    assert sum(lost.values()) == total_dealt + sum(m.environment_damage.values())
    downed = [e for e in run.events if isinstance(e, UnitDowned)]
    assert sum(1 for u in m.units if u.downed) == len(downed)
    assert sum(u.kills for u in m.units) <= len(downed)
    assert m.rounds == run.state.round and m.actions == len(run.actions)
    assert m.result == {None: "draw", Team.ALLY: "ally", Team.ENEMY: "enemy"}[run.state.winner]
    # 每個動作的邊界涵蓋全部事件；AP 取自狀態變化
    assert run.bounds[-1] == len(run.events) and len(run.bounds) == len(run.actions) + 1
    assert all(u.ap_spent >= 0 for u in m.units) and sum(u.ap_spent for u in m.units) > 0
    started = Counter(e.unit_id for e in run.events if isinstance(e, TurnStarted))
    assert {u.unit_id: u.turns for u in m.units} == {
        u.unit_id: started.get(UnitId(u.unit_id), 0) for u in m.units
    }


def test_metrics_do_not_depend_on_how_the_run_was_recorded() -> None:
    """``run_tracked`` 的邊界與 ``run_battle`` 之後重播取得的邊界得到同樣的指標。"""
    setup, seed, lib = _real_run("swamp", 1)
    tracked = run_tracked(setup, seed, UtilityAI(lib.ai_profiles), max_actions=20_000)
    plain = run_battle(setup, seed, UtilityAI(lib.ai_profiles))
    assert not hasattr(plain, "bounds")
    assert battle_metrics(tracked) == battle_metrics(plain)
    assert battle_metrics(plain) == battle_metrics(plain)


@pytest.mark.parametrize("map_id", ["bridge_chasm", "ruined_fort"])
def test_real_battle_control_turns_never_exceed_turns_taken(map_id: str) -> None:
    setup, seed, lib = _real_run(map_id, 2)
    m = battle_metrics(run_battle(setup, seed, UtilityAI(lib.ai_profiles)))
    inflicted = sum(sum(u.control_inflicted.values()) for u in m.units)
    inflicted += sum(m.environment_control.values())
    assert inflicted <= sum(u.turns for u in m.units) * 3


def test_triggered_passives_are_counted_and_attributed_like_a_skill_use() -> None:
    from trpg.engine.events import SkillTriggered, TriggerLimitReached  # noqa: PLC0415

    s = Stream()
    s.turn(A1)
    s.add(
        SkillTriggered,
        unit_id=A1,
        skill_id="skill_ember_brand",
        name_zh="餘燼烙印",
        trigger="on_hit",
        other_id=E1,
        trigger_depth=1,
    )
    s.damage(E1, A1, 30, 22)
    s.add(TriggerLimitReached, unit_id=A1, skill_id="skill_ember_brand", depth=4)
    m = _metrics(s.events, None)
    assert _unit(m, A1).triggers_fired == 1 and _unit(m, E1).triggers_fired == 0
    assert m.trigger_limit_count == 1
    assert m.skills["skill_ember_brand"].uses == 1
    assert m.skills["skill_ember_brand"].damage == 8
    assert m.skill_users["skill_ember_brand"] == ("ally",)
