"""Boss 的階段（Phase 5F-2；``docs/phases/Phase5計畫.md`` 34.4、34.8）。

行為一致測試：都實際跑引擎（``start_battle``／``resolve``／``run_battle``／``replay``）。HP 門檻用
「把 Boss 的 HP 設好、讓行動者結束回合」觸發——結算收尾（``finish_resolution``）一定會檢查。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_setup, spawn, template
from trpg.content.battle import BossPhase, UnitTemplate
from trpg.content.skills import CHARGING
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.actions import EndTurn
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.environment import telegraph
from trpg.engine.events import (
    BossPhaseChanged,
    EventBase,
    FollowupCancelled,
    UnitSpawned,
    WeatherChanged,
)
from trpg.engine.results import ResolveResult
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, build_setup, with_phase_assets
from trpg.engine.state import state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.types import Surface, Team, UnitId

HERO = UnitId("unit_0001")
BOSS = UnitId("unit_0002")

PHASES = (
    {"id": "one", "name_zh": "一"},
    {
        "id": "two",
        "name_zh": "二",
        "trigger": {"kind": "hp_below", "permille": 600},
        "text_zh": "起霧了。",
        "skills": ["skill_blink"],
        "ai_profile": "cunning",
        "add_statuses": [{"status": "concealed", "duration": 2}],
        "weather": "fog",
        "tiles": [{"at": [2, 2], "surface": "water"}],
        "spawns": [{"template": "bandit", "count": 2}],
    },
    {
        "id": "three",
        "name_zh": "三",
        "trigger": {"kind": "hp_below", "permille": 300},
        "skills": ["skill_first_strike"],
        "ai_profile": "brute",
        "remove_statuses": ["concealed"],
        "weather": "clear",
    },
)


def _boss(**overrides: object) -> UnitTemplate:
    fields: dict[str, object] = {
        "max_hp": 100,
        "tags": ("boss", "humanoid"),
        "skills": ("skill_charged_cleave",),
        "phases": PHASES,
        "reactions": (),
    }
    fields.update(overrides)
    return template("bandit", **fields)


def _state(boss: UnitTemplate | None = None) -> BattleState:
    lib = library()
    hero = template("hero_fighter", reactions=())
    setup = make_setup(
        lib.map("test_flat_6x6"),
        [spawn(Team.ALLY, (0, 4), hero), spawn(Team.ENEMY, (4, 0), boss or _boss())],
        max_rounds=30,
    )
    return start_battle(with_phase_assets(lib, setup), 0)


def _end_turn_at(state: BattleState, hp: int, *, actor: UnitId = HERO) -> ResolveResult:
    s = give_turn(state, actor)
    s.units[BOSS].hp = hp
    return resolve(s, EndTurn(unit_id=actor))


def _phases(events: list[EventBase]) -> list[int]:
    return [e.phase for e in events if isinstance(e, BossPhaseChanged)]


# ---------------------------------------------------------------------------
# 門檻觸發（表格）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hp", "fired", "index"),
    [
        (100, [], 0),
        (61, [], 0),
        (60, [2], 1),  # 剛好 60% 也算（代決 5F2-3）
        (31, [2], 1),
        (30, [2, 3], 2),  # 一次跌破兩個門檻：依序觸發（代決 5F2-2）
        (1, [2, 3], 2),
    ],
)
def test_threshold_table(hp: int, fired: list[int], index: int) -> None:
    result = _end_turn_at(_state(), hp)
    assert _phases(result.events) == fired
    assert result.state.units[BOSS].phase_index == index


def test_each_phase_fires_once_even_after_healing() -> None:
    first = _end_turn_at(_state(), 55)
    assert _phases(first.events) == [2]
    healed = _end_turn_at(first.state, 100)  # 治療回門檻以上：不退回、不再觸發
    assert _phases(healed.events) == []
    assert healed.state.units[BOSS].phase_index == 1
    again = _end_turn_at(healed.state, 50)
    assert _phases(again.events) == []
    third = _end_turn_at(again.state, 20)
    assert _phases(third.events) == [3]


def test_the_downing_blow_does_not_fire() -> None:
    s = give_turn(_state(), HERO)
    s.units[BOSS].hp = 0
    s.units[BOSS].downed = True
    result = resolve(s, EndTurn(unit_id=HERO))
    assert _phases(result.events) == []


# ---------------------------------------------------------------------------
# 轉換的內容
# ---------------------------------------------------------------------------


def test_phase_two_changes_skills_ai_status_weather_tiles_and_spawns() -> None:
    state = _state()
    assert state.weather is None  # 測試設定沒給天氣＝晴朗
    result = _end_turn_at(state, 59)
    s = result.state
    boss = s.units[BOSS]
    assert boss.skills == ("skill_blink",)
    assert boss.ai_profile == "cunning"
    assert boss.has_status("concealed")
    assert s.weather is not None and s.weather.id == "fog"
    assert s.tile(2, 2).surface is Surface.WATER
    changed = [e for e in result.events if isinstance(e, BossPhaseChanged)]
    assert (changed[0].phase_id, changed[0].total, changed[0].permille) == ("two", 3, 600)
    weather = [e for e in result.events if isinstance(e, WeatherChanged)]
    assert [(e.before, e.after) for e in weather] == [(None, "fog")]
    spawned = [e for e in result.events if isinstance(e, UnitSpawned)]
    assert [e.template_id for e in spawned] == ["bandit", "bandit"]
    new_ids = [e.unit_id for e in spawned]
    assert all(s.units[u].team is Team.ENEMY for u in new_ids)
    assert s.turn_order[-2:] == new_ids  # 新單位排在先攻順序最後
    # 事件順序：轉換 → 天氣 → 召喚
    seqs = [
        next(e.seq for e in result.events if isinstance(e, cls))
        for cls in (BossPhaseChanged, WeatherChanged, UnitSpawned)
    ]
    assert seqs == sorted(seqs)


def test_phase_three_removes_concealment_and_clears_weather() -> None:
    result = _end_turn_at(_state(), 59)
    result = _end_turn_at(result.state, 10)
    s = result.state
    boss = s.units[BOSS]
    assert boss.skills == ("skill_first_strike",)
    assert boss.ai_profile == "brute"
    assert not boss.has_status("concealed")
    assert s.weather is not None and s.weather.id == "clear"


def test_charging_strike_survives_a_phase_change() -> None:
    s = give_turn(_state(), BOSS)
    s.units[BOSS].hp = 59  # 施放這一步的收尾就會進入第 2 階段
    cast = resolve(s, UseSkill(unit_id=BOSS, skill_id="skill_charged_cleave"))
    assert _phases(cast.events) == [2]
    boss = cast.state.units[BOSS]
    assert boss.has_status(CHARGING)
    assert "skill_charged_cleave" not in boss.skills
    assert [c.skill_id for c in telegraph(cast.state).charges] == ["skill_charged_cleave"]
    state = cast.state
    cancelled: list[FollowupCancelled] = []
    for _ in range(10):
        assert state.active_unit is not None
        step = resolve(state, EndTurn(unit_id=state.active_unit))
        cancelled += [e for e in step.events if isinstance(e, FollowupCancelled)]
        state = step.state
        if not state.units[BOSS].has_status(CHARGING):
            break
    assert not state.units[BOSS].has_status(CHARGING)
    assert cancelled == []  # 照常釋放（代決 5F2-4）


def test_cooldowns_kept_only_for_the_new_skill_set() -> None:
    s = give_turn(_state(), HERO)
    s.units[BOSS].cooldowns = {"skill_charged_cleave": 3, "skill_blink": 3}
    s.units[BOSS].hp = 59
    result = resolve(s, EndTurn(unit_id=HERO))
    cooldowns = result.state.units[BOSS].cooldowns
    assert set(cooldowns) == {"skill_blink"}  # 換手後 Boss 的回合開始可能已倒數 1
    assert cooldowns["skill_blink"] in (2, 3)


def test_missing_phase_assets_do_not_crash() -> None:
    """沒經過 ``with_phase_assets`` 的設定：天氣不改、召喚落空，戰鬥照常。"""
    lib = library()
    setup = make_setup(
        lib.map("test_flat_6x6"),
        [spawn(Team.ALLY, (0, 4), "hero_fighter"), spawn(Team.ENEMY, (4, 0), _boss())],
    )
    state = start_battle(setup, 0)
    result = _end_turn_at(state, 50)
    assert _phases(result.events) == [2]
    assert not any(isinstance(e, WeatherChanged) for e in result.events)
    assert not any(isinstance(e, UnitSpawned) for e in result.events)


def test_battle_log_text() -> None:
    result = _end_turn_at(_state(), 59)
    text = [describe_event(e, result.state) for e in result.events]
    assert (
        "◆ bandit 進入第 2 階段「二」（HP 60% 以下）：起霧了。".replace(
            "bandit", result.state.units[BOSS].name_zh
        )
        in text
    )
    assert "  ☁ 天氣變為濃霧" in text


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phases", "message"),
    [
        ([{"id": "a", "name_zh": "甲"}], "2～4 項"),
        (
            [
                {"id": "a", "name_zh": "甲", "trigger": {"kind": "hp_below", "permille": 900}},
                {"id": "b", "name_zh": "乙", "trigger": {"kind": "hp_below", "permille": 500}},
            ],
            "開場階段",
        ),
        (
            [
                {"id": "a", "name_zh": "甲"},
                {"id": "b", "name_zh": "乙", "trigger": {"kind": "hp_below", "permille": 300}},
                {"id": "c", "name_zh": "丙", "trigger": {"kind": "hp_below", "permille": 500}},
            ],
            "門檻必須比前一個階段低",
        ),
        (
            [{"id": "a", "name_zh": "甲"}, {"id": "b", "name_zh": "乙"}],
            "缺少 trigger",
        ),
        (
            [
                {"id": "a", "name_zh": "甲"},
                {"id": "a", "name_zh": "乙", "trigger": {"kind": "hp_below", "permille": 500}},
            ],
            "不能重複",
        ),
    ],
)
def test_phase_schema_rejects(phases: list[dict[str, object]], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _boss(phases=phases)


def test_unknown_trigger_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        BossPhase.model_validate(
            {"id": "x", "name_zh": "x", "trigger": {"kind": "round_at", "permille": 1}}
        )


# ---------------------------------------------------------------------------
# 霧鎖真人、九轉回天的預告；整場重播
# ---------------------------------------------------------------------------


def test_mist_lock_peaks_telegraphs_a_cross() -> None:
    """5F-2b：十字每臂 2 格，共 9 格（``arm: 2``）。"""
    lib = library()
    master = lib.unit("sect_mist_lock_master").model_copy(
        update={"skills": ("skill_mist_lock_peaks",), "phases": ()}
    )
    setup = make_setup(
        lib.map("test_flat_6x6"),
        [spawn(Team.ALLY, (0, 4), "hero_fighter"), spawn(Team.ENEMY, (2, 2), master)],
    )
    state = give_turn(start_battle(setup, 0), BOSS)
    result = resolve(state, UseSkill(unit_id=BOSS, skill_id="skill_mist_lock_peaks"))
    charges = telegraph(result.state).charges
    assert [c.name_zh for c in charges] == ["霧鎖千山"]
    tiles = {(p.x, p.y) for p in charges[0].tiles}
    assert tiles == {(2, 2), (1, 2), (0, 2), (3, 2), (4, 2), (2, 1), (2, 0), (2, 3), (2, 4)}
    assert result.state.units[BOSS].ap == 0  # 整回合蓄力


def test_nine_turns_revival_telegraphs_a_square() -> None:
    lib = library()
    setup = make_setup(
        lib.map("test_flat_6x6"),
        [
            spawn(Team.ALLY, (0, 5), "hero_fighter"),
            spawn(Team.ENEMY, (2, 2), "sect_steward", skills=None),
        ],
    )
    state = give_turn(start_battle(setup, 0), BOSS)
    result = resolve(state, UseSkill(unit_id=BOSS, skill_id="skill_nine_turns_revival"))
    charges = telegraph(result.state).charges
    assert [c.name_zh for c in charges] == ["九轉回天"]
    assert len(charges[0].tiles) == 9


def _summit_setup() -> BattleSetup:
    lib = library()
    m = lib.map("cloud_summit")
    assert m.encounter is not None
    return build_setup(lib, "cloud_summit", m.encounter.allies, m.encounter.enemies, max_rounds=30)


@pytest.mark.parametrize(
    "seed",
    [1, 3],  # CB-2d：aim_hit_permille 700 後種子 0 打不到第 3 階段
)  # 5F-2b 加 HP 後種子 1 只到第 2 階段；CB-1 門檻 8 後 3、4 → 0、5
def test_summit_battle_runs_all_phases_and_replays(seed: int) -> None:
    setup = _summit_setup()
    assert sorted(setup.spawn_templates) == ["sect_mist_walker"]
    assert sorted(setup.phase_weathers) == ["clear", "fog"]
    run = run_battle(setup, seed, UtilityAI(library().ai_profiles))
    assert run.state.ended
    assert _phases(run.events) == [2, 3]
    again = replay(setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


# ---------------------------------------------------------------------------
# 畫面：單位卡的階段與特性句
# ---------------------------------------------------------------------------


def test_unit_view_reports_phase_and_next_threshold() -> None:
    from trpg.engine.view import project_for  # noqa: PLC0415

    state = _state()
    view = {u.id: u for u in project_for(state, Team.ALLY).units}
    phase = view[BOSS].boss_phase
    assert phase is not None
    assert (phase.index, phase.total, phase.name_zh) == (1, 3, "一")
    assert (phase.next_name_zh, phase.next_permille) == ("二", 600)
    assert view[HERO].boss_phase is None
    last = _end_turn_at(state, 10).state
    phase = {u.id: u for u in project_for(last, Team.ALLY).units}[BOSS].boss_phase
    assert phase is not None
    assert (phase.index, phase.next_name_zh, phase.next_permille) == (3, None, None)


def test_trait_line_lists_phases_from_data() -> None:
    from trpg.narrative.unit_traits import unit_trait_lines  # noqa: PLC0415

    lines = unit_trait_lines(library(), "sect_mist_lock_master")
    assert "階段：劍陣 → HP 60%「鎖霧」 → 30%「歸一」" in lines
