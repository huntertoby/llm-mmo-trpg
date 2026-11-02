"""朋友的影子（Phase 5C-2；``docs/phases/Phase5計畫.md`` 23）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.content.skills import skill_slot_problems
from trpg.shared.types import Attribute, Team
from trpg.world.actions import (
    BattleStartedEvent,
    CampAction,
    FightAction,
    HireAction,
    RestAction,
    ShadowAiAction,
    ShadowLentEvent,
    ShadowSavedEvent,
    TravelAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.party import SEASON_BOSS_PROBLEM, season_boss_problem, slot_capped
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_world
from trpg.world.shadows import (
    capped_attributes,
    save_after_prep,
    shadow_snapshot,
    shadow_spawn,
)
from trpg.world.state import CharacterState, ShadowSnapshot, WorldState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]

DAY = 24 * 3600


def _step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: object,
    now: int = NOON,
) -> StepResult:
    return world_step(library, world, char, action, now)  # type: ignore[arg-type]


def _with_alice_shadow(library: ContentLibrary, make_char: MakeChar) -> WorldState:
    return _step(library, make_world(), make_char("alice"), RestAction()).world


# ---------------------------------------------------------------------------
# 自動存影子（#102）
# ---------------------------------------------------------------------------


def test_town_prep_saves_shadow(library: ContentLibrary, make_char: MakeChar) -> None:
    alice = make_char("alice")
    result = _step(library, make_world(), alice, RestAction())
    assert ShadowSavedEvent(level=1) in result.events
    record = result.world.shadow_of("alice")
    assert record is not None
    snap = record.snapshot
    assert snap.owner == "alice"
    assert snap.hero == alice.hero
    assert snap.level == 1
    assert (snap.region, snap.location) == ("cloud_ridge", "mist_ferry")
    assert snap.saved_at == NOON
    assert snap.gear == ()  # 裝備欄位預留（5D）
    assert record.coins == 0 and record.reports == ()


@pytest.mark.parametrize(
    "action",
    [RestAction(), HireAction(), ShadowAiAction(profile="guard")],
    ids=["rest", "hire", "shadow_ai"],
)
def test_prep_actions_save(library: ContentLibrary, make_char: MakeChar, action: object) -> None:
    result = _step(library, make_world(), make_char("alice"), action)
    assert result.world.shadow_of("alice") is not None


def test_no_save_outside_town_or_busy(calm: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    field = make_char("alice", location="hunter_hut", supplies=3)
    camped = _step(calm, world, field, CampAction())
    assert camped.world.shadows == ()  # 紮營不是城鎮整備
    moved = _step(calm, world, make_char("alice"), TravelAction(to="ferry_steps"))
    assert moved.world.shadows == ()
    busy = make_char("alice", pending_encounter=make_encounter("mist_ferry"))
    assert save_after_prep(calm, world, busy, RestAction(), NOON) == (world, ())
    away = make_char("alice", location="ferry_steps")
    assert save_after_prep(calm, world, away, RestAction(), NOON) == (world, ())


def test_resave_keeps_reports_and_coins(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    record = world.shadow_of("alice")
    assert record is not None
    world = world.model_copy(
        update={"shadows": (record.model_copy(update={"coins": 3, "reward_day": 7}),)}
    )
    leveled = make_char("alice", level=3)
    again = _step(library, world, leveled, RestAction(), NOON + 60).world.shadow_of("alice")
    assert again is not None
    assert again.snapshot.level == 3 and again.snapshot.saved_at == NOON + 60
    assert (again.coins, again.reward_day) == (3, 7)


# ---------------------------------------------------------------------------
# 借用
# ---------------------------------------------------------------------------


def test_borrow_shadow(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    record = world.shadow_of("alice")
    assert record is not None
    result = _step(
        library,
        world,
        make_char("bob"),
        HireAction(mercenaries=("merc_tiebi",), shadows=("alice",)),
    )
    bob = result.char
    assert bob.shadows == (record.snapshot,)
    assert bob.mercenaries == ("merc_tiebi",)
    # 不獨佔、不改主人：alice 的紀錄不變（bob 自己也存了影子）
    assert result.world.shadow_of("alice") == record
    assert result.world.shadow_of("bob") is not None


def test_borrow_is_not_exclusive(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    bob = _step(library, world, make_char("bob"), HireAction(shadows=("alice",)))
    carol = _step(library, bob.world, make_char("carol"), HireAction(shadows=("alice",)))
    assert bob.char.shadows[0].owner == carol.char.shadows[0].owner == "alice"


def test_borrowed_copy_does_not_follow_owner(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    bob = _step(library, world, make_char("bob"), HireAction(shadows=("alice",)))
    later = _step(library, bob.world, make_char("alice", level=4), RestAction(), NOON + 60)
    assert bob.char.shadows[0].level == 1  # 借用當下的複本（代決 5C2-4）
    rehire = _step(library, later.world, bob.char, HireAction(shadows=("alice",)), NOON + 90)
    assert rehire.char.shadows[0].level == 4


@pytest.mark.parametrize(
    ("owner", "mercs", "match"),
    [
        ("bob", (), "自己"),
        ("nobody", (), "沒有這個影子"),
        ("alice", ("merc_tiebi", "merc_huichun"), "最多帶 2 名"),
    ],
)
def test_borrow_errors(
    library: ContentLibrary,
    make_char: MakeChar,
    owner: str,
    mercs: tuple[str, ...],
    match: str,
) -> None:
    world = _with_alice_shadow(library, make_char)
    world = _step(library, world, make_char("bob"), RestAction()).world
    bob = make_char("bob")
    with pytest.raises(WorldActionError, match=match):
        _step(library, world, bob, HireAction(mercenaries=mercs, shadows=(owner,)))
    with pytest.raises(WorldActionError, match="兩次"):
        _step(library, world, bob, HireAction(shadows=("alice", "alice")))


def test_own_other_character_counts_as_shadow(library: ContentLibrary, make_char: MakeChar) -> None:
    """#100：自己的其他角色可以當影子（帳號在 5E，目前任何其他角色都可以借，代決 5C2-1）。"""
    world = _with_alice_shadow(library, make_char)
    alt = _step(library, world, make_char("alice_alt"), HireAction(shadows=("alice",)))
    assert alt.char.shadows[0].owner == "alice"


