"""下一場戰鬥修正、增援與先手（Phase 5A-6；``docs/phases/Phase5計畫.md`` 11.4）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.engine.battle import begin_battle
from trpg.shared.types import Team
from trpg.world.actions import BattleStartedEvent, FightAction, RetreatAction
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.encounters import roll_lineup
from trpg.world.state import CharacterState, NextBattleMod, ThreadState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
DOOR = "gang_fort_secret_door"
FULL = ("scarface_rises",)
"""斷崖幫寨滿 4 名的陣容：線頭到期變化「二當家坐大」（OB-7 起一般陣容 2～3 名）。"""


def _mods(*kinds: str) -> tuple[NextBattleMod, ...]:
    out: list[NextBattleMod] = []
    for kind in kinds:
        if kind == "reinforce":
            out.append(NextBattleMod(kind="reinforce", source="deserter_hide"))
        else:
            polarity, status = kind.split(":")
            out.append(NextBattleMod(kind=polarity, status=status, source="deserter_hide"))  # type: ignore[arg-type]
    return tuple(out)


def _at(make_char: MakeChar, location: str, *, seed: int = 0, **updates: object) -> CharacterState:
    battle_map = "narrow_halls" if location == "cliff_gang_fort" else "cliff_outpost"
    encounter = make_encounter(location, seed=seed, battle_map=battle_map, level=3)
    updates.setdefault("pending_encounter", encounter)
    return make_char(location=location, **updates)


def _door(expires_at: int = NOON + 1000) -> ThreadState:
    return ThreadState(
        thread=DOOR,
        skeleton="bandit_deserter",
        region="cloud_ridge",
        created_at=NOON - 100,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# buff／debuff
# ---------------------------------------------------------------------------


def test_buffs_and_debuffs_on_hero_at_start(library: ContentLibrary, make_char: MakeChar) -> None:
    mods = _mods("buff:guarded", "debuff:weaken", "debuff:weaken")
    char = _at(make_char, "ferry_steps", next_battle=mods)
    prepared = prepare_battle(library, char)
    assert prepared.hero_statuses == ("guarded", "weaken")
    state = begin_battle(prepared.setup, prepared.seed).state
    hero = next(u for u in state.units_sorted() if u.team is Team.ALLY)
    assert hero.has_status("guarded") and hero.has_status("weaken")


def test_mods_consumed_by_fight_not_by_retreat(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _at(
        make_char,
        "ferry_steps",
        next_battle=_mods("debuff:weaken"),
        pending_encounter=make_encounter(
            "ferry_steps", battle_map="cliff_outpost", from_location="mist_ferry"
        ),
    )
    retreated = world_step(library, make_world(), char, RetreatAction(), NOON).char
    assert retreated.next_battle == char.next_battle
    result = world_step(
        library, make_world(), char, FightAction(steps=auto_steps(library, char)), NOON
    )
    assert result.char.next_battle == ()
    started = next(e for e in result.events if isinstance(e, BattleStartedEvent))
    assert started.hero_statuses == ("weaken",)


# ---------------------------------------------------------------------------
# 增援
# ---------------------------------------------------------------------------


def _small_seed(library: ContentLibrary, make_char: MakeChar, location: str) -> int:
    for seed in range(32):
        encounter = _at(make_char, location, seed=seed).pending_encounter
        assert encounter is not None
        if len(roll_lineup(library, encounter).members) <= 3:
            return seed
    raise AssertionError("找不到 3 名以下的陣容")


def test_reinforcement_adds_one_non_elite(library: ContentLibrary, make_char: MakeChar) -> None:
    seed = _small_seed(library, make_char, "ferry_steps")
    plain = prepare_battle(library, _at(make_char, "ferry_steps", seed=seed))
    char = _at(make_char, "ferry_steps", seed=seed, next_battle=_mods("reinforce"))
    prepared = prepare_battle(library, char)
    assert prepared.reinforcements == 1
    assert prepared.lineup.members[:-1] == plain.lineup.members
    added = prepared.lineup.members[-1]
    assert added.affix is None
    table = library.world_encounters["cloud_ridge"]
    entry = table.location_by_id()["ferry_steps"]
    pool = {u for g in entry.groups for u in table.group_by_id()[g.group].units}
    assert added.unit in pool
    catalog = library.enemy_catalog()
    assert not catalog.is_elite(catalog.template(added.unit))
    enemies = [u for u in prepared.setup.units if u.team is Team.ENEMY]
    assert len(enemies) == len(plain.lineup.members) + 1
    assert all(u.template.level == prepared.enemy_level for u in enemies)
    assert prepared.first_team is None
    assert prepare_battle(library, char) == prepared  # 確定性


def test_full_lineup_turns_into_enemy_first(library: ContentLibrary, make_char: MakeChar) -> None:
    # OB-7（#155）：斷崖幫寨的一般陣容改成 2～3 名；滿 4 名的陣容改用「二當家坐大」的遭遇變化（3＋精英）
    char = _at(make_char, "cliff_gang_fort", next_battle=_mods("reinforce"), story_flags=FULL)
    prepared = prepare_battle(library, char)
    assert len(prepared.lineup.members) == 4
    assert prepared.reinforcements == 0
    assert prepared.first_team is Team.ENEMY
    state = begin_battle(prepared.setup, prepared.seed).state
    assert state.units[state.turn_order[0]].team is Team.ENEMY


def test_many_reinforcements_fill_then_enemy_first(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    seed = _small_seed(library, make_char, "ferry_steps")
    char = _at(make_char, "ferry_steps", seed=seed, next_battle=_mods(*["reinforce"] * 3))
    prepared = prepare_battle(library, char)
    assert len(prepared.lineup.members) == 4
    assert prepared.first_team is Team.ENEMY


# ---------------------------------------------------------------------------
# 斷崖幫寨的暗門
# ---------------------------------------------------------------------------


def test_secret_door_gives_ally_first_at_fort(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _at(make_char, "cliff_gang_fort", threads=(_door(),))
    prepared = prepare_battle(library, char)
    assert prepared.first_team is Team.ALLY
    state = begin_battle(prepared.setup, prepared.seed).state
    allies = sum(1 for u in state.units.values() if u.team is Team.ALLY)
    assert all(state.units[u].team is Team.ALLY for u in state.turn_order[:allies])


def test_secret_door_only_at_fort_and_while_valid(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    elsewhere = _at(make_char, "ferry_steps", threads=(_door(),))
    assert prepare_battle(library, elsewhere).first_team is None
    expired = _at(make_char, "cliff_gang_fort", threads=(_door(expires_at=NOON),))
    assert prepare_battle(library, expired).first_team is None
    plain = _at(make_char, "cliff_gang_fort")
    assert prepare_battle(library, plain).first_team is None


def test_door_and_full_reinforcement_cancel(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _at(
        make_char,
        "cliff_gang_fort",
        threads=(_door(),),
        next_battle=_mods("reinforce"),
        story_flags=FULL,  # OB-7：滿 4 名的陣容（見上）
    )
    assert len(prepare_battle(library, char).lineup.members) == 4
    assert prepare_battle(library, char).first_team is None
