"""Phase 3-26a：技能點與技能等級（取得、花點、重配、卸下保留、換裝、戰鬥帶入、存檔、重播）。

3-26b 的分歧進化另有測試（``test_evolution.py``）；這裡用關掉進化的內容庫（沒有進化模板、
門檻 0 次），讓 3 級照 3-26a 的規則直接升。
"""

from __future__ import annotations

import dataclasses
import json
from functools import cache

import pytest

from tests.roguelite.helpers import library as full_library
from trpg.content.library import ContentLibrary
from trpg.content.skill_evolution import EvolutionTable
from trpg.engine.state import state_to_json
from trpg.roguelite import (
    ActiveBattle,
    ChoiceError,
    NodeConflictError,
    RunSave,
    RunState,
    apply_choice,
    auto_choice,
    auto_play,
    battle_setup,
    dumps_save,
    loads_save,
    new_run,
    restore_battle,
)
from trpg.roguelite.auto import AutoStop, auto_levels
from trpg.roguelite.growth import battle_levels, level_of, respec, set_loadout, spent_points
from trpg.roguelite.progress import hero_unit_id
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    LevelUpChoice,
    LevelUpNode,
    LoadoutChoice,
    RespecChoice,
    SpendChoice,
)
from trpg.shared.types import Attribute

BUILD = "build_fire"


@cache
def library() -> ContentLibrary:
    """關掉分歧進化的內容庫（見模組說明）。"""
    lib = full_library()
    growth = lib.ruleset.skill_growth.model_copy(update={"evolve_uses": 0})
    ruleset = lib.ruleset.model_copy(update={"skill_growth": growth})
    return dataclasses.replace(lib, ruleset=ruleset, evolution=EvolutionTable())


def _stop_at(kind: type[object], *, nth: int = 1) -> AutoStop:
    seen = 0

    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        nonlocal seen
        if isinstance(run.node, kind):
            seen += 1
        return seen >= nth

    return stop


def _at(kind: type[object], seed: int = 0, nth: int = 1) -> RunState:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, BUILD, seed), stop=_stop_at(kind, nth=nth))
    assert isinstance(run.node, kind)
    return run


def _actives(run: RunState) -> list[str]:
    lib = library()
    defs = {**lib.skills, **{s.id: s for s in run.generated_skills}}
    return [s for s in run.hero.skills if defs[s].kind == "active"]


def _level_up_choice(run: RunState, **fields: object) -> LevelUpChoice:
    node = run.node
    assert isinstance(node, LevelUpNode)
    return LevelUpChoice(attributes={Attribute.STR: node.points}, pick=None, **fields)  # type: ignore[arg-type]


def test_a_new_run_has_no_points_and_every_level_up_gives_two() -> None:
    lib = library()
    run = new_run(lib, BUILD, 0)
    assert (run.skill_points, run.skill_levels, run.bench) == (0, {}, ())
    points = lib.ruleset.skill_growth.points_per_level
    assert points == 2
    first = _at(LevelUpNode)
    assert first.level == 2 and first.skill_points == points
    second = apply_choice(lib, first, _level_up_choice(first))
    third = _at(LevelUpNode, nth=2)
    # AI 代打每次升級都花光：已花 ＋ 未花 ＝ 每級 2 點 × 升過的級數
    assert third.level == 3 and third.skill_points + spent_points(lib, third) == 2 * points
    assert second.skill_points == points  # 升級選擇本身不吃點數


def test_spend_points_raises_levels_for_one_point_each() -> None:
    lib = library()
    run = _at(LevelUpNode)
    skill = _actives(run)[0]
    spent = apply_choice(lib, run, SpendChoice(levels={skill: 2}))
    assert (spent.skill_points, spent.skill_levels) == (1, {skill: 2})
    assert isinstance(spent.node, LevelUpNode)  # 不推進節點
    again = apply_choice(lib, spent, SpendChoice(levels={skill: 3}))
    assert (again.skill_points, level_of(again, skill)) == (0, 3)
    assert spent_points(lib, again) == 2