# ---------------------------------------------------------------------------
# 強度上限（#87）
# ---------------------------------------------------------------------------


def _strong_snapshot(library: ContentLibrary, make_char: MakeChar) -> ShadowSnapshot:
    alice = make_char("alice", level=5, skill_tier=2, attribute_points=2)
    hero = alice.hero
    attributes = dict(hero.attributes)
    attributes[Attribute.STR] += 4
    attributes[Attribute.WIS] += 2
    hero = hero.model_copy(
        update={"attributes": attributes, "skills": ("skill_chain_lightning", *hero.skills[:2])}
    )
    alice = alice.model_copy(
        update={"hero": hero, "attribute_spent": {Attribute.STR: 4, Attribute.WIS: 2}}
    )
    return shadow_snapshot(alice, NOON)


def test_cap_to_recruiter(library: ContentLibrary, make_char: MakeChar) -> None:
    snap = _strong_snapshot(library, make_char)
    per = library.roguelite.attribute_points_per_level
    attrs = capped_attributes(library, snap, 1)
    removed = per * 4 - 2  # 4 級的點數，先扣未分配的 2 點
    assert sum(snap.hero.attributes.values()) - sum(attrs.values()) == min(removed, 6)
    assert attrs[Attribute.STR] <= snap.hero.attributes[Attribute.STR]
    spawn, skills = shadow_spawn(library, snap, 1, "guard")
    template = spawn.template
    assert template.id == "shadow_alice"
    assert template.name_zh == snap.hero.name_zh
    assert template.level == 1
    assert template.ai_profile == "guard"
    base = snap.hero.max_hp
    assert template.max_hp == base + library.ruleset.core.level_hp_bonus(base, 1)
    assert spawn.team is Team.ALLY
    by_id = {s.id: s for s in skills}
    capped = template.skills[0]
    assert capped.endswith("_alice") and by_id[capped].tier == 1  # 2 階技能往下配到 1 階
    assert template.skills[1:] == snap.hero.skills[1:]  # 內容庫的 1 階技能不動


def test_weaker_shadow_kept_as_is(library: ContentLibrary, make_char: MakeChar) -> None:
    snap = _strong_snapshot(library, make_char)
    spawn, skills = shadow_spawn(library, snap, 9)
    assert spawn.template.level == 5
    assert spawn.template.attributes == snap.hero.attributes
    assert spawn.template.skills == snap.hero.skills  # 2 階技能不超過上限：原樣
    assert skills == ()


def test_battle_has_capped_shadow(library: ContentLibrary, make_char: MakeChar) -> None:
    snap = _strong_snapshot(library, make_char)
    world = make_world()
    bob = make_char("bob").model_copy(update={"shadows": (snap,), "mercenaries": ()})
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    ready = bob.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    prepared = prepare_battle(library, ready)
    allies = [u for u in prepared.setup.units if u.team is Team.ALLY]
    assert [u.template.id for u in allies] == [bob.hero.id, "shadow_alice"]
    assert allies[1].template.level == 1
    known = prepared.setup.ruleset.skills.by_id()
    assert all(s in known for s in allies[1].template.skills)
    assert world.shadows == ()


# ---------------------------------------------------------------------------
# 每天第一次被借用（#102）
# ---------------------------------------------------------------------------


def _fight_with_shadow(
    library: ContentLibrary, world: WorldState, bob: CharacterState, now: int
) -> StepResult:
    encounter = make_encounter(
        "ferry_steps", seed=5, battle_map="cliff_outpost", from_location="mist_ferry"
    )
    ready = bob.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    return _step(library, world, ready, FightAction(steps=auto_steps(library, ready)), now)


