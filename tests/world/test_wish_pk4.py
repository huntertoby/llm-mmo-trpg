"""PK-4 許願池「願望驅動」的世界規則（:mod:`trpg.world.wish`；07 7.6「許願池：願望驅動」）。

- 點選標籤（沒有 LLM）：照標籤做候選、排序取前 3 名；關鍵字、種類是出題條件；每張「做不到」那一行
  照實寫；扣款、次數、退款照舊；待選三選一帶願望原文與標籤。
- 文字許願：只從供應者拿標籤與（LLM 挑的）三選一；標籤不合清單＝拒絕、不扣錢；三選一不合格只丟
  三選一（引擎照標籤算）；「做不到」那一行由引擎重算。
- 選到的技能把願望原文記進魔導書扉頁（``skill_wishes``），重閃後也找得到。
- 開關關掉：不收標籤，其餘照舊流程（舊流程本身的測試在 ``test_wish.py``）。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.engine.helpers import wish_off
from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.skill_pick import WishTags
from trpg.roguelite.offers import candidate_request, pick_player
from trpg.roguelite.state import SkillOffer
from trpg.roguelite.wish_offer import make_wish_offer
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.skill_pick import design_key
from trpg.skillgen.wish_pick import tag_hits, wish_cards, wish_miss_zh
from trpg.world.actions import OfferPickAction, WishAction, WishMadeEvent
from trpg.world.errors import WorldActionError
from trpg.world.generated import GenRequest, Record, WishGen, WishGenRequest, using_generated
from trpg.world.growth import skill_wish, world_library
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState
from trpg.world.step import world_step
from trpg.world.wish import WISH_NO_MATCH_ZH, _wish_run, wish_request

MakeChar = Callable[..., CharacterState]
FIRE_FROST = WishTags(keywords=("frozen",), elements=("fire",))
TEXT = "想把敵人凍在火裡"


def _capital(make_char: MakeChar, coins: int = 20) -> CharacterState:
    return make_char(region="capital", location="capital", quest_coins=coins)


def _offer(library: ContentLibrary, char: CharacterState, tags: WishTags) -> SkillOffer:
    return make_wish_offer(world_library(library), _wish_run(make_world(), char), tags)


def test_tag_wish_offers_three_complete_skills_with_honest_lines(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _capital(make_char)
    result = world_step(library, make_world(), char, WishAction(tags=FIRE_FROST), NOON)
    after = result.char
    assert after.quest_coins == 16 and after.wish_week is not None and after.wish_week.used == 1
    (pending,) = after.pending_offers
    assert pending.source == "wish" and pending.refund == 2
    assert pending.wish is not None and pending.wish.text is None
    assert pending.wish.tags == FIRE_FROST
    offer = pending.offer
    assert offer.reason == "complete" and len(offer.candidates) == 3
    view = world_library(library)
    assert len({design_key(s) for s in offer.candidates}) == 3
    for skill, tag in zip(offer.candidates, offer.tags, strict=True):
        assert skill_has_keywords(skill, ("frozen",), view)  # 關鍵字是出題條件
        assert tag.pick == "top" and tag.wish_reply_zh is None
        assert tag.wish_miss_zh == wish_miss_zh(view, skill, FIRE_FROST)
    made = next(e for e in result.events if isinstance(e, WishMadeEvent))
    assert (made.via, made.keywords, made.tags, made.made_by) == (
        "menu",
        ("frozen",),
        FIRE_FROST,
        "composer",
    )
    # 確定性：同一個角色、同一組標籤，三選一逐字相同
    again = world_step(library, make_world(), char, WishAction(tags=FIRE_FROST), NOON)
    assert again.char.pending_offers[0].offer == offer


def test_kind_tag_is_a_hard_condition(library: ContentLibrary, make_char: MakeChar) -> None:
    offer = _offer(library, _capital(make_char), WishTags(kinds=("reaction",)))
    assert {s.kind for s in offer.candidates} == {"reaction"}


def test_wish_match_is_the_biggest_weight(library: ContentLibrary, make_char: MakeChar) -> None:
    """願望相合每命中一個標籤加 ``weights.wish_match``（高過協同的上限，07 7.6 第 3 點）；這一題分數
    第一名命中的標籤不少於其他候選。"""
    view = world_library(library)
    run = _wish_run(make_world(), _capital(make_char))
    tags = WishTags(effects=("damage",), shapes=("single",), elements=("fire",))
    result = wish_cards(view, candidate_request(view, run), tags, pick_player(view, run))
    ranked = result.slate.ranked
    assert 3 <= len(ranked) <= view.skill_pick.pool.wish_candidates
    weight = view.skill_pick.weights.wish_match
    for c in ranked:
        assert dict(c.parts)["wish"] == weight * len(tag_hits(view, c.skill, tags)[0])
    w = view.skill_pick.weights
    assert weight > w.synergy_per_link * w.synergy_max_links
    top_hits = len(tag_hits(view, ranked[0].skill, tags)[0])
    assert top_hits == max(len(tag_hits(view, c.skill, tags)[0]) for c in ranked)


def test_menu_needs_at_least_one_valid_tag(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    for bad in (WishTags(), WishTags(keywords=("nope",)), WishTags(elements=("fire", "ice"))):
        with pytest.raises(WorldActionError):
            world_step(library, make_world(), char, WishAction(tags=bad), NOON)


def test_old_client_keywords_become_keyword_tags(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _capital(make_char)
    result = world_step(library, make_world(), char, WishAction(keywords=("ignite",)), NOON)
    pending = result.char.pending_offers[0]
    assert pending.wish is not None and pending.wish.tags == WishTags(keywords=("ignite",))


def _supplier(gen: WishGen | None) -> Callable[[GenRequest], Record | None]:
    def supply(request: GenRequest) -> Record | None:
        if gen is None or not isinstance(request, WishGenRequest):
            return None
        assert request.tags_mode
        return gen.model_copy(update={"key": request.key})

    return supply


def test_text_wish_takes_a_valid_llm_offer_and_recomputes_lines(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _capital(make_char)
    offer = _offer(library, char, FIRE_FROST)
    # 傳進來的「做不到」那一行是亂寫的：引擎照標籤重算
    forged = offer.model_copy(
        update={
            "tags": tuple(
                t.model_copy(update={"pick": "llm", "wish_miss_zh": "都做得到"}) for t in offer.tags
            )
        }
    )
    gen = WishGen(
        key="x", source="llm", keywords=("frozen",), tags=FIRE_FROST, offer=forged, attempts=1
    )
    with using_generated(_supplier(gen)) as used:
        result = world_step(library, make_world(), char, WishAction(text=TEXT), NOON)
    pending = result.char.pending_offers[0]
    assert pending.wish is not None and pending.wish.text == TEXT
    assert [t.wish_miss_zh for t in pending.offer.tags] == [t.wish_miss_zh for t in offer.tags]
    made = next(e for e in result.events if isinstance(e, WishMadeEvent))
    assert (made.via, made.made_by) == ("text", "llm")
    (record,) = used
    assert isinstance(record, WishGen) and record.source == "llm"


def test_text_wish_drops_a_bad_offer_only(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    offer = _offer(library, char, FIRE_FROST)
    two = offer.model_copy(update={"candidates": offer.candidates[:2], "tags": offer.tags[:2]})
    gen = WishGen(key="x", source="llm", keywords=("frozen",), tags=FIRE_FROST, offer=two)
    with using_generated(_supplier(gen)) as used:
        result = world_step(library, make_world(), char, WishAction(text=TEXT), NOON)
    assert result.char.pending_offers[0].offer == offer  # 引擎照標籤算的那一份
    (record,) = used
    assert isinstance(record, WishGen) and record.source == "partial" and record.offer is None


@pytest.mark.parametrize(
    "gen",
    [
        None,
        WishGen(key="x", source="none"),
        WishGen(key="x", source="partial", keywords=("no",), tags=WishTags(keywords=("no",))),
        WishGen(key="x", source="partial", keywords=(), tags=WishTags(keywords=("ignite",))),
        WishGen(key="x", source="partial", keywords=(), tags=None),
    ],
)
def test_text_wish_without_valid_tags_is_refused_without_charge(
    library: ContentLibrary, make_char: MakeChar, gen: WishGen | None
) -> None:
    char = _capital(make_char)
    with using_generated(_supplier(gen)), pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH):
        world_step(library, make_world(), char, WishAction(text=TEXT), NOON)


def test_empty_tags_from_text_still_make_an_offer(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """願望對不上任何標籤（只講名字或故事）：照一般完整技能的打分出題（07 7.6 第 1 點）。"""
    char = _capital(make_char)
    gen = WishGen(key="x", source="partial", tags=WishTags())
    with using_generated(_supplier(gen)):
        result = world_step(library, make_world(), char, WishAction(text="我叫亞瑟"), NOON)
    pending = result.char.pending_offers[0]
    assert len(pending.offer.candidates) == 3
    assert all(t.wish_miss_zh is None for t in pending.offer.tags)


def test_taken_skill_gets_the_grimoire_page(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    gen = WishGen(key="x", source="partial", keywords=("frozen",), tags=FIRE_FROST)
    with using_generated(_supplier(gen)):
        wished = world_step(library, make_world(), char, WishAction(text=f"  {TEXT}  "), NOON).char
    taken = world_step(library, make_world(), wished, OfferPickAction(pick=0), NOON).char
    new = next(s for s in (*taken.hero.skills, *taken.bench) if s not in char.hero.skills)
    assert taken.skill_wishes == {new: TEXT}
    assert skill_wish(taken, new) == TEXT
    assert skill_wish(taken, f"{new}_t3") == TEXT  # 階級重配後的 ID 也找得到
    back = loads_char(dumps_char(taken))
    assert back == taken
    # 點選標籤（沒有願望原文）不寫扉頁；沒有扉頁的角色存檔不多欄位
    menu = world_step(library, make_world(), char, WishAction(tags=FIRE_FROST), NOON).char
    plain = world_step(library, make_world(), menu, OfferPickAction(pick=0), NOON).char
    assert plain.skill_wishes == {}
    assert '"skill_wishes"' not in dumps_char(plain)
    assert '"wish"' not in dumps_char(char)


def test_switch_off_refuses_tags(library: ContentLibrary, make_char: MakeChar) -> None:
    off = wish_off(library)
    char = _capital(make_char)
    with pytest.raises(WorldActionError, match="只收願望文字或選單的關鍵字"):
        world_step(off, make_world(), char, WishAction(tags=FIRE_FROST), NOON)
    result = world_step(off, make_world(), char, WishAction(keywords=("frozen",)), NOON)
    pending = result.char.pending_offers[0]
    assert pending.wish is None
    assert all(t.wish_miss_zh is None and t.pick is None for t in pending.offer.tags)
    request = wish_request(off, make_world(), char, TEXT)
    assert not request.tags_mode
    assert request.key != wish_request(library, make_world(), char, TEXT).key
