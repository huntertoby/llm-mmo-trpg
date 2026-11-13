"""RG-2（#162，09 9.6.6）：精英單挑——提出、接受／拒絕、一對一組場、獎勵相同、世界重播。

戰鬥由效用 AI 代打（:func:`auto_steps`）；北坡狼王種子 0、1 一對一與全隊都打得贏（固定種子）。
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_encounter, make_world
from trpg.api.world_party_view import duel_line
from trpg.content.library import ContentLibrary
from trpg.engine.battle import begin_battle
from trpg.shared.types import Team
from trpg.world.actions import BattleEndedEvent, DuelChoiceAction, DuelChosenEvent, FightAction
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.common import world_map_of
from trpg.world.duel import offer_duel
from trpg.world.encounters import roll_lineup
from trpg.world.errors import WorldActionError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_world, loads_char
from trpg.world.solutions import make_encounter as world_encounter
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import StepResult, new_character, world_step

MakeChar = Callable[..., CharacterState]
WON_SEEDS = (0, 1)  # 北坡狼王：一對一與全隊都打贏的種子


def _encounter(region: str, location: str, *, bounty: str | None = None) -> EncounterResult:
    return EncounterResult(
        region=region,
        location=location,
        level=5,
        battle_map=None,
        battle_seed=7,
        weather="clear",
        day_phase="day",
        at=NOON,
        bounty=bounty,
    )


def _wolf_king(library: ContentLibrary, seed: int, duel: str | None) -> CharacterState:
    """主角＋兩名傭兵在北坡遇到狼王（固定精英，狂暴的霧狼）。"""
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    encounter = make_encounter("north_slope", seed=seed, from_location="hunter_hut")
    encounter = encounter.model_copy(update={"duel": duel})
    return char.model_copy(
        update={"location": "north_slope", "mercenaries": PARTY, "pending_encounter": encounter}
    )


def _fight(library: ContentLibrary, char: CharacterState) -> StepResult:
    return world_step(
        library, make_world(), char, FightAction(steps=auto_steps(library, char)), NOON
    )


# ---------------------------------------------------------------------------
# 提出
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        ("cloud_ridge", "north_slope", None, (), True),  # 北坡狼王（固定精英）
        ("cloud_ridge", "north_slope", "north_wolf_king", (), True),  # 北坡狼王（懸賞）
        ("cloud_ridge", "cliff_gang_fort", "scarface", (), True),  # 疤面（懸賞）
        ("cloud_ridge", "cliff_gang_fort", None, ("scarface_rises",), True),  # 疤面（遭遇變化）
        ("cloud_ridge", "cliff_gang_fort", None, (), False),  # 斷崖幫寨平常沒有精英
        ("cloud_ridge", "sword_tomb", "mist_swordsman", (), False),  # 霧中劍客（會分身）不提
        ("cloud_ridge", "ferry_steps", None, (), False),
        ("ashen_waste", "overseer_camp", None, (), True),  # 鍛疤（固定精英）
        ("ashen_waste", "overseer_camp", "furnace_overseer", (), True),  # 鍛疤（懸賞）
        ("ashen_waste", "lava_cave", "molten_lord", (), True),  # 熔核領主（懸賞）
        ("ashen_waste", "lava_cave", None, (), False),  # 平常的熔核領主陣容不提
        ("ashen_waste", "obsidian_valley", "frost_ember_king", (), False),  # 寒燼蜥王（會再生）
    ],
)
def test_who_offers_a_duel(
    library: ContentLibrary, case: tuple[str, str, str | None, tuple[str, ...], bool]
) -> None:
    region, location, bounty, flags, offered = case
    result = offer_duel(library, _encounter(region, location, bounty=bounty), flags)
    assert (result.duel == "offered") is offered
    assert roll_lineup(library, result, flags).duel is offered


def test_making_an_encounter_offers_the_duel(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char().model_copy(update={"location": "north_slope"})
    target = world_map_of(library, "cloud_ridge").location_by_id()["north_slope"]
    result, _ = world_encounter(library, make_world(), char, target, NOON)
    assert result.duel == "offered"
    ferry = world_map_of(library, "cloud_ridge").location_by_id()["ferry_steps"]
    plain, _ = world_encounter(library, make_world(), char, ferry, NOON)
    assert plain.duel is None
    assert "duel" not in plain.model_dump()  # 沒有單挑時不輸出


# ---------------------------------------------------------------------------
# 回應
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("accept", [True, False])
def test_duel_choice_records_the_answer(library: ContentLibrary, accept: bool) -> None:
    char = _wolf_king(library, 0, "offered")
    result = world_step(library, make_world(), char, DuelChoiceAction(accept=accept), NOON)
    assert result.char.pending_encounter is not None
    assert result.char.pending_encounter.duel == ("accepted" if accept else "declined")
    (event,) = (e for e in result.events if isinstance(e, DuelChosenEvent))
    assert (event.location, event.accepted) == ("north_slope", accept)
    with pytest.raises(WorldActionError, match="已經回應過"):
        world_step(library, make_world(), result.char, DuelChoiceAction(accept=True), NOON)


def test_duel_choice_needs_an_offer(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="沒有遭遇"):
        world_step(library, make_world(), make_char(), DuelChoiceAction(accept=True), NOON)
    plain = _wolf_king(library, 0, None)
    with pytest.raises(WorldActionError, match="沒有人提出單挑"):
        world_step(library, make_world(), plain, DuelChoiceAction(accept=True), NOON)


# ---------------------------------------------------------------------------
# 組場
# ---------------------------------------------------------------------------


def test_accepted_duel_fields_only_the_hero_and_the_elite(library: ContentLibrary) -> None:
    prepared = prepare_battle(library, _wolf_king(library, 0, "accepted"))
    assert prepared.duel
    teams = [(u.team, u.template.id) for u in prepared.setup.units]
    assert [t for t, _ in teams] == [Team.ALLY, Team.ENEMY]
    assert teams[1][1] == "mist_wolf_berserk"  # 精英本人（狂暴的霧狼）
    assert len(prepared.lineup.members) == 3  # 獎勵照整個陣容
    assert prepared.fielded.members == prepared.lineup.members[:1]
    # 雙方都獨狼（開戰那一刻自己的陣營只有自己）
    state = begin_battle(prepared.setup, prepared.seed).state
    assert all(u.lone_wolf for u in state.units.values())


@pytest.mark.parametrize("duel", ["declined", "offered", None])
def test_declined_or_unanswered_duel_is_the_original_lineup(
    library: ContentLibrary, duel: str | None
) -> None:
    """拒絕、沒選就開打、沒提出：三者開出一模一樣的戰鬥（全隊＋整個陣容）。"""
    base = prepare_battle(library, _wolf_king(library, 0, None))
    prepared = prepare_battle(library, _wolf_king(library, 0, duel))
    assert not prepared.duel
    assert prepared.setup.model_dump() == base.setup.model_dump()
    assert len(prepared.setup.units) == 1 + len(PARTY) + len(base.lineup.members)


def test_encounter_view_shows_the_duel(library: ContentLibrary) -> None:
    from trpg.api.world_presenter import _encounter_view  # noqa: PLC0415

    offered = _encounter_view(library, _wolf_king(library, 0, "offered"), in_battle=False)
    assert offered is not None and offered.duel == "offered"
    assert len(offered.enemies) == 3 and offered.duel_zh is not None
    assert "要求一對一" in offered.duel_zh and "獎勵一樣" in offered.duel_zh
    accepted = _encounter_view(library, _wolf_king(library, 0, "accepted"), in_battle=False)
    assert accepted is not None and accepted.duel == "accepted"
    assert [e.elite for e in accepted.enemies] == [True]
    assert "一對一" in accepted.allies_zh
    plain = _encounter_view(library, _wolf_king(library, 0, None), in_battle=False)
    assert plain is not None and plain.duel is None and plain.duel_zh is None
    assert duel_line(None, "x") is None


# ---------------------------------------------------------------------------
# 獎勵
# ---------------------------------------------------------------------------

_MAY_DIFFER = {"hp", "mana", "stamina", "skill_usage", "last_battle"}
"""一對一與全隊打的差別只在戰況本身（剩多少血、打幾輪、用了哪些招），不在獎勵。"""


@pytest.mark.parametrize("seed", WON_SEEDS)
def test_rewards_are_identical_field_by_field(library: ContentLibrary, seed: int) -> None:
    accepted = _fight(library, _wolf_king(library, seed, "accepted"))
    declined = _fight(library, _wolf_king(library, seed, "declined"))
    ends = [
        next(e for e in r.events if isinstance(e, BattleEndedEvent)) for r in (accepted, declined)
    ]
    assert all(e.won for e in ends)
    assert ends[0].xp_gained == ends[1].xp_gained > 0
    a, b = accepted.char.model_dump(mode="json"), declined.char.model_dump(mode="json")
    differ = {k for k in a if a[k] != b[k]}
    assert differ <= _MAY_DIFFER, differ - _MAY_DIFFER
    # 經驗、等級、靈感、精英首殺、金錢、背包逐欄相同；掉落的材料與裝備也相同
    for key in ("xp", "level", "insight", "elite_kills", "gold", "quest_coins", "bag", "gear"):
        assert a[key] == b[key], key
    loot_a, loot_b = a["last_battle"]["loot"], b["last_battle"]["loot"]
    assert loot_a == loot_b and loot_a["materials"] and loot_a["gear"]
    assert a["last_battle"]["xp_gained"] == b["last_battle"]["xp_gained"]
    # 世界事件除了「打了幾輪、剩多少血、用了哪些招」以外相同（含戰前事件的陣容）
    strip = {"rounds", "hp", "mana", "skills_used"}

    def norm(result: StepResult) -> list[object]:
        return [
            {k: v for k, v in e.model_dump(mode="json").items() if k not in strip}
            for e in result.events
        ]

    assert norm(accepted) == norm(declined)


# ---------------------------------------------------------------------------
# 世界重播
# ---------------------------------------------------------------------------


def test_world_replay_of_a_duel_matches_live_play(library: ContentLibrary) -> None:
    world = make_world()
    start = {"alice": _wolf_king(library, 0, "offered")}
    char = start["alice"]
    entries: list[WorldLogEntry] = []
    live = world
    for seq, action in enumerate([DuelChoiceAction(accept=True)], start=1):
        result = world_step(library, live, char, action, NOON)
        char, live = result.char, result.world
        entries.append(WorldLogEntry(seq=seq, now=NOON, character_id="alice", action=action))
    fight = FightAction(steps=auto_steps(library, char))
    result = world_step(library, live, char, fight, NOON)
    char, live = result.char, result.world
    entries.append(WorldLogEntry(seq=2, now=NOON, character_id="alice", action=fight))
    replayed = replay(library, world, start, entries)
    assert dumps_world(replayed.world) == dumps_world(live)
    assert dumps_char(replayed.characters["alice"]) == dumps_char(char)
    assert char.pending_encounter is None and char.last_battle is not None
    assert char.last_battle.won


def test_saved_character_keeps_the_duel_state(library: ContentLibrary) -> None:
    char = _wolf_king(library, 0, "offered")
    text = dumps_char(char)
    assert json.loads(text)["format"] == "trpg-char/15"
    assert json.loads(text)["pending_encounter"]["duel"] == "offered"
    assert loads_char(text) == char