def test_spend_points_rejects_bad_requests_and_leaves_the_run_unchanged() -> None:
    lib = library()
    run = _at(LevelUpNode)
    skill = _actives(run)[0]
    with pytest.raises(ChoiceError, match="技能點不足"):
        apply_choice(lib, run, SpendChoice(levels={skill: 4}))
    with pytest.raises(ChoiceError, match="只能往上升"):
        apply_choice(lib, run, SpendChoice(levels={skill: 1}))
    with pytest.raises(ChoiceError, match="最高 5 級"):
        apply_choice(lib, run, SpendChoice(levels={skill: 6}))
    with pytest.raises(ChoiceError, match="沒有裝備"):
        apply_choice(lib, run, SpendChoice(levels={"skill_nobody": 2}))
    passives = [s for s in run.hero.skills if s not in _actives(run)]
    if passives:
        with pytest.raises(ChoiceError, match="不是主動技能"):
            apply_choice(lib, run, SpendChoice(levels={passives[0]: 2}))
    assert run.skill_levels == {} and run.skill_points == 2


def test_spend_can_ride_along_with_the_level_up_choice() -> None:
    lib = library()
    run = _at(LevelUpNode)
    skill = _actives(run)[0]
    after = apply_choice(lib, run, _level_up_choice(run, levels={skill: 3}))
    assert after.skill_levels == {skill: 3} and after.skill_points == 0
    with pytest.raises(ChoiceError, match="技能點不足"):
        apply_choice(lib, run, _level_up_choice(run, levels={skill: 4}))


def test_the_level_up_spend_is_checked_before_anything_changes() -> None:
    lib = library()
    run = _at(LevelUpNode)
    skill = _actives(run)[0]
    with pytest.raises(ChoiceError):
        apply_choice(lib, run, _level_up_choice(run, levels={skill: 5}))
    assert run.level == 2 and isinstance(run.node, LevelUpNode)


def test_spending_is_blocked_after_the_run_ends_and_respec_only_at_the_campfire() -> None:
    lib = library()
    run = _at(LevelUpNode)
    with pytest.raises(NodeConflictError, match="營火"):
        apply_choice(lib, run, RespecChoice())
    with pytest.raises(NodeConflictError, match="營火"):
        apply_choice(lib, run, LoadoutChoice(skills=run.hero.skills))
    ended = run.model_copy(update={"node": BattleNode(index=1)})
    assert (
        apply_choice(lib, ended, SpendChoice(levels={})) == ended
    )  # 戰鬥前（沒有進行中的戰鬥）可以花


def test_auto_play_spends_points_on_the_first_active_skill_until_it_is_full() -> None:
    lib = library()
    run = _at(CampfireNode)
    first = _actives(run)[0]
    # 第一個營火前升了 2 級 × 2 點 ＝ 4 點：全部集中在第一招，剛好升到 5 級
    assert level_of(run, first) == 5 and run.skill_points == 0
    assert run.skill_levels == {first: 5}
    assert spent_points(lib, run) == 4
    assert auto_levels(lib, run) == {}  # 沒有點數就沒有要花的


def test_respec_refunds_every_point_for_free() -> None:
    lib = library()
    run = _at(CampfireNode)
    before = run.skill_points + spent_points(lib, run)
    refunded = apply_choice(lib, run, RespecChoice())
    assert refunded.skill_levels == {} and refunded.skill_points == before
    assert isinstance(refunded.node, CampfireNode)
    redone = apply_choice(lib, refunded, SpendChoice(levels={_actives(run)[0]: 4}))
    assert level_of(redone, _actives(run)[0]) == 4 and redone.skill_points == before - 3
    assert respec(lib, redone).skill_points == before


def test_unequipped_skills_keep_their_levels_and_can_be_equipped_again() -> None:
    lib = library()
    run = _at(CampfireNode)
    first = _actives(run)[0]
    lost = set_loadout(lib, run, tuple(s for s in run.hero.skills if s != first))
    assert first in lost.bench and first not in lost.hero.skills
    assert level_of(lost, first) == 5  # 卸下後等級保留
    assert first not in battle_levels(lost)  # 沒裝備就不帶進戰鬥
    back = set_loadout(lib, lost, (*lost.hero.skills, first))
    assert first not in back.bench and first in back.hero.skills and level_of(back, first) == 5
    assert battle_levels(back)[first] == 5
    # 營火的選擇走 apply_choice，不推進節點
    via = apply_choice(lib, run, LoadoutChoice(skills=lost.hero.skills))
    assert via == lost and isinstance(via.node, CampfireNode)