def test_daily_first_borrow_rewards_owner(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    hired = _step(
        library, world, make_char("bob"), HireAction(mercenaries=PARTY[:1], shadows=("alice",))
    )
    first = _fight_with_shadow(library, hired.world, hired.char, NOON + 60)
    started = next(e for e in first.events if isinstance(e, BattleStartedEvent))
    assert started.shadows == ("alice",)
    assert ShadowLentEvent(owner="alice", coins=1) in first.events
    record = first.world.shadow_of("alice")
    assert record is not None
    assert record.coins == 1 and len(record.reports) == 1
    report = record.reports[0]
    assert report.borrower == "bob" and report.location == "ferry_steps"
    assert report.foes
    # 同一天第二次：不給
    second = _fight_with_shadow(library, first.world, hired.char, NOON + 120)
    assert not any(isinstance(e, ShadowLentEvent) for e in second.events)
    assert second.world.shadow_of("alice") == record
    # 隔天（早上 6 點刷新）再給
    third = _fight_with_shadow(library, second.world, hired.char, NOON + DAY)
    again = third.world.shadow_of("alice")
    assert again is not None and again.coins == 2 and len(again.reports) == 2


def test_season_boss_flag(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    bob = make_char("bob")
    assert season_boss_problem(bob) is None
    hired = _step(library, world, bob, HireAction(shadows=("alice",))).char
    assert season_boss_problem(hired) == SEASON_BOSS_PROBLEM


# ---------------------------------------------------------------------------
# 打法（玩法 PM 定 ④）與欄位上限（②）
# ---------------------------------------------------------------------------


def test_party_ai(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _with_alice_shadow(library, make_char)
    action = HireAction(
        mercenaries=("merc_tiebi",),
        shadows=("alice",),
        ai={"merc_tiebi": "brute", "alice": "support"},
    )
    bob = _step(library, world, make_char("bob"), action).char
    assert bob.party_ai == {"alice": "support", "merc_tiebi": "brute"}
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    ready = bob.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    units = {u.template.id: u.template for u in prepare_battle(library, ready).setup.units}
    assert units["merc_tiebi"].ai_profile == "brute"
    assert units["shadow_alice"].ai_profile == "support"
    with pytest.raises(WorldActionError, match="隊伍成員"):
        _step(library, world, make_char("bob"), HireAction(ai={"merc_tiebi": "brute"}))
    with pytest.raises(WorldActionError, match="沒有這種打法"):
        _step(
            library,
            world,
            make_char("bob"),
            HireAction(mercenaries=("merc_tiebi",), ai={"merc_tiebi": "idle"}),
        )


def test_shadow_ai_is_owner_default(library: ContentLibrary, make_char: MakeChar) -> None:
    alice = _step(library, make_world(), make_char("alice"), ShadowAiAction(profile="guard"))
    assert alice.char.shadow_ai == "guard"
    record = alice.world.shadow_of("alice")
    assert record is not None and record.snapshot.ai_profile == "guard"
    spawn, _ = shadow_spawn(library, record.snapshot, 1)
    assert spawn.template.ai_profile == "guard"
    with pytest.raises(WorldActionError, match="沒有這種打法"):
        _step(library, make_world(), make_char("alice"), ShadowAiAction(profile="idle"))
    with pytest.raises(WorldActionError, match="野外"):
        _step(library, make_world(), make_char("alice", location="ferry_steps"), ShadowAiAction())


def test_mercenary_skills_fit_slots(library: ContentLibrary) -> None:
    slots = library.ruleset.core.skill_slots
    actives = [s.id for s in library.skills.values() if s.slot_kind == "active"][:8]
    base = library.builds.by_id()["build_tank"].hero
    big = base.model_copy(update={"skills": tuple(actives)})
    capped = slot_capped(library, big)
    assert capped.skills == tuple(actives[: slots.active])
    table = library.world_mercenaries
    assert table is not None
    for merc in table.mercenaries:
        hero = slot_capped(library, library.builds.by_id()[merc.build].hero)
        assert not skill_slot_problems([library.skills[s] for s in hero.skills], slots)


# ---------------------------------------------------------------------------
# 重播
# ---------------------------------------------------------------------------


def test_shadow_log_replays(calm: ContentLibrary, make_char: MakeChar) -> None:
    alice, bob = make_char("alice"), make_char("bob")
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id="alice", action=RestAction()),
        WorldLogEntry(
            seq=2,
            now=NOON + 30,
            character_id="bob",
            action=HireAction(shadows=("alice",), ai={"alice": "guard"}),
        ),
        WorldLogEntry(
            seq=3, now=NOON + 60, character_id="bob", action=TravelAction(to="ferry_steps")
        ),
    ]
    chars = {"alice": alice, "bob": bob}
    first = replay(calm, make_world(), chars, entries)
    second = replay(calm, make_world(), chars, entries)
    assert dumps_world(first.world) == dumps_world(second.world)
    assert dumps_char(first.characters["bob"]) == dumps_char(second.characters["bob"])
    assert first.characters["bob"].shadows[0].owner == "alice"
    assert first.events == second.events
