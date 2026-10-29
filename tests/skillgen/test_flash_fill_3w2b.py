"""Phase 3W-2b 第 5 點：強度下限讓選項不足時，補這一招的通用小變化湊滿（不出空選項）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.flash import (
    FlashRequest,
    UsageSource,
    _Builder,
    _fill_up,
    allowed_categories,
    category_counts,
    make_offer,
)
from trpg.skillgen.flash_state import acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.whiteboard import compose_whiteboard


def _request(board: SkillDef, seed: int, tier: int, **extra: object) -> FlashRequest:
    state = acquire(board.id).model_copy(update={"used": True})
    return FlashRequest(board, state, SkillUsage(), seed, tier=tier, **extra)  # type: ignore[arg-type]


def _boards(kind: str, tier: int, count: int = 40) -> list[SkillDef]:
    lib = library()
    return [compose_whiteboard(seed, kind=kind, tier=tier, library=lib) for seed in range(count)]


def test_fill_up_adds_generic_minor_variations_without_duplicates() -> None:
    lib = library()
    board = next(b for b in _boards("active", 2) if b.skeleton == "strike")
    request = _request(board, 3, 2)
    source = UsageSource()
    builder = _Builder(lib, request, 0)
    one = make_offer(lib, request).options[:1]
    assert len(one) == 1
    filled = _fill_up(lib, request, source, builder, board, options=list(one), count=4)
    assert len(filled) == 4
    keys = [o.variation.key() for o in filled]
    assert len(set(keys)) == 4 and keys[0] == one[0].variation.key()
    # 已經夠數就原樣回傳
    assert _fill_up(lib, request, source, builder, board, options=list(filled), count=3) == filled


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_normal_whiteboards_always_get_a_full_open_offer(tier: int) -> None:
    lib = library()
    rule = lib.flash.pricing.open
    for board in _boards("active", tier):
        if board.skeleton not in {"strike", "area", "trap"}:
            continue
        offer = make_offer(lib, _request(board, 5, tier))
        assert len(offer.options) == rule.options, (board.id, len(offer.options))
        assert len({o.variation.key() for o in offer.options}) == rule.options


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_no_whiteboard_offer_is_empty_except_known_gaps(tier: int) -> None:
    """所有白板（主動、被動、反應）的開放式出題都至少有 1 個選項；已知的無解組合（單一效果的
    被動毒牙在 1 階、階梯最頂端的 3 階烈焰／冰川姿態）列在報告的待決。"""
    lib = library()
    empty = []
    for kind in ("active", "passive", "reaction"):
        for board in _boards(kind, tier):
            if not make_offer(lib, _request(board, 5, tier)).options:
                empty.append((board.kind, board.name_zh))
    assert {name for _, name in empty} <= {"毒牙", "烈焰姿態", "冰川姿態"}, empty


def test_summon_whiteboards_get_the_toughen_variation() -> None:
    lib = library()
    found = 0
    for board in _boards("active", 2):
        if board.skeleton != "summon":
            continue
        offer = make_offer(lib, _request(board, 5, 2))
        found += any(o.variation.template == "summon_toughen" for o in offer.options)
    assert found >= 1


def test_focused_offers_never_borrow_from_other_categories() -> None:
    """3W-2c：指定類別只出該類（不到選項數就少出）；每個選項的類別都是指定的那一類。"""
    lib = library()
    rule = lib.flash.pricing.focused
    short = full = 0
    for tier in (1, 2, 3):
        for board in _boards("active", tier, 20):
            request = _request(board, 5, tier)
            for category, count in category_counts(lib, request).items():
                if count == 0:
                    continue
                offer = make_offer(lib, _request(board, 5, tier, category=category))
                assert offer.options, (board.id, category)
                assert {o.variation.category for o in offer.options} == {category}
                assert len(offer.options) == count <= rule.options
                short += count < rule.options
                full += count == rule.options
    assert short >= 1 and full >= 1  # 兩種情況都有被測到


def test_category_counts_match_what_a_focused_offer_shows() -> None:
    lib = library()
    for board in _boards("active", 2, 15) + _boards("passive", 2, 15):
        request = _request(board, 7, 2)
        counts = category_counts(lib, request)
        assert counts and all(
            c in counts for c in allowed_categories(lib.flash, board, major=False)
        )
        for category, count in counts.items():
            focused = _request(board, 7, 2, category=category)
            if count == 0:
                with pytest.raises(ValueError, match="沒有合格"):
                    make_offer(lib, focused)
            else:
                assert len(make_offer(lib, focused).options) == count


def test_unfocused_offers_may_still_fill_from_any_category() -> None:
    lib = library()
    rule = lib.flash.pricing.open
    categories_seen = 0
    for board in _boards("active", 2, 20):
        offer = make_offer(lib, _request(board, 5, 2))
        assert len(offer.options) <= rule.options
        categories_seen += len({o.variation.category for o in offer.options}) >= 2
    assert categories_seen >= 1
