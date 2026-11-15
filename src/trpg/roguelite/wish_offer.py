"""許願池「願望驅動」的完整技能三選一（Phase PK-4；07 7.6「許願池：願望驅動」）。

照願望標籤做候選、打分、挑 3 張（:func:`~trpg.skillgen.wish_pick.wish_cards`），再照一般完整技能
三選一換到角色階級、加上完整技能的強度（:func:`~trpg.roguelite.offers.as_complete`，+120‰，
07 7.6 第 7 點「強度照完整技能」），寫成 :class:`~trpg.roguelite.state.SkillOffer`：每張的標示
（``OfferTag``）帶 ``pick``（``llm``／``top``）、回應願望的一句與做不到時的那一行（照最後給出的
技能重算，:func:`wish_offer_tags`）。

挑選器（LLM）由呼叫端傳入（大世界的預先生成）；世界引擎不傳＝依排序取前 3 名（同一組種子，
確定性）。「任何池」、中性奇幻（``region=None``，#126）。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.content.library import ContentLibrary
from trpg.content.skill_pick import WishTags
from trpg.roguelite.offers import as_complete, at_run_tier, candidate_request, pick_player
from trpg.roguelite.state import LlmRecord, OfferTag, RunState, SkillOffer
from trpg.shared.types import top_attribute
from trpg.skillgen.candidates import LlmTrace, follows_attr
from trpg.skillgen.wish_pick import WishChosen, WishPicker, wish_cards, wish_miss_zh

__all__ = ["make_wish_offer", "wish_offer_tags"]


def _record(trace: LlmTrace | None, offer_index: int) -> LlmRecord | None:
    if trace is None:
        return None
    return LlmRecord(
        offer=offer_index,
        kind="new",
        keywords=trace.keywords,
        rarity=trace.rarity,
        attempts=trace.attempts,
        ok=trace.ok,
        codes=trace.codes,
        reason=trace.reason,
        name_source=trace.name_source,
        name_attempts=trace.name_attempts,
        name_codes=trace.name_codes,
        prompt_version=trace.prompt_version,
        pick_seeds=trace.pick_seeds,
        pick_designs=trace.pick_designs,
        pick_index=trace.pick_index,
        pick_reason=trace.pick_reason,
    )


def _tag(card: WishChosen, offer_index: int) -> OfferTag:
    return OfferTag(
        kind="new",
        keywords=card.keywords,
        source="composer",
        llm=_record(card.trace, offer_index),
        pick=card.pick,
        wish_reply_zh=card.reply_zh,
    )


def make_wish_offer(
    library: ContentLibrary,
    run: RunState,
    tags: WishTags,
    *,
    picker: WishPicker | None = None,
) -> SkillOffer:
    """第 ``run.offers_made`` 組（呼叫者負責把計數器加 1）許願池三選一（見模組說明）。"""
    request = replace(candidate_request(library, run), region=None)
    result = wish_cards(library, request, tags, pick_player(library, run), picker=picker)
    tier = request.tier
    candidates = tuple(
        as_complete(library, at_run_tier(library, c.skill, tier)) for c in result.cards
    )
    top = top_attribute(run.hero.attributes)
    offer = SkillOffer(
        reason="complete",
        tier=tier,
        top_attribute=top,
        candidates=candidates,
        off_route=tuple(
            i for i, s in enumerate(candidates) if not follows_attr(s, top, request.weapon_attrs)
        ),
        tags=tuple(_tag(c, run.offers_made) for c in result.cards),
    )
    return wish_offer_tags(library, offer, tags)


def wish_offer_tags(library: ContentLibrary, offer: SkillOffer, tags: WishTags) -> SkillOffer:
    """每張「做不到」的那一行照最後給出的技能重算（程式產生；引擎收下 LLM 版時也用，不信任傳進來的
    文字）。"""
    fixed = tuple(
        t.model_copy(update={"wish_miss_zh": wish_miss_zh(library, s, tags)})
        for s, t in zip(offer.candidates, offer.tags, strict=True)
    )
    return offer.model_copy(update={"tags": fixed})
