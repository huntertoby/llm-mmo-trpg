"""區域 Boss 的保底掉落與重複挑戰（Phase 5F-3；``docs/phases/Phase5計畫.md`` 36.2、5F3-15）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.engine.battle import begin_battle
from trpg.engine.runner import apply_step
from trpg.shared.types import Team
from trpg.world.actions import FightAction
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.calendar import day_of
from trpg.world.economy_actions import LootGainedEvent
from trpg.world.loot import LootRoll, boss_bonus_units, roll_loot
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
BOSS = "sect_mist_lock_master"
CRYSTAL = "item_summit_mist_crystal"


def _summit_char(make_char: MakeChar, seed: int) -> CharacterState:
    encounter = make_encounter("cloud_summit", seed=seed, battle_map="cloud_summit", level=6)
    return make_char(
        location="cloud_summit", pending_encounter=encounter, level=10, mercenaries=PARTY
    )


def _won_summit(library: ContentLibrary, make_char: MakeChar) -> CharacterState:
    """找一個打得贏雲頂觀的種子（確定性：固定從 1 開始找）。"""
    for seed in range(1, 30):
        char = _summit_char(make_char, seed)
        prepared = prepare_battle(library, char)
        state = begin_battle(prepared.setup, prepared.seed).state
        for step in auto_steps(library, char):
            state = apply_step(state, step).state
        if state.winner is Team.ALLY:
            return char
    raise AssertionError("找不到打得贏的種子")


def test_bonus_only_once_per_day(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _summit_char(make_char, 1)
    lineup = prepare_battle(library, char).lineup
    today = day_of(library, NOON)
    assert boss_bonus_units(library, char, lineup, today) == frozenset({BOSS})
    taken = char.model_copy(update={"boss_drop_days": {BOSS: today}})
    assert boss_bonus_units(library, taken, lineup, today) == frozenset()
    assert boss_bonus_units(library, taken, lineup, today + 1) == frozenset({BOSS})


def test_bonus_forces_epic_and_boss_material(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _won_summit(library, make_char)
    prepared = prepare_battle(library, char)
    opening = begin_battle(prepared.setup, prepared.seed)
    state, events = opening.state, list(opening.events)
    for step in auto_steps(library, char):
        result = apply_step(state, step)
        state = result.state
        events += result.events

    def roll(bonus: frozenset[str]) -> LootRoll:
        return roll_loot(
            library,
            char,
            setup=prepared.setup,
            lineup=prepared.lineup,
            state=state,
            events=events,
            seed=prepared.seed,
            level=prepared.enemy_level,
            boss_bonus=bonus,
        )

    plain = roll(frozenset())
    bonus = roll(frozenset({BOSS}))
    assert CRYSTAL in bonus.materials and CRYSTAL not in plain.materials
    assert len(bonus.materials) == len(plain.materials)  # 只換掉 Boss 那一份
    assert [g.rarity for g in bonus.gear] == ["epic"]
    assert len(plain.gear) == 1


def test_fight_records_the_bonus_day(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _won_summit(library, make_char)
    steps = auto_steps(library, char)
    done = world_step(library, make_world(), char, FightAction(steps=steps), NOON + 60)
    assert done.char.boss_drop_days == {BOSS: day_of(library, NOON + 60)}
    gained = [e for e in done.events if isinstance(e, LootGainedEvent)]
    assert gained and CRYSTAL in gained[0].materials
