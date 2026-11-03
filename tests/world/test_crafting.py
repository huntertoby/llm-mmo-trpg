"""鐵匠與附魔台（Phase 5D-3；``docs/phases/Phase5計畫.md`` 28.4）：打造、配方碼與首位發現者、
隱藏配方、強化、重骰、指定、分解。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.item_budget import affix_budget, affix_points
from trpg.content.item_gen import affix_choices, generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.crafting import build_choices, fingerprint, plan_craft
from trpg.world.crafting_actions import (
    AffixChangedEvent,
    CraftAction,
    EnhanceAction,
    GearCraftedEvent,
    GearSalvagedEvent,
    ImbueAction,
    RerollAction,
    SalvageAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]
SMITHY = "smithy_mist_ferry"
ENCHANTER = "enchanter_mist_ferry"
COARSE = "item_coarse_material"
FINE = "item_fine_material"
MIST = "item_mist_crystal"
FEATHER = "item_thunder_feather"
ASH = "item_talisman_ash"
ESSENCE = "item_essence"
KW_NECK = "affix_kw_burn_duration"
BODY_PICK = "affix_cond_still_defense"


def _rich(make_char: MakeChar, character_id: str = "alice", **updates: Any) -> CharacterState:
    bag = {COARSE: 20, FINE: 20, MIST: 5, FEATHER: 5, ASH: 5, ESSENCE: 20}
    data: dict[str, Any] = {"gold": 5000, "quest_coins": 20, "level": 5, "bag": bag}
    data.update(updates)
    return make_char(character_id, **data)


def _craft(**fields: Any) -> CraftAction:
    data: dict[str, Any] = {"station": SMITHY, "slot_type": "neck", "rarity": "rare"}
    data.update({"affix": KW_NECK, "grade": COARSE})
    data.update(fields)
    return CraftAction(**data)


def _step(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: object
) -> StepResult:
    return world_step(library, world, char, action, NOON)  # type: ignore[arg-type]


def _crafted(result: StepResult) -> GearCraftedEvent:
    return next(e for e in result.events if isinstance(e, GearCraftedEvent))


# ---------------------------------------------------------------------------
# 打造
# ---------------------------------------------------------------------------


def test_craft_basic(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _rich(make_char)
    result = _step(library, make_world(), char, _craft(materials=(MIST,)))
    event = _crafted(result)
    item = result.char.gear[-1]
    assert item.id == f"item_craft_{event.code}_1"
    assert item.slot_type == "neck" and item.rarity == "rare"
    assert item.item_level == 3  # 粗料上限 3（角色 5 級，8.26.2）
    assert item.affixes[0].affix == KW_NECK  # 指定的 build 詞條在第 1 條
    assert "resonance_concealed" in item.tags  # 霧晶的共鳴關鍵字
    assert event.spent == {COARSE: 1, MIST: 1}
    assert result.char.bag[COARSE] == 19 and result.char.bag[MIST] == 4
    assert result.char.gold == 5000 - 10 * 3
    assert event.discovered and event.discoverer_name == char.hero.name_zh
    record = result.world.recipe_of(event.code)
    assert record is not None and record.discoverer == "alice"
    assert result.char.gear_mods[item.id].recipe == event.code


def test_same_recipe_same_item(library: ContentLibrary, make_char: MakeChar) -> None:
    """8.20：同一份配方一定打出同一件裝備（不同角色也一樣），首位發現者只記第一次。"""
    first = _step(library, make_world(), _rich(make_char), _craft(materials=(MIST, ASH)))
    second = _step(library, first.world, _rich(make_char, "bob"), _craft(materials=(ASH, MIST)))
    a, b = first.char.gear[-1], second.char.gear[-1]
    assert a.model_copy(update={"id": "x"}) == b.model_copy(update={"id": "x"})
    assert not _crafted(second).discovered
    assert second.world.recipe_of(_crafted(first).code).discoverer == "alice"  # type: ignore[union-attr]
    # 配方碼打造（朋友用自己的材料）
    third = _step(
        library,
        first.world,
        _rich(make_char, "carol"),
        CraftAction(station=SMITHY, code=_crafted(first).code.upper()),
    )
    assert third.char.gear[-1].affixes == a.affixes


def test_item_level_rules(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _rich(make_char)
    fine = _step(library, make_world(), char, _craft(grade=FINE)).char.gear[-1]
    assert fine.item_level == 5  # 精料上限 7，角色 5 級
    with pytest.raises(WorldActionError, match="最高 3"):
        _step(library, make_world(), char, _craft(item_level=4))
    low = _step(library, make_world(), char, _craft(item_level=2)).char.gear[-1]
    assert low.item_level == 2
    # 配方要求的等級不足時不能用配方碼（8.20）
    done = _step(library, make_world(), char, _craft(grade=FINE))
    code = _crafted(done).code
    with pytest.raises(WorldActionError, match="要 5 級"):
        _step(
            library,
            done.world,
            _rich(make_char, "bob", level=3),
            CraftAction(station=SMITHY, code=code),
        )


def test_craft_costs_and_failure_keeps_state(library: ContentLibrary, make_char: MakeChar) -> None:
    poor = _rich(make_char, gold=5)
    with pytest.raises(WorldActionError, match="金幣不夠"):
        _step(library, make_world(), poor, _craft())
    no_mat = _rich(make_char, bag={})
    with pytest.raises(WorldActionError, match="材料不夠"):
        _step(library, make_world(), no_mat, _craft())
    epic = _step(library, make_world(), _rich(make_char), _craft(rarity="epic"))
    assert _crafted(epic).quest_coins_spent == 2
    with pytest.raises(WorldActionError, match="任務幣不夠"):
        _step(library, make_world(), _rich(make_char, quest_coins=0), _craft(rarity="epic"))
    with pytest.raises(WorldActionError, match="不能指定"):
        _step(library, make_world(), _rich(make_char), _craft(affix="affix_attr_str"))
    with pytest.raises(WorldActionError, match="不在這裡"):
        _step(library, make_world(), _rich(make_char, location="ferry_steps"), _craft())
    with pytest.raises(WorldActionError, match="不是鐵匠"):
        _step(library, make_world(), _rich(make_char), _craft(station=ENCHANTER))


def test_body_build_pick(library: ContentLibrary, make_char: MakeChar) -> None:
    """代決 5D3-3：防具的 build 詞條是條件數值或防守型觸發。"""
    choices = {a.id for a in build_choices(library, "body")}
    assert BODY_PICK in choices and "affix_kw_burn_duration" not in choices
    assert "affix_unique_thunder_mist" not in choices
    result = _step(
        library, make_world(), _rich(make_char), _craft(slot_type="body", affix=BODY_PICK)
    )
    item = result.char.gear[-1]
    assert item.affixes[0].affix == BODY_PICK
    assert _crafted(result).spent[COARSE] == 2  # 身體用 2 個通用料


def test_leanings_shift_affixes(library: ContentLibrary, make_char: MakeChar) -> None:
    """M2：材料傾向讓傾向的詞條比較常出現（多個配方統計）。"""
    char = _rich(make_char, level=3)
    plain: Counter[str] = Counter()
    leaning: Counter[str] = Counter()
    for level in (1, 2, 3):
        for rarity in ("rare", "epic"):
            for slot, pick in (("neck", KW_NECK), ("body", BODY_PICK)):
                base = _craft(slot_type=slot, affix=pick, rarity=rarity, item_level=level)
                for counter, mats in ((plain, ()), (leaning, (MIST,))):
                    try:
                        result = _step(
                            library, make_world(), char, base.model_copy(update={"materials": mats})
                        )
                    except WorldActionError:  # 低等級的小部位放不下 build 詞條
                        continue
                    counter.update(a.affix for a in result.char.gear[-1].affixes[1:])
    assert leaning["affix_attr_dex"] > plain["affix_attr_dex"]


# ---------------------------------------------------------------------------
# 隱藏配方（M7）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slot", "materials", "name", "affix"),
    [
        ("body", (MIST, FEATHER, ASH), "驚雷霧袍", "affix_unique_thunder_mist"),
        ("hands", (MIST, "item_lava_core"), "蒸汽護腕", "affix_unique_steam_guard"),
        ("ring", ("item_frost_ember", "item_molten_heart"), "冰火雙生戒", "affix_unique_frostfire"),
    ],
)
def test_hidden_recipes(  # noqa: PLR0917 — pytest 參數化
    library: ContentLibrary,
    make_char: MakeChar,
    slot: str,
    materials: tuple[str, ...],
    name: str,
    affix: str,
) -> None:
    bag = {FINE: 5, **dict.fromkeys(materials, 1)}
    char = _rich(make_char, bag=bag, level=6)  # 戒指的詞條預算到 6 級才放得下觸發詞條
    action = _craft(slot_type=slot, affix=None, materials=materials, rarity="rare", grade=FINE)
    result = _step(library, make_world(), char, action)
    item = result.char.gear[-1]
    assert item.name_zh == name and item.rarity == "epic"
    assert item.affixes[0].affix == affix
    event = _crafted(result)
    assert event.hidden is not None and event.discovered
    assert result.world.recipe_of(event.code).recipe.affix is None  # type: ignore[union-attr]


def test_unique_affixes_not_in_drops(library: ContentLibrary) -> None:
    seen: set[str] = set()
    for seed in range(60):
        for slot in ("body", "hands", "ring"):
            item = generate_item(library, Rng(seed), slot, "epic", 5)
            seen.update(a.affix for a in item.affixes)
    assert not seen & set(library.item_gen.unique_affixes)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 強化、重骰、指定、分解
# ---------------------------------------------------------------------------


def _with_ring(library: ContentLibrary, make_char: MakeChar) -> tuple[WorldState, CharacterState]:
    result = _step(
        library, make_world(), _rich(make_char), _craft(rarity="epic", materials=(MIST,))
    )
    return result.world, result.char


def test_enhance(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char = _with_ring(library, make_char)
    ring = char.gear[-1]
    for level in (1, 2, 3):
        result = _step(library, world, char, EnhanceAction(station=SMITHY, item=ring.id))
        char = result.char
        assert char.gear_mods[ring.id].enhance == level
    assert char.gear[-1].base_bonus_permille == ring.base_bonus_permille + 60
    with pytest.raises(WorldActionError, match=r"\+3"):
        _step(library, world, char, EnhanceAction(station=SMITHY, item=ring.id))


def test_reroll_deterministic_and_escalating(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char = _with_ring(library, make_char)
    ring = char.gear[-1]
    action = RerollAction(station=ENCHANTER, item=ring.id, index=len(ring.affixes) - 1)
    first = _step(library, world, char, action)
    again = _step(library, world, char, action)
    assert first.char == again.char  # 同狀態同結果
    events = [e for e in first.events if isinstance(e, AffixChangedEvent)]
    assert events[0].old != events[0].new
    second = _step(library, world, first.char, action)
    gold = [
        e.gold_spent for e in (*first.events, *second.events) if isinstance(e, AffixChangedEvent)
    ]
    assert gold == [20, 40]  # 越骰越貴
    item = second.char.gear[-1]
    rules = library.item_gen
    assert rules is not None and item.item_level is not None
    points = sum(affix_points(rules, library.affixes[a.affix], a.value) for a in item.affixes)
    assert points <= affix_budget(rules, item.item_level, item.slot_type)
    assert second.char.bag[ESSENCE] == 18


def test_imbue(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char = _with_ring(library, make_char)
    ring = char.gear[-1]
    index = len(ring.affixes) - 1
    target = affix_choices(library, ring, index)[0][0].id
    action = ImbueAction(station=ENCHANTER, item=ring.id, index=index, affix=target)
    result = _step(library, world, char, action)
    assert result.char.gear[-1].affixes[index].affix == target
    assert result.char.bag[ESSENCE] == 17
    with pytest.raises(WorldActionError, match="不能指定"):
        _step(library, world, char, action.model_copy(update={"affix": "affix_rule_fire_mends"}))


def test_unique_affix_cannot_reroll(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _rich(make_char)
    result = _step(
        library,
        make_world(),
        char,
        _craft(slot_type="body", affix=None, materials=(MIST, FEATHER, ASH)),
    )
    robe = result.char.gear[-1]
    with pytest.raises(WorldActionError, match="不能換"):
        _step(
            library,
            result.world,
            result.char,
            RerollAction(station=ENCHANTER, item=robe.id, index=0),
        )


def test_salvage(library: ContentLibrary, make_char: MakeChar) -> None:
    world, char = _with_ring(library, make_char)
    ring = char.gear[-1]
    result = _step(library, world, char, SalvageAction(station=SMITHY, item=ring.id))
    event = next(e for e in result.events if isinstance(e, GearSalvagedEvent))
    assert event.essence == 3  # 史詩
    assert result.char.bag[ESSENCE] == 23
    assert ring.id not in result.char.gear_mods
    assert all(g.id != ring.id for g in result.char.gear)


def test_fingerprint_is_stable(library: ContentLibrary, make_char: MakeChar) -> None:
    plan = plan_craft(library, make_world(), _rich(make_char), _craft(materials=(MIST,)))
    assert plan.print_ == fingerprint(plan.recipe)
    assert len(plan.code) == 10
