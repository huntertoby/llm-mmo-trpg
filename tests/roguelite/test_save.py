"""存檔 → 讀檔 → 繼續，與一次打完逐位元相同（Phase 3-5a 驗收 1、2）。"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from tests.roguelite.helpers import VICTORY, full_run, library
from trpg.engine.ai.orders import HoldPosition, OrderSet
from trpg.engine.runner import LOG_FORMAT
from trpg.engine.state import state_to_json
from trpg.roguelite import (
    SAVE_FORMAT,
    ActiveBattle,
    RunSave,
    RunState,
    SaveFormatError,
    auto_play,
    dumps_save,
    load_save,
    loads_save,
    new_run,
    restore_battle,
    ruleset_hash,
    save_path,
    write_save,
)
from trpg.roguelite.auto import AutoStop
from trpg.roguelite.state import BattleNode, CampfireNode, LevelUpNode
from trpg.shared.types import Team


def _interrupted(build: str, seed: int, stop: AutoStop) -> RunState:
    """代打到 ``stop``，存成 JSON 文字、讀回、重播進行中的戰鬥，再代打到結束。"""
    lib = library()
    run, battle = auto_play(lib, new_run(lib, build, seed), stop=stop)
    assert not run.ended, "停止條件沒有觸發"
    text = dumps_save(
        RunSave(run_id="t", run=run, battle=None if battle is None else battle.to_saved())
    )
    save = loads_save(text)
    restored = restore_battle(lib, save)
    if battle is not None:
        assert restored is not None
        assert state_to_json(restored.state) == state_to_json(battle.state)
        assert restored.steps == battle.steps
    final, rest = auto_play(lib, save.run, restored)
    assert rest is None
    return final


def _mid_battle(index: int, steps: int) -> AutoStop:
    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        return battle is not None and battle.index == index and len(battle.steps) >= steps

    return stop


def _at_node(kind: type) -> AutoStop:
    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        return isinstance(run.node, kind)

    return stop


def test_same_seed_gives_the_same_run_twice() -> None:
    lib = library()
    a, _ = auto_play(lib, new_run(lib, *VICTORY))
    assert a.model_dump_json() == full_run(*VICTORY).model_dump_json()


def test_different_seeds_give_different_runs() -> None:
    assert full_run("build_fire", 0) != full_run("build_fire", 1)


@pytest.mark.parametrize(
    "stop",
    [
        _mid_battle(1, 0),
        _mid_battle(2, 37),
        _mid_battle(6, 15),
        _at_node(LevelUpNode),
        _at_node(CampfireNode),
    ],
    ids=["battle1_start", "battle2_step37", "boss_step15", "level_up", "campfire"],
)
def test_save_load_continue_matches_one_go_bit_for_bit(stop: AutoStop) -> None:
    final = _interrupted(*VICTORY, stop)
    assert final.model_dump_json() == full_run(*VICTORY).model_dump_json()


def test_save_mid_battle_with_restored_orders_replays_exactly() -> None:
    """戰鬥中存檔帶著隊友指令：讀檔後指令紀錄與目前的指令還原，之後的 AI 決策相同。"""
    lib = library()
    run = new_run(lib, *VICTORY)
    battle = ActiveBattle(lib, run)
    battle.auto(lambda b: len(b.steps) >= 5)
    hero = battle.state.units[battle.hero_id]
    orders = OrderSet(team_orders=(HoldPosition(at=hero.xy),))
    battle.policy.issue(battle.state, Team.ALLY, orders)
    battle.auto(lambda b: len(b.steps) >= 20)
    save = loads_save(dumps_save(RunSave(run_id="o", run=run, battle=battle.to_saved())))
    again = restore_battle(lib, save)
    assert again is not None
    assert again.policy.order_log == battle.policy.order_log
    assert again.policy.current_orders(Team.ALLY) == orders
    battle.auto()
    again.auto()
    assert again.steps == battle.steps
    assert state_to_json(again.state) == state_to_json(battle.state)


def test_save_json_has_format_and_engine_version(tmp_path: Path) -> None:
    lib = library()
    run, battle = auto_play(lib, new_run(lib, *VICTORY), stop=_mid_battle(1, 3))
    assert battle is not None
    path = write_save(tmp_path / "saves", RunSave(run_id="abc", run=run, battle=battle.to_saved()))
    assert path == save_path(tmp_path / "saves", "abc")
    assert path.name == "run-abc.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["format"] == SAVE_FORMAT == "trpg-run/7"
    assert raw["engine"] == LOG_FORMAT
    assert raw["battle"]["index"] == 1 and len(raw["battle"]["steps"]) == 3
    loaded = load_save(path)
    assert loaded.run == run
    assert isinstance(loaded.run.node, BattleNode)


def test_generated_skills_are_saved_with_their_definitions() -> None:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, *VICTORY))
    assert run.generated_skills
    raw = json.loads(dumps_save(RunSave(run_id="g", run=run)))
    ids = [s["id"] for s in raw["run"]["generated_skills"]]
    assert ids == [s.id for s in run.generated_skills]
    assert all(s["effects"] or s.get("modifiers") for s in raw["run"]["generated_skills"])
    assert all(i not in lib.skills for i in ids)


def test_wrong_format_and_engine_are_rejected() -> None:
    lib = library()
    run, battle = auto_play(lib, new_run(lib, *VICTORY), stop=_mid_battle(1, 3))
    assert battle is not None
    raw = json.loads(dumps_save(RunSave(run_id="w", run=run, battle=battle.to_saved())))
    with pytest.raises(SaveFormatError, match="trpg-run/7"):
        loads_save(json.dumps({**raw, "format": "trpg-run/0"}))
    for old in (
        "trpg-run/1",
        "trpg-run/2",
        "trpg-run/3",
        "trpg-run/4",
    ):  # 3-22、3-24b2、3-26a、3-26b：舊版存檔拒絕並提示
        with pytest.raises(SaveFormatError, match="開新一輪"):
            loads_save(json.dumps({**raw, "format": old}))
    with pytest.raises(SaveFormatError, match="引擎版本"):
        loads_save(json.dumps({**raw, "engine": "trpg-battle-log/1"}))
    between = json.loads(dumps_save(RunSave(run_id="w", run=run)))
    assert loads_save(json.dumps({**between, "engine": "trpg-battle-log/1"})).battle is None
    with pytest.raises(SaveFormatError, match="JSON"):
        loads_save("{")
    with pytest.raises(SaveFormatError, match="run_id"):
        save_path(Path("saves"), "../evil")


def test_a_save_whose_battle_does_not_match_the_run_is_rejected() -> None:
    lib = library()
    run, battle = auto_play(lib, new_run(lib, *VICTORY), stop=_mid_battle(1, 3))
    assert battle is not None
    saved = battle.to_saved().model_copy(update={"seed": battle.seed + 1})
    with pytest.raises(SaveFormatError, match="不符"):
        ActiveBattle.restore(lib, run, saved)


def test_ruleset_hash_is_stable_and_follows_content() -> None:
    lib = library()
    first = ruleset_hash(lib)
    assert first == ruleset_hash(lib)
    assert len(first) == 64
    assert ruleset_hash(dataclasses.replace(lib, files=lib.files[1:])) != first
