"""大世界的閃現、重閃、溶掉、傳承、配點與重配（Phase 5A-6；``docs/phases/Phase5計畫.md`` 11.2）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.skillgen.flash_state import SkillFlash, acquire
from trpg.world.actions import (
    AllocateAction,
    AttributesAllocatedEvent,
    BattleEndedEvent,
    CampAction,
    DissolveAction,
    FightAction,
    FlashAction,
    FlashOfferedEvent,
    FlashPickAction,
    FlashPickedEvent,
    InheritAction,
    LoadoutAction,
    RespecAction,
    SkillDissolvedEvent,
    SkillInheritedEvent,
    TravelAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, LocationRef
from trpg.world.step import max_hp, new_character, world_step

MakeChar = Callable[..., CharacterState]
SKILL = "skill_frost_shackle"  # FL-1a：戰歌只有「只多冷卻」的蓄力，改成沒有閃現選項


def _used(char: CharacterState, *skills: str, insight: int = 4) -> CharacterState:
    flash = {s: acquire(s).model_copy(update={"used": True}) for s in skills}
    return char.model_copy(update={"flash": flash, "insight": insight})


def _step(library: ContentLibrary, char: CharacterState, action: object) -> CharacterState:
    return world_step(library, make_world(), char, action, NOON).char  # type: ignore[arg-type]


def _flashed(library: ContentLibrary, char: CharacterState) -> CharacterState:
    char = _step(library, _used(char, SKILL), FlashAction(skill=SKILL))
    return _step(library, char, FlashPickAction(pick=0))


# ---------------------------------------------------------------------------
# 戰後：先上場用過、一般戰鬥不給靈感
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def after_win(library: ContentLibrary) -> tuple[CharacterState, CharacterState]:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"location": "ferry_steps", "mercenaries": PARTY})
    for seed in range(16):
        start = char.model_copy(
            update={
                "pending_encounter": make_encounter(
                    "ferry_steps", seed=seed, battle_map="cliff_outpost"
                )
            }
        )
        result = world_step(
            library, make_world(), start, FightAction(steps=auto_steps(library, start)), NOON
        )
        if next(e for e in result.events if isinstance(e, BattleEndedEvent)).won:
            return start, result.char
    raise AssertionError("找不到會贏的種子")


def test_battle_marks_used_and_usage(after_win: tuple[CharacterState, CharacterState]) -> None:
    before, after = after_win
    assert after.flash  # 裝備著打完一場：被動、反應都算用過；主動放過才算
    assert all(state.used for state in after.flash.values())
    assert set(after.flash) <= set(before.hero.skills)
    assert after.skill_usage
    assert after.insight == 2 * (after.level - before.level)  # 只有升級給的


# ---------------------------------------------------------------------------
# 閃現
# ---------------------------------------------------------------------------


def test_flash_in_town_then_pick(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _used(make_char(), SKILL)
    result = world_step(library, make_world(), char, FlashAction(skill=SKILL), NOON)
    offered = next(e for e in result.events if isinstance(e, FlashOfferedEvent))
    assert (offered.cost, offered.insight) == (1, 3)
    assert offered.options >= 1
    assert result.char.pending_flash is not None
    with pytest.raises(WorldActionError, match="閃現的選項沒有選"):
        world_step(library, make_world(), result.char, TravelAction(to="ferry_steps"), NOON)
    picked = world_step(library, make_world(), result.char, FlashPickAction(pick=0), NOON)
    event = next(e for e in picked.events if isinstance(e, FlashPickedEvent))
    char = picked.char
    assert char.pending_flash is None
    assert event.skill == SKILL and event.new_skill != SKILL
    assert event.new_skill in char.hero.skills
    assert SKILL not in (*char.hero.skills, *char.bench)
    assert event.new_skill in {s.id for s in char.generated_skills}
    assert len(char.flash[event.new_skill].records) == 1
    # 規則包帶著閃現後的技能，可以開戰
    char = char.model_copy(
        update={"pending_encounter": make_encounter("ferry_steps", battle_map="cliff_outpost")}
    )
    prepared = prepare_battle(library, char)
    assert event.new_skill in prepared.setup.ruleset.skills.by_id()


def test_flash_needs_town_or_camp(library: ContentLibrary, make_char: MakeChar) -> None:
    wild = _used(make_char(location="ferry_steps"), SKILL)
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        _step(library, wild, FlashAction(skill=SKILL))
    camped = _step(library, make_char(location="hunter_hut", supplies=3), CampAction())
    assert camped.camped_at == LocationRef(region="cloud_ridge", location="hunter_hut")
    offered = _step(library, _used(camped, SKILL), FlashAction(skill=SKILL))
    assert offered.pending_flash is not None


def test_flash_requires_use_and_insight(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError):
        _step(library, make_char(insight=4), FlashAction(skill=SKILL))  # 還沒上場用過
    with pytest.raises(WorldActionError, match="靈感點不足"):
        _step(library, _used(make_char(), SKILL, insight=0), FlashAction(skill=SKILL))
    with pytest.raises(WorldActionError, match="沒有待選"):
        _step(library, make_char(), FlashPickAction(pick=0))


def test_reflash_slot(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _flashed(library, make_char())
    new_id = next(s for s in char.hero.skills if s.startswith(SKILL))
    reflash = _step(library, char, FlashAction(skill=new_id, slot=1))
    assert reflash.pending_flash is not None
    assert reflash.insight == char.insight - 1
    done = _step(library, reflash, FlashPickAction(pick=0))
    assert done.pending_flash is None


# ---------------------------------------------------------------------------
# 溶掉、傳承
# ---------------------------------------------------------------------------


def test_dissolve_refunds_half(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(flash={SKILL: SkillFlash(base_id=SKILL, spent=5)}, insight=1)
    result = world_step(library, make_world(), char, DissolveAction(skill=SKILL), NOON)
    event = next(e for e in result.events if isinstance(e, SkillDissolvedEvent))
    assert (event.refund, result.char.insight) == (2, 3)
    assert SKILL not in result.char.hero.skills
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        _step(
            library,
            char.model_copy(update={"location": "ferry_steps"}),
            DissolveAction(skill=SKILL),
        )


def test_inherit_carries_minor_variation(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _flashed(library, make_char())
    source = next(s for s in char.hero.skills if s.startswith(SKILL))
    targets = [s for s in char.hero.skills if s != source]
    for target in targets:
        try:
            result = world_step(
                library,
                make_world(),
                char,
                InheritAction(skill=target, source=source, records=(1,)),
                NOON,
            )
        except WorldActionError:
            continue
        event = next(e for e in result.events if isinstance(e, SkillInheritedEvent))
        after = result.char
        assert source not in (*after.hero.skills, *after.bench)
        assert event.new_skill in after.hero.skills
        assert len(after.flash[event.new_skill].records) == 1
        assert after.insight == char.insight  # 不退點
        return
    pytest.fail("沒有任何技能可以接受這個變化")


# ---------------------------------------------------------------------------
# 配點與重配、換技能
# ---------------------------------------------------------------------------


def test_allocate_anywhere_and_hp_follows_con(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(location="ferry_steps", attribute_points=2)
    result = world_step(
        library, make_world(), char, AllocateAction(attributes={Attribute.CON: 2}), NOON
    )
    after = result.char
    assert after.hero.attributes[Attribute.CON] == char.hero.attributes[Attribute.CON] + 2
    assert after.attribute_points == 0
    assert after.attribute_spent == {Attribute.CON: 2}
    assert after.hp == char.hp + max_hp(library, after) - max_hp(library, char)
    assert isinstance(result.events[0], AttributesAllocatedEvent)
    with pytest.raises(WorldActionError, match="屬性點不足"):
        _step(library, after, AllocateAction(attributes={Attribute.STR: 1}))
    encounter = make_encounter("ferry_steps", battle_map="cliff_outpost")
    with pytest.raises(WorldActionError, match="遭遇"):
        _step(
            library,
            char.model_copy(update={"pending_encounter": encounter}),
            AllocateAction(attributes={Attribute.CON: 1}),
        )


def test_respec_only_in_town_or_camp(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _step(
        library, make_char(attribute_points=2), AllocateAction(attributes={Attribute.WIS: 2})
    )
    back = _step(library, char, RespecAction())
    assert back.attribute_points == 2
    assert back.hero.attributes == make_char().hero.attributes
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        _step(library, char.model_copy(update={"location": "ferry_steps"}), RespecAction())


def test_loadout_with_generated_skill(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _flashed(library, make_char())
    new_id = next(s for s in char.hero.skills if s.startswith(SKILL))
    others = tuple(s for s in char.hero.skills if s != new_id)
    benched = _step(library, char, LoadoutAction(skills=others))
    assert new_id in benched.bench
    back = _step(library, benched, LoadoutAction(skills=(new_id, *others)))
    assert back.hero.skills[0] == new_id
    assert new_id in back.flash
