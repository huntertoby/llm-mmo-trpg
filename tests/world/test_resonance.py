"""裝備共鳴（Phase 5D-3；08 8.9、M3；``docs/phases/Phase5計畫.md`` 30.4）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.world.battle import prepare_battle
from trpg.world.crafting_actions import CraftAction
from trpg.world.economy_actions import EquipAction
from trpg.world.gear import hero_loadout, item_loadout
from trpg.world.resonance import active_resonances, item_keywords
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
SMITHY = "smithy_mist_ferry"
MIST = "item_mist_crystal"


def _craft_and_wear(
    library: ContentLibrary, char: CharacterState, slot: str, affix: str, mats: tuple[str, ...]
) -> CharacterState:
    action = CraftAction(
        station=SMITHY,
        slot_type=slot,  # type: ignore[arg-type]
        rarity="rare",
        affix=affix,
        grade="item_coarse_material",
        materials=mats,
    )
    world = make_world()
    char = world_step(library, world, char, action, NOON).char
    return world_step(library, world, char, EquipAction(item=char.gear[-1].id), NOON).char


def _rich(make_char: MakeChar, **updates: Any) -> CharacterState:
    bag = {"item_coarse_material": 20, MIST: 5}
    return make_char(gold=1000, level=3, bag=bag, **updates)


def test_two_pieces_trigger_resonance(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _rich(make_char)
    char = _craft_and_wear(library, char, "body", "affix_cond_still_defense", (MIST,))
    assert "concealed" in item_keywords(library, char.equipment["body"])
    one = item_loadout(library, char.equipment)
    weapon = library.weapons[char.hero.weapon]
    assert active_resonances(library, one, weapon) == ()  # 1 件沒有
    char = _craft_and_wear(library, char, "neck", "affix_kw_burn_duration", (MIST,))
    found = active_resonances(library, item_loadout(library, char.equipment), weapon)
    loadout = hero_loadout(library, char)
    assert [r.resonance.keyword for r in found] == ["concealed"]
    slot = found[0].slot
    assert slot is not None and found[0].affix in {"affix_attr_dex", "affix_max_hp"}
    carrier = loadout.item_in(slot)
    assert carrier is not None and carrier.affixes[-1].affix.id == found[0].affix
    assert "霧隱共鳴" in found[0].text_zh(library)
    # 開戰用的裝備帶共鳴；存檔裡的裝備不變
    battle = char.model_copy(
        update={"location": "ferry_steps", "pending_encounter": make_encounter("ferry_steps")}
    )
    hero = prepare_battle(library, battle).setup.units[0]
    worn: dict[str, Any] = {e.slot: e for e in hero.equipment.items}
    assert len(worn[slot].affixes) == len(char.equipment[slot].affixes) + 1


def test_no_resonance_rules(library: ContentLibrary, make_char: MakeChar) -> None:
    bare = replace(library, world_resonance=None)
    char = _rich(make_char)
    char = _craft_and_wear(library, char, "body", "affix_cond_still_defense", (MIST,))
    char = _craft_and_wear(library, char, "neck", "affix_kw_burn_duration", (MIST,))
    loadout = hero_loadout(bare, char)
    assert all(len(e.affixes) == len(e.item.affixes) for e in loadout.items)
    assert all(e.item == char.equipment[e.slot] for e in loadout.items)
