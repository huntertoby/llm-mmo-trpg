"""戰鬥掉落（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.4）：材料（家族、精英、通用料、第三方）、
裝備（物品等級、精英史詩、區域關鍵字）、進背包（放不下的等戰後結算選要丟哪件，5D-2b）、確定性。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from trpg.content.equipment import ItemDef, KeywordAffix
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.engine.events import DamageDealt, EventBase, UnitDowned
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.world.actions import BattleEndedEvent, FightAction
from trpg.world.battle import PreparedBattle, _run, auto_steps, prepare_battle
from trpg.world.economy_actions import (
    LootAbandonedEvent,
    LootChooseAction,
    LootChosenEvent,
    LootGainedEvent,
)
from trpg.world.encounters import LineupMember
from trpg.world.errors import WorldActionError
from trpg.world.loot import LootRoll, add_loot, loot_rules, roll_loot, third_downed_by_allies
from trpg.world.state import CharacterState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]


def _ready(make_char: MakeChar, seed: int) -> CharacterState:
    return make_char(
        location="ferry_steps",
        mercenaries=PARTY,
        pending_encounter=make_encounter("ferry_steps", seed=seed),
    )


def _fight(library: ContentLibrary, char: CharacterState) -> StepResult:
    action = FightAction(steps=auto_steps(library, char))
    return world_step(library, make_world(), char, action, NOON)


def _won_battle(
    library: ContentLibrary, make_char: MakeChar
) -> tuple[CharacterState, PreparedBattle, BattleState, list[EventBase]]:
    for seed in range(12):
        char = _ready(make_char, seed)
        prepared = prepare_battle(library, char)
        state, events = _run(prepared, auto_steps(library, char))
        if state.winner is Team.ALLY:
            return char, prepared, state, events
    raise AssertionError("12 個種子都沒有打贏")


def _roll(
    library: ContentLibrary,
    char: CharacterState,
    prepared: PreparedBattle,
    state: BattleState,
    events: list[EventBase],
    *,
    seed: int | None = None,
    lineup: object = None,
) -> LootRoll:
    return roll_loot(
        library,
        char,
        setup=prepared.setup,
        lineup=prepared.lineup if lineup is None else lineup,  # type: ignore[arg-type]
        state=state,
        events=events,
        seed=prepared.seed if seed is None else seed,
        level=prepared.enemy_level,
    )


def test_win_puts_loot_in_bag(library: ContentLibrary, make_char: MakeChar) -> None:
    for seed in range(12):
        char = _ready(make_char, seed)
        result = _fight(library, char)
        ended = next(e for e in result.events if isinstance(e, BattleEndedEvent))
        loot = [e for e in result.events if isinstance(e, LootGainedEvent)]
        if not ended.won:
            assert loot == []
            assert result.char.last_battle is not None and result.char.last_battle.loot is None
            continue
        if not loot:
            continue
        event = loot[0]
        for item, n in event.materials.items():
            assert result.char.bag.get(item, 0) == char.bag.get(item, 0) + n
        assert tuple(g.id for g in result.char.gear) == event.gear
        summary = result.char.last_battle.loot  # type: ignore[union-attr]
        assert summary is not None and summary.materials == event.materials
        again = _fight(library, char)
        assert again.char == result.char  # 同種子、同步驟：逐位元相同
        return
    raise AssertionError("12 個種子都沒有掉落")


def test_gear_item_level_is_location_level(library: ContentLibrary, make_char: MakeChar) -> None:
    char, prepared, state, events = _won_battle(library, make_char)
    elite = LineupMember(unit=prepared.lineup.members[0].unit, affix="regenerating")
    lineup = prepared.lineup.model_copy(update={"members": (elite, *prepared.lineup.members[1:])})
    roll = _roll(library, char, prepared, state, events, lineup=lineup)
    assert len(roll.gear) == 1  # 精英必掉 1 件
    assert roll.gear[0].item_level == prepared.enemy_level
    assert roll.materials[0] == "item_living_bone"  # 再生的 → 活血骨


def test_elite_gear_epic_about_half(library: ContentLibrary, make_char: MakeChar) -> None:
    char, prepared, state, events = _won_battle(library, make_char)
    elite = LineupMember(unit=prepared.lineup.members[0].unit, affix="regenerating")
    lineup = prepared.lineup.model_copy(update={"members": (elite, *prepared.lineup.members[1:])})
    rolls = [
        _roll(library, char, prepared, state, events, seed=s, lineup=lineup) for s in range(40)
    ]
    epic = sum(1 for r in rolls if r.gear and r.gear[0].rarity == "epic")
    assert all(len(r.gear) == 1 for r in rolls)
    assert 10 <= epic <= 30  # 50%


def test_each_elite_drops_one_gear(library: ContentLibrary, make_char: MakeChar) -> None:
    """5D-2b（20.2，玩法 PM 2026-11-03 代決）：每名精英 1 件。"""
    char, prepared, state, events = _won_battle(library, make_char)
    members = prepared.lineup.members
    assert len(members) >= 2
    one = (LineupMember(unit=members[0].unit, affix="regenerating"), *members[1:])
    two = (
        LineupMember(unit=members[0].unit, affix="regenerating"),
        LineupMember(unit=members[1].unit, affix="regenerating"),
        *members[2:],
    )
    for seed in range(5):
        single = _roll(
            library,
            char,
            prepared,
            state,
            events,
            seed=seed,
            lineup=prepared.lineup.model_copy(update={"members": one}),
        )
        double = _roll(
            library,
            char,
            prepared,
            state,
            events,
            seed=seed,
            lineup=prepared.lineup.model_copy(update={"members": two}),
        )
        assert len(single.gear) == 1 and len(double.gear) == 2
        assert double.gear[0].id != double.gear[1].id
        assert all(g.item_level == prepared.enemy_level for g in double.gear)


def test_normal_material_rate(library: ContentLibrary, make_char: MakeChar) -> None:
    char, prepared, state, events = _won_battle(library, make_char)
    downed = sum(
        1
        for uid, spawn in zip(sorted(state.units), prepared.setup.units, strict=False)
        if spawn.team is Team.ENEMY and state.units[uid].downed
    )
    assert downed >= 1
    trials = 200
    got = sum(
        len(_roll(library, char, prepared, state, events, seed=s).materials) for s in range(trials)
    )
    rate = got / (trials * downed)
    assert 0.3 <= rate <= 0.5  # 40%
    gear = sum(
        1 for s in range(trials) if _roll(library, char, prepared, state, events, seed=s).gear
    )
    assert 15 <= gear <= 50  # 15%


def test_family_or_generic_material(library: ContentLibrary, make_char: MakeChar) -> None:
    char, prepared, state, events = _won_battle(library, make_char)
    rules = library.world_loot
    assert rules is not None
    found = {m.unit: rules.family_material("cloud_ridge", m.unit) for m in prepared.lineup.members}
    allowed = {item for item in found.values() if item is not None}
    if None in found.values():
        allowed.add("item_coarse_material")  # 1 級地點：沒有家族的掉粗料
    seen: set[str] = set()
    for s in range(30):
        seen.update(_roll(library, char, prepared, state, events, seed=s).materials)
    assert seen and seen <= allowed


def test_third_party_needs_ally_kill(library: ContentLibrary, make_char: MakeChar) -> None:
    _, prepared, state, _ = _won_battle(library, make_char)
    ally = next(u for u in state.units_sorted() if u.team is Team.ALLY)
    foe = [u for u in state.units_sorted() if u.team is Team.ENEMY]

    def hit(seq: int, target: UnitId, source: UnitId) -> EventBase:
        return DamageDealt.model_validate(
            {
                "seq": seq,
                "round": 1,
                "target_id": target,
                "source_id": source,
                "cause": "attack",
                "element": "physical",
                "rolls": (3,),
                "crit": False,
                "element_mod_ppm": 1_000_000,
                "amount": 3,
                "hp_before": 3,
                "hp_after": 0,
            }
        )

    events: list[EventBase] = [
        hit(0, foe[0].id, ally.id),
        UnitDowned(seq=1, round=1, unit_id=foe[0].id),
        hit(2, foe[1].id, foe[0].id),
        UnitDowned(seq=3, round=1, unit_id=foe[1].id),
    ]
    assert third_downed_by_allies(state, events) == frozenset({foe[0].id})
    assert prepared.lineup.third == ()


FULL_BAG = {"item_hp_potion_small": 300}  # 30 格滿


def test_full_bag_waits_for_choice(library: ContentLibrary, make_char: MakeChar) -> None:
    """5D-2b（玩法 PM 2026-11-03 代決）：放不下的不再直接不撿，留給戰後結算選要丟哪件。"""
    item = generate_item(library, Rng(1), "body", "rare", 1)
    char = make_char(bag=FULL_BAG)
    roll = LootRoll(materials=("item_wolf_fang",), gear=(item,))
    after, summary, events = add_loot(library, char, roll)
    assert after.bag == char.bag and after.gear == ()
    assert after.pending_loot is not None
    assert after.pending_loot.materials == {"item_wolf_fang": 1}
    assert after.pending_loot.gear == (item,)
    assert summary is not None and summary.lost_materials == {} and summary.lost_gear == ()
    event = events[0]
    assert isinstance(event, LootGainedEvent)
    assert event.pending_materials == {"item_wolf_fang": 1}
    assert event.pending_gear_names == (item.name_zh,)


def test_partial_room(library: ContentLibrary, make_char: MakeChar) -> None:
    item = generate_item(library, Rng(1), "body", "rare", 1)
    char = make_char(bag={"item_hp_potion_small": 290})  # 29 格
    roll = LootRoll(materials=("item_wolf_fang", "item_wolf_fang"), gear=(item,))
    after, _, _ = add_loot(library, char, roll)
    assert after.bag["item_wolf_fang"] == 2  # 同一格疊 20
    assert after.pending_loot is not None and after.pending_loot.gear == (item,)


def _full_with_pending(
    library: ContentLibrary, make_char: MakeChar
) -> tuple[CharacterState, ItemDef, ItemDef]:
    old = generate_item(library, Rng(2), "head", "rare", 1)
    new = generate_item(library, Rng(1), "body", "rare", 1)
    char = make_char(bag={"item_hp_potion_small": 290}, gear=(old,))  # 29 格＋1 件＝30
    after, _, _ = add_loot(library, char, LootRoll(materials=("item_wolf_fang",), gear=(new,)))
    assert after.pending_loot is not None
    return after, old, new


def _choose(library: ContentLibrary, char: CharacterState, **kwargs: object) -> StepResult:
    return world_step(library, make_world(), char, LootChooseAction(**kwargs), NOON)  # type: ignore[arg-type]


def test_choose_drop_old_gear(library: ContentLibrary, make_char: MakeChar) -> None:
    """丟背包裡原本的裝備＋1 組藥水，新拿到的全部收下。"""
    char, old, new = _full_with_pending(library, make_char)
    result = _choose(library, char, drop_gear=(old.id,), drop_items={"item_hp_potion_small": 10})
    after = result.char
    assert after.pending_loot is None
    assert after.gear == (new,)
    assert after.bag == {"item_hp_potion_small": 280, "item_wolf_fang": 1}
    event = result.events[0]
    assert isinstance(event, LootChosenEvent)
    assert event.dropped_gear_names == (old.name_zh,)
    assert event.gear == (new.id,) and event.materials == {"item_wolf_fang": 1}
    again = _choose(library, char, drop_gear=(old.id,), drop_items={"item_hp_potion_small": 10})
    assert again.char == after  # 確定性


def test_choose_drop_new_loot(library: ContentLibrary, make_char: MakeChar) -> None:
    """新拿到的也可以丟：丟掉新的裝備與材料，背包不變。"""
    char, old, new = _full_with_pending(library, make_char)
    after = _choose(library, char, drop_gear=(new.id,), drop_items={"item_wolf_fang": 1}).char
    assert after.pending_loot is None
    assert after.gear == (old,) and after.bag == {"item_hp_potion_small": 290}


def test_choose_must_fit(library: ContentLibrary, make_char: MakeChar) -> None:
    char, old, _new = _full_with_pending(library, make_char)
    with pytest.raises(WorldActionError, match="還差 2 格"):
        _choose(library, char)
    with pytest.raises(WorldActionError, match="還差 1 格"):
        _choose(library, char, drop_gear=(old.id,))
    with pytest.raises(WorldActionError, match="沒有這件裝備"):
        _choose(library, char, drop_gear=("item_nope",))
    with pytest.raises(WorldActionError, match="沒有那麼多"):
        _choose(library, char, drop_items={"item_wolf_fang": 2})
    with pytest.raises(WorldActionError, match="沒有等著決定"):
        _choose(library, char.model_copy(update={"pending_loot": None}))
    worn = char.model_copy(update={"gear": (), "equipment": {"head": old}})
    with pytest.raises(WorldActionError, match="穿戴中的不能丟"):
        _choose(library, worn, drop_gear=(old.id,))


def test_next_win_abandons_undecided(library: ContentLibrary, make_char: MakeChar) -> None:
    """沒決定的只留到下一場打贏結算掉落前（不做暫存區）。"""
    char, _, new = _full_with_pending(library, make_char)
    after, _, events = add_loot(library, char, LootRoll())
    assert after.pending_loot is None
    gone = events[0]
    assert isinstance(gone, LootAbandonedEvent)
    assert gone.gear_names == (new.name_zh,) and gone.materials == {"item_wolf_fang": 1}


def test_pending_loot_defaults_for_old_saves(make_char: MakeChar) -> None:
    data = make_char().model_dump(mode="json")
    data.pop("pending_loot", None)
    assert CharacterState.model_validate(data).pending_loot is None


def test_keywords_default_is_unchanged(library: ContentLibrary) -> None:
    for seed in range(5):
        plain = generate_item(library, Rng(seed), "ring", "rare", 3)
        empty = generate_item(library, Rng(seed), "ring", "rare", 3, keywords=())
        assert plain == empty


def test_keywords_bias_build_affix(library: ContentLibrary) -> None:
    wanted = {
        a.id
        for a in library.affixes.values()
        if isinstance(a, KeywordAffix) and a.keyword in ("wet", "charged")
    }
    if not wanted:
        pytest.skip("沒有潮濕、帶電的技能強化詞條")
    hits = 0
    for seed in range(10):
        item = generate_item(library, Rng(seed), "neck", "rare", 5, keywords=("wet", "charged"))
        hits += any(r.affix in wanted for r in item.affixes)
    assert hits >= 8


def test_cloud_ridge_bias_reaches_all_three_keywords(library: ContentLibrary) -> None:
    """5D-2b：雲嶺的偏向（潮濕、帶電、隱蔽）每個都有技能強化詞條，掉落真的會出現三種。"""
    rules = loot_rules(library)
    assert rules is not None
    keywords = rules.region("cloud_ridge").keywords
    assert set(keywords) == {"wet", "charged", "concealed"}
    by_id = {
        a.id: a
        for a in library.affixes.values()
        if isinstance(a, KeywordAffix) and a.keyword in keywords
    }
    seen: set[str] = set()
    for seed in range(40):
        item = generate_item(library, Rng(seed), "neck", "rare", 5, keywords=keywords)
        seen |= {by_id[r.affix].keyword for r in item.affixes if r.affix in by_id}
    assert seen == set(keywords)


@pytest.mark.parametrize("keyword", ["ignite", "prone", "poisoned", "wet", "concealed"])
def test_every_region_keyword_has_create_and_exploit(library: ContentLibrary, keyword: str) -> None:
    """8.21.4.1：雲嶺與荒原（點燃、倒地、中毒）的偏向關鍵字各有製造 1、利用 1 條技能強化詞條。"""
    directions = {
        a.direction
        for a in library.affixes.values()
        if isinstance(a, KeywordAffix) and a.keyword == keyword
    }
    assert directions == {"create", "exploit"}
