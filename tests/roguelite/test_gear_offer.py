"""Phase 3K-2：戰後裝備三選一接進一輪（07 7.1；行為一致測試見 Phase3K計畫 第 4 節）。

候選：同種子同結果、3 件部位不重複、主手同大類、稀有度權重、每件穿得上。流程：先裝備三選一再升級、
Boss 戰後不給、跳過、換下的進背包、營火換裝、雙手武器收副手。一致：存檔往返與戰鬥中存檔重播、
換上後開戰的實際數值等於卡片寫的、AI 代打確定。
"""

from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction

import pytest

from tests.roguelite.helpers import library
from trpg.content.equipment import ItemDef, StatAffix, loadout_problems
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.engine import begin_battle
from trpg.engine.gear.core import build_gear, geared_template
from trpg.narrative.events import _skill_name, _View
from trpg.roguelite import (
    ActiveBattle,
    ChoiceError,
    NodeConflictError,
    RunSave,
    RunState,
    apply_choice,
    auto_play,
    battle_setup,
    dumps_save,
    finish_battle,
    loads_save,
    new_keyword_run,
)
from trpg.roguelite.gear import (
    auto_gear_pick,
    current_item,
    equip,
    item_score,
    make_gear_offer,
    run_loadout,
    weapon_swap_prompt,
    worn_items,
)
from trpg.roguelite.progress import hero_effective_attributes, hero_unit_id
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    EquipChoice,
    GearOfferNode,
    GearPickChoice,
    LevelUpChoice,
    LevelUpNode,
)
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, top_attribute

KEYWORDS = ("ignite", "prone")


def _run(weapon: str = "one_handed_sword", seed: int = 3, **kwargs: object) -> RunState:
    return new_keyword_run(library(), weapon, KEYWORDS, seed, **kwargs)  # type: ignore[arg-type]


def _won(run: RunState) -> RunState:
    """打贏現在的戰鬥（AI 控制整場）並結算，回傳戰後狀態。"""
    battle = ActiveBattle(library(), run)
    battle.auto()
    return finish_battle(library(), run, battle.state, len(battle.steps), battle.steps)


def _after_first_win(seed: int = 3, weapon: str = "one_handed_sword") -> RunState:
    after = _won(_run(weapon, seed))
    assert isinstance(after.node, GearOfferNode)
    return after


# ---------------------------------------------------------------------------
# 候選
# ---------------------------------------------------------------------------


def test_offer_is_deterministic_per_seed_and_battle() -> None:
    run = _run()
    assert make_gear_offer(library(), run, 1) == make_gear_offer(library(), run, 1)
    assert make_gear_offer(library(), run, 1) != make_gear_offer(library(), run, 2)
    assert make_gear_offer(library(), run, 1) != make_gear_offer(library(), _run(seed=4), 1)


@pytest.mark.parametrize("weapon", ["one_handed_sword", "dual_pistol", "fire_staff"])
def test_three_distinct_parts_and_main_hand_matches_the_hero_class(weapon: str) -> None:
    lib = library()
    run = _run(weapon)
    hero_class = lib.weapons[weapon].weapon_class
    for seed in range(60):
        offer = make_gear_offer(lib, run.model_copy(update={"seed": seed}), 1)
        assert len(offer) == lib.item_gen.offer_size == 3  # type: ignore[union-attr]
        types = [i.slot_type for i in offer]
        assert len(set(types)) == 3
        assert len({i.id for i in offer}) == 3
        for item in offer:
            if item.slot_type == "weapon":
                assert item.weapon is not None
                assert lib.weapons[item.weapon].weapon_class == hero_class


def test_every_offered_item_can_be_worn_and_passes_the_whole_loadout_checks() -> None:
    lib = library()
    run = _run()
    for seed in range(80):
        trial = run.model_copy(update={"seed": seed})
        for item in make_gear_offer(lib, trial, 1):
            after = equip(lib, trial, item)
            weapon = lib.weapons[after.hero.weapon]
            assert loadout_problems(run_loadout(lib, after), weapon, lib.ruleset.equipment) == []


