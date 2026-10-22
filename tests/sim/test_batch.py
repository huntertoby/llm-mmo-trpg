"""``trpg.sim.batch``（Phase 2C-1 驗收 5、6）：異常偵測、彙總與確定性。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.engine.actions import Action, EndTurn
from trpg.engine.ai import Policy
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.setup import build_setup
from trpg.engine.state import BattleState
from trpg.shared.types import Team
from trpg.sim.batch import (
    ANOMALY_KINDS,
    ONE_SHOT_SEED_LIMIT,
    REPORT_LIST_ADAPTER,
    BatchSpec,
    BattleOutcome,
    UtilityPolicyFactory,
    build_report,
    format_report,
    map_spec,
    run_batch,
    run_batches,
)
from trpg.sim.metrics import BattleMetrics, SkillMetrics, UnitMetrics


def _pass_policy(state: BattleState) -> Action:
    assert state.active_unit is not None
    return EndTurn(unit_id=state.active_unit)


def _pass_factory() -> Policy:
    return _pass_policy


def _crash_policy(state: BattleState) -> Action:
    raise RuntimeError("第一行\nboom: 最後一行")


def _crash_factory() -> Policy:
    return _crash_policy


def _spec(
    *,
    seeds: tuple[int, ...] = (0, 1, 2),
    factory: Any = None,
    max_rounds: int | None = 30,
    max_actions: int = 20_000,
    map_id: str = "oil_depot",
) -> BatchSpec:
    lib = library()
    enc = lib.map(map_id).encounter
    assert enc is not None
    setup = build_setup(lib, map_id, enc.allies, enc.enemies, max_rounds=max_rounds)
    return BatchSpec(
        name=map_id,
        setup=setup,
        seeds=seeds,
        policy_factory=factory or UtilityPolicyFactory(lib.ai_profiles),
        max_actions=max_actions,
    )


# ---------------------------------------------------------------------------
# 真實戰鬥的異常
# ---------------------------------------------------------------------------


def test_an_exception_in_one_battle_is_recorded_and_the_batch_continues() -> None:
    report = run_batch(_spec(seeds=(4, 5), factory=_crash_factory))
    assert (report.battles, report.completed) == (2, 0)
    anomaly = report.anomaly("exception")
    assert anomaly is not None and anomaly.count == 2 and anomaly.seeds == (4, 5)
    assert anomaly.details[4] == "RuntimeError: boom: 最後一行"  # 只取最後一行


def test_max_actions_is_reported_with_the_seed() -> None:
    report = run_batch(_spec(seeds=(0,), max_actions=5))
    anomaly = report.anomaly("max_actions")
    assert anomaly is not None and anomaly.seeds == (0,)
    assert report.anomaly("exception") is None and report.completed == 0


def test_draw_when_the_round_limit_is_reached() -> None:
    report = run_batch(_spec(seeds=(0, 1), factory=_pass_factory, max_rounds=2))
    assert (report.draws, report.draw_rate) == (2, 1.0)
    draw = report.anomaly("draw")
    assert draw is not None and draw.seeds == (0, 1)
    assert report.anomaly("long_battle") is None  # 2 輪 ≤ 10


def test_long_battle_when_more_than_ten_rounds() -> None:
    report = run_batch(_spec(seeds=(3,), factory=_pass_factory, max_rounds=12))
    long = report.anomaly("long_battle")
    assert long is not None and long.seeds == (3,) and long.details[3] == "12 輪"
    assert report.rounds_max == 12 and report.anomaly("draw") is not None


def test_a_normal_batch_has_no_crash_anomalies() -> None:
    report = run_batch(map_spec(library(), "oil_depot", range(3)))
    assert report.completed == 3
    assert report.anomaly("exception") is None and report.anomaly("max_actions") is None
    assert {a.kind for a in report.anomalies} <= set(ANOMALY_KINDS)


# ---------------------------------------------------------------------------
# 手工指標的彙總與異常（chain_limit、boss_burst、one_shot）
# ---------------------------------------------------------------------------


def _unit(
    unit_id: str,
    template: str,
    team: Team,
    *,
    rounds: int = 4,
    turns: int = 4,
    ap: int = 8,
    direct: int = 0,
    indirect: int = 0,
    taken: int = 0,
    healing: int = 0,
    kills: int = 0,
    downed: bool = False,
    control: dict[str, int] | None = None,
) -> UnitMetrics:
    return UnitMetrics(
        unit_id=unit_id,
        template_id=template,
        team=team,
        alive_rounds=rounds,
        turns=turns,
        ap_spent=ap,
        damage_direct=direct,
        damage_indirect=indirect,
        damage_friendly=0,
        damage_taken=taken,
        healing_done=healing,
        kills=kills,
        downed=downed,
        control_inflicted=control or {},
    )


def _metrics(seed: int, result: str = "ally", rounds: int = 4, **kw: Any) -> BattleMetrics:
    fields: dict[str, Any] = {
        "seed": seed,
        "result": result,
        "rounds": rounds,
        "actions": 10,
        "units": (),
        "environment_damage": {},
        "environment_control": {},
        "skills": {},
        "skill_users": {},
        "chain_limit_count": 0,
        "boss_burst": None,
        "one_shot_count": 0,
    }
    fields.update(kw)
    return BattleMetrics(**fields)


def test_chain_limit_boss_burst_and_one_shot_anomalies() -> None:
    outcomes = [
        BattleOutcome(0, _metrics(0, chain_limit_count=2)),
        BattleOutcome(1, _metrics(1, boss_burst="Boss 在第 1 輪被擊倒")),
        BattleOutcome(2, _metrics(2, chain_limit_count=1, one_shot_count=2)),
        *(BattleOutcome(s, _metrics(s, one_shot_count=1)) for s in range(3, 10)),
    ]
    report = build_report("x", outcomes)
    chain = report.anomaly("chain_limit")
    assert chain is not None and chain.count == 3 and chain.seeds == (0, 2)  # 次數 ＝ 事件總數
    assert chain.details == {0: "2 次", 2: "1 次"}
    burst = report.anomaly("boss_burst")
    assert burst is not None and burst.seeds == (1,) and "第 1 輪" in burst.details[1]
    shot = report.anomaly("one_shot")
    assert shot is not None and shot.count == 2 + 7  # 計數是全部
    assert shot.seeds == (2, 3, 4, 5, 6) and len(shot.seeds) == ONE_SHOT_SEED_LIMIT  # 只列前 5 個
    assert report.anomaly("draw") is None and report.anomaly("long_battle") is None
    assert [a.kind for a in report.anomalies] == ["chain_limit", "boss_burst", "one_shot"]


def test_aggregates_rates_rounds_templates_control_and_skills() -> None:
    m1 = _metrics(
        0,
        "ally",
        rounds=4,
        units=(
            _unit("a", "hero", Team.ALLY, direct=40, indirect=8, taken=10, kills=2, healing=6),
            _unit(
                "b",
                "grunt",
                Team.ENEMY,
                rounds=2,
                turns=2,
                ap=3,
                direct=6,
                taken=30,
                downed=True,
                control={"slow": 1},
            ),
        ),
        environment_damage={"enemy": 4},
        environment_control={"stun": 2},
        skills={"skill_a": SkillMetrics(uses=2, rolls=3, hits=2, damage=30, healed=0)},
        skill_users={"skill_a": ("ally",)},
    )
    m2 = _metrics(
        1,
        "enemy",
        rounds=6,
        units=(
            _unit("a", "hero", Team.ALLY, rounds=3, direct=12, taken=40, downed=True),
            _unit("b", "grunt", Team.ENEMY, rounds=6, turns=6, ap=12, direct=24, taken=5),
        ),
        skills={"skill_a": SkillMetrics(uses=1, rolls=1, hits=0, damage=0, healed=0)},
        skill_users={"skill_a": ("ally",)},
    )
    m3 = _metrics(2, "draw", rounds=8)
    report = build_report(
        "agg",
        [BattleOutcome(2, m3), BattleOutcome(1, m2), BattleOutcome(0, m1)],  # 亂序輸入
        equipped=("skill_a", "skill_never"),
        max_rounds=30,
    )
    assert (report.ally_wins, report.enemy_wins, report.draws) == (1, 1, 1)
    assert report.ally_win_rate == pytest.approx(1 / 3)
    assert (report.rounds_mean, report.rounds_median) == (6.0, 6.0)
    assert (report.rounds_min, report.rounds_max) == (4, 8)
    assert report.actions_mean == 10.0
    ally = report.team(Team.ALLY)
    # 陣營 DPR：每場（傷害 ÷ 輪數）再平均：m1 40/4、m2 12/6、m3 0
    assert ally.dpr_direct == pytest.approx((10 + 2 + 0) / 3)
    assert ally.dpr_indirect == pytest.approx((8 / 4) / 3)
    enemy = report.team(Team.ENEMY)
    assert enemy.dpr_direct == pytest.approx((6 / 4 + 24 / 6) / 3)
    assert enemy.environment_damage_taken == pytest.approx(4 / 3)
    hero = next(t for t in report.templates if t.template_id == "hero")
    # 實例 DPR：(48/4)=12、(12/3)=4 → 平均 8；承受 25；存活 1/2
    assert (hero.instances, hero.dpr, hero.damage_taken) == (2, 8.0, 25.0)
    assert (hero.healing, hero.kills, hero.survival) == (3.0, 1.0, 0.5)
    assert hero.ap_per_turn == pytest.approx(16 / 8)
    grunt = next(t for t in report.templates if t.template_id == "grunt")
    assert grunt.survival == 0.5 and grunt.ap_per_turn == pytest.approx(15 / 8)
    assert [t.template_id for t in report.templates] == ["hero", "grunt"]  # 我方在前
    control = {c.source: c.turns for c in report.control}
    assert control["enemy"]["slow"] == pytest.approx(1 / 3)  # 敵方單位施加的緩速
    assert control["environment"]["stun"] == pytest.approx(2 / 3)
    assert control["ally"] == {"stun": 0.0, "frozen": 0.0, "root": 0.0, "slow": 0.0}
    skill = report.skills[0]
    assert skill.skill_id == "skill_a" and skill.teams == ("ally",)
    assert skill.uses_per_battle == pytest.approx(1.0)
    assert skill.hit_rate == pytest.approx(2 / 4) and skill.avg_damage == pytest.approx(10.0)
    assert report.unused_skills == ("skill_never",)


def test_report_text_and_json_round_trip() -> None:
    report = run_batch(map_spec(library(), "swamp", range(2)))
    text = format_report(report)
    for section in ("## swamp", "勝負：", "輪數：", "陣營 DPR", "單位範本", "控制回合", "技能使用"):
        assert section in text
    assert "從未使用的技能：" in text and "異常：" in text
    assert format_report(report) == text
    restored = REPORT_LIST_ADAPTER.validate_json(REPORT_LIST_ADAPTER.dump_json([report]))
    assert restored == [report]


# ---------------------------------------------------------------------------
# 確定性
# ---------------------------------------------------------------------------


def test_same_spec_twice_gives_equal_reports() -> None:
    spec = map_spec(library(), "bridge_chasm", range(3))
    assert run_batch(spec) == run_batch(spec)


@pytest.mark.xdist_group("sim_pool")
@pytest.mark.slow
def test_report_does_not_depend_on_the_number_of_jobs() -> None:
    lib = library()
    specs = [map_spec(lib, "oil_depot", range(3)), map_spec(lib, "swamp", range(1, 4))]
    one = run_batches(specs, jobs=1)
    two = run_batches(specs, jobs=2)
    assert one == two
    assert [format_report(r) for r in one] == [format_report(r) for r in two]
    assert [r.name for r in two] == ["oil_depot", "swamp"]


def test_seed_order_in_the_spec_does_not_change_the_report() -> None:
    lib = library()
    forward = run_batch(map_spec(lib, "oil_depot", [0, 1, 2]))
    backward = run_batch(map_spec(lib, "oil_depot", [2, 1, 0]))
    assert forward == backward


def test_jobs_must_be_positive() -> None:
    with pytest.raises(ValueError):
        run_batches([_spec()], jobs=0)


def test_utility_policy_factory_builds_a_fresh_policy_each_time() -> None:
    factory = UtilityPolicyFactory(library().ai_profiles)
    assert isinstance(factory(), UtilityAI) and factory() is not factory()
