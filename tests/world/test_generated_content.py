"""6L-2：大世界三個 LLM 入口（閃現、劇情技能「破霧」、古松祭壇的機遇）經生成內容的供應者
（``trpg.world.generated``），來源記進日誌，重播只讀日誌、不呼叫 LLM。全部用 Mock，不需網路。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_opportunity import ALTAR, OPPORTUNITY, _at_altar, _charged
from trpg.api.llm_source import MockLlmProvider
from trpg.api.world_pregen import Generators, provider_generators
from trpg.content.library import ContentLibrary
from trpg.roguelite.offers import make_offer
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.story_theme import damage_elements
from trpg.world.actions import (
    FlashAction,
    FlashOfferedEvent,
    FlashPickAction,
    FlashPickedEvent,
    OfferPickAction,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    StorySkillGrantedEvent,
    WorldAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.generated import (
    FlashGen,
    FlashGenRequest,
    GenRequest,
    OfferGen,
    OfferGenRequest,
    StoryGen,
    StoryGenRequest,
    recorded,
    using_generated,
)
from trpg.world.growth import skill_region, world_library
from trpg.world.quests import advance_quests
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_log_entry, loads_log
from trpg.world.state import CharacterState, QuestState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]
SKILL = "skill_war_hymn"
STORY = "skill_mist_breaker"


class Counting:
    """供應者：用 Mock 生成函式當場產生（記下呼叫次數與請求）。``broken`` 為真時回不合格的紀錄。"""

    def __init__(self, library: ContentLibrary, *, broken: bool = False) -> None:
        self.library = library
        self.gens: Generators = provider_generators(MockLlmProvider())
        self.requests: list[GenRequest] = []
        self.broken = broken

    def __call__(self, request: GenRequest) -> FlashGen | StoryGen | OfferGen | None:
        self.requests.append(request)
        view = world_library(self.library)
        if isinstance(request, FlashGenRequest):
            assert self.gens.flash is not None
            return self.gens.flash(view, request)
        if isinstance(request, StoryGenRequest):
            assert self.gens.story is not None
            made = self.gens.story(view, request)
            return made.model_copy(update={"element": "holy_fire"}) if self.broken else made
        assert isinstance(request, OfferGenRequest)
        assert self.gens.offer is not None
        made_offer = self.gens.offer(view, request)  # Mock 提議器真的被呼叫（題目是史詩，常退回）
        offer = made_offer.offer
        if offer is None:  # 模擬模型提議成功：拿組合器的三選一，第一張標成 LLM
            offer = make_offer(
                view,
                request.run,
                "complete",
                region_keywords=request.region_keywords,
                tier_bonus=request.tier_bonus,
                pinned_keyword=request.pinned_keyword,
                region=request.region,
            )
            tags = (offer.tags[0].model_copy(update={"source": "llm"}), *offer.tags[1:])
            offer = offer.model_copy(update={"tags": tags})
        if self.broken:
            offer = offer.model_copy(update={"tier": offer.tier + 5})
        return OfferGen(key=request.key, source="llm", offer=offer)


def _never(request: GenRequest) -> None:
    raise AssertionError(f"重播不可以呼叫 LLM：{request.key}")


def _step(
    library: ContentLibrary,
    char: CharacterState,
    action: WorldAction,
    supplier: Callable[[GenRequest], FlashGen | StoryGen | OfferGen | None] | None,
) -> tuple[StepResult, tuple[FlashGen | StoryGen | OfferGen, ...]]:
    with using_generated(supplier) as used:
        result = world_step(library, make_world(), char, action, NOON)
    return result, tuple(used)


def _flashable(char: CharacterState) -> CharacterState:
    flash = {SKILL: acquire(SKILL).model_copy(update={"used": True})}
    return char.model_copy(update={"flash": flash, "insight": 4})


# ---------------------------------------------------------------------------
# 閃現與重閃
# ---------------------------------------------------------------------------


def test_flash_calls_llm_and_records_source(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _flashable(make_char()).model_copy(update={"skill_regions": {SKILL: "cloud_ridge"}})
    supplier = Counting(library)
    result, used = _step(library, char, FlashAction(skill=SKILL), supplier)
    assert len(supplier.requests) == 1
    request = supplier.requests[0]
    assert isinstance(request, FlashGenRequest)
    assert request.request.region == "cloud_ridge"  # 閃現的變化名照原技能的界域（#126）
    offered = next(e for e in result.events if isinstance(e, FlashOfferedEvent))
    assert offered.source in {"llm", "partial"}  # Mock 湊不滿時其餘用模板補
    assert [type(g) for g in used] == [FlashGen]
    assert isinstance(used[0], FlashGen) and used[0].record.source == offered.source
    assert used[0].record.accepted
    # 選了之後，新技能沿用原技能的界域
    picked = world_step(library, make_world(), result.char, FlashPickAction(pick=0), NOON)
    new_skill = next(e for e in picked.events if isinstance(e, FlashPickedEvent)).new_skill
    assert picked.char.skill_regions[new_skill] == "cloud_ridge"
    assert skill_region(picked.char, new_skill) == "cloud_ridge"


def test_flash_replay_reads_log_only(library: ContentLibrary, make_char: MakeChar) -> None:
    """驗收 1：同一角色重播後，閃現選項完全相同（重播只讀日誌，不呼叫 LLM）。"""
    char = _flashable(make_char())
    live, used = _step(library, char, FlashAction(skill=SKILL), Counting(library))
    again, used_again = _step(library, char, FlashAction(skill=SKILL), recorded(used))
    assert again.char.pending_flash == live.char.pending_flash
    assert used_again == used
    # 透過日誌重播（trpg.world.replay 自己裝上記錄的供應者）
    entry = WorldLogEntry(
        seq=1,
        now=NOON,
        character_id=char.character_id,
        action=FlashAction(skill=SKILL),
        generated=used,
    )
    (loaded,) = loads_log('{"format": "trpg-wlog/9"}\n' + dumps_log_entry(entry) + "\n")
    with using_generated(_never):  # 外面裝了會報錯的供應者：replay 不用它
        out = replay(library, make_world(), {char.character_id: char}, [loaded])
    assert out.characters[char.character_id].pending_flash == live.char.pending_flash
    # 沒有記錄的舊日誌＝模板（和 6L-2 以前相同）
    plain = world_step(library, make_world(), char, FlashAction(skill=SKILL), NOON)
    old = replay(
        library,
        make_world(),
        {char.character_id: char},
        [entry.model_copy(update={"generated": ()})],
    )
    assert old.characters[char.character_id].pending_flash == plain.char.pending_flash


def test_flash_falls_back_when_model_off(library: ContentLibrary, make_char: MakeChar) -> None:
    """驗收 2：模型關閉（沒有供應者或供應者回 None）時用模板，照常可以閃。"""
    char = _flashable(make_char())
    plain = world_step(library, make_world(), char, FlashAction(skill=SKILL), NOON)
    off, used = _step(library, char, FlashAction(skill=SKILL), None)
    assert off.char.pending_flash == plain.char.pending_flash
    assert isinstance(used[0], FlashGen) and used[0].record.source == "template"
    event = next(e for e in off.events if isinstance(e, FlashOfferedEvent))
    assert event.source == "template"


def test_flash_not_asked_when_illegal(library: ContentLibrary, make_char: MakeChar) -> None:
    """出題本身不合法（沒用過、點數不足）時不問 LLM。"""
    supplier = Counting(library)
    with pytest.raises(WorldActionError):
        _step(
            library,
            make_char().model_copy(update={"insight": 4}),
            FlashAction(skill=SKILL),
            supplier,
        )
    assert supplier.requests == []


# ---------------------------------------------------------------------------
# 劇情技能「破霧」
# ---------------------------------------------------------------------------


def _story_char(make_char: MakeChar) -> CharacterState:
    char = make_char(location="mist_temple_gate")
    quest = QuestState(quest="main_mist_rift", started_at=NOON, steps_done=1)
    return char.model_copy(update={"quests": (quest,), "affinity": {"daoist_qingya": 30}})


def _granted(
    library: ContentLibrary,
    char: CharacterState,
    supplier: Callable[[GenRequest], FlashGen | StoryGen | OfferGen | None] | None,
) -> tuple[CharacterState, StorySkillGrantedEvent, tuple[FlashGen | StoryGen | OfferGen, ...]]:
    with using_generated(supplier) as used:
        after, events = advance_quests(library, make_world(), char, (), NOON)
    granted = next(e for e in events if isinstance(e, StorySkillGrantedEvent))
    return after, granted, tuple(used)


def test_story_skill_rethemed_by_keywords(library: ContentLibrary, make_char: MakeChar) -> None:
    """驗收 3：元素跟著玩家的關鍵字換，骨架和預算不變；來源記下來；取得地點＝雲嶺。"""
    char = _story_char(make_char)
    content_char, content_event, content_used = _granted(library, char, None)
    content = next(s for s in content_char.generated_skills if s.id == STORY)
    assert content.name_zh == "破霧" and content_event.source == "content"
    assert isinstance(content_used[0], StoryGen) and content_used[0].source == "content"

    supplier = Counting(library)
    after, event, used = _granted(library, char, supplier)
    request = supplier.requests[0]
    assert isinstance(request, StoryGenRequest) and request.region == "cloud_ridge"
    assert request.elements  # 預設主角持有凍結、隱蔽 → 冰霜、暗影
    themed = next(s for s in after.generated_skills if s.id == STORY)
    assert event.source == "llm"
    assert damage_elements(themed) == (request.elements[0],)
    assert damage_elements(themed) != damage_elements(content)
    assert themed.name_zh != "破霧"
    # 骨架與預算不變
    view = world_library(library)
    assert themed.skeleton == content.skeleton and themed.shape == content.shape
    assert themed.cost == content.cost and themed.ap_cost == content.ap_cost
    assert [e.type for e in themed.effects] == [e.type for e in content.effects]
    assert skill_budget(themed, view).total == skill_budget(content, view).total
    assert after.skill_regions[STORY] == "cloud_ridge"
    # 重播只讀紀錄
    replayed, _, _ = _granted(library, char, recorded(used))
    assert replayed == after
    _granted(library, char, recorded(used))


def test_story_skill_invalid_proposal_falls_back(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """驗證失敗（元素不在選單內）時用內容版。"""
    after, event, used = _granted(library, _story_char(make_char), Counting(library, broken=True))
    skill = next(s for s in after.generated_skills if s.id == STORY)
    assert skill.name_zh == "破霧" and event.source == "content"
    assert isinstance(used[0], StoryGen) and used[0].source == "content"


# ---------------------------------------------------------------------------
# 古松祭壇的機遇（完整技能三選一）
# ---------------------------------------------------------------------------


def test_opportunity_offer_from_llm(library: ContentLibrary, make_char: MakeChar) -> None:
    from trpg.world.actions import EventSolveAction  # noqa: PLC0415

    char = _at_altar(_charged(make_char()))
    supplier = Counting(library)
    result, used = _step(library, char, EventSolveAction(solution=OPPORTUNITY), supplier)
    request = supplier.requests[0]
    assert isinstance(request, OfferGenRequest) and request.region == "cloud_ridge"
    offered = next(e for e in result.events if isinstance(e, SkillOfferedEvent))
    assert offered.made_by == "llm"
    gen = used[0]
    assert isinstance(gen, OfferGen) and gen.source == "llm" and gen.offer is not None
    pending = result.char.pending_offers[0]
    assert pending.offer == gen.offer and pending.region == "cloud_ridge"
    assert any(t.source == "llm" for t in pending.offer.tags)
    # 重播只讀紀錄
    again, _ = _step(library, char, EventSolveAction(solution=OPPORTUNITY), recorded(used))
    assert again.char == result.char
    # 學到的技能記下取得地點
    picked = world_step(library, make_world(), result.char, OfferPickAction(pick=0), NOON)
    taken = next(e for e in picked.events if isinstance(e, SkillOfferTakenEvent))
    assert taken.skill is not None and picked.char.skill_regions[taken.skill] == "cloud_ridge"
    assert ALTAR in picked.char.opportunities


@pytest.mark.parametrize("broken", [False, True])
def test_opportunity_falls_back(library: ContentLibrary, make_char: MakeChar, broken: bool) -> None:
    """模型關閉（沒有供應者）或驗證失敗（階級不對）時用組合器，結果和 6L-2 以前相同。"""
    from trpg.world.actions import EventSolveAction  # noqa: PLC0415

    char = _at_altar(_charged(make_char()))
    plain = world_step(library, make_world(), char, EventSolveAction(solution=OPPORTUNITY), NOON)
    supplier = Counting(library, broken=True) if broken else None
    result, used = _step(library, char, EventSolveAction(solution=OPPORTUNITY), supplier)
    assert result.char == plain.char
    assert isinstance(used[0], OfferGen) and used[0].source == "composer"
    offered = next(e for e in result.events if isinstance(e, SkillOfferedEvent))
    assert offered.made_by == "composer"


# ---------------------------------------------------------------------------
# 日誌與存檔
# ---------------------------------------------------------------------------


def test_log_line_without_generated_is_unchanged() -> None:
    entry = WorldLogEntry(seq=1, now=NOON, character_id="alice", action=FlashPickAction(pick=0))
    assert "generated" not in dumps_log_entry(entry)
    (old,) = loads_log('{"format": "trpg-wlog/7"}\n' + dumps_log_entry(entry) + "\n")
    assert old == entry


def test_old_char_without_regions_is_neutral(library: ContentLibrary, make_char: MakeChar) -> None:
    from trpg.world.save import dumps_char, loads_char  # noqa: PLC0415

    char = make_char()
    text = (
        dumps_char(char)
        .replace('"trpg-char/13"', '"trpg-char/7"')
        .replace('"skill_regions": {},', "")
    )
    old = loads_char(text)
    assert old.format == "trpg-char/13" and old.skill_regions == {}
    assert skill_region(old, SKILL) is None