def test_rarity_follows_the_weights_40_25_20_13_2() -> None:
    lib = library()
    assert lib.item_gen is not None
    assert lib.item_gen.rarity_weights == {
        "common": 40,
        "uncommon": 25,
        "rare": 20,
        "epic": 13,
        "legendary": 2,
    }
    run = _run()
    counts: Counter[str] = Counter()
    for seed in range(1500):
        for item in make_gear_offer(lib, run.model_copy(update={"seed": seed}), 1):
            counts[item.rarity or ("legendary" if item.legendary else "?")] += 1
    total = sum(counts.values())
    assert total > 4000
    for rarity, weight in lib.item_gen.rarity_weights.items():
        assert abs(counts[rarity] / total - weight / 100) < 0.03, (rarity, counts)


def test_offered_items_are_at_the_hero_level_budget() -> None:
    lib = library()
    run = _run().model_copy(update={"level": 4})
    for item in make_gear_offer(lib, run, 2):
        assert item.item_level in (4, None)  # 傳說從現有物品挑，沒有物品等級


# ---------------------------------------------------------------------------
# 流程
# ---------------------------------------------------------------------------


def test_gear_comes_before_level_up_and_skip_keeps_the_gear() -> None:
    after = _after_first_win()
    assert after.levels_pending == 1 and after.level == 1  # 還沒升級
    assert after.equipment == {} and after.backpack == ()
    skipped = apply_choice(library(), after, GearPickChoice(pick=None))
    assert isinstance(skipped.node, LevelUpNode)
    assert skipped.equipment == {} and skipped.backpack == ()
    assert run_loadout(library(), skipped) == run_loadout(library(), after)


def test_picking_equips_directly_and_the_replaced_item_goes_to_the_backpack() -> None:
    lib = library()
    after = _after_first_win()
    node = after.node
    assert isinstance(node, GearOfferNode)
    taken = apply_choice(lib, after, GearPickChoice(pick=0))
    assert isinstance(taken.node, LevelUpNode)
    first = node.candidates[0]
    assert first in taken.equipment.values()
    # 換同部位的另一件（戒指有兩個欄位，指定同一欄）：舊的進背包
    slot = next(s for s, i in taken.equipment.items() if i == first)
    other = generate_item(lib, Rng(5), first.slot_type, "uncommon", 1)
    swapped = equip(lib, taken, other, slot)
    assert swapped.equipment[slot] == other and first in swapped.backpack
    assert len(swapped.equipment) == len(taken.equipment)


def test_bad_gear_choices_are_rejected() -> None:
    after = _after_first_win()
    with pytest.raises(ChoiceError):
        apply_choice(library(), after, GearPickChoice(pick=3))
    with pytest.raises(NodeConflictError):
        apply_choice(library(), after, LevelUpChoice(attributes={Attribute.STR: 2}))
    with pytest.raises(NodeConflictError):
        apply_choice(library(), after, EquipChoice(item_id="x"))  # 只能在營火換裝


def test_boss_battle_win_ends_the_run_without_a_gear_offer() -> None:
    run = _run()
    last = len(run.plan)
    boss = run.model_copy(
        update={"battles_done": last - 1, "node": BattleNode(index=last), "levels_pending": 0}
    )
    after = _won(boss)
    assert after.history[-1].boss and not isinstance(after.node, GearOfferNode)


def _weapon_item(lib, weapon_id: str):  # type: ignore[no-untyped-def]
    """指定武器的產生物品（換底材重抽到為止）。"""
    for seed in range(3000):
        item = generate_item(lib, Rng(seed), "weapon", "uncommon", 2)
        if item.weapon == weapon_id:
            return item
    raise AssertionError(weapon_id)


def test_main_hand_swap_changes_the_hero_weapon_within_the_class() -> None:
    lib = library()
    run = _run("one_handed_sword")
    spear = _weapon_item(lib, "spear")
    assert lib.weapons["spear"].weapon_class == "melee"
    after = equip(lib, run, spear)
    assert after.hero.weapon == "spear" and after.equipment["main_hand"] == spear
    assert [i.id for i in after.backpack] == ["base_one_handed_sword"]  # 原本的基礎武器進背包
    # 營火可以換回
    back = equip(lib, after, after.backpack[0], from_backpack=True)
    assert back.hero.weapon == "one_handed_sword" and spear in back.backpack
    # 不同大類的武器換不上
    with pytest.raises(ChoiceError, match="同一大類"):
        equip(lib, run, _weapon_item(lib, "bow"))


