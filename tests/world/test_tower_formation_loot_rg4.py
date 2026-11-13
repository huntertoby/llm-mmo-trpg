"""RG-4：打盾兵拿盾兵的盾（#163，08 8.11「取得」）——掉落算在持盾弟子／熔殼甲兵頭上、掉到塔盾時
必帶「盾陣」；同一個種子換成別的敵人時，掉的東西只差在那條詞條（必帶不用亂數）。

RG-5（玩法PM交接 4.1.5）：外觀也一定是對應形制——持盾弟子 → 雲紋碑盾 ``sect_great``、
熔殼甲兵 → 熔殼塔盾 ``molten_shell``；材質照一般規則（和換成別的敵人時同一件的材質相同）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.test_loot import _roll, _won_battle
from trpg.content.library import ContentLibrary
from trpg.world.encounters import LineupMember
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]
FORMATION = "affix_trait_tower_formation"
FORM = {"sect_shield_disciple": "sect_great", "molten_shell_trooper": "molten_shell"}


def test_an_elite_shield_troop_drops_tower_shields_with_the_formation(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char, prepared, state, events = _won_battle(library, make_char)
    # 範例主角拿雙手法杖（不掉副手）：改成單手劍，讓副手進掉落部位
    char = char.model_copy(
        update={"hero": char.hero.model_copy(update={"weapon": "one_handed_sword"})}
    )
    found = 0
    for unit in ("sect_shield_disciple", "molten_shell_trooper"):
        guard = prepared.lineup.model_copy(
            update={"members": (LineupMember(unit=unit, affix="regenerating"),)}
        )
        other = prepared.lineup.model_copy(
            update={"members": (LineupMember(unit="bandit", affix="regenerating"),)}
        )
        for seed in range(300):
            with_guard = _roll(library, char, prepared, state, events, seed=seed, lineup=guard)
            plain = _roll(library, char, prepared, state, events, seed=seed, lineup=other)
            (item,) = with_guard.gear
            (base,) = plain.gear
            assert item.id == base.id and item.offhand == base.offhand
            if item.offhand != "tower_shield":
                assert item == base
                continue
            found += 1
            assert any(r.affix == FORMATION for r in item.affixes)
            assert (base.kind, base.form) == ("kite_shield", "tower")
            assert (item.kind, item.form, item.material) == (
                "kite_shield",
                FORM[unit],
                base.material,
            )
            if not any(r.affix == FORMATION for r in base.affixes):
                assert item != base
    assert found > 0
