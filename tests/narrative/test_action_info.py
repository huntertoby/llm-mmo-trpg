"""基本動作與勝利條件的規則說明（Phase 3-41b）：數字取自 ``core.yaml``，改資料文字跟著變；
勝利條件的文字和 ``engine/objectives.py`` 的判定一致。"""

from __future__ import annotations

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from trpg.api.glossary import build_glossary
from trpg.engine import EndTurn, resolve
from trpg.engine.state import BattleState
from trpg.narrative.action_info import ROUNDS_PLACEHOLDER, action_texts, objective_texts
from trpg.shared.types import Team, UnitId

ALL_ACTIONS = {
    "move",
    "attack",
    "run",
    "defend",
    "shove",
    "trip",
    "interact",
    "shove_aside",
    "swap",
    "aim",
    "vault",
    "reload",
    "end_stance",
    "stand",
    "end_turn",
}


def _by_id(core_update: dict[str, int] | None = None) -> dict[str, str]:
    core = library().ruleset.core
    if core_update:
        core = core.model_copy(update=core_update)
    return {t.id: "".join((t.summary_zh, *t.lines_zh)) for t in action_texts(core)}


def test_every_action_has_a_text() -> None:
    assert set(_by_id()) == ALL_ACTIONS
    for t in action_texts(library().ruleset.core):
        assert t.name_zh and t.summary_zh and t.lines_zh, t.id


def test_numbers_come_from_core_rules() -> None:
    base = _by_id()
    assert "+3 格" in base["run"] and "+25%" in base["defend"]
    changed = _by_id({"run_move_bonus": 5, "defend_defense_bonus_permille": 400, "run_ap_cost": 2})
    assert "+5 格" in changed["run"] and "花 2 AP" in changed["run"]
    assert "+40%" in changed["defend"] and "+25%" not in changed["defend"]
    assert "命中 +2" in base["aim"]
    assert "命中 +4" in _by_id({"aim_hit_bonus": 4})["aim"]


def test_glossary_carries_actions_and_objectives() -> None:
    glossary = build_glossary(library())
    assert {e.id for e in glossary.actions} == ALL_ACTIONS
    run = next(e for e in glossary.actions if e.id == "run")
    assert run.name_zh == "跑步" and run.description_zh and run.rules_zh
    ids = {e.id for e in glossary.objectives}
    assert {"eliminate", "escape", "defend", "exit", "point"} <= ids
    assert {f"result_{r}" for r in ("escaped", "escape_failed", "defended", "point_lost")} <= ids


def test_objective_texts_have_the_rounds_placeholder() -> None:
    by_id = {t.id: t for t in objective_texts()}
    for kind in ("escape", "defend"):
        assert ROUNDS_PLACEHOLDER in by_id[kind].summary_zh
    assert ROUNDS_PLACEHOLDER not in by_id["eliminate"].summary_zh


def _defend_state() -> BattleState:
    m = make_map(
        "00000",
        objective={"kind": "defend", "rounds": 2, "tiles": [[2, 0]]},
        ally=[(0, 0)],
        enemy=[(4, 0)],
    )
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (4, 0), no_reactions()),
            spawn(Team.ENEMY, (2, 0), no_reactions()),
        ],
    )


def test_text_claim_enemy_summons_do_not_count_on_the_point() -> None:
    """文字寫「敵方召喚物不算」：召喚物站在守點上，一輪結束也不失守。"""
    state = give_turn(_defend_state(), "unit_0001")
    state.units[UnitId("unit_0003")].owner_id = UnitId("unit_0002")  # 守點上的那隻是召喚物
    for _ in range(3):
        if state.ended:
            break
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    assert state.end_reason != "point_lost"
    by_id = {t.id: t for t in objective_texts()}
    assert "敵方召喚物不算" in "".join(by_id["defend"].lines_zh)