def test_two_handed_main_hand_moves_the_off_hand_into_the_backpack() -> None:
    lib = library()
    run = _run("one_handed_sword")
    shield = next(
        i
        for s in range(300)
        if (i := generate_item(lib, Rng(s), "offhand", "common", 2)).slot_type == "offhand"
    )
    held = equip(lib, run, shield)
    assert held.equipment["off_hand"] == shield
    two_handed = next(
        i
        for s in range(2000)
        if (i := generate_item(lib, Rng(s), "weapon", "common", 2, weapon_class="melee")).weapon
        and (w := lib.weapons[i.weapon]).two_handed
        and not w.paired
    )
    swapped = equip(lib, held, two_handed)
    assert "off_hand" not in swapped.equipment
    assert shield in swapped.backpack
    assert swapped.hero.weapon == two_handed.weapon
    # 主手是雙手武器時，副手候選不出，也放不上去
    assert all(
        i.slot_type != "offhand"
        for s in range(30)
        for i in make_gear_offer(lib, swapped.model_copy(update={"seed": s}), 1)
    )
    with pytest.raises(ChoiceError):
        equip(lib, swapped, shield)


def _campfire_run() -> RunState:
    lib = library()
    run = _run()
    for _ in range(3):  # 第 3 場後營火
        run = _won(run)
        run = apply_choice(lib, run, GearPickChoice(pick=0))
        if isinstance(run.node, LevelUpNode):
            run = apply_choice(lib, run, LevelUpChoice(attributes={Attribute.STR: run.node.points}))
        assert isinstance(run.node, BattleNode | CampfireNode)
    return run


def test_campfire_can_swap_gear_from_the_backpack_for_free() -> None:
    lib = library()
    run = _campfire_run()
    assert isinstance(run.node, CampfireNode)
    shirt = generate_item(lib, Rng(11), "body", "uncommon", 2)
    run = equip(lib, run, shirt)
    older = generate_item(lib, Rng(12), "body", "common", 1)
    run = run.model_copy(update={"backpack": (*run.backpack, older)})
    assert shirt in run.equipment.values()
    swapped = apply_choice(lib, run, EquipChoice(item_id=older.id))
    assert isinstance(swapped.node, CampfireNode)  # 不推進節點
    assert older in swapped.equipment.values() and shirt in swapped.backpack
    assert older not in swapped.backpack
    with pytest.raises(ChoiceError):
        apply_choice(lib, swapped, EquipChoice(item_id="item_nope"))
    with pytest.raises(ChoiceError):
        apply_choice(lib, swapped, EquipChoice(item_id=shirt.id, slot="head"))


def test_rings_fill_the_empty_ring_slot_first_then_replace_the_weaker() -> None:
    lib = library()
    run = _run()
    strong = generate_item(lib, Rng(1), "ring", "uncommon", 6)
    weak = generate_item(lib, Rng(2), "ring", "uncommon", 1)
    third = generate_item(lib, Rng(3), "ring", "uncommon", 3)
    run = equip(lib, equip(lib, run, strong), weak)
    assert set(run.equipment) == {"ring_1", "ring_2"}
    assert run.equipment["ring_1"] == strong and run.equipment["ring_2"] == weak
    run = equip(lib, run, third)
    assert strong in run.equipment.values() and third in run.equipment.values()
    assert weak in run.backpack


# ---------------------------------------------------------------------------
# 一致性
# ---------------------------------------------------------------------------


