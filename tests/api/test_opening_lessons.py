"""#150 配點教學與教學順序（Phase OB-3；21 21.5 第 3、6 點、09 9.6.9）。

- 入門期不出配點教學；正式選定、三選一選完之後在葛蘭所在的城鎮出（點數都已照推薦配好，教的是
  重配再自己分）。
- 略過（``lesson:allocate_skip``）與上完（``lesson:allocate``）分開記；略過之後換過地點、第一次進
  城鎮或營火再提示一次。
- 第一次閃現的引導：4 級前不出（見 ``test_opening_flash.py``），開局結束（4 級）後才出。
- 已完成開局的舊角色（``opening is None``）教學順序與改前相同。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, hero, make_world
from tests.world.test_opening_choice import _confirm, _fast_played
from tests.world.test_opening_reselect import _chosen
from tests.world.test_opening_stages import _starter
from trpg.api.world_newcomer_view import lesson_view
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import (
    AllocateAction,
    HintSeenAction,
    OfferPickAction,
    RespecAction,
    RestAction,
    TravelAction,
    WorldAction,
)
from trpg.world.growth import at_service
from trpg.world.state import CharacterState, LocationRef, QuestState
from trpg.world.step import (
    LESSON_ALLOCATE,
    LESSON_ALLOCATE_AGAIN,
    LESSON_ALLOCATE_LEFT,
    LESSON_ALLOCATE_SKIP,
    new_character,
    world_step,
)

type MakeChar = Callable[..., CharacterState]


@pytest.fixture
def make_char(calm: ContentLibrary) -> MakeChar:
    def factory(character_id: str = "alice", **updates: object) -> CharacterState:
        char = new_character(calm, character_id, hero(calm), region="cloud_ridge")
        return char.model_copy(update=updates) if updates else char

    return factory


def _do(library: ContentLibrary, char: CharacterState, action: WorldAction) -> CharacterState:
    return world_step(library, make_world(), char, action, NOON).char


def _seen(library: ContentLibrary, char: CharacterState, *ids: str) -> CharacterState:
    return _do(library, char, HintSeenAction(ids=ids))


def test_no_allocate_lesson_in_the_starter_stage(calm: ContentLibrary, make_char: MakeChar) -> None:
    """入門期不出：升級的點數已經自動配掉；就算手動重配出了沒分的點也不教。OB-5：打完新手前兩步、
    人在葛蘭的城鎮時出的是「正式選定」（``choose``），不是配點。"""
    fresh = _starter(calm, make_char).model_copy(update={"location": "mist_ferry"})
    played = _fast_played(calm, make_char)
    assert played.level == 3 and played.attribute_points == 0
    respecced = _do(calm, played, RespecAction())
    assert respecced.attribute_points > 0
    assert lesson_view(calm, fresh) is None
    for char in (played, respecced):
        lesson = lesson_view(calm, char)
        assert lesson is not None and lesson.kind == "choose"


def test_allocate_lesson_after_the_formal_choice(calm: ContentLibrary, make_char: MakeChar) -> None:
    """正式選定後才出：三選一還沒選完不出；只在葛蘭所在的城鎮；教的是重配再分（全部 8 點）。"""
    chosen = _do(calm, _fast_played(calm, make_char), _confirm("melee"))
    assert chosen.pending_offers and lesson_view(calm, chosen) is None
    for _ in range(2):
        chosen = _do(calm, chosen, OfferPickAction(pick=0))
    lesson = lesson_view(calm, chosen)
    assert lesson is not None and lesson.kind == "allocate"
    assert lesson.respec and not lesson.reminder
    assert chosen.attribute_points == 0  # 都配好了：教學要先重配
    assert lesson.points == sum(chosen.attribute_spent.values()) == 8
    assert lesson.start_points == 0
    assert dict(lesson.recommended) == dict(chosen.attribute_spent)  # 推薦＝現在這套
    assert lesson.recommended_zh and lesson.skip_zh and {n.attr for n in lesson.notes}
    capital = chosen.model_copy(update={"region": "capital", "location": "capital"})
    assert lesson_view(calm, capital) is None  # 葛蘭在霧渡鎮
    # 照教學做：重配、自己分、記上完——不再出；4 級前也不會接閃現教學
    done = _do(calm, chosen, RespecAction())
    assert done.attribute_points == 8
    done = _do(calm, done, AllocateAction(attributes={Attribute.CON: 8}))
    done = _seen(calm, done, LESSON_ALLOCATE)
    assert lesson_view(calm, done) is None


def test_skipped_lesson_comes_back_once(calm: ContentLibrary, make_char: MakeChar) -> None:
    """略過與上完分開記；略過之後離開、第一次進城鎮再提示一次，出過就不再出。"""
    chosen = _chosen(calm, make_char)
    skipped = _seen(calm, chosen, LESSON_ALLOCATE_SKIP)
    assert LESSON_ALLOCATE not in skipped.hints_seen
    assert lesson_view(calm, skipped) is None  # 還在原地：不馬上再問
    assert lesson_view(calm, _do(calm, skipped, RestAction())) is None
    away = _do(calm, skipped, TravelAction(to="ferry_steps"))
    assert LESSON_ALLOCATE_LEFT in away.hints_seen
    assert not at_service(calm, away) and lesson_view(calm, away) is None  # 野外不提示
    back = _do(calm, away, TravelAction(to="mist_ferry"))
    again = lesson_view(calm, back)
    assert again is not None and again.kind == "allocate" and again.reminder and again.respec
    assert again.points == 8
    assert [line.speaker_zh for line in again.lines] == ["葛蘭"]
    assert again.lines != lesson_view(calm, chosen).lines  # type: ignore[union-attr]
    shown = _seen(calm, back, LESSON_ALLOCATE_AGAIN)
    assert lesson_view(calm, shown) is None
    assert lesson_view(calm, _do(calm, shown, TravelAction(to="ferry_steps"))) is None
    finished = _seen(calm, back, LESSON_ALLOCATE)  # 這次照做了
    assert lesson_view(calm, finished) is None


def test_skipped_lesson_comes_back_at_a_campfire(calm: ContentLibrary, make_char: MakeChar) -> None:
    """略過之後第一次進的是營火：也提示。"""
    skipped = _seen(calm, _chosen(calm, make_char), LESSON_ALLOCATE_SKIP)
    away = _do(calm, skipped, TravelAction(to="ferry_steps"))
    assert lesson_view(calm, away) is None
    # 紮營的條件（清空敵人、補給）另有測試；這裡直接擺成「在這裡紮了營」
    camped = away.model_copy(
        update={"camped_at": LocationRef(region=away.region, location=away.location)}
    )
    assert at_service(calm, camped)
    again = lesson_view(calm, camped)
    assert again is not None and again.kind == "allocate" and again.reminder


def test_old_characters_keep_the_old_lesson_order(
    calm: ContentLibrary, make_char: MakeChar
) -> None:
    """已完成開局的舊角色：2 級、有沒分的點、在霧渡鎮＝配點教學（不用重配）；之後接第一次閃現
    （新手第 1 步打完就教，和改前相同）；換地點不會記略過的紀錄。"""
    quest = QuestState(quest="starter_ferry", steps_done=1, started_at=NOON)
    old = make_char(level=2, attribute_points=2, location="mist_ferry", quests=(quest,))
    flash = {s: acquire(s).model_copy(update={"used": True}) for s in old.hero.skills}
    old = old.model_copy(update={"flash": dict(sorted(flash.items())), "insight": 1})
    assert old.opening is None
    lesson = lesson_view(calm, old)
    assert lesson is not None and lesson.kind == "allocate"
    assert not lesson.respec and not lesson.reminder
    assert lesson.points == 2 and lesson.start_points == calm.roguelite.start_free_points
    after = lesson_view(calm, _seen(calm, old, LESSON_ALLOCATE))
    assert after is not None and after.kind == "flash"
    moved = _do(calm, _seen(calm, old, LESSON_ALLOCATE), TravelAction(to="ferry_steps"))
    assert LESSON_ALLOCATE_LEFT not in moved.hints_seen
