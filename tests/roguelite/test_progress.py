"""一輪的推進：HP、法力、源力跨戰鬥、營火、Boss 前保底、升級、重骰（Phase 3-5a）。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import VICTORY, full_run, library
from trpg.engine import battle_result, begin_battle
from trpg.engine.state import BattleState, state_from_json, state_to_json
from trpg.roguelite import (
    ActiveBattle,
    ChoiceError,
    NodeConflictError,
    RunState,
    apply_choice,
    battle_setup,
    finish_battle,
    new_run,
    next_node,
)
from trpg.roguelite.progress import hero_unit_id
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    EndedNode,
    LeaveChoice,
    LevelUpChoice,
    LevelUpNode,
    PickChoice,
    RerollChoice,
)
from trpg.shared.types import Attribute, Team


def _first_battle(build: str = "build_fire", seed: int = 0) -> tuple[RunState, ActiveBattle]:
    run = new_run(library(), build, seed)
    battle = ActiveBattle(library(), run)
    battle.auto()
    return run, battle


def test_battle_setup_puts_the_hero_first_with_run_resources() -> None:
    lib = library()
    run = new_run(lib, "build_push", 4).model_copy(update={"hp": 17, "mana": 3, "source": 0})
    setup = battle_setup(lib, run)
    hero = setup.units[0]
    assert (hero.template, hero.team, hero.hp, hero.mana) == (run.hero, Team.ALLY, 17, 3)
    assert [u.template.id for u in setup.units[1:3]] == list(lib.roguelite.companions)
    assert [u.template.id for u in setup.units[3:]] == list(run.plan[0].enemies)
    assert setup.map.id == run.plan[0].map_id
    assert setup.max_rounds == lib.roguelite.max_rounds
    state = begin_battle(setup, run.plan[0].seed).state
    unit = state.units[hero_unit_id(state)]
    assert (unit.hp, unit.mana) == (17, 3)
    assert unit.source == 1  # 開場至少 1（存檔值 0）
    companions = [u for u in state.units_sorted() if u.team is Team.ALLY][1:]
    assert all(u.hp == u.max_hp for u in companions)  # 隊友滿狀態


def test_source_at_start_keeps_the_saved_value_up_to_the_cap() -> None:
    lib = library()
    run = new_run(lib, "build_push", 4).model_copy(update={"source": 3})
    state = begin_battle(battle_setup(lib, run), 0).state
    assert state.units[hero_unit_id(state)].source == 3


def test_won_battle_writes_back_hp_mana_and_source_plus_reward() -> None:
    lib = library()
    run, battle = _first_battle()
    result = battle_result(battle.state)
    assert result.winner is Team.ALLY
    hero = result.ally(battle.hero_id)
    assert hero is not None
    after = finish_battle(lib, run, battle.state, len(battle.steps))
    # 贏了之後升到 2 級：目前 HP 同步增加等級帶來的最大 HP（Phase 3-7）
    level_gain = lib.ruleset.core.level_hp_bonus(run.hero.max_hp, after.level)
    assert after.level == 2 and level_gain > 0
    assert after.hp == max(hero.hp, 1) + level_gain
    assert after.mana == hero.mana
    assert after.source == min(3, hero.source + lib.roguelite.source.after_battle)
    assert after.xp == lib.roguelite.xp_per_battle
    assert after.battles_done == 1
    record = after.history[-1]
    assert (record.index, record.won, record.steps) == (1, True, len(battle.steps))
    assert record.map_id == run.plan[0].map_id
    # 下一場以寫回的值開戰（戰鬥之間不回復）
    node = after.node
    assert isinstance(node, LevelUpNode)  # 第 1 場後升到 2 級
    skipped = apply_choice(lib, after, LevelUpChoice(attributes={Attribute.STR: 2}))
    assert skipped.node == BattleNode(index=2)
    setup = battle_setup(lib, skipped)
    assert (setup.units[0].hp, setup.units[0].mana) == (after.hp, after.mana)
    assert setup.units[0].source == after.source


def _edited(state: BattleState, **fields: object) -> BattleState:
    copy = state_from_json(state_to_json(state))
    hero = copy.units[hero_unit_id(copy)]
    for key, value in fields.items():
        setattr(hero, key, value)
    return copy


def test_hero_downed_in_a_won_battle_continues_with_one_hp() -> None:
    run, battle = _first_battle()
    downed = _edited(battle.state, hp=0, downed=True)
    after = finish_battle(library(), run, downed, len(battle.steps))
    level_gain = library().ruleset.core.level_hp_bonus(run.hero.max_hp, after.level)
    assert after.hp == 1 + level_gain  # 以 1 HP 繼續，再加上升級的最大 HP 增量
    assert after.history[-1].hero_downed
    assert not after.ended


def test_a_lost_battle_ends_the_run() -> None:
    run, battle = _first_battle()
    lost = _edited(battle.state, hp=0, downed=True)
    lost.winner = Team.ENEMY
    after = finish_battle(library(), run, lost, len(battle.steps))
    assert after.node == EndedNode(victory=False)
    assert after.hp == 0
    assert not after.history[-1].won


def test_source_reward_is_capped() -> None:
    run, battle = _first_battle()
    full = _edited(battle.state, source=3)
    assert finish_battle(library(), run, full, 1).source == 3


def test_finish_requires_an_ended_battle_and_a_battle_node() -> None:
    lib = library()
    run = new_run(lib, "build_fire", 0)
    battle = ActiveBattle(lib, run)
    with pytest.raises(NodeConflictError, match="還沒結束"):
        finish_battle(lib, run, battle.state, 0)
    with pytest.raises(NodeConflictError, match="不是戰鬥"):
        finish_battle(
            lib, run.model_copy(update={"node": EndedNode(victory=True)}), battle.state, 0
        )


def _after(run: RunState, done: int, **update: object) -> RunState:
    return next_node(library(), run.model_copy(update={"battles_done": done, **update}))


def test_campfire_mid_run_restores_hp_and_mana_and_adds_source() -> None:
    run = new_run(library(), "build_push", 2)
    camp = _after(run, 3, hp=5, mana=0, source=1)
    assert camp.node == CampfireNode(after_battle=3, rerolls_left=1)
    assert (camp.hp, camp.mana, camp.source) == (
        run.max_hp_in(library().ruleset.core),
        run.max_mana,
        2,
    )
    capped = _after(run, 3, source=3)
    assert capped.source == 3
    left = apply_choice(library(), camp, LeaveChoice())
    assert left.node == BattleNode(index=4)
    assert left.campfires_done == (3,)


def test_no_campfire_outside_the_configured_points() -> None:
    run = new_run(library(), "build_push", 2)
    for done in (1, 2, 4):
        assert _after(run, done, hp=5).node == BattleNode(index=done + 1)


def test_boss_floor_applies_before_the_boss_battle() -> None:
    run = new_run(library(), "build_push", 2)
    boss = _after(run, 5, source=0, campfires_done=(3, 5))
    assert boss.node == BattleNode(index=6)
    assert boss.plan_of(6).boss
    assert boss.source == library().roguelite.source.boss_floor
    assert _after(run, 5, source=3, campfires_done=(3, 5)).source == 3
    assert _after(run, 6, campfires_done=(3, 5)).node == EndedNode(victory=True)


def test_campfire_reroll_once_then_pick_or_leave() -> None:
    lib = library()
    camp = _after(new_run(lib, "build_push", 2), 3)
    rerolled = apply_choice(lib, camp, RerollChoice())
    node = rerolled.node
    assert isinstance(node, CampfireNode) and node.offer is not None
    assert node.offer.reason == "reroll"
    assert len(node.offer.candidates) == 3
    assert rerolled.offers_made == camp.offers_made + 1
    with pytest.raises(NodeConflictError, match="已經重骰過"):
        apply_choice(lib, rerolled, RerollChoice())
    skipped = apply_choice(lib, rerolled, PickChoice(pick=None))
    assert skipped.node == BattleNode(index=4)
    assert skipped.hero.skills == camp.hero.skills
    no_more = camp.model_copy(update={"node": CampfireNode(after_battle=3, rerolls_left=0)})
    with pytest.raises(NodeConflictError, match="沒有重骰次數"):
        apply_choice(lib, no_more, RerollChoice())
    with pytest.raises(NodeConflictError, match="還沒有重骰"):
        apply_choice(lib, camp, PickChoice(pick=0))


def test_level_up_gives_two_points_and_a_skippable_offer() -> None:
    lib = library()
    run = _after(new_run(lib, "build_push", 2), 1, levels_pending=1)
    node = run.node
    assert isinstance(node, LevelUpNode)
    assert (node.level, node.points, run.level) == (2, 2, 2)
    with pytest.raises(ChoiceError, match="必須分配 2 點"):
        apply_choice(lib, run, LevelUpChoice(attributes={Attribute.STR: 1}))
    with pytest.raises(NodeConflictError, match="升級"):
        apply_choice(lib, run, RerollChoice())
    after = apply_choice(lib, run, LevelUpChoice(attributes={Attribute.WIL: 2}))
    assert after.hero.attributes[Attribute.WIL] == run.hero.attributes[Attribute.WIL] + 2
    assert after.hero.skills == run.hero.skills
    assert after.node == BattleNode(index=2)


def test_two_levels_at_once_give_two_level_up_nodes() -> None:
    lib = library()
    run = _after(new_run(lib, "build_push", 2), 1, levels_pending=2)
    first = apply_choice(lib, run, LevelUpChoice(attributes={Attribute.STR: 2}))
    assert isinstance(first.node, LevelUpNode) and first.node.level == 3
    assert first.node.offer != run.node.offer  # type: ignore[union-attr]


def test_choices_are_rejected_in_battle_and_after_the_end() -> None:
    lib = library()
    run = new_run(lib, "build_push", 2)
    with pytest.raises(NodeConflictError, match="戰鬥"):
        apply_choice(lib, run, LeaveChoice())
    with pytest.raises(NodeConflictError, match="一輪已結束"):
        apply_choice(lib, run.model_copy(update={"node": EndedNode(victory=True)}), LeaveChoice())


def test_a_full_victorious_run_visits_both_campfires_and_rerolls_twice() -> None:
    run = full_run(*VICTORY)
    assert run.node == EndedNode(victory=True)
    assert run.campfires_done == (3, 5)
    assert len(run.history) == len(run.plan) == 6
    assert run.history[-1].boss and all(r.won for r in run.history)
    levels = run.level - 1
    assert run.offers_made == levels + 2  # 每次升級一組 ＋ 兩次重骰
    assert 0 <= run.source <= 3