def test_battle_values_match_the_item_cards() -> None:
    """換上後開戰的主角：屬性、最大 HP 等於卡片寫的詞條加成。"""
    lib = library()
    run = _run()
    base_attrs = hero_effective_attributes(lib, run)
    base_hp = geared_template(
        run.hero, build_gear(run_loadout(lib, run), lib.ruleset.equipment), lib.ruleset
    ).max_hp
    checked = 0
    for seed in range(120):
        for item in generate_item_batch(lib, seed):
            rolls = {lib.affixes[r.affix].id: r for r in item.affixes}
            after = equip(lib, run, item)
            attrs = hero_effective_attributes(lib, after)
            gain_by_attr = {a: attrs[a] - base_attrs[a] for a in Attribute}
            card_by_attr = {a: 0 for a in Attribute}
            for roll in rolls.values():
                affix = lib.affixes[roll.affix]
                if isinstance(affix, StatAffix) and affix.attribute is not None:
                    card_by_attr[affix.attribute] += roll.value or 0
            assert gain_by_attr == card_by_attr
            hp = geared_template(
                after.hero, build_gear(run_loadout(lib, after), lib.ruleset.equipment), lib.ruleset
            ).max_hp
            card_hp = 0
            for r in item.affixes:
                found = lib.affixes[r.affix]
                if isinstance(found, StatAffix) and found.stat == "max_hp":
                    card_hp += r.value or 0
            assert hp - base_hp == card_hp
            checked += 1
    assert checked > 100


def generate_item_batch(lib: ContentLibrary, seed: int) -> list[ItemDef]:
    return [
        generate_item(lib, Rng(seed), "neck", "uncommon", 4),
        generate_item(lib, Rng(seed), "body", "uncommon", 4),
        generate_item(lib, Rng(seed), "ring", "common", 4),
    ]


def test_the_hero_spawns_with_the_run_equipment() -> None:
    lib = library()
    after = _after_first_win()
    node = after.node
    assert isinstance(node, GearOfferNode)
    taken = apply_choice(lib, after, GearPickChoice(pick=0))
    setup = battle_setup(
        lib, apply_choice(lib, taken, LevelUpChoice(attributes={Attribute.STR: 2}, pick=None))
    )
    hero = setup.units[0]
    assert hero.equipment == run_loadout(lib, taken)
    assert node.candidates[0] in [e.item for e in hero.equipment.items]


def test_save_round_trip_keeps_equipment_and_backpack_and_the_gear_node() -> None:
    lib = library()
    after = _after_first_win()
    save = loads_save(dumps_save(RunSave(run_id="g", run=after)))
    assert save.run == after and isinstance(save.run.node, GearOfferNode)
    taken = apply_choice(lib, after, GearPickChoice(pick=0))
    taken = taken.model_copy(update={"backpack": (taken.equipment[next(iter(taken.equipment))],)})
    raw = json.loads(dumps_save(RunSave(run_id="g", run=taken)))
    assert raw["format"] == "trpg-run/11" and raw["run"]["equipment"] and raw["run"]["backpack"]
    assert loads_save(json.dumps(raw)).run == taken


def test_a_trpg_run_5_save_without_the_new_fields_still_loads() -> None:
    run = _run()
    raw = json.loads(dumps_save(RunSave(run_id="old", run=run)))
    raw["format"] = "trpg-run/5"
    del raw["run"]["equipment"], raw["run"]["backpack"]
    loaded = loads_save(json.dumps(raw))
    assert loaded.format == "trpg-run/11"
    assert loaded.run.equipment == {} and loaded.run.backpack == ()
    assert loaded.run == run


def test_battle_in_progress_replays_identically_with_run_equipment() -> None:
    lib = library()
    after = _after_first_win()
    run = apply_choice(lib, after, GearPickChoice(pick=0))
    run = apply_choice(lib, run, LevelUpChoice(attributes={Attribute.STR: 2}))
    assert isinstance(run.node, BattleNode)
    battle = ActiveBattle(lib, run)
    battle.auto(lambda b: len(b.steps) >= 8)
    saved = loads_save(dumps_save(RunSave(run_id="m", run=run, battle=battle.to_saved())))
    restored = ActiveBattle.restore(lib, saved.run, saved.battle)  # type: ignore[arg-type]
    assert restored.steps == battle.steps
    hero = hero_unit_id(restored.state)
    assert restored.state.units[hero] == battle.state.units[hero]
    restored.auto()
    battle.auto()
    assert restored.state == battle.state


