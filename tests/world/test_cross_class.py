"""大世界主手換別大類（Phase 6T-1b；玩法 PM 決定 6T-1a 第 5 項，08 8.13 #135）。

- 城鎮與營火可以把主手換成別大類的武器；roguelite 照 07 7.1 只換同大類。
- 換上後原大類的武器技開戰時不放進技能列（戰鬥裡不能用）；技能還在角色身上，換回同大類就恢復。
- 掉落判斷「同大類」看目前裝備的主手。
- 戰鬥與世界日誌的重播一致。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from trpg.content.equipment import ItemDef
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.engine.actions import UseSkill
from trpg.engine.battle import begin_battle, legal_actions
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.gear import equip_swap
from trpg.shared.rng import Rng
from trpg.world.actions import FightAction
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.economy_actions import EquipAction
from trpg.world.gear import gear_run
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.state import CharacterState
from trpg.world.step import world_step
from trpg.world.weapon_mix import hero_skills, usable_skills, weapon_class_of

MakeChar = Callable[..., CharacterState]


def _sword(library: ContentLibrary) -> ItemDef:
    for seed in range(200):
        item = generate_item(library, Rng(seed), "weapon", "rare", 2, weapon_class="melee")
        weapon = library.weapons[item.weapon or ""]
        if not weapon.two_handed and not weapon.paired:
            return item
    raise AssertionError("找不到單手近戰武器")


def _focus_skills(library: ContentLibrary, char: CharacterState) -> list[str]:
    return [s for s in char.hero.skills if library.skills[s].weapon_req == "focus"]


@pytest.fixture
def swapped(library: ContentLibrary, make_char: MakeChar) -> tuple[CharacterState, CharacterState]:
    """（換之前、換上近戰武器之後）：測試主角拿法器。"""
    sword = _sword(library)
    before = make_char(gear=(sword,))
    after = world_step(library, make_world(), before, EquipAction(item=sword.id), NOON).char
    return before, after


def test_world_equips_other_class(
    library: ContentLibrary, swapped: tuple[CharacterState, CharacterState]
) -> None:
    before, after = swapped
    assert weapon_class_of(library, before) == "focus"
    assert weapon_class_of(library, after) == "melee"  # 掉落的「同大類」跟著目前的主手
    assert after.hero.skills == before.hero.skills  # 技能留在身上
    blocked = _focus_skills(library, before)
    assert blocked  # 測試主角有法器武器技
    assert hero_skills(library, after) == tuple(s for s in before.hero.skills if s not in blocked)
    assert hero_skills(library, before) == before.hero.skills


def test_roguelite_still_same_class(library: ContentLibrary, make_char: MakeChar) -> None:
    sword = _sword(library)
    run = gear_run(make_char(gear=(sword,)))
    with pytest.raises(ChoiceError, match="同一大類"):
        equip_swap(library, run, sword, from_backpack=True)


def _battle_char(char: CharacterState) -> CharacterState:
    return char.model_copy(
        update={
            "location": "ferry_steps",
            "pending_encounter": make_encounter("ferry_steps"),
            "mercenaries": PARTY,
        }
    )


def test_blocked_skills_absent_in_battle(
    library: ContentLibrary, swapped: tuple[CharacterState, CharacterState]
) -> None:
    before, after = swapped
    blocked = set(_focus_skills(library, before))
    prepared = prepare_battle(library, _battle_char(after))
    hero = prepared.setup.units[0]
    assert hero.weapon.weapon_class == "melee"
    assert not blocked & set(hero.template.skills)
    state = begin_battle(prepared.setup, prepared.seed).state  # 引擎的技能／武器檢查通過
    used = {a.skill_id for a in legal_actions(state) if isinstance(a, UseSkill)}
    assert not blocked & used
    # 換回原本的法器：全部恢復
    staff = next(g for g in after.gear if g.weapon is not None)
    back = world_step(library, make_world(), after, EquipAction(item=staff.id), NOON).char
    assert weapon_class_of(library, back) == "focus"
    restored = prepare_battle(library, _battle_char(back)).setup.units[0]
    assert blocked <= set(restored.template.skills)


def test_cross_class_fight_replays(
    library: ContentLibrary, swapped: tuple[CharacterState, CharacterState]
) -> None:
    before, after = swapped
    char = _battle_char(after)
    steps = auto_steps(library, char)
    blocked = set(_focus_skills(library, before))
    assert not blocked & {s.skill_id for s in steps if isinstance(s, UseSkill)}
    fight = FightAction(steps=steps)
    first = world_step(library, make_world(), char, fight, NOON)
    again = world_step(library, make_world(), char, fight, NOON)
    assert first == again
    # 世界日誌：換裝一筆（城鎮）、戰鬥一筆（野外），重播得到同樣的角色
    sword_id = after.equipment["main_hand"].id
    wear = EquipAction(item=sword_id)
    equip = (WorldLogEntry(seq=1, now=NOON, character_id="alice", action=wear),)
    equipped = replay(library, make_world(), {"alice": before}, equip).characters["alice"]
    assert equipped == after
    fought = (WorldLogEntry(seq=1, now=NOON, character_id="alice", action=fight),)
    done = replay(library, make_world(), {"alice": char}, fought)
    assert done.characters["alice"] == first.char
    assert replay(library, make_world(), {"alice": char}, fought) == done


def test_usable_skills_keeps_order() -> None:
    assert usable_skills(("a", "b", "c"), {}, "melee") == ("a", "b", "c")
