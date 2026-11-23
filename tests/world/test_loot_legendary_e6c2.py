"""E6-c2 第 2 項：世界掉落傳說（08 8.30 第 8 點）。

只有精英、頭目的掉落有 2% 是傳說（``loot.yaml`` 的 ``elite_legendary_permille``），一般戰鬥照舊
不出；受 ``legendary_enabled`` 控制，關著時掉落逐位元不變。傳說的亂數用 ``fork("legendary")``，
不推進原本的串流，所以開關打開後沒抽到傳說的那件和關著時相同。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from trpg.content.equipment import ItemDef
from trpg.content.item_budget import Rarity
from trpg.content.library import ContentLibrary
from trpg.content.world_loot import GearDropRules
from trpg.shared.rng import Rng
from trpg.world.loot import _roll_gear, loot_rules
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]
REGION = "cloud_ridge"
LEVEL = 6
LEGENDARY_SLOTS = ("weapon", "offhand", "body", "feet", "neck")


def _with(lib: ContentLibrary, *, enabled: bool, permille: int | None = None) -> ContentLibrary:
    assert lib.item_gen is not None and lib.world_loot is not None
    gen = lib.item_gen.model_copy(update={"legendary_enabled": enabled})
    loot = lib.world_loot
    if permille is not None:
        gear = loot.gear.model_copy(update={"elite_legendary_permille": permille})
        loot = loot.model_copy(update={"gear": gear})
    return dataclasses.replace(lib, item_gen=gen, world_loot=loot)


def _drop(
    lib: ContentLibrary,
    char: CharacterState,
    seed: int,
    *,
    elite: bool,
    forced: Rarity | None = None,
) -> tuple[ItemDef, ...]:
    rules = loot_rules(lib)
    assert rules is not None
    return _roll_gear(
        lib, rules, char, Rng(seed), region=REGION, level=LEVEL, elite=elite, forced=forced
    )


def test_default_rate_is_two_percent(library: ContentLibrary) -> None:
    rules = loot_rules(library)
    assert rules is not None
    assert rules.gear.elite_legendary_permille == 20
    assert library.item_gen is not None and library.item_gen.legendary_enabled is False


def test_switch_off_is_unchanged(library: ContentLibrary, make_char: MakeChar) -> None:
    """開關關著（預設）：2% 不抽，精英、一般戰鬥的掉落和機率 0 時逐位元相同。"""
    char = make_char()
    zero = _with(library, enabled=False, permille=0)
    for seed in range(60):
        for elite in (True, False):
            assert _drop(library, char, seed, elite=elite) == _drop(zero, char, seed, elite=elite)


def test_only_elites_drop_legendaries(library: ContentLibrary, make_char: MakeChar) -> None:
    """機率調到 100%：精英那一件一定是傳說（頭、手、戒指降成史詩，8.30 第 6 點）；一般戰鬥不出。"""
    char = make_char()
    lib = _with(library, enabled=True, permille=1000)
    elites = [g for seed in range(40) for g in _drop(lib, char, seed, elite=True)]
    assert len(elites) == 40
    for item in elites:
        if item.slot_type in LEGENDARY_SLOTS:
            assert item.rarity == "legendary" and item.legendary
        else:
            assert item.rarity == "epic"
    assert any(i.rarity == "legendary" for i in elites)
    normal = [g for seed in range(200) for g in _drop(lib, char, seed, elite=False)]
    assert normal and all(i.rarity != "legendary" for i in normal)


def test_two_percent_with_switch_on(library: ContentLibrary, make_char: MakeChar) -> None:
    """初值 2%：精英偶爾出傳說；沒抽到的那件和開關關著時相同（亂數用 fork，不推進串流）。"""
    char = make_char()
    on = _with(library, enabled=True)
    legendary = 0
    for seed in range(400):
        got = _drop(on, char, seed, elite=True)
        if got[0].rarity == "legendary":
            legendary += 1
        else:
            assert got == _drop(library, char, seed, elite=True)
    assert 1 <= legendary <= 25
    normal = [g for seed in range(300) for g in _drop(on, char, seed, elite=False)]
    assert all(i.rarity != "legendary" for i in normal)


def test_boss_floor_can_become_legendary(library: ContentLibrary, make_char: MakeChar) -> None:
    """頭目的保底史詩（5F-3）：抽到傳說時換成傳說。"""
    char = make_char()
    lib = _with(library, enabled=True, permille=1000)
    rarities = {
        g.rarity
        for seed in range(20)
        for g in _drop(lib, char, seed, elite=True, forced="epic")
        if g.slot_type in LEGENDARY_SLOTS
    }
    assert rarities == {"legendary"}


def test_battle_weights_cannot_have_legendary(library: ContentLibrary) -> None:
    """一般戰鬥不掉傳說（8.30 第 8 點）：``battle_weights`` 寫傳說被擋下。"""
    rules = loot_rules(library)
    assert rules is not None
    data = rules.gear.model_dump()
    data["battle_weights"] = {**data["battle_weights"], "legendary": 1}
    with pytest.raises(ValidationError, match="一般戰鬥不掉傳說"):
        GearDropRules.model_validate(data)