def test_auto_play_is_deterministic_and_takes_gear() -> None:
    lib = library()
    a, _ = auto_play(lib, _run(seed=9))
    b, _ = auto_play(lib, _run(seed=9))
    assert a == b
    assert a.equipment  # AI 在三選一裡至少挑過一件


def test_auto_pick_prefers_the_largest_gain_over_what_is_worn() -> None:
    lib = library()
    run = _run()
    weak = generate_item(lib, Rng(1), "neck", "common", 1)
    strong = generate_item(lib, Rng(2), "neck", "uncommon", 6)
    run = equip(lib, run, strong)
    other = generate_item(lib, Rng(3), "head", "uncommon", 6)
    node = GearOfferNode(after_battle=1, candidates=(weak, other))
    # 項鍊已經是強的 → 選空著的頭
    assert auto_gear_pick(lib, run, node) == 1
    # 全部都不比目前好 → 跳過
    run = equip(lib, run, other)
    assert auto_gear_pick(lib, run, GearOfferNode(after_battle=1, candidates=(weak,))) is None
    assert item_score(lib, strong) > item_score(lib, weak) > Fraction(0)
    assert worn_items(lib, run)["neck"] == strong


def test_legendary_rule_gear_from_the_offer_can_be_narrated() -> None:
    """傳說裝備的規則改變詞條沒有技能定義（``skill_gear_*``）；事件描述要找得到名稱（3K-2 起戰後會
    拿到傳說物品，不能在描述事件時 KeyError）。"""
    lib = library()
    run = equip(lib, _run(), lib.items["item_g3b_legend_wake"])
    setup = battle_setup(lib, run.model_copy(update={"node": BattleNode(index=1)}))
    view = _View(begin_battle(setup, 0).state, {}, {})
    wake = lib.affixes["affix_rule_bleeding_wake"].name_zh
    assert _skill_name(view, "skill_gear_rule_bleeding_wake") == wake
    assert _skill_name(view, "skill_nope") == "skill_nope"


# --- 3K-2b：換主手的提示與預算分數的基礎強度 ----------------------------------------------------


def test_weapon_swap_prompt_only_when_the_scaling_attributes_differ() -> None:
    lib = library()
    run = _run("one_handed_sword")
    attrs = hero_effective_attributes(lib, run)
    top = top_attribute(attrs)
    same = weapon_swap_prompt(lib, run, _weapon_item(lib, "spear"), "main_hand", attrs)
    assert same is None  # 單手劍與長槍都看力量：直接換
    text = weapon_swap_prompt(lib, run, _weapon_item(lib, "dagger"), "main_hand", attrs)
    assert text == f"這把看敏捷、力量，你目前最高的是{top.display_name}"
    # 不是主手欄位時沒有提示
    ring = generate_item(lib, Rng(1), "ring", "common", 2)
    assert weapon_swap_prompt(lib, run, ring, "ring_1", attrs) is None


def test_base_weapon_score_is_not_zero_and_follows_the_base_damage() -> None:
    lib = library()
    run = _run("one_handed_sword")
    base = current_item(lib, run, "main_hand")
    assert base is not None and base.id == "base_one_handed_sword"
    sword = lib.weapons["one_handed_sword"]
    assert sword.dice.sides == 8 and sword.dice.count == 1  # 參考底材：1d8
    assert item_score(lib, base) == Fraction(18)  # 等級 1 主手基礎份額池 18，單手劍拿整個池
    greatsword = _weapon_item(lib, "greatsword")
    plain = greatsword.model_copy(update={"affixes": (), "base_bonus_permille": 0})
    assert item_score(lib, plain) > item_score(lib, base)  # 大劍的基礎傷害比較高
    body = generate_item(lib, Rng(2), "body", "common", 3).model_copy(
        update={"kind": "plate", "affixes": (), "base_bonus_permille": 0}
    )
    assert body.item_level == 3
    assert item_score(lib, body) == Fraction(18)  # 等級 3 身體池 18（同部位底材都拿整池）
