"""許願池（Phase WP-1；:mod:`trpg.world.wish`；``docs/phases/PhaseWP計畫.md`` 第 2、3.3 節）。

- 選單許願：扣任務幣、本週次數、完整技能三選一三張都帶第 1 個關鍵字；每週 2 次、換週重算。
- 都不拿：次數照扣、退一半任務幣；選一招照一般三選一。
- 不能許的情況一律拒絕、狀態不變（主城、入門期、遭遇、次數、任務幣、關鍵字）。
- 文字許願：只從生成內容的供應者拿資料；沒對上＝拒絕且不扣錢；三選一不合格只丟三選一。
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.roguelite.state import SkillOffer
from trpg.world.actions import (
    OfferPickAction,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    WishAction,
    WishMadeEvent,
)
from trpg.world.errors import WorldActionError
from trpg.world.generated import GenRequest, Record, WishGen, WishGenRequest, using_generated
from trpg.world.opening import new_opening
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import world_step
from trpg.world.wish import (
    WISH_NO_MATCH_ZH,
    WISH_QUEST,
    wish_menu,
    wish_problem,
    wishes_left,
)

MakeChar = Callable[..., CharacterState]
WEEK = 7 * 86_400


def _capital(make_char: MakeChar, coins: int = 20) -> CharacterState:
    return make_char(region="capital", location="capital", quest_coins=coins)


def _wish(
    library: ContentLibrary,
    char: CharacterState,
    action: WishAction,
    *,
    now: int = NOON,
    world: WorldState | None = None,
) -> tuple[CharacterState, tuple[object, ...]]:
    result = world_step(library, world or make_world(), char, action, now)
    return result.char, result.events


def _skip(library: ContentLibrary, char: CharacterState, now: int = NOON) -> CharacterState:
    return world_step(library, make_world(), char, OfferPickAction(), now).char


MENU = WishAction(keywords=("frozen", "collision"))


# ---------------------------------------------------------------------------
# 選單許願
# ---------------------------------------------------------------------------


def test_menu_wish_charges_counts_and_offers(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    after, events = _wish(library, char, MENU)
    assert after.quest_coins == 16
    assert after.wish_week is not None and after.wish_week.used == 1
    (pending,) = after.pending_offers
    assert (pending.source, pending.quest, pending.refund) == ("wish", WISH_QUEST, 2)
    assert pending.region == "capital"
    assert pending.offer.reason == "complete" and len(pending.offer.candidates) == 3
    assert all("frozen" in t.keywords for t in pending.offer.tags)
    made = next(e for e in events if isinstance(e, WishMadeEvent))
    assert (made.via, made.keywords, made.made_by) == ("menu", ("frozen", "collision"), "composer")
    assert (made.coins_spent, made.used, made.refund) == (4, 1, 2)
    offered = next(e for e in events if isinstance(e, SkillOfferedEvent))
    assert offered.source == "wish"
    assert after.offers_made == char.offers_made + 1


def test_menu_wish_is_deterministic(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    one, _ = _wish(library, char, MENU)
    two, _ = _wish(library, char, MENU)
    assert one == two


def test_two_wishes_a_week(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    first, _ = _wish(library, char, MENU)
    second, _ = _wish(library, _skip(library, first), MENU)
    assert second.wish_week is not None and second.wish_week.used == 2
    ready = _skip(library, second)
    assert wishes_left(library, make_world(), ready, NOON) == 0
    with pytest.raises(WorldActionError, match="這週已經許了 2 次願"):
        _wish(library, ready, MENU)
    # 換週：重新算
    later = NOON + WEEK
    assert wishes_left(library, make_world(), ready, later) == 2
    third, _ = _wish(library, ready, MENU, now=later)
    assert third.wish_week is not None
    assert (third.wish_week.week, third.wish_week.used) == (1, 1)


def test_skip_refunds_half_and_keeps_count(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    after, _ = _wish(library, char, MENU)
    result = world_step(library, make_world(), after, OfferPickAction(), NOON)
    assert result.char.quest_coins == 18
    assert result.char.wish_week == after.wish_week
    assert not result.char.pending_offers
    taken = next(e for e in result.events if isinstance(e, SkillOfferTakenEvent))
    assert (taken.source, taken.skill, taken.refund) == ("wish", None, 2)


def test_pick_learns_the_skill(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    after, _ = _wish(library, char, MENU)
    result = world_step(library, make_world(), after, OfferPickAction(pick=0), NOON)
    taken = next(e for e in result.events if isinstance(e, SkillOfferTakenEvent))
    assert taken.skill is not None and taken.refund == 0
    assert result.char.quest_coins == 16  # 選了不退
    learned = (*result.char.hero.skills, *result.char.bench)
    assert taken.skill in learned
    assert result.char.skill_regions.get(taken.skill) == "capital"


# ---------------------------------------------------------------------------
# 不能許
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"region": "cloud_ridge", "location": "mist_ferry"}, "只有在主城能許願"),
        ({"quest_coins": 3}, "任務幣不足"),
    ],
)
def test_blocked_states(
    library: ContentLibrary, make_char: MakeChar, updates: dict[str, object], match: str
) -> None:
    char = _capital(make_char).model_copy(update=updates)
    with pytest.raises(WorldActionError, match=match):
        _wish(library, char, MENU)


def test_starter_period_blocks(library: ContentLibrary, make_char: MakeChar) -> None:
    opening = new_opening(7).model_copy(update={"stage": "starter"})
    char = _capital(make_char).model_copy(update={"opening": opening})
    assert wish_problem(library, make_world(), char, NOON) is not None
    with pytest.raises(WorldActionError):
        _wish(library, char, MENU)


@pytest.mark.parametrize(
    ("keywords", "match"),
    [
        (("frozen", "frozen"), "不能重複"),
        (("frozen", "collision", "ignite"), "1～2 個"),
        (("not_a_keyword",), "沒有這個關鍵字"),
    ],
)
def test_bad_menu_keywords(
    library: ContentLibrary, make_char: MakeChar, keywords: tuple[str, ...], match: str
) -> None:
    char = _capital(make_char)
    with pytest.raises(WorldActionError, match=match):
        _wish(library, char, WishAction(keywords=keywords))


def test_hidden_keywords_not_in_menu(library: ContentLibrary) -> None:
    hidden = {k.id for k in library.keywords.keywords if k.start_hidden}
    menu = wish_menu(library)
    assert menu and not hidden & set(menu)


def test_action_needs_exactly_one_way() -> None:
    with pytest.raises(ValueError, match="剛好一種"):
        WishAction()
    with pytest.raises(ValueError, match="剛好一種"):
        WishAction(text="冰", keywords=("frozen",))


# ---------------------------------------------------------------------------
# 文字許願（供應者是資料來源；真正的 LLM 在 API 層，見 tests/api/test_wish_pregen.py）
# ---------------------------------------------------------------------------

TEXT = WishAction(text="想把敵人凍住再一錘敲碎")


def _with(
    supplier: Callable[[GenRequest], Record | None] | None,
    library: ContentLibrary,
    char: CharacterState,
    action: WishAction = TEXT,
) -> tuple[CharacterState, tuple[object, ...], tuple[Record, ...]]:
    with using_generated(supplier) as used:
        after, events = _wish(library, char, action)
    return after, events, tuple(used)


def _fixed(gen: Callable[[WishGenRequest], WishGen]) -> Callable[[GenRequest], Record | None]:
    def supply(request: GenRequest) -> Record | None:
        assert isinstance(request, WishGenRequest)
        return gen(request)

    return supply


def test_text_wish_without_llm_is_refused_free(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _capital(make_char)
    for supplier in (None, _fixed(lambda r: WishGen(key=r.key))):
        with pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH):
            _with(supplier, library, char)
    with pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH):  # 沒裝供應者（模擬、測試）
        _wish(library, char, TEXT)


def test_text_wish_rejects_keywords_outside_menu(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _capital(make_char)
    bad = _fixed(lambda r: WishGen(key=r.key, source="partial", keywords=("frozen", "frozen")))
    with pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH):
        _with(bad, library, char)
    wrong_key = _fixed(lambda r: WishGen(key="wish:other", source="partial", keywords=("frozen",)))
    with pytest.raises(WorldActionError, match=WISH_NO_MATCH_ZH):
        _with(wrong_key, library, char)


def test_text_wish_with_keywords_only_uses_composer(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _capital(make_char)
    gen = _fixed(lambda r: WishGen(key=r.key, source="partial", keywords=("frozen", "collision")))
    after, events, used = _with(gen, library, char)
    menu_after, _ = _wish(library, char, MENU)
    assert after.pending_offers == menu_after.pending_offers  # 同樣的關鍵字＝同樣的組合器版
    made = next(e for e in events if isinstance(e, WishMadeEvent))
    assert (made.via, made.made_by) == ("text", "composer")
    (record,) = used
    assert isinstance(record, WishGen) and record.source == "partial"
    assert TEXT.text is not None and TEXT.text not in record.model_dump_json()


def _llm_offer(library: ContentLibrary, char: CharacterState) -> SkillOffer:
    """一份合格的「LLM 版」：拿組合器版、把第一張標成 LLM 提議的。"""
    after, _ = _wish(library, char, MENU)
    offer = after.pending_offers[0].offer
    tags = (offer.tags[0].model_copy(update={"source": "llm"}), *offer.tags[1:])
    return offer.model_copy(update={"tags": tags})


def test_text_wish_takes_a_valid_llm_offer(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    offer = _llm_offer(library, char)
    gen = _fixed(
        lambda r: WishGen(key=r.key, source="llm", keywords=("frozen", "collision"), offer=offer)
    )
    after, events, used = _with(gen, library, char)
    assert after.pending_offers[0].offer == offer
    made = next(e for e in events if isinstance(e, WishMadeEvent))
    assert made.made_by == "llm"
    (record,) = used
    assert isinstance(record, WishGen) and record.source == "llm"


def test_text_wish_drops_a_bad_llm_offer_only(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    offer = _llm_offer(library, char)
    wrong_tier = offer.model_copy(update={"tier": offer.tier + 1})
    gen = _fixed(lambda r: WishGen(key=r.key, source="llm", keywords=("frozen",), offer=wrong_tier))
    after, events, used = _with(gen, library, char)
    made = next(e for e in events if isinstance(e, WishMadeEvent))
    assert made.made_by == "composer"
    (record,) = used  # 日誌記下引擎最後收下的版本（只剩關鍵字）
    assert isinstance(record, WishGen) and (record.source, record.offer) == ("partial", None)
    assert all("frozen" in t.keywords for t in after.pending_offers[0].offer.tags)


def test_text_too_long_refused(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    with pytest.raises(WorldActionError, match="最多 60 個字"):
        _wish(library, char, WishAction(text="冰" * 61))


# ---------------------------------------------------------------------------
# 存檔
# ---------------------------------------------------------------------------


def test_save_round_trip_and_old_format(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _capital(make_char)
    after, _ = _wish(library, char, MENU)
    assert loads_char(dumps_char(after)) == after
    plain = json.loads(dumps_char(char))
    assert "wish_week" not in plain
    assert all("refund" not in json.dumps(p) for p in plain.get("pending_offers", []))
    old = dumps_char(char).replace('"trpg-char/14"', '"trpg-char/13"')
    assert loads_char(old) == char
