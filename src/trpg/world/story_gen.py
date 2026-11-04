"""劇情技能與機遇三選一的生成請求（Phase 6L-2；07 7.6、06 6.34.7）。

世界引擎（``quests._grant_story_skill``、``solutions._opportunity``）和 API 層的預先生成都用這裡的
函式組請求，鍵（:func:`~trpg.world.generated.input_key`）才會一致。

- **劇情技能**（:func:`story_request`、:func:`themed_story_skill`）：骨架固定、每人相同；LLM 只依
  玩家的關鍵字換元素（:func:`~trpg.skillgen.story_theme.story_elements` 的選單內）、名稱與描述
  （照取得地點的界域，#126）。引擎驗證：元素在選單內、換完預算不變
  （:func:`~trpg.skillgen.story_theme.retheme`）、文字通過長度與字元檢查；不過就用內容版。
- **機遇**（:func:`opportunity_request`、:func:`checked_offer`）：``make_offer`` 的參數同
  ``solutions._opportunity``；LLM 給的三選一要是完整技能、同階級、候選與標示一一對應，否則照常
  同步算（組合器）。
"""

from __future__ import annotations

import re

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world import NamingRules
from trpg.roguelite.offers import as_complete, at_run_tier, skill_defs
from trpg.roguelite.state import RunState, SkillOffer
from trpg.skillgen.candidates import keyword_distribution
from trpg.skillgen.story_theme import damage_elements, retheme, story_elements
from trpg.world.generated import OfferGenRequest, StoryGen, StoryGenRequest, input_key
from trpg.world.growth import as_run, char_library, hero_tier, world_library
from trpg.world.state import CharacterState

__all__ = [
    "checked_offer",
    "opportunity_request",
    "story_base",
    "story_request",
    "themed_story_skill",
]

_ASCII = re.compile(r"[A-Za-z]")
_TEXT_RULES = NamingRules()


def story_base(library: ContentLibrary, char: CharacterState, base: SkillDef) -> SkillDef:
    """內容版的劇情技能：照角色階級、完整技能強度（同 6L-2 以前的 ``_grant_story_skill``）。"""
    lib = world_library(library)
    return as_complete(lib, at_run_tier(lib, base, hero_tier(library, char.level)))


def story_request(
    library: ContentLibrary, char: CharacterState, skill: SkillDef, region: str | None
) -> StoryGenRequest:
    """``skill``（:func:`story_base` 做好的內容版）的生成請求：元素選單看玩家裝備中技能的關鍵字。"""
    lib = char_library(library, char)
    run = as_run(char)
    counts = keyword_distribution(skill_defs(lib, run, run.hero.skills), lib)
    elements = story_elements(lib, counts)
    keywords = tuple(sorted(counts.items()))
    weapon = library.weapons.get(char.hero.weapon)
    data = {
        "char": char.character_id,
        "skill": skill.model_dump(mode="json"),
        "elements": elements,
        "keywords": keywords,
        "region": region,
    }
    return StoryGenRequest(
        character_id=char.character_id,
        key=input_key(f"story/{skill.id}", data),
        skill=skill,
        elements=elements,
        keywords=keywords,
        region=region,
        weapon_zh=None if weapon is None else weapon.name_zh,
    )


def _text_ok(text: str | None, limit: int) -> bool:
    return text is not None and 0 < len(text.strip()) <= limit and not _ASCII.search(text)


def themed_story_skill(
    library: ContentLibrary, request: StoryGenRequest, gen: StoryGen
) -> SkillDef | None:
    """套用 LLM 的元素與文字；不合格（元素不在選單、預算變了、文字不合格）時 ``None``。內容版
    （``source="content"``）回傳原本的技能。"""
    skill = request.skill
    if gen.source == "content":
        return skill
    if gen.skill != skill.id:
        return None
    if gen.element is not None and (gen.element,) != damage_elements(skill):
        if gen.element not in request.elements:
            return None
        themed = retheme(world_library(library), skill, gen.element)
        if themed is None:
            return None
        skill = themed
    rules = _TEXT_RULES
    if not (
        _text_ok(gen.name_zh, rules.name_max_chars)
        and _text_ok(gen.concept, rules.concept_max_chars)
        and _text_ok(gen.cast_flavor, rules.flavor_max_chars)
    ):
        return None
    assert gen.name_zh is not None and gen.concept is not None and gen.cast_flavor is not None
    narrative = skill.narrative.model_copy(
        update={"concept": gen.concept, "cast_flavor": gen.cast_flavor}
    )
    return skill.model_copy(update={"name_zh": gen.name_zh, "narrative": narrative})


def opportunity_request(
    char: CharacterState,
    run: RunState,
    key: str,
    *,
    keyword: str | None,
    tier_bonus: int,
    region: str | None,
) -> OfferGenRequest:
    """機遇完整技能三選一的生成請求（``key`` 是 ``offer_key`` 的快取鍵）。"""
    return OfferGenRequest(
        character_id=char.character_id,
        key=f"opportunity:{char.character_id}:{key}",
        run=run,
        region_keywords=() if keyword is None else (keyword,),
        tier_bonus=tier_bonus,
        pinned_keyword=keyword,
        region=region,
    )


def checked_offer(offer: SkillOffer | None, expected_tier: int) -> SkillOffer | None:
    """LLM 版的三選一合不合格：完整技能、階級相同、候選與標示一一對應（數值與預算已由提議器與
    組合器驗過）。"""
    if offer is None or offer.reason != "complete" or offer.tier != expected_tier:
        return None
    if not offer.candidates or len(offer.tags) != len(offer.candidates):
        return None
    if any(s.tier != expected_tier for s in offer.candidates):
        return None
    if any(t.source not in {"llm", "composer", "pool"} for t in offer.tags):
        return None
    return offer
