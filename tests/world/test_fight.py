"""戰鬥與勝負回寫（Phase 5A-4；``docs/phases/Phase5計畫.md`` 9.4）。

戰鬥由效用 AI 代打（:func:`auto_steps`），步驟放進 ``fight`` 動作；同樣的步驟永遠得到同樣的結果，
所以「找一個會贏／會輸的種子」是確定性的。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_encounter, make_world, with_rules
from trpg.content.library import ContentLibrary
from trpg.engine.battle import begin_battle
from trpg.engine.results import battle_result
from trpg.engine.runner import apply_step
from trpg.world.actions import (
    BattleEndedEvent,
    CampAction,
    FightAction,
    TravelAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import StepResult, max_hp, max_mana, new_character, world_step

MakeChar = Callable[..., CharacterState]


def _fight(library: ContentLibrary, char: CharacterState, now: int = NOON) -> StepResult:
    return world_step(
        library, make_world(), char, FightAction(steps=auto_steps(library, char)), now
    )


def _ended(result: StepResult) -> BattleEndedEvent:
    return next(e for e in result.events if isinstance(e, BattleEndedEvent))


def _find(
    library: ContentLibrary,
    char: CharacterState,
    make: Callable[[int], EncounterResult],
    *,
    won: bool,
) -> tuple[CharacterState, StepResult]:
    for seed in range(16):
        start = char.model_copy(update={"pending_encounter": make(seed)})
        result = _fight(library, start)
        if _ended(result).won is won:
            return start, result
    raise AssertionError(f"16 個種子都找不到 won={won} 的戰鬥")


@pytest.fixture(scope="module")
def win(library: ContentLibrary) -> tuple[CharacterState, StepResult]:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"location": "ferry_steps", "mercenaries": PARTY})
    return _find(
        library,
        char,
        lambda s: make_encounter(
            "ferry_steps", seed=s, battle_map="cliff_outpost", from_location="mist_ferry"
        ),
        won=True,
    )


@pytest.fixture(scope="module")
def loss(library: ContentLibrary) -> tuple[CharacterState, StepResult]:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"location": "elixir_cave", "hp": 1, "camped_at": None})
    return _find(
        library,
        char,
        lambda s: make_encounter(
            "elixir_cave", seed=s, level=5, battle_map="narrow_halls", from_location="herb_valley"
        ),
        won=False,
    )


def test_win_writes_back(library: ContentLibrary, win: tuple[CharacterState, StepResult]) -> None:
    start, result = win
    char = result.char
    ended = _ended(result)
    kinds = [e.kind for e in result.events]
    assert kinds[:2] == ["battle_started", "battle_ended"]
    assert library.world_rules is not None
    share = library.world_rules.xp.share_xp(1)  # 渡口石階 1 級地點：1 份（一般戰鬥）
    assert ended.xp_gained == share
    assert char.xp == start.xp + share
    assert char.level == 1  # 世界門檻 950，打一場不會升級
    assert char.pending_encounter is None
    assert char.stamina is None  # 耐力戰後回滿（#113）
    assert char.mana == ended.mana  # 法力不回
    assert char.hp == ended.hp
    assert char.hp >= 1
    assert char.location == "ferry_steps"
    assert not char.fatigued


def test_win_does_not_heal(library: ContentLibrary, make_char: MakeChar) -> None:
    """HP 不自動回：打贏後的 HP ＝ 引擎戰鬥結束時主角的 HP ＋ 升級多出的最大 HP（不回滿）。"""
    char = make_char(location="ferry_steps", hp=20, mercenaries=PARTY)
    for seed in range(8):
        start = char.model_copy(
            update={
                "pending_encounter": make_encounter(
                    "ferry_steps", seed=seed, battle_map="cliff_outpost"
                )
            }
        )
        steps = auto_steps(library, start)
        result = world_step(library, make_world(), start, FightAction(steps=steps), NOON)
        if _ended(result).won:
            prepared = prepare_battle(library, start)
            state = begin_battle(prepared.setup, prepared.seed).state
            for step in steps:
                state = apply_step(state, step).state
            hero_hp = battle_result(state).allies[0].hp
            grown = max_hp(library, result.char) - max_hp(library, start)
            assert result.char.hp == max(1, hero_hp) + grown
            return
    pytest.fail("找不到打贏的種子")


def test_win_clears_camp(win: tuple[CharacterState, StepResult]) -> None:
    _, result = win
    cleared = result.world.cleared
    assert [(c.location, c.respawn_at) for c in cleared] == [("ferry_steps", NOON + 1800)]
    assert any(e.kind == "location_cleared" for e in result.events)


def test_cleared_camp_allows_camping_and_blocks_encounters(
    library: ContentLibrary, win: tuple[CharacterState, StepResult]
) -> None:
    _, result = win
    world, char = result.world, result.char
    camped = world_step(library, world, char, CampAction(), NOON + 5)
    assert camped.char.camped_at is not None
    ambush = with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})
    home = char.model_copy(update={"location": "mist_ferry"})
    calm = world_step(ambush, world, home, TravelAction(to="ferry_steps"), NOON + 10)
    check = next(e for e in calm.events if e.kind == "encounter_check")
    assert check.chance_permille == 0
    assert calm.char.pending_encounter is None
    later = world_step(ambush, world, home, TravelAction(to="ferry_steps"), NOON + 1800)
    assert later.char.pending_encounter is not None  # 重生了


def test_non_clear_kinds(library: ContentLibrary, win: tuple[CharacterState, StepResult]) -> None:
    start, _ = win
    keep = with_rules(library, battle={"clear_kinds": []})
    result = _fight(keep, start)
    assert result.world.cleared == ()
    assert all(e.kind != "location_cleared" for e in result.events)


def test_loss_returns_to_town_fatigued(
    library: ContentLibrary, loss: tuple[CharacterState, StepResult]
) -> None:
    start, result = loss
    char = result.char
    kinds = [e.kind for e in result.events]
    assert kinds == ["battle_started", "battle_ended", "defeated"]
    assert _ended(result).xp_gained == 0
    assert char.location == "mist_ferry"
    assert char.hp == max_hp(library, char)
    assert char.mana == max_mana(library, char)  # 6F-1：回鎮法力也回滿
    assert _ended(result).mana == char.mana
    assert char.xp == start.xp  # 不扣經驗
    assert char.level == start.level
    assert char.fatigued
    assert char.stamina is None
    assert char.pending_encounter is None
    assert result.world.cleared == ()


def test_fatigue_lasts_one_battle(
    library: ContentLibrary, loss: tuple[CharacterState, StepResult]
) -> None:
    _, result = loss
    tired = result.char.model_copy(
        update={
            "location": "ferry_steps",
            "pending_encounter": make_encounter("ferry_steps", battle_map="cliff_outpost"),
        }
    )
    prepared = prepare_battle(library, tired)
    assert prepared.hero_hp == max_hp(library, tired) * 800 // 1000
    after = _fight(library, tired)
    started = next(e for e in after.events if e.kind == "battle_started")
    assert started.fatigued
    if _ended(after).won:
        assert not after.char.fatigued


def test_fight_errors(library: ContentLibrary, win: tuple[CharacterState, StepResult]) -> None:
    start, _ = win
    world = make_world()
    steps = auto_steps(library, start)
    with pytest.raises(WorldActionError, match="沒有遭遇"):
        world_step(
            library,
            world,
            start.model_copy(update={"pending_encounter": None}),
            FightAction(steps=steps),
            NOON,
        )
    with pytest.raises(WorldActionError, match="還沒結束"):
        world_step(library, world, start, FightAction(steps=steps[:3]), NOON)
    with pytest.raises(WorldActionError):
        world_step(library, world, start, FightAction(steps=(*steps, steps[-1])), NOON)


def test_fight_is_deterministic(
    library: ContentLibrary, win: tuple[CharacterState, StepResult]
) -> None:
    start, result = win
    again = _fight(library, start)
    assert again.char.model_dump_json() == result.char.model_dump_json()
    assert again.world == result.world
    assert again.events == result.events


def test_every_encounter_location_battle_runs(library: ContentLibrary, make_char: MakeChar) -> None:
    """smoke：雲嶺每個有遭遇表的地點，照地點等級成長的敵人都能打完一場（重配技能進得了引擎）。"""
    world_map = library.world_maps["cloud_ridge"]
    table = library.world_encounters["cloud_ridge"]
    for entry in table.locations:
        location = world_map.location_by_id()[entry.location]
        assert location.level_max is not None
        maps = location.battle_maps
        encounter = make_encounter(
            entry.location,
            seed=5,
            level=location.level_max,
            battle_map=maps[0] if maps else None,
        )
        char = make_char(location=entry.location, pending_encounter=encounter)
        result = _fight(library, char)
        assert _ended(result).rounds >= 1
        assert result.char.pending_encounter is None