def test_loadout_rejects_unknown_duplicate_and_overfull_equipment() -> None:
    lib = library()
    run = _at(CampfireNode)
    with pytest.raises(ChoiceError, match="沒有的技能"):
        set_loadout(lib, run, (*run.hero.skills, "skill_nobody"))
    with pytest.raises(ChoiceError, match="重複"):
        set_loadout(lib, run, (run.hero.skills[0], run.hero.skills[0]))
    actives = [s for s in lib.skills.values() if s.kind == "active" and s.rule_change_id is None]
    crowded = run.model_copy(update={"bench": tuple(s.id for s in actives[:8])})
    with pytest.raises(ChoiceError):
        set_loadout(lib, crowded, (*run.hero.skills, *crowded.bench))


def test_replacing_a_skill_sends_it_to_the_bench_with_its_level() -> None:
    lib = library()
    run = _at(LevelUpNode, nth=2)
    node = run.node
    assert isinstance(node, LevelUpNode)
    victim = run.hero.skills[0]
    levelled = run.model_copy(update={"skill_levels": {victim: 3}})
    picked = None
    for index, candidate in enumerate(node.offer.candidates):
        if candidate.kind == "active" and candidate.id not in run.hero.skills:
            picked = index
            break
    assert picked is not None
    after = apply_choice(
        lib,
        levelled,
        LevelUpChoice(attributes={Attribute.STR: node.points}, pick=picked, replace=victim),
    )
    assert victim in after.bench and victim not in after.hero.skills
    assert level_of(after, victim) == 3
    assert victim not in battle_levels(after)


def test_battle_levels_flow_into_the_battle_setup_and_the_engine_state() -> None:
    lib = library()
    run = _at(CampfireNode)
    first = _actives(run)[0]
    leveled = run.model_copy(update={"node": BattleNode(index=4)})
    setup = battle_setup(lib, leveled)
    assert setup.units[0].template.skill_levels == battle_levels(leveled) != {}
    battle = ActiveBattle(lib, leveled)
    hero = battle.state.units[hero_unit_id(battle.state)]
    assert hero.skill_levels[first] == 5
    # 隊友的技能不受影響
    others = [u for u in battle.state.units.values() if u.id != hero.id]
    assert all(not u.skill_levels for u in others)


def test_replay_is_deterministic_with_levels_and_the_save_round_trips() -> None:
    lib = library()

    def final(seed: int) -> RunState:
        run, battle = auto_play(lib, new_run(lib, BUILD, seed))
        assert battle is None
        return run

    a, b = final(2), final(2)
    assert a == b and dumps_save(RunSave(run_id="a", run=a)) == dumps_save(
        RunSave(run_id="a", run=b)
    )
    assert a.skill_levels  # 這一輪確實升了級
    raw = json.loads(dumps_save(RunSave(run_id="a", run=a)))
    assert raw["format"] == "trpg-run/5"
    assert raw["run"]["skill_levels"] == a.skill_levels and "bench" in raw["run"]
    assert loads_save(json.dumps(raw)).run == a


@pytest.mark.slow
def test_a_mid_battle_save_with_levels_replays_to_the_same_state() -> None:
    lib = library()

    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        return (
            battle is not None
            and isinstance(run.node, BattleNode)
            and run.node.index >= 3
            and len(battle.steps) >= 6
        )

    run, battle = auto_play(lib, new_run(lib, BUILD, 0), stop=stop)
    assert battle is not None and battle_levels(run)
    save = loads_save(dumps_save(RunSave(run_id="m", run=run, battle=battle.to_saved())))
    restored = restore_battle(lib, save)
    assert restored is not None
    assert state_to_json(restored.state) == state_to_json(battle.state)
    finished, _ = auto_play(lib, save.run, restored)
    direct, _ = auto_play(lib, run, battle)
    assert finished == direct


def test_old_saves_are_refused_with_a_hint() -> None:
    lib = library()
    run = new_run(lib, BUILD, 0)
    raw = json.loads(dumps_save(RunSave(run_id="o", run=run)))
    for old in ("trpg-run/1", "trpg-run/2", "trpg-run/3"):
        with pytest.raises(Exception, match="開新一輪"):
            loads_save(json.dumps({**raw, "format": old}))


def test_auto_choice_includes_the_spend() -> None:
    lib = library()
    run = _at(LevelUpNode)
    choice = auto_choice(lib, run)
    assert isinstance(choice, LevelUpChoice) and choice.levels == {_actives(run)[0]: 3}
